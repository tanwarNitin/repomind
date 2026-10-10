import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { generateExplain } from '../api';

export default function Explain({ currentRepo }) {
  const [explanation, setExplanation] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleExplain = async () => {
    if (!currentRepo) return alert('Select a repo');
    setLoading(true);
    setError('');
    try {
      const res = await generateExplain(currentRepo);
      if (res.explanation) {
        setExplanation(res.explanation);
      } else if (res.error) {
        setError(res.error);
      }
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-8 h-full overflow-y-auto bg-bg text-textMain font-mono text-sm">
      <div className="max-w-4xl mx-auto">
        <div className="flex justify-between items-center mb-8 border-b border-border pb-4">
          <h1 className="text-xl font-bold tracking-wider">ARCHITECTURE EXPLAINER: {currentRepo || 'NONE'}</h1>
          <button 
            onClick={handleExplain}
            disabled={loading}
            className="bg-border hover:bg-textMuted px-4 py-2 rounded font-bold transition-colors disabled:opacity-50"
          >
            {loading ? 'ANALYZING...' : 'EXPLAIN ARCHITECTURE'}
          </button>
        </div>

        {error && <div className="text-accentFail mb-4">{error}</div>}

        {!explanation && !loading && !error && (
          <div className="text-textMuted italic">No architecture overview generated.</div>
        )}

        {explanation && (
          <div className="bg-panel border border-border p-6 shadow-sm prose prose-invert max-w-none prose-pre:bg-[#0A0A0A] prose-pre:border prose-pre:border-border">
            <ReactMarkdown>{explanation}</ReactMarkdown>
          </div>
        )}
      </div>
    </div>
  );
}
