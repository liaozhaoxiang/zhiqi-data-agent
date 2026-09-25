"""演示数仓：SQLite 三张表 + 只读连接 + SQL 白名单校验。

权限隔离落点：
- sql_agent 只能通过 get_readonly_conn() 拿 mode=ro 连接；
- validate_sql() 只放行单条 SELECT，拒绝 PRAGMA/ATTACH/多语句。
"""
import os
import random
import re
import sqlite3

from . import config

REGIONS = ["华东", "华南", "华北", "西南"]


def build_db(path=None):
    """确定性生成演示数据（华东近三月投放削减+库存积压，供归因演示）。"""
    path = path or config.DB_PATH
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if os.path.exists(path):
        os.remove(path)
    conn = sqlite3.connect(path)
    c = conn.cursor()
    c.execute("CREATE TABLE sales (id INTEGER PRIMARY KEY, month TEXT, region TEXT, category TEXT, amount REAL)")
    c.execute("CREATE TABLE marketing_spend (id INTEGER PRIMARY KEY, month TEXT, region TEXT, channel TEXT, spend REAL)")
    c.execute("CREATE TABLE inventory (id INTEGER PRIMARY KEY, month TEXT, region TEXT, category TEXT, stock_qty INTEGER, turnover_days REAL)")
    rnd = random.Random(42)
    months = ["2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06"]
    cats = ["家电", "数码", "家居"]
    base = {"华东": 900, "华南": 600, "华北": 500, "西南": 300}
    for mi, m in enumerate(months):
        for r in REGIONS:
            decay = 0.82 ** max(0, mi - 2) if r == "华东" else 1.03 ** mi  # 华东 3 月起持续下滑
            for cat in cats:
                c.execute("INSERT INTO sales(month,region,category,amount) VALUES(?,?,?,?)",
                          (m, r, cat, round(base[r] * decay * rnd.uniform(0.85, 1.15), 2)))
            # 华东 3 月起投放削减 30%
            spend_factor = 0.7 if (r == "华东" and mi >= 2) else (1.0 + 0.03 * mi)
            for ch in ["搜索", "信息流"]:
                c.execute("INSERT INTO marketing_spend(month,region,channel,spend) VALUES(?,?,?,?)",
                          (m, r, ch, round(base[r] * 0.4 * spend_factor * rnd.uniform(0.9, 1.1), 2)))
            # 华东 3 月起库存周转恶化
            bad = 1.0 + 0.25 * (mi - 2) if (r == "华东" and mi >= 2) else 1.0
            for cat in cats:
                c.execute("INSERT INTO inventory(month,region,category,stock_qty,turnover_days) VALUES(?,?,?,?,?)",
                          (m, r, cat, int(base[r] * 0.5 * bad * rnd.uniform(0.9, 1.1)),
                           round(30 * bad * rnd.uniform(0.9, 1.1), 1)))
    conn.commit()
    conn.close()
    return path


def get_readonly_conn(path=None):
    """只读连接：mode=ro，写操作直接抛 sqlite3.OperationalError。"""
    path = path or config.DB_PATH
    if not os.path.exists(path):
        build_db(path)
    return sqlite3.connect("file:%s?mode=ro" % path.replace("\\", "/"), uri=True)


_FORBIDDEN = re.compile(r"\b(insert|update|delete|drop|alter|create|attach|pragma|vacuum)\b", re.I)


def validate_sql(sql):
    """只放行单条 SELECT。返回 (ok, reason)。"""
    sql = sql.strip().rstrip(";")
    if ";" in sql:
        return False, "拒绝多语句"
    if not re.match(r"(?is)^\s*select\b", sql):
        return False, "仅允许 SELECT"
    if _FORBIDDEN.search(sql):
        return False, "包含被禁关键词"
    return True, ""


def run_sql(sql, path=None):
    ok, reason = validate_sql(sql)
    if not ok:
        raise PermissionError("SQL 校验失败: %s | sql=%s" % (reason, sql))
    conn = get_readonly_conn(path)
    try:
        cur = conn.execute(sql)
        cols = [d[0] for d in cur.description]
        rows = cur.fetchall()
        return cols, rows
    finally:
        conn.close()


if __name__ == "__main__":
    p = build_db()
    print("demo db built:", p)
