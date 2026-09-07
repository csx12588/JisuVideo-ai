"""Recompute the v0.1 production-package fingerprints without third-party deps."""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path


MANIFEST_NAME = "source-manifest.md"
DECLARED_FINGERPRINT = re.compile(
    rb"^package_fingerprint:\s*[\"']?(sha256:[0-9a-f]{64})[\"']?\s*$",
    re.MULTILINE,
)


def normalize_file(path: Path) -> bytes:
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        raise ValueError(f"UTF-8 BOM is not allowed: {path}")
    try:
        raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"file is not valid UTF-8: {path}") from exc
    normalized = raw.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return normalized.rstrip(b"\n") + b"\n"


def fingerprint(rows: list[tuple[str, str]]) -> str:
    payload = b"".join(
        path.encode("utf-8") + b"\0" + digest.encode("ascii") + b"\n"
        for path, digest in rows
    )
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--package-root",
        type=Path,
        default=Path(__file__).parent / "production-package-v0.1",
    )
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    root = args.package_root.resolve()
    if not root.is_dir():
        print(f"package root does not exist: {root}", file=sys.stderr)
        return 2

    rows: list[tuple[str, str]] = []
    sizes: dict[str, int] = {}
    try:
        for path in sorted(p for p in root.rglob("*") if p.is_file()):
            relative = path.relative_to(root).as_posix()
            normalized = normalize_file(path)
            digest = hashlib.sha256(normalized).hexdigest()
            rows.append((relative, digest))
            sizes[relative] = len(normalized)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    package_rows = [(path, digest) for path, digest in rows if path != MANIFEST_NAME]
    package_fp = fingerprint(package_rows)
    validation_fp = fingerprint(rows)
    manifest = (root / MANIFEST_NAME).read_bytes()
    match = DECLARED_FINGERPRINT.search(manifest)
    declared = match.group(1).decode("ascii") if match else "<missing or invalid>"

    print(f"package_fingerprint: {package_fp}")
    print(f"validation_fingerprint: {validation_fp}")
    print(f"manifest_declared_package_fingerprint: {declared}")
    for path, digest in rows:
        print(f"{path}\t{digest}\t{sizes[path]} bytes")

    if args.check and declared != package_fp:
        print("ERROR: manifest package_fingerprint does not match", file=sys.stderr)
        return 1
    if args.check:
        print("OK: package fingerprints are reproducible")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
