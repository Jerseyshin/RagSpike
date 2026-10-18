#!/usr/bin/env python3
"""Download approved public corpus sources and record file-level evidence.

The downloader never mutates the document manifest. It writes one raw artifact per
official URL and a JSONL result log that can later be reconciled into the manifest.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import re
import subprocess
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


USER_AGENT = "RagSpike-CorpusCollector/1.0 (+public compliance research)"
SAFE_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", default="data/manifests/documents.jsonl")
    parser.add_argument("--output-dir", default="data/raw")
    parser.add_argument("--results", default="data/downloads/download-results.jsonl")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--timeout", type=int, default=45)
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument("--priority", choices=("P0", "P1", "P2"))
    parser.add_argument("--limit", type=int)
    parser.add_argument("--force", action="store_true")
    parser.add_argument(
        "--allow-insecure-fallback",
        action="store_true",
        help="Retry curl certificate failures with --insecure and record tls_verified=false.",
    )
    return parser.parse_args()


def read_manifest(path: Path, priority: str | None, limit: int | None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            row = json.loads(line)
            document_id = row.get("document_id", "")
            if not SAFE_ID.fullmatch(document_id):
                raise ValueError(f"invalid document_id at line {line_number}: {document_id!r}")
            if row.get("review_status") != "approved":
                continue
            if priority and row.get("priority") != priority:
                continue
            rows.append(row)
    return rows[:limit] if limit is not None else rows


def detect_extension(data_prefix: bytes, content_type: str, url: str) -> str:
    content_type = content_type.lower().split(";", 1)[0].strip()
    if data_prefix.startswith(b"%PDF") or content_type == "application/pdf":
        return ".pdf"
    if data_prefix.startswith(b"PK\x03\x04"):
        if url.lower().endswith(".docx"):
            return ".docx"
        if url.lower().endswith(".xlsx"):
            return ".xlsx"
        return ".zip"
    if content_type in {"text/html", "application/xhtml+xml"} or b"<html" in data_prefix.lower():
        return ".html"
    if content_type in {"application/json", "text/json"}:
        return ".json"
    if content_type.startswith("text/"):
        return ".txt"
    suffix = Path(urllib.request.url2pathname(urllib.parse.urlparse(url).path)).suffix.lower()
    return suffix if suffix in {".pdf", ".doc", ".docx", ".zip", ".html", ".htm"} else ".bin"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def existing_artifact(document_dir: Path, index: int) -> Path | None:
    matches = sorted(document_dir.glob(f"source-{index:02d}.*"))
    matches = [path for path in matches if not path.name.endswith(".part")]
    return matches[0] if matches else None


def download_one(task: tuple[dict[str, Any], int, str], args: argparse.Namespace) -> dict[str, Any]:
    row, index, url = task
    document_id = row["document_id"]
    document_dir = Path(args.output_dir) / document_id
    document_dir.mkdir(parents=True, exist_ok=True)
    retrieved_at = datetime.now(timezone.utc).isoformat()

    previous = existing_artifact(document_dir, index)
    if previous and not args.force:
        return {
            "document_id": document_id,
            "priority": row["priority"],
            "source_index": index,
            "source_url": url,
            "status": "existing",
            "http_status": None,
            "final_url": None,
            "content_type": None,
            "artifact_path": str(previous),
            "size_bytes": previous.stat().st_size,
            "sha256": sha256_file(previous),
            "retrieved_at": retrieved_at,
            "tls_verified": None,
            "error": None,
        }

    last_error: str | None = None
    for attempt in range(1, args.retries + 2):
        temporary = document_dir / f"source-{index:02d}.part"
        try:
            network_url = urllib.parse.quote(url, safe=":/?&=%+#")
            command = [
                    "curl",
                    "--location",
                    "--fail",
                    "--silent",
                    "--show-error",
                    "--connect-timeout",
                    str(min(args.timeout, 15)),
                    "--max-time",
                    str(args.timeout),
                    "--user-agent",
                    USER_AGENT,
                    "--header",
                    "Accept-Encoding: identity",
                    "--output",
                    str(temporary),
                    "--write-out",
                    "%{http_code}\\t%{url_effective}\\t%{content_type}",
                    network_url,
                ]
            completed = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
                timeout=args.timeout + 10,
            )
            tls_verified = True
            if completed.returncode == 60 and args.allow_insecure_fallback:
                completed = subprocess.run(
                    command[:1] + ["--insecure"] + command[1:],
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=args.timeout + 10,
                )
                tls_verified = False
            if completed.returncode != 0:
                raise subprocess.CalledProcessError(
                    completed.returncode,
                    command,
                    output=completed.stdout,
                    stderr=completed.stderr,
                )
            http_status_text, final_url, content_type = completed.stdout.split("\t", 2)
            http_status = int(http_status_text)
            with temporary.open("rb") as handle:
                data_prefix = handle.read(4096)
            extension = detect_extension(data_prefix, content_type, final_url)
            artifact = document_dir / f"source-{index:02d}{extension}"
            os.replace(temporary, artifact)
            return {
                "document_id": document_id,
                "priority": row["priority"],
                "source_index": index,
                "source_url": url,
                "status": "downloaded",
                "http_status": http_status,
                "final_url": final_url,
                "content_type": content_type,
                "artifact_path": str(artifact),
                "size_bytes": artifact.stat().st_size,
                "sha256": sha256_file(artifact),
                "retrieved_at": retrieved_at,
                "tls_verified": tls_verified,
                "error": None,
            }
        except (subprocess.SubprocessError, ValueError, OSError) as exc:
            temporary.unlink(missing_ok=True)
            if isinstance(exc, subprocess.CalledProcessError):
                detail = (exc.stderr or "").strip()
                last_error = f"curl exit {exc.returncode}: {detail}"
            else:
                last_error = f"{type(exc).__name__}: {exc}"
            if attempt <= args.retries:
                time.sleep(min(2**attempt, 8))

    return {
        "document_id": document_id,
        "priority": row["priority"],
        "source_index": index,
        "source_url": url,
        "status": "failed",
        "http_status": None,
        "final_url": None,
        "content_type": None,
        "artifact_path": None,
        "size_bytes": 0,
        "sha256": None,
        "retrieved_at": retrieved_at,
        "tls_verified": None,
        "error": last_error,
    }


def main() -> int:
    args = parse_args()
    rows = read_manifest(Path(args.manifest), args.priority, args.limit)
    tasks = [
        (row, index, url)
        for row in rows
        for index, url in enumerate(row["official_urls"], 1)
    ]
    results: list[dict[str, Any]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = [executor.submit(download_one, task, args) for task in tasks]
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            results.append(result)
            print(
                f"{result['status']:10} {result['document_id']} "
                f"source-{result['source_index']:02d} {result['size_bytes']} bytes",
                flush=True,
            )

    results.sort(key=lambda item: (item["document_id"], item["source_index"]))
    results_path = Path(args.results)
    results_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = results_path.with_suffix(results_path.suffix + ".part")
    with temporary.open("w", encoding="utf-8") as handle:
        for result in results:
            handle.write(json.dumps(result, ensure_ascii=False, sort_keys=True) + "\n")
    os.replace(temporary, results_path)

    failed = sum(result["status"] == "failed" for result in results)
    print(f"completed: {len(results)} sources, {failed} failed", flush=True)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
