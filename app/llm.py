"""LLM 适配层。

- mock 模式（默认）：返回 None，由各 Agent 走内置确定性逻辑，保证零依赖可跑。
- 配置 ZHIQI_API_KEY 后走 OpenAI 兼容接口（标准库 urllib，无第三方依赖）。
"""
import json
import urllib.request

from . import config


def chat(messages, role="supervisor", temperature=0.2):
    """按角色路由模型。返回文本或 None(mock)。"""
    plan = config.MODEL_PLAN.get(role, {})
    if not config.API_KEY:
        return None
    payload = json.dumps({
        "model": config.MODEL,
        "messages": messages,
        "temperature": temperature,
    }).encode("utf-8")
    req = urllib.request.Request(
        config.BASE_URL.rstrip("/") + "/chat/completions",
        data=payload,
        headers={"Content-Type": "application/json",
                 "Authorization": "Bearer " + config.API_KEY},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["choices"][0]["message"]["content"]
