"""Tests for the in-memory AI conversation manager and context window trimming."""

from ghosttrace.ai.conversation import ConversationManager
from ghosttrace.ai.prompts import DEFAULT_SYSTEM_PROMPT, get_developer_system_prompt
from ghosttrace.ai.schemas import ChatRole


def test_conversation_initialization_defaults() -> None:
    """Verify default initialization sets system prompt and initial structure."""
    cm = ConversationManager(history_limit=5)
    assert cm.history_limit == 5
    assert cm.system_prompt == DEFAULT_SYSTEM_PROMPT
    assert cm.exchange_count == 0
    assert cm.total_messages == 1

    messages = cm.get_messages()
    assert len(messages) == 1
    assert messages[0].role == ChatRole.SYSTEM
    assert messages[0].content == get_developer_system_prompt()


def test_conversation_custom_system_prompt() -> None:
    """Verify custom system prompt is set correctly."""
    custom = "You are a specialized Python debugging companion."
    cm = ConversationManager(system_prompt=custom, history_limit=3)
    assert cm.system_prompt == custom
    assert cm.get_messages()[0].content == custom


def test_conversation_add_messages_and_count() -> None:
    """Verify user and assistant messages are recorded and exchange count increments."""
    cm = ConversationManager(history_limit=10)
    cm.add_user_message("Hello, who are you?")
    cm.add_assistant_message("I am GhostTrace, your local assistant.")

    assert cm.exchange_count == 1
    assert cm.total_messages == 3

    # Empty/whitespace messages must be ignored
    cm.add_user_message("   ")
    cm.add_assistant_message("")
    assert cm.exchange_count == 1
    assert cm.total_messages == 3

    llm_msgs = cm.get_messages_for_llm()
    assert len(llm_msgs) == 3
    assert llm_msgs[0] == {"role": "system", "content": cm.system_prompt}
    assert llm_msgs[1] == {"role": "user", "content": "Hello, who are you?"}
    assert llm_msgs[2] == {"role": "assistant", "content": "I am GhostTrace, your local assistant."}


def test_conversation_pruning_respects_history_limit() -> None:
    """Verify older messages are pruned when exceeding limit while system prompt is kept."""
    # history_limit = 2 means max 2 exchanges (4 messages: u1, a1, u2, a2)
    cm = ConversationManager(history_limit=2)

    cm.add_user_message("Question 1")
    cm.add_assistant_message("Answer 1")
    cm.add_user_message("Question 2")
    cm.add_assistant_message("Answer 2")
    assert cm.total_messages == 5  # System + 4

    # Add 3rd exchange - must trigger pruning
    cm.add_user_message("Question 3")
    cm.add_assistant_message("Answer 3")

    # Should retain System + (last 4 messages)
    msgs = cm.get_messages()
    assert len(msgs) == 5
    assert msgs[0].role == ChatRole.SYSTEM
    assert msgs[1].content == "Question 2"
    assert msgs[2].content == "Answer 2"
    assert msgs[3].content == "Question 3"
    assert msgs[4].content == "Answer 3"


def test_conversation_reset() -> None:
    """Verify reset() clears all history and re-instates system prompt."""
    cm = ConversationManager()
    cm.add_user_message("Question")
    cm.add_assistant_message("Answer")
    assert cm.exchange_count == 1

    cm.reset()
    assert cm.exchange_count == 0
    assert cm.total_messages == 1
    assert cm.get_messages()[0].role == ChatRole.SYSTEM
