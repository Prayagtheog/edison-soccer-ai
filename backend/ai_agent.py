import os
import json
from typing import List, Dict
from groq import Groq
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Initialize Groq client
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

SYSTEM_PROMPT = """You are an expert soccer analyst and scout assistant for Edison High School's soccer team (The Eagles).
You have access to real team data that will be provided to you.

Your job is to:
1. Answer questions about the team, players, and upcoming opponents with specific data
2. Provide tactical insights and scouting reports
3. Analyze trends and performance patterns
4. Be conversational but professional - like talking to a coach or player
5. Use data to back up your insights - cite specific stats when making points
6. Be encouraging about the team while being realistic about challenges

Format responses clearly using bullet points and emojis to make it readable.
Keep responses concise but informative - coaches and players need quick insights, not essays."""


async def get_team_data() -> Dict:
    """Fetch all relevant data from the backend API"""
    import httpx
    base_url = "http://localhost:8000"
    data = {}

    async with httpx.AsyncClient(timeout=10.0) as client_http:
        try:
            r = await client_http.get(f"{base_url}/api/team/overview")
            data["overview"] = r.json()
        except:
            data["overview"] = {}

        try:
            r = await client_http.get(f"{base_url}/api/players/top-scorers?limit=5")
            data["top_scorers"] = r.json()
        except:
            data["top_scorers"] = {}

        try:
            r = await client_http.get(f"{base_url}/api/schedule/recent?limit=5")
            data["recent_games"] = r.json()
        except:
            data["recent_games"] = {}

        try:
            r = await client_http.get(f"{base_url}/api/schedule/upcoming?limit=3")
            data["upcoming_games"] = r.json()
        except:
            data["upcoming_games"] = {}

        try:
            r = await client_http.get(f"{base_url}/api/goalkeepers")
            data["goalkeepers"] = r.json()
        except:
            data["goalkeepers"] = {}

    return data


async def process_chat_message(user_message: str, conversation_history: List[Dict] = None) -> Dict:
    """Process a user message using Groq (Llama 3.3 70B)"""
    if conversation_history is None:
        conversation_history = []

    print(f"\n🤖 User asked: {user_message}")

    # Fetch real team data
    team_data = await get_team_data()

    # Build context with real data
    context = f"""Here is the current Edison Eagles soccer team data:

TEAM OVERVIEW:
{json.dumps(team_data.get('overview', {}), indent=2)}

TOP SCORERS:
{json.dumps(team_data.get('top_scorers', {}), indent=2)}

RECENT GAMES:
{json.dumps(team_data.get('recent_games', {}), indent=2)}

UPCOMING GAMES:
{json.dumps(team_data.get('upcoming_games', {}), indent=2)}

GOALKEEPERS:
{json.dumps(team_data.get('goalkeepers', {}), indent=2)}

Now answer this question using the data above: {user_message}"""

    # Build messages for Groq
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    # Add conversation history
    for msg in conversation_history[-6:]:  # Keep last 6 messages for context
        messages.append({"role": msg["role"], "content": msg["content"]})

    # Add current message with data context
    messages.append({"role": "user", "content": context})

    # Call Groq API
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        max_tokens=1024,
        temperature=0.7
    )

    final_response = response.choices[0].message.content
    print(f"✅ Response length: {len(final_response)} chars")

    # Update conversation history
    updated_history = conversation_history + [
        {"role": "user", "content": user_message},
        {"role": "assistant", "content": final_response}
    ]

    return {
        "response": final_response,
        "conversation_history": updated_history
    }