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
from state import QueryResult, Intent, filter_valid_results, format_all_results
from prompts import format_planning_prompt
from query_scorer import score_and_rank_queries


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


async def understand_user_intent(query: str, tools) -> Intent:
    """
    理解用户查询意图

    分析用户的医学查询，提取：
    - 核心目标：用户想要达成什么
    - 分析目的：为什么需要这个分析
    - 关注领域：应该优先关注哪些方面
    - 约束条件：有哪些特定条件或限制

    Args:
        query: 用户的原始查询
        tools: 工具列表

    Returns:
        Intent: 用户意图信息
    """
    print(f"\n🎯 分析用户意图...")

    llm = ChatOpenAI(
        openai_api_base=config.OPENROUTER_API_BASE,
        openai_api_key=config.OPENROUTER_API_KEY,
        model_name=config.LLM_MODEL,
        temperature=0
    )

    prompt = f"""Analyze the following medical query and extract user intent.

**Query**: {query}

Please analyze and return JSON:
{{
  "goal": "Primary goal: What outcome does the user want to achieve?",
  "purpose": "Analysis purpose: Why is this analysis needed? (e.g., cost reduction, quality improvement, risk assessment)",
  "focus_areas": ["Area1", "Area2", "Area3"],
  "constraints": ["Constraint1", "Constraint2"]
}}

**Examples**:

Query: "Calculate average length of stay for acute MI patients"
{{
  "goal": "Understand hospitalization duration for acute MI patients",
  "purpose": "Identify opportunities to reduce length of stay and costs",
  "focus_areas": ["treatment efficiency", "department comparison", "patient characteristics"],
  "constraints": ["acute myocardial infarction patients"]
}}

Query: "Analyze ICU patient outcomes"
{{
  "goal": "Assess ICU treatment effectiveness",
  "purpose": "Improve patient outcomes and resource allocation",
  "focus_areas": ["mortality rates", "ICU length of stay", "readmission rates"],
  "constraints": ["ICU patients"]
}}

Now analyze the user's query and return JSON only.
"""

    try:
        response = await llm.ainvoke([{"role": "user", "content": prompt}])
        result_text = response.content

        # 解析JSON
        if "```json" in result_text:
            json_start = result_text.find("```json") + 7
            json_end = result_text.find("```", json_start)
            json_str = result_text[json_start:json_end].strip()
        elif "{" in result_text and "}" in result_text:
            json_start = result_text.find("{")
            json_end = result_text.rfind("}") + 1
            json_str = result_text[json_start:json_end]
        else:
            raise ValueError("未找到JSON格式")

        data = json.loads(json_str)

        intent = Intent(
            goal=data.get("goal", ""),
            purpose=data.get("purpose", ""),
            focus_areas=data.get("focus_areas", []),
            constraints=data.get("constraints", [])
        )

        print(f"✅ 意图分析完成:")
        print(f"   目标: {intent['goal']}")
        print(f"   目的: {intent['purpose']}")
        print(f"   关注领域: {', '.join(intent['focus_areas'])}")
        if intent['constraints']:
            print(f"   约束条件: {', '.join(intent['constraints'])}")

        return intent

    except Exception as e:
        print(f"⚠️  意图分析失败: {e}，使用默认意图")
        # 返回默认意图
        return Intent(
            goal=f"Analyze: {query}",
            purpose="Data exploration and analysis",
            focus_areas=["general analysis"],
            constraints=[]
        )


async def generate_and_score_queries(
    original_query: str,
    intent: Intent,
    all_results: List[QueryResult],
    iteration: int,
    max_iterations: int,
    tools
) -> List[str]:
    """
    生成衍生查询并进行评分排序

    Args:
        original_query: 原始用户查询
        intent: 用户意图信息
        all_results: 所有已执行的查询结果
        iteration: 当前迭代次数
        max_iterations: 最大迭代次数
        tools: 工具列表

    Returns:
        List[str]: 评分后的Top-3查询列表
    """
    # 1. 生成原始衍生查询
    raw_queries = await generate_extended_queries(
        all_results, iteration, max_iterations, tools
    )

    if not raw_queries:
        print("⚠️  未生成任何衍生查询")
        return []

    # 2. 评分和排序
    print(f"\n📊 对 {len(raw_queries)} 个衍生查询进行评分...")
    scored_queries = await score_and_rank_queries(
        original_query, intent, raw_queries, all_results
    )

    if not scored_queries:
        print("⚠️  评分后无有效查询")
        return []

    # 3. 过滤低分查询并返回Top-3
    # 过滤掉评分过低的查询
    qualified_queries = [
        (query, score, reasoning)
        for query, score, reasoning in scored_queries
        if score >= config.MIN_SCORE_THRESHOLD
    ]

    if not qualified_queries:
        print(f"⚠️  所有查询评分都低于阈值 {config.MIN_SCORE_THRESHOLD}，停止生成衍生查询")
        print("   这表明生成的查询与原始意图不相关，应该结束迭代")
        return []

    # 取前3个合格的查询（可能少于3个）
    top_queries = [query for query, score, reasoning in qualified_queries[:3]]

    print(f"\n✅ 选择Top-{len(top_queries)}查询执行:")
    for i, (query, score, reasoning) in enumerate(qualified_queries[:3], 1):
        print(f"  {i}. [{score:.3f}] {query}")
        print(f"     理由: {reasoning}")

    if len(top_queries) < 3:
        print(f"ℹ️  注意：只有 {len(top_queries)} 个查询达到评分标准")

    return top_queries


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
    prompt += "\n\nPlease generate 3-5 derivative queries and return in JSON format: {\"extended_queries\": [...], \"reasoning\": \"...\"}"

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
    intent: Intent,
    tools
) -> bool:
    """
    判断是否应该继续迭代（智能停止条件）

    Args:
        all_results: 所有结果
        iteration: 当前迭代次数
        max_iterations: 最大迭代次数
        intent: 用户意图
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

    # 新增：新颖性检测
    if len(all_results) >= 6:  # 至少需要6个结果才能比较新颖性
        novelty_score = await _calculate_novelty(all_results)
        if novelty_score < config.NOVELTY_THRESHOLD:
            print(f"⏹️  新发现减少 (novelty={novelty_score:.3f} < {config.NOVELTY_THRESHOLD})，停止迭代")
            return False

    # 新增：目标完成度评估
    if len(valid_results) >= 3:  # 至少需要3个有效结果
        completion = await _assess_goal_completion(all_results, intent, tools)
        if completion > 0.8:
            print(f"✅ 目标已基本完成 (completion={completion:.3f})，停止迭代")
            return False

    print(f"✅ 继续迭代 (当前 {iteration}/{max_iterations})")
    return True


async def _calculate_novelty(all_results: List[QueryResult]) -> float:
    """
    计算最近结果的新颖性

    比较最近3个结果与之前结果的差异度

    Args:
        all_results: 所有查询结果

    Returns:
        float: 新颖性分数 (0-1)，1表示完全新颖
    """
    if len(all_results) < 6:
        return 1.0  # 结果少时认为是新颖的

    # 提取最近3个和历史结果的查询文本
    recent = all_results[-3:]
    historical = all_results[:-3]

    # 修复：正确的set嵌套理解语法
    recent_queries = [set(r['query'].lower().split()) for r in recent]
    historical_queries = [set(r['query'].lower().split()) for r in historical]

    # 计算词汇新颖性
    novelty_scores = []
    for recent_words in recent_queries:
        max_overlap = 0
        for hist_words in historical_queries:
            if len(recent_words) > 0:
                overlap = len(recent_words & hist_words) / len(recent_words)
                max_overlap = max(max_overlap, overlap)
        novelty = 1.0 - max_overlap
        novelty_scores.append(novelty)

    avg_novelty = sum(novelty_scores) / len(novelty_scores) if novelty_scores else 0.5
    print(f"   📊 新颖性评分: {avg_novelty:.3f}")
    return avg_novelty


async def _assess_goal_completion(
    all_results: List[QueryResult],
    intent: Intent,
    tools
) -> float:
    """
    评估用户目标的完成度

    Args:
        all_results: 所有查询结果
        intent: 用户意图
        tools: 工具列表

    Returns:
        float: 完成度分数 (0-1)，1表示完全完成
    """
    llm = ChatOpenAI(
        openai_api_base=config.OPENROUTER_API_BASE,
        openai_api_key=config.OPENROUTER_API_KEY,
        model_name=config.LLM_MODEL,
        temperature=0
    )

    # 格式化已有结果
    valid_results = filter_valid_results(all_results)
    results_summary = "\n".join([
        f"- {r['query']}: {r['insight'][:100]}"
        for r in valid_results[:5]  # 只展示前5个
    ])

    prompt = f"""Evaluate whether the following analysis results adequately address the user's goal.

**User Intent**:
- Goal: {intent['goal']}
- Purpose: {intent['purpose']}
- Focus Areas: {', '.join(intent['focus_areas'])}
- Constraints: {', '.join(intent['constraints'])}

**Analysis Results**:
{results_summary}

Rate the goal completion on a scale of 0.0-1.0:
- 0.9-1.0: Goal fully achieved, all focus areas covered
- 0.7-0.8: Most aspects addressed, minor gaps remain
- 0.5-0.6: Partially addressed, significant gaps
- 0.0-0.4: Goal not adequately addressed

Return JSON: {{"completion": 0.0-1.0, "reasoning": "Brief explanation"}}
"""

    try:
        response = await llm.ainvoke([{"role": "user", "content": prompt}])
        result_text = response.content

        # 解析JSON
        if "```json" in result_text:
            json_start = result_text.find("```json") + 7
            json_end = result_text.find("```", json_start)
            json_str = result_text[json_start:json_end].strip()
        elif "{" in result_text and "}" in result_text:
            json_start = result_text.find("{")
            json_end = result_text.rfind("}") + 1
            json_str = result_text[json_start:json_end]
        else:
            raise ValueError("未找到JSON格式")

        data = json.loads(json_str)
        completion = data.get("completion", 0.5)
        reasoning = data.get("reasoning", "")

        print(f"   📊 目标完成度: {completion:.3f} - {reasoning}")
        return completion

    except Exception as e:
        print(f"   ⚠️  完成度评估失败: {e}，返回默认值")
        return 0.5  # 默认返回中等完成度，继续迭代


async def should_continue_legacy(
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
    prompt = f"""Based on all query results below, generate a comprehensive medical data analysis report.

{results_summary}

Please generate a report in JSON format:
{{
  "report": "Comprehensive analysis report content...",
  "key_findings": ["Finding 1", "Finding 2", "Finding 3"],
  "recommendations": ["Recommendation 1", "Recommendation 2"]
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

            # Format report
            report = "# Medical Data Analysis Report\n\n"
            report += "## Comprehensive Analysis\n"
            report += data.get("report", "") + "\n\n"

            if "key_findings" in data and data["key_findings"]:
                report += "## Key Findings\n"
                for i, finding in enumerate(data["key_findings"], 1):
                    report += f"{i}. {finding}\n"
                report += "\n"

            if "recommendations" in data and data["recommendations"]:
                report += "## Recommendations\n"
                for i, rec in enumerate(data["recommendations"], 1):
                    report += f"{i}. {rec}\n"
                report += "\n"

            report += "## Detailed Query Results\n"
            report += results_summary

            print("✅ 报告生成完成")
            return report

        except (json.JSONDecodeError, ValueError, KeyError) as e:
            print(f"⚠️  解析JSON失败，使用原始响应: {e}")
            report = "# Medical Data Analysis Report\n\n"
            report += final_message + "\n\n"
            report += "## Detailed Query Results\n"
            report += results_summary
            return report

    except Exception as e:
        print(f"❌ 生成报告失败: {e}")
        return f"Report generation failed: {str(e)}\n\n{results_summary}"


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
