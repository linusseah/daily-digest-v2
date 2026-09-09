"""
tools/send_email.py — CLI tool for the digest agent.

Usage:
    python tools/send_email.py <html_file> "<subject>"
    python tools/send_email.py <html_file> "<subject>" --dry-run

Env vars required: GMAIL_ADDRESS, GMAIL_APP_PASS
DIGEST_TO (optional, defaults to GMAIL_ADDRESS) — comma-separated for multiple recipients

Output: JSON {success: bool, message: str} to stdout.
Exit 0 on success, 1 on failure.
"""

import sys
import os
import json
import argparse
import smtplib
from email.mime.text import MIMEText


def send_email(html_body: str, subject: str, dry_run: bool = False) -> dict:
    gmail_address = os.environ["GMAIL_ADDRESS"]
    gmail_app_pass = os.environ["GMAIL_APP_PASS"]
    to_addresses = [a.strip() for a in (os.environ.get("DIGEST_TO") or gmail_address).split(",") if a.strip()]

    if dry_run:
        return {"success": True, "message": f"[DRY RUN] Would send to {', '.join(to_addresses)}: {subject}"}

    msg = MIMEText(html_body, "html")
    msg["Subject"] = subject
    msg["From"] = f"Daily Digest <{gmail_address}>"
    msg["To"] = ", ".join(to_addresses)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=15) as server:
        server.login(gmail_address, gmail_app_pass)
        server.sendmail(gmail_address, to_addresses, msg.as_string())

    return {"success": True, "message": f"Email sent to {', '.join(to_addresses)} via Gmail SMTP"}


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
