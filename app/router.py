"""复杂度路由：简单取数走单 agent 快速通道，复杂任务才进多 agent 编排。

判断标准三条：上下文会不会爆、模型要不要异构、权限要不要隔离；
同时按"是否多源归因/并行"识别复杂度。三条都不占 → 不拆。
"""
import re

from . import db

SIMPLE_PAT = re.compile(r"^(上个月|本月|最近)?(的)?\s*(总销售额|销售额|总投放|投放花费|库存总量)[是多]?(多少|是多少|什么水平)?[??]?$")


def classify(question):
    """返回 'simple' | 'complex'。"""
    q = question.strip()
    if SIMPLE_PAT.match(q) and "为什么" not in q and "为什么" not in q:
        return "simple"
    complex_signals = ["为什么", "归因", "原因", "下滑", "增长", "对比", "和.*关系", "影响"]
    if any(re.search(p, q) for p in complex_signals):
        return "complex"
    return "simple"


def fast_path(question):
    """快速通道：单 agent 直接调工具，不走编排。"""
    r = db.run_sql  # 仅演示权限路径一致：同样走只读+校验
    from .agents import sql_agent
    res = sql_agent.run(question)
    return "直接结果: %s" % (res["rows"][:5] or "空"), [{"agent": "sql-fast", "sql": res["sql"], "n_rows": len(res["rows"])}]
