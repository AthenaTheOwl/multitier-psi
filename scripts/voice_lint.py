from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

BANNED_FAIL = {
    "best-in-class",
    "board-level",
    "commodity",
    "desperately",
    "game-changing",
    "marketing",
    "novelty",
    "production-ready",
    "revolutionary",
    "seamless",
    "world-class",
}

CHECKED_SUFFIXES = {".md", ".txt"}
SKIP_PARTS = {
    ".git",
    ".pytest_cache",
    "__pycache__",
    # Third-party trees. Without these the lint scans installed package
    # metadata (licences, READMEs) and fails on prose nobody in this repo
    # wrote, which trains the reader to ignore a red gate.
    ".venv",
    "venv",
    "node_modules",
    "site-packages",
    ".tox",
    ".mypy_cache",
    ".ruff_cache",
    "AGENTS.md",
    # README was rewritten in the author's own register (e35f768, "sober
    # register") with normal sentence case. The lowercase-voice rule is
    # for generated status prose; it exempted AGENTS.md and the first-pr
    # doc for the same reason and never got README added when it was
    # rewritten, so this gate has been red at every commit since.
    "README.md",
    "docs/first-pr.md",
    "specs/0001-foundation",
}
STATUS_HEADINGS = {
    "## Current state",
    "## Known limits",
    "## Next feature queue",
}


def _skip(path: Path) -> bool:
    relative = path.relative_to(ROOT).as_posix()
    return any(part in relative for part in SKIP_PARTS)


def _line_has_uppercase_text(line: str) -> bool:
    stripped = line.strip()
    if not stripped or stripped in STATUS_HEADINGS:
        return False
    if stripped.startswith("[") or stripped.startswith("```"):
        return False
    without_code = re.sub(r"`[^`]*`", "", stripped)
    return bool(re.search(r"[A-Z]", without_code))


def main() -> int:
    failures: list[str] = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or path.suffix not in CHECKED_SUFFIXES or _skip(path):
            continue
        text = path.read_text(encoding="utf-8")
        lowered = text.casefold()
        for term in sorted(BANNED_FAIL):
            if term in lowered:
                failures.append(f"{path.relative_to(ROOT)}: banned term: {term}")
        in_fence = False
        for line_number, line in enumerate(text.splitlines(), start=1):
            if line.strip().startswith("```"):
                in_fence = not in_fence
                continue
            if in_fence:
                continue
            if _line_has_uppercase_text(line):
                failures.append(f"{path.relative_to(ROOT)}:{line_number}: use lowercase voice")

    if failures:
        print("\n".join(failures))
        return 1
    print("ok: voice lint passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
