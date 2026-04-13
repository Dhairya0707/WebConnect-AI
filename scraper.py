import requests
from bs4 import BeautifulSoup
import re
import concurrent.futures

def scrape_url(url: str, min_paragraph_chars: int = 50) -> str:
    """
    Fetch and clean text from a single URL using heuristics to avoid noise.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    }

    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return ""

    soup = BeautifulSoup(resp.text, "html.parser")

    # 1. Remove obvious noise tags
    for tag in soup(["script", "style", "noscript", "nav", "header", "footer", "aside", "meta", "link", "title"]):
        tag.decompose()

    # 2. Remove common layout/CSS noise classes
    noise_selectors = [
        ".cookie", ".cookie-banner", ".banner", ".ad", ".ads",
        ".advertisement", ".sidebar", ".aside", ".toc", ".table-of-contents",
        ".crumb", ".breadcrumb", ".nav", ".menu", ".pagination",
        "#cookie", "#cookies", "#cookie-banner", "#ad", "#ads", "#advertisement",
        "#toc", "#table-of-contents", "#footer", "#header", "#menu", "#sidebar",
    ]

    for sel in noise_selectors:
        for el in soup.select(sel):
            el.decompose()

    # 3. Remove elements with aria-hidden="true" or hidden
    for el in soup.select("[aria-hidden='true'], [hidden]"):
        el.decompose()

    # 4. Extract main content heuristics:
    main_block = (
        soup.select_one("main") or
        soup.select_one("article") or
        soup.select_one(".content") or
        soup.select_one(".main") or
        soup.select_one("#content") or
        soup.select_one("#main") or
        soup
    )

    if main_block:
        text = main_block.get_text(separator="\n", strip=True)
    else:
        text = soup.get_text(separator="\n", strip=True)

    # 5. Clean and normalize text
    text = re.sub(r"\n\s*\n\s*\n", "\n\n", text)
    text = re.sub(r"^\s*\n", "", text, flags=re.MULTILINE)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n +", "\n", text)
    text = re.sub(r" +\n", "\n", text)
    text = text.strip()

    # 6. Keep only meaningful lines
    lines = [line.strip() for line in text.split("\n")]
    meaningful = [
        line for line in lines
        if len(line) >= min_paragraph_chars or
           line.lower() in ("abstract", "introduction", "installation", "usage")
    ]

    if meaningful:
        return "\n\n".join(meaningful)

    return "\n\n".join(lines)

def scrape_urls(urls: list[str]) -> str:
    """
    Fetch content from multiple URLs concurrently and combine the results.
    """
    combined_text = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        future_to_url = {executor.submit(scrape_url, url): url for url in urls}
        for future in concurrent.futures.as_completed(future_to_url):
            url = future_to_url[future]
            try:
                data = future.result()
                if data:
                    combined_text.append(f"--- Context from {url} ---\n{data}\n--- End Context ---\n")
            except Exception as exc:
                print(f"{url} generated an exception: {exc}")
                
    return "\n".join(combined_text)
