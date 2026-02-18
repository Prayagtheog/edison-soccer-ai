import os
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict
from dotenv import load_dotenv

load_dotenv()

# In-memory session store
_sessions: Dict[str, dict] = {}

def verify_password(password: str) -> bool:
    coach_password = os.environ.get("COACH_PASSWORD", "eagles2026")
    return password == coach_password

def create_session_token(coach_name: str = "Coach") -> str:
    token = secrets.token_hex(32)
    _sessions[token] = {
        "coach": coach_name,
        "created_at": datetime.utcnow().isoformat(),
        "expires_at": (datetime.utcnow() + timedelta(hours=24)).isoformat()
    }
    return token

def validate_token(token: str) -> Optional[dict]:
    session = _sessions.get(token)
    if not session:
        return None
    expires = datetime.fromisoformat(session["expires_at"])
    if datetime.utcnow() > expires:
        del _sessions[token]
        return None
    return session

def invalidate_token(token: str):
    _sessions.pop(token, None)