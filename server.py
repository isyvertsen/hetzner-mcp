"""
Hetzner Cloud MCP Server
Sikker lokal MCP-server som gir Claude tilgang til Hetzner Cloud API.
API-nøkkelen lagres kun lokalt som miljøvariabel.
"""

import os
import json
import asyncio
from datetime import datetime
from typing import Any

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    from fastmcp import FastMCP

import httpx

# ── Konfigurasjon ──────────────────────────────────────────────
HETZNER_API_BASE = "https://api.hetzner.cloud/v1"

def get_token() -> str:
    token = os.environ.get("HETZNER_API_TOKEN")
    if not token:
        raise RuntimeError(
            "HETZNER_API_TOKEN er ikke satt. "
            "Sett miljøvariabelen før du starter serveren:\n"
            "  export HETZNER_API_TOKEN='din-token-her'"
        )
    return token

def headers() -> dict:
    return {
        "Authorization": f"Bearer {get_token()}",
        "Content-Type": "application/json",
    }

async def api_get(path: str, params: dict | None = None) -> dict:
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            f"{HETZNER_API_BASE}{path}",
            headers=headers(),
            params=params,
        )
        resp.raise_for_status()
        return resp.json()

async def api_post(path: str, data: dict | None = None) -> dict:
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            f"{HETZNER_API_BASE}{path}",
            headers=headers(),
            json=data,
        )
        resp.raise_for_status()
        return resp.json()

# ── MCP Server ─────────────────────────────────────────────────
mcp = FastMCP(
    name="Hetzner Cloud",
    instructions=(
        "MCP-server for Hetzner Cloud. "
        "Gir tilgang til serverstatus, brannmurer, nettverk, snapshots og backups. "
        "API-nøkkelen er lagret lokalt og sendes aldri til Claude."
    ),
)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  SERVERE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@mcp.tool()
async def list_servers() -> str:
    """List alle Hetzner Cloud-servere med status, IP-adresser og ressurser."""
    data = await api_get("/servers")
    servers = data.get("servers", [])
    if not servers:
        return "Ingen servere funnet."

    results = []
    for s in servers:
        public_net = s.get("public_net", {})
        ipv4 = public_net.get("ipv4", {}).get("ip", "N/A")
        ipv6 = public_net.get("ipv6", {}).get("ip", "N/A")
        st = s.get("server_type", {})

        results.append({
            "id": s["id"],
            "name": s["name"],
            "status": s["status"],
            "ipv4": ipv4,
            "ipv6": ipv6,
            "datacenter": s.get("datacenter", {}).get("name", "N/A"),
            "server_type": st.get("name", "N/A"),
            "cores": st.get("cores", "N/A"),
            "memory_gb": st.get("memory", "N/A"),
            "disk_gb": st.get("disk", "N/A"),
            "created": s.get("created", "N/A"),
            "labels": s.get("labels", {}),
        })

    return json.dumps(results, indent=2, ensure_ascii=False)


@mcp.tool()
async def get_server(server_id: int) -> str:
    """Hent detaljert info om en spesifikk server."""
    data = await api_get(f"/servers/{server_id}")
    s = data.get("server", {})
    public_net = s.get("public_net", {})
    st = s.get("server_type", {})

    result = {
        "id": s["id"],
        "name": s["name"],
        "status": s["status"],
        "ipv4": public_net.get("ipv4", {}).get("ip", "N/A"),
        "ipv6": public_net.get("ipv6", {}).get("ip", "N/A"),
        "datacenter": s.get("datacenter", {}).get("name", "N/A"),
        "location": s.get("datacenter", {}).get("location", {}).get("city", "N/A"),
        "server_type": st.get("name", "N/A"),
        "cores": st.get("cores", "N/A"),
        "memory_gb": st.get("memory", "N/A"),
        "disk_gb": st.get("disk", "N/A"),
        "image": s.get("image", {}).get("description", "N/A") if s.get("image") else "N/A",
        "created": s.get("created", "N/A"),
        "rescue_enabled": s.get("rescue_enabled", False),
        "locked": s.get("locked", False),
        "backup_window": s.get("backup_window", "N/A"),
        "load_balancers": s.get("load_balancers", []),
        "volumes": s.get("volumes", []),
        "labels": s.get("labels", {}),
        "protection": s.get("protection", {}),
    }

    return json.dumps(result, indent=2, ensure_ascii=False)


@mcp.tool()
async def get_server_metrics(server_id: int, metric_type: str = "cpu", period: str = "1h") -> str:
    """Hent metrikker (cpu, disk, network) for en server.

    Args:
        server_id: Server-ID
        metric_type: Type metrikk - 'cpu', 'disk' eller 'network'
        period: Tidsperiode - f.eks. '1h', '6h', '24h', '7d', '30d'
    """
    # Konverter periode til start/end
    now = datetime.utcnow()
    period_map = {
        "1h": 3600, "6h": 21600, "24h": 86400,
        "7d": 604800, "30d": 2592000,
    }
    seconds = period_map.get(period, 3600)
    start = datetime.utcfromtimestamp(now.timestamp() - seconds).isoformat() + "Z"
    end = now.isoformat() + "Z"

    data = await api_get(
        f"/servers/{server_id}/metrics",
        params={"type": metric_type, "start": start, "end": end},
    )

    return json.dumps(data.get("metrics", {}), indent=2, ensure_ascii=False)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  BRANNMURER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@mcp.tool()
async def list_firewalls() -> str:
    """List alle brannmurer med regler og tilknyttede ressurser."""
    data = await api_get("/firewalls")
    firewalls = data.get("firewalls", [])
    if not firewalls:
        return "Ingen brannmurer funnet."

    results = []
    for fw in firewalls:
        results.append({
            "id": fw["id"],
            "name": fw["name"],
            "rules": fw.get("rules", []),
            "applied_to": [
                {
                    "type": a.get("type"),
                    "server_id": a.get("server", {}).get("id") if a.get("server") else None,
                    "label_selector": a.get("label_selector", {}).get("selector") if a.get("label_selector") else None,
                }
                for a in fw.get("applied_to", [])
            ],
            "labels": fw.get("labels", {}),
            "created": fw.get("created", "N/A"),
        })

    return json.dumps(results, indent=2, ensure_ascii=False)


@mcp.tool()
async def get_firewall(firewall_id: int) -> str:
    """Hent detaljert info om en spesifikk brannmur inkludert alle regler."""
    data = await api_get(f"/firewalls/{firewall_id}")
    fw = data.get("firewall", {})

    result = {
        "id": fw["id"],
        "name": fw["name"],
        "rules": fw.get("rules", []),
        "applied_to": fw.get("applied_to", []),
        "labels": fw.get("labels", {}),
        "created": fw.get("created", "N/A"),
    }

    return json.dumps(result, indent=2, ensure_ascii=False)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  NETTVERK
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@mcp.tool()
async def list_networks() -> str:
    """List alle private nettverk med subnets og tilknyttede servere."""
    data = await api_get("/networks")
    networks = data.get("networks", [])
    if not networks:
        return "Ingen nettverk funnet."

    results = []
    for net in networks:
        results.append({
            "id": net["id"],
            "name": net["name"],
            "ip_range": net.get("ip_range", "N/A"),
            "subnets": net.get("subnets", []),
            "routes": net.get("routes", []),
            "servers": net.get("servers", []),
            "labels": net.get("labels", {}),
            "created": net.get("created", "N/A"),
        })

    return json.dumps(results, indent=2, ensure_ascii=False)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  SNAPSHOTS & BACKUPS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@mcp.tool()
async def list_images(image_type: str = "snapshot") -> str:
    """List alle snapshots eller backups.

    Args:
        image_type: 'snapshot', 'backup' eller 'system' (standardbilder)
    """
    data = await api_get("/images", params={"type": image_type, "sort": "created:desc"})
    images = data.get("images", [])
    if not images:
        return f"Ingen {image_type}s funnet."

    results = []
    for img in images:
        created_from = img.get("created_from", {})
        results.append({
            "id": img["id"],
            "description": img.get("description", "N/A"),
            "type": img.get("type", "N/A"),
            "status": img.get("status", "N/A"),
            "image_size_gb": img.get("image_size"),
            "disk_size_gb": img.get("disk_size"),
            "created_from_server": created_from.get("name") if created_from else None,
            "created_from_server_id": created_from.get("id") if created_from else None,
            "os_flavor": img.get("os_flavor", "N/A"),
            "created": img.get("created", "N/A"),
            "labels": img.get("labels", {}),
            "protection": img.get("protection", {}),
        })

    return json.dumps(results, indent=2, ensure_ascii=False)


@mcp.tool()
async def create_snapshot(server_id: int, description: str = "") -> str:
    """Opprett et snapshot av en server.

    Args:
        server_id: ID-en til serveren du vil ta snapshot av
        description: Valgfri beskrivelse av snapshotet
    """
    payload = {"type": "snapshot"}
    if description:
        payload["description"] = description

    data = await api_post(f"/servers/{server_id}/actions/create_image", payload)

    action = data.get("action", {})
    image = data.get("image", {})

    result = {
        "action_id": action.get("id"),
        "action_status": action.get("status"),
        "image_id": image.get("id"),
        "description": image.get("description", "N/A"),
        "status": image.get("status", "N/A"),
        "created": image.get("created", "N/A"),
    }

    return json.dumps(result, indent=2, ensure_ascii=False)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  HELSEOVERSIKT
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@mcp.tool()
async def health_check() -> str:
    """Kjør en helsesjekk av alle servere — viser status, brannmurer og siste snapshots."""
    servers_data = await api_get("/servers")
    firewalls_data = await api_get("/firewalls")
    snapshots_data = await api_get("/images", params={"type": "snapshot", "sort": "created:desc"})

    servers = servers_data.get("servers", [])
    firewalls = firewalls_data.get("firewalls", [])
    snapshots = snapshots_data.get("images", [])

    # Bygg rapport
    report = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "summary": {
            "total_servers": len(servers),
            "running": sum(1 for s in servers if s["status"] == "running"),
            "stopped": sum(1 for s in servers if s["status"] != "running"),
            "total_firewalls": len(firewalls),
            "total_snapshots": len(snapshots),
        },
        "servers": [],
    }

    # Bygg mapping fra server-id til brannmurer
    server_firewalls: dict[int, list[str]] = {}
    for fw in firewalls:
        for applied in fw.get("applied_to", []):
            srv = applied.get("server", {})
            if srv and srv.get("id"):
                server_firewalls.setdefault(srv["id"], []).append(fw["name"])

    # Bygg mapping fra server-id til siste snapshot
    server_snapshots: dict[int, dict] = {}
    for snap in snapshots:
        cf = snap.get("created_from", {})
        if cf and cf.get("id") and cf["id"] not in server_snapshots:
            server_snapshots[cf["id"]] = {
                "id": snap["id"],
                "description": snap.get("description", ""),
                "created": snap.get("created", ""),
            }

    for s in servers:
        sid = s["id"]
        public_net = s.get("public_net", {})
        st = s.get("server_type", {})

        report["servers"].append({
            "name": s["name"],
            "id": sid,
            "status": s["status"],
            "ipv4": public_net.get("ipv4", {}).get("ip", "N/A"),
            "datacenter": s.get("datacenter", {}).get("name", "N/A"),
            "type": st.get("name", "N/A"),
            "cores": st.get("cores"),
            "memory_gb": st.get("memory"),
            "firewalls": server_firewalls.get(sid, []),
            "has_firewall": bool(server_firewalls.get(sid)),
            "latest_snapshot": server_snapshots.get(sid),
            "has_recent_snapshot": bool(server_snapshots.get(sid)),
            "backup_window": s.get("backup_window"),
            "rescue_enabled": s.get("rescue_enabled", False),
            "locked": s.get("locked", False),
        })

    # Legg til advarsler
    warnings = []
    for srv in report["servers"]:
        if srv["status"] != "running":
            warnings.append(f"⚠ {srv['name']} er IKKE kjørende (status: {srv['status']})")
        if not srv["has_firewall"]:
            warnings.append(f"⚠ {srv['name']} har INGEN brannmur tilknyttet")
        if not srv["has_recent_snapshot"]:
            warnings.append(f"⚠ {srv['name']} har ingen snapshots")
        if srv["rescue_enabled"]:
            warnings.append(f"⚠ {srv['name']} er i RESCUE-modus")
        if srv["locked"]:
            warnings.append(f"⚠ {srv['name']} er LÅST")

    report["warnings"] = warnings

    return json.dumps(report, indent=2, ensure_ascii=False)


# ── Kjør serveren ──────────────────────────────────────────────
if __name__ == "__main__":
    mcp.run(transport="stdio")
