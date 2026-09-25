"""轻量状态图编排入口。

生产版可平移到 LangGraph：AnalysisState → StateGraph，
并行分发 → Send API（Map-Reduce），本文件的 graph() 保持同样的节点签名。
"""
from . import router
from .agents import supervisor


def graph(question):
    """入口：先路由，再选择执行拓扑。返回 (输出文本, 执行轨迹)。"""
    kind = router.classify(question)
    if kind == "simple":
        out, trace = router.fast_path(question)
        trace.insert(0, {"node": "router", "decision": "simple→快速通道(单agent)"})
        return out, trace
    report, st = supervisor.run(question)
    trace = [{"node": "router", "decision": "complex→多agent编排"}] + st["traces"]
    return report, trace
