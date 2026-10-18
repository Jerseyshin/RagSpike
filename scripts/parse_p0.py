#!/usr/bin/env python3
"""Parse P0 legal documents into reviewable Markdown and article-level JSONL."""

from __future__ import annotations

import hashlib
import html.parser
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


MANIFEST = Path("data/manifests/documents.jsonl")
OUTPUT = Path("data/processed/p0")
ARTICLE = r"第[一二三四五六七八九十百千万零〇两0-9]+条"
CHAPTER = re.compile(r"^第[一二三四五六七八九十百千万零〇两0-9]+章(?:\s|　)*(.*)$")
SECTION = re.compile(r"^第[一二三四五六七八九十百千万零〇两0-9]+节(?:\s|　)*(.*)$")
ARTICLE_LINE = re.compile(rf"^({ARTICLE})(?:\s|　)*(.*)$")
SPACE = re.compile(r"[ \t\u00a0]+")

SOURCES = {
    "cn-pipl-2021": "data/raw/cn-pipl-2021/source-01.html",
    "cn-data-security-law-2021": "data/raw-attachments/cn-data-security-law-2021/source-01.html",
    "cn-cybersecurity-law-2025": "data/raw-flk/cn-cybersecurity-law-2025/consolidated.pdf",
    "cn-civil-code-2020-privacy-sections": "data/raw/cn-civil-code-2020-privacy-sections/source-01.pdf",
    "cn-network-data-regulation-2024": "data/raw/cn-network-data-regulation-2024/source-01.html",
    "cn-data-export-security-assessment-measures-2022": "data/raw/cn-data-export-security-assessment-measures-2022/source-01.html",
    "cn-pi-export-standard-contract-measures-2023": [
        "data/raw/cn-pi-export-standard-contract-measures-2023/source-01.html",
        "data/raw/cn-pi-export-standard-contract-measures-2023/source-02.pdf",
    ],
    "cn-cross-border-data-flow-provisions-2024": "data/raw/cn-cross-border-data-flow-provisions-2024/source-01.html",
    "cn-pi-compliance-audit-measures-2025": "data/raw/cn-pi-compliance-audit-measures-2025/source-01.html",
    "cn-app-illegal-pi-identification-method-2019": "data/raw/cn-app-illegal-pi-identification-method-2019/source-01.html",
    "cn-app-necessary-pi-scope-provisions-2021": "data/raw/cn-app-necessary-pi-scope-provisions-2021/source-01.html",
}

TARGET_IDS = {"BodyLabel", "articleins", "con_con"}
TARGET_CLASSES = {"Three_xilan_07", "TRS_Editor"}
BLOCK_TAGS = {"p", "li", "h1", "h2", "h3", "h4", "h5", "h6", "tr", "br"}


class BodyExtractor(html.parser.HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.active_depth = 0
        self.hidden_depth = 0
        self.parts: list[str] = []
        self.matched = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        classes = set((values.get("class") or "").split())
        match = values.get("id") in TARGET_IDS or bool(classes & TARGET_CLASSES)
        if self.active_depth:
            self.active_depth += 1
        elif match:
            self.active_depth = 1
            self.matched = True
        if self.active_depth and tag in {"script", "style", "noscript", "svg"}:
            self.hidden_depth += 1
        if self.active_depth and not self.hidden_depth and tag in BLOCK_TAGS:
            self.parts.append("\n")

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        if self.active_depth and not self.hidden_depth and tag in BLOCK_TAGS:
            self.parts.append("\n")
        if self.active_depth and tag in {"script", "style", "noscript", "svg"} and self.hidden_depth:
            self.hidden_depth -= 1
        if self.active_depth:
            self.active_depth -= 1

    def handle_data(self, data: str) -> None:
        if self.active_depth and not self.hidden_depth:
            self.parts.append(data)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_lines(text: str) -> list[str]:
    lines: list[str] = []
    for raw in text.replace("\r", "\n").replace("\f", "\n").split("\n"):
        line = SPACE.sub(" ", raw).strip(" \u3000")
        line = re.sub(r"(?<=[\u3400-\u9fff]) (?=[\u3400-\u9fff])", "", line)
        line = re.sub(r"(?<=[0-9０-９]) (?=[0-9０-９])", "", line)
        if re.fullmatch(r"—?\s*[0-9０-９ ]+\s*—?", line):
            continue
        if line.startswith("全国人民代表大会常务委员会公报"):
            continue
        if line and (not lines or line != lines[-1]):
            lines.append(line)
    return lines


def extract_html(path: Path) -> list[str]:
    parser = BodyExtractor()
    parser.feed(path.read_text(encoding="utf-8", errors="replace"))
    if not parser.matched:
        raise RuntimeError(f"no known body container found in {path}")
    return normalize_lines("".join(parser.parts))


def extract_pdf(path: Path) -> list[str]:
    completed = subprocess.run(
        ["pdftotext", "-raw", str(path), "-"],
        check=True,
        capture_output=True,
        timeout=120,
    )
    return normalize_lines(completed.stdout.decode("utf-8", errors="replace"))


def scope_civil_code(lines: list[str]) -> list[str]:
    start = next(i for i, line in enumerate(lines) if line.startswith("第一千零三十二条"))
    end_start = next(i for i, line in enumerate(lines[start:], start) if line.startswith("第一千零三十九条"))
    end = next(
        (
            i
            for i in range(end_start + 1, len(lines))
            if ARTICLE_LINE.match(lines[i]) or CHAPTER.match(lines[i]) or re.match(r"^第[一二三四五六七八九十]+编", lines[i])
        ),
        len(lines),
    )
    prefix = ["第六章 隐私权和个人信息保护（节选：第一千零三十二条至第一千零三十九条）"]
    return prefix + lines[start:end]


def scope_cybersecurity_law(lines: list[str]) -> list[str]:
    last_article = next(i for i, line in enumerate(lines) if line.startswith("第八十一条"))
    end = next(
        (i for i in range(last_article + 1, len(lines)) if lines[i].startswith("关于 《中华人民共和国网络安全法")),
        len(lines),
    )
    return lines[:end]


def markdown_lines(lines: list[str]) -> list[str]:
    rendered: list[str] = []
    last_article_number: int | None = None
    for line in lines:
        if line.startswith("来源文本 "):
            last_article_number = None
            rendered.extend(["", f"## {line}", ""])
            continue
        if CHAPTER.match(line):
            rendered.extend(["", f"## {line}", ""])
        elif SECTION.match(line):
            rendered.extend(["", f"### {line}", ""])
        elif match := ARTICLE_LINE.match(line):
            candidate_number = article_number(match.group(1))
            if last_article_number is None or candidate_number == last_article_number + 1:
                last_article_number = candidate_number
                rendered.extend(["", f"#### {match.group(1)}", ""])
                if match.group(2):
                    rendered.append(match.group(2))
            else:
                rendered.append(line)
        else:
            rendered.append(line)
    return rendered


def article_number(article: str) -> int | None:
    value = article.removeprefix("第").removesuffix("条")
    if value.isdigit():
        return int(value)
    digits = {"零": 0, "〇": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}
    units = {"十": 10, "百": 100, "千": 1000, "万": 10000}
    total = section = number = 0
    for char in value:
        if char in digits:
            number = digits[char]
        elif char in units:
            unit = units[char]
            if unit == 10000:
                total += (section + number) * unit
                section = number = 0
            else:
                section += (number or 1) * unit
                number = 0
        else:
            return None
    return total + section + number


def article_chunks(
    lines: list[str],
    row: dict[str, Any],
    artifact: Path,
    source_url: str,
    source_sequence: int,
) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    chapter: str | None = None
    section: str | None = None
    current_article: str | None = None
    current_article_number: int | None = None
    current: list[str] = []

    def flush() -> None:
        if not current:
            return
        article = current_article or "full-document"
        chunks.append(
            {
                "chunk_id": f"{row['document_id']}::source-{source_sequence:02d}::{article}::{len(chunks) + 1:03d}",
                "document_id": row["document_id"],
                "title": row["title"],
                "article": current_article,
                "heading_path": [item for item in (chapter, section, current_article) if item],
                "text": "\n".join(current).strip(),
                "source_url": source_url,
                "source_artifact": str(artifact),
                "source_sha256": sha256(artifact),
                "validity_status": row["validity_status"],
                "effective_date": row.get("effective_date"),
            }
        )

    for line in lines:
        if CHAPTER.match(line):
            chapter = line
            section = None
            if current_article:
                current.append(line)
            continue
        if SECTION.match(line):
            section = line
            if current_article:
                current.append(line)
            continue
        if match := ARTICLE_LINE.match(line):
            candidate_number = article_number(match.group(1))
            if current_article_number is not None and candidate_number != current_article_number + 1:
                current.append(line)
                continue
            flush()
            current_article = match.group(1)
            current_article_number = candidate_number
            current = [line]
        elif current_article:
            current.append(line)
        elif not chunks:
            current.append(line)
    flush()
    return chunks


def split_large_chunks(chunks: list[dict[str, Any]], threshold: int = 1500) -> list[dict[str, Any]]:
    marker = re.compile(r"^(?:[一二三四五六七八九十百]+、|（[一二三四五六七八九十百]+）)")
    output: list[dict[str, Any]] = []
    for chunk in chunks:
        if len(chunk["text"]) <= threshold:
            output.append(chunk)
            continue
        lines = chunk["text"].splitlines()
        starts = [index for index, line in enumerate(lines) if marker.match(line)]
        if len(starts) < 2:
            output.append(chunk)
            continue
        boundaries = starts + [len(lines)]
        prefix = lines[: starts[0]]
        context = lines[0]
        if "附件" in prefix:
            attachment_index = prefix.index("附件")
            if attachment_index + 1 < len(prefix):
                context = f"附件：{prefix[attachment_index + 1]}"
        segments: list[list[str]] = []
        if prefix:
            segments.append(prefix)
        segments.extend(lines[start:end] for start, end in zip(boundaries, boundaries[1:]))
        for part_number, segment in enumerate(segments, 1):
            text = "\n".join(segment).strip()
            if part_number > 1 and not text.startswith(context):
                text = f"{context}\n{text}"
            part = dict(chunk)
            part["chunk_id"] = f"{chunk['chunk_id']}::part-{part_number:02d}"
            part["text"] = text
            part["section_label"] = marker.match(segment[0]).group(0) if segment and marker.match(segment[0]) else None
            output.append(part)
    return output


def main() -> int:
    rows = {
        row["document_id"]: row
        for row in (json.loads(line) for line in MANIFEST.read_text(encoding="utf-8").splitlines() if line.strip())
        if row["priority"] == "P0"
    }
    OUTPUT.mkdir(parents=True, exist_ok=True)
    indexes: list[dict[str, Any]] = []
    all_chunks: list[dict[str, Any]] = []
    parsed_at = datetime.now(timezone.utc).isoformat()
    for document_id, row in rows.items():
        configured_sources = SOURCES[document_id]
        artifacts = [Path(path) for path in configured_sources] if isinstance(configured_sources, list) else [Path(configured_sources)]
        bodies: list[list[str]] = []
        chunks: list[dict[str, Any]] = []
        source_urls: list[str] = []
        for source_sequence, artifact in enumerate(artifacts, 1):
            lines = extract_pdf(artifact) if artifact.suffix.lower() == ".pdf" else extract_html(artifact)
            if document_id == "cn-civil-code-2020-privacy-sections":
                lines = scope_civil_code(lines)
            elif document_id == "cn-cybersecurity-law-2025":
                lines = scope_cybersecurity_law(lines)
            source_url = (
                "https://flk.npc.gov.cn/law-search/download/pc?format=pdf&bbbs=021e7d7684474107b8f3febbb1c4f8b5&fileId="
                if document_id == "cn-cybersecurity-law-2025"
                else row["official_urls"][min(source_sequence - 1, len(row["official_urls"]) - 1)]
            )
            bodies.append(lines)
            source_urls.append(source_url)
            chunks.extend(article_chunks(lines, row, artifact, source_url, source_sequence))
        lines = []
        for source_sequence, body in enumerate(bodies, 1):
            if len(bodies) > 1:
                lines.append(f"来源文本 {source_sequence}")
            lines.extend(body)
        article_count = sum(chunk["article"] is not None for chunk in chunks)
        chunks = split_large_chunks(chunks)
        frontmatter = [
            "---",
            f"document_id: {document_id}",
            f"title: {row['title']}",
            f"source_urls: {json.dumps(source_urls, ensure_ascii=False)}",
            f"source_artifacts: {json.dumps([str(path) for path in artifacts], ensure_ascii=False)}",
            f"source_sha256: {json.dumps([sha256(path) for path in artifacts], ensure_ascii=False)}",
            f"parsed_at: {parsed_at}",
            f"scope_mode: {row['scope_mode']}",
            "---",
            "",
            f"# {row['title']}",
            "",
        ]
        output_path = OUTPUT / f"{document_id}.md"
        output_path.write_text("\n".join(frontmatter + markdown_lines(lines)).strip() + "\n", encoding="utf-8")
        indexes.append(
            {
                "document_id": document_id,
                "output_path": str(output_path),
                "source_artifacts": [str(path) for path in artifacts],
                "source_sha256": [sha256(path) for path in artifacts],
                "line_count": len(lines),
                "article_count": article_count,
                "chunk_count": len(chunks),
                "parsed_at": parsed_at,
            }
        )
        all_chunks.extend(chunks)

    (OUTPUT / "index.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in indexes),
        encoding="utf-8",
    )
    (OUTPUT / "chunks.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in all_chunks),
        encoding="utf-8",
    )
    print(json.dumps({"documents": len(indexes), "chunks": len(all_chunks), "articles": sum(row["article_count"] for row in indexes)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
