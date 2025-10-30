from pathlib import Path
from datetime import datetime, timedelta
import json
import hashlib

class DiskCache:
    def __init__(self, cache_dir: str = "./cache", ttl_hours: int = 24):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.ttl = timedelta(hours=ttl_hours)
    
    def _get_cache_path(self, key: str) -> Path:
        """Generate cache file path from key"""
        key_hash = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / f"{key_hash}.json"
    
    def get(self, key: str):
        """Get value from cache if not expired"""
        cache_path = self._get_cache_path(key)
        
        if not cache_path.exists():
            return None
        
        try:
            with open(cache_path, 'r') as f:
                data = json.load(f)
            
            # Check expiry
            cached_time = datetime.fromisoformat(data['timestamp'])
            if datetime.now() - cached_time > self.ttl:
                cache_path.unlink()  # Delete expired cache
                return None
            
            return data['value']
        except (json.JSONDecodeError, KeyError, ValueError):
            return None
    
    def set(self, key: str, value):
        """Store value in cache"""
        cache_path = self._get_cache_path(key)
        
        data = {
            'timestamp': datetime.now().isoformat(),
            'value': value
        }
        
        with open(cache_path, 'w') as f:
            json.dump(data, f)
    
    def clear(self):
        """Clear all cache files"""
        for cache_file in self.cache_dir.glob("*.json"):
            cache_file.unlink()