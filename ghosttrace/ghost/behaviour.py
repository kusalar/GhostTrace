"""Context-aware behaviour selection and conversational guidance for GhostTrace."""

from __future__ import annotations

import re

from ghosttrace.ghost.profiles import PersonalityProfile
from ghosttrace.ghost.schemas import InteractionContext

# Keyword and pattern matchers for contextual classification
_GREETING_PATTERNS = re.compile(
    r"\b(hello|hi|hey|greetings|who are you|what are you|good (morning|afternoon|evening|day))\b",
    re.IGNORECASE,
)
_DANGEROUS_PATTERNS = re.compile(
    r"(rm\s+-rf|del\s+/[fqs]|format\s+[a-z]:|drop\s+database|drop\s+table|"
    r"chmod\s+777|mkfs|dd\s+if=|:\(\)\s*\{\s*:\|:&\s*\};:|truncate\s+table)",
    re.IGNORECASE,
)
_ERROR_PATTERNS = re.compile(
    r"\b(traceback|exception|error|failed|failure|crashed|segfault|"
    r"syntaxerror|typeerror|valueerror|nullpointer|panicked)\b",
    re.IGNORECASE,
)
_DEBUG_PATTERNS = re.compile(
    r"\b(debug|investigate|troubleshoot|fix this|why does this (fail|error|break)|"
    r"what('s| is) wrong with|find the bug|stack\s*trace)\b",
    re.IGNORECASE,
)
_SUCCESS_PATTERNS = re.compile(
    r"\b(it worked|fixed it|that worked|solved|success|"
    r"working now|passed all tests|thank you|thanks)\b",
    re.IGNORECASE,
)
_TECHNICAL_PATTERNS = re.compile(
    r"\b(how (to|do i)|what is|explain|difference between|implement|write|refactor|"
    r"python|rust|c\+\+|javascript|typescript|docker|git|linux|windows|powershell|"
    r"sql|database|api|async|thread|function|class|decorator|generator)\b",
    re.IGNORECASE,
)


def classify_interaction_context(
    query: str,
    last_context: InteractionContext | None = None,
) -> InteractionContext:
    """Classify user query into an InteractionContext using rule-based heuristics."""
    clean = query.strip()
    if not clean:
        return InteractionContext.ORDINARY_CONVERSATION

    if _DANGEROUS_PATTERNS.search(clean):
        return InteractionContext.POTENTIALLY_DANGEROUS_INSTRUCTION

    if _DEBUG_PATTERNS.search(clean):
        return InteractionContext.DEBUGGING

    if _ERROR_PATTERNS.search(clean):
        return InteractionContext.ERROR_ENCOUNTERED

    if _SUCCESS_PATTERNS.search(clean):
        return InteractionContext.SUCCESSFUL_OPERATION

    if _GREETING_PATTERNS.search(clean) and len(clean.split()) <= 8:
        return InteractionContext.GREETING

    if _TECHNICAL_PATTERNS.search(clean) or "?" in clean:
        return InteractionContext.TECHNICAL_QUESTION

    return InteractionContext.ORDINARY_CONVERSATION


def get_behavioural_instructions(
    context: InteractionContext,
    profile: PersonalityProfile,
) -> str:
    """Return behavioural guidance for prompt injection based on interaction context."""
    match context:
        case InteractionContext.GREETING:
            return (
                "CONTEXT: The user has initiated a greeting.\n"
                f"GUIDELINES: Respond with a brief, atmospheric greeting matching your identity "
                f"as the {profile.name}. Keep it concise (1-2 sentences) and offer assistance "
                "with programming or terminal tasks."
            )

        case InteractionContext.TECHNICAL_QUESTION:
            return (
                "CONTEXT: The user has asked a technical programming or systems question.\n"
                "GUIDELINES: Prioritize complete technical accuracy, clarity, and well-structured "
                f"code. Express your {profile.name} identity through subtle word choices, "
                "framing, and tone, but NEVER allow personality banter to obscure explanations "
                "or clutter code snippets."
            )

        case InteractionContext.DEBUGGING:
            return (
                "CONTEXT: The user is debugging code or investigating unexpected behavior.\n"
                "GUIDELINES: Adopt an analytical, methodical approach. Deconstruct the problem "
                "step by step, isolate potential failure modes, suggest diagnostic checks, "
                "and provide the exact fix with clear rationale."
            )

        case InteractionContext.ERROR_ENCOUNTERED:
            return (
                "CONTEXT: An error, traceback, or failure was presented.\n"
                "GUIDELINES: Maintain steady composure. Explain precisely why the error occurred "
                "without condescension or melodrama, and offer clear, direct remediation steps."
            )

        case InteractionContext.POTENTIALLY_DANGEROUS_INSTRUCTION:
            return (
                "CONTEXT: CRITICAL SAFETY ALERT - The user mentioned a potentially destructive "
                "or risky operation.\n"
                "GUIDELINES: Safety and clarity completely supersede personality roleplay. "
                "Prominently warn about potential data destruction, system impairment, or security "
                "risks. Explain the exact hazards and recommend a safe, verified alternative "
                "before any other discussion."
            )

        case InteractionContext.SUCCESSFUL_OPERATION:
            return (
                "CONTEXT: The user confirmed a successful resolution or completed milestone.\n"
                "GUIDELINES: Acknowledge the success with quiet satisfaction fitting your persona. "
                "Offer clean next steps or potential edge-case hardening without being pushy."
            )

        case InteractionContext.REPEATED_QUESTION:
            return (
                "CONTEXT: The user is asking for clarification or revisiting a previous topic.\n"
                "GUIDELINES: Patiently re-explain from a different perspective with a concrete, "
                "minimal example. Avoid repetition and focus on addressing what might have "
                "caused confusion."
            )

        case InteractionContext.LONG_IDLE_GAP:
            return (
                "CONTEXT: The session resumed after an idle period.\n"
                "GUIDELINES: Re-engage with a subtle atmospheric acknowledgment of the silence "
                "breaking, and ask how you can assist with their code."
            )

        case InteractionContext.MODEL_UNAVAILABLE:
            return (
                "CONTEXT: The local language model or inference runtime is currently unavailable.\n"
                "GUIDELINES: Honestly and directly state that your cognitive subsystem is offline. "
                "Do not pretend to be able to analyze code without the model."
            )

        case InteractionContext.ORDINARY_CONVERSATION:
            return (
                "CONTEXT: General conversational inquiry.\n"
                f"GUIDELINES: Converse naturally in the voice of the {profile.name}. "
                "Remain polite, concise, and gently steer toward programming or development topics."
            )
