"""CLI 入口：python main.py "问题"  （不带参数则跑内置演示）"""
import sys

from app.graph import graph as run_graph

DEMOS = [
    "上个月总销售额是多少",
    "2026-06 哪个region销售额最高",
    "上个月华东大区销售额为什么下滑？和投放、库存各有什么关系？",
]


def main():
    questions = sys.argv[1:] or DEMOS
    for q in questions:
        print("=" * 70)
        print("问题:", q)
        out, trace = run_graph(q)
        print("-" * 70)
        for t in trace:
            print("[trace]", t)
        print("-" * 70)
        print(out)
        print()


if __name__ == "__main__":
    main()
