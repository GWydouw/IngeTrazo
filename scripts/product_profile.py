#!/usr/bin/env python3
"""Validate and report a product profile without importing Qt or private code."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def inspect_profile(root, product, require_ready=False):
    if product not in {"mijn-it", "siteref-for-it", "siteref-for-su"}:
        raise ValueError(f"Unknown product: {product}")
    data = json.loads((root / "products" / f"{product}.json").read_text())
    if data["id"] != product:
        raise ValueError("Profile ID does not match its filename")
    private = product.startswith("siteref-")
    if data["visibility"] != ("private" if private else "public"):
        raise ValueError("Incorrect product visibility")
    if private and not (root / ".siteref-private").is_file():
        raise ValueError("Private profile requires the private repository marker")
    if not private and (root / ".siteref-private").exists():
        raise ValueError("Inspect/build mijn iT from a public checkout, not private product history")
    for key in ("source_ready", "packaging_ready"):
        if not isinstance(data[key], bool):
            raise ValueError(f"{key} must be boolean")
    for key, readiness in (("entrypoint", "source_ready"), ("packaging", "packaging_ready")):
        value = data[key]
        if value is not None:
            path = (root / value).resolve()
            if not path.is_relative_to(root.resolve()):
                raise ValueError(f"{key} must stay inside the checkout")
            if data[readiness] and not path.is_file():
                raise ValueError(f"Missing {key}: {value}")
        elif data[readiness]:
            raise ValueError(f"Ready product requires {key}")
    if require_ready and not (data["source_ready"] and data["packaging_ready"]):
        raise ValueError(f"{data['name']} is not ready for a packaged build: {data['notes']}")
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("product", choices=("mijn-it", "siteref-for-it", "siteref-for-su"))
    parser.add_argument("--require-ready", action="store_true")
    args = parser.parse_args()
    try:
        data = inspect_profile(ROOT, args.product, args.require_ready)
        data["source_commit"] = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        data["dirty"] = bool(subprocess.check_output(
            ["git", "status", "--porcelain"], cwd=ROOT, text=True).strip())
    except (ValueError, KeyError, OSError, subprocess.CalledProcessError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(json.dumps(data, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
