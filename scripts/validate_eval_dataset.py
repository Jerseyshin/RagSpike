#!/usr/bin/env python3
"""Dependency-free structural and provenance validation for evaluation JSONL."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from collections import Counter
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "data/evaluation/pilot-cases.jsonl"
CHUNKS = ROOT / "data/processed/p0/chunks.jsonl"

QUESTION_TYPES = {
    "single_document_fact",
    "exact_article",
    "condition_exception",
    "cross_document",
    "version_conflict",
    "knowledge_missing",
    "ambiguity_false_premise",
}
RISK_LEVELS = {"low", "medium", "high"}
BEHAVIORS = {"answer", "refuse", "clarify", "correct_premise"}
SPLITS = {"unassigned", "train", "development", "blind_test"}
REVIEW_STATUSES = {"draft", "approved", "rejected"}
REQUIRED_FIELDS = {
    "schema_version", "case_id", "question", "question_type", "risk_level",
    "answerable", "gold_answer", "required_claims", "forbidden_claims",
    "evidence", "reasoning_outline", "expected_behavior", "as_of_date",
    "tags", "split", "review_status", "review_note",
}
EVIDENCE_FIELDS = {
    "document_id", "title", "article", "source_artifact", "source_sha256",
    "source_url", "quote",
}


def normalize(text: str) -> str:
    return "".join(text.split())


def load_jsonl(path: Path) -> list[dict]:
    result = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_number}: invalid JSON: {exc}") from exc
        if not isinstance(value, dict):
            raise ValueError(f"{path}:{line_number}: each line must be an object")
        result.append(value)
    return result


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_case(item: dict, index: int, chunks: list[dict], errors: list[str]) -> None:
    label = item.get("case_id", f"line {index}")
    missing = REQUIRED_FIELDS - item.keys()
    extra = item.keys() - REQUIRED_FIELDS
    if missing:
        errors.append(f"{label}: missing fields {sorted(missing)}")
    if extra:
        errors.append(f"{label}: unexpected fields {sorted(extra)}")
    if missing:
        return

    if item["schema_version"] != "1.0":
        errors.append(f"{label}: schema_version must be 1.0")
    if not re.fullmatch(r"CN-PRIV-[0-9]{4}", item["case_id"]):
        errors.append(f"{label}: invalid case_id")
    if not isinstance(item["question"], str) or len(item["question"].strip()) < 5:
        errors.append(f"{label}: question is too short")
    if item["question_type"] not in QUESTION_TYPES:
        errors.append(f"{label}: invalid question_type")
    if item["risk_level"] not in RISK_LEVELS:
        errors.append(f"{label}: invalid risk_level")
    if not isinstance(item["answerable"], bool):
        errors.append(f"{label}: answerable must be boolean")
    if not isinstance(item["gold_answer"], str) or not item["gold_answer"].strip():
        errors.append(f"{label}: empty gold_answer")
    for field in ("required_claims", "forbidden_claims", "reasoning_outline", "tags", "evidence"):
        if not isinstance(item[field], list):
            errors.append(f"{label}: {field} must be a list")
    if not item["required_claims"] or not all(isinstance(x, str) and x.strip() for x in item["required_claims"]):
        errors.append(f"{label}: required_claims must contain non-empty strings")
    if not item["reasoning_outline"] or not all(isinstance(x, str) and x.strip() for x in item["reasoning_outline"]):
        errors.append(f"{label}: reasoning_outline must contain non-empty strings")
    if not item["tags"] or len(item["tags"]) != len(set(item["tags"])):
        errors.append(f"{label}: tags must be non-empty and unique")
    elif not all(re.fullmatch(r"[a-z0-9_]+", tag) for tag in item["tags"]):
        errors.append(f"{label}: invalid tag")
    if item["expected_behavior"] not in BEHAVIORS:
        errors.append(f"{label}: invalid expected_behavior")
    if item["split"] not in SPLITS:
        errors.append(f"{label}: invalid split")
    if item["review_status"] not in REVIEW_STATUSES:
        errors.append(f"{label}: invalid review_status")
    try:
        date.fromisoformat(item["as_of_date"])
    except (TypeError, ValueError):
        errors.append(f"{label}: invalid as_of_date")

    if item["answerable"] and not item["evidence"]:
        errors.append(f"{label}: answerable case has no evidence")
    if item["expected_behavior"] == "refuse":
        if item["answerable"]:
            errors.append(f"{label}: refuse case must be answerable=false")
        if item["evidence"]:
            errors.append(f"{label}: refuse case must not contain evidence")

    for evidence_number, evidence in enumerate(item["evidence"], 1):
        prefix = f"{label}: evidence {evidence_number}"
        if not isinstance(evidence, dict):
            errors.append(f"{prefix} must be an object")
            continue
        missing_evidence = EVIDENCE_FIELDS - evidence.keys()
        extra_evidence = evidence.keys() - EVIDENCE_FIELDS
        if missing_evidence:
            errors.append(f"{prefix}: missing fields {sorted(missing_evidence)}")
            continue
        if extra_evidence:
            errors.append(f"{prefix}: unexpected fields {sorted(extra_evidence)}")
        if not re.fullmatch(r"[0-9a-f]{64}", evidence["source_sha256"]):
            errors.append(f"{prefix}: invalid SHA-256")
        source_path = ROOT / evidence["source_artifact"]
        if not source_path.is_file():
            errors.append(f"{prefix}: source artifact not found: {evidence['source_artifact']}")
        elif sha256(source_path) != evidence["source_sha256"]:
            errors.append(f"{prefix}: source artifact SHA-256 mismatch")

        matches = [
            chunk for chunk in chunks
            if chunk["document_id"] == evidence["document_id"]
            and chunk.get("article") == evidence["article"]
            and chunk["source_artifact"] == evidence["source_artifact"]
            and chunk["source_sha256"] == evidence["source_sha256"]
            and chunk["source_url"] == evidence["source_url"]
            and chunk["title"] == evidence["title"]
            and normalize(evidence["quote"]) in normalize(chunk["text"])
        ]
        if not matches:
            errors.append(f"{prefix}: quote or provenance not found in approved P0 chunks")


def main() -> int:
    cases = load_jsonl(DATASET)
    chunks = load_jsonl(CHUNKS)
    errors: list[str] = []

    for index, item in enumerate(cases, 1):
        validate_case(item, index, chunks, errors)

    ids = [item.get("case_id") for item in cases]
    questions = [normalize(item.get("question", "")) for item in cases]
    if len(ids) != len(set(ids)):
        errors.append("case_id values are not unique")
    if len(questions) != len(set(questions)):
        errors.append("question texts are not unique after whitespace normalization")

    type_counts = Counter(item.get("question_type") for item in cases)
    if len(cases) == 28:
        for question_type in sorted(QUESTION_TYPES):
            if type_counts[question_type] != 4:
                errors.append(f"pilot quota mismatch: {question_type}={type_counts[question_type]}, expected 4")
        if any(item.get("split") != "unassigned" for item in cases):
            errors.append("pilot cases must remain split=unassigned before review")
        if any(item.get("review_status") != "draft" for item in cases):
            errors.append("pilot cases must remain review_status=draft before review")

    if errors:
        print(f"FAILED: {len(errors)} validation error(s)", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    risk_counts = Counter(item["risk_level"] for item in cases)
    behavior_counts = Counter(item["expected_behavior"] for item in cases)
    evidence_count = sum(len(item["evidence"]) for item in cases)
    print(f"PASS: {len(cases)} evaluation cases")
    print("question types:", ", ".join(f"{key}={type_counts[key]}" for key in sorted(type_counts)))
    print("risk levels:", ", ".join(f"{key}={risk_counts[key]}" for key in sorted(risk_counts)))
    print("expected behaviors:", ", ".join(f"{key}={behavior_counts[key]}" for key in sorted(behavior_counts)))
    print(f"evidence records: {evidence_count}; all quotes and source hashes verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
