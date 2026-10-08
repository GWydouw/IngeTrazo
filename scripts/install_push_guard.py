#!/usr/bin/env python3
"""Install the standalone product guard in the common Git hooks directory."""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def main():
    custom = subprocess.run(["git", "config", "--get", "core.hooksPath"],
                            cwd=ROOT, text=True, capture_output=True)
    if custom.returncode == 0:
        raise SystemExit("Custom core.hooksPath detected; integrate the guard with that hook manager.")
    common = subprocess.check_output(["git", "rev-parse", "--git-common-dir"],
                                     cwd=ROOT, text=True).strip()
    hook = (ROOT / common).resolve() / "hooks" / "pre-push"
    if hook.exists() and "INGETRAZO_PRODUCT_PUSH_GUARD" not in hook.read_text():
        raise SystemExit(f"Existing hook preserved: {hook}. Integrate the guard manually.")
    hook.parent.mkdir(parents=True, exist_ok=True)
    hook.write_text((ROOT / "scripts" / "pre_push_guard.py").read_text())
    hook.chmod(0o755)
    print(f"Installed shared worktree push guard: {hook}")


if __name__ == "__main__":
    main()
