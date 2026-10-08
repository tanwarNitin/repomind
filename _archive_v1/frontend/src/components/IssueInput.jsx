import React, { useState } from 'react';
import { Bug, Send, Sparkles, ShieldAlert, Code2, Key, ChevronDown, ChevronUp } from 'lucide-react';

const SAMPLE_ISSUES = [
  {
    title: "Database Credentials & Connection Bug",
    issue: `CRITICAL: Database connection fails silently when executing queries!
Stacktrace:
File "src/database/connection.py", line 18, in connect
DB_URI = "postgresql://admin:SecretPass123!@db.internal.repo:5432/repomind_db"
API_KEY = "gsk_live_99887766554433221100aabbccdd"
RuntimeError: Database connection is closed!
Please sanitize sensitive credentials and ensure connect() validates status before executing queries.`
  },
  {
    title: "C++ Buffer Overflow & Null Pointer Bug",
    issue: `SEGFAULT IN CPP PACKET PROCESSOR:
File "src/parser/parser.cpp", line 22, in PacketProcessor::add_packet
Warning: empty packet received
Crash: Memory access violation at 0x00000000000.
PacketProcessor fails to check string validity before buffer.push_back().
Please patch C++ struct memory handling.`
  }
];

export default function IssueInput({ onSubmit, isRunning }) {
  const [issueText, setIssueText] = useState(SAMPLE_ISSUES[0].issue);
  const [showKeysDrawer, setShowKeysDrawer] = useState(false);
  const [groqKey, setGroqKey] = useState('');
  const [geminiKey, setGeminiKey] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!issueText.trim() || isRunning) return;
    onSubmit(issueText, groqKey, geminiKey);
  };

  return (
    <div className="glass-panel rounded-xl p-4 border border-slate-800 shadow-xl flex flex-col h-full">
      <div className="flex items-center justify-between pb-3 mb-3 border-b border-slate-800">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-rose-500/10 text-rose-400 border border-rose-500/20">
            <Bug className="w-4 h-4" />
          </div>
          <div>
            <h2 className="text-sm font-bold text-slate-100 uppercase tracking-wider">Issue & Log Trace Input</h2>
            <p className="text-xs text-slate-400">Guardrails Secret Sanitizer Active</p>
          </div>
        </div>
        <button
          type="button"
          onClick={() => setShowKeysDrawer(!showKeysDrawer)}
          className="flex items-center gap-1 text-[11px] px-2.5 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 font-medium transition"
        >
          <Key className="w-3 h-3 text-emerald-400" />
          {showKeysDrawer ? 'Hide Keys' : 'API Keys'}
          {showKeysDrawer ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
        </button>
      </div>

      {/* Optional Free API Keys Drawer */}
      {showKeysDrawer && (
        <div className="mb-3 p-3 bg-slate-900/90 rounded-xl border border-slate-800 space-y-2 animate-in fade-in duration-150">
          <p className="text-[11px] text-slate-400">
            Supply your free-tier API keys below (or leave blank to use built-in offline fallback engine):
          </p>
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="text-[10px] text-slate-400 font-mono">GROQ_API_KEY (Free)</label>
              <input
                type="password"
                value={groqKey}
                onChange={(e) => setGroqKey(e.target.value)}
                placeholder="gsk_..."
                className="w-full p-1.5 text-xs font-mono bg-slate-950 text-slate-200 border border-slate-800 rounded focus:outline-none focus:border-emerald-500/50"
              />
            </div>
            <div>
              <label className="text-[10px] text-slate-400 font-mono">GEMINI_API_KEY (Free)</label>
              <input
                type="password"
                value={geminiKey}
                onChange={(e) => setGeminiKey(e.target.value)}
                placeholder="AIzaSy..."
                className="w-full p-1.5 text-xs font-mono bg-slate-950 text-slate-200 border border-slate-800 rounded focus:outline-none focus:border-emerald-500/50"
              />
            </div>
          </div>
        </div>
      )}

      <form onSubmit={handleSubmit} className="flex-1 flex flex-col space-y-3">
        <div className="flex flex-wrap gap-2">
          <span className="text-xs text-slate-400 self-center font-medium">Quick Samples:</span>
          {SAMPLE_ISSUES.map((sample, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => setIssueText(sample.issue)}
              className="text-xs px-2.5 py-1 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-300 border border-slate-700/80 hover:border-emerald-500/40 transition flex items-center gap-1.5"
            >
              <Code2 className="w-3 h-3 text-emerald-400" />
              {sample.title}
            </button>
          ))}
        </div>

        <div className="relative flex-1">
          <textarea
            value={issueText}
            onChange={(e) => setIssueText(e.target.value)}
            placeholder="Paste bug report, error stack trace, or issue description here..."
            className="w-full h-full min-h-[160px] p-3 text-xs font-mono bg-slate-950/80 text-slate-200 border border-slate-800 rounded-lg focus:outline-none focus:border-emerald-500/60 focus:ring-1 focus:ring-emerald-500/40 resize-none transition"
          />
        </div>

        <div className="flex items-center justify-between pt-1">
          <span className="text-[11px] text-slate-500">
            Routes via LiteLLM to Groq Llama-3.3-70B & Gemini Free APIs
          </span>
          <button
            type="submit"
            disabled={isRunning || !issueText.trim()}
            className="flex items-center gap-2 px-4 py-2 text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg transition duration-200 shadow-lg shadow-emerald-900/30 disabled:opacity-50"
          >
            {isRunning ? (
              <>
                <Sparkles className="w-4 h-4 animate-spin text-emerald-200" />
                Triaging Agent Active...
              </>
            ) : (
              <>
                <Send className="w-4 h-4" />
                Triage Issue & Fix Bug
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
}
