#!/usr/bin/env python3
"""
快速配置LangSmith追踪
直接在代码中设置LangSmith配置，无需修改.env文件
"""
import os

# LangSmith配置
LANGSMITH_API_KEY = "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"

def enable_langsmith():
    """启用LangSmith追踪"""
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = LANGSMITH_API_KEY
    print("✅ LangSmith追踪已启用")
    print(f"   API Key: {LANGSMITH_API_KEY[:20]}...")
    print("   追踪数据将上传到: https://smith.langchain.com/")

if __name__ == "__main__":
    enable_langsmith()
