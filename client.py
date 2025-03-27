# Create server parameters for stdio connection
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.prebuilt import create_react_agent
from langchain_mcp_adapters.client import MultiServerMCPClient

from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

import asyncio
import os

# Load environment variables from .env file
load_dotenv()

model = ChatOpenAI(model="llama-3.3-70b-instruct", base_url=os.getenv("SCW_ENDPOINT_URL"), api_key=os.getenv("SCW_SECRET_KEY"))

server_params = StdioServerParameters(
    command="python",
    # Make sure to update to the full absolute path to your math_server.py file
    args=["server.py"],
)


async def run_agent_simple():
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # Initialize the connection
            await session.initialize()

            # Get tools
            tools = await load_mcp_tools(session)

            # Create and run the agent
            agent = create_react_agent(model, tools)
            agent_response = await agent.ainvoke({"messages": "what's (3 + 5) x 12?"})
            return agent_response["messages"][3].content
        
        

async def run_agent_multi():

    async with MultiServerMCPClient(
        {
            "math": {
                "command": "python",
                # Make sure to update to the full absolute path to your math_server.py file
                "args": ["server_math.py"],
                "transport": "stdio",
            },
            "weather": {
                # make sure you start your weather server on port 8000
                "url": "http://localhost:8000/sse",
                "transport": "sse",
            }
        }
    ) as client:
        agent = create_react_agent(model, client.get_tools())
        math_response = await agent.ainvoke({"messages": "what's (3 + 5) x 12?"})
        print_response(math_response)
        weather_response = await agent.ainvoke({"messages": "what is the weather in nyc?"})
        print_response(weather_response)



def print_response(response):

    for msg in response["messages"]:
        print(msg.content)

        
if __name__ == "__main__":
    result = asyncio.run(run_agent_multi())
    print(result)
