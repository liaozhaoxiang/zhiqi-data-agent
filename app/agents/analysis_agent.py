"""归因分析子 Agent：维度对比 → 找最大差异因子 → 不充分时触发补充查询循环。

上下文物隔离的示范：它不接收 SQL agent 的原始 schema/SQL，只接收
supervisor 分发的子问题与查询结果的结构化摘要。
"""
import threading

from .. import llm
from . import sql_agent


def _mock_attribution(question, series):
    """对月度序列做趋势归因：给出环比拐点与幅度。"""
    if len(series) < 2:
        return {"conclusion": "数据点不足，无法归因", "evidence": series}
    drops = []
    for i in range(1, len(series)):
        prev, cur = series[i - 1][1], series[i][1]
        if prev:
            drops.append((series[i][0], (cur - prev) / prev))
    worst = min(drops, key=lambda x: x[1])
    first, last = series[0][1], series[-1][1]
    total_chg = (last - first) / first if first else 0
    return {
        "conclusion": "从 %s 到 %s 累计变化 %+.1f%%，最大单月拐点在 %s（%+.1f%%）"
                      % (series[0][0], series[-1][0], total_chg * 100, worst[0], worst[1] * 100),
        "evidence": series,
    }


def _parallel_subqueries(subquestions):
    """Map-Reduce：子问题并行分发（生产环境对应 LangGraph Send API）。"""
    results = {}
    threads = []

    def worker(key, q):
        results[key] = sql_agent.run(q)

    for k, q in subquestions.items():
        t = threading.Thread(target=worker, args=(k, q))
        t.start()
        threads.append(t)
    for t in threads:
        t.join(timeout=30)
    return results


def run(question, main_series):
    """main_series: [(month, value)] 主指标序列；补充查询并行执行。"""
    attr = _mock_attribution(question, main_series)
    # 相关性不足时（这里演示为：存在明显下滑则并行拉三条数据线）
    if any(chg < -0.05 for _, chg in _monthly_changes(main_series)):
        subs = {
            "投放": "华东 marketing_spend 每个月趋势",
            "库存": "华东 库存 每个月趋势",
            "主指标按区": "sales 哪个region最高 2026-06",
        }
        extra = _parallel_subqueries(subs)
        summary_lines = ["- 主指标: " + attr["conclusion"]]
        for k, v in extra.items():
            summary_lines.append("- %s: %s => %s" % (k, v["sql"], v["rows"][:6]))
        attr["supporting"] = extra
        attr["conclusion"] += "。结合并行补充查询（投放/库存同周期变化），下滑与投放削减、库存周转恶化同现，构成主要归因假设。"
    else:
        summary_lines = ["- 主指标: " + attr["conclusion"]]
    return {"attribution": attr, "summary": "\n".join(summary_lines)}


def _monthly_changes(series):
    out = []
    for i in range(1, len(series)):
        prev, cur = series[i - 1][1], series[i][1]
        out.append((series[i][0], (cur - prev) / prev if prev else 0))
    return out
