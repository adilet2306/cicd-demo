"""Render the two controlled placeholders without modifying source manifests."""

import argparse
import re
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True)
    parser.add_argument("--version", required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z0-9][a-z0-9./_-]*@sha256:[a-f0-9]{64}", args.image):
        parser.error("image must be a lowercase registry/repository@sha256:digest reference")
    if not re.fullmatch(r"[a-f0-9]{40}", args.version):
        parser.error("version must be a full Git commit SHA")
    source = Path("k8s/app.yaml").read_text()
    print(source.replace("IMAGE_PLACEHOLDER", args.image).replace("VERSION_PLACEHOLDER", args.version))


if __name__ == "__main__":
    main()
