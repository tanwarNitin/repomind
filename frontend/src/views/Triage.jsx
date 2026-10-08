import React, { useState, useEffect, useRef } from 'react';
import { submitTriage, streamUrl, getState, followupTriage } from '../api';
import TerminalLog from '../components/TerminalLog';
import DiffModal from '../components/DiffModal';

export default function Triage({ currentRepo }) {
  const [issueText, setIssueText] = useState('');
  const [issueUrl, setIssueUrl] = useState('');
  const [threadId, setThreadId] = useState(null);
  const [logs, setLogs] = useState([]);
  const [evidence, setEvidence] = useState([]);
  const [status, setStatus] = useState('IDLE');
  const [followupMsg, setFollowupMsg] = useState('');
  const [finalState, setFinalState] = useState(null);
  const [showModal, setShowModal] = useState(false);

  useEffect(() => {
    if (!threadId) return;
    const source = new EventSource(streamUrl(threadId));
    
    source.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.log) {
        setLogs(prev => [...prev, data.log]);
        if (data.log.evidence && Array.isArray(data.log.evidence)) {
          setEvidence(prev => {
            const newEv = [...prev];
            data.log.evidence.forEach(e => {
              if (!newEv.some(ex => ex.file === e.file && ex.line === e.line)) {
                newEv.push(e);
              }
            });
            return newEv;
          });
        }
      } else if (data.status === 'done') {
        source.close();
        checkFinalState();
      }
    };
    source.onerror = () => {
      source.close();
      checkFinalState();
    };
    return () => source.close();
  }, [threadId]);

  const checkFinalState = async () => {
    try {
      const res = await getState(threadId);
      if (res.data && res.data.approval_status) {
        setFinalState(res.data);
        setStatus(res.data.approval_status);
        if (res.data.approval_status === 'AWAITING_APPROVAL') {
          setShowModal(true);
        }
      } else {
        setStatus('FAILED');
      }
    } catch (err) {
      setStatus('FAILED');
    }
  };

  const handleStart = async () => {
    if (!currentRepo) return alert('Select a repo');
    if (!issueText && !issueUrl) return alert('Enter issue text or URL');
    setLogs([]);
    setEvidence([]);
    setFinalState(null);
    setStatus('STARTING');
    try {
      const res = await submitTriage({ repo_id: currentRepo, issue_text: issueText, issue_url: issueUrl });
      setThreadId(res.data.thread_id);
      setStatus('RUNNING');
    } catch (err) {
      alert('Error: ' + err.message);
      setStatus('FAILED');
    }
  };

  const handleFollowup = async () => {
    if (!followupMsg || !threadId) return;
    setStatus('RUNNING');
    try {
      await followupTriage({ thread_id: threadId, message: followupMsg });
      setFollowupMsg('');
    } catch (err) {
      alert('Followup failed: ' + err.message);
    }
  };

  return (
    <div className="flex h-full bg-bg text-textMain font-mono text-sm">
      {/* LEFT PANEL */}
      <div className="w-1/4 min-w-[300px] border-r border-border bg-panel p-4 flex flex-col">
        <h2 className="font-bold mb-4">TRIAGE CONFIG</h2>
        <div className="mb-4">
          <label className="block text-textMuted mb-1">Target Repo</label>
          <div className="bg-bg border border-border p-2 rounded truncate">{currentRepo || 'None selected'}</div>
        </div>
        <div className="mb-4">
          <label className="block text-textMuted mb-1">Issue URL</label>
          <input 
            type="text" 
            className="w-full bg-bg border border-border rounded p-2 focus:outline-none focus:border-textMuted" 
            value={issueUrl}
            onChange={(e) => setIssueUrl(e.target.value)}
            placeholder="https://github.com/..."
          />
        </div>
        <div className="flex-1 flex flex-col mb-4">
          <label className="block text-textMuted mb-1">Issue Description</label>
          <textarea 
            className="w-full flex-1 bg-bg border border-border rounded p-2 focus:outline-none focus:border-textMuted resize-none"
            value={issueText}
            onChange={(e) => setIssueText(e.target.value)}
            placeholder="Describe the issue..."
          ></textarea>
        </div>
        <button 
          onClick={handleStart}
          disabled={status === 'RUNNING' || status === 'STARTING'}
          className="bg-accentVer hover:bg-opacity-80 text-white font-bold py-2 rounded disabled:opacity-50"
        >
          {status === 'RUNNING' ? 'RUNNING...' : 'START RUN'}
        </button>
      </div>

      {/* CENTER PANEL */}
      <div className="flex-1 border-r border-border flex flex-col p-4 bg-bg">
        <div className="flex justify-between items-center mb-4">
          <h2 className="font-bold">BUILD LOG</h2>
          <div className="text-xs">
            STATUS: <span className={
              status === 'AWAITING_APPROVAL' ? 'text-accentRev' : 
              status === 'APPROVED' ? 'text-accentVer' : 
              status === 'FAILED' ? 'text-accentFail' : 'text-textMuted'
            }>{status}</span>
          </div>
        </div>
        <div className="flex-1 bg-[#0A0A0A] border border-border rounded p-2 overflow-y-auto">
          <TerminalLog logs={logs} />
        </div>
        
        {/* FOLLOWUP INPUT */}
        {(status === 'AWAITING_APPROVAL' || status === 'FAILED' || status === 'REJECTED') && threadId && (
          <div className="mt-4 flex space-x-2">
            <input 
              type="text" 
              className="flex-1 bg-panel border border-border rounded p-2 focus:outline-none focus:border-textMuted" 
              placeholder="Provide follow-up instructions..."
              value={followupMsg}
              onChange={(e) => setFollowupMsg(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleFollowup()}
            />
            <button onClick={handleFollowup} className="bg-border hover:bg-textMuted px-4 py-2 rounded">SEND</button>
            {status === 'AWAITING_APPROVAL' && (
              <button onClick={() => setShowModal(true)} className="bg-accentRev hover:bg-opacity-80 text-[#000] px-4 py-2 rounded font-bold">
                VIEW PATCH
              </button>
            )}
          </div>
        )}
      </div>

      {/* RIGHT PANEL */}
      <div className="w-1/4 min-w-[250px] bg-panel p-4 flex flex-col">
        <h2 className="font-bold mb-4">EVIDENCE PANEL</h2>
        <div className="flex-1 overflow-y-auto">
          {(!Array.isArray(evidence) || evidence.length === 0) ? (
            <div className="text-textMuted text-xs">No citations yet.</div>
          ) : (
            <ul className="space-y-2">
              {evidence.map((ev, i) => (
                <li key={i} className="bg-bg border border-border p-2 rounded text-xs">
                  <div className="font-bold text-textMain break-all">{ev.file}</div>
                  <div className="text-textMuted">Line {ev.line}</div>
                  {ev.snippet && <div className="mt-1 text-gray-500 whitespace-pre-wrap">{ev.snippet}</div>}
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      {showModal && finalState && (
        <DiffModal 
          threadId={threadId} 
          state={finalState} 
          onClose={(newState) => {
            setShowModal(false);
            if (newState) {
              setFinalState(newState);
              setStatus(newState.approval_status);
            }
          }} 
        />
      )}
    </div>
  );
}
