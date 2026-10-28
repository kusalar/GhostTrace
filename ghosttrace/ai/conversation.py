"""In-memory conversation history management for GhostTrace AI."""

from __future__ import annotations

import logging

from ghosttrace.ai.prompts import get_developer_system_prompt
from ghosttrace.ai.schemas import ChatMessage, ChatRole

logger = logging.getLogger("ghosttrace.ai.conversation")


class ConversationManager:
    """Manages in-memory conversation history, prompt limits, and older message trimming."""

    def __init__(
        self,
        system_prompt: str | None = None,
        history_limit: int = 10,
    ) -> None:
        self._system_prompt = system_prompt or get_developer_system_prompt()
        self._history_limit = max(1, history_limit)
        self._messages: list[ChatMessage] = []
        self.reset()

    @property
    def history_limit(self) -> int:
        """Return the maximum number of exchanges retained in memory."""
        return self._history_limit

    @property
    def system_prompt(self) -> str:
        """Return the active system prompt."""
        return self._system_prompt

    def update_system_prompt(self, new_prompt: str) -> None:
        """Update system prompt in-place while preserving existing conversation history."""
        clean = new_prompt.strip()
        if not clean:
            return
        self._system_prompt = clean
        if self._messages and self._messages[0].role == ChatRole.SYSTEM:
            self._messages[0] = ChatMessage(role=ChatRole.SYSTEM, content=clean)
        else:
            self._messages.insert(0, ChatMessage(role=ChatRole.SYSTEM, content=clean))
        logger.debug("Active system prompt updated in-place.")

    def reset(self) -> None:
        """Clear all conversation history and re-insert the initial system prompt."""
        self._messages = [ChatMessage(role=ChatRole.SYSTEM, content=self._system_prompt)]
        logger.debug("Conversation context reset to initial system prompt.")

    def add_user_message(self, content: str) -> None:
        """Add a user message to the conversation and trim if exceeding history limit."""
        clean = content.strip()
        if not clean:
            return
        self._messages.append(ChatMessage(role=ChatRole.USER, content=clean))
        self._trim_if_needed()

    def add_assistant_message(self, content: str) -> None:
        """Add an assistant response to the conversation and trim if exceeding history limit."""
        clean = content.strip()
        if not clean:
            return
        self._messages.append(ChatMessage(role=ChatRole.ASSISTANT, content=clean))
        self._trim_if_needed()

    def get_messages(self) -> list[ChatMessage]:
        """Return a copy of the current message list."""
        return list(self._messages)

    def get_messages_for_llm(self) -> list[dict[str, str]]:
        """Return messages formatted as dictionaries for llama-cpp create_chat_completion."""
        return [{"role": m.role.value, "content": m.content} for m in self._messages]

    @property
    def exchange_count(self) -> int:
        """Return the number of user messages recorded in current session."""
        return sum(1 for m in self._messages if m.role == ChatRole.USER)

    @property
    def total_messages(self) -> int:
        """Return total count of messages including system prompt."""
        return len(self._messages)

    def _trim_if_needed(self) -> None:
        """Enforce history limit by pruning oldest messages while preserving system prompt."""
        # Non-system messages
        non_system = [m for m in self._messages if m.role != ChatRole.SYSTEM]
        max_messages = self._history_limit * 2

        if len(non_system) > max_messages:
            excess = len(non_system) - max_messages
            pruned_non_system = non_system[excess:]
            system_msg = self._messages[0]
            self._messages = [system_msg, *pruned_non_system]
            logger.debug("Pruned %d older messages from conversation history.", excess)
