# 智析 zhiqi-data-agent

企业数据智能分析多 Agent 系统（面试演示版）。复杂度路由 + 主管 Agent + 三个专职子 Agent（SQL / 归因分析 / 报告），演示三大生产约束下的多 Agent 架构：

1. **上下文物隔离**：子 Agent 各自持有独立上下文，主管只消费结构化摘要（`AgentResult.summary`）。
2. **模型异构**：`app/llm.py` 的适配层按 agent 角色路由到不同模型档位（mock 模式下统一走确定性模板，接真实 API 时按 `MODEL_PLAN` 分流——SQL 走代码模型、归因走推理模型、报告走中档模型）。
3. **权限隔离**：SQL Agent 只能拿到 SQLite 只读连接（`mode=ro`），且 SQL 校验层只放行单条 `SELECT`；分析/报告 Agent 拿不到任何 DB 句柄。

## 架构

```
                        ┌────────────────────────────┐
   用户问题 ──► 复杂度路由 ─┤ 简单取数：快速通道(单agent) │──► 直接结果
                        └─────────────┬──────────────┘
                                      │ 复杂（多源归因/并行子问题）
                                      ▼
                        ┌────────────────────────────┐
                        │   Supervisor（主管 Agent）  │  共享状态: AnalysisState
                        │  任务拆解 → Send 式并行分发 │
                        └──┬──────────┬──────────┬───┘
                           ▼          ▼          ▼
                     SQL Agent   归因 Agent   (按子问题动态 fan-out)
                     (只读DB+     (对比归因,
                      校验重试)    补充查询循环)
                           └──────────┴──────────┘
                                      ▼ 结构化摘要回写
                        ┌────────────────────────────┐
                        │      Report Agent          │
                        └────────────────────────────┘
```

## 快速开始

```bash
# mock 模式（默认，无需任何 API key）
python main.py "上个月华东大区销售额为什么下滑？和投放、库存各有什么关系？"
python main.py "上个月总销售额是多少"

# 接真实模型（OpenAI 兼容接口）
set ZHIQI_API_KEY=sk-xxx
set ZHIQI_BASE_URL=https://api.deepseek.com/v1
set ZHIQI_MODEL=deepseek-chat
python main.py "..."
```

## 评测

```bash
python eval/run_eval.py    # SQL Agent 准确率，mock 模式下 20/20
```

## 目录

```
app/
  router.py        复杂度路由（规则分：简单取数走快速通道）
  graph.py         轻量状态图编排（生产版可平移到 LangGraph：StateGraph + Send API）
  llm.py           模型适配层（mock / OpenAI 兼容，按 agent 角色选模型档）
  db.py            演示数仓（SQLite），只读连接 + SQL 白名单校验
  agents/
    supervisor.py  主管：拆解子问题 → 并行分发 → 汇总摘要
    sql_agent.py   SQL 生成 + 执行 + schema 修正重试循环
    analysis_agent.py  归因分析（维度对比、最大差异因子、补充查询循环）
    report_agent.py    报告生成（消费摘要，无 DB 权限）
eval/run_eval.py   SQL 准确率回归
```

## 数据来源

`app/db.py` 内置确定性生成器：3 张业务表（销售流水 / 投放花费 / 库存快照），覆盖华东等 4 大区、12 个月，华东近三月投放削减 + 库存积压用于归因演示。

> 本仓库为面试演示用途的最小可运行实现；生产化要点（LangGraph Send API 并行、按 agent 的独立评测集、审计日志分域）见 README 上方架构说明。
