from fastmcp import FastMCP
from fastmcp.server.auth import OIDCProxy
import oci
from starlette.responses import PlainTextResponse
from starlette.requests import Request
from fastmcp.server.dependencies import get_access_token

from fastmcp.server.context import Context
from oci.auth.signers import TokenExchangeSigner

from utilities.diskcache import DiskCache
from utilities.rediscache import RedisTokenCache
from utilities.inmemorycache import InMemoryCache

_global_token_cache = {}

# Store tokens on disk for persistence across restarts
#token_storage = DiskCache(cache_dir="/Users/kgthakka/Downloads/agentdemo/sessionstore", ttl_hours=24)
#token_storage = RedisTokenCache(redis_url="redis://aaac3adhhqamfxfpu5p2acfahvsziks2gjlsk3pf2daire2ar2zyduq-p.redis.us-sanjose-1.oci.oraclecloud.com:6379") 
token_storage = InMemoryCache()

auth = OIDCProxy(
    config_url="https://integrator-3139143.okta.com/oauth2/default/.well-known/openid-configuration",
    client_id="0oawrvptehqbp705U697",
    client_secret="ZM2JU-wVGtY8vvoxtcRvOUs-GVs8OMeXINObpkGsykpkIgzfdByIQXbWcT0XpHdb",
    base_url="http://localhost:8000",
    required_scopes=["openid", "profile", "email"],
    #redirect_path="/auth/callback"
)

mcp = FastMCP("My MCP Server", auth=auth)

def get_oci_signer(token: str, tokenID: str, ctx: Context) -> TokenExchangeSigner:
    """Create an OCI TokenExchangeSigner using the provided token."""
    #cached = token_storage.get(tokenID,ctx)
    cached_signer = _global_token_cache.get(tokenID)
    print(f"Global cached signer: {cached_signer}")
    if cached_signer:
        print(f"Using globally cached signer for token ID: {tokenID}")
        return cached_signer
    """
    cached_signer = ctx.get_state('signer')
    print(f"Cached signer from context: {cached_signer}")
    print(f"Context Session ID: {ctx.session_id}")
    if cached_signer:
        print(f"Using cached signer for token ID: {tokenID}")
        return cached_signer
    """
    print(f"Creating new signer for token ID: {tokenID}")
    signer = TokenExchangeSigner(
        jwt_or_func=token,
        oci_domain_id="idcs-c124f391ebad4514b859eeab5e3d7b08",
        client_id="39f4950e34674d1cb71c3e025d2d9030",
        client_secret="idcscs-19fd401d-1293-49cc-aa31-4fc62c713628"
    )
    print(f"Signer created: {signer}")
    _global_token_cache[tokenID] = signer
    print(f"Signer cached globally for token ID: {tokenID}")
    #ctx.set_state('signer', signer)
    signerfromstate = _global_token_cache.get(tokenID)
    print(f"Signer from context after setting: {signerfromstate}")
    #token_storage.set(tokenID, signer, ctx)
    return signer


@mcp.tool
def get_os_namespace(ctx: Context) -> str:
    
    token = get_access_token()
    tokenID = token.claims.get("jti")
    ac_token = token.token
    signer = get_oci_signer(ac_token, tokenID, ctx)
    region = "us-sanjose-1"
    object_storage_client = oci.object_storage.ObjectStorageClient(config={'region': region}, signer=signer)

    # Get the namespace
    namespace_response = object_storage_client.get_namespace()
    namespace_name = namespace_response.data
    return namespace_name
    

@mcp.tool
def greet(name: str, ctx: Context) -> str:
    print(f"Context info: {ctx.info}")
    print(f"Context user: {ctx.session.client_params}")
    return f"Hello, {name}!"

@mcp.tool
def whoami(ctx: Context) -> str:
    """Get the authenticated user's info"""
    token = get_access_token()
    user = token.claims.get("sub")
    return f"You are User: {user}"

@mcp.tool
async def get_token() -> str:
    """Get the authenticated user's access token."""
    token = get_access_token()
    return token.token

@mcp.tool
async def get_access_token_claims() -> dict:
    """Get the authenticated user's access token claims."""
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
    return PlainTextResponse("OK")