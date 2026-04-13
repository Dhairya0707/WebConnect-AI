import requests
from bs4 import BeautifulSoup
import urllib.parse
import time
import random


def scrape_ddg_html(query: str, max_results: int = 8) -> list[dict]:
    """
    Search DuckDuckGo via its plain-HTML endpoint and return rich result dicts.

    Each result dict has:
        - title   (str): Page title
        - url     (str): Final destination URL (DDG redirect unwrapped)
        - snippet (str): Short description / snippet

    Args:
        query (str): Search query string.
        max_results (int): Maximum number of results to return.

    Returns:
        list[dict]: Up to `max_results` result dicts.
    """
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Firefox/126.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
    ]

    results: list[dict] = []

    headers = {"User-Agent": random.choice(user_agents)}
    url = "https://html.duckduckgo.com/html/"
    params = {"q": query}

    try:
        response = requests.get(url, headers=headers, params=params, timeout=15)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        for result in soup.find_all("div", class_="result"):
            if len(results) >= max_results:
                break

            title_tag = result.find("a", class_="result__a")
            url_tag = result.find("a", class_="result__url")
            snippet_tag = result.find("a", class_="result__snippet")

            if not title_tag or not url_tag:
                continue

            raw_url = url_tag.get("href") or url_tag.get_text(strip=True)

            # Unwrap DDG redirect links (uddg= parameter)
            parsed = urllib.parse.urlparse(raw_url)
            query_params = urllib.parse.parse_qs(parsed.query)
            final_url = (
                urllib.parse.unquote(query_params["uddg"][0])
                if "uddg" in query_params
                else raw_url
            )

            # Skip DDG ad links that couldn't be fully unwrapped
            if "duckduckgo.com" in final_url:
                continue

            results.append(
                {
                    "title": title_tag.get_text(strip=True),
                    "url": final_url,
                    "snippet": snippet_tag.get_text(strip=True) if snippet_tag else "No snippet",
                }
            )

    except requests.exceptions.RequestException as e:
        print(f"[search_engine] Request to DuckDuckGo failed: {e}")

    return results


def search_web(query: str, num_results: int = 5, **kwargs) -> list[str]:
    """
    Search DuckDuckGo and return a list of result URLs.

    This is the primary function consumed by the rest of the pipeline.
    Extra kwargs (e.g. `region`, `timelimit`) are accepted but ignored so
    existing call-sites don't need to change.

    Args:
        query (str): The search query.
        num_results (int): Maximum number of URLs to return.

    Returns:
        list[str]: A list of result URLs.
    """
    results = scrape_ddg_html(query, max_results=num_results)
    return [r["url"] for r in results]
