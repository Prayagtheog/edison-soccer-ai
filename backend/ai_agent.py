"""
Edison Athletics AI Agent
Reads team_data directly from memory (passed in from api.py).
Handles actual scraper.py data structures: pandas DataFrames, 
real column names (Player/Goals/Points/Rebounds/AVG/ERA etc.)
"""

import os
import pandas as pd
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

SYSTEM_PROMPT = """You are the Edison Eagles Athletics AI Analyst — the official AI for ALL Edison High School sports.

You cover 6 sports: Boys Soccer, Girls Soccer, Boys Basketball, Girls Basketball, Baseball, and Wrestling.

CRITICAL RULES:
- NEVER say "I only have soccer data" — you have data for ALL sports
- NEVER say you don't have stats if the data is in the context below
- If a sport truly has no stats, say "I don't have [sport] stats right now" — NOT "I only cover soccer"
- Always lead with the direct answer using the actual player names and numbers from the context
- Use sport-appropriate language:
  * Basketball: PPG, RPG, APG — always show per-game averages alongside totals
  * Baseball: ERA for pitchers, batting average + RBI for hitters
  * Wrestling: wins, losses, pins, technical falls, weight class
  * Soccer: goals, assists, clean sheets for GKs
- Be specific. Vague answers are not helpful.

Your personality: Knowledgeable, enthusiastic, loyal to the Edison Eagles.
"""


def _df_context(df, sport: str, max_rows: int = 12) -> str:
    """Convert a pandas DataFrame to a readable string using real column names."""
    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        return "  No data available."

    lines = []
    for _, p in df.head(max_rows).iterrows():
        name = p.get("Player", "Unknown")

        if sport in ("boys_soccer", "girls_soccer"):
            lines.append(
                f"  {name}: {p.get('Goals', 0)} goals, "
                f"{p.get('Assists', 0)} assists, "
                f"{p.get('Points', 0)} pts"
            )

        elif sport in ("boys_basketball", "girls_basketball"):
            pts = p.get("Points", 0) or 0
            reb = p.get("Rebounds", 0) or 0
            ast = p.get("Assists", 0) or 0
            gp  = p.get("GP", 1) or 1
            lines.append(
                f"  {name}: {pts} pts ({round(pts/gp,1)} PPG), "
                f"{reb} reb ({round(reb/gp,1)} RPG), "
                f"{ast} ast ({round(ast/gp,1)} APG), "
                f"{gp} GP"
            )

        elif sport == "baseball":
            era = p.get("ERA", None)
            if era and float(era) > 0:
                lines.append(
                    f"  {name} (P): ERA {era}, "
                    f"{p.get('Strikeouts', 0)} K, "
                    f"{p.get('IP', 0)} IP"
                )
            else:
                lines.append(
                    f"  {name}: {p.get('AVG', '---')} AVG, "
                    f"{p.get('RBI', 0)} RBI, "
                    f"{p.get('H', 0)} H, "
                    f"{p.get('AB', 0)} AB"
                )

        elif sport == "wrestling":
            w    = p.get("Wins", 0) or 0
            l    = p.get("Losses", 0) or 0
            pins = p.get("Pins", 0) or 0
            tf   = p.get("Tech Falls", 0) or 0
            wt   = p.get("Weight", "")
            lines.append(
                f"  {name}: {w}W-{l}L, {pins} pins, {tf} tech falls"
                + (f", {wt}" if wt else "")
            )

        else:
            lines.append(f"  {name}: {dict(p)}")

    return "\n".join(lines) if lines else "  No player data."


def _build_full_context(team_data: dict, coach_data: dict, is_coach: bool) -> str:
    """
    Build full context string from team_data.
    
    Real structure from scraper.py:
      team_data['boys_basketball'] = {
          'current_stats': {'players': DataFrame, 'season': str},
          'fixtures':      {'coach': str, 'record': str, 'games': DataFrame},
          'history':       {season_str: {'players': DataFrame, ...}, ...}
      }
      team_data['boys_soccer'] uses 'field_players' + 'goalies' instead of 'players'
      team_data['baseball'] uses 'batters' + 'pitchers'
      team_data['wrestling'] uses 'wrestlers'
    """
    sections = ["=== EDISON ATHLETICS DATA ===\n"]

    sport_configs = {
        "boys_soccer":     "Boys Soccer",
        "girls_soccer":    "Girls Soccer",
        "boys_basketball": "Boys Basketball",
        "girls_basketball":"Girls Basketball",
        "baseball":        "Baseball",
        "wrestling":       "Wrestling",
    }

    for sport_key, label in sport_configs.items():
        sport = team_data.get(sport_key, {})
        if not sport:
            sections.append(f"--- {label}: No data loaded ---\n")
            continue

        sections.append(f"--- {label} ---")

        # Record and coach come from fixtures, NOT current_stats
        fixtures = sport.get("fixtures", {})
        coach  = fixtures.get("coach", "")
        record = fixtures.get("record", "")
        if record:
            sections.append(f"Record: {record}" + (f" | Coach: {coach}" if coach else ""))
        elif coach:
            sections.append(f"Coach: {coach}")

        cs = sport.get("current_stats") or {}

        # ── Soccer ──
        if sport_key in ("boys_soccer", "girls_soccer"):
            fp = cs.get("field_players")
            gk = cs.get("goalies")

            if isinstance(fp, pd.DataFrame) and not fp.empty:
                fp_sorted = fp.sort_values("Goals", ascending=False) if "Goals" in fp.columns else fp
                sections.append("Field Players (sorted by goals):")
                sections.append(_df_context(fp_sorted, sport_key))
            else:
                sections.append("Field Players: No stats available")

            if isinstance(gk, pd.DataFrame) and not gk.empty:
                sections.append("Goalkeepers:")
                for _, row in gk.head(4).iterrows():
                    sections.append(
                        f"  {row.get('Player','?')}: "
                        f"{row.get('Saves', 0)} saves, "
                        f"{row.get('Games Played', 0)} GP"
                    )

        # ── Basketball ──
        elif sport_key in ("boys_basketball", "girls_basketball"):
            pl = cs.get("players")
            if isinstance(pl, pd.DataFrame) and not pl.empty:
                pl_sorted = pl.sort_values("Points", ascending=False) if "Points" in pl.columns else pl
                sections.append("Players (sorted by total points):")
                sections.append(_df_context(pl_sorted, sport_key))
            else:
                sections.append("Players: No stats available")

        # ── Baseball ──
        elif sport_key == "baseball":
            bt = cs.get("batters")
            pt = cs.get("pitchers")
            if isinstance(bt, pd.DataFrame) and not bt.empty:
                bt_sorted = bt.sort_values("AVG", ascending=False) if "AVG" in bt.columns else bt
                sections.append("Batters (sorted by AVG):")
                sections.append(_df_context(bt_sorted, sport_key))
            else:
                sections.append("Batters: No stats available")
            if isinstance(pt, pd.DataFrame) and not pt.empty:
                pt_sorted = pt.sort_values("ERA", ascending=True) if "ERA" in pt.columns else pt
                sections.append("Pitchers (sorted by ERA, lower is better):")
                sections.append(_df_context(pt_sorted, sport_key))

        # ── Wrestling ──
        elif sport_key == "wrestling":
            wr = cs.get("wrestlers")
            if isinstance(wr, pd.DataFrame) and not wr.empty:
                wr_sorted = wr.sort_values("Wins", ascending=False) if "Wins" in wr.columns else wr
                sections.append("Wrestlers (sorted by wins):")
                sections.append(_df_context(wr_sorted, sport_key))
            else:
                sections.append("Wrestlers: No stats available")

        # ── Historical summary ──
        history = sport.get("history", {})
        if history:
            sections.append("Historical Seasons:")
            for yr in sorted(history.keys(), reverse=True)[:4]:
                yr_data = history.get(yr, {})
                count = 0
                for key in ("players", "field_players", "batters", "wrestlers"):
                    df = yr_data.get(key)
                    if isinstance(df, pd.DataFrame) and not df.empty:
                        count = len(df)
                        break
                sections.append(f"  {yr}: {count} players on record" if count else f"  {yr}: data available")

        sections.append("")

    # ── Coach portal ──
    if coach_data:
        injuries = [i for i in coach_data.get("injuries", []) if not i.get("resolved", False)]
        notes    = coach_data.get("player_notes", [])
        scouting = coach_data.get("scouting_reports", [])

        if injuries or (notes and is_coach) or (scouting and is_coach):
            sections.append("--- Coach Portal ---")

        if injuries:
            if is_coach:
                sections.append("Active Injuries:")
                for inj in injuries:
                    sections.append(
                        f"  {inj.get('player_name','?')} ({inj.get('sport','?')}): "
                        f"{inj.get('description','')} — "
                        f"Return: {inj.get('expected_return','TBD')}"
                    )
            else:
                sections.append(f"  Note: {len(injuries)} player(s) currently dealing with injuries.")

        if notes and is_coach:
            sections.append("Coach Notes:")
            for n in notes[-10:]:
                sections.append(
                    f"  [{n.get('sport','?')}] {n.get('player_name','?')}: {n.get('note','')}"
                )

        if scouting and is_coach:
            sections.append("Scouting Reports:")
            for s in scouting[-3:]:
                sections.append(f"  vs {s.get('opponent','?')}: {s.get('notes','')}")

    return "\n".join(sections)


def get_ai_response(
    message: str,
    conversation_history: list,
    team_data: dict,
    coach_data: dict,
    is_coach: bool = False,
) -> str:
    """
    Main entry point. Called from api.py with in-memory data — no HTTP calls.
    """
    context = _build_full_context(team_data, coach_data, is_coach)

    messages = [
        {
            "role": "user",
            "content": f"{SYSTEM_PROMPT}\n\nHere is all current Edison Athletics data:\n\n{context}"
        },
        {
            "role": "assistant",
            "content": "Got it — I have all Edison Athletics data loaded for all 6 sports. Ask me anything!"
        }
    ]

    # Include last 6 turns of conversation history
    for turn in (conversation_history or [])[-6:]:
        role    = turn.get("role", "user")
        content = turn.get("content", "")
        if role in ("user", "assistant") and content:
            messages.append({"role": role, "content": content})

    messages.append({"role": "user", "content": message})

    try:
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            max_tokens=600,
            temperature=0.7,
        )
        return resp.choices[0].message.content
    except Exception as e:
        return f"Sorry, I ran into an issue connecting to the AI: {str(e)}. Please try again."