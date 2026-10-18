#!/usr/bin/env python3
"""Validate corpus integrity, provenance, scope, and evaluation-data isolation."""

from __future__ import annotations

import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "data/ingest/p0/manifest.json"
SOURCE_INDEX = ROOT / "data/processed/p0/index.jsonl"
SOURCE_CHUNKS = ROOT / "data/processed/p0/chunks.jsonl"
AUDIT = ROOT / "data/downloads/download-audit.jsonl"
BACKLOG = ROOT / "data/normalization/backlog.jsonl"
FORBIDDEN_FIELDS = {"question", "gold_answer", "required_claims", "forbidden_claims", "expected_behavior"}


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    errors: list[str] = []
    package = json.loads(PACKAGE.read_text(encoding="utf-8"))
    documents_path = ROOT / package["documents_path"]
    records_path = ROOT / package["records_path"]
    documents = load_jsonl(documents_path)
    records = load_jsonl(records_path)
    index = load_jsonl(SOURCE_INDEX)
    source_chunks = load_jsonl(SOURCE_CHUNKS)
    backlog = load_jsonl(BACKLOG)
    p0_ids = {row["document_id"] for row in index}

    if package["corpus_id"] != "cn-privacy-p0-v0.1":
        errors.append("unexpected corpus_id")
    if package["document_count"] != len(documents) or len(documents) != 11:
        errors.append("document count mismatch")
    if package["record_count"] != len(records) or len(records) != 571:
        errors.append("record count mismatch")
    if package["documents_sha256"] != sha256_file(documents_path):
        errors.append("documents.jsonl hash mismatch")
    if package["records_sha256"] != sha256_file(records_path):
        errors.append("records.jsonl hash mismatch")
    if set(package["document_ids"]) != p0_ids:
        errors.append("package document allowlist differs from P0 index")
    if {row["document_id"] for row in documents} != p0_ids:
        errors.append("document payload contains IDs outside the P0 allowlist")
    if {row["document_id"] for row in records} != p0_ids:
        errors.append("record payload contains IDs outside the P0 allowlist")

    record_ids = [row["record_id"] for row in records]
    if len(record_ids) != len(set(record_ids)):
        errors.append("duplicate record IDs")
    texts = ["".join(row["content"].split()) for row in records]
    if len(texts) != len(set(texts)):
        errors.append("duplicate normalized record text")

    source_by_id = {row["chunk_id"]: row for row in source_chunks}
    for row in records:
        if FORBIDDEN_FIELDS & row.keys() or FORBIDDEN_FIELDS & row.get("metadata", {}).keys():
            errors.append(f"{row.get('record_id')}: evaluation field leaked into ingestion record")
        source = source_by_id.get(row["record_id"])
        if source is None:
            errors.append(f"{row['record_id']}: no approved source chunk")
            continue
        if row["content"] != source["text"] or row["document_id"] != source["document_id"]:
            errors.append(f"{row['record_id']}: content differs from approved source chunk")
        metadata = row["metadata"]
        if metadata["source_artifact"] != source["source_artifact"]:
            errors.append(f"{row['record_id']}: source artifact mismatch")
        artifact = ROOT / metadata["source_artifact"]
        if not artifact.is_file() or sha256_file(artifact) != metadata["source_sha256"]:
            errors.append(f"{row['record_id']}: source file missing or hash mismatch")

    audit_by_doc: dict[str, list[dict]] = defaultdict(list)
    for row in load_jsonl(AUDIT):
        audit_by_doc[row["document_id"]].append(row)
    body_ids = {
        document_id
        for document_id, artifacts in audit_by_doc.items()
        if any(item["classification"] == "body_candidate" for item in artifacts)
    }
    backlog_ids = {row["document_id"] for row in backlog}
    if len(backlog) != 39 or len(backlog_ids) != 39:
        errors.append("normalization backlog must contain 39 unique documents")
    if backlog_ids & p0_ids:
        errors.append("normalization backlog overlaps P0 payload")
    if backlog_ids | p0_ids != body_ids or len(body_ids) != 50:
        errors.append("P0 plus backlog does not equal the 50 body-candidate documents")
    deferred_ids = set(audit_by_doc) - body_ids
    if len(deferred_ids) != 11:
        errors.append("deferred set must contain 11 documents")
    if deferred_ids & ({row["document_id"] for row in records} | backlog_ids):
        errors.append("a deferred document entered the payload or backlog")

    if errors:
        print(f"FAILED: {len(errors)} ingestion validation error(s)", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print("PASS: ingestion package integrity and scope")
    print(f"corpus={package['corpus_id']}; documents={len(documents)}; records={len(records)}")
    print(f"normalization_backlog={len(backlog)}; deferred={len(deferred_ids)}")
    print("evaluation fields and non-allowlisted document IDs found in payload: 0")
    print(f"records_sha256={package['records_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
