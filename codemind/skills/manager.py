from typing import List, Optional, Type
from .base import BaseSkill
from .security import SecuritySkill
from .ui import UIArchitectSkill
from .docs import DocumentationSkill
from .intent_cache import IntentCache

class SkillManager:
    def __init__(self, cache_path: Optional[str] = None):
        self._skills: List[BaseSkill] = [
            SecuritySkill(),
            UIArchitectSkill(),
            DocumentationSkill()
        ]
        self._active_skill: Optional[BaseSkill] = None
        self._intent_cache = IntentCache(cache_path=cache_path)

    def get_all_skills(self) -> List[BaseSkill]:
        return self._skills

    def detect_skill(self, query: str) -> Optional[BaseSkill]:
        """Automatically detect the best skill for the given query.

        Uses IntentCache to short-circuit when a similar query has
        been classified before, avoiding redundant match_intent() calls
        on every skill.
        """
        # Check cache first
        cached_name = self._intent_cache.get_cached(query)
        if cached_name is not None:
            for skill in self._skills:
                if skill.name.lower() == cached_name.lower():
                    self._active_skill = skill
                    return skill

        # Full detection
        best_skill = None
        best_score = 0.5  # Threshold

        for skill in self._skills:
            score = skill.match_intent(query)
            if score > best_score:
                best_score = score
                best_skill = skill

        # Cache the result
        self._intent_cache.store(query, best_skill.name if best_skill else None)
        self._active_skill = best_skill
        return best_skill

    def activate_skill(self, name: str) -> bool:
        for skill in self._skills:
            if skill.name.lower() == name.lower():
                self._active_skill = skill
                return True
        return False

    @property
    def active_skill(self) -> Optional[BaseSkill]:
        return self._active_skill
