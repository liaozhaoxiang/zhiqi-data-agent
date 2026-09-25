"""SQL Agent 准确率回归评测。

评测集独立于 Agent 代码（独立评测与回归：换模型/调 prompt 单独跑本文件）。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import db  # noqa: E402
from app.agents import sql_agent  # noqa: E402

CASES = [
    # (question, expected_sql 关键片段)
    ("上个月总销售额是多少", ["sales", "SUM(amount)"]),
    ("2026-06 总销售额是多少", ["sales", "SUM(amount)", "2026-06"]),
    ("2026-06 华南 销售额", ["sales", "华南"]),
    ("2026-03 总投放花费是多少", ["marketing_spend", "SUM(spend)", "2026-03"]),
    ("华东 2026-06 投放", ["marketing_spend", "华东", "2026-06"]),
    ("2026-06 库存总量", ["inventory", "SUM(stock_qty)"]),
    ("每个月 销售额 趋势", ["GROUP BY month", "ORDER BY month"]),
    ("华东 每个月 投放 趋势", ["marketing_spend", "GROUP BY month", "华东"]),
    ("2026-06 哪个region销售额最高", ["GROUP BY region", "ORDER BY"]),
    ("2026-06 哪个region库存最多", ["inventory", "GROUP BY region"]),
    ("西南 2026-01 销售额", ["sales", "西南", "2026-01"]),
    ("华北 2026-05 投放花费", ["marketing_spend", "华北"]),
    ("每个月 库存 趋势", ["inventory", "GROUP BY month"]),
    ("2026-02 哪个region投放最多", ["marketing_spend", "GROUP BY region"]),
    ("销售额 2026-04", ["sales", "2026-04"]),
    ("2026-06 营销花费", ["marketing_spend"]),
    ("华南 每个月 销售额 趋势", ["GROUP BY month", "华南"]),
    ("2026-03 库存 周转", ["inventory"]),
    ("2026-05 哪个region销售额最高", ["GROUP BY region"]),
    ("华东 2026-02 销售额", ["sales", "华东", "2026-02"]),
]

# 权限回归：这些 SQL 必须被拒绝
PERMISSION_CASES = [
    "DROP TABLE sales",
    "INSERT INTO sales VALUES(1,'x','y','z',1)",
    "SELECT 1; SELECT 2",
    "PRAGMA table_info(sales)",
    "ATTACH DATABASE 'x' AS x",
]


def main():
    db.build_db()
    hit = 0
    for q, expects in CASES:
        try:
            res = sql_agent.run(q)
            ok = all(e.lower() in res["sql"].lower() for e in expects)
        except Exception:
            ok = False
        hit += ok
        print("%s  %s  ->  %s" % ("PASS" if ok else "FAIL", q, getattr(sql_agent, "_last", "?")))
        if not ok:
            print("       sql:", res.get("sql", "<error>"))
    print("SQL 准确率: %d/%d = %.0f%%" % (hit, len(CASES), 100.0 * hit / len(CASES)))

    blocked = 0
    for s in PERMISSION_CASES:
        try:
            db.run_sql(s)
            print("FAIL 未拦截:", s)
        except Exception:
            blocked += 1
            print("PASS 已拦截:", s)
    print("权限拦截: %d/%d" % (blocked, len(PERMISSION_CASES)))


if __name__ == "__main__":
    main()
