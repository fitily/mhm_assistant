"""Mémoire des dix derniers échanges et stockage par session."""
from __future__ import annotations

import threading
from collections import OrderedDict


class ConversationMemory:
    def __init__(self, max_turns: int = 10):
        self.max_turns = max_turns
        self.history: list[tuple[str, str]] = []

    def add(self, question: str, answer: str) -> None:
        self.history.append((question, answer))
        self.history = self.history[-self.max_turns:]

    def clear(self) -> None:
        self.history = []


class SessionStore:
    """Garde en mémoire vive les conversations récentes (supprime les plus anciennes)."""

    def __init__(self, max_sessions: int = 200):
        self._data: OrderedDict[str, ConversationMemory] = OrderedDict()
        self._max = max_sessions
        self._lock = threading.Lock()

    def get(self, key: str) -> ConversationMemory:
        with self._lock:
            memory = self._data.pop(key, None) or ConversationMemory()
            self._data[key] = memory
            while len(self._data) > self._max:
                self._data.popitem(last=False)
            return memory
