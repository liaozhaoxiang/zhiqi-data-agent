"""配置与模型分工计划。

单 agent 只能绑定一个模型，而 SQL / 归因 / 报告三类子任务的最优模型档位不同——
MODEL_PLAN 显式声明这种异构性，是拆多 agent 的第一性原因之一。
"""
import os

# 每个子角色的模型档位（接真实 API 时生效；mock 模式下仅作声明）
MODEL_PLAN = {
    "sql":      {"role": "code",    "note": "生产环境: LoRA 微调的 CodeQwen-7B（企业 schema+查询日志微调）"},
    "analysis": {"role": "reasoning", "note": "生产环境: 大参数通用推理模型"},
    "report":   {"role": "balanced", "note": "生产环境: 中档模型，格式遵循+文笔优先"},
    "supervisor": {"role": "reasoning", "note": "主管复用推理档"},
}

API_KEY = os.environ.get("ZHIQI_API_KEY", "")
BASE_URL = os.environ.get("ZHIQI_BASE_URL", "https://api.deepseek.com/v1")
MODEL = os.environ.get("ZHIQI_MODEL", "deepseek-chat")

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "enterprise.db")
