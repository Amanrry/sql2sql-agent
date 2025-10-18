#!/usr/bin/env python3
"""
LangGraph图定义
编排Planning Agent和Execute SubAgent的协作流程
"""
from typing import Literal
from langgraph.graph import StateGraph, START, END

from config import config
from state import AgentState, create_initial_state
from execute_agent import execute_query, execute_batch_queries
from planning_agent import (
    understand_user_intent,
    generate_and_score_queries,
    generate_extended_queries,
    should_continue,
    generate_final_report
)


async def build_graph(tools):
    """
    构建SQL-to-SQL多智能体系统的LangGraph（改进版）

    执行流程：
    0. 理解用户意图（新增）→ 1. 执行初始查询 → 2. 生成并评分衍生查询（改进）
    → 3. 执行衍生查询（并行） → 4. 检查完成（带新颖性和目标完成度检测）
    → 5a. 如未完成，返回步骤2
    → 5b. 如已完成，生成最终报告

    改进点：
    - 意图理解：提取用户核心目标、分析目的、关注领域
    - 自适应评分：根据查询数量选择评分策略（嵌入向量/LLM）
    - 智能停止：新颖性检测 + 目标完成度评估
    - 优先执行：只执行Top-3最相关查询
    """

    # 创建状态图
    workflow = StateGraph(AgentState)

    # 节点0: 理解用户意图（新增）
    async def understand_intent_node(state: AgentState) -> dict:
        """理解用户查询意图"""
        print("\n" + "="*60)
        print("📍 节点0: 理解用户意图")
        print("="*60)

        intent = await understand_user_intent(state["initial_query"], tools)

        return {
            "intent": intent
        }

    # 节点1: 执行初始查询
    async def execute_initial_query_node(state: AgentState) -> dict:
        """执行初始查询"""
        print("\n" + "="*60)
        print("📍 节点1: 执行初始查询")
        print("="*60)

        result = await execute_query(state["initial_query"], tools)

        return {
            "all_results": [result],
            "iteration": 1
        }

    # 节点2: 生成并评分衍生查询（改进）
    async def generate_extended_queries_node(state: AgentState) -> dict:
        """生成并评分衍生查询"""
        print("\n" + "="*60)
        print(f"📍 节点2: 生成并评分衍生查询 (迭代 {state['iteration']})")
        print("="*60)

        # 使用新的评分函数
        queries = await generate_and_score_queries(
            state["initial_query"],
            state["intent"],
            state["all_results"],
            state["iteration"],
            state["max_iterations"],
            tools
        )

        return {
            "pending_queries": queries
        }

    # 节点3: 执行衍生查询（并行）
    async def execute_extended_queries_node(state: AgentState) -> dict:
        """并行执行衍生查询"""
        print("\n" + "="*60)
        print(f"📍 节点3: 执行衍生查询 (共 {len(state['pending_queries'])} 个)")
        print("="*60)

        if not state["pending_queries"]:
            print("⚠️  没有待执行的查询")
            return {"all_results": []}

        results = await execute_batch_queries(state["pending_queries"], tools)

        return {
            "all_results": results,
            "pending_queries": []
        }

    # 节点4: 聚合结果并检查是否完成（改进）
    async def check_completion_node(state: AgentState) -> dict:
        """检查是否应该继续迭代（带智能停止条件）"""
        print("\n" + "="*60)
        print("📍 节点4: 检查完成状态")
        print("="*60)

        continue_iteration = await should_continue(
            state["all_results"],
            state["iteration"],
            state["max_iterations"],
            state["intent"],  # 新增：传入意图信息
            tools
        )

        if continue_iteration:
            # 继续迭代
            return {
                "iteration": state["iteration"] + 1,
                "is_completed": False
            }
        else:
            # 完成迭代
            return {
                "is_completed": True
            }

    # 节点5: 生成最终报告
    async def generate_report_node(state: AgentState) -> dict:
        """生成最终报告"""
        print("\n" + "="*60)
        print("📍 节点5: 生成最终报告")
        print("="*60)

        report = await generate_final_report(state["all_results"], tools)

        return {
            "final_report": report,
            "is_completed": True
        }

    # 添加节点
    workflow.add_node("understand_intent", understand_intent_node)  # 新增
    workflow.add_node("execute_initial", execute_initial_query_node)
    workflow.add_node("generate_extended", generate_extended_queries_node)
    workflow.add_node("execute_extended", execute_extended_queries_node)
    workflow.add_node("check_completion", check_completion_node)
    workflow.add_node("generate_report", generate_report_node)

    # 定义边
    workflow.add_edge(START, "understand_intent")  # 新增：首先理解意图
    workflow.add_edge("understand_intent", "execute_initial")  # 新增
    workflow.add_edge("execute_initial", "generate_extended")
    workflow.add_edge("generate_extended", "execute_extended")
    workflow.add_edge("execute_extended", "check_completion")

    # 条件边：根据是否完成决定下一步
    def route_after_check(state: AgentState) -> Literal["generate_extended", "generate_report"]:
        """路由函数：决定是继续迭代还是生成报告"""
        if state["is_completed"]:
            return "generate_report"
        else:
            return "generate_extended"

    workflow.add_conditional_edges(
        "check_completion",
        route_after_check,
        {
            "generate_extended": "generate_extended",
            "generate_report": "generate_report"
        }
    )

    workflow.add_edge("generate_report", END)

    # 编译图
    app = workflow.compile()

    return app


async def run_sql2sql_system(query: str, tools, max_iterations: int = None):
    """
    运行SQL-to-SQL多智能体系统

    Args:
        query: 初始查询
        tools: 工具列表
        max_iterations: 最大迭代次数

    Returns:
        最终状态
    """
    if max_iterations is None:
        max_iterations = config.MAX_ITERATIONS

    print(f"\n{'='*60}")
    print(f"🚀 启动SQL-to-SQL多智能体系统")
    print(f"{'='*60}")
    print(f"📝 初始查询: {query}")
    print(f"🔄 最大迭代次数: {max_iterations}")
    print(f"{'='*60}\n")

    # 构建图
    app = await build_graph(tools)

    # 创建初始状态
    initial_state = create_initial_state(query, max_iterations)

    # 执行图
    final_state = await app.ainvoke(initial_state)

    print(f"\n{'='*60}")
    print(f"✅ 系统执行完成")
    print(f"{'='*60}")
    print(f"📊 总查询数: {len(final_state['all_results'])}")
    print(f"🔄 迭代次数: {final_state['iteration']}")
    print(f"{'='*60}\n")

    return final_state


if __name__ == "__main__":
    import asyncio
    from tools import get_all_tools

    async def test():
        print("🧪 测试LangGraph图")

        tools = await get_all_tools()
        test_query = "统计患者总数"

        final_state = await run_sql2sql_system(test_query, tools, max_iterations=2)

        print("\n📄 最终报告:")
        print(final_state["final_report"])

    asyncio.run(test())
