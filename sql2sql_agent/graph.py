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
from planning_agent import generate_extended_queries, should_continue, generate_final_report


async def build_graph(tools):
    """
    构建SQL-to-SQL多智能体系统的LangGraph

    执行流程：
    1. 初始化 → 2. 执行初始查询 → 3. 生成衍生查询
    → 4. 执行衍生查询 → 5. 聚合结果 → 6. 检查完成
    → 7a. 如未完成，返回步骤3
    → 7b. 如已完成，生成最终报告
    """

    # 创建状态图
    workflow = StateGraph(AgentState)

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

    # 节点2: 生成衍生查询
    async def generate_extended_queries_node(state: AgentState) -> dict:
        """生成衍生查询"""
        print("\n" + "="*60)
        print(f"📍 节点2: 生成衍生查询 (迭代 {state['iteration']})")
        print("="*60)

        queries = await generate_extended_queries(
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

    # 节点4: 聚合结果并检查是否完成
    async def check_completion_node(state: AgentState) -> dict:
        """检查是否应该继续迭代"""
        print("\n" + "="*60)
        print("📍 节点4: 检查完成状态")
        print("="*60)

        continue_iteration = await should_continue(
            state["all_results"],
            state["iteration"],
            state["max_iterations"],
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
    workflow.add_node("execute_initial", execute_initial_query_node)
    workflow.add_node("generate_extended", generate_extended_queries_node)
    workflow.add_node("execute_extended", execute_extended_queries_node)
    workflow.add_node("check_completion", check_completion_node)
    workflow.add_node("generate_report", generate_report_node)

    # 定义边
    workflow.add_edge(START, "execute_initial")
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
