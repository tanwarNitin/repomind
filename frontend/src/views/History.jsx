import React, { useEffect, useState } from 'react';
import { getHistory } from '../api';

export default function History() {
  const [runs, setRuns] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchHistory = async () => {
      try {
        const res = await getHistory();
        setRuns(res.data);
      } catch (e) {
        console.error(e);
      } finally {
        setLoading(false);
      }
    };
    fetchHistory();
  }, []);

  return (
    <div className="p-8 h-full overflow-y-auto bg-bg text-textMain font-mono text-sm">
      <div className="max-w-6xl mx-auto">
        <h1 className="text-xl font-bold tracking-wider mb-8 border-b border-border pb-4">RUN HISTORY</h1>
        
        {loading ? (
          <div className="text-textMuted italic">Loading...</div>
        ) : runs.length === 0 ? (
          <div className="text-textMuted italic">No previous runs.</div>
        ) : (
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="border-b border-border text-textMuted text-xs">
                <th className="py-2 px-4 font-normal">ID</th>
                <th className="py-2 px-4 font-normal">REPO</th>
                <th className="py-2 px-4 font-normal">STATUS</th>
                <th className="py-2 px-4 font-normal">PATCH VERDICT</th>
                <th className="py-2 px-4 font-normal">TOKENS</th>
              </tr>
            </thead>
            <tbody>
              {runs.map(run => (
                <tr key={run.id} className="border-b border-border hover:bg-[#121212] transition-colors">
                  <td className="py-3 px-4">{run.id}</td>
                  <td className="py-3 px-4 truncate max-w-[200px]">{run.repo_url}</td>
                  <td className="py-3 px-4">
                    <span className={`font-bold ${
                      run.status === 'APPROVED' ? 'text-accentVer' : 
                      run.status === 'AWAITING_APPROVAL' ? 'text-accentRev' : 
                      run.status === 'FAILED' ? 'text-accentFail' : 'text-textMain'
                    }`}>
                      {run.status}
                    </span>
                  </td>
                  <td className="py-3 px-4">{run.patch_verdict}</td>
                  <td className="py-3 px-4 text-textMuted">{run.tokens_used}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
