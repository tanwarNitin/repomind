import React, { useState, useEffect } from 'react';
import { Cpu, ShieldCheck, Zap, Terminal } from 'lucide-react';
import RepoExplorer from './components/RepoExplorer';
import IssueInput from './components/IssueInput';
import AgentLiveStream from './components/AgentLiveStream';
import DiffViewerModal from './components/DiffViewerModal';

export default function App() {
  const [astTree, setAstTree] = useState([]);
  const [basePath, setBasePath] = useState('');
  const [isIngesting, setIsIngesting] = useState(false);
  const [isRunning, setIsRunning] = useState(false);
  const [logs, setLogs] = useState([]);
  const [currentThreadId, setCurrentThreadId] = useState(null);
  const [patchText, setPatchText] = useState('');
  const [isDiffModalOpen, setIsDiffModalOpen] = useState(false);
  const [statusMessage, setStatusMessage] = useState('System Ready. Standby for issue triage.');
  const [stateData, setStateData] = useState(null);

  // Fetch AST symbol tree on mount
  useEffect(() => {
    fetchTree();
  }, []);

  const fetchTree = async () => {
    try {
      const res = await fetch('/api/tree');
      if (res.ok) {
        const data = await res.json();
        setAstTree(data.tree || []);
        setBasePath(data.base_path || '');
      }
    } catch (e) {
      console.warn("Backend API offline or unreachable:", e);
    }
  };

  const handleIngest = async (customPath) => {
    setIsIngesting(true);
    setStatusMessage("Parsing Tree-sitter C++ & Python AST graphs...");
    try {
      const res = await fetch('/api/ingest', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ dir_path: customPath || undefined })
      });
      if (res.ok) {
        const data = await res.json();
        setStatusMessage(data.message);
        setBasePath(data.base_path || '');
        await fetchTree();
      } else {
        const errData = await res.json();
        setStatusMessage(errData.detail || "Error ingesting directory.");
      }
    } catch (e) {
      setStatusMessage("Error connecting to backend server.");
    } finally {
      setIsIngesting(false);
    }
  };

  const handleTriageSubmit = async (rawIssue, groqKey, geminiKey) => {
    setIsRunning(true);
    setLogs([]);
    setPatchText('');
    setStatusMessage("Initiating LangGraph Multi-Agent Workflow...");

    try {
      const res = await fetch('/api/triage', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          raw_issue: rawIssue,
          groq_api_key: groqKey || undefined,
          gemini_api_key: geminiKey || undefined
        })
      });

      if (res.ok) {
        const data = await res.json();
        const threadId = data.thread_id;
        setCurrentThreadId(threadId);
        listenToStream(threadId);
      } else {
        setIsRunning(false);
        setStatusMessage("Failed to trigger triage workflow.");
      }
    } catch (e) {
      setIsRunning(false);
      setStatusMessage("Network error triggering workflow.");
    }
  };

  const listenToStream = (threadId) => {
    const eventSource = new EventSource(`/api/stream/${threadId}`);

    eventSource.addEventListener('agent_step', (e) => {
      try {
        const parsed = JSON.parse(e.data);
        const nodeState = parsed.updated_state || {};
        if (nodeState.execution_logs) {
          setLogs(nodeState.execution_logs);
        }
        if (nodeState.suggested_patch) {
          setPatchText(nodeState.suggested_patch);
        }
        if (nodeState.total_tokens || nodeState.total_cost !== undefined) {
          setStateData(prev => ({ ...prev, ...nodeState }));
        }
      } catch (err) {
        console.error("Error parsing SSE agent_step:", err);
      }
    });

    eventSource.addEventListener('interrupt', (e) => {
      try {
        const parsed = JSON.parse(e.data);
        if (parsed.patch) {
          setPatchText(parsed.patch);
        }
        setIsDiffModalOpen(true);
        setIsRunning(false);
        setStatusMessage("HITL Interrupt: Awaiting maintainer patch approval.");
        eventSource.close();
      } catch (err) {
        console.error("Error handling interrupt SSE:", err);
      }
    });

    eventSource.addEventListener('completion', (e) => {
      setIsRunning(false);
      setStatusMessage("Agent workflow completed.");
      eventSource.close();
    });

    eventSource.onerror = () => {
      eventSource.close();
      setIsRunning(false);
    };
  };

  const handleApproveAction = async (action, customPatch) => {
    setIsDiffModalOpen(false);
    setStatusMessage(`Applying HITL action: ${action}...`);

    try {
      const res = await fetch('/api/approve', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          thread_id: currentThreadId,
          action: action,
          patch: customPatch
        })
      });

      if (res.ok) {
        const data = await res.json();
        const diskMsg = data.disk_status ? ` (${data.disk_status})` : '';
        setStatusMessage(`Workflow completed: ${action}.${diskMsg}`);
        setLogs(prev => [
          ...prev,
          {
            step: 'hitl_approval',
            timestamp: new Date().toLocaleTimeString(),
            action: action,
            message: `Maintainer action '${action}' processed. ${diskMsg}`
          }
        ]);
      }
    } catch (e) {
      setStatusMessage("Error submitting approval action.");
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-slate-950 text-slate-100">
      {/* Top Header */}
      <header className="border-b border-slate-800 bg-slate-900/80 backdrop-blur-md sticky top-0 z-40 px-6 py-3">
        <div className="max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-gradient-to-tr from-emerald-500 to-teal-400 text-slate-950 shadow-lg shadow-emerald-500/20">
              <Cpu className="w-5 h-5 font-bold" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-base font-extrabold tracking-tight text-white">RepoMind</h1>
                <span className="text-[10px] font-semibold px-2 py-0.5 rounded-md bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                  Zero-Cost Free API Edition
                </span>
              </div>
              <p className="text-xs text-slate-400">Tree-sitter AST • Guardrails PII • LiteLLM Router • LangGraph HITL</p>
            </div>
          </div>

          <div className="flex items-center gap-4 text-xs font-mono">
            <div className="flex items-center gap-1.5 text-slate-300 bg-slate-800/80 px-3 py-1.5 rounded-lg border border-slate-700">
              <Zap className="w-3.5 h-3.5 text-emerald-400" />
              <span>Router: <strong className="text-emerald-400">Groq & Gemini Free</strong></span>
            </div>
            <div className="flex items-center gap-1.5 text-slate-300 bg-slate-800/80 px-3 py-1.5 rounded-lg border border-slate-700">
              <ShieldCheck className="w-3.5 h-3.5 text-purple-400" />
              <span>Guardrails: <strong className="text-purple-300">Active</strong></span>
            </div>
          </div>
        </div>
      </header>

      {/* Main Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-6 grid grid-cols-12 gap-6">
        {/* Left Column: AST Symbol Explorer */}
        <div className="col-span-12 lg:col-span-4 h-[calc(100vh-140px)]">
          <RepoExplorer treeData={astTree} basePath={basePath} onIngest={handleIngest} isIngesting={isIngesting} />
        </div>

        {/* Center Column: Issue Input & Controls */}
        <div className="col-span-12 lg:col-span-4 h-[calc(100vh-140px)]">
          <IssueInput onSubmit={handleTriageSubmit} isRunning={isRunning} />
        </div>

        {/* Right Column: Live Stream & Metrics */}
        <div className="col-span-12 lg:col-span-4 h-[calc(100vh-140px)]">
          <AgentLiveStream logs={logs} isRunning={isRunning} stateData={stateData} />
        </div>
      </main>

      {/* Footer Status Bar */}
      <footer className="border-t border-slate-800 bg-slate-900/90 px-6 py-2.5 text-xs text-slate-400 flex items-center justify-between">
        <div className="flex items-center gap-2 font-mono">
          <Terminal className="w-3.5 h-3.5 text-emerald-400" />
          <span>Status: <strong className="text-slate-200">{statusMessage}</strong></span>
        </div>
        <div className="flex items-center gap-4 text-[11px]">
          <span>FastAPI :8000</span>
          <span>•</span>
          <span>Vite React :5173</span>
          <span>•</span>
          <span>Playwright MCP Verified</span>
        </div>
      </footer>

      {/* HITL Patch Diff Viewer Modal */}
      <DiffViewerModal
        isOpen={isDiffModalOpen}
        patchText={patchText}
        onApprove={handleApproveAction}
        onClose={() => setIsDiffModalOpen(false)}
      />
    </div>
  );
}
