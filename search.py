import os
from langchain import agents
from langchain_openai import ChatOpenAI
from langchain.tools import Tool
from langchain_tavily import TavilySearch
from langgraph.prebuilt import create_react_agent
llm = ChatOpenAI(
    openai_api_base="https://openrouter.ai/api/v1",
    openai_api_key="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",    
    model_name="deepseek/deepseek-chat-v3.1:free",   
)

os.environ["TAVILY_API_KEY"] = "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"


tool = TavilySearch(max_results=5)
agent = create_react_agent(
    model= llm,
    tools=[tool],
)


for chunk in agent.stream(
    {"messages": [{"role": "user", "content": "what is the weather in sf"}]},
    stream_mode="updates"
):
    print(chunk)
    print("\n")