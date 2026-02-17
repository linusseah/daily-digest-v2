"""
tools/write_log.py — CLI tool for the digest agent.

Usage:
    python tools/write_log.py '<json_string>'

Writes a structured log file to logs/YYYY-MM-DD.json.
Creates the logs/ directory if it doesn't exist.

Output: JSON {success: bool, path: str} to stdout.
"""

import sys
import os
import json
import datetime
import argparse
from pathlib import Path


def write_log(log_data: dict) -> str:
    logs_dir = Path(__file__).parent.parent / "logs"
    logs_dir.mkdir(exist_ok=True)

    date_str = datetime.date.today().isoformat()
    log_path = logs_dir / f"{date_str}.json"

    # Add timestamp if not present
    if "timestamp" not in log_data:
        log_data["timestamp"] = datetime.datetime.utcnow().isoformat() + "Z"

    with open(log_path, "w") as f:
        json.dump(log_data, f, indent=2, ensure_ascii=False)

    return str(log_path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Write run log to logs/YYYY-MM-DD.json")
    parser.add_argument("json_string", help="JSON string to write as log")
    args = parser.parse_args()

    try:
        log_data = json.loads(args.json_string)
        path = write_log(log_data)
        print(json.dumps({"success": True, "path": path}))
    except Exception as e:
        print(json.dumps({"success": False, "error": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
