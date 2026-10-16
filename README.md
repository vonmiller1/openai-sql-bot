# OpenAI SQL Bot

OpenAI SQL Bot is a Python agent that sends natural-language requests to Azure OpenAI and connects to SQL Server through a Node.js Model Context Protocol (MCP) server. The MCP server is based on Azure's SQL-AI-samples project and is customized here for multiple SQL Server authentication methods.

## How it works

```text
Question ──> Python agent ──> Azure OpenAI
                  │
                  └── MCP over stdio ──> Node.js SQL server ──> SQL Server
```

The Python entry point is `program.py`. The root `index.ts` is intended to replace the MCP sample's Node server source before it is built. `sql_system_instructions.txt` supplies the agent instructions, and `.env-template` lists the environment variables used by the example.

## Capabilities and access

The MCP server exposes tools for listing tables, reading data, and describing tables. With `READONLY=true`, only those read-oriented tools are made available. With read-only mode disabled, the server also exposes insert, update, table creation, index creation, and table deletion tools.

**Use a dedicated database account with least privilege.** The example configuration sets `READONLY=false`, which enables tools that can modify or delete database objects. Set `READONLY=true` unless write access is explicitly required. This flag limits the tools presented by the MCP server; it is not a substitute for database-side permissions.

## Prerequisites

- Python and the packages in `requirements.txt`
- Node.js and npm
- Azure OpenAI access and a deployed chat model
- A SQL Server database reachable from the machine running the bot

## Setup

Clone the project with its SQL sample submodule:

```bash
git clone --recurse-submodules https://github.com/vonmiller1/openai-sql-bot.git
cd openai-sql-bot
```

If the project was cloned without submodules, initialize them from the project root:

```bash
git submodule update --init --recursive
```

Create and activate a Python virtual environment, then install the dependencies:

```bash
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS/Linux:
# source .venv/bin/activate
python -m pip install -r requirements.txt
```

Install and build the Node.js MCP server, replacing its source with this repository's customized version:

```bash
cd repo/SQL-AI-samples/MssqlMcp/Node
npm install
# Copy the customized source into the sample project:
# Windows PowerShell:
Copy-Item ..\..\..\..\index.ts .\src\index.ts
# macOS/Linux:
# cp ../../../../index.ts src/index.ts
npm run build
cd ../../../../
```

The copy command assumes the sample project has the `src/index.ts` layout described above. Use the build script defined by the checked-out sample if its scripts differ.

Create a local `.env` file from the template and fill in the values for your environment:

```bash
# Windows PowerShell:
Copy-Item .env-template .env
# macOS/Linux:
# cp .env-template .env
```

At minimum, configure the Azure OpenAI endpoint, API key, API version, and the deployed chat model name, along with the SQL server, database, and credentials. `program.py` passes `AZURE_OPENAI_CHAT_DEPLOYMENT_MODEL` as the model identifier. Although `AZURE_OPENAI_CHAT_DEPLOYMENT` is present in the template and loaded by the script, it is not currently used to select the model.

### SQL connection settings

| Variable | Purpose |
| --- | --- |
| `SERVER_NAME` | SQL Server hostname |
| `DATABASE_NAME` | Database to connect to |
| `AUTH_METHOD` | `sql`, `azure-ad`, or `windows` |
| `SQL_USERNAME`, `SQL_PASSWORD` | Credentials for SQL authentication |
| `READONLY` | Set to `true` to expose only read-oriented tools |
| `CONNECTION_TIMEOUT` | Connection timeout in seconds |
| `TRUST_SERVER_CERTIFICATE` | Whether to trust the server certificate without normal certificate validation |

The Python example defaults `AUTH_METHOD` to `sql`; the MCP server itself defaults to `azure-ad` when started directly without an authentication setting. Azure AD authentication uses an interactive browser credential. Windows/NTLM authentication reads `DOMAIN`, `USERNAME`, and `PASSWORD`, which are not included in `.env-template`.

For production, prefer certificate validation (`TRUST_SERVER_CERTIFICATE=false`) and credentials restricted by database permissions. Set it to `true` only when the server certificate is managed and trusted through a separate process.

## Run

Before starting the agent, update the MCP executable path in `program.py`. It currently points to the original developer's absolute path (`D:/Research/sql-mcp-integration/...`), which will not exist in a fresh clone. Point the `args` entry at the built file:

```text
repo/SQL-AI-samples/MssqlMcp/Node/dist/index.js
```

Run the program from the project root:

```bash
python program.py
```

The example sends a fixed sample question defined by `user_input` in `program.py`. To ask a different question, edit that value before running.

## Repository layout

```text
.
├── README.md
├── plan.md
├── program.py
├── index.ts
├── index.js
├── sql_system_instructions.txt
├── requirements.txt
├── .env-template
└── repo/
    └── SQL-AI-samples/       # Git submodule; initialize before setup
        └── MssqlMcp/Node/    # Customized and built MCP server
```

## Current limitations and next steps

- The MCP server path in `program.py` is machine-specific and must be corrected before use.
- The sample accepts one hard-coded question per run; it does not currently provide an interactive prompt or command-line query argument.
- Azure OpenAI configuration is not validated up front, so missing or incorrect values may fail during client creation or execution.
- The repository's optimization and follow-up work is tracked in [`plan.md`](plan.md).
