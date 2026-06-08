import os
import requests
import logging
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.server import TransportSecuritySettings

# Load environment variables from .env file for local development
load_dotenv()

# Configure logging to print to the terminal
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("doppler-mcp")

# Initialize FastMCP (disabling DNS rebinding protection to allow requests on Render)
security = TransportSecuritySettings(enable_dns_rebinding_protection=False)
mcp = FastMCP("Doppler Secrets MCP", transport_security=security)

# ─── CONFIG ───────────────────────────────────────────────
DOPPLER_TOKEN   = os.environ.get('DOPPLER_TOKEN')
DOPPLER_PROJECT = os.environ.get('DOPPLER_PROJECT')
DOPPLER_CONFIG  = os.environ.get('DOPPLER_CONFIG')
# ──────────────────────────────────────────────────────────

def get_all_secrets():
    logger.info(f"Connecting to Doppler API for project '{DOPPLER_PROJECT}' and config '{DOPPLER_CONFIG}'...")
    if not DOPPLER_TOKEN:
        logger.error("DOPPLER_TOKEN is not set in the environment variables!")
        raise ValueError("Missing DOPPLER_TOKEN")
        
    url = "https://api.doppler.com/v3/configs/config/secrets"
    params = {"project": DOPPLER_PROJECT, "config": DOPPLER_CONFIG}
    headers = {"Authorization": f"Bearer {DOPPLER_TOKEN}", "Accept": "application/json"}
    
    response = requests.get(url, headers=headers, params=params)
    if response.status_code != 200:
        logger.error(f"Doppler API Error: {response.status_code} - {response.text}")
    response.raise_for_status()
    
    data = response.json()
    secrets = {}
    for key, val in data.get("secrets", {}).items():
        secrets[key] = val.get("computed", "")
        
    logger.info(f"Successfully retrieved {len(secrets)} secrets from Doppler.")
    return secrets

@mcp.tool()
def fetch_all_secrets() -> str:
    """Fetch all secrets from Doppler"""
    logger.info("Tool 'fetch_all_secrets' called by client.")
    try:
        secrets = get_all_secrets()
        return str(secrets)
    except Exception as e:
        logger.error(f"Error in fetch_all_secrets: {e}")
        return f"Error: {e}"

@mcp.tool()
def fetch_secret(name: str) -> str:
    """Fetch a specific secret by name"""
    logger.info(f"Tool 'fetch_secret' called by client for secret: '{name}'")
    try:
        secrets = get_all_secrets()
        if name in secrets:
            logger.info(f"Secret '{name}' found.")
            return f"{name}: {secrets[name]}"
        else:
            logger.warning(f"Secret '{name}' not found.")
            return f"{name}: NOT FOUND"
    except Exception as e:
        logger.error(f"Error in fetch_secret: {e}")
        return f"Error: {e}"

# Expose the Starlette app for ASGI servers like Uvicorn (used by Render)
app = mcp.sse_app()

if __name__ == "__main__":
    # Runs the server using standard SSE transport (defaults to port 8000)
    mcp.run(transport="sse")
