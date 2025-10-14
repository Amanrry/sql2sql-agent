#!/usr/bin/env python3
"""
LangGraph状态定义
定义系统中使用的所有状态结构
"""
from typing import Any, List, Literal, TypedDict, Annotated
import operator


class QueryResult(TypedDict):
    """单个查询的执行结果"""
    query: str              # 原始查询
    sql: str                # 生成的SQL语句
    result: Any             # 执行结果（可能是list、dict或None）
    insight: str            # 数据洞察
    status: Literal["success", "failed", "empty"]  # 执行状态


class AgentState(TypedDict):
    """主系统状态"""
    # 输入
    initial_query: str                                      # 用户的初始查询

    # 迭代控制
    iteration: int                                          # 当前迭代次数
    max_iterations: int                                     # 最大迭代次数

    # 查询管理
    pending_queries: List[str]                              # 待执行的查询列表

    # 结果收集（使用operator.add作为reducer，自动累加）
    all_results: Annotated[List[QueryResult], operator.add]  # 所有查询结果

    # 最终输出
    final_report: str                                       # 最终医学报告
    is_completed: bool                                      # 是否完成


class ExecuteSubAgentInput(TypedDict):
    """Execute SubAgent的输入"""
    query: str              # 要执行的查询
    retry_count: int        # 当前重试次数


class PlanningContext(TypedDict):
    """Planning Agent的上下文信息"""
    current_results: List[QueryResult]      # 当前已有的结果
    iteration: int                          # 当前迭代次数
    max_iterations: int                     # 最大迭代次数


def create_initial_state(query: str, max_iterations: int = 3) -> AgentState:
    """创建初始状态"""
    return AgentState(
        initial_query=query,
        iteration=0,
        max_iterations=max_iterations,
        pending_queries=[],
        all_results=[],
        final_report="",
        is_completed=False
    )


def is_valid_result(result: QueryResult) -> bool:
    """判断结果是否有效"""
    return result["status"] == "success" and result["result"] is not None


def filter_valid_results(results: List[QueryResult]) -> List[QueryResult]:
    """筛选有效结果"""
    return [r for r in results if is_valid_result(r)]


def format_result_summary(result: QueryResult) -> str:
    """格式化单个结果摘要"""
    status_emoji = {
        "success": "✅",
        "failed": "❌",
        "empty": "⚠️"
    }
    emoji = status_emoji.get(result["status"], "❓")

    summary = f"{emoji} 查询: {result['query']}\n"
    summary += f"   SQL: {result['sql']}\n"

    if result["status"] == "success":
        summary += f"   洞察: {result['insight']}\n"
    else:
        summary += f"   状态: {result['status']}\n"

    return summary


def format_all_results(results: List[QueryResult]) -> str:
    """格式化所有结果"""
    if not results:
        return "暂无结果"

    output = "\n" + "="*60 + "\n"
    output += f"📊 共 {len(results)} 个查询结果\n"
    output += "="*60 + "\n\n"

    for idx, result in enumerate(results, 1):
        output += f"[结果 {idx}]\n"
        output += format_result_summary(result)
        output += "\n"

    return output


if __name__ == "__main__":
    # 测试状态创建
    state = create_initial_state("测试查询", max_iterations=3)
    print("初始状态:")
    print(state)

    # 测试结果过滤
    test_results = [
        QueryResult(
            query="查询1",
            sql="SELECT * FROM test",
            result=[{"id": 1}],
            insight="发现1条记录",
            status="success"
        ),
        QueryResult(
            query="查询2",
            sql="SELECT * FROM test2",
            result=None,
            insight="",
            status="failed"
        )
    ]

    valid = filter_valid_results(test_results)
    print(f"\n有效结果数: {len(valid)}")
    print(format_all_results(test_results))
