import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime

def scrape_edison_soccer_stats(year="2025-2026"):
    """
    Scrapes Edison High School soccer stats from nj.com
    """
    url = f"https://highschoolsports.nj.com/school/edison-edison/boyssoccer/season/{year}/stats"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find all stat tables
        tables = soup.find_all('table', class_='table-stats')
        
        # Parse field player stats (first table)
        field_players = []
        if len(tables) > 0:
            rows = tables[0].find('tbody').find_all('tr')
            for row in rows:
                if 'table-secondary' in row.get('class', []):  # Skip total row
                    continue
                    
                cols = row.find_all('td')
                if len(cols) >= 4:
                    player_link = cols[0].find('a')
                    player_name = player_link.text.strip() if player_link else "Unknown"
                    
                    player_info = cols[0].find('small', class_='text-muted')
                    year_position = player_info.text.strip() if player_info else ""
                    
                    goals = cols[1].text.strip()
                    goals = 0 if goals == "—" else int(goals)
                    
                    assists = cols[2].text.strip()
                    assists = 0 if assists == "—" else int(assists)
                    
                    points = cols[3].text.strip()
                    points = 0 if points == "—" else int(points)
                    
                    field_players.append({
                        'Player': player_name,
                        'Year/Position': year_position,
                        'Goals': goals,
                        'Assists': assists,
                        'Points': points
                    })
        
        # Parse goalkeeper stats (second table)
        goalies = []
        if len(tables) > 1:
            rows = tables[1].find('tbody').find_all('tr')
            for row in rows:
                if 'table-secondary' in row.get('class', []):
                    continue
                    
                cols = row.find_all('td')
                if len(cols) >= 3:
                    player_link = cols[0].find('a')
                    player_name = player_link.text.strip() if player_link else "Unknown"
                    
                    player_info = cols[0].find('small', class_='text-muted')
                    year_position = player_info.text.strip() if player_info else ""
                    
                    saves = cols[1].text.strip()
                    saves = 0 if saves == "—" else int(saves)
                    
                    games = cols[2].text.strip()
                    games = 0 if games == "—" else int(games)
                    
                    goalies.append({
                        'Player': player_name,
                        'Year/Position': year_position,
                        'Saves': saves,
                        'Games Played': games
                    })
        
        field_df = pd.DataFrame(field_players)
        goalie_df = pd.DataFrame(goalies)
        
        print(f"✅ Scraped {len(field_players)} field players from {year}")
        print(f"✅ Scraped {len(goalies)} goalkeepers from {year}")
        
        return {
            'field_players': field_df,
            'goalies': goalie_df
        }
        
    except Exception as e:
        print(f"❌ Error scraping stats for {year}: {e}")
        return None

def scrape_fixtures(year="2025-2026"):
    """
    Scrapes schedule/fixtures
    """
    url = f"https://highschoolsports.nj.com/school/edison-edison/boyssoccer/season/{year}"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Hardcode coach for now (can update to scrape later)
        coach_name = "Steve Rubin"
        
        # Find schedule table
        games = []
        schedule_table = soup.find('table', class_='table')
        
        if schedule_table:
            rows = schedule_table.find('tbody').find_all('tr') if schedule_table.find('tbody') else schedule_table.find_all('tr')
            
            for row in rows:
                cols = row.find_all('td')
                if len(cols) >= 3:
                    try:
                        date = cols[0].text.strip()
                        opponent = cols[1].text.strip()
                        result = cols[2].text.strip() if len(cols) > 2 else "—"
                        record = cols[3].text.strip() if len(cols) > 3 else "—"
                        
                        # Determine if home or away
                        location = "Home" if "vs" in opponent else "Away"
                        # Clean opponent name
                        opponent = opponent.replace("vs ", "").replace("@ ", "").strip()
                        
                        # Parse result
                        if result and result != "—":
                            if result.startswith("W"):
                                outcome = "W"
                            elif result.startswith("L"):
                                outcome = "L"
                            elif result.startswith("T"):
                                outcome = "T"
                            else:
                                outcome = "—"
                        else:
                            outcome = "—"
                        
                        games.append({
                            'Date': date,
                            'Opponent': opponent,
                            'Location': location,
                            'Result': result,
                            'Outcome': outcome,
                            'Record': record
                        })
                    except Exception as e:
                        continue
        
        print(f"✅ Scraped {len(games)} games from schedule")
        print(f"✅ Head Coach: {coach_name}")
        
        return {
            'coach': coach_name,
            'games': pd.DataFrame(games)
        }
        
    except Exception as e:
        print(f"❌ Error scraping fixtures: {e}")
        return {'coach': 'Steve Rubin', 'games': pd.DataFrame()}

def scrape_roster(year="2025-2026"):
    """
    Scrapes team roster
    """
    url = f"https://highschoolsports.nj.com/school/edison-edison/boyssoccer/season/{year}/roster"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        players = []
        roster_rows = soup.find_all('tr')
        
        for row in roster_rows:
            cols = row.find_all('td')
            if len(cols) >= 4:
                try:
                    number = cols[0].text.strip()
                    name = cols[1].text.strip()
                    position = cols[2].text.strip()
                    year = cols[3].text.strip()
                    
                    players.append({
                        'Number': number,
                        'Name': name,
                        'Position': position,
                        'Year': year
                    })
                except:
                    continue
        
        print(f"✅ Scraped {len(players)} players from roster")
        
        return pd.DataFrame(players)
        
    except Exception as e:
        print(f"❌ Error scraping roster: {e}")
        return pd.DataFrame()

def scrape_all_data():
    """
    Scrapes all data: current stats, previous year stats, fixtures, roster
    """
    print("🔄 Starting full data scrape...")
    
    # Current year
    current_stats = scrape_edison_soccer_stats("2025-2026")
    fixtures_data = scrape_fixtures("2025-2026")
    roster = scrape_roster("2025-2026")
    
    # Previous year for comparison
    previous_stats = scrape_edison_soccer_stats("2024-2025")
    
    return {
        'current_stats': current_stats,
        'previous_stats': previous_stats,
        'fixtures': fixtures_data,
        'roster': roster
    }

if __name__ == "__main__":
    data = scrape_all_data()
    
    if data['current_stats']:
        print("\n📊 Current Year Field Players Preview:")
        print(data['current_stats']['field_players'].head())
    
    if data['previous_stats']:
        print("\n📊 Previous Year Field Players Preview:")
        print(data['previous_stats']['field_players'].head())
    
    if not data['roster'].empty:
        print("\n👥 Roster Preview:")
        print(data['roster'].head())
    
    if not data['fixtures']['games'].empty:
        print("\n📅 Fixtures Preview:")
        print(data['fixtures']['games'].head())