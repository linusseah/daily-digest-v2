"""
tools/fetch_imap.py — CLI tool for the digest agent.

Usage:
    python tools/fetch_imap.py --sender <email_or_keyword> --subject <keyword> [--limit N]

Env vars required: GMAIL_ADDRESS, GMAIL_APP_PASS

Output: JSON array to stdout. Each item: {subject, sender, date, body_snippet}
Exit 0 on success, 1 on failure (error message in stderr).
"""

import sys
import os
import json
import email
import email.message
import imaplib
import argparse
from bs4 import BeautifulSoup


def fetch_imap(sender_kw: str, subject_kw: str, limit: int = 3) -> list[dict]:
    gmail_address = os.environ["GMAIL_ADDRESS"]
    gmail_pass    = os.environ["GMAIL_APP_PASS"]

    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    mail.login(gmail_address, gmail_pass)
    mail.select("inbox")

    # Try sender first, then subject keyword
    results = []
    for criteria in [f'FROM "{sender_kw}"', f'SUBJECT "{subject_kw}"']:
        _, data = mail.search(None, criteria)
        ids = data[0].split()
        if ids:
            # Most recent N
            for msg_id in reversed(ids[-limit:]):
                _, msg_data = mail.fetch(msg_id, "(RFC822)")
                raw = msg_data[0][1]
                msg = email.message_from_bytes(raw)

                body = _extract_body(msg)
                results.append({
                    "subject": msg.get("Subject", ""),
                    "sender":  msg.get("From", ""),
                    "date":    msg.get("Date", ""),
                    "body_snippet": body[:3000],
                })
            break  # stop if sender search succeeded

    mail.logout()
    return results


def _extract_body(msg: email.message.Message) -> str:
    body = ""
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            if ct == "text/plain":
                body = part.get_payload(decode=True).decode("utf-8", errors="ignore")
                break
            elif ct == "text/html" and not body:
                html = part.get_payload(decode=True).decode("utf-8", errors="ignore")
                body = BeautifulSoup(html, "html.parser").get_text(separator="\n")
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            body = payload.decode("utf-8", errors="ignore")
    return body.strip()


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch email via IMAP and output JSON")
    parser.add_argument("--sender",  required=True, help="Sender email or keyword to search")
    parser.add_argument("--subject", required=True, help="Subject keyword to search")
    parser.add_argument("--limit",   type=int, default=3, help="Max emails to return")
    args = parser.parse_args()

    try:
        items = fetch_imap(args.sender, args.subject, args.limit)
        print(json.dumps(items, ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
