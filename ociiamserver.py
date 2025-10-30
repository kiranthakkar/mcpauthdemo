import os

from fastmcp import Context, FastMCP
from fastmcp.server.auth.oidc_proxy import OIDCProxy
from fastmcp.server.dependencies import get_access_token

import oci
from oci.auth.signers import TokenExchangeSigner
from starlette.responses import PlainTextResponse
from starlette.requests import Request

_IDCS_DOMAIN = os.getenv("IDCS_DOMAIN")
_IDCS_CLIENT_ID = os.getenv("IDCS_CLIENT_ID")
_IDCS_CLIENT_SECRET = os.getenv("IDCS_CLIENT_SECRET")
_IDCS_WIF_CLIENT_ID = os.getenv("IDCS_WIF_CLIENT_ID")
_IDCS_WIF_CLIENT_SECRET = os.getenv("IDCS_WIF_CLIENT_SECRET")

_global_token_cache = {}

def get_oci_signer(token: str, tokenID: str) -> TokenExchangeSigner:
    """Create an OCI TokenExchangeSigner using the provided token."""
    cached_signer = _global_token_cache.get(tokenID)
    if cached_signer:
        return cached_signer
    signer = TokenExchangeSigner(
        jwt_or_func=token,
        oci_domain_id=_IDCS_DOMAIN,
        client_id=_IDCS_WIF_CLIENT_ID,
        client_secret=_IDCS_WIF_CLIENT_SECRET
    )
    _global_token_cache[tokenID] = signer
    return signer

def get_os_client(token,region) -> oci.object_storage.ObjectStorageClient:

    signer = get_oci_signer(token.token, token.claims.get("jti"))
    object_storage_client = oci.object_storage.ObjectStorageClient(config={'region': region}, signer=signer)
    return object_storage_client

auth = OIDCProxy(
    config_url=f"https://{_IDCS_DOMAIN}/.well-known/openid-configuration",
    client_id=_IDCS_CLIENT_ID,
    client_secret=_IDCS_CLIENT_SECRET,
    # FastMCP endpoint
    base_url="http://localhost:5000",
    # audience=IDCS_CLIENT_ID,
    required_scopes=["openid"],
    # redirect_path="/custom/callback",
)

mcp = FastMCP(name="My Server", auth=auth)

@mcp.tool
def get_os_namespace(ctx: Context) -> str:
    
    token = get_access_token()
    region = "us-sanjose-1"
    object_storage_client = get_os_client(token, region)

    # Get the namespace
    namespace_response = object_storage_client.get_namespace()
    namespace_name = namespace_response.data
    return namespace_name

mcp.run(transport="http", host="localhost", port=5000)

@mcp.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> PlainTextResponse:
    return PlainTextResponse("OK")