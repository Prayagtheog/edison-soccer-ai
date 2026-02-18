from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict
import pandas as pd
from scraper import scrape_all_data, scrape_opponent_data, SEASONS, CURRENT_SEASON, PREVIOUS_SEASON
from ai_agent import get_ai_response
import database as db

app = FastAPI(title="Edison Athletics Analytics API v3")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

team_data = {}

@app.on_event("startup")
async def startup_event():
    global team_data
    print("🔄 Loading all Edison sports data (~30s for 5 sports × 5 years)...")
    team_data = scrape_all_data()
    print("✅ All data loaded")

def get_coach_session(authorization: Optional[str] = Header(None)):
    from auth import validate_token
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    session = validate_token(authorization.replace("Bearer ", ""))
    if not session:
        raise HTTPException(status_code=401, detail="Session expired")
    return session

def get_sport_data(sport: str):
    if not team_data:
        raise HTTPException(status_code=503, detail="Data still loading")
    if sport not in team_data:
        raise HTTPException(status_code=404, detail=f"Sport '{sport}' not found. Options: boys_soccer, girls_soccer, boys_basketball, girls_basketball, baseball, wrestling")
    return team_data[sport]

# ── AUTH ──
class LoginRequest(BaseModel):
    password: str
    coach_name: Optional[str] = "Coach"

@app.post("/api/auth/login")
def login(req: LoginRequest):
    from auth import verify_password, create_session_token
    if not verify_password(req.password):
        raise HTTPException(status_code=401, detail="Invalid password")
    token = create_session_token(req.coach_name)
    return {"token": token, "coach": req.coach_name, "message": "Welcome back, Coach!"}

@app.post("/api/auth/logout")
def logout(authorization: Optional[str] = Header(None)):
    from auth import invalidate_token
    if authorization and authorization.startswith("Bearer "):
        invalidate_token(authorization.replace("Bearer ", ""))
    return {"message": "Logged out"}

@app.get("/api/auth/me")
def get_me(session=Depends(get_coach_session)):
    return {"coach": session["coach"], "authenticated": True}

# ── SPORTS META ──
@app.get("/api/sports")
def list_sports():
    return {
        "sports": [
            {"key": "boys_soccer",     "name": "Boys Soccer",     "icon": "⚽"},
            {"key": "girls_soccer",    "name": "Girls Soccer",    "icon": "⚽"},
            {"key": "boys_basketball",  "name": "Boys Basketball",  "icon": "🏀"},
            {"key": "girls_basketball", "name": "Girls Basketball", "icon": "🏀"},
            {"key": "baseball",         "name": "Baseball",         "icon": "⚾"},
            {"key": "wrestling",       "name": "Wrestling",       "icon": "🤼"},
        ],
        "seasons": SEASONS,
        "current_season": CURRENT_SEASON,
    }

# ── GENERIC SPORT ENDPOINTS ──
@app.get("/api/{sport}/overview")
def sport_overview(sport: str):
    sd = get_sport_data(sport)
    cs = sd.get('current_stats')
    fixtures = sd.get('fixtures', {})
    games_df = fixtures.get('games')
    result = {"sport": sport, "season": CURRENT_SEASON, "coach": fixtures.get('coach', 'Unknown')}
    if games_df is not None and not games_df.empty:
        played = games_df[games_df['Outcome'] != '—']
        wins = len(played[played['Outcome'] == 'W'])
        losses = len(played[played['Outcome'] == 'L'])
        ties = len(played[played['Outcome'] == 'T'])
        results = played['Outcome'].tolist()
        streak_type = results[-1] if results else ""
        streak = sum(1 for r in reversed(results) if r == streak_type) if results else 0
        result["record"] = {
            "wins": wins, "losses": losses, "ties": ties,
            "record": f"{wins}-{losses}-{ties}",
            "games_played": len(played),
            "win_pct": round(wins / len(played) * 100, 1) if len(played) > 0 else 0,
            "current_streak": f"{streak}{streak_type}" if streak else "—"
        }
    if cs:
        if sport in ("boys_soccer", "girls_soccer"):
            fp = cs.get('field_players', pd.DataFrame())
            gk = cs.get('goalies', pd.DataFrame())
            if not fp.empty:
                result["scoring"] = {"total_goals": int(fp['Goals'].sum()), "total_assists": int(fp['Assists'].sum())}
            result["squad_size"] = {"field_players": len(fp), "goalkeepers": len(gk), "total": len(fp) + len(gk)}
        elif sport in ("boys_basketball", "girls_basketball"):
            pl = cs.get('players', pd.DataFrame())
            if not pl.empty:
                result["scoring"] = {"total_points": float(pl['Points'].sum()), "players": len(pl)}
                result["squad_size"] = {"total": len(pl), "players": len(pl)}
        elif sport == "baseball":
            bt = cs.get('batters', pd.DataFrame()); pt = cs.get('pitchers', pd.DataFrame())
            result["squad_size"] = {"batters": len(bt), "pitchers": len(pt), "total": len(bt)}
            result["scoring"] = {"total_hits": int(bt['H'].sum()) if not bt.empty and 'H' in bt.columns else 0}
        elif sport == "wrestling":
            wr = cs.get('wrestlers', pd.DataFrame())
            if not wr.empty:
                result["stats"] = {"total_wins": int(wr['Wins'].sum()), "total_pins": int(wr['Pins'].sum())}
                result["squad_size"] = {"total": len(wr), "wrestlers": len(wr)}
    return result

@app.get("/api/{sport}/leaderboard")
def sport_leaderboard(sport: str, limit: int = 8):
    sd = get_sport_data(sport)
    cs = sd.get('current_stats')
    if not cs:
        raise HTTPException(status_code=404, detail="No current stats")
    if sport in ("boys_soccer", "girls_soccer"):
        fp = cs.get('field_players', pd.DataFrame())
        if fp.empty: return {"top_goals": [], "top_assists": [], "top_points": []}
        return {
            "top_goals":   fp.nlargest(limit, 'Goals')[['Player', 'Goals']].to_dict('records'),
            "top_assists": fp.nlargest(limit, 'Assists')[['Player', 'Assists']].to_dict('records'),
            "top_points":  fp.nlargest(limit, 'Points')[['Player', 'Points']].to_dict('records'),
        }
    elif sport in ("boys_basketball", "girls_basketball"):
        pl = cs.get('players', pd.DataFrame())
        if pl.empty: return {}
        return {
            "top_points":   pl.nlargest(limit, 'Points')[['Player', 'Points']].to_dict('records'),
            "top_rebounds": pl.nlargest(limit, 'Rebounds')[['Player', 'Rebounds']].to_dict('records'),
            "top_assists":  pl.nlargest(limit, 'Assists')[['Player', 'Assists']].to_dict('records'),
        }
    elif sport == "baseball":
        bt = cs.get('batters', pd.DataFrame()); pt = cs.get('pitchers', pd.DataFrame())
        result = {}
        if not bt.empty:
            result["top_avg"] = bt.nlargest(limit, 'AVG')[['Player', 'AVG']].to_dict('records')
            result["top_rbi"] = bt.nlargest(limit, 'RBI')[['Player', 'RBI']].to_dict('records')
        if not pt.empty:
            result["top_k"] = pt.nlargest(limit, 'Strikeouts')[['Player', 'Strikeouts']].to_dict('records')
        return result
    elif sport == "wrestling":
        wr = cs.get('wrestlers', pd.DataFrame())
        if wr.empty: return {}
        return {
            "top_wins": wr.nlargest(limit, 'Wins')[['Player', 'Wins', 'Pins']].to_dict('records'),
            "top_pins": wr.nlargest(limit, 'Pins')[['Player', 'Pins']].to_dict('records'),
        }
    return {}

@app.get("/api/{sport}/history")
def sport_history(sport: str):
    sd = get_sport_data(sport)
    history = sd.get('history', {})
    trend = []
    for season in SEASONS:
        entry = {"season": season}
        data = history.get(season)
        if not data:
            trend.append({**entry, "data": None}); continue
        if sport in ("boys_soccer", "girls_soccer"):
            fp = data.get('field_players', pd.DataFrame())
            entry["goals"] = int(fp['Goals'].sum()) if not fp.empty else 0
            entry["assists"] = int(fp['Assists'].sum()) if not fp.empty else 0
            entry["players"] = len(fp)
            if not fp.empty:
                top = fp.nlargest(1, 'Goals').iloc[0]
                entry["top_scorer"] = {"name": top['Player'], "goals": int(top['Goals'])}
        elif sport in ("boys_basketball", "girls_basketball"):
            pl = data.get('players', pd.DataFrame())
            entry["players"] = len(pl)
            if not pl.empty:
                top = pl.nlargest(1, 'Points').iloc[0]
                entry["top_scorer"] = {"name": top['Player'], "points": float(top['Points'])}
        elif sport == "baseball":
            bt = data.get('batters', pd.DataFrame()); pt = data.get('pitchers', pd.DataFrame())
            entry["batters"] = len(bt); entry["pitchers"] = len(pt)
        elif sport == "wrestling":
            wr = data.get('wrestlers', pd.DataFrame())
            entry["wrestlers"] = len(wr)
            if not wr.empty:
                entry["total_wins"] = int(wr['Wins'].sum())
                entry["total_pins"] = int(wr['Pins'].sum())
        trend.append(entry)
    return {"sport": sport, "seasons": SEASONS, "trend": trend}

@app.get("/api/{sport}/schedule")
def sport_schedule(sport: str, filter: str = "all"):
    sd = get_sport_data(sport)
    df = sd.get('fixtures', {}).get('games', pd.DataFrame())
    if df is None or df.empty: return {"games": []}
    if filter == "upcoming": return {"games": df[df['Outcome'] == '—'].to_dict('records')}
    if filter == "recent":   return {"games": df[df['Outcome'] != '—'].tail(10).to_dict('records')}
    return {"games": df.to_dict('records')}

@app.get("/api/{sport}/goalkeepers")
def sport_goalkeepers(sport: str):
    if sport not in ("boys_soccer", "girls_soccer"):
        raise HTTPException(status_code=400, detail="Goalkeepers only for soccer")
    sd = get_sport_data(sport)
    cs = sd.get('current_stats')
    if not cs: raise HTTPException(status_code=404, detail="No data")
    return {"goalkeepers": cs.get('goalies', pd.DataFrame()).to_dict('records')}

# ── BACKWARDS COMPAT ──
@app.get("/api/team/overview")
def get_team_overview(): return sport_overview("boys_soccer")

@app.get("/api/players/leaderboard")
def get_leaderboard(limit: int = 8): return sport_leaderboard("boys_soccer", limit)

@app.get("/api/players/top-scorers")
def get_top_scorers(limit: int = 10):
    sd = get_sport_data("boys_soccer")
    cs = sd.get('current_stats')
    if not cs: raise HTTPException(status_code=404, detail="No data")
    fp = cs['field_players']
    return {"top_scorers": fp.nlargest(limit, 'Goals')[['Player', 'Year/Position', 'Goals', 'Assists', 'Points']].to_dict('records')}

@app.get("/api/players/search/{name}")
def search_player(name: str):
    if not team_data: raise HTTPException(status_code=503, detail="Loading")
    from database import get_custom_player_data, get_player_notes, get_injuries
    cs = team_data.get('current_stats')
    if not cs: return {"found": False}
    field_df = cs['field_players']; goalie_df = cs['goalies']
    m = field_df[field_df['Player'].str.contains(name, case=False, na=False)]
    if not m.empty:
        row = m.iloc[0]; pname = row['Player']
        custom = (get_custom_player_data(pname) or [{}])[0]
        notes = get_player_notes(pname)
        inj = next((i for i in get_injuries() if pname.lower() in i['player_name'].lower()), None)
        return {"found": True, "player": {
            "name": pname, "position": row['Year/Position'], "type": "field_player",
            "stats": {"goals": int(row['Goals']), "assists": int(row['Assists']), "points": int(row['Points']),
                      "minutes_played": custom.get('minutes_played'), "yellow_cards": custom.get('yellow_cards')},
            "ratings": {"fitness": custom.get('fitness_rating'), "technical": custom.get('technical_rating'), "attitude": custom.get('attitude_rating')},
            "coach_notes": notes, "current_injury": inj
        }}
    gm = goalie_df[goalie_df['Player'].str.contains(name, case=False, na=False)]
    if not gm.empty:
        row = gm.iloc[0]
        return {"found": True, "player": {"name": row['Player'], "type": "goalkeeper",
                "stats": {"saves": int(row['Saves']), "games_played": int(row['Games Played'])}}}
    return {"found": False, "message": f"No player found matching '{name}'"}

@app.get("/api/goalkeepers")
def get_goalkeepers(): return sport_goalkeepers("boys_soccer")

@app.get("/api/schedule/upcoming")
def get_upcoming(limit: int = 5):
    df = get_sport_data("boys_soccer")['fixtures']['games']
    return {"upcoming_games": df[df['Outcome'] == '—'].head(limit)[['Date', 'Opponent', 'Location']].to_dict('records')}

@app.get("/api/schedule/recent")
def get_recent(limit: int = 10):
    df = get_sport_data("boys_soccer")['fixtures']['games']
    return {"recent_games": df[df['Outcome'] != '—'].tail(limit)[['Date', 'Opponent', 'Location', 'Result', 'Outcome', 'Record']].to_dict('records')}

@app.get("/api/schedule/all")
def get_all_games():
    return {"games": get_sport_data("boys_soccer")['fixtures']['games'].to_dict('records')}

@app.get("/api/schedule/opponent/{team_name}")
def get_opponent_history(team_name: str):
    df = get_sport_data("boys_soccer")['fixtures']['games']
    og = df[df['Opponent'].str.contains(team_name, case=False, na=False)]
    if og.empty: return {"found": False}
    played = og[og['Outcome'] != '—']
    return {"found": True, "opponent": team_name, "games_played": len(played),
            "record_vs_opponent": played['Outcome'].value_counts().to_dict(),
            "games": og[['Date', 'Location', 'Result', 'Record']].to_dict('records')}

@app.get("/api/opponent/scrape/{team_name}")
def scrape_opponent(team_name: str):
    return {"found": bool(scrape_opponent_data(team_name)), "data": scrape_opponent_data(team_name)}

@app.get("/api/analytics/form")
def get_form(last_n: int = 5):
    played = get_sport_data("boys_soccer")['fixtures']['games']
    played = played[played['Outcome'] != '—'].tail(last_n)
    w = len(played[played['Outcome'] == 'W']); l = len(played[played['Outcome'] == 'L']); t = len(played[played['Outcome'] == 'T'])
    return {"last_n": last_n, "record": f"{w}-{l}-{t}", "form_string": "".join(played['Outcome'].tolist()),
            "games": played[['Date', 'Opponent', 'Result', 'Outcome']].to_dict('records')}

@app.get("/api/analytics/goal-distribution")
def get_goal_dist():
    fp = get_sport_data("boys_soccer")['current_stats']['field_players']
    scorers = fp[fp['Goals'] > 0]; total = int(fp['Goals'].sum())
    if not total: return {"message": "No goal data"}
    return {"total_goals": total, "players_with_goals": len(scorers),
            "distribution": scorers[['Player', 'Goals', 'Assists', 'Points']].sort_values('Goals', ascending=False).to_dict('records')}

@app.get("/api/comparison/year-over-year")
def compare_seasons():
    sd = get_sport_data("boys_soccer")
    cur = sd['current_stats']['field_players']
    prev = sd['previous_stats']['field_players'] if sd.get('previous_stats') else pd.DataFrame()
    cg = int(cur['Goals'].sum()); ca = int(cur['Assists'].sum())
    pg = int(prev['Goals'].sum()) if not prev.empty else 0
    pa = int(prev['Assists'].sum()) if not prev.empty else 0
    cur_top  = cur.nlargest(1, 'Goals').iloc[0]  if not cur.empty  else None
    prev_top = prev.nlargest(1, 'Goals').iloc[0] if not prev.empty else None
    return {
        "2024-2025": {"total_goals": pg, "total_assists": pa, "players": len(prev),
                      "top_scorer": {"Player": prev_top['Player'], "Goals": int(prev_top['Goals'])} if prev_top is not None else None,
                      "top_scorers": prev.nlargest(5, 'Goals')[['Player', 'Goals', 'Assists']].to_dict('records') if not prev.empty else []},
        "2025-2026": {"total_goals": cg, "total_assists": ca, "players": len(cur),
                      "top_scorer": {"Player": cur_top['Player'], "Goals": int(cur_top['Goals'])} if cur_top is not None else None,
                      "top_scorers": cur.nlargest(5, 'Goals')[['Player', 'Goals', 'Assists']].to_dict('records')},
        "change": {"goals_diff": cg - pg, "assists_diff": ca - pa,
                   "goals_change_pct": round((cg - pg) / pg * 100, 1) if pg else 0}
    }

# ── COACH PORTAL ──
class PlayerNoteRequest(BaseModel):
    player_name: Optional[str] = "Team"; note: str; category: Optional[str] = "general"

class InjuryRequest(BaseModel):
    player_name: str; injury_type: str; expected_return: Optional[str] = None; notes: Optional[str] = ""

class GameNoteRequest(BaseModel):
    opponent: str; note: str; game_date: Optional[str] = None; category: Optional[str] = "general"

class ScoutingReportRequest(BaseModel):
    opponent: str; formation: Optional[str] = None; key_players: Optional[str] = None
    strengths: Optional[str] = None; weaknesses: Optional[str] = None
    tactical_notes: Optional[str] = None; game_plan: Optional[str] = None

class PlayerStatsRequest(BaseModel):
    player_name: str; minutes_played: Optional[int] = None; yellow_cards: Optional[int] = None
    red_cards: Optional[int] = None; shots_on_target: Optional[int] = None
    key_passes: Optional[int] = None; interceptions: Optional[int] = None
    fitness_rating: Optional[int] = None; technical_rating: Optional[int] = None
    attitude_rating: Optional[int] = None; position_primary: Optional[str] = None
    jersey_number: Optional[int] = None; notes: Optional[str] = None

@app.post("/api/coach/notes")
@app.post("/api/coach/player-notes")
def coach_add_note(req: PlayerNoteRequest, session=Depends(get_coach_session)):
    from database import add_player_note
    return {"success": True, "note": add_player_note(req.player_name, req.note, req.category, session['coach'])}

@app.get("/api/coach/player-notes")
def coach_get_notes(player: Optional[str] = None, session=Depends(get_coach_session)):
    from database import get_player_notes
    return {"notes": get_player_notes(player)}

@app.delete("/api/coach/player-notes/{note_id}")
def coach_del_note(note_id: str, session=Depends(get_coach_session)):
    from database import delete_player_note
    delete_player_note(note_id); return {"success": True}

@app.get("/api/coach/injuries")
def coach_get_injuries(active_only: bool = True, session=Depends(get_coach_session)):
    from database import get_injuries
    return {"injuries": get_injuries(active_only)}

@app.post("/api/coach/injuries")
def coach_add_injury(req: InjuryRequest, session=Depends(get_coach_session)):
    from database import add_injury
    return {"success": True, "injury": add_injury(req.player_name, req.injury_type, req.expected_return, req.notes)}

@app.patch("/api/coach/injuries/{injury_id}/resolve")
def coach_resolve(injury_id: str, session=Depends(get_coach_session)):
    from database import resolve_injury
    resolve_injury(injury_id); return {"success": True}

@app.get("/api/coach/scouting")
def coach_get_scouting(opponent: Optional[str] = None, session=Depends(get_coach_session)):
    from database import get_scouting_reports
    return {"reports": get_scouting_reports(opponent)}

@app.post("/api/coach/scouting")
def coach_add_scouting(req: ScoutingReportRequest, session=Depends(get_coach_session)):
    from database import add_scouting_report
    return {"success": True, "report": add_scouting_report(req.opponent, req.formation, req.key_players, req.strengths, req.weaknesses, req.tactical_notes)}

@app.post("/api/coach/player-stats")
def coach_upsert_stats(req: PlayerStatsRequest, session=Depends(get_coach_session)):
    from database import upsert_custom_player_data
    return {"success": True, "player": upsert_custom_player_data(req.player_name, minutes_played=req.minutes_played,
        yellow_cards=req.yellow_cards, red_cards=req.red_cards, shots_on_target=req.shots_on_target,
        key_passes=req.key_passes, interceptions=req.interceptions, fitness_rating=req.fitness_rating,
        technical_rating=req.technical_rating, attitude_rating=req.attitude_rating,
        position_primary=req.position_primary, jersey_number=req.jersey_number, notes=req.notes)}

@app.get("/api/coach/dashboard")
def coach_dashboard(session=Depends(get_coach_session)):
    from database import get_injuries, get_player_notes, get_scouting_reports
    injuries = get_injuries(True); notes = get_player_notes(); scouting = get_scouting_reports()
    recent_form = []; top_performers = []
    if team_data and team_data.get('boys_soccer'):
        games_df = team_data['boys_soccer']['fixtures']['games']
        played = games_df[games_df['Outcome'] != '—']
        recent_form = played['Outcome'].tail(5).tolist()
        cs = team_data['boys_soccer'].get('current_stats')
        if cs:
            fp = cs.get('field_players', pd.DataFrame())
            if not fp.empty:
                top_performers = fp.nlargest(3, 'Goals')[['Player', 'Goals', 'Assists']].to_dict('records')
    return {
        "coach": session['coach'],
        "team_health": {"injured_count": len(injuries),
                        "active_injuries": [{"player": i["player_name"], "injury": i["injury_type"], "expected_return": i.get("expected_return")} for i in injuries]},
        "coach_notes_count": len(notes), "scouting_reports_count": len(scouting),
        "recent_form": recent_form, "top_performers": top_performers,
    }

# ── CHAT ──
class ChatRequest(BaseModel):
    message: str; conversation_history: Optional[List[Dict]] = []; is_coach: Optional[bool] = False

@app.post("/api/chat")
async def chat(request: ChatRequest):
    try:
        coach_data = {}
        try:
            coach_data = db.get_all_coach_context()
        except:
            pass

        from ai_agent import get_ai_response
        response = get_ai_response(
            message=request.message,
            conversation_history=request.conversation_history or [],
            team_data=team_data,
            coach_data=coach_data,
            is_coach=request.is_coach or False,
        )
        return {"response": response, "status": "success"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
def root():
    sports_loaded = {k: bool(team_data.get(k, {}).get('current_stats')) for k in ['boys_soccer', 'girls_soccer', 'boys_basketball', 'girls_basketball', 'baseball', 'wrestling']} if team_data else {}
    return {"status": "online", "message": "Edison Athletics Analytics API v3", "sports_loaded": sports_loaded}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)