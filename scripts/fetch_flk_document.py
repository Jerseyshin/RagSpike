#!/usr/bin/env python3
"""Fetch a current consolidated PDF from the National Laws Database API."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


def run_curl(url: str, output: Path) -> None:
    completed = subprocess.run(
        ["curl", "--location", "--fail", "--silent", "--show-error", "--max-time", "60", "--output", str(output), url],
        check=False,
        capture_output=True,
        text=True,
        timeout=70,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"curl exit {completed.returncode}: {completed.stderr.strip()}")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("document_id")
    parser.add_argument("bbbs")
    parser.add_argument("--output-dir", default="data/raw-flk")
    parser.add_argument("--results", default="data/downloads/flk-download-results.jsonl")
    args = parser.parse_args()

    api_url = (
        "https://flk.npc.gov.cn/law-search/download/pc"
        f"?format=pdf&bbbs={args.bbbs}&fileId="
    )
    document_dir = Path(args.output_dir) / args.document_id
    document_dir.mkdir(parents=True, exist_ok=True)
    metadata_path = document_dir / "download-link.json"
    run_curl(api_url, metadata_path)
    response = json.loads(metadata_path.read_text(encoding="utf-8"))
    signed_url = response["data"]["url"]
    artifact = document_dir / "consolidated.pdf"
    run_curl(signed_url, artifact)
    if artifact.read_bytes()[:5] != b"%PDF-":
        raise RuntimeError("downloaded artifact is not a PDF")

    result = {
        "document_id": args.document_id,
        "bbbs": args.bbbs,
        "source_url": api_url,
        "artifact_path": str(artifact),
        "size_bytes": artifact.stat().st_size,
        "sha256": sha256(artifact),
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "status": "downloaded",
        "source_note": "National Laws Database current consolidated PDF; signed object URL omitted because it expires.",
    }
    results_path = Path(args.results)
    results_path.parent.mkdir(parents=True, exist_ok=True)
    existing = []
    if results_path.exists():
        existing = [json.loads(line) for line in results_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    existing = [row for row in existing if row.get("document_id") != args.document_id]
    existing.append(result)
    results_path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in existing),
        encoding="utf-8",
    )
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
