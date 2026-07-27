#!/usr/bin/env python3
"""Validate local href/src references in the static site."""

from __future__ import annotations

import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
IGNORED_SCHEMES = {"http", "https", "mailto", "tel", "data", "javascript"}


class ReferenceParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.references: list[tuple[str, int]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for name, value in attrs:
            if name in {"href", "src"} and value is not None:
                self.references.append((value.strip(), self.getpos()[0]))


def resolve_local_reference(source: Path, reference: str) -> Path | None:
    if not reference or reference.startswith("#"):
        return None

    parsed = urlsplit(reference)
    if parsed.scheme.lower() in IGNORED_SCHEMES or parsed.netloc:
        return None

    path = unquote(parsed.path)
    if not path:
        return None

    candidate = ROOT / path.lstrip("/") if path.startswith("/") else source.parent / path
    candidate = candidate.resolve()

    try:
        candidate.relative_to(ROOT.resolve())
    except ValueError:
        return candidate

    if path.endswith("/") or candidate.is_dir():
        return candidate / "index.html"
    return candidate


def main() -> int:
    errors: list[str] = []
    html_files = sorted(ROOT.rglob("*.html"))

    for source in html_files:
        parser = ReferenceParser()
        parser.feed(source.read_text(encoding="utf-8"))

        for reference, line in parser.references:
            target = resolve_local_reference(source, reference)
            if target is None:
                continue
            if not target.exists():
                errors.append(
                    f"{source.relative_to(ROOT)}:{line}: broken local reference "
                    f"{reference!r} -> {target.relative_to(ROOT) if target.is_relative_to(ROOT) else target}"
                )

    if errors:
        print("Local link validation failed:")
        print("\n".join(f"- {error}" for error in errors))
        return 1

    print(f"Validated {len(html_files)} HTML files: no broken local href/src references.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
