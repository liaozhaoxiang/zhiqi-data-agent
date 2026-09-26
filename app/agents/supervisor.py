"""主管 Agent：共享状态 AnalysisState + 拆解分发 + 摘要回写。"""
from . import sql_agent, analysis_agent, report_agent


class AnalysisState(dict):
    """黑板模式共享状态：supervisor 写入任务规格，子 agent 回写结构化结果。"""


def run(question):
    """复杂问题的多 agent 编排主入口。返回 (report, state)。"""
    from .. import audit
    st = AnalysisState(question=question, traces=[])
    audit.log("supervisor", "task_start", question)
    # 1) 主查询：拿到主指标序列
    main = sql_agent.run(question)
    st["traces"].append({"agent": "sql", "sql": main["sql"], "n_rows": len(main["rows"])})
    # 2) 归因：内部含并行补充查询（Map-Reduce / Send 式 fan-out）
    ana = analysis_agent.run(question, main["rows"])
    st["traces"].append({"agent": "analysis", "parallel": list(ana.get("attribution", {}).get("supporting", {}).keys())})
    # 3) 报告：仅消费摘要
    sql_trace = "\n".join("sql: %s (%d rows)" % (t["sql"], t["n_rows"]) for t in st["traces"] if "sql" in t)
    report = report_agent.run(question, ana["summary"], sql_trace)
    st["traces"].append({"agent": "report", "done": True})
    audit.log("supervisor", "task_done", "report generated",
              extra={"n_agents": 3 + len(ana.get("attribution", {}).get("supporting", {}))})
    return report, st
