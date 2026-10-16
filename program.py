from agents import (
    Agent,
    Runner,
    set_default_openai_client,
    OpenAIChatCompletionsModel,
    set_tracing_disabled,
)
from agents.mcp import MCPServerStdio
import argparse
import asyncio
import os
import shutil
import subprocess
import sys
import warnings
from pathlib import Path

from dotenv import load_dotenv
from openai import AsyncAzureOpenAI

warnings.filterwarnings("ignore", category=ResourceWarning)

PROJECT_ROOT = Path(__file__).resolve().parent
DEFAULT_MCP_SCRIPT = (
    PROJECT_ROOT
    / "repo"
    / "SQL-AI-samples"
    / "MssqlMcp"
    / "Node"
    / "dist"
    / "index.js"
)

REQUIRED_AZURE_VARS = (
    "AZURE_OPENAI_API_KEY",
    "AZURE_OPENAI_ENDPOINT",
    "AZURE_OPENAI_CHAT_DEPLOYMENT_MODEL",
    "AZURE_OPENAI_API_VERSION",
)
REQUIRED_SQL_VARS = ("SERVER_NAME", "DATABASE_NAME")


def resolve_mcp_script() -> Path:
    override = os.getenv("MCP_SERVER_SCRIPT")
    if override:
        return Path(override).expanduser().resolve()
    return DEFAULT_MCP_SCRIPT.resolve()


def missing_env_vars(names: tuple[str, ...]) -> list[str]:
    return [name for name in names if not os.getenv(name)]


def validate_configuration(auth_method: str) -> bool:
    missing = missing_env_vars(REQUIRED_AZURE_VARS)
    missing.extend(missing_env_vars(REQUIRED_SQL_VARS))

    if auth_method in ("sql", "sqlserver"):
        missing.extend(missing_env_vars(("SQL_USERNAME", "SQL_PASSWORD")))
    elif auth_method in ("windows", "ntlm"):
        missing.extend(missing_env_vars(("DOMAIN", "USERNAME", "PASSWORD")))

    if missing:
        print(
            "Error: missing required environment variables: "
            + ", ".join(sorted(set(missing)))
        )
        return False
    return True


# Load environment variables
load_dotenv()

# Load environment variables for Azure OpenAI
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_CHAT_DEPLOYMENT_MODEL = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT_MODEL")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION")

# Load environment variables for SQL MCP server
SERVER_NAME = os.getenv("SERVER_NAME")
DATABASE_NAME = os.getenv("DATABASE_NAME")
AUTH_METHOD = os.getenv("AUTH_METHOD", "sql")
SQL_USERNAME = os.getenv("SQL_USERNAME")
SQL_PASSWORD = os.getenv("SQL_PASSWORD")
READONLY = os.getenv("READONLY", "false")
CONNECTION_TIMEOUT = os.getenv("CONNECTION_TIMEOUT", "50")
TRUST_SERVER_CERTIFICATE = os.getenv("TRUST_SERVER_CERTIFICATE", "true")

if not validate_configuration(AUTH_METHOD.lower()):
    sys.exit(1)

# Configure Azure OpenAI client
try:
    client = AsyncAzureOpenAI(
        api_key=AZURE_OPENAI_API_KEY,
        azure_endpoint=AZURE_OPENAI_ENDPOINT,
        api_version=AZURE_OPENAI_API_VERSION,
    )
except Exception as e:
    print(f"Error configuring Azure OpenAI client: {e}")
    sys.exit(1)

# Configure the default OpenAI client
set_default_openai_client(client)

# Disable tracing
set_tracing_disabled(disabled=True)


async def run_agent_with_sql_server(
    sql_server: MCPServerStdio, instructions: str, user_input: str
) -> None:
    """Run the agent with the SQL MCP server."""

    agent = Agent(
        name="SQL Automation Agent",
        instructions=instructions,
        mcp_servers=[sql_server],
        model=OpenAIChatCompletionsModel(
            model=AZURE_OPENAI_CHAT_DEPLOYMENT_MODEL,
            openai_client=client,
        ),
    )

    result = await Runner.run(
        starting_agent=agent,
        input=user_input,
        max_turns=100,
    )
    print(f"SQL Agent execution completed with result: {result.final_output}")


async def main() -> None:
    """Main function to run the SQL agent."""
    parser = argparse.ArgumentParser(
        description="Run the Azure OpenAI SQL agent against a SQL Server MCP server."
    )
    parser.add_argument(
        "question",
        nargs="?",
        default=(
            "Show me the top 10 products by total sales value, including the product "
            "name, category, and the total revenue for each, ordered from highest to "
            "lowest revenue"
        ),
        help="Natural-language question for the SQL agent",
    )
    args = parser.parse_args()

    if not shutil.which("node"):
        print("Error: node is not installed. Please install Node.js and try again.")
        return

    mcp_script = resolve_mcp_script()
    if not mcp_script.is_file():
        print(
            "Error: MCP server entry point not found at "
            f"{mcp_script}. Initialize the submodule, build the Node server, and copy "
            "index.ts into the sample project (see README.md), or set MCP_SERVER_SCRIPT."
        )
        return

    try:
        with open(PROJECT_ROOT / "sql_system_instructions.txt", encoding="utf-8") as f:
            instructions = f.read().strip()
    except FileNotFoundError:
        print("Error: sql_system_instructions.txt file not found.")
        return
    except OSError as e:
        print(f"Error reading instructions file: {e}")
        return

    user_input = args.question.strip()
    if not user_input:
        print("Error: question must not be empty.")
        return

    print(f"User input: {user_input}")

    try:
        async with MCPServerStdio(
            name="SQL Server MCP",
            client_session_timeout_seconds=30,
            params={
                "command": "node",
                "args": [str(mcp_script)],
                "env": {
                    "SERVER_NAME": SERVER_NAME,
                    "DATABASE_NAME": DATABASE_NAME,
                    "AUTH_METHOD": AUTH_METHOD,
                    "SQL_USERNAME": SQL_USERNAME,
                    "SQL_PASSWORD": SQL_PASSWORD,
                    "READONLY": READONLY,
                    "CONNECTION_TIMEOUT": CONNECTION_TIMEOUT,
                    "TRUST_SERVER_CERTIFICATE": TRUST_SERVER_CERTIFICATE,
                },
                "stderr": subprocess.DEVNULL,
            },
            cache_tools_list=True,
        ) as sql_server:
            try:
                sql_tools = await sql_server.list_tools()
                if not sql_tools:
                    print("Error: No tools available from MCP server")
                    return
            except Exception as e:
                print(f"Error connecting to MCP server: {e}")
                return

            await run_agent_with_sql_server(sql_server, instructions, user_input)

    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"Error: {e}")
