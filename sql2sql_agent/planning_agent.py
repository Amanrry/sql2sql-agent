#!/usr/bin/env python3
"""
Planning Agent实现
负责任务规划、衍生查询生成、结果聚合和最终报告生成
"""
import json
from typing import List, Dict, Any
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

from config import config
from state import QueryResult, filter_valid_results, format_all_results
from prompts import format_planning_prompt


def create_planning_agent(tools):
    """创建Planning Agent"""
    llm = ChatOpenAI(
        openai_api_base=config.OPENROUTER_API_BASE,
        openai_api_key=config.OPENROUTER_API_KEY,
        model_name=config.LLM_MODEL,
        temperature=config.LLM_TEMPERATURE
    )

    agent = create_react_agent(llm, tools)
    return agent


async def generate_extended_queries(
    all_results: List[QueryResult],
    iteration: int,
    max_iterations: int,
    tools
) -> List[str]:
    """
    生成衍生查询

    Args:
        all_results: 所有已执行的查询结果
        iteration: 当前迭代次数
        max_iterations: 最大迭代次数
        tools: 工具列表（可能需要搜索）

    Returns:
        List[str]: 衍生查询列表
    """
    print(f"\n🎯 生成衍生查询 (迭代 {iteration}/{max_iterations})")

    # 过滤有效结果
    valid_results = filter_valid_results(all_results)
    results_summary = format_all_results(valid_results)

    agent = create_planning_agent(tools)
    prompt = format_planning_prompt(results_summary, iteration, max_iterations)
    prompt += "\n\n请生成3-5个衍生查询，以JSON格式返回：{\"extended_queries\": [...], \"reasoning\": \"...\"}"

    try:
        response = await agent.ainvoke(
            {"messages": [{"role": "user", "content": prompt}]},
            config={"recursion_limit": config.AGENT_RECURSION_LIMIT}
        )

        final_message = response['messages'][-1].content
        print(f"📝 Planning Agent响应: {final_message[:200]}...")

        # 解析JSON
        try:
            if "```json" in final_message:
                json_start = final_message.find("```json") + 7
                json_end = final_message.find("```", json_start)
                json_str = final_message[json_start:json_end].strip()
            elif "{" in final_message and "}" in final_message:
                json_start = final_message.find("{")
                json_end = final_message.rfind("}") + 1
                json_str = final_message[json_start:json_end]
            else:
                raise ValueError("未找到JSON格式")

            data = json.loads(json_str)
            queries = data.get("extended_queries", [])
            reasoning = data.get("reasoning", "")

            print(f"💡 推理: {reasoning}")
            print(f"📋 生成了 {len(queries)} 个衍生查询:")
            for i, q in enumerate(queries, 1):
                print(f"  {i}. {q}")

            return queries

        except (json.JSONDecodeError, ValueError, KeyError) as e:
            print(f"⚠️  解析JSON失败: {e}")
            # 尝试从文本中提取查询
            lines = final_message.split('\n')
            queries = []
            for line in lines:
                line = line.strip()
                if line and (line[0].isdigit() or line.startswith('-') or line.startswith('•')):
                    # 移除序号和标记
                    query = line.lstrip('0123456789.-• ')
                    if len(query) > 10:  # 过滤太短的行
                        queries.append(query)

            print(f"📋 从文本提取了 {len(queries)} 个查询")
            return queries[:5]  # 最多返回5个

    except Exception as e:
        print(f"❌ 生成衍生查询失败: {e}")
        return []


async def should_continue(
    all_results: List[QueryResult],
    iteration: int,
    max_iterations: int,
    tools
) -> bool:
    """
    判断是否应该继续迭代

    Args:
        all_results: 所有结果
        iteration: 当前迭代次数
        max_iterations: 最大迭代次数
        tools: 工具列表

    Returns:
        bool: 是否继续
    """
    # 达到最大迭代次数
    if iteration >= max_iterations:
        print(f"⏹️  已达到最大迭代次数 ({max_iterations})")
        return False

    # 如果没有有效结果，不继续
    valid_results = filter_valid_results(all_results)
    if not valid_results:
        print("⏹️  没有有效结果，停止迭代")
        return False

    # 如果最近的结果都失败了，不继续
    recent_results = all_results[-3:] if len(all_results) >= 3 else all_results
    recent_valid = filter_valid_results(recent_results)
    if not recent_valid:
        print("⏹️  最近的查询都失败了，停止迭代")
        return False

    print(f"✅ 继续迭代 (当前 {iteration}/{max_iterations})")
    return True


async def generate_final_report(
    all_results: List[QueryResult],
    tools
) -> str:
    """
    生成最终医学报告

    Args:
        all_results: 所有查询结果
        tools: 工具列表

    Returns:
        str: 最终报告
    """
    print(f"\n📄 生成最终报告")

    valid_results = filter_valid_results(all_results)
    results_summary = format_all_results(all_results)

    agent = create_planning_agent(tools)
    prompt = f"""基于以下所有查询结果，生成一份综合的医学数据分析报告。

{results_summary}

请生成JSON格式的报告：
{{
  "report": "综合分析报告...",
  "key_findings": ["发现1", "发现2", "发现3"],
  "recommendations": ["建议1", "建议2"]
}}"""

    try:
        response = await agent.ainvoke(
            {"messages": [{"role": "user", "content": prompt}]},
            config={"recursion_limit": config.AGENT_RECURSION_LIMIT}
        )

        final_message = response['messages'][-1].content

        # 解析JSON
        try:
            if "```json" in final_message:
                json_start = final_message.find("```json") + 7
                json_end = final_message.find("```", json_start)
                json_str = final_message[json_start:json_end].strip()
            elif "{" in final_message and "}" in final_message:
                json_start = final_message.find("{")
                json_end = final_message.rfind("}") + 1
                json_str = final_message[json_start:json_end]
            else:
                raise ValueError("未找到JSON格式")

            data = json.loads(json_str)

            # 格式化报告
            report = "# 医学数据分析报告\n\n"
            report += "## 综合分析\n"
            report += data.get("report", "") + "\n\n"

            if "key_findings" in data and data["key_findings"]:
                report += "## 关键发现\n"
                for i, finding in enumerate(data["key_findings"], 1):
                    report += f"{i}. {finding}\n"
                report += "\n"

            if "recommendations" in data and data["recommendations"]:
                report += "## 建议\n"
                for i, rec in enumerate(data["recommendations"], 1):
                    report += f"{i}. {rec}\n"
                report += "\n"

            report += "## 详细查询结果\n"
            report += results_summary

            print("✅ 报告生成完成")
            return report

        except (json.JSONDecodeError, ValueError, KeyError) as e:
            print(f"⚠️  解析JSON失败，使用原始响应: {e}")
            report = "# 医学数据分析报告\n\n"
            report += final_message + "\n\n"
            report += "## 详细查询结果\n"
            report += results_summary
            return report

    except Exception as e:
        print(f"❌ 生成报告失败: {e}")
        return f"报告生成失败: {str(e)}\n\n{results_summary}"


if __name__ == "__main__":
    import asyncio
    from tools import get_all_tools

    async def test():
        print("🧪 测试Planning Agent")
        print("="*60)

        tools = await get_all_tools()

        # 测试数据
        test_results = [
            QueryResult(
                query="查询患者总数",
                sql="SELECT COUNT(*) FROM patients",
                result=[{"count": 100}],
                insight="数据库中共有100名患者",
                status="success"
            )
        ]

        # 测试生成衍生查询
        queries = await generate_extended_queries(test_results, 1, 3, tools)
        print(f"\n生成的衍生查询: {queries}")

        # 测试生成报告
        report = await generate_final_report(test_results, tools)
        print(f"\n生成的报告:\n{report}")

    asyncio.run(test())
