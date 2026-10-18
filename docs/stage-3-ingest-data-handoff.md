# LightRAG 入库数据准备交接

> 状态：P0 试跑包已就绪
>
> 语料版本：`cn-privacy-p0-v0.1`
>
> 日期：2026-10-18

## 交付结果

- `data/ingest/p0/records.jsonl`：正式的 P0 试跑输入，571 个固定分块。
- `data/ingest/p0/documents.jsonl`：11 份规范化全文，用于来源重建和 API 适配。
- `data/ingest/p0/manifest.json`：允许清单、数量、文件哈希和排除范围。
- `data/normalization/backlog.jsonl`：另外 39 份已有正文的规范化队列。
- `scripts/build_ingest_package.py`：可重复构建数据包。
- `scripts/validate_ingest_package.py`：校验内容、来源、范围及评测数据隔离。

## 当前边界

P0 数据包用于先调通 LightRAG 和普通向量 RAG 的入库、检索及回答链路。正式首轮语料仍以 50 份为目标，即 P0 的 11 份加上完成规范化与人工验收的 39 份。11 份受限或失链文档继续延期。

评测集位于 `data/evaluation/`，未进入入库包。入库适配器必须只读取 `manifest.json` 指定的文件，禁止递归扫描整个 `data/` 目录。

## 重建与校验

```bash
python3 scripts/build_ingest_package.py
python3 scripts/validate_ingest_package.py
```

校验必须确认：

- 11 份 P0 文档和 571 个记录与已验收分块逐字一致；
- 每个来源文件的 SHA-256 正确；
- 记录 ID 和正文没有重复；
- P0 与 39 份待处理正文合计正好覆盖 50 份正文候选；
- 11 份延期文档没有进入数据包或规范化队列；
- 入库数据中不存在评测问题、标准答案、必含要点或期望行为字段。

## 下一步

1. 根据当前 LightRAG 版本实现只读取 `records.jsonl` 的入库适配器。
2. 建立完全独立的 LightRAG 和普通向量 RAG 存储目录。
3. 先用少量记录做冒烟测试，再导入完整 571 个记录。
4. 检查实体关系抽取质量、条款引用元数据和重复入库幂等性。
5. 在同一固定分块上运行 28 题 Pilot，不在此阶段形成最终选型结论。
