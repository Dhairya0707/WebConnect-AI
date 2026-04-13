# Project Description: WebConnect AI System (Technical Deep-Dive)

## 🎯 Project Goal
The mission of this project is to create a **fully optimized, autonomous AI search engine** that operates at **zero cost** for developers. By bypassing premium Search APIs (like Bing or Google) and using free NVIDIA inference credits, this system provides a production-grade RAG (Retrieval-Augmented Generation) pipeline for free.

---

## 🏗️ The "Zero Cost" Approach
*   **Search Engine**: Instead of an API, we use direct HTML scraping of DuckDuckGo (`search_engine.py`).
*   **LLM Inference**: Powered by the **NVIDIA API Catalog** (Mistral-Small), which offers free credits to developers.
*   **Web Interface**: A responsive, modern frontend built with vanilla HTML/JS and a FastAPI backend.
*   **Compute**: Minimal Python overhead, designed to run locally or on basic 1-core cloud instances.

---

## 📂 Detailed File-by-File Analysis

### 1. `main.py` — The Orchestrator
The entry point that launches the high-performance **Uvicorn** server. It manages the web application lifecycle and environment configuration.

### 2. `api.py` — The Bridge
Acts as the communication layer between the frontend and the AI agent.
*   **Endpoints**:
    *   `GET /`: Serves the `index.html` workbench.
    *   `POST /search`: Receives queries, invokes the agent, and returns synthesized answers with source metadata.

### 3. `llm_agent.py` — The "Thinking" Brain
Manages the strict **2-stage agentic loop**:
*   **Stage 1 (Think)**: Analyzes the user query to decide if search is required and generates an optimized search query.
*   **Stage 2 (Synthesize)**: After scraping content, it compiles a natural language response.
*   **Mechanism**: Uses tool-calling (function calling) to interface with the web search engine.

### 4. `search_engine.py` — The Stealth Searcher
Directly scrapes `html.duckduckgo.com` and unwraps redirects to find primary source URLs without requiring an API key.

### 5. `scraper.py` — The Content Extractor
Uses **BeautifulSoup4** with aggressive noise-reduction heuristics:
*   Strips `<script>`, `<style>`, `<nav>`, and `<footer>` tags.
*   Decomposes common ad and sidebar CSS classes.
*   Prioritizes `<main>` and `<article>` blocks to ensure high signal-to-noise ratio.

### 6. `index.html` — The Workbench
An editorial-style UI designed for readability and focus.
*   **Tech Stack**: Vanilla JS, CSS3, IBM Plex Sans typography.
*   **Features**: Markdown rendering with **Marked.js**, syntax highlighting with **Highlight.js**, and a terminal-style loading state.

---

## 🔃 Tiered Reliability Workflow
1.  **Thinking Phase**: LLM decides if search is needed.
2.  **Batch Scraping**:
    *   **Attempt 1**: Scrape top 3 links concurrently.
    *   **Attempt 2**: If Batch 1 is empty, scrape links 4-6.
3.  **Snippet Fallback**: If full scraping fails, the system uses DuckDuckGo's result snippets as a secondary context source.
4.  **Synthesis**: LLM generates the final answer based on the best available context.

## 🚀 Vision
Proof of concept that high-quality AI search assistants can be built using smart engineering rather than expensive enterprise APIs.
