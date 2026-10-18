#!/usr/bin/env python3
"""Regression checks for the first P0 parsing batch."""

from __future__ import annotations

import json
from pathlib import Path


EXPECTED_ARTICLES = {
    "cn-pipl-2021": 74,
    "cn-data-security-law-2021": 55,
    "cn-cybersecurity-law-2025": 81,
    "cn-civil-code-2020-privacy-sections": 8,
    "cn-network-data-regulation-2024": 64,
    "cn-data-export-security-assessment-measures-2022": 20,
    "cn-pi-export-standard-contract-measures-2023": 22,
    "cn-cross-border-data-flow-provisions-2024": 14,
    "cn-pi-compliance-audit-measures-2025": 20,
    "cn-app-illegal-pi-identification-method-2019": 0,
    "cn-app-necessary-pi-scope-provisions-2021": 7,
}


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main() -> int:
    root = Path("data/processed/p0")
    index = load_jsonl(root / "index.jsonl")
    chunks = load_jsonl(root / "chunks.jsonl")
    actual = {row["document_id"]: row["article_count"] for row in index}
    assert actual == EXPECTED_ARTICLES, (actual, EXPECTED_ARTICLES)
    assert len(index) == len(EXPECTED_ARTICLES)
    assert len({row["chunk_id"] for row in chunks}) == len(chunks)
    assert all(row["text"].strip() for row in chunks)
    assert all(Path(path).is_file() for row in index for path in row["source_artifacts"])

    cybersecurity = (root / "cn-cybersecurity-law-2025.md").read_text(encoding="utf-8")
    assert "2025年10月28日" in cybersecurity
    assert cybersecurity.count("#### 第三十二条") == 1
    assert "#### 第八十一条" in cybersecurity
    assert "修正草案" not in cybersecurity

    civil_code = (root / "cn-civil-code-2020-privacy-sections.md").read_text(encoding="utf-8")
    assert "第一千零三十二条" in civil_code and "第一千零三十九条" in civil_code
    assert "第五编婚姻家庭" not in civil_code

    lengths = [len(row["text"]) for row in chunks]
    summary = {
        "documents": len(index),
        "chunks": len(chunks),
        "articles_detected": sum(row["article_count"] for row in index),
        "min_chunk_characters": min(lengths),
        "max_chunk_characters": max(lengths),
        "mean_chunk_characters": round(sum(lengths) / len(lengths), 1),
    }
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
