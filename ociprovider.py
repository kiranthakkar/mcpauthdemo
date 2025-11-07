"""OCI OIDC provider for FastMCP.

The pull request for the provider is submitted to fastmcp. 

This module provides OIDC Implementation to integrate MCP servers with OCI.
You only need OCI Identity Domain's discovery URL, client ID, client secret, and base URL.

Post Authentication, you get OCI IAM domain access token. That is not authorized to invoke OCI control plane.
You need to exchange the IAM domain access token for OCI UPST token to invoke OCI control plane APIs.
The sample code below has get_oci_signer function that returns OCI TokenExchangeSigner object. 
You can use the signer object to create OCI service object.

Example:
    ```python
    from fastmcp import FastMCP
    from fastmcp.server.auth.providers.ociprovider import OCIProvider
    
    import oci
    from oci.auth.signers import TokenExchangeSigner
    
    _global_token_cache = {} #In memory cache for OCI session token signer

    # Simple OCI OIDC protection
    auth = OCIProvider(
        config_url="https://{IDCS_GUID}.identity.oraclecloud.com/.well-known/openid-configuration",
        client_id="oci-iamdomain-app-client-id",
        client_secret="oci-iamdomain-app-client-secret",
        base_url="http://localhost:8000",
    )
    
    def get_oci_signer() -> TokenExchangeSigner:
    
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

    mcp = FastMCP("My Protected Server", auth=auth)
    ```
"""
from key_value.aio.protocols import AsyncKeyValue
from pydantic import AnyHttpUrl, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from fastmcp.server.auth.oidc_proxy import OIDCProxy
from fastmcp.settings import ENV_FILE
from fastmcp.utilities.auth import parse_scopes
from fastmcp.utilities.logging import get_logger
from fastmcp.utilities.types import NotSet, NotSetT

logger = get_logger(__name__)


class OCIProviderSettings(BaseSettings):
    """Settings for OCI IAM domain OIDC provider."""

    model_config = SettingsConfigDict(
        env_prefix="FASTMCP_SERVER_AUTH_OCI_",
        env_file=ENV_FILE,
        extra="ignore",
    )

    config_url: AnyHttpUrl | None = None
    client_id: str | None = None
    client_secret: SecretStr | None = None
    audience: str | None = None
    base_url: AnyHttpUrl | None = None
    issuer_url: AnyHttpUrl | None = None
    redirect_path: str | None = None
    required_scopes: list[str] | None = None
    allowed_client_redirect_uris: list[str] | None = None
    jwt_signing_key: str | None = None

    @field_validator("required_scopes", mode="before")
    @classmethod
    def _parse_scopes(cls, v):
        return parse_scopes(v)


class OCIProvider(OIDCProxy):
    """An OCI provider implementation for FastMCP.

    This provider is a complete OCI integration that's ready to use with
    just the configuration URL, client ID, client secret, audience, and base URL.

    """

    def __init__(
        self,
        *,
        config_url: AnyHttpUrl | str | NotSetT = NotSet,
        client_id: str | NotSetT = NotSet,
        client_secret: str | NotSetT = NotSet,
        audience: str | NotSetT = NotSet,
        base_url: AnyHttpUrl | str | NotSetT = NotSet,
        issuer_url: AnyHttpUrl | str | NotSetT = NotSet,
        required_scopes: list[str] | NotSetT = ["openid"],
        redirect_path: str | NotSetT = NotSet,
        allowed_client_redirect_uris: list[str] | NotSetT = NotSet,
        client_storage: AsyncKeyValue | None = None,
        jwt_signing_key: str | bytes | NotSetT = NotSet,
        require_authorization_consent: bool = False,
    ) -> None:
        """Initialize OCI OIDC provider.

        Args:
            config_url: OCI OIDC Discovery URL
            client_id: OCI Integrated Application client id
            client_secret: OCI Integrated Application client secret
            audience: OCI API audience
            base_url: Public URL where OAuth endpoints will be accessible (includes any mount path)
            issuer_url: Issuer URL for OAuth metadata (defaults to base_url). Use root-level URL
                to avoid 404s during discovery when mounting under a path.
            required_scopes: Required OCI scopes (defaults to ["openid"])
            redirect_path: Redirect path configured in OCI application
            allowed_client_redirect_uris: List of allowed redirect URI patterns for MCP clients.
        """
        settings = OCIProviderSettings.model_validate(
            {
                k: v
                for k, v in {
                    "config_url": config_url,
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "audience": audience,
                    "base_url": base_url,
                    "issuer_url": issuer_url,
                    "required_scopes": required_scopes,
                    "redirect_path": redirect_path,
                    "allowed_client_redirect_uris": allowed_client_redirect_uris,
                    "jwt_signing_key": jwt_signing_key,
                }.items()
                if v is not NotSet
            }
        )
        
        if not settings.config_url:
            raise ValueError(
                "config_url is required - set via parameter or FASTMCP_SERVER_AUTH_OCI_CONFIG_URL"
            )

        if not settings.client_id:
            raise ValueError(
                "client_id is required - set via parameter or FASTMCP_SERVER_AUTH_OCI_CLIENT_ID"
            )

        if not settings.client_secret:
            raise ValueError(
                "client_secret is required - set via parameter or FASTMCP_SERVER_AUTH_OCI_CLIENT_SECRET"
            )

        if not settings.base_url:
            raise ValueError(
                "base_url is required - set via parameter or FASTMCP_SERVER_AUTH_OCI_BASE_URL"
            )

        oci_required_scopes = settings.required_scopes or ["openid"]

        super().__init__(
            config_url=settings.config_url,
            client_id=settings.client_id,
            client_secret=settings.client_secret.get_secret_value(),
            audience=settings.audience,
            base_url=settings.base_url,
            issuer_url=settings.issuer_url,
            redirect_path=settings.redirect_path,
            required_scopes=oci_required_scopes,
            allowed_client_redirect_uris=settings.allowed_client_redirect_uris,
            client_storage=client_storage,
            jwt_signing_key=settings.jwt_signing_key,
            require_authorization_consent=require_authorization_consent,
        )
        
        

        logger.debug(
            "Initialized OCI OAuth provider for client %s with scopes: %s",
            settings.client_id,
            oci_required_scopes,
        )