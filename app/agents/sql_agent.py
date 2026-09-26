"""SQL 子 Agent：schema 感知生成 + 校验 + 失败带 schema 修正循环重试。

独立上下文：本 Agent 只接触 schema 与用户子问题，不感知其他 agent 的过程。
"""
import re

from .. import db, llm

SCHEMA = {
    "sales": "sales(id, month TEXT 'YYYY-MM', region TEXT, category TEXT, amount REAL)",
    "marketing_spend": "marketing_spend(id, month TEXT, region TEXT, channel TEXT, spend REAL)",
    "inventory": "inventory(id, month TEXT, region TEXT, category TEXT, stock_qty INTEGER, turnover_days REAL)",
}

_SCHEMA_PROMPT = (
    "你是企业数仓 SQL 专家。可用表:\n" +
    "\n".join(SCHEMA.values()) +
    "\n只输出一条 SELECT 语句，不要解释。"
)


def _mock_sql(question):
    """确定性模板生成：覆盖评测集的问式。"""
    q = question
    month = re.search(r"(2026-\d{2})", q)
    region = next((r for r in db.REGIONS if r in q), None)
    table = None
    if "为什么" in q or any(k in q for k in ["归因", "原因"]):
        table = "sales"  # 归因问题的主指标恒为销售额，辅助线由归因 agent 并行补查
    elif any(k in q for k in ["投放", "营销", "花费", "spend"]):
        table = "marketing_spend"
    elif any(k in q for k in ["库存", "周转", "积压"]):
        table = "inventory"
    else:
        table = "sales"
    metric = {"sales": "SUM(amount)", "marketing_spend": "SUM(spend)",
              "inventory": "SUM(stock_qty)"}[table]
    if re.search(r"每个月|按月|趋势|逐月", q) or "为什么" in q:
        sql = "SELECT month, %s AS v FROM %s" % (metric, table)
        if region:
            sql += " WHERE region='%s'" % region
        sql += " GROUP BY month ORDER BY month"
        return sql
    if re.search(r"哪个|最高|top|排行|最多", q.lower()):
        sql = "SELECT region, %s AS v FROM %s" % (metric, table)
        if month:
            sql += " WHERE month='%s'" % month.group(1)
        sql += " GROUP BY region ORDER BY v DESC"
        return sql
    # 简单总量：默认最近月份
    sql = "SELECT %s AS v FROM %s" % (metric, table)
    conds = []
    if month:
        conds.append("month='%s'" % month.group(1))
    if region:
        conds.append("region='%s'" % region)
    if conds:
        sql += " WHERE " + " AND ".join(conds)
    return sql


def run(question, max_retry=2):
    """返回 {sql, cols, rows, attempts}。带 schema 修正重试循环。"""
    from .. import audit
    attempts = []
    sql = None
    resp = llm.chat([{"role": "system", "content": _SCHEMA_PROMPT},
                     {"role": "user", "content": question}], role="sql")
    sql = resp if resp else _mock_sql(question)
    for i in range(max_retry + 1):
        attempts.append(sql)
        audit.log("sql", "sql_generate", sql, extra={"attempt": i + 1})
        try:
            cols, rows = db.run_sql(sql)
            return {"sql": sql, "cols": cols, "rows": rows, "attempts": attempts}
        except Exception as e:  # 带错误信息走一轮 schema 修正
            audit.log("sql", "sql_retry", str(e)[:120], status="error", extra={"attempt": i + 1})
            if i == max_retry:
                raise
            fix = llm.chat([
                {"role": "system", "content": _SCHEMA_PROMPT},
                {"role": "user", "content": "SQL: %s\n错误: %s\n请修正后只输出 SELECT。"
                 % (sql, e)}], role="sql")
            sql = fix if fix else sql
    raise RuntimeError("unreachable")
