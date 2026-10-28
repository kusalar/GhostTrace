"""Exact-command approval verification and token lifecycle for GhostTrace Guardian."""

from __future__ import annotations

import hashlib
import hmac
import secrets
import time
import uuid
from pathlib import Path

from ghosttrace.guardian.schemas import ApprovalRequest, ApprovalStatus, CommandAnalysis, RiskLevel


class ApprovalManager:
    """Manages short-lived, single-use, cryptographically bound approval requests."""

    def __init__(self, default_ttl_seconds: float = 60.0) -> None:
        self.default_ttl_seconds = default_ttl_seconds
        self._session_secret = secrets.token_bytes(32)
        self._pending_requests: dict[str, ApprovalRequest] = {}

    def _compute_digest(
        self,
        analysis: CommandAnalysis,
        working_dir: str,
        policy_fingerprint: str,
    ) -> str:
        """Calculate HMAC-SHA256 digest sealing command details and execution context."""
        canonical_dir = str(Path(working_dir).resolve())
        args_str = " ".join(analysis.args)
        payload = (
            f"{analysis.original_command}|{analysis.normalized_command}|"
            f"{analysis.executable or ''}|{args_str}|{canonical_dir}|"
            f"{analysis.risk_level.value}|{policy_fingerprint}"
        )
        return hmac.new(self._session_secret, payload.encode("utf-8"), hashlib.sha256).hexdigest()

    def create_request(
        self,
        analysis: CommandAnalysis,
        working_dir: str,
        policy_fingerprint: str,
        ttl_seconds: float | None = None,
    ) -> ApprovalRequest:
        """Create a new short-lived approval request for an eligible command.

        Raises:
            PermissionError: If command risk level is HIGH or BLOCKED, or execution is prohibited.
        """
        if not analysis.is_permitted:
            msg = (
                "Cannot issue approval for non-permitted command with risk level "
                f"{analysis.risk_level.value}."
            )
            raise PermissionError(msg)

        if analysis.risk_level in (RiskLevel.HIGH, RiskLevel.BLOCKED):
            msg = (
                f"Commands classified as {analysis.risk_level.value} cannot be approved "
                "under safety policy."
            )
            raise PermissionError(msg)

        canonical_dir = str(Path(working_dir).resolve())
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl_seconds
        now = time.time()
        token = uuid.uuid4().hex[:10]

        digest = self._compute_digest(analysis, canonical_dir, policy_fingerprint)

        request = ApprovalRequest(
            token=token,
            analysis=analysis,
            working_dir=canonical_dir,
            created_at=now,
            expires_at=now + ttl,
            status=ApprovalStatus.PENDING,
            digest=digest,
        )

        self._pending_requests[token] = request
        return request

    def validate_and_consume(
        self,
        token: str,
        command: str,
        working_dir: str,
        policy_fingerprint: str,
    ) -> tuple[bool, str, ApprovalRequest | None]:
        """Validate approval token integrity and consume it upon successful verification.

        Guarantees single-use semantics: the token is removed upon evaluation.
        """
        clean_token = token.strip()
        if clean_token not in self._pending_requests:
            return (
                False,
                f"Approval token '{clean_token}' not found, already consumed, or invalid.",
                None,
            )

        request = self._pending_requests.pop(clean_token)
        now = time.time()

        # 1. Check expiration
        if now > request.expires_at:
            expired_req = request.model_copy(update={"status": ApprovalStatus.EXPIRED})
            return (
                False,
                f"Approval token '{clean_token}' has expired. "
                "Re-run command to request fresh approval.",
                expired_req,
            )

        # 2. Recompute digest and verify exact command & context integrity
        canonical_dir = str(Path(working_dir).resolve())
        recomputed_digest = self._compute_digest(
            request.analysis, canonical_dir, policy_fingerprint
        )

        # Confirm command string matches analysis original command
        if command.strip() != request.analysis.original_command.strip():
            rejected_req = request.model_copy(update={"status": ApprovalStatus.REJECTED})
            return (
                False,
                "Approval token mismatch: command string does not match the approved command.",
                rejected_req,
            )

        if not hmac.compare_digest(recomputed_digest, request.digest):
            rejected_req = request.model_copy(update={"status": ApprovalStatus.REJECTED})
            return (
                False,
                "Approval integrity check failed: execution context or policy has changed.",
                rejected_req,
            )

        approved_req = request.model_copy(update={"status": ApprovalStatus.APPROVED})
        return True, "Approval confirmed.", approved_req

    def cancel_request(self, token: str | None = None) -> tuple[bool, str]:
        """Cancel a pending approval request or clear all pending requests."""
        if token:
            clean_token = token.strip()
            if clean_token in self._pending_requests:
                del self._pending_requests[clean_token]
                return True, f"Approval request '{clean_token}' cancelled."
            return False, f"Approval request '{clean_token}' not found."

        count = len(self._pending_requests)
        self._pending_requests.clear()
        return True, f"All pending approval requests cancelled ({count} removed)."

    def get_request(self, token: str) -> ApprovalRequest | None:
        """Lookup an active pending approval request by token without consuming it."""
        return self._pending_requests.get(token.strip())

    def get_latest_pending(self) -> ApprovalRequest | None:
        """Return the most recently created active pending approval request, if any."""
        if not self._pending_requests:
            return None
        # Return last inserted request
        return next(reversed(self._pending_requests.values()))

    @property
    def pending_count(self) -> int:
        """Return the count of active pending approval requests."""
        return len(self._pending_requests)
