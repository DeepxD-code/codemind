"""Tests for intent discovery cache."""

import os
import tempfile
import pytest

from codemind.skills.intent_cache import IntentCache, _tokenize, _jaccard, SIMILARITY_THRESHOLD


class TestTokenize:
    def test_basic(self):
        assert _tokenize("Hello World 123") == {"hello", "world", "123"}

    def test_empty(self):
        assert _tokenize("") == set()

    def test_special_chars(self):
        assert _tokenize("fix: SQL-injection!") == {"fix", "sql", "injection"}


class TestJaccard:
    def test_identical(self):
        assert _jaccard({"a", "b"}, {"a", "b"}) == 1.0

    def test_disjoint(self):
        assert _jaccard({"a", "b"}, {"c", "d"}) == 0.0

    def test_partial(self):
        sim = _jaccard({"a", "b", "c"}, {"a", "b", "d"})
        assert 0.0 < sim < 1.0

    def test_empty(self):
        assert _jaccard(set(), {"a"}) == 0.0


class TestIntentCache:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.cache_path = os.path.join(self.tmpdir, ".codemind_intent_cache.json")
        self.cache = IntentCache(cache_path=self.cache_path)

    def test_get_cached_returns_none_for_empty(self):
        assert self.cache.get_cached("hello world") is None

    def test_store_and_retrieve_exact(self):
        self.cache.store("fix sql injection", "SecuritySkill")
        result = self.cache.get_cached("fix sql injection")
        assert result == "SecuritySkill"

    def test_store_and_retrieve_similar(self):
        base = "fix sql injection vulnerability in user authentication code with parameterized queries"
        self.cache.store(base, "SecuritySkill")
        # Same query with one extra stopword-level token still above threshold
        result = self.cache.get_cached(base + " now")
        assert result == "SecuritySkill"

    def test_no_match_for_dissimilar(self):
        self.cache.store("fix sql injection vulnerability", "SecuritySkill")
        result = self.cache.get_cached("design a button component")
        assert result is None

    def test_store_none_skill_noop(self):
        self.cache.store("query", None)
        assert self.cache.get_cached("query") is None
        assert self.cache.stats()["entries"] == 0

    def test_invalidate(self):
        self.cache.store("fix sql injection", "SecuritySkill")
        self.cache.invalidate("fix sql injection")
        assert self.cache.get_cached("fix sql injection") is None

    def test_clear(self):
        self.cache.store("query1", "SecuritySkill")
        self.cache.store("query2", "UIArchitectSkill")
        self.cache.clear()
        assert self.cache.stats()["entries"] == 0

    def test_stats(self):
        self.cache.store("q1", "SecuritySkill")
        assert self.cache.stats()["entries"] == 1

    def test_persistence(self):
        self.cache.store("persist query", "SecuritySkill")
        cache2 = IntentCache(cache_path=self.cache_path)
        assert cache2.get_cached("persist query") == "SecuritySkill"

    def test_corrupt_cache_handled(self):
        with open(self.cache_path, "w") as f:
            f.write("not valid json{{{")
        cache = IntentCache(cache_path=self.cache_path)
        assert cache.get_cached("query") is None