import { useState } from 'react';
import { Bot, Send, User, AlertCircle, Loader2 } from 'lucide-react';
import { askQuestion, getIncidents } from '../api/client';
import { useEffect } from 'react';
import type { Incident } from '../types';
import clsx from 'clsx';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  sources?: string[];
  error?: boolean;
}

const SUGGESTED_QUESTIONS = [
  'Why did this incident happen?',
  'Which service caused the issue?',
  'What changed before the incident?',
  'Which logs support this root cause?',
  'What should I investigate next?',
  'How can this incident be prevented?',
];

export default function AIAssistant() {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'assistant',
      content: 'Hello! I\'m the DevInsight AI assistant. I can help you investigate incidents, understand root causes, and recommend remediation steps. Select an incident below and ask me anything about it.',
    },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [selectedIncident, setSelectedIncident] = useState<string>('');

  useEffect(() => {
    getIncidents({ page_size: 10 })
      .then(d => setIncidents(d.incidents))
      .catch(() => null);
  }, []);

  const send = async (question?: string) => {
    const q = question || input;
    if (!q.trim() || loading) return;
    setInput('');

    const userMsg: Message = { role: 'user', content: q };
    setMessages(m => [...m, userMsg]);
    setLoading(true);

    try {
      const result = await askQuestion({
        question: q,
        incident_id: selectedIncident || undefined,
      });

      setMessages(m => [...m, {
        role: 'assistant',
        content: result.answer || 'No response received.',
        sources: result.sources,
      }]);
    } catch (e: unknown) {
      setMessages(m => [...m, {
        role: 'assistant',
        content: 'Failed to get a response. Please check the backend connection.',
        error: true,
      }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full p-6">
      <div className="mb-5">
        <h1 className="text-xl font-semibold text-white">AI Assistant</h1>
        <p className="text-sm text-slate-400 mt-0.5">
          Incident investigation assistant powered by Gemini AI
        </p>
      </div>

      <div className="flex gap-5 flex-1 min-h-0">
        {/* Chat */}
        <div className="flex flex-col flex-1 card overflow-hidden">
          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {messages.map((msg, i) => (
              <div key={i} className={clsx('flex gap-3', msg.role === 'user' && 'flex-row-reverse')}>
                <div className={clsx(
                  'w-8 h-8 rounded-full flex items-center justify-center shrink-0',
                  msg.role === 'assistant' ? 'bg-brand-600' : 'bg-surface-600'
                )}>
                  {msg.role === 'assistant' ? <Bot size={16} /> : <User size={16} />}
                </div>
                <div className={clsx(
                  'flex-1 max-w-[80%] p-3 rounded-xl text-sm',
                  msg.role === 'assistant'
                    ? clsx('bg-surface-700 text-slate-200', msg.error && 'border border-red-700/30 bg-red-900/10')
                    : 'bg-brand-600 text-white ml-auto',
                )}>
                  <p className="leading-relaxed whitespace-pre-wrap">{msg.content}</p>
                  {msg.sources && msg.sources.length > 0 && (
                    <p className="text-xs text-slate-500 mt-2">Sources: {msg.sources.join(', ')}</p>
                  )}
                  {msg.error && (
                    <div className="flex items-center gap-1 mt-1 text-xs text-red-400">
                      <AlertCircle size={12} /> Error
                    </div>
                  )}
                </div>
              </div>
            ))}
            {loading && (
              <div className="flex gap-3">
                <div className="w-8 h-8 rounded-full bg-brand-600 flex items-center justify-center shrink-0">
                  <Bot size={16} />
                </div>
                <div className="bg-surface-700 rounded-xl p-3">
                  <Loader2 size={16} className="animate-spin text-slate-400" />
                </div>
              </div>
            )}
          </div>

          {/* Suggested questions */}
          <div className="px-4 py-2 border-t border-slate-700/50 flex flex-wrap gap-2">
            {SUGGESTED_QUESTIONS.map((q, i) => (
              <button
                key={i}
                onClick={() => send(q)}
                disabled={loading}
                className="text-xs px-2.5 py-1.5 bg-surface-700 hover:bg-surface-600 text-slate-400 hover:text-slate-200 rounded-full border border-slate-700/30 transition-colors disabled:opacity-50"
              >
                {q}
              </button>
            ))}
          </div>

          {/* Input */}
          <div className="p-4 border-t border-slate-700/50 flex gap-3">
            <input
              type="text"
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && !e.shiftKey && send()}
              placeholder="Ask about an incident…"
              disabled={loading}
              className="flex-1 bg-surface-700 border border-slate-700/50 rounded-lg px-3 py-2 text-sm text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-brand-500/50 disabled:opacity-50"
            />
            <button
              onClick={() => send()}
              disabled={loading || !input.trim()}
              className="btn-primary disabled:opacity-40"
            >
              <Send size={14} />
            </button>
          </div>
        </div>

        {/* Sidebar */}
        <div className="w-64 shrink-0 space-y-4">
          <div className="card p-4">
            <h3 className="text-sm font-medium text-slate-300 mb-3">Incident Context</h3>
            <select
              value={selectedIncident}
              onChange={e => setSelectedIncident(e.target.value)}
              className="w-full bg-surface-700 border border-slate-700/50 rounded-lg px-3 py-2 text-xs text-slate-200"
            >
              <option value="">No specific incident</option>
              {incidents.map(inc => (
                <option key={inc.id} value={inc.id}>
                  {inc.title.slice(0, 45)}…
                </option>
              ))}
            </select>
            {selectedIncident && (
              <p className="text-xs text-slate-500 mt-2">
                Questions will use this incident's data as context.
              </p>
            )}
          </div>

          <div className="card p-4">
            <h3 className="text-sm font-medium text-slate-300 mb-2">How it works</h3>
            <p className="text-xs text-slate-500 leading-relaxed">
              The AI assistant uses incident data, RCA results, and telemetry evidence as context.
              It only answers based on available evidence — it does not invent metrics or logs.
            </p>
            <p className="text-xs text-slate-600 mt-2">
              Requires GEMINI_API_KEY to be configured for full AI responses.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
