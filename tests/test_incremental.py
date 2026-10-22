"""Tests for incremental SAST scanning cache."""

import os
import json
import tempfile
import pytest

from codemind.analysis.incremental import IncrementalScanCache, _content_hash


class TestContentHash:
    def test_same_content_same_hash(self):
        assert _content_hash("hello") == _content_hash("hello")

    def test_different_content_different_hash(self):
        assert _content_hash("hello") != _content_hash("world")

    def test_hash_is_hex_string(self):
        h = _content_hash("test")
        assert len(h) == 64
        int(h, 16)  # Should not raise


class TestIncrementalScanCache:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.cache_path = os.path.join(self.tmpdir, ".codemind_scan_cache.json")
        self.cache = IncrementalScanCache(cache_path=self.cache_path)

    def test_get_cached_returns_none_for_missing(self):
        assert self.cache.get_cached("foo.py", "code") is None

    def test_store_and_retrieve(self):
        findings = [{"type": "SQL_INJECTION", "line": 5}]
        self.cache.store("foo.py", "code", findings)
        result = self.cache.get_cached("foo.py", "code")
        assert result == findings

    def test_cache_miss_on_content_change(self):
        findings = [{"type": "SQL_INJECTION", "line": 5}]
        self.cache.store("foo.py", "old code", findings)
        result = self.cache.get_cached("foo.py", "new code")
        assert result is None

    def test_invalidate(self):
        findings = [{"type": "XSS", "line": 1}]
        self.cache.store("bar.py", "code", findings)
        self.cache.invalidate("bar.py")
        assert self.cache.get_cached("bar.py", "code") is None

    def test_clear(self):
        self.cache.store("a.py", "code", [{"type": "XSS"}])
        self.cache.store("b.py", "code", [{"type": "SQL_INJECTION"}])
        self.cache.clear()
        assert self.cache.get_cached("a.py", "code") is None
        assert self.cache.get_cached("b.py", "code") is None
        assert self.cache.stats()["entries"] == 0

    def test_stats(self):
        self.cache.store("a.py", "code", [])
        assert self.cache.stats()["entries"] == 1

    def test_persistence_across_instances(self):
        findings = [{"type": "SECRET", "line": 10}]
        self.cache.store("persist.py", "code", findings)
        # Create new instance pointing to same file
        cache2 = IncrementalScanCache(cache_path=self.cache_path)
        result = cache2.get_cached("persist.py", "code")
        assert result == findings

    def test_corrupt_cache_handled(self):
        with open(self.cache_path, "w") as f:
            f.write("not valid json{{{")
        cache = IncrementalScanCache(cache_path=self.cache_path)
        assert cache.get_cached("foo.py", "code") is None

    def test_missing_cache_file_handled(self):
        cache = IncrementalScanCache(cache_path=os.path.join(self.tmpdir, "nonexistent.json"))
        assert cache.get_cached("foo.py", "code") is None