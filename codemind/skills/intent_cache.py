"""Intent discovery cache for skill detection.

Caches query-to-skill mappings so repeated or similar queries skip
re-running match_intent() on every skill. Uses keyword-overlap
similarity to short-circuit when a cached query is sufficiently
similar to the new one.

Usage:
    cache = IntentCache()
    skill = cache.get_cached(query)
    if skill is None:
        skill = skill_manager.detect_skill(query)
        cache.store(query, skill)
"""

import hashlib
import json
import os
import re
from typing import Optional, List, Dict, Any, Set

CACHE_FILE = ".codemind_intent_cache.json"
SIMILARITY_THRESHOLD = 0.85


def _tokenize(text: str) -> Set[str]:
    """Extract lowercase keyword tokens from a query."""
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def _jaccard(a: Set[str], b: Set[str]) -> float:
    """Jaccard similarity between two token sets."""
    if not a or not b:
        return 0.0
    intersection = len(a & b)
    union = len(a | b)
    return intersection / union if union else 0.0


class IntentCache:
    """File-based intent-to-skill cache.

    Stores {query_hash: {query: str, skill: str, tokens: [str]}}.
    On lookup, computes Jaccard similarity against cached queries;
    returns the cached skill name if similarity >= threshold.
    """

    def __init__(self, cache_path: Optional[str] = None):
        self.cache_path = cache_path or os.path.join(os.getcwd(), CACHE_FILE)
        self._cache: Dict[str, Dict[str, Any]] = self._load()

    def _load(self) -> Dict[str, Dict[str, Any]]:
        try:
            with open(self.cache_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _save(self) -> None:
        try:
            with open(self.cache_path, "w", encoding="utf-8") as f:
                json.dump(self._cache, f, indent=2)
        except OSError:
            pass

    def get_cached(self, query: str) -> Optional[str]:
        """Return cached skill name if a similar query exists, else None."""
        tokens = _tokenize(query)
        if not tokens:
            return None

        best_sim = 0.0
        best_skill = None
        for entry in self._cache.values():
            cached_tokens = set(entry.get("tokens", []))
            sim = _jaccard(tokens, cached_tokens)
            if sim >= SIMILARITY_THRESHOLD and sim > best_sim:
                best_sim = sim
                best_skill = entry.get("skill")

        return best_skill

    def store(self, query: str, skill_name: Optional[str]) -> None:
        """Store a query-to-skill mapping."""
        if skill_name is None:
            return
        key = hashlib.sha256(query.encode("utf-8")).hexdigest()[:16]
        self._cache[key] = {
            "query": query,
            "skill": skill_name,
            "tokens": sorted(_tokenize(query)),
        }
        self._save()

    def invalidate(self, query: str) -> None:
        """Remove cached entries matching the query."""
        tokens = _tokenize(query)
        keys_to_remove = []
        for key, entry in self._cache.items():
            if _jaccard(tokens, set(entry.get("tokens", []))) >= SIMILARITY_THRESHOLD:
                keys_to_remove.append(key)
        for key in keys_to_remove:
            del self._cache[key]
        self._save()

    def clear(self) -> None:
        """Clear the entire cache."""
        self._cache = {}
        self._save()

    def stats(self) -> Dict[str, int]:
        return {"entries": len(self._cache)}