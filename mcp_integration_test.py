#!/usr/bin/env python3
import asyncio
import sys
import os

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.prebuilt import create_react_agent
from langchain_openai import ChatOpenAI


async def main():
    """主函数"""
    print("🚀 正在初始化 SQLite MCP Server...")

    try:
        # 配置 MCP 客户端
        client = MultiServerMCPClient(
            {
                "sqlite": {
                    "command": "uv",
                    "args": [
                        "--directory",
                        r"D:\Dev Project\mimic_iv\sqlite",
                        "run",
                        "mcp-server-sqlite",
                        "--db-path",
                        r"D:\Dev Project\mimic_iv\mimic_iv.sqlite"
                    ],
                    "transport": "stdio",
                },
            }
        )

        print("✅ MCP 客户端配置完成")

        # 配置 LLM
        llm = ChatOpenAI(
            openai_api_base="https://api.siliconflow.cn/v1",
            openai_api_key="sk-yandggkqnosrspklnhbgmyitdsoanhzqftbglbqvdhhmbymh",
            model_name="zai-org/GLM-4.6",
            temperature=0.1
        )

        print("✅ LLM 配置完成")

        # 获取工具并创建 agent
        print("🔧 正在获取 MCP 工具...")
        tools = await client.get_tools()
        print(f"✅ 获取到 {len(tools)} 个工具: {[tool.name for tool in tools]}")

        # 创建 agent
        agent = create_react_agent(llm, tools)
        print("✅ Agent 创建完成")

        # 测试查询
        print("\n📊 执行测试查询: 查询 patients 表的前5行数据")
        response = await agent.ainvoke(
            {"messages": [{"role": "user", "content": "运行SQL查询，查询mimic_iv数据库中patients表的前5行数据"}]}
        )

        print("\n📋 查询结果:")
        print("=" * 50)
        print(response['messages'][-1].content)
        print("=" * 50)

        # 更多测试
        print("\n🔍 探索数据库结构...")

        # 列出所有表
        tables_response = await agent.ainvoke(
            {"messages": [{"role": "user", "content": "请列出数据库中的所有表"}]}
        )
        print("\n数据库中的表:")
        print(tables_response['messages'][-1].content)

        # 查看表结构
        schema_response = await agent.ainvoke(
            {"messages": [{"role": "user", "content": "请描述admissions表的结构"}]}
        )
        print("\nadmissions表结构:")
        print(schema_response['messages'][-1].content)
        print("\n✅ 连接已关闭，程序执行完成！")

    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0

if __name__ == "__main__":
    # 运行主函数
    exit_code = asyncio.run(main())
    sys.exit(exit_code)