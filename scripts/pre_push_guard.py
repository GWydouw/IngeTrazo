#!/usr/bin/env python3
"""INGETRAZO_PRODUCT_PUSH_GUARD: prevent private history reaching public remotes."""
import re
import subprocess
import sys

PRIVATE_REPO = "github.com/gwydouw/siteref-ingetrazo"
OFFICIAL_REPO = "github.com/ingelibre/ingetrazo"
PRIVATE_PATHS = ("poc/siteref", "siteref", ".siteref-private",
                 ":(glob)products/siteref-*.json")


def repository(url):
    value = url.lower().rstrip("/")
    value = re.sub(r"^(https?://|ssh://)([^/@]+@)?", "", value)
    value = re.sub(r"^git@", "", value).replace("github.com:", "github.com/")
    return value.removesuffix(".git")


def check_push(destination, rows):
    target = repository(destination)
    for row in rows:
        local_ref, local_sha, remote_ref, _ = row.split()
        if not local_sha.strip("0"):
            continue  # A deletion publishes no new history.
        if target == OFFICIAL_REPO:
            return "Direct pushes to officiële iT are disabled; use a reviewed upstream PR."
        if target == PRIVATE_REPO:
            continue
        shallow = subprocess.run(["git", "rev-parse", "--is-shallow-repository"],
                                 capture_output=True, text=True)
        if shallow.returncode or shallow.stdout.strip() != "false":
            return "Full history is required before publishing to a non-private destination."
        if any("siteref" in ref.lower() for ref in (local_ref, remote_ref)):
            return "SiteRef branches and tags may only be pushed to siteref-private."
        commit = subprocess.run(["git", "rev-parse", "--verify", f"{local_sha}^{{commit}}"],
                                capture_output=True, text=True)
        if commit.returncode:
            return "Cannot inspect the pushed object; push refused."
        history = subprocess.run(["git", "rev-list", "-1", commit.stdout.strip(),
                                  "--", *PRIVATE_PATHS], capture_output=True, text=True)
        if history.returncode or history.stdout.strip():
            return ("Private SiteRef history detected. Push only to siteref-private; "
                    "cherry-pick reviewed general fixes onto a public base branch.")
    return None


def main():
    if len(sys.argv) != 3:
        print("Usage: pre_push_guard.py <remote-name> <remote-url>", file=sys.stderr)
        return 1
    try:
        error = check_push(sys.argv[2], sys.stdin)
    except (OSError, ValueError) as exc:
        error = f"Push inspection failed: {exc}"
    if error:
        print(f"Push blocked: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
