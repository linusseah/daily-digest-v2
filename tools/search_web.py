"""
tools/search_web.py — CLI tool for the digest agent.

Uses Brave Search API (free tier: 2000 req/month).
Falls back to DuckDuckGo HTML scraping if BRAVE_SEARCH_API_KEY is not set.

Usage:
    python tools/search_web.py "<query>" [--limit N]

Env vars optional: BRAVE_SEARCH_API_KEY

Output: JSON array to stdout. Each item: {title, url, description}
Exit 0 on success, 1 on failure.
"""

import sys
import os
import json
import argparse
import requests
from bs4 import BeautifulSoup


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


def search_duckduckgo(query: str, limit: int = 5) -> list[dict]:
    """Fallback: scrape DuckDuckGo HTML (no API key needed, rate-limited)."""
    headers = {"User-Agent": "Mozilla/5.0 (compatible; DailyDigestBot/2.0)"}
    resp = requests.get(
        "https://html.duckduckgo.com/html/",
        params={"q": query},
        headers=headers,
        timeout=15,
    )
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")
    results = []
    for result in soup.select(".result")[:limit]:
        title_el = result.select_one(".result__title")
        link_el  = result.select_one(".result__url")
        snip_el  = result.select_one(".result__snippet")
        title = title_el.get_text(strip=True) if title_el else ""
        url   = link_el.get_text(strip=True)  if link_el  else ""
        desc  = snip_el.get_text(strip=True)  if snip_el  else ""
        if title:
            results.append({"title": title, "url": url, "description": desc})

    return results


def search_web(query: str, limit: int = 5) -> list[dict]:
    if os.environ.get("BRAVE_SEARCH_API_KEY"):
        return search_brave(query, limit)
    else:
        return search_duckduckgo(query, limit)


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
