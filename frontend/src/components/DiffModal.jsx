import React, { useState } from 'react';
import { approvePatch, openPr } from '../api';

export default function DiffModal({ threadId, state, onClose }) {
  const [editedDiff, setEditedDiff] = useState(state.patch_diff || '');
  const [editing, setEditing] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleApprove = async (action) => {
    setLoading(true);
    try {
      await approvePatch({ thread_id: threadId, action, edited_diff: action === 'EDITED' ? editedDiff : null });
      onClose({ ...state, approval_status: action, patch_diff: action === 'EDITED' ? editedDiff : state.patch_diff });
    } catch (e) {
      alert('Error: ' + e.message);
    } finally {
      setLoading(false);
    }
  };

  const handleOpenPr = async () => {
    setLoading(true);
    try {
      const res = await openPr({ thread_id: threadId });
      if (res.data.error) alert('PR Error: ' + res.data.error);
      else alert('PR Opened: ' + res.data.url);
    } catch (e) {
      alert('Error: ' + e.message);
    } finally {
      setLoading(false);
    }
  };

  const ver = state.verification_result || {};
  const isPassed = ver.tests_passed;
  const isApproved = state.approval_status === 'APPROVED' || state.approval_status === 'EDITED';

  return (
    <div className="fixed inset-0 bg-black bg-opacity-80 flex items-center justify-center z-50 p-8 font-mono text-sm">
      <div className="bg-panel border border-border flex flex-col w-full max-w-6xl h-full shadow-2xl">
        <div className="flex justify-between items-center p-4 border-b border-border">
          <h2 className="font-bold text-lg">PATCH REVIEW</h2>
          <div className="flex space-x-4 text-xs">
            <span className={isPassed ? 'text-accentVer' : 'text-accentFail'}>
              VERIFICATION: {isPassed ? 'PASSED' : 'FAILED'}
            </span>
            <span className="text-textMuted">SECURITY: CLEAN</span>
            <span className="text-textMuted">TOKENS: {state.total_tokens || 0} (~$0.00)</span>
          </div>
          <button onClick={() => onClose()} className="text-textMuted hover:text-textMain">CLOSE</button>
        </div>
        
        <div className="flex-1 overflow-hidden flex flex-col p-4 bg-[#050505]">
          <div className="mb-2 flex justify-between">
            <span className="text-textMuted">UNIFIED DIFF</span>
            {!isApproved && (
              <button 
                onClick={() => setEditing(!editing)}
                className="text-blue-400 hover:underline"
              >
                {editing ? 'CANCEL EDIT' : 'EDIT DIFF'}
              </button>
            )}
          </div>
          {editing ? (
            <textarea 
              className="flex-1 bg-bg border border-border text-gray-300 p-2 font-mono whitespace-pre focus:outline-none resize-none"
              value={editedDiff}
              onChange={(e) => setEditedDiff(e.target.value)}
            />
          ) : (
            <div className="flex-1 bg-bg border border-border p-2 overflow-auto text-gray-300">
              {editedDiff.split('\n').map((line, i) => {
                let colorClass = '';
                if (line.startsWith('+')) colorClass = 'text-accentVer bg-accentVer bg-opacity-10';
                else if (line.startsWith('-')) colorClass = 'text-accentFail bg-accentFail bg-opacity-10';
                else if (line.startsWith('@@')) colorClass = 'text-blue-400';
                
                return <div key={i} className={`whitespace-pre ${colorClass}`}>{line || ' '}</div>;
              })}
            </div>
          )}
          {ver.output && (
            <div className="mt-4 max-h-32 overflow-y-auto bg-bg border border-border p-2 text-textMuted text-xs">
              <div className="font-bold mb-1">VERIFICATION LOGS:</div>
              <pre>{ver.output}</pre>
            </div>
          )}
        </div>

        <div className="p-4 border-t border-border flex justify-between items-center bg-bg">
          <div>
            {!isApproved && state.approval_status === 'AWAITING_APPROVAL' && (
              <div className="flex space-x-2">
                <button onClick={() => handleApprove('REJECTED')} disabled={loading} className="bg-accentFail text-[#000] font-bold px-4 py-2 rounded">
                  REJECT
                </button>
                {editing ? (
                  <button onClick={() => handleApprove('EDITED')} disabled={loading} className="bg-blue-600 text-[#000] font-bold px-4 py-2 rounded">
                    APPROVE EDITED
                  </button>
                ) : (
                  <button onClick={() => handleApprove('APPROVED')} disabled={loading} className="bg-accentVer text-[#000] font-bold px-4 py-2 rounded">
                    APPROVE
                  </button>
                )}
              </div>
            )}
            {isApproved && (
              <div className="text-accentVer font-bold">PATCH APPROVED</div>
            )}
          </div>
          <div>
            {isApproved && (
              <button onClick={handleOpenPr} disabled={loading} className="border border-border hover:bg-border px-4 py-2 rounded font-bold">
                OPEN DRAFT PR
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
