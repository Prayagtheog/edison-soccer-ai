import re
import requests
from bs4 import BeautifulSoup
import pandas as pd

HEADERS = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}

SEASONS = ["2025-2026", "2024-2025", "2023-2024", "2022-2023", "2021-2022"]
CURRENT_SEASON = SEASONS[0]
PREVIOUS_SEASON = SEASONS[1]

# Baseball uses previous season since 2025-26 hasn't started yet
BASEBALL_SEASON = "2024-2025"

# Months to validate date strings — prevents schedule table bleed
MONTH_ABBREVS = re.compile(
    r'\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec|\d{1,2}/\d{1,2})',
    re.I
)


def _get(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=12)
        r.raise_for_status()
        return BeautifulSoup(r.text, 'html.parser')
    except Exception as e:
        print(f"  ⚠️  {url}: {e}")
        return None


def _safe_float(cols, idx):
    try:
        v = cols[idx].text.strip().replace('—', '0').replace('–', '0')
        return float(v) if v else 0
    except:
        return 0


def _safe_int(cols, idx):
    return int(_safe_float(cols, idx))


# ──────────────────────────────────────────────
# COACH + RECORD from main season page header
# ──────────────────────────────────────────────

def _scrape_meta(soup):
    """Extract coach name and record from a season page header only."""
    coach_name = 'Unknown'
    record_str = None

    if not soup:
        return coach_name, record_str

    page_text = soup.get_text('\n')
    lines = [l.strip() for l in page_text.split('\n') if l.strip()]

    for i, line in enumerate(lines):
        # Match "Head Coach: Frank Eckert" on the same line
        m = re.match(r'^Head Coach:\s*(.+)', line, re.I)
        if m:
            candidate = m.group(1).strip()
            # Reject if it looks like a schedule row or junk
            if (candidate and len(candidate) < 60
                    and not any(c in candidate for c in ['(', '@', 'vs', 'Schedule', 'Roster', 'Share', '/', '-', 'W ', 'L '])):
                coach_name = candidate
                break
        # Match "Head Coach:" on one line, name on next
        if re.match(r'^Head Coach\s*:?\s*$', line, re.I):
            if i + 1 < len(lines):
                next_line = lines[i + 1]
                if (next_line and len(next_line) < 60
                        and not any(c in next_line for c in ['Schedule', 'Roster', 'Stats', '/', '@', 'vs'])):
                    coach_name = next_line
                    break

    # Record
    for line in lines:
        m = re.match(r'^Record:\s*(.+)', line, re.I)
        if m:
            record_str = m.group(1).strip()
            break
        if re.match(r'^\d+-\d+\s*[•\*]', line):
            record_str = line
            break
        if re.match(r'^\d+-\d+$', line):
            record_str = line
            break

    return coach_name, record_str


# ──────────────────────────────────────────────
# SOCCER
# ──────────────────────────────────────────────

def scrape_soccer_stats(sport_slug, year):
    url = f"https://highschoolsports.nj.com/school/edison-edison/{sport_slug}/season/{year}/stats"
    soup = _get(url)
    if not soup:
        return None

    tables = soup.find_all('table', class_='table-stats')
    field_players, goalies = [], []

    if tables:
        for row in tables[0].find('tbody').find_all('tr'):
            if 'table-secondary' in row.get('class', []):
                continue
            cols = row.find_all('td')
            if len(cols) < 4:
                continue
            try:
                name = (cols[0].find('a') or cols[0]).text.strip()
                pos  = cols[0].find('small', class_='text-muted')
                field_players.append({
                    'Player':        name,
                    'Year/Position': pos.text.strip() if pos else '',
                    'Goals':         _safe_int(cols, 1),
                    'Assists':       _safe_int(cols, 2),
                    'Points':        _safe_int(cols, 3),
                    'Season':        year,
                })
            except:
                continue

    if len(tables) > 1:
        for row in tables[1].find('tbody').find_all('tr'):
            if 'table-secondary' in row.get('class', []):
                continue
            cols = row.find_all('td')
            if len(cols) < 3:
                continue
            try:
                name = (cols[0].find('a') or cols[0]).text.strip()
                pos  = cols[0].find('small', class_='text-muted')
                goalies.append({
                    'Player':        name,
                    'Year/Position': pos.text.strip() if pos else '',
                    'Saves':         _safe_int(cols, 1),
                    'Games Played':  _safe_int(cols, 2),
                    'Season':        year,
                })
            except:
                continue

    print(f"  ✅ {sport_slug} {year} | {len(field_players)} players, {len(goalies)} GKs")
    return {
        'field_players': pd.DataFrame(field_players),
        'goalies':       pd.DataFrame(goalies),
        'season':        year,
    }


# ──────────────────────────────────────────────
# BOYS BASKETBALL
# Columns: Player | 2PT | 3PT | FTM | FTA | PTS | REB | AST | BLK | STL | GP
#          idx:  0     1    2    3    4    5    6    7    8    9    10
# ──────────────────────────────────────────────

def scrape_basketball_stats(gender='boys', year=CURRENT_SEASON):
    slug = 'boysbasketball' if gender == 'boys' else 'girlsbasketball'
    url  = f"https://highschoolsports.nj.com/school/edison-edison/{slug}/season/{year}/stats"
    soup = _get(url)
    if not soup:
        return None

    tables = soup.find_all('table', class_='table-stats')
    players = []

    if tables:
        for row in tables[0].find('tbody').find_all('tr'):
            if 'table-secondary' in row.get('class', []):
                continue
            cols = row.find_all('td')
            if len(cols) < 6:
                continue
            try:
                name = (cols[0].find('a') or cols[0]).text.strip()
                pos  = cols[0].find('small', class_='text-muted')
                # Column mapping verified against nj.com HTML:
                # 0=Player, 1=2PT, 2=3PT, 3=FTM, 4=FTA, 5=PTS, 6=REB, 7=AST, 8=BLK, 9=STL, 10=GP
                players.append({
                    'Player':        name,
                    'Year/Position': pos.text.strip() if pos else '',
                    'Points':        _safe_float(cols, 5),   # PTS column
                    'Rebounds':      _safe_float(cols, 6),   # REB column
                    'Assists':       _safe_float(cols, 7),   # AST column
                    'Blocks':        _safe_float(cols, 8) if len(cols) > 8 else 0,
                    'Steals':        _safe_float(cols, 9) if len(cols) > 9 else 0,
                    'GP':            _safe_int(cols, 10) if len(cols) > 10 else 0,
                    'FGM_2':         _safe_float(cols, 1),
                    'FGM_3':         _safe_float(cols, 2),
                    'FTM':           _safe_float(cols, 3),
                    'FTA':           _safe_float(cols, 4),
                    'Season':        year,
                })
            except:
                continue

    print(f"  ✅ {slug} {year} | {len(players)} players")
    return {'players': pd.DataFrame(players), 'season': year}


# ──────────────────────────────────────────────
# GIRLS BASKETBALL — per-player scraping
# Uses "Featured Stats" section on player profile pages (more reliable than career table)
# Profile URL: /player/{slug}/girlsbasketball/season/{year}
# ──────────────────────────────────────────────

def _get_roster_links(sport_slug, year):
    """Get list of (player_name, player_url) from roster page."""
    url  = f"https://highschoolsports.nj.com/school/edison-edison/{sport_slug}/season/{year}/roster"
    soup = _get(url)
    if not soup:
        return []
    players = []
    for a in soup.find_all('a', href=True):
        href = a['href']
        if '/player/' in href:
            name = a.get_text(strip=True)
            # Build correct player-sport URL regardless of what the link says
            player_slug = href.split('/player/')[-1].split('/')[0]
            full = f"https://highschoolsports.nj.com/player/{player_slug}/{sport_slug}/season/{year}"
            if name and len(name) > 2 and (name, full) not in players:
                players.append((name, full))
    return players


def _parse_featured_stats(soup, year):
    """
    Parse the 'Featured Stats' section from a player profile page.
    Returns dict with Points, Rebounds, Assists, GP or None.
    Example HTML structure:
      <div class="featured-stat"><span>206</span> Points Total</div>
    """
    result = {}
    page_text = soup.get_text('\n')
    lines = [l.strip() for l in page_text.split('\n') if l.strip()]

    # Strategy 1: Look for "Featured Stats" heading then parse nearby numbers
    in_featured = False
    for i, line in enumerate(lines):
        if 'Featured Stats' in line:
            in_featured = True
        if in_featured:
            # Look for patterns like "206" followed by "Points" "Total"
            if re.match(r'^\d+$', line):
                # Next lines tell us what stat this is
                context = ' '.join(lines[i:i+4]).lower()
                if 'point' in context and 'Points' not in result:
                    result['Points'] = float(line)
                elif 'rebound' in context and 'Rebounds' not in result:
                    result['Rebounds'] = float(line)
                elif 'assist' in context and 'Assists' not in result:
                    result['Assists'] = float(line)
            # Stop after we've found all three or hit another major section
            if len(result) == 3:
                break
            if in_featured and re.match(r'^(Career Stats|Game Log|Season)', line):
                break

    # Strategy 2: Look for the season row in the career stats table
    # Columns: Season | 2PT | 3PT | FTM | FTA | PTS | REB | AST | BLK | STL | GP
    if 'Points' not in result:
        tables = soup.find_all('table')
        for table in tables:
            for row in table.find_all('tr'):
                cols = row.find_all('td')
                if not cols:
                    continue
                if cols[0].get_text(strip=True) == year and len(cols) >= 8:
                    try:
                        gp_val = int(cols[-1].get_text(strip=True)) if cols[-1].get_text(strip=True).isdigit() else 0
                        result['Points']   = float(cols[5].get_text(strip=True).replace('—', '0') or '0')
                        result['Rebounds'] = float(cols[6].get_text(strip=True).replace('—', '0') or '0')
                        result['Assists']  = float(cols[7].get_text(strip=True).replace('—', '0') or '0')
                        if len(cols) > 10:
                            result['GP'] = int(cols[10].get_text(strip=True).replace('—', '0') or '0')
                        elif gp_val:
                            result['GP'] = gp_val
                    except:
                        pass
                    break

    return result if result else None


def scrape_girls_basketball_stats(year=CURRENT_SEASON):
    """Scrape girls basketball by visiting each player's profile page."""
    roster = _get_roster_links('girlsbasketball', year)
    print(f"  📋 Girls basketball roster: {len(roster)} players found for {year}")
    players = []

    for name, url in roster[:25]:
        soup = _get(url)
        if not soup:
            continue
        try:
            stats = _parse_featured_stats(soup, year)
            if not stats or 'Points' not in stats:
                continue

            # Get GP from game log Season Totals if not found above
            gp = stats.get('GP', 0)
            if not gp:
                page_text = soup.get_text('\n')
                lines = [l.strip() for l in page_text.split('\n') if l.strip()]
                for i, line in enumerate(lines):
                    if 'Season Totals' in line:
                        # GP is usually the last number in the totals row
                        for j in range(i+1, min(i+20, len(lines))):
                            if lines[j].isdigit():
                                gp = int(lines[j])
                        break

            players.append({
                'Player':   name,
                'Year/Position': '',
                'Points':   stats.get('Points', 0),
                'Rebounds': stats.get('Rebounds', 0),
                'Assists':  stats.get('Assists', 0),
                'Blocks':   stats.get('Blocks', 0),
                'Steals':   stats.get('Steals', 0),
                'GP':       gp,
                'Season':   year,
            })
        except Exception as e:
            print(f"    ⚠️  {name}: {e}")
            continue

    print(f"  ✅ Girls basketball {year} | {len(players)} players with stats")
    return {'players': pd.DataFrame(players), 'season': year}


# ──────────────────────────────────────────────
# WRESTLING — per-player scraping
# Profile URL: /player/{slug}/wrestling/season/{year}
# Page shows match results as text lines:
#   "1/14/2026, South Plainfield (56) at Edison (22) Win over Elias Perez by Pin, 6-1, 1:02"
# Weight class appears as: "2025-2026 144 pound" in page text
# ──────────────────────────────────────────────

def scrape_wrestling_stats(year=CURRENT_SEASON):
    """Scrape wrestling by visiting each player's profile page."""
    roster = _get_roster_links('wrestling', year)
    print(f"  📋 Wrestling roster: {len(roster)} players found for {year}")
    wrestlers = []

    for name, url in roster[:40]:
        soup = _get(url)
        if not soup:
            continue
        try:
            wins = 0; losses = 0; pins = 0; tech_falls = 0
            weight_class = ''

            page_text = soup.get_text('\n')
            lines = [l.strip() for l in page_text.split('\n') if l.strip()]

            # Weight class: look for "{year} {number} pound" in page text
            # e.g. "2025-2026 144 pound" or "144 pound" standalone
            for line in lines:
                m = re.search(r'(\d{2,3})\s*pound', line, re.I)
                if m:
                    weight_class = m.group(1) + ' lb'
                    break

            # Count match results — only count lines that look like actual match results
            # Format: "date, teams Win/Loss over/to opponent by method"
            # We filter to lines that start with a date pattern to avoid false positives
            in_season_section = False
            for line in lines:
                # Detect when we enter this season's section
                if year in line and ('pound' in line.lower() or 'lb' in line.lower()):
                    in_season_section = True
                    continue
                # Stop if we hit a different season
                if re.match(r'^\d{4}-\d{4}', line) and year not in line:
                    in_season_section = False

                if not in_season_section:
                    continue

                # A valid match result line starts with a date (M/D/YYYY or MM/DD/YYYY)
                if not re.match(r'^\d{1,2}/\d{1,2}/\d{4}', line):
                    continue

                if 'Win' in line:
                    wins += 1
                    if 'Pin' in line and 'Pinned' not in line:
                        pins += 1
                    elif 'Technical Fall' in line:
                        tech_falls += 1
                elif 'Loss' in line:
                    losses += 1

            if wins + losses > 0:
                wrestlers.append({
                    'Player':     name,
                    'Weight':     weight_class,
                    'Wins':       wins,
                    'Losses':     losses,
                    'Pins':       pins,
                    'Tech Falls': tech_falls,
                    'Season':     year,
                })
        except Exception as e:
            print(f"    ⚠️  {name}: {e}")
            continue

    print(f"  ✅ Wrestling {year} | {len(wrestlers)} wrestlers with stats")
    return {'wrestlers': pd.DataFrame(wrestlers), 'season': year}


# ──────────────────────────────────────────────
# BASEBALL
# Cols batting: Player | AB | R | H | RBI | 1B | 2B | 3B | HR | BB | HBP | SB | AVG | SLG
# Cols pitching: Player | PIT | IP | H | R | ER | BB | K | HB | ERA
# ──────────────────────────────────────────────

def scrape_baseball_stats(year=BASEBALL_SEASON):
    url  = f"https://highschoolsports.nj.com/school/edison-edison/baseball/season/{year}/stats"
    soup = _get(url)
    if not soup:
        return None

    tables = soup.find_all('table', class_='table-stats')
    batters, pitchers = [], []

    if tables:
        for row in tables[0].find('tbody').find_all('tr'):
            if 'table-secondary' in row.get('class', []):
                continue
            cols = row.find_all('td')
            if len(cols) < 5:
                continue
            try:
                name = (cols[0].find('a') or cols[0]).text.strip()
                pos  = cols[0].find('small', class_='text-muted')
                # AB | R | H | RBI | 1B | 2B | 3B | HR | BB | HBP | SB | AVG | SLG
                batters.append({
                    'Player':        name,
                    'Year/Position': pos.text.strip() if pos else '',
                    'AB':            _safe_int(cols, 1),
                    'R':             _safe_int(cols, 2),
                    'H':             _safe_int(cols, 3),
                    'RBI':           _safe_int(cols, 4),
                    '2B':            _safe_int(cols, 6) if len(cols) > 6 else 0,
                    '3B':            _safe_int(cols, 7) if len(cols) > 7 else 0,
                    'HR':            _safe_int(cols, 8) if len(cols) > 8 else 0,
                    'BB':            _safe_int(cols, 9) if len(cols) > 9 else 0,
                    'AVG':           _safe_float(cols, 12) if len(cols) > 12 else 0,
                    'SLG':           _safe_float(cols, 13) if len(cols) > 13 else 0,
                    'Season':        year,
                })
            except:
                continue

    if len(tables) > 1:
        for row in tables[1].find('tbody').find_all('tr'):
            if 'table-secondary' in row.get('class', []):
                continue
            cols = row.find_all('td')
            if len(cols) < 5:
                continue
            try:
                name = (cols[0].find('a') or cols[0]).text.strip()
                pos  = cols[0].find('small', class_='text-muted')
                # PIT | IP | H | R | ER | BB | K | HB | ERA
                pitchers.append({
                    'Player':        name,
                    'Year/Position': pos.text.strip() if pos else '',
                    'IP':            _safe_float(cols, 2),
                    'H':             _safe_int(cols, 3),
                    'ER':            _safe_int(cols, 5),
                    'BB':            _safe_int(cols, 6),
                    'Strikeouts':    _safe_int(cols, 7) if len(cols) > 7 else 0,
                    'ERA':           _safe_float(cols, 9) if len(cols) > 9 else 0,
                    'Season':        year,
                })
            except:
                continue

    print(f"  ✅ Baseball {year} | {len(batters)} batters, {len(pitchers)} pitchers")
    return {'batters': pd.DataFrame(batters), 'pitchers': pd.DataFrame(pitchers), 'season': year}


# ──────────────────────────────────────────────
# FIXTURES — schedule + coach + record
# FIX: strict date validation prevents raw schedule text from bleeding into page
# ──────────────────────────────────────────────

def _is_valid_date(s):
    """Returns True only if the string looks like an actual game date."""
    if not s or len(s) > 35:
        return False
    # Must contain a month abbreviation or M/D pattern
    return bool(MONTH_ABBREVS.search(s))


def scrape_fixtures(sport_slug, year):
    url  = f"https://highschoolsports.nj.com/school/edison-edison/{sport_slug}/season/{year}"
    soup = _get(url)
    if not soup:
        return {'coach': 'Unknown', 'record': None, 'games': pd.DataFrame()}

    coach_name, record_str = _scrape_meta(soup)
    games = []

    for table in soup.find_all('table'):
        # Skip stats tables — those are player leaderboards, not schedule
        classes = table.get('class', [])
        if 'table-stats' in classes:
            continue

        rows = (table.find('tbody') or table).find_all('tr')
        if len(rows) < 2:
            continue

        found_games = []
        for row in rows:
            cols = row.find_all('td')
            if len(cols) < 2:
                continue
            try:
                date_raw = cols[0].get_text(separator=' ', strip=True)
                # STRICT: skip anything that doesn't look like a real date
                if not _is_valid_date(date_raw):
                    continue

                date = date_raw.split('\n')[0].strip()
                opp_raw = cols[1].get_text(separator=' ', strip=True)
                result  = cols[2].get_text(strip=True) if len(cols) > 2 else '—'
                record  = cols[3].get_text(strip=True) if len(cols) > 3 else '—'

                location = 'Away' if '@' in opp_raw else 'Home'
                opponent = re.sub(r'^(vs\.?\s*|@\s*)', '', opp_raw).strip()
                opponent = opponent.split('\n')[0].strip()

                # Skip header rows or junk
                if not opponent or opponent.lower() in ('opponent', 'team', 'date'):
                    continue

                if result and result[0] in ('W', 'L', 'T'):
                    outcome = result[0]
                else:
                    outcome = '—'

                found_games.append({
                    'Date': date, 'Opponent': opponent, 'Location': location,
                    'Result': result, 'Outcome': outcome, 'Record': record,
                    'Season': year
                })
            except:
                continue

        if found_games:
            games = found_games
            break  # Stop at first table that yields valid games

    print(f"  ✅ {sport_slug} {year} | {len(games)} games | Coach: {coach_name}")
    return {'coach': coach_name, 'record': record_str, 'games': pd.DataFrame(games)}


# ──────────────────────────────────────────────
# OPPONENT SCRAPER
# ──────────────────────────────────────────────

def scrape_opponent_data(team_name, sport_slug='boyssoccer', year=None):
    year = year or CURRENT_SEASON
    slug = team_name.lower().replace(' ', '-')
    url  = f"https://highschoolsports.nj.com/school/{slug}-{slug}/{sport_slug}/season/{year}/stats"
    soup = _get(url)
    if not soup:
        return None
    tables = soup.find_all('table', class_='table-stats')
    if not tables:
        return None
    players = []
    for row in tables[0].find('tbody').find_all('tr'):
        cols = row.find_all('td')
        if len(cols) >= 4:
            try:
                players.append({
                    'Player':  (cols[0].find('a') or cols[0]).text.strip(),
                    'Goals':   _safe_int(cols, 1),
                    'Assists': _safe_int(cols, 2),
                    'Points':  _safe_int(cols, 3),
                })
            except:
                continue
    return {'team': team_name, 'players': players, 'season': year}


# ──────────────────────────────────────────────
# MAIN — scrape all sports
# ──────────────────────────────────────────────

def scrape_all_data():
    print('🔄 Starting full multi-sport, multi-year scrape...')
    result = {}

    # ── Boys Soccer ──
    print('\n⚽ Boys Soccer:')
    bs_history = {}
    for season in SEASONS:
        data = scrape_soccer_stats('boyssoccer', season)
        if data:
            bs_history[season] = data
    result['boys_soccer'] = {
        'current_stats':  bs_history.get(CURRENT_SEASON),
        'previous_stats': bs_history.get(PREVIOUS_SEASON),
        'history':        bs_history,
        'fixtures':       scrape_fixtures('boyssoccer', CURRENT_SEASON),
    }
    # Backwards compat keys used by old endpoints
    result['current_stats']  = result['boys_soccer']['current_stats']
    result['previous_stats'] = result['boys_soccer']['previous_stats']
    result['fixtures']       = result['boys_soccer']['fixtures']

    # ── Girls Soccer ──
    print('\n⚽ Girls Soccer:')
    gs_history = {}
    for season in SEASONS:
        data = scrape_soccer_stats('girlssoccer', season)
        if data:
            gs_history[season] = data
    result['girls_soccer'] = {
        'current_stats': gs_history.get(CURRENT_SEASON),
        'history':       gs_history,
        'fixtures':      scrape_fixtures('girlssoccer', CURRENT_SEASON),
    }

    # ── Boys Basketball ──
    print('\n🏀 Boys Basketball:')
    bb_history = {}
    for season in SEASONS:
        data = scrape_basketball_stats('boys', season)
        if data:
            bb_history[season] = data
    result['boys_basketball'] = {
        'current_stats': bb_history.get(CURRENT_SEASON),
        'history':       bb_history,
        'fixtures':      scrape_fixtures('boysbasketball', CURRENT_SEASON),
    }

    # ── Girls Basketball ──
    print('\n🏀 Girls Basketball:')
    gb_history = {}
    for season in SEASONS:
        data = scrape_girls_basketball_stats(season)
        if data:
            gb_history[season] = data
    result['girls_basketball'] = {
        'current_stats': gb_history.get(CURRENT_SEASON),
        'history':       gb_history,
        'fixtures':      scrape_fixtures('girlsbasketball', CURRENT_SEASON),
    }

    # ── Baseball ──
    print('\n⚾ Baseball:')
    bsb_history = {}
    for season in SEASONS:
        data = scrape_baseball_stats(season)
        if data:
            bsb_history[season] = data
    result['baseball'] = {
        'current_stats': bsb_history.get(BASEBALL_SEASON),
        'history':       bsb_history,
        'fixtures':      scrape_fixtures('baseball', BASEBALL_SEASON),
    }

    # ── Wrestling ──
    print('\n🤼 Wrestling:')
    wr_history = {}
    for season in SEASONS:
        data = scrape_wrestling_stats(season)
        if data:
            wr_history[season] = data
    result['wrestling'] = {
        'current_stats': wr_history.get(CURRENT_SEASON),
        'history':       wr_history,
        'fixtures':      scrape_fixtures('wrestling', CURRENT_SEASON),
    }

    print('\n✅ All sports scraped!')
    return result


if __name__ == '__main__':
    data = scrape_all_data()
    for sport in ['boys_soccer', 'girls_soccer', 'boys_basketball', 'girls_basketball', 'baseball', 'wrestling']:
        sd = data.get(sport, {})
        cs = sd.get('current_stats')
        coach = sd.get('fixtures', {}).get('coach', '?')
        has_players = False
        if cs:
            for key in ('field_players', 'players', 'batters', 'wrestlers'):
                df = cs.get(key)
                if df is not None and not df.empty:
                    has_players = True
                    print(f"  {sport}: {len(df)} {key}")
                    break
        print(f"{sport}: coach={coach}, has_stats={has_players}")