# 中国区法律法规知识库：评测集 Pilot 交接

> 状态：待项目负责人审核
>
> 生成日期：2026-10-18
>
> 数据版本：Pilot v0.1

## 已完成

- 已记录 P0 语料验收通过，并将 11 份受限或失链文档标记为延期处理。
- 已定义机器可读的单题 JSON Schema、标注口径、风险等级和审核规则。
- 已生成 28 题 Pilot，七类题型各 4 题。
- 每题均包含标准答案、必含要点、禁答项、期望行为、判断路径摘要和基准日期。
- 24 道非拒答题共绑定 36 条证据；4 道知识缺失题不附伪证据，期望系统明确拒答。
- 已生成面向人工审核的 Markdown 展开稿。

## Pilot 构成

| 维度 | 分布 |
|---|---|
| 题型 | 单文档事实、精确条款、条件与例外、跨文档综合、版本与冲突、知识缺失、歧义或错误前提各 4 题 |
| 风险 | 高风险 16 题、中风险 10 题、低风险 2 题 |
| 期望行为 | 直接回答 20 题、纠正错误前提 3 题、澄清 1 题、拒答 4 题 |
| 状态 | 全部为 `draft`、`split=unassigned` |

高风险占比较高是有意设计：跨境路径、版本冲突、敏感个人信息、未成年人和事件通知是本轮最需要防止错误行动的场景。正式 100 题扩充时再补足低风险基础事实题，并保持既定总配额。

## 自动校验结果

执行：

```bash
python3 scripts/build_eval_pilot.py
python3 scripts/validate_eval_dataset.py
```

当前结果：

```text
PASS: 28 evaluation cases
question types: ambiguity_false_premise=4, condition_exception=4,
cross_document=4, exact_article=4, knowledge_missing=4,
single_document_fact=4, version_conflict=4
risk levels: high=16, low=2, medium=10
expected behaviors: answer=20, clarify=1, correct_premise=3, refuse=4
evidence records: 36; all quotes and source hashes verified
```

此外，P0 语料校验仍通过：11 份文档、365 个条款、571 个分块，最长分块 1136 字符。

## 需要项目负责人审核

请在 `docs/evaluation-pilot-review.md` 中重点审核：

1. 问题是否符合公司 Agent 的真实提问方式。
2. 标准答案是否准确、简洁且没有超出证据。
3. 必含要点能否用于判分，禁答项是否覆盖关键风险。
4. 跨境数据和版本冲突题的规则适用是否符合预期。
5. 知识缺失题是否应该拒答，歧义题需要澄清的条件是否充分。

审核时可以直接按题号给出修改意见，例如：`CN-PRIV-0013：答案需要补充单独同意`。项目文件中的结构化状态暂不改为 `approved`，也暂不划分盲测集，以免在口径冻结前产生数据泄露或反复重分。

## 审核后的下一步

1. 将审核意见回写生成脚本并重新执行证据校验。
2. 把通过的 Pilot 样本标记为 `approved`。
3. 按既定配额扩充到 100 题正式候选集。
4. 完成近重复检查后，按题型和风险分层划分 60/20/20。
5. 冻结 20 题盲测集，再开始普通向量 RAG 与 LightRAG 的正式对比。
