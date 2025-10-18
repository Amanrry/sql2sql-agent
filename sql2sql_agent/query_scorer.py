#!/usr/bin/env python3
"""
查询评分模块
提供查询相关性评分和排序功能
"""
import json
from typing import List, Tuple, Dict, Any
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from langchain_openai import OpenAIEmbeddings, ChatOpenAI

from config import config
from state import QueryResult


async def score_and_rank_queries(
    original_query: str,
    intent: dict,
    derived_queries: List[str],
    context: List[QueryResult]
) -> List[Tuple[str, float, str]]:
    """
    自适应查询评分和排序

    策略：
    - 查询数 <= 5：直接用LLM评分（精准但慢）
    - 查询数 > 5：先用嵌入向量筛选Top-5，再LLM评分（快速且精准）

    Args:
        original_query: 原始用户查询
        intent: 用户意图信息
        derived_queries: 待评分的衍生查询列表
        context: 已执行的查询结果上下文

    Returns:
        List[(query, score, reasoning)]: 排序后的查询列表，包含评分和理由
    """
    if not derived_queries:
        return []

    # 去重：移除与已执行查询过于相似的
    filtered_queries = _remove_duplicates(derived_queries, context)

    if not filtered_queries:
        print("⚠️  所有衍生查询都与已执行查询重复")
        return []

    print(f"📊 评分模式: ", end="")

    # 自适应策略
    if len(filtered_queries) <= config.ADAPTIVE_SCORING_THRESHOLD:
        # 直接用LLM评分
        print(f"直接LLM评分 (查询数={len(filtered_queries)})")
        scored_results = await _llm_score_batch(
            original_query, intent, filtered_queries, context
        )
    else:
        # 两阶段评分：嵌入向量 + LLM
        print(f"两阶段评分 (查询数={len(filtered_queries)})")

        # 阶段1：嵌入向量快速筛选
        embedding_scores = await _embedding_score_batch(
            original_query, intent, filtered_queries
        )

        # 选择Top-5进入LLM评分
        top_k = min(5, len(filtered_queries))
        candidates = sorted(
            zip(filtered_queries, embedding_scores),
            key=lambda x: x[1],
            reverse=True
        )[:top_k]

        candidate_queries = [q for q, _ in candidates]
        candidate_emb_scores = [s for _, s in candidates]

        print(f"   阶段1: 嵌入向量筛选到Top-{top_k}")

        # 阶段2：LLM精细评分
        llm_results = await _llm_score_batch(
            original_query, intent, candidate_queries, context
        )

        # 综合得分：嵌入30% + LLM70%
        scored_results = []
        for i, (query, llm_score, reasoning) in enumerate(llm_results):
            combined_score = 0.3 * candidate_emb_scores[i] + 0.7 * llm_score
            scored_results.append((query, combined_score, reasoning))

        print(f"   阶段2: LLM精细评分完成")

    # 排序
    scored_results.sort(key=lambda x: x[1], reverse=True)

    return scored_results


async def _embedding_score_batch(
    original_query: str,
    intent: dict,
    queries: List[str]
) -> List[float]:
    """
    使用嵌入向量批量评分

    Args:
        original_query: 原始查询
        intent: 用户意图
        queries: 待评分查询列表

    Returns:
        List[float]: 每个查询的相似度分数 (0-1)
    """
    embeddings = OpenAIEmbeddings(
        openai_api_base=config.EMBEDDING_API_BASE,
        openai_api_key=config.EMBEDDING_API_KEY,
        model=config.EMBEDDING_MODEL
    )

    # 构建增强的意图表示
    intent_text = f"""
    Query: {original_query}
    Goal: {intent.get('goal', '')}
    Focus: {', '.join(intent.get('focus_areas', []))}
    Purpose: {intent.get('purpose', '')}
    """

    # 批量嵌入
    all_texts = [intent_text] + queries
    try:
        all_embeddings = await embeddings.aembed_documents(all_texts)
    except Exception as e:
        print(f"⚠️  嵌入向量计算失败: {e}，使用默认分数")
        return [0.5] * len(queries)

    # 计算余弦相似度
    intent_emb = np.array(all_embeddings[0]).reshape(1, -1)
    query_embs = np.array(all_embeddings[1:])

    similarities = cosine_similarity(intent_emb, query_embs)[0]

    # 归一化到0-1
    scores = (similarities + 1) / 2  # cosine范围[-1,1]转到[0,1]

    return scores.tolist()


async def _llm_score_batch(
    original_query: str,
    intent: dict,
    queries: List[str],
    context: List[QueryResult]
) -> List[Tuple[str, float, str]]:
    """
    使用LLM批量评分查询

    Args:
        original_query: 原始查询
        intent: 用户意图
        queries: 待评分查询列表
        context: 已执行的查询结果

    Returns:
        List[(query, score, reasoning)]: 查询及其评分和理由
    """
    llm = ChatOpenAI(
        openai_api_base=config.OPENROUTER_API_BASE,
        openai_api_key=config.OPENROUTER_API_KEY,
        model_name=config.LLM_MODEL,
        temperature=0
    )

    # 格式化上下文
    context_summary = _format_context(context)

    # 构建评分prompt
    queries_text = "\n".join([f"{i+1}. {q}" for i, q in enumerate(queries)])

    prompt = f"""You are a query relevance evaluator for medical data analysis.

**Original Query**: {original_query}

**User Intent**:
- Goal: {intent.get('goal', 'Not specified')}
- Purpose: {intent.get('purpose', 'Not specified')}
- Focus Areas: {', '.join(intent.get('focus_areas', []))}
- Constraints: {', '.join(intent.get('constraints', []))}

**Candidate Derived Queries**:
{queries_text}

**Previous Results**:
{context_summary}

Evaluate each derived query's relevance on a scale of 0.0-1.0:
- 0.9-1.0: Highly relevant, directly addresses the goal
- 0.7-0.8: Relevant, provides valuable insights
- 0.5-0.6: Somewhat relevant, indirect value
- 0.0-0.4: Not relevant or redundant

Consider:
1. Alignment with user's goal and focus areas
2. Novelty compared to previous results
3. Potential for actionable insights
4. Avoidance of redundancy

Return JSON array with one entry per query:
[
  {{
    "query_number": 1,
    "score": 0.0-1.0,
    "reasoning": "Brief explanation"
  }},
  ...
]
"""

    try:
        response = await llm.ainvoke([{"role": "user", "content": prompt}])
        result_text = response.content

        # 解析JSON
        if "```json" in result_text:
            json_start = result_text.find("```json") + 7
            json_end = result_text.find("```", json_start)
            json_str = result_text[json_start:json_end].strip()
        elif "[" in result_text and "]" in result_text:
            json_start = result_text.find("[")
            json_end = result_text.rfind("]") + 1
            json_str = result_text[json_start:json_end]
        else:
            raise ValueError("未找到JSON格式")

        evaluations = json.loads(json_str)

        # 构建结果
        results = []
        for i, query in enumerate(queries):
            eval_data = evaluations[i] if i < len(evaluations) else {}
            score = eval_data.get("score", 0.5)
            reasoning = eval_data.get("reasoning", "No reasoning provided")
            results.append((query, score, reasoning))

        return results

    except Exception as e:
        print(f"⚠️  LLM评分失败: {e}，使用默认分数")
        # 返回默认分数
        return [(q, 0.5, "评分失败") for q in queries]


def _remove_duplicates(
    queries: List[str],
    context: List[QueryResult]
) -> List[str]:
    """
    移除与已执行查询重复的衍生查询

    Args:
        queries: 待检查的查询列表
        context: 已执行的查询结果

    Returns:
        List[str]: 去重后的查询列表
    """
    if not context:
        return queries

    # 提取已执行的查询
    executed_queries = [r['query'] for r in context]

    filtered = []
    for query in queries:
        query_words = set(query.lower().split())

        # 检查与已执行查询的相似度
        is_duplicate = False
        for executed in executed_queries:
            executed_words = set(executed.lower().split())

            # 计算词汇重叠率
            if len(query_words) == 0:
                continue
            overlap = len(query_words & executed_words) / len(query_words)

            if overlap > config.SIMILARITY_THRESHOLD:
                is_duplicate = True
                break

        if not is_duplicate:
            filtered.append(query)

    if len(filtered) < len(queries):
        removed = len(queries) - len(filtered)
        print(f"🗑️  去重：移除了 {removed} 个重复查询")

    return filtered


def _format_context(context: List[QueryResult]) -> str:
    """
    格式化上下文信息供LLM使用

    Args:
        context: 查询结果列表

    Returns:
        str: 格式化的上下文摘要
    """
    if not context:
        return "No previous results yet."

    # 只显示最近3个结果
    recent = context[-3:]

    summary = []
    for i, result in enumerate(recent, 1):
        status = result['status']
        query = result['query']

        if status == 'success':
            insight = result.get('insight', '')[:100]  # 截取前100字符
            summary.append(f"{i}. ✅ {query}\n   Insight: {insight}")
        else:
            summary.append(f"{i}. ❌ {query} (Failed)")

    return "\n".join(summary)


if __name__ == "__main__":
    import asyncio
    from state import QueryResult

    async def test():
        print("🧪 测试查询评分模块")
        print("="*60)

        # 测试数据
        original_query = "统计急性心肌梗死患者的平均住院天数"
        intent = {
            "goal": "优化治疗效率，降低住院成本",
            "purpose": "识别可以缩短住院时间的因素",
            "focus_areas": ["科室效率", "治疗方案", "患者特征"],
            "constraints": ["急性心肌梗死患者"]
        }

        derived_queries = [
            "按科室分组统计急性心肌梗死患者的平均住院天数",
            "分析不同年龄段心肌梗死患者的住院时长差异",
            "统计心肌梗死患者的常用药物处方",
            "对比不同治疗方案的住院时长",
            "分析住院时长与患者合并症的关系",
            "统计心肌梗死患者的ICU使用情况",
            "分析不同入院时间段的住院时长差异"
        ]

        context = [
            QueryResult(
                query="统计急性心肌梗死患者总数",
                sql="SELECT COUNT(*) FROM ...",
                result=[{"count": 150}],
                insight="数据库中有150名心肌梗死患者",
                status="success"
            )
        ]

        # 测试评分
        results = await score_and_rank_queries(
            original_query, intent, derived_queries, context
        )

        print(f"\n📋 评分结果 (Top-3):")
        for i, (query, score, reasoning) in enumerate(results[:3], 1):
            print(f"\n{i}. [{score:.3f}] {query}")
            print(f"   理由: {reasoning}")

    asyncio.run(test())
