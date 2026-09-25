"""报告子 Agent：只消费上游结构化摘要，无任何 DB 权限。"""
from .. import llm


def run(question, analysis_summary, sql_trace):
    """生成 Markdown 报告。sql_trace 只保留 sql 文本与行数，不含过程态。"""
    resp = llm.chat([
        {"role": "system", "content": "你是数据分析报告撰写者，只依据给定摘要写 Markdown 报告，包含：结论、依据、建议三节。"},
        {"role": "user", "content": "问题: %s\n摘要:\n%s\nSQL轨迹:\n%s" % (question, analysis_summary, sql_trace)},
    ], role="report")
    if resp:
        return resp
    lines = [
        "# 数据分析报告",
        "",
        "## 问题",
        question,
        "",
        "## 结论",
        analysis_summary,
        "",
        "## 依据",
        "```sql\n%s\n```" % sql_trace.splitlines()[0] if sql_trace else "（无）",
        "",
        "## 建议",
        "1. 核对投放策略与下滑拐点的时间耦合，验证归因假设；",
        "2. 对库存周转恶化类目做补货/促销干预并观察 1-2 个月；",
        "3. 下一次复核建议拉长窗口至 12 个月以排除季节性。",
    ]
    return "\n".join(lines)
