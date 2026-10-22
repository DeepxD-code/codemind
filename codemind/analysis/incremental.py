"""Incremental SAST scanning cache.

Tracks file content hashes so unchanged files skip re-analysis.
On a subsequent scan, only files whose hashes differ are re-analyzed;
cached findings are returned for unchanged files.

Usage:
    cache = IncrementalScanCache()
    findings = cache.get_cached("src/main.py", code)
    if findings is None:
        findings = analyzer.analyze(code, "python")
        cache.store("src/main.py", code, findings)
"""

import hashlib
import json
import os
from pathlib import Path
from typing import List, Optional, Dict, Any

CACHE_FILE = ".codemind_scan_cache.json"


def _content_hash(code: str) -> str:
    """Return a SHA-256 hex digest of the code content."""
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


class IncrementalScanCache:
    """File-based incremental scan cache.

    Stores ``{filename: {hash: str, findings: [...]}}`` in a JSON file.
    Thread-safe for single-process use.
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
            pass  # Cache write failure is non-fatal

    def get_cached(self, filename: str, code: str) -> Optional[List[Dict[str, Any]]]:
        """Return cached findings if the content hash matches, else None."""
        entry = self._cache.get(filename)
        if entry is None:
            return None
        if entry.get("hash") != _content_hash(code):
            return None
        return entry.get("findings")

    def store(self, filename: str, code: str, findings: List[Dict[str, Any]]) -> None:
        """Store findings keyed by filename and content hash."""
        self._cache[filename] = {
            "hash": _content_hash(code),
            "findings": findings,
        }
        self._save()

    def invalidate(self, filename: str) -> None:
        """Remove a cached entry."""
        self._cache.pop(filename, None)
        self._save()

    def clear(self) -> None:
        """Clear the entire cache."""
        self._cache = {}
        self._save()

    def stats(self) -> Dict[str, int]:
        """Return cache statistics."""
        return {"entries": len(self._cache)}