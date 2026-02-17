"""
tools/send_email.py — CLI tool for the digest agent.

Usage:
    python tools/send_email.py <html_file> "<subject>"
    python tools/send_email.py <html_file> "<subject>" --dry-run

Env vars required: RESEND_API_KEY, DIGEST_TO (or GMAIL_ADDRESS as fallback)

Output: JSON {success: bool, message: str} to stdout.
Exit 0 on success, 1 on failure.
"""

import sys
import os
import json
import argparse
import requests


def send_email(html_body: str, subject: str, dry_run: bool = False) -> dict:
    resend_key = os.environ["RESEND_API_KEY"]
    to_address = os.environ.get("DIGEST_TO") or os.environ["GMAIL_ADDRESS"]

    if dry_run:
        return {"success": True, "message": f"[DRY RUN] Would send to {to_address}: {subject}"}

    resp = requests.post(
        "https://api.resend.com/emails",
        headers={
            "Authorization": f"Bearer {resend_key}",
            "Content-Type": "application/json",
        },
        json={
            "from":    "Daily Digest <onboarding@resend.dev>",
            "to":      [to_address],
            "subject": subject,
            "html":    html_body,
        },
        timeout=15,
    )
    resp.raise_for_status()
    return {"success": True, "message": f"Email sent to {to_address} — status {resp.status_code}"}


def main() -> None:
    parser = argparse.ArgumentParser(description="Send digest email via Resend")
    parser.add_argument("html_file", help="Path to HTML file to send")
    parser.add_argument("subject",   help="Email subject line")
    parser.add_argument("--dry-run", action="store_true", help="Skip actual send")
    args = parser.parse_args()

    try:
        with open(args.html_file) as f:
            html_body = f.read()

        result = send_email(html_body, args.subject, dry_run=args.dry_run)
        print(json.dumps(result))
    except Exception as e:
        print(json.dumps({"success": False, "message": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
