#!/usr/bin/env python3
"""
Execute SubAgent实现
负责将自然语言查询转换为SQL并执行
"""
import json
from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent

from config import config
from state import QueryResult
from prompts import format_execute_prompt


def create_execute_agent(tools):
    """创建Execute SubAgent"""
    llm = ChatOpenAI(
        openai_api_base=config.OPENROUTER_API_BASE,
        openai_api_key=config.OPENROUTER_API_KEY,
        model_name=config.LLM_MODEL,
        temperature=config.LLM_TEMPERATURE
    )

    agent = create_react_agent(llm, tools)
    return agent


async def execute_query(query: str, tools, max_retries: int = None) -> QueryResult:
    """
    执行单个查询

    Args:
        query: 自然语言查询
        tools: 工具列表
        max_retries: 最大重试次数

    Returns:
        QueryResult: 查询结果
    """
    if max_retries is None:
        max_retries = config.MAX_SQL_RETRIES

    agent = create_execute_agent(tools)
    prompt = format_execute_prompt(query)

    try:
        print(f"\n🔍 执行查询: {query}")

        # 设置recursion_limit以支持复杂查询（ReAct循环可能需要多次工具调用）
        response = await agent.ainvoke(
            {"messages": [{"role": "user", "content": prompt}]},
            config={"recursion_limit": config.AGENT_RECURSION_LIMIT}
        )

        # 提取agent的最终回复
        final_message = response['messages'][-1].content
        print(f"📝 Agent响应: {final_message[:200]}...")

        # 尝试解析JSON结果
        try:
            # 查找JSON部分
            if "```json" in final_message:
                json_start = final_message.find("```json") + 7
                json_end = final_message.find("```", json_start)
                json_str = final_message[json_start:json_end].strip()
            elif "{" in final_message and "}" in final_message:
                json_start = final_message.find("{")
                json_end = final_message.rfind("}") + 1
                json_str = final_message[json_start:json_end]
            else:
                raise ValueError("未找到JSON格式的结果")

            result_data = json.loads(json_str)

            # 构建QueryResult
            result = QueryResult(
                query=result_data.get("query", query),
                sql=result_data.get("sql", ""),
                result=result_data.get("result"),
                insight=result_data.get("insight", ""),
                status=result_data.get("status", "success")
            )

            print(f"✅ 查询成功: {result['status']}")
            return result

        except (json.JSONDecodeError, ValueError, KeyError) as e:
            print(f"⚠️  解析JSON失败: {e}")

            # 如果解析失败，让LLM重新生成正确的JSON格式
            retry_result = await _retry_with_json_format(query, final_message, agent)
            if retry_result:
                return retry_result

            # 如果重试也失败，返回基于原始响应的结果
            return QueryResult(
                query=query,
                sql="",
                result=final_message,
                insight=final_message,
                status="success" if "成功" in final_message or "结果" in final_message else "failed"
            )

    except Exception as e:
        print(f"❌ 查询执行失败: {e}")
        return QueryResult(
            query=query,
            sql="",
            result=None,
            insight=f"执行失败: {str(e)}",
            status="failed"
        )


async def execute_batch_queries(queries: list[str], tools) -> list[QueryResult]:
    """
    批量并行执行多个查询

    Args:
        queries: 查询列表
        tools: 工具列表

    Returns:
        List[QueryResult]: 结果列表
    """
    import asyncio

    tasks = [execute_query(q, tools) for q in queries]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # 处理可能的异常
    processed_results = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            processed_results.append(QueryResult(
                query=queries[i],
                sql="",
                result=None,
                insight=f"执行异常: {str(result)}",
                status="failed"
            ))
        else:
            processed_results.append(result)

    return processed_results


async def _retry_with_json_format(query: str, original_response: str, agent) -> QueryResult:
    """
    当JSON解析失败时，让LLM重新生成正确的JSON格式

    Args:
        query: 原始查询
        original_response: 原始响应
        agent: Execute Agent实例

    Returns:
        QueryResult: 重试后的结果，失败时返回None
    """
    try:
        print("🔄 尝试重新生成JSON格式...")

        retry_prompt = f"""The previous response did not follow the required JSON format. Please convert the following analysis into proper JSON format.

**Original Query**: {query}

**Previous Response**:
{original_response}

Please return the result in this exact JSON format:
```json
{{
  "query": "{query}",
  "sql": "SQL statement used (or empty string)",
  "result": "The actual data result (can be list, dict, or summary)",
  "insight": "Key insights and medical interpretation from the analysis",
  "status": "success"
}}
```

Important:
- Make sure the JSON is valid and properly formatted
- Include the key findings from your analysis
- Keep the insight concise but informative
- Return ONLY the JSON response
"""

        retry_response = await agent.ainvoke(
            {"messages": [{"role": "user", "content": retry_prompt}]},
            config={"recursion_limit": config.AGENT_RECURSION_LIMIT}
        )

        retry_message = retry_response['messages'][-1].content
        print(f"📝 重试响应: {retry_message[:200]}...")

        # 解析重试的JSON
        if "```json" in retry_message:
            json_start = retry_message.find("```json") + 7
            json_end = retry_message.find("```", json_start)
            json_str = retry_message[json_start:json_end].strip()
        elif "{" in retry_message and "}" in retry_message:
            json_start = retry_message.find("{")
            json_end = retry_message.rfind("}") + 1
            json_str = retry_message[json_start:json_end]
        else:
            print("❌ 重试响应仍无JSON格式")
            return None

        result_data = json.loads(json_str)

        result = QueryResult(
            query=result_data.get("query", query),
            sql=result_data.get("sql", ""),
            result=result_data.get("result"),
            insight=result_data.get("insight", ""),
            status=result_data.get("status", "success")
        )

        print("✅ JSON重试成功")
        return result

    except Exception as e:
        print(f"❌ JSON重试失败: {e}")
        return None


if __name__ == "__main__":
    import asyncio
    from tools import get_all_tools

    async def test():
        print("🧪 测试Execute SubAgent")
        print("="*60)

        tools = await get_all_tools()
        print(f"✅ 获取到 {len(tools)} 个工具\n")

        # 测试单个查询
        test_query = "查询patients表的前5行数据"
        result = await execute_query(test_query, tools)

        print("\n📊 查询结果:")
        print(f"  查询: {result['query']}")
        print(f"  SQL: {result['sql']}")
        print(f"  状态: {result['status']}")
        print(f"  洞察: {result['insight'][:100]}...")

    asyncio.run(test())
