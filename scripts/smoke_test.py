"""Verify health, release identity, and behavior through a forwarded Service."""

import argparse
import json
import time
import urllib.error
import urllib.request


def get_json(url, body=None):
    data = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(request, timeout=5) as response:
        return json.load(response)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:18080")
    parser.add_argument("--version", required=True)
    args = parser.parse_args()
    last_error = None
    for _ in range(30):
        try:
            assert get_json(args.url + "/health") == {"status": "ok"}
            body = get_json(args.url + "/")
            assert body["version"] == args.version, body
            assert body["message"] == "Hello from Kaizen!", body
            assert get_json(args.url + "/api/add", {"a": 2, "b": 3}) == {"result": 5}
            print(f"PASS: health, version {args.version}, greeting, and addition")
            return
        except (AssertionError, OSError, ValueError) as error:
            last_error = error
            time.sleep(2)
    raise SystemExit(f"Smoke test failed: {last_error}")


if __name__ == "__main__":
    main()
