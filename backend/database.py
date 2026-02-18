import json
import os
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any

DB_FILE = os.path.join(os.path.dirname(__file__), "coach_data.json")

def _load() -> dict:
    if not os.path.exists(DB_FILE):
        return {"player_notes": [], "injuries": [], "game_notes": [], "scouting_reports": [], "custom_player_data": []}
    try:
        with open(DB_FILE, "r") as f:
            return json.load(f)
    except:
        return {"player_notes": [], "injuries": [], "game_notes": [], "scouting_reports": [], "custom_player_data": []}

def _save(data: dict):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=2)

# ── PLAYER NOTES ──
def get_player_notes(player_name: Optional[str] = None) -> List[dict]:
    db = _load()
    notes = db.get("player_notes", [])
    if player_name:
        notes = [n for n in notes if player_name.lower() in n.get("player_name", "").lower()]
    return sorted(notes, key=lambda x: x.get("created_at", ""), reverse=True)

def add_player_note(player_name: str, note: str, category: str = "general", coach: str = "Coach") -> dict:
    db = _load()
    entry = {
        "id": str(uuid.uuid4()),
        "player_name": player_name,
        "note": note,
        "category": category,
        "coach": coach,
        "created_at": datetime.utcnow().isoformat()
    }
    db["player_notes"].append(entry)
    _save(db)
    return entry

def delete_player_note(note_id: str):
    db = _load()
    db["player_notes"] = [n for n in db["player_notes"] if n.get("id") != note_id]
    _save(db)

# ── INJURIES ──
def get_injuries(active_only: bool = True) -> List[dict]:
    db = _load()
    injuries = db.get("injuries", [])
    if active_only:
        injuries = [i for i in injuries if i.get("active", True)]
    return sorted(injuries, key=lambda x: x.get("created_at", ""), reverse=True)

def add_injury(player_name: str, injury_type: str, expected_return: Optional[str] = None, notes: str = "") -> dict:
    db = _load()
    entry = {
        "id": str(uuid.uuid4()),
        "player_name": player_name,
        "injury_type": injury_type,
        "expected_return": expected_return,
        "notes": notes,
        "active": True,
        "created_at": datetime.utcnow().isoformat()
    }
    db["injuries"].append(entry)
    _save(db)
    return entry

def resolve_injury(injury_id: str):
    db = _load()
    for i in db["injuries"]:
        if i.get("id") == injury_id:
            i["active"] = False
            i["resolved_at"] = datetime.utcnow().isoformat()
    _save(db)

# ── GAME NOTES ──
def get_game_notes(opponent: Optional[str] = None) -> List[dict]:
    db = _load()
    notes = db.get("game_notes", [])
    if opponent:
        notes = [n for n in notes if opponent.lower() in n.get("opponent", "").lower()]
    return sorted(notes, key=lambda x: x.get("created_at", ""), reverse=True)

def add_game_note(opponent: str, note: str, game_date: Optional[str] = None, category: str = "general") -> dict:
    db = _load()
    entry = {
        "id": str(uuid.uuid4()),
        "opponent": opponent,
        "note": note,
        "game_date": game_date,
        "category": category,
        "created_at": datetime.utcnow().isoformat()
    }
    db["game_notes"].append(entry)
    _save(db)
    return entry

# ── SCOUTING REPORTS ──
def get_scouting_reports(opponent: Optional[str] = None) -> List[dict]:
    db = _load()
    reports = db.get("scouting_reports", [])
    if opponent:
        reports = [r for r in reports if opponent.lower() in r.get("opponent", "").lower()]
    return sorted(reports, key=lambda x: x.get("created_at", ""), reverse=True)

def add_scouting_report(opponent: str, formation: Optional[str] = None, key_players: Optional[str] = None,
                         strengths: Optional[str] = None, weaknesses: Optional[str] = None,
                         tactical_notes: Optional[str] = None) -> dict:
    db = _load()
    entry = {
        "id": str(uuid.uuid4()),
        "opponent": opponent,
        "formation": formation,
        "key_players": key_players,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "tactical_notes": tactical_notes,
        "created_at": datetime.utcnow().isoformat()
    }
    db["scouting_reports"].append(entry)
    _save(db)
    return entry

# ── CUSTOM PLAYER DATA ──
def get_custom_player_data(player_name: Optional[str] = None) -> List[dict]:
    db = _load()
    players = db.get("custom_player_data", [])
    if player_name:
        players = [p for p in players if player_name.lower() in p.get("player_name", "").lower()]
    return players

def upsert_custom_player_data(player_name: str, **kwargs) -> dict:
    db = _load()
    players = db.get("custom_player_data", [])
    existing = next((p for p in players if p["player_name"].lower() == player_name.lower()), None)
    if existing:
        for k, v in kwargs.items():
            if v is not None:
                existing[k] = v
        existing["updated_at"] = datetime.utcnow().isoformat()
        entry = existing
    else:
        entry = {"id": str(uuid.uuid4()), "player_name": player_name, "created_at": datetime.utcnow().isoformat()}
        for k, v in kwargs.items():
            if v is not None:
                entry[k] = v
        players.append(entry)
    db["custom_player_data"] = players
    _save(db)
    return entry

# ── ALL COACH CONTEXT (for AI) ──
def get_all_coach_context() -> dict:
    db = _load()
    return {
        "active_injuries": get_injuries(active_only=True),
        "player_notes": get_player_notes(),
        "scouting_reports": get_scouting_reports(),
        "game_notes": get_game_notes(),
        "custom_player_data": get_custom_player_data()
    }