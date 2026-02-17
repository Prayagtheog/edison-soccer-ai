'use client';

import { useState, useRef, useEffect } from 'react';

interface Message {
  role: 'user' | 'assistant';
  content: string;
}

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [conversationHistory, setConversationHistory] = useState<any[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage = input.trim();
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
    setIsLoading(true);

    try {
      const response = await fetch('http://localhost:8000/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: userMessage,
          conversation_history: conversationHistory
        })
      });

      const data = await response.json();

      if (data.response) {
        setMessages(prev => [...prev, { role: 'assistant', content: data.response }]);
        setConversationHistory(data.conversation_history || []);
      } else {
        throw new Error('No response from server');
      }
    } catch (error) {
      console.error('Error:', error);
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: '❌ Error connecting to backend. Make sure it is running on port 8000.'
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const suggestions = [
    "⚽ Who are our top scorers?",
    "📊 What's our record?",
    "📅 Tell me about our next game",
    "🥅 How are our goalkeepers doing?",
    "📈 Compare this season to last year"
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900">
      {/* Header */}
      <div className="border-b border-gray-700 bg-gray-900/80 backdrop-blur-sm sticky top-0 z-10">
        <div className="max-w-4xl mx-auto px-6 py-4 flex items-center gap-4">
          <div className="text-4xl">🦅</div>
          <div>
            <h1 className="text-2xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-red-500 to-yellow-400">
              Edison Eagles Soccer AI
            </h1>
            <p className="text-gray-400 text-sm">Your intelligent scouting assistant</p>
          </div>
          <div className="ml-auto flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></div>
            <span className="text-green-400 text-sm">Live</span>
          </div>
        </div>
      </div>

      {/* Chat Container */}
      <div className="max-w-4xl mx-auto px-4 py-6 flex flex-col h-[calc(100vh-80px)]">
        {/* Messages */}
        <div className="flex-1 overflow-y-auto space-y-4 pb-4">
          {messages.length === 0 && (
            <div className="text-center mt-16">
              <div className="text-7xl mb-4">⚽</div>
              <p className="text-gray-300 text-xl font-medium">Hey! I'm your Edison Eagles soccer analyst.</p>
              <p className="text-gray-500 mt-2">Ask me anything about the team - stats, players, upcoming games, scouting reports.</p>

              {/* Suggestion chips */}
              <div className="mt-8 flex flex-wrap gap-2 justify-center">
                {suggestions.map((s, i) => (
                  <button
                    key={i}
                    onClick={() => setInput(s.replace(/^[^\s]+ /, ''))}
                    className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-gray-300 rounded-full text-sm transition-all hover:scale-105 border border-gray-600"
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((msg, idx) => (
            <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              {msg.role === 'assistant' && (
                <div className="w-8 h-8 rounded-full bg-gradient-to-r from-red-600 to-yellow-500 flex items-center justify-center text-sm mr-2 flex-shrink-0 mt-1">
                  🦅
                </div>
              )}
              <div className={`max-w-[80%] rounded-2xl px-5 py-3 ${
                msg.role === 'user'
                  ? 'bg-gradient-to-r from-red-700 to-red-600 text-white rounded-br-sm'
                  : 'bg-gray-700/80 text-gray-100 rounded-bl-sm border border-gray-600'
              }`}>
                <p className="whitespace-pre-wrap text-sm leading-relaxed">{msg.content}</p>
              </div>
            </div>
          ))}

          {isLoading && (
            <div className="flex justify-start">
              <div className="w-8 h-8 rounded-full bg-gradient-to-r from-red-600 to-yellow-500 flex items-center justify-center text-sm mr-2 flex-shrink-0">
                🦅
              </div>
              <div className="bg-gray-700/80 border border-gray-600 rounded-2xl rounded-bl-sm px-5 py-4">
                <div className="flex space-x-1">
                  <div className="w-2 h-2 bg-red-400 rounded-full animate-bounce"></div>
                  <div className="w-2 h-2 bg-yellow-400 rounded-full animate-bounce" style={{ animationDelay: '0.15s' }}></div>
                  <div className="w-2 h-2 bg-red-400 rounded-full animate-bounce" style={{ animationDelay: '0.3s' }}></div>
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div className="border-t border-gray-700 pt-4">
          <div className="flex gap-3 items-end">
            <div className="flex-1 bg-gray-700/80 border border-gray-600 rounded-2xl overflow-hidden focus-within:border-red-500 transition-colors">
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyPress}
                placeholder="Ask me anything about Edison soccer..."
                rows={1}
                className="w-full bg-transparent text-white px-5 py-3 focus:outline-none placeholder-gray-400 resize-none text-sm"
              />
            </div>
            <button
              onClick={handleSend}
              disabled={!input.trim() || isLoading}
              className="bg-gradient-to-r from-red-600 to-red-700 hover:from-red-500 hover:to-red-600 disabled:from-gray-600 disabled:to-gray-700 text-white w-12 h-12 rounded-2xl font-medium transition-all disabled:cursor-not-allowed flex items-center justify-center text-lg hover:scale-105 active:scale-95"
            >
              {isLoading ? '⏳' : '➤'}
            </button>
          </div>
          <p className="text-gray-600 text-xs mt-2 text-center">Powered by Edison Soccer AI • Real stats from nj.com</p>
        </div>
      </div>
    </div>
  );
}