#!/usr/bin/env python3
"""Build the isolated P0 ingestion payload and the remaining normalization queue."""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
P0_DIR = ROOT / "data/processed/p0"
MANIFEST_SOURCE = ROOT / "data/manifests/documents.jsonl"
AUDIT_SOURCE = ROOT / "data/downloads/download-audit.jsonl"
INGEST_DIR = ROOT / "data/ingest/p0"
BACKLOG_PATH = ROOT / "data/normalization/backlog.jsonl"
CORPUS_ID = "cn-privacy-p0-v0.1"


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def jsonl_bytes(rows: list[dict]) -> bytes:
    return "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def build_ingest_records() -> tuple[list[dict], list[dict], list[dict]]:
    index = load_jsonl(P0_DIR / "index.jsonl")
    chunks = load_jsonl(P0_DIR / "chunks.jsonl")
    catalog = {row["document_id"]: row for row in load_jsonl(MANIFEST_SOURCE)}
    p0_ids = {row["document_id"] for row in index}

    if {row["document_id"] for row in chunks} != p0_ids:
        raise ValueError("P0 index and chunk document IDs differ")

    documents = []
    for item in index:
        document_id = item["document_id"]
        metadata = catalog[document_id]
        markdown_path = ROOT / item["output_path"]
        documents.append(
            {
                "corpus_id": CORPUS_ID,
                "document_id": document_id,
                "title": metadata["title"],
                "content": markdown_path.read_text(encoding="utf-8"),
                "metadata": {
                    "document_type": metadata["document_type"],
                    "priority": metadata["priority"],
                    "publication_date": metadata["publication_date"],
                    "effective_date": metadata["effective_date"],
                    "validity_status": metadata["validity_status"],
                    "legal_effect": metadata["legal_effect"],
                    "version_label": metadata["version_label"],
                    "scope_mode": metadata["scope_mode"],
                    "topics": metadata["topics"],
                    "official_urls": metadata["official_urls"],
                    "normalized_path": item["output_path"],
                    "normalized_sha256": sha256_file(markdown_path),
                    "source_artifacts": item["source_artifacts"],
                    "source_sha256": item["source_sha256"],
                },
            }
        )

    records = []
    for item in chunks:
        record = {
            "corpus_id": CORPUS_ID,
            "record_id": item["chunk_id"],
            "document_id": item["document_id"],
            "content": item["text"],
            "metadata": {
                "title": item["title"],
                "article": item.get("article"),
                "heading_path": item.get("heading_path", []),
                "section_label": item.get("section_label"),
                "effective_date": item.get("effective_date"),
                "validity_status": item.get("validity_status"),
                "source_artifact": item["source_artifact"],
                "source_sha256": item["source_sha256"],
                "source_url": item["source_url"],
            },
        }
        records.append(record)
    return index, documents, records


def build_backlog(p0_ids: set[str]) -> list[dict]:
    catalog = {row["document_id"]: row for row in load_jsonl(MANIFEST_SOURCE)}
    audited_by_doc: dict[str, list[dict]] = defaultdict(list)
    for row in load_jsonl(AUDIT_SOURCE):
        audited_by_doc[row["document_id"]].append(row)

    body_ids = {
        document_id
        for document_id, artifacts in audited_by_doc.items()
        if any(item["classification"] == "body_candidate" for item in artifacts)
    }
    backlog_ids = sorted(body_ids - p0_ids)
    rows = []
    for document_id in backlog_ids:
        metadata = catalog[document_id]
        candidates = []
        actions = set()
        for item in audited_by_doc[document_id]:
            if item["classification"] != "body_candidate":
                continue
            suffix = Path(item["artifact_path"]).suffix.lower()
            action = {
                ".pdf": "extract_pdf_text",
                ".docx": "extract_docx_body",
                ".doc": "convert_legacy_doc",
            }.get(suffix, "extract_html_body")
            actions.add(action)
            candidates.append(
                {
                    "artifact_path": item["artifact_path"],
                    "source_url": item["source_url"],
                    "visible_characters": item["visible_characters"],
                    "article_markers": item["article_markers"],
                    "sha256_verified": item["sha256_verified"],
                    "recommended_action": action,
                }
            )
        rows.append(
            {
                "document_id": document_id,
                "title": metadata["title"],
                "priority": metadata["priority"],
                "document_type": metadata["document_type"],
                "validity_status": metadata["validity_status"],
                "scope_mode": metadata["scope_mode"],
                "candidate_sources": candidates,
                "required_actions": sorted(actions | {"verify_body_boundary", "verify_version", "normalize_structure", "human_review"}),
                "status": "pending_normalization",
            }
        )
    if len(rows) != 39:
        raise ValueError(f"Expected 39 normalization backlog documents, got {len(rows)}")
    return rows


def main() -> None:
    index, documents, records = build_ingest_records()
    record_ids = [row["record_id"] for row in records]
    if len(record_ids) != len(set(record_ids)):
        raise ValueError("Duplicate ingestion record IDs")
    normalized_text = ["".join(row["content"].split()) for row in records]
    if len(normalized_text) != len(set(normalized_text)):
        raise ValueError("Duplicate ingestion chunk text")

    INGEST_DIR.mkdir(parents=True, exist_ok=True)
    documents_payload = jsonl_bytes(documents)
    records_payload = jsonl_bytes(records)
    (INGEST_DIR / "documents.jsonl").write_bytes(documents_payload)
    (INGEST_DIR / "records.jsonl").write_bytes(records_payload)

    document_ids = [row["document_id"] for row in index]
    package_manifest = {
        "schema_version": "1.0",
        "corpus_id": CORPUS_ID,
        "purpose": "LightRAG and vector-RAG P0 pipeline trial",
        "status": "ready_for_pipeline_trial",
        "document_count": len(documents),
        "record_count": len(records),
        "document_ids": document_ids,
        "documents_path": "data/ingest/p0/documents.jsonl",
        "documents_sha256": sha256_bytes(documents_payload),
        "records_path": "data/ingest/p0/records.jsonl",
        "records_sha256": sha256_bytes(records_payload),
        "canonical_trial_input": "data/ingest/p0/records.jsonl",
        "input_policy": "Use identical fixed records for LightRAG and vector-RAG comparison; documents.jsonl is retained for source reconstruction and API adaptation.",
        "explicitly_excluded": [
            "data/evaluation/",
            "data/downloads/",
            "data/raw/",
            "data/raw-attachments/",
            "11 restricted or broken-link documents without approved body text",
        ],
    }
    (INGEST_DIR / "manifest.json").write_text(
        json.dumps(package_manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    backlog = build_backlog(set(document_ids))
    BACKLOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    BACKLOG_PATH.write_bytes(jsonl_bytes(backlog))

    print(json.dumps({
        "corpus_id": CORPUS_ID,
        "documents": len(documents),
        "records": len(records),
        "normalization_backlog": len(backlog),
        "records_sha256": package_manifest["records_sha256"],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
