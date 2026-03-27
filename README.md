# Hetzner Cloud MCP Server

A secure, local [MCP](https://modelcontextprotocol.io/) server that gives Claude access to your Hetzner Cloud infrastructure. Your API token stays on your machine and is **never sent to Anthropic**.

## Features

- **Server monitoring** — list servers, check status, view CPU/disk/network metrics
- **Firewall inspection** — view firewall rules and which servers they're applied to
- **Network overview** — private networks, subnets, and routes
- **Snapshot & backup management** — list and create snapshots
- **Health check** — one-command overview with warnings for missing firewalls, stopped servers, etc.

## Quick Start

### 1. Clone and install

```bash
git clone https://github.com/ivarwerner/hetzner-mcp.git
cd hetzner-mcp
chmod +x install.sh
./install.sh
```

### 2. Get a Hetzner API token

Go to [Hetzner Cloud Console](https://console.hetzner.cloud/) → Security → API Tokens → Generate API Token.

Use **Read** permissions for a read-only setup, or **Read & Write** if you want to create snapshots.

### 3. Configure Claude Desktop

Edit your Claude Desktop config:

- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "hetzner": {
      "command": "/path/to/hetzner-mcp/.venv/bin/python",
      "args": ["/path/to/hetzner-mcp/server.py"],
      "env": {
        "HETZNER_API_TOKEN": "your-token-here",
        "PYTHONUNBUFFERED": "1"
      }
    }
  }
}
```

### 4. Restart Claude Desktop

The Hetzner tools should now be available. Try asking Claude: *"Run a health check on my Hetzner servers"*.

## Available Tools

| Tool | Description |
|------|-------------|
| `list_servers` | List all servers with status, IPs, and resources |
| `get_server` | Detailed info for a specific server |
| `get_server_metrics` | CPU, disk, and network metrics (1h–30d) |
| `list_firewalls` | List firewalls with rules and applied resources |
| `get_firewall` | Detailed view of a specific firewall |
| `list_networks` | Private networks, subnets, and routes |
| `list_images` | List snapshots or backups |
| `create_snapshot` | Create a snapshot of a server |
| `health_check` | Full health report with warnings |

## Security

Your API token is stored in the local Claude Desktop config file — it is **never** included in conversations or sent to Anthropic's servers. The MCP server runs locally on your machine and communicates with Claude via stdio.

For extra safety:

- Use a **read-only** API token if you don't need write operations
- Rotate your token regularly via Hetzner Cloud Console
- The `.gitignore` ensures `.env` files are never committed

## Requirements

- Python 3.10+
- A Hetzner Cloud account with an API token

## License

[MIT](LICENSE)
