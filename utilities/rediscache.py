import redis
from datetime import timedelta
from oci.auth.signers import TokenExchangeSigner

class RedisTokenCache:
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_client = redis.from_url(redis_url)
        
    def set(self, tokenID: str, signer: TokenExchangeSigner, ttl_hours: int = 24):
        """Store signer in Redis with TTL"""

        cache_key = f"mcp:token:{tokenID}"
        # Store in Redis with TTL
        self.redis_client.setex(
            cache_key,
            timedelta(hours=ttl_hours),
            signer
        )
    
    def get(self, tokenID: str):
        """Retrieve signer from Redis"""
        cache_key = f"mcp:token:{tokenID}"
        cached = self.redis_client.get(cache_key)

        if cached:
            return cached
        return None