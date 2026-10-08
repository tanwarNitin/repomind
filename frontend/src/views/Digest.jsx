import React, { useState } from 'react';
import { generateDigest, getDigest } from '../api';

export default function Digest({ currentRepo }) {
  const [digestData, setDigestData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleGenerate = async () => {
    if (!currentRepo) return alert('Select a repo');
    setLoading(true);
    setError('');
    try {
      const res = await generateDigest(currentRepo);
      if (res.data.digest_id) {
        const fetchRes = await getDigest(res.data.digest_id);
        if (fetchRes.data) {
          setDigestData(fetchRes.data);
        } else {
          setError('Failed to fetch digest data');
        }
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
          <h1 className="text-xl font-bold tracking-wider">MORNING DIGEST: {currentRepo || 'NONE'}</h1>
          <button 
            onClick={handleGenerate}
            disabled={loading}
            className="bg-border hover:bg-textMuted px-4 py-2 rounded font-bold transition-colors disabled:opacity-50"
          >
            {loading ? 'GENERATING...' : 'GENERATE DIGEST'}
          </button>
        </div>

        {error && <div className="text-accentFail mb-4">{error}</div>}

        {!digestData && !loading && !error && (
          <div className="text-textMuted italic">No digest generated for current session.</div>
        )}

        {digestData && (
          <div className="space-y-6">
            {digestData.issues && digestData.issues.map((issue, i) => (
              <div key={i} className="bg-panel border border-border p-4 shadow-sm">
                <div className="flex justify-between items-start mb-2">
                  <h3 className="font-bold text-lg">
                    {issue.issue_id || `Issue #${i + 1}`} - {issue.summary}
                  </h3>
                  <div className="flex space-x-2">
                    <span className={`px-2 py-1 text-xs font-bold ${issue.severity === 'high' ? 'bg-accentFail text-[#000]' : 'bg-border text-textMain'}`}>
                      SEV: {issue.severity?.toUpperCase()}
                    </span>
                    <span className="px-2 py-1 bg-border text-xs font-bold text-textMain">
                      CONF: {issue.confidence?.toUpperCase()}
                    </span>
                    {issue.duplicate_flag && (
                      <span className="px-2 py-1 bg-accentRev text-[#000] text-xs font-bold">
                        DUPE
                      </span>
                    )}
                  </div>
                </div>
                <p className="text-textMuted mt-2">{issue.description || issue.summary}</p>
                <div className="mt-4 border-t border-border pt-2 flex space-x-4">
                  <a href={`/?url=${encodeURIComponent(issue.url || '')}`} className="text-blue-400 hover:underline">Deep-dive &gt;</a>
                </div>
              </div>
            ))}
            {(!digestData.issues || digestData.issues.length === 0) && (
              <div className="text-textMuted">No issues found in this digest.</div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
