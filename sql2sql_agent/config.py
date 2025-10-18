#!/usr/bin/env python3
"""
配置管理模块
从环境变量加载所有配置信息
"""
import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# 加载.env文件
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
else:
    print("⚠️  警告: .env文件不存在，请从.env.example复制并配置")


class Config:
    """配置类"""

    # OpenRouter API配置
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    OPENROUTER_API_BASE: str = os.getenv("OPENROUTER_API_BASE", "https://api.siliconflow.cn/v1")

    # LLM模型配置
    LLM_MODEL: str = os.getenv("LLM_MODEL", "deepseek-ai/DeepSeek-V3.2-Exp")
    LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.1"))

    # 嵌入模型配置
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
    EMBEDDING_API_KEY: str = os.getenv("EMBEDDING_API_KEY", "")
    EMBEDDING_API_BASE: str = os.getenv("EMBEDDING_API_BASE", "https://api.siliconflow.cn/v1")

    # Tavily搜索API配置
    TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", "")

    # LangSmith追踪配置（可选）
    LANGCHAIN_TRACING_V2: str = os.getenv("LANGCHAIN_TRACING_V2", "false")
    LANGCHAIN_API_KEY: str = os.getenv("LANGCHAIN_API_KEY", "")

    # SQLite数据库配置
    SQLITE_DB_PATH: str = os.getenv("SQLITE_DB_PATH", "D:\\Dev Project\\mimic_iv\\mimic_iv.sqlite")
    SQLITE_MCP_PATH: str = os.getenv("SQLITE_MCP_PATH", "D:\\Dev Project\\mimic_iv\\sqlite")

    # 系统配置
    MAX_ITERATIONS: int = int(os.getenv("MAX_ITERATIONS", "3"))
    MAX_SQL_RETRIES: int = int(os.getenv("MAX_SQL_RETRIES", "5"))
    AGENT_RECURSION_LIMIT: int = int(os.getenv("AGENT_RECURSION_LIMIT", "100"))

    # 查询评分配置
    ADAPTIVE_SCORING_THRESHOLD: int = int(os.getenv("ADAPTIVE_SCORING_THRESHOLD", "5"))
    SIMILARITY_THRESHOLD: float = float(os.getenv("SIMILARITY_THRESHOLD", "0.7"))

    # 动态停止条件配置
    NOVELTY_THRESHOLD: float = float(os.getenv("NOVELTY_THRESHOLD", "0.3"))

    # 查询评分过滤配置
    MIN_SCORE_THRESHOLD: float = float(os.getenv("MIN_SCORE_THRESHOLD", "0.1"))

    @classmethod
    def enable_langsmith_tracing(cls):
        """启用LangSmith追踪"""
        if cls.LANGCHAIN_TRACING_V2.lower() == "true" and cls.LANGCHAIN_API_KEY:
            os.environ["LANGCHAIN_TRACING_V2"] = "true"
            os.environ["LANGCHAIN_API_KEY"] = cls.LANGCHAIN_API_KEY
            print("✅ LangSmith追踪已启用")
            return True
        return False

    @classmethod
    def validate(cls) -> bool:
        """验证必要的配置是否存在"""
        errors = []

        if not cls.OPENROUTER_API_KEY:
            errors.append("OPENROUTER_API_KEY未设置")

        if not cls.EMBEDDING_API_KEY:
            errors.append("EMBEDDING_API_KEY未设置")

        if not cls.TAVILY_API_KEY:
            errors.append("TAVILY_API_KEY未设置")

        if not os.path.exists(cls.SQLITE_DB_PATH):
            errors.append(f"SQLite数据库文件不存在: {cls.SQLITE_DB_PATH}")

        if not os.path.exists(cls.SQLITE_MCP_PATH):
            errors.append(f"SQLite MCP路径不存在: {cls.SQLITE_MCP_PATH}")

        if errors:
            print("❌ 配置验证失败:")
            for error in errors:
                print(f"  - {error}")
            return False

        print("✅ 配置验证成功")
        return True

    @classmethod
    def display(cls):
        """显示当前配置（隐藏敏感信息）"""
        print("\n📋 当前配置:")
        print(f"  LLM模型: {cls.LLM_MODEL}")
        print(f"  温度: {cls.LLM_TEMPERATURE}")
        print(f"  嵌入模型: {cls.EMBEDDING_MODEL}")
        print(f"  数据库路径: {cls.SQLITE_DB_PATH}")
        print(f"  最大迭代次数: {cls.MAX_ITERATIONS}")
        print(f"  SQL最大重试次数: {cls.MAX_SQL_RETRIES}")
        print(f"  Agent递归限制: {cls.AGENT_RECURSION_LIMIT}")
        print(f"  自适应评分阈值: {cls.ADAPTIVE_SCORING_THRESHOLD}")
        print(f"  相似度阈值: {cls.SIMILARITY_THRESHOLD}")
        print(f"  新颖性阈值: {cls.NOVELTY_THRESHOLD}")
        print(f"  最低评分阈值: {cls.MIN_SCORE_THRESHOLD}")
        print(f"  OpenRouter API Key: {'已设置' if cls.OPENROUTER_API_KEY else '未设置'}")
        print(f"  Embedding API Key: {'已设置' if cls.EMBEDDING_API_KEY else '未设置'}")
        print(f"  Tavily API Key: {'已设置' if cls.TAVILY_API_KEY else '未设置'}")
        print(f"  LangSmith追踪: {'启用' if cls.LANGCHAIN_TRACING_V2.lower() == 'true' else '禁用'}")
        print()


# 导出配置实例
config = Config()

if __name__ == "__main__":
    config.display()
    config.validate()
