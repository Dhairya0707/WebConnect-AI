import json
import os
import requests
from search_engine import scrape_ddg_html
from scraper import scrape_urls, scrape_url

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

invoke_url = "https://integrate.api.nvidia.com/v1/chat/completions"

# API Key from environment variable
API_KEY = os.getenv("NVIDIA_API_KEY")

if not API_KEY:
    print("[llm_agent] WARNING: NVIDIA_API_KEY is not set. /search will return a clear error until it is configured.")

headers = {
    "Authorization": f"Bearer {API_KEY}",
    "Accept": "application/json",
    "Content-Type": "application/json"
}

def web_search_and_scrape(query: str):
    """
    Search DuckDuckGo and scrape pages. 
    Tries the top 3 results first; if empty, tries the next 3.
    """
    print(f"🔧 TOOL EXECUTED: web_search_and_scrape | Query: '{query}'")

    ddg_results = scrape_ddg_html(query, max_results=5)
    if not ddg_results:
        return "[WEB_SEARCH_UNAVAILABLE] No search results found.", []

    # --- Attempt 1: Top 3 links ---
    print(f"   => Attempting Scraping (Top 3 links)...", end=" ", flush=True)
    batch1_urls = [r["url"] for r in ddg_results[:3]]
    context = scrape_urls(batch1_urls)

    if context and context.strip():
        print("✅ Success")
    else:
        print("⚠️ Empty")
        # --- Attempt 2: Next 3 links (Offset) ---
        if len(ddg_results) > 3:
            print(f"   => Retrying with Offset (Next 3 links)...", end=" ", flush=True)
            batch2_urls = [r["url"] for r in ddg_results[3:6]]
            context = scrape_urls(batch2_urls)
            
            if context and context.strip():
                print("✅ Success")
            else:
                print("⚠️ Empty")

    # --- Fallback to Snippets if all scraping failed ---
    if not context or not context.strip():
        print("   => Falling back to search snippets.")
        context = "\n\n".join(
            f"Source: {r['title']}\nURL: {r['url']}\nSummary: {r['snippet']}"
            for r in ddg_results if r.get("snippet") and r["snippet"] != "No snippet"
        )
        
    if not context.strip():
        return "[WEB_SCRAPE_FAILED] No content could be retrieved from any source.", ddg_results

    # Cap context length
    max_char_limit = 20000
    if len(context) > max_char_limit:
        context = context[:max_char_limit] + "\n...[Content Truncated]..."

    return context, ddg_results

def direct_web_scrape(url: str):
    """
    Directly scrapes a single URL.
    """
    print(f"🔧 TOOL EXECUTED: direct_web_scrape | URL: '{url}'")
    
    content = scrape_url(url)
    if not content or not content.strip():
        return f"[WEB_SCRAPE_FAILED] Could not retrieve content from: {url}", []
    
    # Cap context length
    max_char_limit = 20000
    if len(content) > max_char_limit:
        content = content[:max_char_limit] + "\n...[Content Truncated]..."
    
    # Return as a snippet so it matches the format expected by all_sources
    source_record = {
        "title": url,
        "url": url,
        "snippet": "Content directly scraped from the provided URL."
    }
    
    return content, [source_record]

# Schema for the LLM
tools = [
     {
        "type": "function",
        "function": {
            "name": "web_search_and_scrape",
            "description": "Searches the internet and scrapes web page content to provide context. Give this tool a highly optimized search query.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Optimized search query, e.g. 'latest AI news today'"
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "direct_web_scrape",
            "description": "Scrapes a specific URL provided by the user to extract its content.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The full URL to scrape, e.g. 'https://example.com/article'"
                    }
                },
                "required": ["url"]
            }
        }
    }
]

# Load system prompt from external file for easy editing
_PROMPT_FILE = os.path.join(os.path.dirname(__file__), "system_prompt.md")

if os.path.exists(_PROMPT_FILE):
    with open(_PROMPT_FILE, "r") as f:
        _raw_prompt = f.read()
else:
    _raw_prompt = "You are an intelligent AI assistant with web search capabilities. Use the web_search_and_scrape tool for any recent or real-time information."

# Inject the REAL current date so the model never relies on its training cutoff year
import datetime
_today = datetime.datetime.now().strftime("%A, %B %d, %Y")
system_prompt = _raw_prompt.replace("{CURRENT_DATE}", _today)

def extract_manual_tool_calls(content: str):
    """
    Fallback for when models return tool calls as strings like:
    [TOOL_CALLS]web_search_and_scrape{"query": "..."}
    """
    if not content or "[TOOL_CALLS]" not in content:
        return None
    
    try:
        parts = content.split("[TOOL_CALLS]")
        if len(parts) < 2:
            return None
        
        tool_input = parts[1].strip()
        # Find the first brace for JSON
        brace_idx = tool_input.find("{")
        if brace_idx == -1:
            return None
        
        name = tool_input[:brace_idx].strip()
        args_str = tool_input[brace_idx:].strip()
        
        # Sometimes there's more text after the JSON, try to find the last closing brace
        last_brace = args_str.rfind("}")
        if last_brace != -1:
            args_str = args_str[:last_brace+1]
        
        return {
            "name": name,
            "arguments": args_str,
            "id": "manual_call_" + os.urandom(4).hex()
        }
    except Exception:
        return None

def run_agent_loop(user_input: str):
    """
    Executes a strict 2-stage agent process:
    1. Initial LLM call to decide if search is needed.
    2. Optional tool execution followed by a final synthesis call.
    """
    if not API_KEY:
        return {
            "content": (
                "Server configuration error: NVIDIA_API_KEY is missing. "
                "Set the environment variable in Railway and redeploy."
            ),
            "sources": []
        }

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user",   "content": user_input}
    ]

    payload = {
        "model": "mistralai/mistral-small-4-119b-2603",
        "messages": messages,
        "max_tokens": 16000,
        "temperature": 0.2,
        "tools": tools,
        "tool_choice": "auto"
    }

    all_sources = []

    print("\n[Thinking] Analyzing request...")
    response = requests.post(invoke_url, headers=headers, json=payload)

    if response.status_code != 200:
        return {"content": f"API Error ({response.status_code}): {response.text}", "sources": []}

    data    = response.json()
    message = data["choices"][0]["message"]
    finish  = data["choices"][0].get("finish_reason", "")

    # --- Case 1: Model wants to search (Standard or Manual Fallback) ---
    tool_calls = message.get("tool_calls") or []
    manual_call = extract_manual_tool_calls(message.get("content", ""))
    
    if manual_call:
        # If we found a manual call and no standard calls, use it
        if not tool_calls:
            tool_calls = [manual_call]
            # Clear the content so we don't treat it as a direct answer
            message["content"] = None
    
    if finish == "tool_calls" or tool_calls:
        messages.append(message)
        
        # Execute tool calls
        for tool_call in tool_calls:
            # Handle both standard object and our manual dict
            if hasattr(tool_call, "get"):
                # Manual dict or dict from API
                tc_id = tool_call.get("id")
                if "function" in tool_call:
                    name = tool_call["function"]["name"]
                    args_raw = tool_call["function"]["arguments"]
                else:
                    name = tool_call.get("name")
                    args_raw = tool_call.get("arguments")
            else:
                # Standard tool call object (if it's not a dict)
                tc_id = tool_call.id
                name = tool_call.function.name
                args_raw = tool_call.function.arguments

            try:
                args = json.loads(args_raw)
            except json.JSONDecodeError:
                args = {}

            if name == "web_search_and_scrape":
                query_to_search = args.get("query", user_input)
                tool_result, sources = web_search_and_scrape(query=query_to_search)
                if isinstance(sources, list):
                    all_sources.extend(sources)
                
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc_id,
                    "name": name,
                    "content": tool_result
                })

            elif name == "direct_web_scrape":
                url_to_scrape = args.get("url")
                if not url_to_scrape:
                    # Fallback check if the model used 'query' instead of 'url'
                    url_to_scrape = args.get("query")
                
                if url_to_scrape:
                    tool_result, sources = direct_web_scrape(url=url_to_scrape)
                    if isinstance(sources, list):
                        all_sources.extend(sources)
                    
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc_id,
                        "name": name,
                        "content": tool_result
                    })
                else:
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tc_id,
                        "name": name,
                        "content": "[ERROR] No URL provided to direct_web_scrape."
                    })

        # Final Synthesis Call
        print("\n[Synthesizing] Generating final response with web data...")
        payload["messages"] = messages
        # Force a stop after this call to avoid infinite recursion/loops
        payload["tool_choice"] = "none" 
        
        response2 = requests.post(invoke_url, headers=headers, json=payload)
        if response2.status_code == 200:
            final_msg = response2.json()["choices"][0]["message"]
            return {"content": final_msg.get("content", ""), "sources": all_sources}
        else:
            return {"content": f"Synthesis Error: {response2.text}", "sources": all_sources}

    else:
        # --- Case 2: Model answers directly ---
        return {"content": message.get("content", ""), "sources": []}

def print_final_answer(content: str):
    print("\n==================== FINAL ANSWER ====================")
    if content:
        print(content)
    else:
        print("[No response content returned by the model.]")
    print("======================================================\n")
