本文介绍如下内容
如何设置带有提示、资源和工具的MCP服务器
如何使用客户端与MCP服务器交互
如何将MCP服务器与LangGraph集成来构建AI代理
前提条件
安装所需的包：mcp, langchain, langgraph, langchain-google-genai, langchain-mcp-adapters
步骤1：创建MCP服务器
MCP服务器是我们系统的骨干，它暴露提示、资源和工具。以下是一个简单的数学助手MCP服务器示例。

参考：https://github.com/modelcontextprotocol/python-sdk

服务器代码
我们使用MCP Python SDK中的FastMCP类创建一个名为“Math”的服务器。我们定义提示、资源和工具。

from mcp.server.fastmcp import FastMCP
​
mcp = FastMCP("Math")
​
# Prompts
@mcp.prompt()
def example_prompt(question: str) -> str:
    """Example prompt description"""
    return f"""
    You are a math assistant. Answer the question.
    Question: {question}
    """
​
@mcp.prompt()
def system_prompt() -> str:
    """System prompt description"""
    return """
    You are an AI assistant use the tools if needed.
    """
​
# Resources
@mcp.resource("greeting://{name}")
def get_greeting(name: str) -> str:
    """Get a personalized greeting"""
    return f"Hello, {name}!"
​
@mcp.resource("config://app")
def get_config() -> str:
    """Static configuration data"""
    return "App configuration here"
​
# Tools
@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers"""
    return a + b
​
@mcp.tool()
def multiply(a: int, b: int) -> int:
    """Multiply two numbers"""
    return a * b
​
if __name__ == "__main__":
    mcp.run()  # Run server via stdio
这段代码：

初始化一个名为“Math”的MCP服务器
定义两个提示：用于数学问题的example_prompt和用于一般指令的system_prompt
定义两个资源：动态资源greeting://{name}和静态资源config://app
定义两个工具：用于基本数学运算的add和multiply
使用stdio运行服务器
对于可流式HTTP：

使用mcp.run(transport="streamable-http")
...
​
if __name__ == "__main__":
    mcp.run(transport="streamable-http")  # Run server via streamable-http
将在http://localhost:8000/mcp上可用
将此代码保存为math_mcp_server.py

步骤2：创建MCP客户端
要与服务器交互，我们使用MCP客户端。客户端通过stdio与服务器通信，允许我们列出提示、资源和工具，并调用它们。

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import asyncio
​
# Math Server Parameters
server_params = StdioServerParameters(
    command="python",
    args=["math_mcp_server.py"],
    env=None,
)
​
async def main():
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
​
            # List available prompts
            response = await session.list_prompts()
            print("\n/////////////////prompts//////////////////")
            for prompt in response.prompts:
                print(prompt)
​
            # List available resources
            response = await session.list_resources()
            print("\n/////////////////resources//////////////////")
            for resource in response.resources:
                print(resource)
​
            # List available resource templates
            response = await session.list_resource_templates()
            print("\n/////////////////resource_templates//////////////////")
            for resource_template in response.resourceTemplates:
                print(resource_template)
​
            # List available tools
            response = await session.list_tools()
            print("\n/////////////////tools//////////////////")
            for tool in response.tools:
                print(tool)
​
            # Get a prompt
            prompt = await session.get_prompt("example_prompt", arguments={"question": "what is 2+2"})
            print("\n/////////////////prompt//////////////////")
            print(prompt.messages[0].content.text)
​
            # Read a resource
            content, mime_type = await session.read_resource("greeting://Alice")
            print("\n/////////////////content//////////////////")
            print(mime_type[1][0].text)
​
            # Call a tool
            result = await session.call_tool("add", arguments={"a": 2, "b": 2})
            print("\n/////////////////result//////////////////")
            print(result.content[0].text)
​
if __name__ == "__main__":
    asyncio.run(main())
输出
运行客户端代码会产生以下输出：

Processing request of type ListPromptsRequest
​
/////////////////prompts//////////////////
name='example_prompt' description='Example prompt description' arguments=[PromptArgument(name='question', description=None, required=True)]
name='system_prompt' description='System prompt description' arguments=[]
​
Processing request of type ListResourcesRequest
​
/////////////////resources//////////////////
uri=AnyUrl('config://app') name='get_config' description='Static configuration data' mimeType='text/plain' size=None annotations=None
​
Processing request of type ListResourceTemplatesRequest
​
/////////////////resource_templates//////////////////
uriTemplate='greeting://{name}' name='get_greeting' description='Get a personalized greeting' mimeType=None annotations=None
​
Processing request of type ListToolsRequest
​
/////////////////tools//////////////////
name='add' description='Add two numbers' inputSchema={'properties': {'a': {'title': 'A', 'type': 'integer'}, 'b': {'title': 'B', 'type': 'integer'}}, 'required': ['a', 'b'], 'title': 'addArguments', 'type': 'object'} annotations=None
name='multiply' description='Multiply two numbers' inputSchema={'properties': {'a': {'title': 'A', 'type': 'integer'}, 'b': {'title': 'B', 'type': 'integer'}}, 'required': ['a', 'b'], 'title': 'multiplyArguments', 'type': 'object'} annotations=None
​
Processing request of type GetPromptRequest
​
/////////////////prompt//////////////////
    You are a math assistant. Answer the question.
    Question: what is 2+2
    
Processing request of type ReadResourceRequest
​
/////////////////content//////////////////
Hello, Alice!
​
Processing request of type CallToolRequest
​
/////////////////result//////////////////
4
这个输出显示了：

可用的提示（example_prompt和system_prompt）
可用的资源（config://app）和资源模板（greeting://{name}）
可用的工具（add和multiply）及其输入模式
使用“what is 2+2”调用example_prompt的结果
读取greeting://Alice资源的结果
使用输入a=2和b=2调用add工具的结果
对于可流式HTTP：

使用streamablehttp_client代替stdio_client
from mcp.client.streamable_http import streamablehttp_client
​
# Math server
math_server_url = "http://localhost:8000/mcp"
​
async def main():
    async with streamablehttp_client(math_server_url) as (read, write, _):
        async with ClientSession(read, write) as session:
            ...
步骤3：将MCP与LangGraph集成
LangGraph允许我们使用基于图的方法构建有状态工作流。我们可以将MCP服务器与LangGraph集成，创建一个使用服务器工具和提示的AI代理。

from typing import List
from typing_extensions import TypedDict
from typing import Annotated
​
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import tools_condition, ToolNode
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import AnyMessage, add_messages
from langgraph.checkpoint.memory import MemorySaver
​
from langchain_mcp_adapters.tools import load_mcp_tools
from langchain_mcp_adapters.resources import load_mcp_resources
from langchain_mcp_adapters.prompts import load_mcp_prompt
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
​
import asyncio
​
# Math Server Parameters
server_params = StdioServerParameters(
    command="python",
    args=["math_mcp_server.py"],
    env=None,
)
​
async def create_graph(session):
    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0, api_key="your_google_api_key")
    
    tools = await load_mcp_tools(session)
    llm_with_tool = llm.bind_tools(tools)
​
    system_prompt = await load_mcp_prompt(session, "system_prompt")
    prompt_template = ChatPromptTemplate.from_messages([
        ("system", system_prompt[0].content),
        MessagesPlaceholder("messages")
    ])
    chat_llm = prompt_template | llm_with_tool
​
    # State Management
    class State(TypedDict):
        messages: Annotated[List[AnyMessage], add_messages]
​
    # Nodes
    def chat_node(state: State) -> State:
        state["messages"] = chat_llm.invoke({"messages": state["messages"]})
        return state
​
    # Building the graph
    graph_builder = StateGraph(State)
    graph_builder.add_node("chat_node", chat_node)
    graph_builder.add_node("tool_node", ToolNode(tools=tools))
    graph_builder.add_edge(START, "chat_node")
    graph_builder.add_conditional_edges("chat_node", tools_condition, {"tools": "tool_node", "__end__": END})
    graph_builder.add_edge("tool_node", "chat_node")
    graph = graph_builder.compile(checkpointer=MemorySaver())
    return graph
​
async def main():
    config = {"configurable": {"thread_id": 1234}}
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
​
            # Check available tools
            tools = await load_mcp_tools(session)
            print("Available tools:", [tool.name for tool in tools])
​
            # Check available prompts
            prompts = await load_mcp_prompt(session, "example_prompt", arguments={"question": "what is 2+2"})
            print("Available prompts:", [prompt.content for prompt in prompts])
            prompts = await load_mcp_prompt(session, "system_prompt")
            print("Available prompts:", [prompt.content for prompt in prompts])
​
            # Check available resources
            resources = await load_mcp_resources(session, uris=["greeting://Alice", "config://app"])
            print("Available resources:", [resource.data for resource in resources])
​
            # Use the MCP Server in the graph
            agent = await create_graph(session)
            while True:
                message = input("User: ")
                response = await agent.ainvoke({"messages": message}, config=config)
                print("AI: "+response["messages"][-1].content)
​
if __name__ == "__main__":
    asyncio.run(main())
输出
Processing request of type ListToolsRequest
Available tools: ['add', 'multiply']
​
Processing request of type GetPromptRequest
Available prompts: ['\n    You are a math assistant. Answer the question.\n    Question: what is 2+2\n    ']
​
Processing request of type GetPromptRequest
Available prompts: ['\n    You are an AI assistant use the tools if needed.\n    ']
​
Processing request of type ReadResourceRequest
Processing request of type ReadResourceRequest
Available resources: ['Hello, Alice!', 'App configuration here']
​
Processing request of type ListToolsRequest
Processing request of type GetPromptRequest
​
User: Hi
AI: Hi there! How can I help you today?
User: what is 2 + 4
Processing request of type CallToolRequest
AI: 2 + 4 = 6
此输出显示：

代理列出可用工具（add、multiply）和提示
代理访问资源（greeting://Alice、config://app）
代理响应用户输入，包括调用add工具计算2 + 4 = 6
步骤4：将多个MCP服务器与LangGraph集成
我们可以使用MultiServerMCPClient连接到多个服务器。

创建另一个MCP服务器
from mcp.server.fastmcp import FastMCP
​
mcp = FastMCP("BMI")
​
# Tools
@mcp.tool()
def calculate_bmi(weight: int, height: int) -> str:
    """Calculate BMI"""
    return "BMI: "+str(weight/(height*height))
​
if __name__ == "__main__":
    mcp.run(transport="streamable-http")
将此代码保存为bmi_mcp_server.py。这个服务器：

初始化一个名为“BMI”的MCP服务器
定义一个calculate_bmi工具，使用体重（千克）和身高（米）计算BMI
通过HTTP在http://localhost:8000/mcp运行服务器
多MCP服务器LangGraph代码（会话已关闭）
在以下代码中，我们使用client.get_tools()和client.get_prompt()，每次工具调用都会创建一个新的MCP ClientSession

from typing import List
from typing_extensions import TypedDict
from typing import Annotated
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import tools_condition, ToolNode
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import AnyMessage, add_messages
from langgraph.checkpoint.memory import MemorySaver
from langchain_mcp_adapters.client import MultiServerMCPClient
import asyncio
​
client = MultiServerMCPClient(
    {
        "math": {
            "command": "python",
            "args": ["math_mcp_server.py"],
            "transport": "stdio",
        },
        "bmi": {
            "url": "http://localhost:8000/mcp",
            "transport": "streamable_http",
        }
    }
)
​
async def create_graph():
    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0, api_key="your_google_api_key")
    tools = await client.get_tools()
    llm_with_tool = llm.bind_tools(tools)
    system_prompt = await client.get_prompt(server_name="math", prompt_name="system_prompt")
    prompt_template = ChatPromptTemplate.from_messages([
        ("system", system_prompt[0].content),
        MessagesPlaceholder("messages")
    ])
    chat_llm = prompt_template | llm_with_tool
​
    # State Management
    class State(TypedDict):
        messages: Annotated[List[AnyMessage], add_messages]
​
    # Nodes
    def chat_node(state: State) -> State:
        state["messages"] = chat_llm.invoke({"messages": state["messages"]})
        return state
​
    # Building the graph
    graph_builder = StateGraph(State)
    graph_builder.add_node("chat_node", chat_node)
    graph_builder.add_node("tool_node", ToolNode(tools=tools))
    graph_builder.add_edge(START, "chat_node")
    graph_builder.add_conditional_edges("chat_node", tools_condition, {"tools": "tool_node", "__end__": END})
    graph_builder.add_edge("tool_node", "chat_node")
    graph = graph_builder.compile(checkpointer=MemorySaver())
    return graph
​
async def main():
    config = {"configurable": {"thread_id": 1234}}
    agent = await create_graph()
    while True:
        message = input("User: ")
        response = await agent.ainvoke({"messages": message}, config=config)
        print("AI: "+response["messages"][-1].content)
​
if __name__ == "__main__":
    asyncio.run(main())
多MCP服务器LangGraph代码（持久会话）
我们可以使用client.session为两个服务器保持会话开启。

from typing import List
from typing_extensions import TypedDict
from typing import Annotated
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import tools_condition, ToolNode
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import AnyMessage, add_messages
from langgraph.checkpoint.memory import MemorySaver
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_mcp_adapters.tools import load_mcp_tools
from langchain_mcp_adapters.prompts import load_mcp_prompt
import asyncio
​
client = MultiServerMCPClient(
    {
        "math": {
            "command": "python",
            "args": ["math_mcp_server.py"],
            "transport": "stdio",
        },
        "bmi": {
            "url": "http://localhost:8000/mcp",
            "transport": "streamable_http",
        }
    }
)
​
async def create_graph(math_session, bmi_session):
    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0, api_key="your_google_api_key")
    
    math_tools = await load_mcp_tools(math_session)
    bmi_tools = await load_mcp_tools(bmi_session)
    tools = math_tools + bmi_tools
    llm_with_tool = llm.bind_tools(tools)
    
    system_prompt = await load_mcp_prompt(math_session, "system_prompt")
    prompt_template = ChatPromptTemplate.from_messages([
        ("system", system_prompt[0].content),
        MessagesPlaceholder("messages")
    ])
    chat_llm = prompt_template | llm_with_tool
​
    # State Management
    class State(TypedDict):
        messages: Annotated[List[AnyMessage], add_messages]
​
    # Nodes
    def chat_node(state: State) -> State:
        state["messages"] = chat_llm.invoke({"messages": state["messages"]})
        return state
​
    # Building the graph
    graph_builder = StateGraph(State)
    graph_builder.add_node("chat_node", chat_node)
    graph_builder.add_node("tool_node", ToolNode(tools=tools))
    graph_builder.add_edge(START, "chat_node")
    graph_builder.add_conditional_edges("chat_node", tools_condition, {"tools": "tool_node", "__end__": END})
    graph_builder.add_edge("tool_node", "chat_node")
    graph = graph_builder.compile(checkpointer=MemorySaver())
    return graph
​
async def main():
    config = {"configurable": {"thread_id": 1234}}
    async with client.session("math") as math_session, client.session("bmi") as bmi_session:
        agent = await create_graph(math_session, bmi_session)
        while True:
            message = input("User: ")
            response = await agent.ainvoke({"messages": message}, config=config)
            print("AI: "+response["messages"][-1].content)
​
if __name__ == "__main__":
    asyncio.run(main())
输出
User: Hi
AI: Hi there! How can I help you today?
User: how many tools do you have
AI: I have 3 tools available: `add`, `multiply`, and `calculate_bmi`.
User: find 5 * 4
Processing request of type CallToolRequest
AI: The answer is 20.
此输出显示：

代理识别来自两个服务器的三个工具
调用multiply工具计算5 * 4
结论
通过将MCP与LangGraph结合，您可以构建灵活、模块化的AI系统，在有状态工作流中利用结构化提示和工具。MCP服务器为定义AI功能提供了一个干净的接口，而LangGraph则编排信息流。