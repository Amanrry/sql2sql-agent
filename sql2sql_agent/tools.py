#!/usr/bin/env python3
"""
工具配置模块
简单配置SQLite MCP和Tavily搜索工具
"""
import os
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_tavily import TavilySearch
from config import config


async def get_mcp_tools():
    """获取SQLite MCP工具"""
    client = MultiServerMCPClient(
        {
            "sqlite": {
                "command": "uv",
                "args": [
                    "--directory",
                    config.SQLITE_MCP_PATH,
                    "run",
                    "mcp-server-sqlite",
                    "--db-path",
                    config.SQLITE_DB_PATH
                ],
                "transport": "stdio",
            },
        }
    )
    tools = await client.get_tools()
    return tools


def get_search_tool():
    """获取Tavily搜索工具"""
    os.environ["TAVILY_API_KEY"] = config.TAVILY_API_KEY
    tool = TavilySearch(max_results=5)
    return tool


async def get_all_tools():
    """获取所有工具"""
    mcp_tools = await get_mcp_tools()
    search_tool = get_search_tool()
    return list(mcp_tools) + [search_tool]


if __name__ == "__main__":
    import asyncio

    async def test():
        tools = await get_all_tools()
        print(f"✅ 获取到 {len(tools)} 个工具:")
        for tool in tools:
            print(f"  - {tool.name}")

    asyncio.run(test())
