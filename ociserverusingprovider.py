import os
from dotenv import load_dotenv

import oci
from oci.auth.signers import TokenExchangeSigner
from ociprovider import OCIProvider

from starlette.responses import PlainTextResponse
from starlette.requests import Request
from fastmcp import FastMCP
from fastmcp.server.dependencies import get_access_token
from fastmcp.server.auth import OIDCProxy
from fastmcp.server.context import Context
from fastmcp.utilities.logging import get_logger

logger = get_logger(__name__)

# Store tokens on disk for persistence across restarts
#token_storage = DiskCache(cache_dir="/Users/kgthakka/Downloads/agentdemo/sessionstore", ttl_hours=24)
#token_storage = RedisTokenCache(redis_url="redis://{REDIS_SERVER}:6379") 
#token_storage = InMemoryContextCache()
_global_token_cache = {} #In memory cache for OCI session token signer

load_dotenv()
IAM_DOMAIN = os.getenv("IAM_DOMAIN")
IAM_CLIENT_ID = os.getenv("IAM_CLIENT_ID")
IAM_CLIENT_SECRET = os.getenv("IAM_CLIENT_SECRET")

IAM_GUID = os.getenv("IAM_GUID")
IAM_TOKENEXCHANGE_CLIENT_ID = os.getenv("IAM_TOKENEXCHANGE_CLIENT_ID")
IAM_TOKENEXCHANGE_CLIENT_SECRET = os.getenv("IAM_TOKENEXCHANGE_CLIENT_SECRET")

auth = OCIProvider(
    config_url= f"https://{IAM_DOMAIN}/.well-known/openid-configuration",
    client_id=IAM_CLIENT_ID,
    client_secret=IAM_CLIENT_SECRET,
    base_url="http://localhost:8000",
    required_scopes=["openid", "profile", "email"],
)

mcp = FastMCP("My MCP Server", auth=auth)

def get_oci_signer(token: str, tokenID: str) -> TokenExchangeSigner:
    """Create an OCI TokenExchangeSigner using the provided token."""
    
    #Check if the signer exists for the token ID in memory cache
    cached_signer = _global_token_cache.get(tokenID)
    logger.debug(f"Global cached signer: {cached_signer}")
    if cached_signer:
        logger.debug(f"Using globally cached signer for token ID: {tokenID}")
        return cached_signer

    #If the signer is not yet created for the token then create new OCI signer object
    logger.debug(f"Creating new signer for token ID: {tokenID}")
    signer = TokenExchangeSigner(
        jwt_or_func=token,
        oci_domain_id=IAM_GUID,
        client_id=IAM_TOKENEXCHANGE_CLIENT_ID,
        client_secret=IAM_TOKENEXCHANGE_CLIENT_SECRET
    )
    logger.debug(f"Signer {signer} created for token ID: {tokenID}")
    
    #Cache the signer object in memory cache
    _global_token_cache[tokenID] = signer
    logger.debug(f"Signer cached for token ID: {tokenID}")

    return signer

@mcp.tool
def get_os_namespace(region: str, ctx: Context) -> str:
    """Get OCI Object Storage namespace for the tenancy"""
    
    """First create OCI Object storage client. 
    To create the client, we need OCI signer. 
    We will exchange IAM domain JWT token for OCI UPST token and use the UPST token to create signer object.
    """
    token = get_access_token()
    tokenID = token.claims.get("jti")
    ac_token = token.token
    signer = get_oci_signer(ac_token, tokenID)
    object_storage_client = ociprovider.object_storage.ObjectStorageClient(config={'region': region}, signer=signer)

    # Get the namespace using Object Storage Client
    namespace_response = object_storage_client.get_namespace()
    namespace_name = namespace_response.data
    return namespace_name

@mcp.tool
def whoami(ctx: Context) -> str:
    """The whoami function is to test MCP server without requiring token exchange.
    This tool can be used to test successful authentication against OCI IAM.
    It will return logged in user's subject (username from IAM domain)."""
    token = get_access_token()
    user = token.claims.get("sub")
    return f"You are User: {user}"

@mcp.tool
async def get_token() -> str:
    """This tool can be used to get logged in user's IAM domain access token."""
    token = get_access_token()
    return token.token

@mcp.tool
async def get_access_token_claims() -> dict:
    """This tool can be used to get the authenticated user's access token claims."""
    token = get_access_token()
    return {
        "sub": token.claims.get("sub"),
        "uid": token.claims.get("uid"),
        "aud": token.claims.get("aud"),
        "iss": token.claims.get("iss"),
        "jti": token.claims.get("jti")
    }

if __name__ == "__main__":
    mcp.run(transport="http", port=8000)
    
@mcp.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> PlainTextResponse:
    """This custom route can be used to run health check against MCP server.
    If you deploy load balancer, it can use /health URL to run the health check."""
    return PlainTextResponse("OK")