import re
import logging
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any

from db.session import async_session_factory
from db.models import SecurityIncident

logger = logging.getLogger(__name__)

# Heuristic patterns for adversarial prompts and system prompt bypass attempts
INJECTION_PATTERNS = [
    (r"(?i)(ignore|disregard|forget|override)\s+(all\s+)?(previous|prior|above|system)\s+(instructions|prompts|rules|guidelines|commands)", "SYSTEM_OVERRIDE_DIRECTIVE"),
    (r"(?i)(reveal|show|print|display|dump|leak|output)\s+(your\s+)?(system\s+prompt|initial\s+prompt|hidden\s+instructions|developer\s+mode)", "PROMPT_EXTRACTION_ATTEMPT"),
    (r"(?i)<\|im_start\|>|<\|im_end\|>|\[INST\]|\[/INST\]|<<SYS>>|<</SYS>>", "TOKEN_DELIMITER_INJECTION"),
    (r"(?i)(you\s+are\s+now\s+in\s+developer\s+mode|dan\s+mode|jailbreak|bypass\s+all\s+(filters|rules|safety))", "JAILBREAK_FRAMEWORK"),
    (r"(?i)(pretend\s+you\s+are\s+unrestricted|act\s+as\s+an\s+unfiltered|behave\s+as\s+an\s+evil)", "ROLEPLAY_SAFETY_BYPASS"),
    (r"(?i)(drop\s+table|union\s+select|;\s*delete\s+from|exec\s*\(|eval\s*\()", "SQL_CODE_INJECTION"),
]

def detect_prompt_injection(text: str) -> Optional[Dict[str, str]]:
    """
    Scans incoming text for adversarial prompt injection or bypass signatures.
    Returns matched rule and snippet if detected, None otherwise.
    """
    if not text or not isinstance(text, str):
        return None

    for pattern, rule_name in INJECTION_PATTERNS:
        match = re.search(pattern, text)
        if match:
            return {
                "rule": rule_name,
                "snippet": match.group(0),
                "matched_text": text[:200]
            }
    return None

async def log_security_event(
    event_type: str,
    severity: str = "MEDIUM",
    client_ip: Optional[str] = None,
    user_identifier: Optional[str] = None,
    endpoint: Optional[str] = None,
    detail: Optional[str] = None,
    action_taken: str = "BLOCKED"
) -> Optional[str]:
    """
    Asynchronously records a security incident into the database.
    Catches and suppresses errors so operational audit failures never break incoming requests.
    """
    try:
        async with async_session_factory() as session:
            incident = SecurityIncident(
                timestamp=datetime.utcnow(),
                event_type=event_type,
                severity=severity.upper(),
                client_ip=client_ip,
                user_identifier=user_identifier or "anonymous",
                endpoint=endpoint,
                detail=detail[:1500] if detail else None,
                action_taken=action_taken
            )
            session.add(incident)
            await session.commit()
            await session.refresh(incident)
            logger.warning(
                f"[SECURITY AUDIT] [{incident.severity}] {incident.event_type} "
                f"from {incident.client_ip} ({incident.user_identifier}) on {incident.endpoint}: {incident.action_taken}"
            )
            return str(incident.id)
    except Exception as e:
        logger.error(f"Failed to record security incident: {e}", exc_info=False)
        return None

def record_security_incident_bg(
    event_type: str,
    severity: str = "MEDIUM",
    client_ip: Optional[str] = None,
    user_identifier: Optional[str] = None,
    endpoint: Optional[str] = None,
    detail: Optional[str] = None,
    action_taken: str = "BLOCKED"
):
    """
    Fire-and-forget background task wrapper for security logging.
    """
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(log_security_event(
            event_type=event_type,
            severity=severity,
            client_ip=client_ip,
            user_identifier=user_identifier,
            endpoint=endpoint,
            detail=detail,
            action_taken=action_taken
        ))
    except RuntimeError:
        pass
