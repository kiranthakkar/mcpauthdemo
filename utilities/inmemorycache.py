from fastmcp.server.context import Context
from oci.auth.signers import TokenExchangeSigner

class InMemoryCache:
    def __init__(self):
        self.cache = {}
        
    def set(self, tokenID: str, signer: TokenExchangeSigner, ctx: Context):
        """Cache token in memory"""
        ctx.set_state('signer', signer)
        
    def get(self, tokenID: str, ctx: Context) -> TokenExchangeSigner | None:
        """Retrieve token from memory"""
        return ctx.get_state('signer')