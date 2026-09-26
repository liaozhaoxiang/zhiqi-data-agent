"""Agent 级访问审计日志（JSONL，一行一条）。

设计要点（面试口径：审计日志按 agent 分域）：
- 记录维度：谁(agent) / 做了什么(action) / 细节 / 状态 / 耗时
- 安全重点：**被 SQL 校验层拒绝的语句同样留痕**（status=denied），
  权限违规可回溯——这是单 agent 全权限混合体做不到的审计粒度
- 生产化演进：本地 JSONL → 按天分文件 → 采集进 ELK/Loki，按 agent 域建索引
"""
import json
import os
import time

LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logs")
LOG_PATH = os.path.join(LOG_DIR, "audit.jsonl")


def log(agent, action, detail="", status="ok", latency_ms=None, extra=None):
    rec = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "agent": agent,          # supervisor / sql / analysis / report / db-gate
        "action": action,        # task_start / sql_generate / sql_executed / sql_rejected / ...
        "status": status,        # ok / denied / error
    }
    if detail:
        rec["detail"] = detail
    if latency_ms is not None:
        rec["latency_ms"] = round(latency_ms, 1)
    if extra:
        rec.update(extra)
    os.makedirs(LOG_DIR, exist_ok=True)
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rec


def read_tail(n=20):
    """读取最近 n 条审计记录（CLI 展示用）。"""
    if not os.path.exists(LOG_PATH):
        return []
    with open(LOG_PATH, encoding="utf-8") as f:
        lines = f.readlines()
    return [json.loads(l) for l in lines[-n:]]
