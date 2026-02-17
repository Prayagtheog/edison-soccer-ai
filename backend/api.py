from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd
from typing import Optional, List, Dict
from scraper import scrape_all_data

app = FastAPI(title="Edison Soccer Analytics API")

# Enable CORS so frontend can call this
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global data storage
team_data = None

@app.on_event("startup")
async def startup_event():
    """Load data on server startup"""
    global team_data
    print("🔄 Loading Edison soccer data...")
    team_data = scrape_all_data()
    print("✅ Data loaded successfully")

@app.get("/api/team/overview")
def get_team_overview():
    """Get overall team stats and info"""
    if not team_data or not team_data['current_stats']:
        raise HTTPException(status_code=404, detail="No data available")
    
    current_stats = team_data['current_stats']
    field_df = current_stats['field_players']
    goalie_df = current_stats['goalies']
    games_df = team_data['fixtures']['games']
    
    total_goals = int(field_df['Goals'].sum())
    total_assists = int(field_df['Assists'].sum())
    total_points = int(field_df['Points'].sum())
    
    wins = len(games_df[games_df['Outcome'] == 'W'])
    losses = len(games_df[games_df['Outcome'] == 'L'])
    ties = len(games_df[games_df['Outcome'] == 'T'])
    
    return {
        "team": "Edison High School",
        "season": "2025-2026",
        "coach": team_data['fixtures']['coach'],
        "stats": {
            "total_goals": total_goals,
            "total_assists": total_assists,
            "total_points": total_points,
            "games_played": len(games_df[games_df['Outcome'] != '—']),
            "wins": wins,
            "losses": losses,
            "ties": ties,
            "record": f"{wins}-{losses}-{ties}"
        },
        "squad_size": {
            "field_players": len(field_df),
            "goalkeepers": len(goalie_df),
            "total": len(field_df) + len(goalie_df)
        }
    }

@app.get("/api/players/top-scorers")
def get_top_scorers(limit: int = 5):
    """Get top goal scorers"""
    if not team_data or not team_data['current_stats']:
        raise HTTPException(status_code=404, detail="No data available")
    
    field_df = team_data['current_stats']['field_players']
    top = field_df.nlargest(limit, 'Goals')[['Player', 'Year/Position', 'Goals', 'Assists', 'Points']]
    
    return {
        "top_scorers": top.to_dict('records')
    }

@app.get("/api/players/search/{name}")
def search_player(name: str):
    """Search for a specific player by name"""
    if not team_data or not team_data['current_stats']:
        raise HTTPException(status_code=404, detail="No data available")
    
    field_df = team_data['current_stats']['field_players']
    goalie_df = team_data['current_stats']['goalies']
    
    field_match = field_df[field_df['Player'].str.contains(name, case=False, na=False)]
    if not field_match.empty:
        player = field_match.iloc[0]
        return {
            "found": True,
            "player": {
                "name": player['Player'],
                "position": player['Year/Position'],
                "type": "field_player",
                "stats": {
                    "goals": int(player['Goals']),
                    "assists": int(player['Assists']),
                    "points": int(player['Points'])
                }
            }
        }
    
    goalie_match = goalie_df[goalie_df['Player'].str.contains(name, case=False, na=False)]
    if not goalie_match.empty:
        player = goalie_match.iloc[0]
        return {
            "found": True,
            "player": {
                "name": player['Player'],
                "position": player['Year/Position'],
                "type": "goalkeeper",
                "stats": {
                    "saves": int(player['Saves']),
                    "games_played": int(player['Games Played'])
                }
            }
        }
    
    return {"found": False, "message": f"No player found matching '{name}'"}

@app.get("/api/schedule/upcoming")
def get_upcoming_games(limit: int = 3):
    """Get upcoming games"""
    if not team_data or not team_data['fixtures']:
        raise HTTPException(status_code=404, detail="No data available")
    
    games_df = team_data['fixtures']['games']
    upcoming = games_df[games_df['Outcome'] == '—'].head(limit)
    
    return {
        "upcoming_games": upcoming[['Date', 'Opponent', 'Location']].to_dict('records')
    }

@app.get("/api/schedule/recent")
def get_recent_games(limit: int = 5):
    """Get recent game results"""
    if not team_data or not team_data['fixtures']:
        raise HTTPException(status_code=404, detail="No data available")
    
    games_df = team_data['fixtures']['games']
    recent = games_df[games_df['Outcome'] != '—'].tail(limit)
    
    return {
        "recent_games": recent[['Date', 'Opponent', 'Location', 'Result', 'Record']].to_dict('records')
    }

@app.get("/api/schedule/opponent/{team_name}")
def get_opponent_history(team_name: str):
    """Get all games vs a specific opponent"""
    if not team_data or not team_data['fixtures']:
        raise HTTPException(status_code=404, detail="No data available")
    
    games_df = team_data['fixtures']['games']
    opponent_games = games_df[games_df['Opponent'].str.contains(team_name, case=False, na=False)]
    
    if opponent_games.empty:
        return {
            "found": False,
            "message": f"No games found against {team_name}"
        }
    
    vs_record = opponent_games[opponent_games['Outcome'] != '—']['Outcome'].value_counts().to_dict()
    
    return {
        "found": True,
        "opponent": team_name,
        "games_played": len(opponent_games[opponent_games['Outcome'] != '—']),
        "record_vs_opponent": vs_record,
        "games": opponent_games[['Date', 'Location', 'Result', 'Record']].to_dict('records')
    }

@app.get("/api/goalkeepers")
def get_goalkeeper_stats():
    """Get all goalkeeper stats"""
    if not team_data or not team_data['current_stats']:
        raise HTTPException(status_code=404, detail="No data available")
    
    goalie_df = team_data['current_stats']['goalies']
    goalies = goalie_df.to_dict('records')
    
    return {
        "goalkeepers": goalies
    }

@app.get("/api/analytics/goal-distribution")
def get_goal_distribution():
    """Analyze how goals are distributed across the team"""
    if not team_data or not team_data['current_stats']:
        raise HTTPException(status_code=404, detail="No data available")
    
    field_df = team_data['current_stats']['field_players']
    scorers = field_df[field_df['Goals'] > 0]
    non_scorers = len(field_df[field_df['Goals'] == 0])
    
    if len(scorers) > 0:
        top_scorer_goals = scorers['Goals'].max()
        total_goals = field_df['Goals'].sum()
        top_scorer_pct = (top_scorer_goals / total_goals * 100) if total_goals > 0 else 0
        
        return {
            "total_goals": int(total_goals),
            "players_with_goals": len(scorers),
            "players_without_goals": non_scorers,
            "top_scorer_goals": int(top_scorer_goals),
            "top_scorer_percentage": round(top_scorer_pct, 1),
            "average_goals_per_scorer": round(scorers['Goals'].mean(), 2)
        }
    
    return {"message": "No goal data available"}

@app.get("/api/comparison/year-over-year")
def compare_seasons():
    """Compare current season to previous season"""
    if not team_data or not team_data['current_stats'] or not team_data['previous_stats']:
        raise HTTPException(status_code=404, detail="Comparison data not available")
    
    current = team_data['current_stats']['field_players']
    previous = team_data['previous_stats']['field_players']
    
    current_goals = int(current['Goals'].sum())
    previous_goals = int(previous['Goals'].sum())
    
    current_assists = int(current['Assists'].sum())
    previous_assists = int(previous['Assists'].sum())
    
    return {
        "2024-2025": {
            "total_goals": previous_goals,
            "total_assists": previous_assists,
            "players": len(previous)
        },
        "2025-2026": {
            "total_goals": current_goals,
            "total_assists": current_assists,
            "players": len(current)
        },
        "change": {
            "goals_diff": current_goals - previous_goals,
            "assists_diff": current_assists - previous_assists,
            "goals_change_pct": round((current_goals - previous_goals) / previous_goals * 100, 1) if previous_goals > 0 else 0
        }
    }

class ChatRequest(BaseModel):
    message: str
    conversation_history: Optional[List[Dict]] = []

@app.post("/api/chat")
async def chat(request: ChatRequest):
    """Main chat endpoint"""
    from ai_agent import process_chat_message
    
    try:
        response = await process_chat_message(request.message, request.conversation_history)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
def root():
    return {
        "status": "online",
        "message": "Edison Soccer Analytics API",
        "data_loaded": team_data is not None
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)