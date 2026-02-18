'use client';

import { useState, useRef, useEffect } from 'react';

interface Message { role: 'user' | 'assistant'; content: string; }
type View = 'landing' | 'stats' | 'chat' | 'coach';

function BarChart({ data, valueKey, labelKey, color }: { data: any[]; valueKey: string; labelKey: string; color: string; }) {
  if (!data || data.length === 0) return <p className="text-gray-500 text-sm">No data</p>;
  const max = Math.max(...data.map(d => d[valueKey]));
  return (
    <div className="space-y-2">
      {data.map((item, i) => (
        <div key={i} className="flex items-center gap-2">
          <span className="text-xs text-gray-400 w-28 truncate flex-shrink-0">{item[labelKey]}</span>
          <div className="flex-1 bg-gray-800 rounded-full h-5 overflow-hidden">
            <div className="h-full rounded-full flex items-center justify-end pr-2 transition-all duration-700"
              style={{ width: `${max > 0 ? (item[valueKey] / max) * 100 : 0}%`, background: color }}>
              <span className="text-white text-xs font-bold">{item[valueKey]}</span>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

function FormDots({ form }: { form: string[] }) {
  const colors: Record<string, string> = { W: 'bg-green-500', L: 'bg-red-500', T: 'bg-yellow-500' };
  return (
    <div className="flex gap-1">
      {form.map((r, i) => (
        <div key={i} className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold text-white ${colors[r] || 'bg-gray-600'}`}>{r}</div>
      ))}
    </div>
  );
}

function StatCard({ label, value, sub, icon }: { label: string; value: string | number; sub?: string; icon: string }) {
  return (
    <div className="bg-gray-800/60 border border-gray-700 rounded-xl p-4 flex items-start gap-3">
      <span className="text-2xl">{icon}</span>
      <div>
        <div className="text-2xl font-black text-white">{value}</div>
        <div className="text-xs text-gray-400 uppercase tracking-wide">{label}</div>
        {sub && <div className="text-xs text-gray-500 mt-0.5">{sub}</div>}
      </div>
    </div>
  );
}

export default function Home() {
  const [view, setView] = useState<View>('landing');
  const [coachPassword, setCoachPassword] = useState('');
  const [coachToken, setCoachToken] = useState('');
  const [coachName, setCoachName] = useState('Coach');
  const [coachAuthed, setCoachAuthed] = useState(false);
  const [coachAuthError, setCoachAuthError] = useState('');
  const [overview, setOverview] = useState<any>(null);
  const [leaderboard, setLeaderboard] = useState<any>(null);
  const [yearOverYear, setYearOverYear] = useState<any>(null);
  const [allGames, setAllGames] = useState<any[]>([]);
  const [upcomingGames, setUpcomingGames] = useState<any[]>([]);
  const [goalkeepers, setGoalkeepers] = useState<any[]>([]);
  const [activeSport, setActiveSport] = useState('boys_soccer');
  const [statsLoading, setStatsLoading] = useState(false);
  const [coachDashboard, setCoachDashboard] = useState<any>(null);
  const [newNote, setNewNote] = useState({ note: '', category: 'general' });
  const [newInjury, setNewInjury] = useState({ player_name: '', injury_type: '', expected_return: '' });
  const [newScouting, setNewScouting] = useState({ opponent: '', strengths: '', weaknesses: '', key_players: '', tactical_notes: '', game_plan: '' });
  const [coachSaving, setCoachSaving] = useState('');
  const [coachFeedback, setCoachFeedback] = useState('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [conversationHistory, setConversationHistory] = useState<any[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const API = 'http://localhost:8000';

  useEffect(() => { messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages]);
  useEffect(() => {
    if (view === 'stats' && !overview) loadStats(activeSport);
    if (view === 'coach' && coachAuthed && !coachDashboard) loadCoachDashboard();
  }, [view, coachAuthed]);

  const authHeaders = () => ({
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${coachToken}`
  });

  async function loadStats(sport = activeSport) {
    setStatsLoading(true);
    setOverview(null); setLeaderboard(null); setAllGames([]); setUpcomingGames([]); setGoalkeepers([]);
    const isSoccer = sport === 'boys_soccer' || sport === 'girls_soccer';
    const isBasketball = sport === 'boys_basketball' || sport === 'girls_basketball';
    try {
      const [ov, lb, games, upcoming] = await Promise.all([
        fetch(`${API}/api/${sport}/overview`).then(r => r.json()),
        fetch(`${API}/api/${sport}/leaderboard`).then(r => r.json()),
        fetch(`${API}/api/${sport}/schedule?filter=all`).then(r => r.json()).catch(() => ({ games: [] })),
        fetch(`${API}/api/${sport}/schedule?filter=upcoming`).then(r => r.json()).catch(() => ({ games: [] })),
      ]);
      const yoy = isSoccer ? await fetch(`${API}/api/comparison/year-over-year`).then(r => r.json()).catch(() => null) : null;
      const gk  = isSoccer ? await fetch(`${API}/api/${sport}/goalkeepers`).then(r => r.json()).catch(() => ({ goalkeepers: [] })) : { goalkeepers: [] };
      setOverview(ov); setLeaderboard(lb); setYearOverYear(yoy);
      setAllGames(games.games || []); setUpcomingGames(upcoming.games || []);
      setGoalkeepers(gk.goalkeepers || []);
    } catch (e) { console.error('Stats error:', e); }
    setStatsLoading(false);
  }

  async function loadCoachDashboard() {
    try {
      const res = await fetch(`${API}/api/coach/dashboard`, { headers: authHeaders() });
      if (res.ok) setCoachDashboard(await res.json());
    } catch (e) { console.error(e); }
  }

  async function handleCoachLogin() {
    setCoachAuthError('');
    try {
      const res = await fetch(`${API}/api/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password: coachPassword, coach_name: 'Coach' })
      });
      if (res.ok) {
        const data = await res.json();
        setCoachToken(data.token);
        setCoachName(data.coach);
        setCoachAuthed(true);
        // Load dashboard with the new token directly
        const dash = await fetch(`${API}/api/coach/dashboard`, {
          headers: { 'Authorization': `Bearer ${data.token}` }
        });
        if (dash.ok) setCoachDashboard(await dash.json());
      } else {
        setCoachAuthError('Wrong password. Try again.');
      }
    } catch {
      setCoachAuthError('Cannot connect to backend. Is it running?');
    }
  }

  async function saveCoachNote() {
    if (!newNote.note.trim()) return;
    setCoachSaving('note');
    try {
      await fetch(`${API}/api/coach/notes`, {
        method: 'POST',
        headers: authHeaders(),
        body: JSON.stringify({ player_name: 'Team', ...newNote })
      });
      setNewNote({ note: '', category: 'general' });
      setCoachFeedback('✅ Note saved!');
      loadCoachDashboard();
    } catch { setCoachFeedback('❌ Error saving note'); }
    setCoachSaving('');
    setTimeout(() => setCoachFeedback(''), 3000);
  }

  async function saveInjury() {
    if (!newInjury.player_name.trim() || !newInjury.injury_type.trim()) return;
    setCoachSaving('injury');
    try {
      await fetch(`${API}/api/coach/injuries`, {
        method: 'POST',
        headers: authHeaders(),
        body: JSON.stringify(newInjury)
      });
      setNewInjury({ player_name: '', injury_type: '', expected_return: '' });
      setCoachFeedback('✅ Injury reported!');
      loadCoachDashboard();
    } catch { setCoachFeedback('❌ Error saving injury'); }
    setCoachSaving('');
    setTimeout(() => setCoachFeedback(''), 3000);
  }

  async function saveScouting() {
    if (!newScouting.opponent.trim()) return;
    setCoachSaving('scouting');
    try {
      await fetch(`${API}/api/coach/scouting`, {
        method: 'POST',
        headers: authHeaders(),
        body: JSON.stringify(newScouting)
      });
      setNewScouting({ opponent: '', strengths: '', weaknesses: '', key_players: '', tactical_notes: '', game_plan: '' });
      setCoachFeedback('✅ Scouting report saved!');
      loadCoachDashboard();
    } catch { setCoachFeedback('❌ Error saving report'); }
    setCoachSaving('');
    setTimeout(() => setCoachFeedback(''), 3000);
  }

  async function handleSend() {
    if (!input.trim() || isLoading) return;
    const userMessage = input.trim();
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
    setIsLoading(true);
    try {
      const response = await fetch(`${API}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: userMessage, conversation_history: conversationHistory, is_coach: coachAuthed })
      });
      const data = await response.json();
      if (data.response) {
        setMessages(prev => [...prev, { role: 'assistant', content: data.response }]);
        setConversationHistory(data.conversation_history || []);
      }
    } catch {
      setMessages(prev => [...prev, { role: 'assistant', content: '❌ Cannot connect to backend. Make sure it is running on port 8000.' }]);
    }
    setIsLoading(false);
  }

  const completedGames = allGames.filter(g => g.Outcome !== '—');
  const recentForm = completedGames.slice(-5).map(g => g.Outcome);


  const SPORTS: { key: string; label: string; icon: string }[] = [
    { key: 'boys_soccer',      label: 'Boys Soccer',      icon: '⚽' },
    { key: 'girls_soccer',     label: 'Girls Soccer',     icon: '⚽' },
    { key: 'boys_basketball',  label: 'Boys Basketball',  icon: '🏀' },
    { key: 'girls_basketball', label: 'Girls Basketball', icon: '🏀' },
    { key: 'baseball',         label: 'Baseball',         icon: '⚾' },
    { key: 'wrestling',        label: 'Wrestling',        icon: '🤼' },
  ];

  const Nav = () => (
    <div className="border-b border-gray-800 bg-gray-950/95 backdrop-blur-sm sticky top-0 z-20">
      <div className="max-w-6xl mx-auto px-4 py-3 flex items-center gap-2 overflow-x-auto">
        <button onClick={() => setView('landing')} className="text-2xl mr-2 flex-shrink-0">🦅</button>
        {(['stats', 'chat', 'coach'] as View[]).map(v => (
          <button key={v} onClick={() => setView(v)}
            className={`px-4 py-2 rounded-lg font-medium text-sm transition-all flex-shrink-0 ${view === v ? 'bg-red-600 text-white' : 'text-gray-400 hover:text-white hover:bg-gray-800'}`}>
            {v === 'stats' ? '📊 Stats' : v === 'chat' ? '🤖 AI Chat' : '🔐 Coach Portal'}
            {v === 'coach' && coachAuthed && <span className="ml-1 text-xs text-yellow-400">●</span>}
          </button>
        ))}
        {coachAuthed && <span className="ml-auto text-xs text-green-400 flex-shrink-0 flex items-center gap-1"><span className="w-1.5 h-1.5 bg-green-400 rounded-full"></span> Coach Mode On</span>}
      </div>
    </div>
  );

  // ── LANDING ──
  if (view === 'landing') return (
    <div className="min-h-screen bg-gray-950 text-white overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-br from-red-950/40 via-gray-950 to-yellow-950/20 pointer-events-none" />
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-[800px] h-[500px] bg-red-600/10 rounded-full blur-3xl pointer-events-none" />
      <div className="relative max-w-5xl mx-auto px-6 py-16 flex flex-col items-center text-center">
        <div className="text-8xl mb-4" style={{ animation: 'bounce 3s infinite' }}>🦅</div>
        <h1 className="text-6xl md:text-7xl font-black tracking-tight mb-2">
          <span className="text-transparent bg-clip-text bg-gradient-to-r from-red-400 via-red-500 to-yellow-400">Edison Eagles</span>
        </h1>
        <h2 className="text-3xl md:text-4xl font-bold text-gray-300 mb-4">Athletics Hub</h2>
        <p className="text-lg text-gray-400 max-w-xl mb-10">Real-time stats, AI-powered analytics, and a full coach portal for all Edison athletics — powered by live data from nj.com.</p>
        <div className="flex flex-wrap gap-2 justify-center mb-12">
          {['📊 Live Stats', '🤖 AI Chat', '⚽🏀⚾🤼 Multi-Sport', '📈 5-Year History', '🏥 Injury Tracker', '📋 Coach Portal'].map(f => (
            <span key={f} className="px-3 py-1 bg-gray-800 border border-gray-700 rounded-full text-sm text-gray-300">{f}</span>
          ))}
        </div>
        <div className="flex flex-col sm:flex-row gap-4 w-full max-w-md">
          <button onClick={() => setView('stats')} className="flex-1 py-4 px-6 bg-gradient-to-r from-red-600 to-red-700 hover:from-red-500 hover:to-red-600 text-white font-bold rounded-xl text-lg transition-all hover:scale-105 hover:shadow-lg hover:shadow-red-500/25">
            📊 View Stats & Analytics
          </button>
          <button onClick={() => setView('chat')} className="flex-1 py-4 px-6 bg-gray-800 hover:bg-gray-700 border border-gray-600 text-white font-bold rounded-xl text-lg transition-all hover:scale-105">
            🤖 Ask the AI
          </button>
        </div>
        <button onClick={() => setView('coach')} className="mt-4 py-3 px-8 bg-yellow-600/20 hover:bg-yellow-600/30 border border-yellow-600/40 text-yellow-400 font-semibold rounded-xl transition-all">
          🔐 Coach Portal
        </button>
        <div className="mt-16 grid grid-cols-3 gap-6 w-full max-w-md">
          {[['Sports Tracked', '6', '🏆'], ['Seasons of Data', '5', '📅'], ['AI Model', 'Llama 3.3', '🧠']].map(([label, val, icon]) => (
            <div key={label as string} className="bg-gray-800/40 border border-gray-700 rounded-xl p-4 text-center">
              <div className="text-2xl mb-1">{icon}</div>
              <div className="text-xl font-black text-white">{val}</div>
              <div className="text-xs text-gray-500">{label}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );

  // ── STATS ──
  if (view === 'stats') return (
    <div className="min-h-screen bg-gray-950 text-white">
      <Nav />
      <div className="max-w-6xl mx-auto px-4 py-8">
        {/* ── Sport Switcher ── */}
        <div className="flex gap-2 overflow-x-auto pb-2 mb-6">
          {SPORTS.map(s => (
            <button key={s.key}
              onClick={() => { setActiveSport(s.key); loadStats(s.key); }}
              className={`flex items-center gap-2 px-4 py-2 rounded-xl font-semibold text-sm whitespace-nowrap transition-all flex-shrink-0 border ${activeSport === s.key ? 'bg-red-600 border-red-500 text-white' : 'bg-gray-800/60 border-gray-700 text-gray-400 hover:text-white hover:border-gray-500'}`}>
              <span>{s.icon}</span>{s.label}
            </button>
          ))}
        </div>
        {statsLoading ? (
          <div className="flex items-center justify-center py-32 gap-3">
            <div className="w-3 h-3 bg-red-500 rounded-full animate-bounce"></div>
            <div className="w-3 h-3 bg-yellow-500 rounded-full animate-bounce" style={{ animationDelay: '0.15s' }}></div>
            <div className="w-3 h-3 bg-red-500 rounded-full animate-bounce" style={{ animationDelay: '0.3s' }}></div>
            <span className="text-gray-400 ml-2">Loading stats...</span>
          </div>
        ) : overview ? (
          <>
            <div className="mb-8">
              <h1 className="text-3xl font-black text-white">Edison {SPORTS.find(s => s.key === activeSport)?.label} <span className="text-gray-500 font-normal text-xl">2025-2026</span></h1>
              <p className="text-gray-400 text-sm">Head Coach: {(overview.coach && overview.coach.length < 60) ? overview.coach : '—'}</p>
              {overview.record?.record && <p className="text-gray-500 text-xs mt-0.5">Record: {overview.record.record} · {overview.record.win_pct}% win rate</p>}
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-8">
              <StatCard icon="🏆" label="Record" value={overview.record?.record ?? overview.stats?.record ?? '—'} sub={`${overview.record?.win_pct ?? overview.stats?.win_percentage ?? 0}% win rate`} />
              <StatCard
                icon={(activeSport === 'boys_soccer' || activeSport === 'girls_soccer') ? '⚽' : (activeSport === 'boys_basketball' || activeSport === 'girls_basketball') ? '🏀' : activeSport === 'baseball' ? '⚾' : '🤼'}
                label={(activeSport === 'boys_soccer' || activeSport === 'girls_soccer') ? 'Goals Scored' : (activeSport === 'boys_basketball' || activeSport === 'girls_basketball') ? 'Total Points' : activeSport === 'baseball' ? 'Team Hits' : 'Total Wins'}
                value={
                  (activeSport === 'boys_soccer' || activeSport === 'girls_soccer')
                    ? (overview.scoring?.total_goals ?? '—')
                    : (activeSport === 'boys_basketball' || activeSport === 'girls_basketball')
                    ? (overview.scoring?.total_points ?? '—')
                    : activeSport === 'baseball'
                    ? (overview.scoring?.total_hits ?? '—')
                    : activeSport === 'wrestling'
                    ? (overview.stats?.total_wins ?? '—')
                    : '—'
                }
                sub={`${overview.record?.games_played ?? overview.stats?.games_played ?? 0} games played`}
              />
              <StatCard
                icon={(activeSport === 'boys_soccer' || activeSport === 'girls_soccer') ? '🛡️' : '📊'}
                label={(activeSport === 'boys_soccer' || activeSport === 'girls_soccer') ? 'Goals Against' : 'More Stats'}
                value={overview.stats?.goals_against ?? '—'}
              />
              <StatCard
                icon="👥"
                label="Squad Size"
                value={overview.squad_size?.total ?? '—'}
                sub={
                  (activeSport === 'boys_soccer' || activeSport === 'girls_soccer')
                    ? `${overview.squad_size?.field_players ?? '?'} field + ${overview.squad_size?.goalkeepers ?? '?'} GK`
                    : activeSport === 'baseball'
                    ? `${overview.squad_size?.batters ?? '?'} batters · ${overview.squad_size?.pitchers ?? '?'} pitchers`
                    : activeSport === 'wrestling'
                    ? `${overview.squad_size?.wrestlers ?? overview.squad_size?.total ?? '?'} wrestlers`
                    : `${overview.squad_size?.players ?? overview.squad_size?.total ?? '?'} players`
                }
              />
            </div>

            {recentForm.length > 0 && (
              <div className="bg-gray-800/40 border border-gray-700 rounded-xl p-4 mb-8">
                <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wide mb-3">Recent Form (Last 5)</h3>
                <FormDots form={recentForm} />
              </div>
            )}

            {leaderboard && (
              <div className="grid md:grid-cols-3 gap-4 mb-8">
                {/* Soccer */}
                {(activeSport === 'boys_soccer' || activeSport === 'girls_soccer') && (<>
                  <div className="bg-gray-800/40 border border-gray-700 rounded-xl p-5">
                    <h3 className="font-bold text-white mb-4">⚽ Top Goal Scorers</h3>
                    <BarChart data={leaderboard.top_goals || []} valueKey="Goals" labelKey="Player" color="linear-gradient(to right, #dc2626, #ef4444)" />
                  </div>
                  <div className="bg-gray-800/40 border border-gray-700 rounded-xl p-5">
                    <h3 className="font-bold text-white mb-4">🎯 Top Assists</h3>
                    <BarChart data={leaderboard.top_assists || []} valueKey="Assists" labelKey="Player" color="linear-gradient(to right, #d97706, #f59e0b)" />
                  </div>
                  <div className="bg-gray-800/40 border border-gray-700 rounded-xl p-5">
                    <h3 className="font-bold text-white mb-4">🌟 Top Points</h3>
                    <BarChart data={leaderboard.top_points || []} valueKey="Points" labelKey="Player" color="linear-gradient(to right, #7c3aed, #8b5cf6)" />
                  </div>
                </>)}
                {/* Basketball */}
                {(activeSport === 'boys_basketball' || activeSport === 'girls_basketball') && (<>
                  <div className="bg-gray-800/40 border border-gray-700 rounded-xl p-5">
                    <h3 className="font-bold text-white mb-4">🏀 Top Points (Season)</h3>
                    <BarChart data={leaderboard.top_points || []} valueKey="Points" labelKey="Player" color="linear-gradient(to right, #ea580c, #f97316)" />
                  </div>
                  <div className="bg-gray-800/40 border border-gray-700 rounded-xl p-5">
                    <h3 className="font-bold text-white mb-4">🔄 Top Rebounds</h3>
                    <BarChart data={leaderboard.top_rebounds || []} valueKey="Rebounds" labelKey="Player" color="linear-gradient(to right, #0284c7, #38bdf8)" />
                  </div>
                  <div className="bg-gray-800/40 border border-gray-700 rounded-xl p-5">
                    <h3 className="font-bold text-white mb-4">🎯 Top Assists</h3>
                    <BarChart data={leaderboard.top_assists || []} valueKey="Assists" labelKey="Player" color="linear-gradient(to right, #7c3aed, #8b5cf6)" />
                  </div>
                </>)}
                {/* Baseball */}
                {activeSport === 'baseball' && (<>
                  <div className="bg-gray-800/40 border border-gray-700 rounded-xl p-5">
                    <h3 className="font-bold text-white mb-4">⚾ Top Batting AVG</h3>
                    <BarChart data={leaderboard.top_avg || []} valueKey="AVG" labelKey="Player" color="linear-gradient(to right, #15803d, #22c55e)" />
                  </div>
                  <div className="bg-gray-800/40 border border-gray-700 rounded-xl p-5">
                    <h3 className="font-bold text-white mb-4">💥 Top RBI</h3>
                    <BarChart data={leaderboard.top_rbi || []} valueKey="RBI" labelKey="Player" color="linear-gradient(to right, #dc2626, #ef4444)" />
                  </div>
                  <div className="bg-gray-800/40 border border-gray-700 rounded-xl p-5">
                    <h3 className="font-bold text-white mb-4">🔥 Top Strikeouts (P)</h3>
                    <BarChart data={leaderboard.top_k || []} valueKey="Strikeouts" labelKey="Player" color="linear-gradient(to right, #d97706, #f59e0b)" />
                  </div>
                </>)}
                {/* Wrestling */}
                {activeSport === 'wrestling' && (<>
                  <div className="bg-gray-800/40 border border-gray-700 rounded-xl p-5">
                    <h3 className="font-bold text-white mb-4">🤼 Most Wins</h3>
                    <BarChart data={leaderboard.top_wins || []} valueKey="Wins" labelKey="Player" color="linear-gradient(to right, #dc2626, #ef4444)" />
                  </div>
                  <div className="bg-gray-800/40 border border-gray-700 rounded-xl p-5">
                    <h3 className="font-bold text-white mb-4">📌 Most Pins</h3>
                    <BarChart data={leaderboard.top_pins || []} valueKey="Pins" labelKey="Player" color="linear-gradient(to right, #7c3aed, #8b5cf6)" />
                  </div>
                  <div className="bg-gray-800/40 border border-gray-700 rounded-xl p-5 flex items-center justify-center text-gray-500 text-sm">
                    More stats coming soon
                  </div>
                </>)}
              </div>
            )}

            {(activeSport === 'boys_soccer' || activeSport === 'girls_soccer') && yearOverYear && yearOverYear['2024-2025'] && yearOverYear['2025-2026'] && (
              <div className="bg-gray-800/40 border border-gray-700 rounded-xl p-5 mb-8">
                <h3 className="font-bold text-white mb-4">📈 Year-Over-Year Comparison</h3>
                <div className="grid md:grid-cols-3 gap-4">
                  {[
                    { label: 'Total Goals', prev: yearOverYear['2024-2025'].total_goals, curr: yearOverYear['2025-2026'].total_goals },
                    { label: 'Total Assists', prev: yearOverYear['2024-2025'].total_assists, curr: yearOverYear['2025-2026'].total_assists },
                    { label: 'Players', prev: yearOverYear['2024-2025'].players, curr: yearOverYear['2025-2026'].players },
                  ].map(({ label, prev, curr }) => {
                    const diff = curr - prev;
                    const pct = prev > 0 ? Math.round((diff / prev) * 100) : 0;
                    return (
                      <div key={label} className="bg-gray-900/50 rounded-lg p-4">
                        <div className="text-xs text-gray-500 uppercase tracking-wide mb-2">{label}</div>
                        <div className="flex items-end gap-3">
                          <div className="text-center"><div className="text-xl font-bold text-gray-400">{prev}</div><div className="text-xs text-gray-600">2024-25</div></div>
                          <div className={`text-sm font-bold px-2 py-0.5 rounded flex-shrink-0 ${diff > 0 ? 'text-green-400 bg-green-400/10' : diff < 0 ? 'text-red-400 bg-red-400/10' : 'text-gray-400 bg-gray-700'}`}>
                            {diff > 0 ? '▲' : diff < 0 ? '▼' : '='} {Math.abs(pct)}%
                          </div>
                          <div className="text-center"><div className="text-xl font-bold text-white">{curr}</div><div className="text-xs text-gray-600">2025-26</div></div>
                        </div>
                      </div>
                    );
                  })}
                </div>
                <div className="mt-3 grid md:grid-cols-2 gap-3 text-sm">
                  {([['2024-2025', yearOverYear['2024-2025']], ['2025-2026', yearOverYear['2025-2026']]] as [string, any][]).map(([season, d]) => d?.top_scorer && (
                    <div key={season} className="bg-gray-900/50 rounded-lg p-3">
                      <span className="text-gray-500 text-xs">{season} Top Scorer:</span>
                      <span className="ml-2 text-white font-semibold">{d.top_scorer.Player}</span>
                      <span className="ml-1 text-yellow-400">({d.top_scorer.Goals} goals)</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {(activeSport === 'boys_soccer' || activeSport === 'girls_soccer') && goalkeepers.length > 0 && (
              <div className="bg-gray-800/40 border border-gray-700 rounded-xl p-5 mb-8">
                <h3 className="font-bold text-white mb-4">🥅 Goalkeepers</h3>
                <div className="grid md:grid-cols-2 gap-3">
                  {goalkeepers.map((gk: any, i: number) => (
                    <div key={i} className="bg-gray-900/50 rounded-lg p-4 flex justify-between items-center">
                      <div><div className="font-semibold text-white">{gk.Player}</div><div className="text-xs text-gray-500">{gk['Year/Position']}</div></div>
                      <div className="text-right"><div className="text-2xl font-black text-yellow-400">{gk.Saves}</div><div className="text-xs text-gray-500">saves · {gk['Games Played']} games</div></div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {upcomingGames.length > 0 && (
              <div className="bg-gray-800/40 border border-gray-700 rounded-xl p-5 mb-8">
                <h3 className="font-bold text-white mb-4">📅 Upcoming Games</h3>
                <div className="space-y-2">
                  {upcomingGames.map((g: any, i: number) => (
                    <div key={i} className="flex items-center justify-between bg-gray-900/50 rounded-lg px-4 py-3">
                      <span className="text-gray-300 font-medium">{g.Opponent}</span>
                      <span className="text-xs text-gray-500">{g.Date}</span>
                      <span className={`text-xs px-2 py-1 rounded ${g.Location === 'Home' ? 'bg-green-900/40 text-green-400' : 'bg-blue-900/40 text-blue-400'}`}>{g.Location}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="text-center py-4">
              <p className="text-gray-400 mb-3">Want deeper analysis?</p>
              <button onClick={() => setView('chat')} className="px-6 py-3 bg-gradient-to-r from-red-600 to-red-700 hover:from-red-500 hover:to-red-600 text-white font-bold rounded-xl transition-all hover:scale-105">
                🤖 Ask the AI →
              </button>
            </div>
          </>
        ) : (
          <div className="text-center py-32 text-gray-500">
            <p className="text-xl mb-4">⚠️ Could not load stats</p>
            <p className="text-sm mb-4">Make sure the backend is running: <code className="bg-gray-800 px-2 py-1 rounded">python api.py</code></p>
            <button 
              onClick={() => loadStats()} 
              className="px-4 py-2 bg-red-600 text-white rounded-lg"
            >
              Retry
            </button>
          </div>
        )}
      </div>
    </div>
  );

  // ── CHAT ──
  if (view === 'chat') return (
    <div className="min-h-screen bg-gray-950 text-white flex flex-col">
      <Nav />
      <div className="max-w-4xl mx-auto w-full px-4 py-4 flex flex-col" style={{ height: 'calc(100vh - 57px)' }}>
        <div className="flex-1 overflow-y-auto space-y-4 pb-4">
          {messages.length === 0 && (
            <div className="text-center mt-12">
              <div className="text-6xl mb-4">🤖</div>
              <p className="text-gray-300 text-xl font-semibold">Edison Eagles AI Analyst</p>
              <p className="text-gray-500 mt-2 text-sm">{coachAuthed ? '🔐 Coach mode — I have access to injuries, notes & scouting reports.' : 'Ask me anything about the team — stats, scouting, tactics, trends.'}</p>
              <div className="mt-6 flex flex-wrap gap-2 justify-center">
                {["Who are the top performers in boys basketball?", "How is girls soccer doing?", "Compare this soccer season to last year", "Who leads wrestling in wins?", coachAuthed ? "Who should start given current injuries?" : "When is our next game?", "Who has the most assists in boys soccer?"].map((s, i) => (
                  <button key={i} onClick={() => setInput(s)} className="px-3 py-2 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded-full text-xs border border-gray-700 transition-all hover:scale-105">{s}</button>
                ))}
              </div>
            </div>
          )}
          {messages.map((msg, idx) => (
            <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              {msg.role === 'assistant' && <div className="w-8 h-8 rounded-full bg-gradient-to-r from-red-600 to-yellow-500 flex items-center justify-center text-sm mr-2 flex-shrink-0 mt-1">🦅</div>}
              <div className={`max-w-[80%] rounded-2xl px-5 py-3 text-sm leading-relaxed whitespace-pre-wrap ${msg.role === 'user' ? 'bg-gradient-to-r from-red-700 to-red-600 text-white rounded-br-sm' : 'bg-gray-800 text-gray-100 rounded-bl-sm border border-gray-700'}`}>
                {msg.content}
              </div>
            </div>
          ))}
          {isLoading && (
            <div className="flex justify-start">
              <div className="w-8 h-8 rounded-full bg-gradient-to-r from-red-600 to-yellow-500 flex items-center justify-center text-sm mr-2 flex-shrink-0">🦅</div>
              <div className="bg-gray-800 border border-gray-700 rounded-2xl rounded-bl-sm px-5 py-4">
                <div className="flex space-x-1">
                  {[0, 0.15, 0.3].map((d, i) => <div key={i} className="w-2 h-2 bg-red-400 rounded-full animate-bounce" style={{ animationDelay: `${d}s` }}></div>)}
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
        <div className="border-t border-gray-800 pt-4">
          <div className="flex gap-3 items-end">
            <div className="flex-1 bg-gray-800 border border-gray-700 rounded-2xl overflow-hidden focus-within:border-red-500 transition-colors">
              <textarea value={input} onChange={e => setInput(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); } }}
                placeholder={coachAuthed ? "Coach mode active — ask anything..." : "Ask me anything about Edison Athletics..."}
                rows={1} className="w-full bg-transparent text-white px-5 py-3 focus:outline-none placeholder-gray-500 resize-none text-sm" />
            </div>
            <button onClick={handleSend} disabled={!input.trim() || isLoading}
              className="bg-gradient-to-r from-red-600 to-red-700 hover:from-red-500 hover:to-red-600 disabled:from-gray-700 disabled:to-gray-800 text-white w-12 h-12 rounded-2xl transition-all disabled:cursor-not-allowed flex items-center justify-center text-lg hover:scale-105 active:scale-95">
              {isLoading ? '⏳' : '➤'}
            </button>
          </div>
          <p className="text-gray-700 text-xs mt-2 text-center">Powered by Llama 3.3 70B · Live data from nj.com</p>
        </div>
      </div>
    </div>
  );

  // ── COACH PORTAL ──
  return (
    <div className="min-h-screen bg-gray-950 text-white">
      <Nav />
      <div className="max-w-4xl mx-auto px-4 py-8">
        {!coachAuthed ? (
          <div className="flex items-center justify-center py-20">
            <div className="bg-gray-900 border border-gray-700 rounded-2xl p-8 w-full max-w-sm">
              <div className="text-center mb-6">
                <div className="text-5xl mb-3">🔐</div>
                <h2 className="text-2xl font-black">Coach Portal</h2>
                <p className="text-gray-400 text-sm mt-1">Restricted to coaching staff</p>
              </div>
              <input type="password" value={coachPassword} onChange={e => setCoachPassword(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleCoachLogin()}
                placeholder="Enter coach password"
                className="w-full bg-gray-800 border border-gray-700 rounded-xl px-4 py-3 text-white placeholder-gray-500 focus:outline-none focus:border-red-500 mb-3" />
              {coachAuthError && <p className="text-red-400 text-sm mb-3">{coachAuthError}</p>}
              <button onClick={handleCoachLogin} className="w-full py-3 bg-gradient-to-r from-red-600 to-red-700 hover:from-red-500 hover:to-red-600 text-white font-bold rounded-xl transition-all">Login →</button>
              <p className="text-center text-xs text-gray-600 mt-3">Default: eagles2026<br />(set COACH_PASSWORD in .env to change)</p>
            </div>
          </div>
        ) : (
          <>
            <div className="flex items-center justify-between mb-8">
              <div>
                <h1 className="text-3xl font-black">Coach Dashboard</h1>
                <p className="text-green-400 text-sm flex items-center gap-1 mt-1"><span className="w-1.5 h-1.5 bg-green-400 rounded-full"></span> Authenticated as {coachName}</p>
              </div>
              <button onClick={() => setView('chat')} className="px-4 py-2 bg-red-600 hover:bg-red-500 text-white rounded-lg font-semibold text-sm transition-all">🤖 AI (Coach Mode)</button>
            </div>

            {coachFeedback && <div className="mb-4 px-4 py-3 bg-green-900/30 border border-green-700 text-green-400 rounded-xl text-sm">{coachFeedback}</div>}

            {coachDashboard && (
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-8">
                <StatCard icon="🏥" label="Active Injuries" value={coachDashboard.team_health?.injured_count || 0} />
                <StatCard icon="📋" label="Scouting Reports" value={coachDashboard.scouting_reports_count || 0} />
                <StatCard icon="📝" label="Coach Notes" value={coachDashboard.coach_notes_count || 0} />
                <div className="bg-gray-800/60 border border-gray-700 rounded-xl p-4">
                  <div className="text-2xl mb-1">📈</div>
                  <div className="text-xs text-gray-400 uppercase tracking-wide mb-2">Recent Form</div>
                  <FormDots form={coachDashboard.recent_form || []} />
                </div>
              </div>
            )}

            {coachDashboard?.top_performers?.length > 0 && (
              <div className="bg-gray-800/40 border border-gray-700 rounded-xl p-5 mb-6">
                <h3 className="font-bold text-white mb-3">⭐ Top Performers</h3>
                <div className="grid md:grid-cols-3 gap-3">
                  {coachDashboard.top_performers.map((p: any, i: number) => (
                    <div key={i} className="bg-gray-900/50 rounded-lg p-3 flex justify-between items-center">
                      <div className="font-medium text-white text-sm">{p.Player}</div>
                      <div className="text-xs text-gray-400">{p.Goals}G / {p.Assists}A</div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {coachDashboard?.team_health?.active_injuries?.length > 0 && (
              <div className="bg-red-900/20 border border-red-800 rounded-xl p-5 mb-6">
                <h3 className="font-bold text-red-400 mb-3">🏥 Active Injuries</h3>
                <div className="space-y-2">
                  {coachDashboard.team_health.active_injuries.map((inj: any, i: number) => (
                    <div key={i} className="flex justify-between items-center bg-gray-900/50 rounded-lg px-4 py-2">
                      <div><span className="font-semibold text-white">{inj.player}</span><span className="text-gray-400 text-sm ml-2">— {inj.injury}</span></div>
                      {inj.expected_return && <span className="text-xs text-yellow-400">Return: {inj.expected_return}</span>}
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="grid md:grid-cols-3 gap-4 mb-6">
              <div className="bg-gray-800/40 border border-gray-700 rounded-xl p-5">
                <h3 className="font-bold text-white mb-3">📝 Add Team Note</h3>
                <select value={newNote.category} onChange={e => setNewNote(p => ({ ...p, category: e.target.value }))}
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm mb-2 focus:outline-none">
                  <option value="general">General</option>
                  <option value="tactical">Tactical</option>
                  <option value="motivation">Motivation</option>
                </select>
                <textarea value={newNote.note} onChange={e => setNewNote(p => ({ ...p, note: e.target.value }))}
                  placeholder="Add a team note..." rows={4}
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm placeholder-gray-500 focus:outline-none resize-none mb-2" />
                <button onClick={saveCoachNote} disabled={coachSaving === 'note'}
                  className="w-full py-2 bg-red-600 hover:bg-red-500 disabled:bg-gray-700 text-white font-semibold rounded-lg text-sm transition-all">
                  {coachSaving === 'note' ? 'Saving...' : 'Save Note'}
                </button>
              </div>

              <div className="bg-gray-800/40 border border-gray-700 rounded-xl p-5">
                <h3 className="font-bold text-white mb-3">🏥 Report Injury</h3>
                {[
                  { key: 'player_name', ph: 'Player name', val: newInjury.player_name, set: (v: string) => setNewInjury(p => ({ ...p, player_name: v })) },
                  { key: 'injury_type', ph: 'Injury description', val: newInjury.injury_type, set: (v: string) => setNewInjury(p => ({ ...p, injury_type: v })) },
                  { key: 'expected_return', ph: 'Expected return (e.g. Jan 15)', val: newInjury.expected_return, set: (v: string) => setNewInjury(p => ({ ...p, expected_return: v })) },
                ].map(({ key, ph, val, set }) => (
                  <input key={key} value={val} onChange={e => set(e.target.value)} placeholder={ph}
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm placeholder-gray-500 focus:outline-none mb-2" />
                ))}
                <button onClick={saveInjury} disabled={coachSaving === 'injury'}
                  className="w-full py-2 bg-red-600 hover:bg-red-500 disabled:bg-gray-700 text-white font-semibold rounded-lg text-sm transition-all">
                  {coachSaving === 'injury' ? 'Saving...' : 'Report Injury'}
                </button>
              </div>

              <div className="bg-gray-800/40 border border-gray-700 rounded-xl p-5">
                <h3 className="font-bold text-white mb-3">🎯 Scouting Report</h3>
                {[
                  { key: 'opponent', ph: 'Opponent name *' },
                  { key: 'strengths', ph: 'Their strengths' },
                  { key: 'weaknesses', ph: 'Their weaknesses' },
                  { key: 'key_players', ph: 'Key players to watch' },
                  { key: 'tactical_notes', ph: 'Tactical notes' },
                  { key: 'game_plan', ph: 'Our game plan' },
                ].map(({ key, ph }) => (
                  <input key={key} value={(newScouting as any)[key]} onChange={e => setNewScouting(p => ({ ...p, [key]: e.target.value }))} placeholder={ph}
                    className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm placeholder-gray-500 focus:outline-none mb-2" />
                ))}
                <button onClick={saveScouting} disabled={coachSaving === 'scouting'}
                  className="w-full py-2 bg-red-600 hover:bg-red-500 disabled:bg-gray-700 text-white font-semibold rounded-lg text-sm transition-all">
                  {coachSaving === 'scouting' ? 'Saving...' : 'Save Report'}
                </button>
              </div>
            </div>

            <div className="bg-gray-900 border border-gray-700 rounded-xl p-4 text-sm">
              <p className="font-semibold text-gray-300 mb-1">💡 Tips</p>
              <p className="text-xs text-gray-500">All notes, injuries, and scouting reports feed into the AI in Coach Mode. Try asking: "Who should start given current injuries?" or "Give me a game plan against [opponent]"</p>
            </div>
          </>
        )}
      </div>
    </div>
  );
}