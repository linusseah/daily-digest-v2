"""
tools/search_web.py — CLI tool for the digest agent.

Uses Exa Search API (https://exa.ai) — neural search, great for news/content.
Falls back to Brave Search API if EXA_API_KEY not set but BRAVE_SEARCH_API_KEY is.
Without any key, returns empty results (exit 0) so the agent can skip gracefully.

Usage:
    python tools/search_web.py "<query>" [--limit N]

Env vars (at least one recommended): EXA_API_KEY, BRAVE_SEARCH_API_KEY

Output: JSON array to stdout. Each item: {title, url, description}
Exit 0 on success or when search is unavailable, 1 on unexpected failure.
"""

import sys
import os
import json
import argparse
import requests


def search_exa(query: str, limit: int = 5) -> list[dict]:
    api_key = os.environ["EXA_API_KEY"]
    resp = requests.post(
        "https://api.exa.ai/search",
        headers={
            "x-api-key": api_key,
            "Content-Type": "application/json",
        },
        json={
            "query": query,
            "numResults": limit,
            "useAutoprompt": True,
            "type": "neural",
            "contents": {"summary": {"query": query}},
        },
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()

    results = []
    for item in data.get("results", [])[:limit]:
        results.append({
            "title":       item.get("title", ""),
            "url":         item.get("url", ""),
            "description": item.get("snippet", item.get("summary", "")),
        })
    return results


def search_brave(query: str, limit: int = 5) -> list[dict]:
    api_key = os.environ["BRAVE_SEARCH_API_KEY"]
    resp = requests.get(
        "https://api.search.brave.com/res/v1/web/search",
        headers={
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": api_key,
        },
        params={"q": query, "count": limit},
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()

    results = []
    for item in data.get("web", {}).get("results", [])[:limit]:
        results.append({
            "title":       item.get("title", ""),
            "url":         item.get("url", ""),
            "description": item.get("description", ""),
        })
    return results


def search_web(query: str, limit: int = 5) -> list[dict]:
    if os.environ.get("EXA_API_KEY"):
        return search_exa(query, limit)
    if os.environ.get("BRAVE_SEARCH_API_KEY"):
        return search_brave(query, limit)
    # No API key available — return empty rather than attempting unreliable scraping
    print("WARNING: No search API key set (EXA_API_KEY or BRAVE_SEARCH_API_KEY); web search unavailable.", file=sys.stderr)
    return []


def main() -> None:
    parser = argparse.ArgumentParser(description="Web search and output JSON")
    parser.add_argument("query", help="Search query")
    parser.add_argument("--limit", type=int, default=5, help="Max results")
    args = parser.parse_args()

    try:
        results = search_web(args.query, args.limit)
        print(json.dumps(results, ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
