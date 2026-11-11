"""Enforce an example classroom policy on pip-licenses JSON output."""

import json
import sys

# Exact values only: unknown and compound expressions require explicit review.
# This is an example organizational policy, not a legal classification.
ALLOWED = {
    "MIT",
    "MIT License",
    "BSD-3-Clause",
    "BSD-2-Clause",
    "BSD License",
    "Apache-2.0",
    "Apache Software License",
    "ISC",
    "ISC License (ISCL)",
}


def violations(packages):
    return [p for p in packages if p.get("License", "UNKNOWN") not in ALLOWED]


def main():
    with open(sys.argv[1], encoding="utf-8") as report:
        packages = json.load(report)
    failed = violations(packages)
    for package in packages:
        print(f"{package['Name']} {package['Version']}: {package.get('License', 'UNKNOWN')}")
    if failed:
        print("FAIL: a runtime dependency has an unapproved or unknown license.")
        return 1
    print("PASS: runtime dependency licenses match the classroom policy.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
