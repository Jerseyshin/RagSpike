#!/usr/bin/env python3
"""Audit downloaded corpus artifacts for actual, parseable body content."""

from __future__ import annotations

import argparse
import collections
import hashlib
import html.parser
import json
import re
import subprocess
import urllib.parse
import zipfile
from pathlib import Path
from typing import Any


ARTICLE_RE = re.compile(r"第[一二三四五六七八九十百千万零〇两0-9]+条")
SPACE_RE = re.compile(r"\s+")
BLOCK_PATTERNS = ("404", "页面不存在", "访问验证", "访问异常", "系统繁忙", "Forbidden")


class VisibleHTML(html.parser.HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.hidden = 0
        self.in_title = False
        self.title_parts: list[str] = []
        self.text_parts: list[str] = []
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "noscript", "svg"}:
            self.hidden += 1
        if tag == "title":
            self.in_title = True
        if tag == "a":
            href = dict(attrs).get("href")
            if href:
                self.links.append(href)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript", "svg"} and self.hidden:
            self.hidden -= 1
        if tag == "title":
            self.in_title = False

    def handle_data(self, data: str) -> None:
        if self.in_title:
            self.title_parts.append(data)
        if not self.hidden:
            self.text_parts.append(data)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", action="append")
    parser.add_argument("--audit", default="data/downloads/download-audit.jsonl")
    parser.add_argument("--report", default="docs/corpus-download-report.md")
    return parser.parse_args()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def audit_pdf(path: Path) -> dict[str, Any]:
    signature_ok = path.read_bytes()[:5] == b"%PDF-"
    completed = subprocess.run(
        ["pdftotext", "-layout", str(path), "-"],
        check=False,
        capture_output=True,
        timeout=60,
    )
    text = completed.stdout.decode("utf-8", errors="replace") if completed.returncode == 0 else ""
    visible = SPACE_RE.sub("", text)
    if not signature_ok:
        classification = "invalid_file"
    elif len(visible) >= 1000:
        classification = "body_candidate"
    elif visible:
        classification = "partial_or_scanned_pdf"
    else:
        classification = "unreadable_or_scanned_pdf"
    return {
        "classification": classification,
        "title": None,
        "visible_characters": len(visible),
        "article_markers": len(ARTICLE_RE.findall(text)),
        "attachment_urls": [],
        "diagnostic": None if completed.returncode == 0 else completed.stderr.decode(errors="replace")[:500],
    }


def audit_docx(path: Path) -> dict[str, Any]:
    try:
        with zipfile.ZipFile(path) as archive:
            xml = archive.read("word/document.xml").decode("utf-8", errors="replace")
        text = re.sub(r"<[^>]+>", " ", xml)
        visible = SPACE_RE.sub("", text)
        classification = "body_candidate" if len(visible) >= 1000 else "partial_or_metadata"
        diagnostic = None
    except (OSError, KeyError, zipfile.BadZipFile) as exc:
        visible = ""
        classification = "invalid_file"
        diagnostic = f"{type(exc).__name__}: {exc}"
    return {
        "classification": classification,
        "title": None,
        "visible_characters": len(visible),
        "article_markers": len(ARTICLE_RE.findall(visible)),
        "attachment_urls": [],
        "diagnostic": diagnostic,
    }


def audit_html(path: Path, source_url: str) -> dict[str, Any]:
    raw = path.read_bytes()
    text = raw.decode("utf-8", errors="replace")
    parser = VisibleHTML()
    parser.feed(text)
    visible = SPACE_RE.sub("", " ".join(parser.text_parts))
    title = SPACE_RE.sub(" ", " ".join(parser.title_parts)).strip() or None
    article_markers = len(ARTICLE_RE.findall(visible))
    attachment_urls = sorted(
        {
            urllib.parse.urljoin(source_url, link)
            for link in parser.links
            if urllib.parse.urlparse(link).path.lower().endswith((".pdf", ".doc", ".docx", ".zip"))
        }
    )
    blocked = next((pattern for pattern in BLOCK_PATTERNS if pattern.lower() in visible.lower()), None)
    platform_metadata = title and (
        "全国标准信息公共服务平台" in title or title in {"协会标准", "全国网络安全标准化技术委员会"}
    )
    if article_markers >= 3:
        classification = "body_candidate"
    elif blocked and len(visible) < 1500:
        classification = "blocked_or_error"
    elif len(visible) < 300:
        classification = "dynamic_shell"
    elif platform_metadata:
        classification = "partial_or_metadata" if len(visible) >= 1200 else "metadata_only"
    elif len(visible) >= 900:
        classification = "body_candidate"
    elif len(visible) >= 1200:
        classification = "partial_or_metadata"
    else:
        classification = "metadata_only"
    return {
        "classification": classification,
        "title": title,
        "visible_characters": len(visible),
        "article_markers": article_markers,
        "attachment_urls": attachment_urls,
        "diagnostic": blocked,
    }


def main() -> int:
    args = parse_args()
    result_paths = args.results or ["data/downloads/download-results.jsonl"]
    rows = [row for path in result_paths for row in load_jsonl(Path(path))]
    audited: list[dict[str, Any]] = []
    for row in rows:
        path = Path(row["artifact_path"])
        if path.suffix.lower() == ".pdf":
            detail = audit_pdf(path)
        elif path.suffix.lower() == ".docx":
            detail = audit_docx(path)
        else:
            detail = audit_html(path, row["source_url"])
        audited.append(
            {
                "document_id": row["document_id"],
                "source_index": row.get("source_index", 1),
                "source_url": row["source_url"],
                "artifact_path": str(path),
                "size_bytes": path.stat().st_size,
                "sha256_verified": file_sha256(path) == row["sha256"],
                "tls_verified": row.get("tls_verified"),
                **detail,
            }
        )

    audit_path = Path(args.audit)
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    with audit_path.open("w", encoding="utf-8") as handle:
        for row in audited:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")

    by_doc: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    for row in audited:
        by_doc[row["document_id"]].append(row)
    usable = {
        document_id
        for document_id, artifacts in by_doc.items()
        if any(item["classification"] == "body_candidate" for item in artifacts)
    }
    needs_work = sorted(set(by_doc) - usable)
    classes = collections.Counter(row["classification"] for row in audited)
    insecure = sum(row["tls_verified"] is False for row in audited)
    attachments = sum(len(row["attachment_urls"]) for row in audited)

    report = [
        "# 语料下载与可用性审计报告",
        "",
        "> 状态：自动审计结果，需人工复核正文边界与版本信息。",
        "",
        "## 汇总",
        "",
        f"- 清单文档：{len(by_doc)}",
        f"- 官方来源文件：{len(audited)}",
        f"- 至少有一个正文候选的文档：{len(usable)}",
        f"- 尚未识别出正文的文档：{len(needs_work)}",
        f"- SHA-256 校验失败：{sum(not row['sha256_verified'] for row in audited)}",
        f"- 因官方站点证书问题降级下载的来源：{insecure}",
        f"- 页面中发现的附件链接：{attachments}",
        "",
        "### 文件分类",
        "",
    ]
    report.extend(f"- `{name}`：{count}" for name, count in sorted(classes.items()))
    report.extend(["", "## 尚需补正文或人工复核", ""])
    if needs_work:
        for document_id in needs_work:
            summary = ", ".join(
                f"source-{item['source_index']:02d}={item['classification']}"
                for item in by_doc[document_id]
            )
            report.append(f"- `{document_id}`：{summary}")
    else:
        report.append("- 无")
    report.extend(
        [
            "",
            "## 判定说明",
            "",
            "`body_candidate` 只表示文件内检测到足量可解析文本或法规条款标记；它不代表版本、正文边界或法律效力已人工确认。动态壳页、元数据页和扫描 PDF 会进入后续补采或 OCR 队列。",
            "",
        ]
    )
    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(report), encoding="utf-8")
    print(json.dumps({"documents": len(by_doc), "sources": len(audited), "usable": len(usable), "needs_work": len(needs_work), "classes": classes}, ensure_ascii=False, default=dict))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
