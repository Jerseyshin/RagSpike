# 原始语料

本目录由 `scripts/fetch_corpus.py` 根据已批准的文档清单生成。

- 每个 `document_id` 使用独立子目录。
- `source-01`、`source-02` 对应清单中 `official_urls` 的顺序。
- 文件保持下载时的原始字节，不在本目录清洗或改写。
- 下载 URL、最终跳转 URL、响应类型、文件大小和 SHA-256 记录在 `data/downloads/download-results.jsonl`。
- HTML 详情页不自动等同于正文；后续完整性检查会区分“全文”“元数据页”和“下载失败”。
