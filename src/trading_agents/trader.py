# src/trading_agents/trader.py
"""AI Trader agent implementation driven by TraderConfig."""

from contextlib import AsyncExitStack
from dotenv import load_dotenv
import os
import json
from agents import Agent, Tool, Runner, OpenAIChatCompletionsModel, trace
from openai import AsyncOpenAI
from agents.mcp import MCPServerStdio

from .templates import (
    researcher_instructions,
    trader_instructions,
    trade_message,
    rebalance_message,
    research_tool,
)
from .mcp_config import trader_mcp_server_params, researcher_mcp_server_params
from ..utils.tracers import make_trace_id
from ..mcp_servers.accounts_client import read_accounts_resource, read_strategy_resource
from ..utils.config import settings, TraderConfig

load_dotenv(override=True)

MAX_TURNS = 30

# Central OpenRouter AsyncOpenAI client instance
openrouter_client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=settings.openrouter_api_key
)


def get_model(model_name: str):
    """Get the model client dynamically based on model name."""
    if not model_name:
        return "gpt-4o-mini"
    return OpenAIChatCompletionsModel(model=model_name, openai_client=openrouter_client)


async def get_researcher(mcp_servers, model_name) -> Agent:
    """Create a researcher agent."""
    return Agent(
        name="Researcher",
        instructions=researcher_instructions(),
        model=get_model(model_name),
        mcp_servers=mcp_servers,
    )


async def get_researcher_tool(mcp_servers, model_name) -> Tool:
    """Create a researcher tool from the researcher agent."""
    researcher = await get_researcher(mcp_servers, model_name)
    return researcher.as_tool(tool_name="Researcher", tool_description=research_tool())


class Trader:
    """AI Trader agent driven by structured TraderConfig dataclass."""
    
    def __init__(self, config_or_name: str | TraderConfig, lastname: str = "Trader", model_name: str = "gpt-4o-mini"):
        if isinstance(config_or_name, TraderConfig):
            self.config = config_or_name
            self.name = config_or_name.name
            self.lastname = config_or_name.lastname
            self.model_name = config_or_name.model_name
        else:
            self.name = config_or_name
            self.lastname = lastname
            self.model_name = model_name
            self.config = None

        self.agent = None
        self.do_trade = True

    async def create_agent(self, trader_mcp_servers, researcher_mcp_servers) -> Agent:
        """Create the trader agent with researcher tool."""
        tool = await get_researcher_tool(researcher_mcp_servers, self.model_name)
        self.agent = Agent(
            name=self.name,
            instructions=trader_instructions(self.name),
            model=get_model(self.model_name),
            tools=[tool],
            mcp_servers=trader_mcp_servers,
        )
        return self.agent

    async def get_account_report(self) -> str:
        """Get account report from MCP resource."""
        account = await read_accounts_resource(self.name)
        account_json = json.loads(account)
        account_json.pop("portfolio_value_time_series", None)
        return json.dumps(account_json)

    async def run_agent(self, trader_mcp_servers, researcher_mcp_servers):
        """Run the trader agent with appropriate message."""
        self.agent = await self.create_agent(trader_mcp_servers, researcher_mcp_servers)
        account = await self.get_account_report()
        strategy = await read_strategy_resource(self.name)
        message = (
            trade_message(self.name, strategy, account)
            if self.do_trade
            else rebalance_message(self.name, strategy, account)
        )
        await Runner.run(self.agent, message, max_turns=MAX_TURNS)

    async def run_with_mcp_servers(self):
        """Run trader with MCP servers initialized."""
        async with AsyncExitStack() as stack:
            trader_mcp_servers = [
                await stack.enter_async_context(
                    MCPServerStdio(params, client_session_timeout_seconds=120)
                )
                for params in trader_mcp_server_params
            ]
            async with AsyncExitStack() as stack:
                researcher_mcp_servers = [
                    await stack.enter_async_context(
                        MCPServerStdio(params, client_session_timeout_seconds=120)
                    )
                    for params in researcher_mcp_server_params(self.name)
                ]
                await self.run_agent(trader_mcp_servers, researcher_mcp_servers)

    async def run_with_trace(self):
        """Run trader with tracing enabled."""
        trace_name = f"{self.name}-trading" if self.do_trade else f"{self.name}-rebalancing"
        trace_id = make_trace_id(f"{self.name.lower()}")
        with trace(trace_name, trace_id=trace_id):
            await self.run_with_mcp_servers()

    async def run(self):
        """Main entry point to run the trader."""
        try:
            await self.run_with_trace()
        except Exception as e:
            print(f"Error running trader {self.name}: {e}")
        self.do_trade = not self.do_trade
