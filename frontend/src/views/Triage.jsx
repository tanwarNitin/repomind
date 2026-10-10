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
      if (res && res.approval_status) {
        setFinalState(res);
        setStatus(res.approval_status);
        if (res.approval_status === 'AWAITING_APPROVAL') {
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
      setThreadId(res.thread_id);
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
      <div className="w-1/4 min-w-[300px] border-r border-border bg-panel p-6 flex flex-col">
        <h2 className="font-bold mb-6 tracking-wider">TRIAGE CONFIG</h2>
        <div className="mb-6">
          <label className="block text-xs font-normal text-textMuted opacity-80 mb-2 uppercase tracking-wider">Issue URL</label>
          <input 
            type="text" 
            className="w-full bg-[#0A0A0A] border border-border rounded p-2.5 focus:outline-none focus:border-textMuted transition-colors" 
            value={issueUrl}
            onChange={(e) => setIssueUrl(e.target.value)}
            placeholder="https://github.com/..."
          />
        </div>
        <div className="flex-1 flex flex-col mb-6">
          <label className="block text-xs font-normal text-textMuted opacity-80 mb-2 uppercase tracking-wider">Issue Description</label>
          <textarea 
            className="w-full flex-1 bg-[#0A0A0A] border border-border rounded p-2.5 focus:outline-none focus:border-textMuted resize-none transition-colors"
            value={issueText}
            onChange={(e) => setIssueText(e.target.value)}
            placeholder="Describe the issue..."
          ></textarea>
        </div>
        <button 
          onClick={handleStart}
          disabled={status === 'RUNNING' || status === 'STARTING'}
          className="bg-accentVer hover:bg-opacity-80 text-[#fff] font-bold py-3 rounded disabled:opacity-50 transition-colors tracking-widest"
        >
          {status === 'RUNNING' ? 'RUNNING...' : 'START RUN'}
        </button>
      </div>

      {/* CENTER PANEL */}
      <div className="flex-1 border-r border-border flex flex-col p-6 bg-bg">
        <div className="flex justify-between items-center mb-6">
          <h2 className="font-bold tracking-wider">BUILD LOG</h2>
          <div className="text-xs font-bold tracking-wider">
            STATUS: <span className={
              status === 'AWAITING_APPROVAL' ? 'text-accentRev' : 
              status === 'APPROVED' ? 'text-accentVer' : 
              status === 'FAILED' ? 'text-accentFail' : 'text-textMuted'
            }>{status}</span>
          </div>
        </div>
        <div className="flex-1 bg-[#050505] border border-border rounded p-4 overflow-y-auto shadow-inner">
          <TerminalLog logs={logs} />
        </div>
        
        {/* FOLLOWUP INPUT */}
        {(status === 'AWAITING_APPROVAL' || status === 'FAILED' || status === 'REJECTED') && threadId && (
          <div className="mt-6 flex space-x-3">
            <input 
              type="text" 
              className="flex-1 bg-[#0A0A0A] border border-border rounded p-3 focus:outline-none focus:border-textMuted transition-colors" 
              placeholder="Provide follow-up instructions..."
              value={followupMsg}
              onChange={(e) => setFollowupMsg(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleFollowup()}
            />
            <button onClick={handleFollowup} className="bg-border hover:bg-textMuted px-6 py-3 rounded font-bold transition-colors">SEND</button>
            {status === 'AWAITING_APPROVAL' && (
              <button onClick={() => setShowModal(true)} className="bg-accentRev hover:bg-opacity-80 text-[#000] px-6 py-3 rounded font-bold transition-colors">
                VIEW PATCH
              </button>
            )}
          </div>
        )}
      </div>

      {/* RIGHT PANEL */}
      <div className="w-1/4 min-w-[300px] bg-panel p-6 flex flex-col">
        <h2 className="font-bold mb-6 tracking-wider">EVIDENCE PANEL</h2>
        <div className="flex-1 overflow-y-auto">
          {(!Array.isArray(evidence) || evidence.length === 0) ? (
            <div className="flex flex-col items-center justify-center h-full text-textMuted opacity-50 space-y-2">
              <span className="text-2xl font-bold">∅</span>
              <span className="text-xs tracking-wider">NO CITATIONS YET</span>
            </div>
          ) : (
            <ul className="space-y-3">
              {evidence.map((ev, i) => (
                <li key={i} className="bg-[#0A0A0A] border border-border p-3 rounded text-xs shadow-sm">
                  <div className="font-bold text-textMain break-all mb-1">{ev.file}</div>
                  <div className="text-textMuted mb-2">Line {ev.line}</div>
                  {ev.snippet && <div className="p-2 bg-[#050505] border border-[#222] text-gray-400 whitespace-pre-wrap rounded">{ev.snippet}</div>}
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
