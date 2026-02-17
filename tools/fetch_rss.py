"""
tools/fetch_rss.py — CLI tool for the digest agent.

Usage:
    python tools/fetch_rss.py <url> [--limit N]

Output: JSON array to stdout. Each item: {title, link, summary, published}
Exit 0 on success, 1 on failure (error message in stderr).
"""

import sys
import json
import argparse
import datetime
import feedparser
from bs4 import BeautifulSoup


def fetch_rss(url: str, limit: int = 10) -> list[dict]:
    feed = feedparser.parse(url)
    if feed.bozo and not feed.entries:
        raise ValueError(f"Failed to parse feed: {feed.bozo_exception}")

    items = []
    for entry in feed.entries[:limit]:
        summary_raw = entry.get("summary", entry.get("description", ""))
        summary_text = BeautifulSoup(summary_raw, "html.parser").get_text()[:400]

        published = ""
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            try:
                published = datetime.datetime(*entry.published_parsed[:6]).isoformat()
            except Exception:
                published = entry.get("published", "")

        items.append({
            "title":     entry.get("title", "").strip(),
            "link":      entry.get("link", ""),
            "summary":   summary_text.strip(),
            "published": published,
            "source":    feed.feed.get("title", url),
        })

    return items


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch RSS feed and output JSON")
    parser.add_argument("url", help="RSS/Atom feed URL")
    parser.add_argument("--limit", type=int, default=10, help="Max items to return")
    args = parser.parse_args()

    try:
        items = fetch_rss(args.url, args.limit)
        print(json.dumps(items, ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
