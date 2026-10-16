# OpenAI SQL Bot

Natural-language SQL assistant that uses Azure OpenAI and a Node.js Model Context Protocol (MCP) server to query Microsoft SQL Server.

## Overview

This repository wires the OpenAI Agents SDK (Python) to Azure’s SQL MCP sample (`SQL-AI-samples`), with a customized root `index.ts` that supports SQL login, Azure AD, and Windows/NTLM authentication. You ask a question in plain language; the agent chooses MCP tools, runs SQL, and returns tabular results.

## Features

- Azure OpenAI chat agent with MCP tool calling over stdio
- SQL Server tools: list/describe tables, read data, and (when not read-only) insert, update, DDL, and drop
- Configurable authentication: `sql`, `azure-ad`, or `windows`
- Read-only mode to hide mutation tools at the MCP layer
- Optional CLI question argument; sensible default sample query if omitted
- Project-relative path to the built MCP server, with optional `MCP_SERVER_SCRIPT` override

## Tech stack

| Layer | Technology |
| --- | --- |
| Agent | Python 3, `openai-agents`, `openai`, `python-dotenv` |
| MCP server | Node.js, `@modelcontextprotocol/sdk`, `mssql`, `@azure/identity` |
| Database | Microsoft SQL Server |
| AI | Azure OpenAI (chat completions) |

## Prerequisites

- Python 3.10+ recommended
- Node.js 18+ and npm
- Azure OpenAI resource with a deployed chat model
- SQL Server instance reachable from the host running the bot

## Getting started

Clone including the SQL sample submodule:

```bash
git clone --recurse-submodules https://github.com/vonmiller1/openai-sql-bot.git
cd openai-sql-bot
```

If the repo was cloned without submodules:

```bash
git submodule update --init --recursive
```

Create a virtual environment and install Python dependencies:

```bash
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS/Linux:
# source .venv/bin/activate
python -m pip install -r requirements.txt
```

Build the MCP server (copy this repo’s server source into the sample, then compile):

```bash
cd repo/SQL-AI-samples/MssqlMcp/Node
npm install
# Windows PowerShell:
Copy-Item ..\..\..\..\index.ts .\src\index.ts
# macOS/Linux:
# cp ../../../../index.ts src/index.ts
npm run build
cd ../../../../
```

Copy environment template and set values (names only—never commit secrets):

```bash
# Windows PowerShell:
Copy-Item .env-template .env
# macOS/Linux:
# cp .env-template .env
```

Required Azure OpenAI variables: `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_CHAT_DEPLOYMENT_MODEL`, `AZURE_OPENAI_API_VERSION`.

Required SQL variables: `SERVER_NAME`, `DATABASE_NAME`, plus credentials matching `AUTH_METHOD`.

## Running locally

From the project root with `.env` configured and the MCP server built:

```bash
python program.py
```

Pass a custom question:

```bash
python program.py "List the five most recent orders with customer name and total"
```

The agent loads instructions from `sql_system_instructions.txt` and starts the MCP server at `repo/SQL-AI-samples/MssqlMcp/Node/dist/index.js` unless `MCP_SERVER_SCRIPT` is set.

## Testing

This project does not ship automated tests. To verify manually: build the MCP server, configure `.env`, run `python program.py` with a read-only question, and confirm tool listing and query results against a non-production database.

## Project structure

```text
.
├── README.md
├── program.py                 # Python agent entry point
├── index.ts                   # Custom MCP server source (copy into submodule before build)
├── index.js                   # Reference/transpiled-style copy of server logic
├── sql_system_instructions.txt
├── requirements.txt
├── .env-template
├── plan.md                    # Optimization notes (local planning)
└── repo/SQL-AI-samples/       # Git submodule (Azure sample)
    └── MssqlMcp/Node/         # Built MCP server output: dist/index.js
```

## Configuration

| Variable | Purpose |
| --- | --- |
| `SERVER_NAME` | SQL Server host |
| `DATABASE_NAME` | Target database |
| `AUTH_METHOD` | `sql`, `azure-ad`, or `windows` |
| `SQL_USERNAME`, `SQL_PASSWORD` | SQL authentication |
| `DOMAIN`, `USERNAME`, `PASSWORD` | Windows/NTLM (not in template; set when using `windows`) |
| `READONLY` | `true` exposes only read-oriented MCP tools (recommended default) |
| `CONNECTION_TIMEOUT` | Seconds before connection timeout |
| `TRUST_SERVER_CERTIFICATE` | `false` recommended for production TLS validation |
| `MCP_SERVER_SCRIPT` | Optional absolute path to `dist/index.js` |

The Python agent defaults `AUTH_METHOD` to `sql`. The MCP server defaults to `azure-ad` when started directly without that variable.

**Least privilege:** MCP read-only mode limits exposed tools; database permissions remain the real security boundary.

## Deployment

No Dockerfile or CI is included. Deploy by running `program.py` on a host that can reach Azure OpenAI and SQL Server, with secrets supplied via environment or a secure secret store—not committed files.

## Contributing

1. Fork [vonmiller1/openai-sql-bot](https://github.com/vonmiller1/openai-sql-bot).
2. Create a feature branch from `main`.
3. Keep commits focused; use clear messages (`fix:`, `docs:`, `sec:`).
4. Open a pull request describing behavior and configuration impact.

## License

No `LICENSE` file is present in this repository. Treat usage as at your own discretion until a license is added; submodule `SQL-AI-samples` remains under its upstream terms.

## Further reading

Implementation priorities and follow-ups are tracked in [`plan.md`](plan.md).
