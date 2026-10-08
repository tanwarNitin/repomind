import React from 'react';
import { Activity, ShieldCheck, Cpu, DollarSign, CheckCircle2, AlertCircle, Clock, Zap } from 'lucide-react';

export default function AgentLiveStream({ logs = [], isRunning, stateData }) {
  const redactedCount = logs.reduce((acc, log) => acc + (log.redacted_secrets_count || 0), 0);
  const totalTokens = stateData?.total_tokens || logs.reduce((acc, log) => acc + (log.tokens || 0), 0);
  const totalCost = stateData?.total_cost || 0.0;

  const getStepIcon = (step) => {
    switch (step) {
      case 'issue_parser':
        return <ShieldCheck className="w-4 h-4 text-emerald-400" />;
      case 'tree_search':
        return <Cpu className="w-4 h-4 text-purple-400" />;
      case 'patch_generator':
        return <Zap className="w-4 h-4 text-amber-400" />;
      case 'hitl_approval':
        return <CheckCircle2 className="w-4 h-4 text-blue-400" />;
      default:
        return <Activity className="w-4 h-4 text-slate-400" />;
    }
  };

  return (
    <div className="glass-panel rounded-xl p-4 border border-slate-800 shadow-xl flex flex-col h-full">
      <div className="flex items-center justify-between pb-3 mb-3 border-b border-slate-800">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-purple-500/10 text-purple-400 border border-purple-500/20">
            <Activity className="w-4 h-4" />
          </div>
          <div>
            <h2 className="text-sm font-bold text-slate-100 uppercase tracking-wider">Agent SSE Execution Stream</h2>
            <p className="text-xs text-slate-400">LiteLLM Free API Router & Thought Timeline</p>
          </div>
        </div>
        {isRunning && (
          <span className="flex items-center gap-1.5 text-xs px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 animate-pulse font-medium">
            <span className="w-2 h-2 rounded-full bg-emerald-400"></span>
            Streaming SSE
          </span>
        )}
      </div>

      {/* Metrics Header */}
      <div className="grid grid-cols-3 gap-2 mb-3">
        <div className="bg-slate-900/80 p-2.5 rounded-lg border border-slate-800 flex items-center justify-between">
          <div>
            <p className="text-[10px] text-slate-400 font-medium">Redacted Secrets</p>
            <p className="text-sm font-bold text-emerald-400 font-mono">{redactedCount}</p>
          </div>
          <ShieldCheck className="w-5 h-5 text-emerald-500/40" />
        </div>
        <div className="bg-slate-900/80 p-2.5 rounded-lg border border-slate-800 flex items-center justify-between">
          <div>
            <p className="text-[10px] text-slate-400 font-medium">Total Tokens</p>
            <p className="text-sm font-bold text-purple-300 font-mono">{totalTokens}</p>
          </div>
          <Cpu className="w-5 h-5 text-purple-500/40" />
        </div>
        <div className="bg-slate-900/80 p-2.5 rounded-lg border border-slate-800 flex items-center justify-between">
          <div>
            <p className="text-[10px] text-slate-400 font-medium">API Cost</p>
            <p className="text-sm font-bold text-emerald-400 font-mono">${totalCost.toFixed(4)} <span className="text-[9px] font-sans text-emerald-500">(Free)</span></p>
          </div>
          <DollarSign className="w-5 h-5 text-emerald-500/40" />
        </div>
      </div>

      {/* Timeline Stream */}
      <div className="flex-1 overflow-y-auto pr-1 space-y-2.5">
        {logs.length === 0 ? (
          <div className="text-center py-10 text-slate-500 text-xs flex flex-col items-center gap-2">
            <Clock className="w-6 h-6 text-slate-600" />
            Waiting for issue submission to stream agent thoughts...
          </div>
        ) : (
          logs.map((log, idx) => (
            <div key={idx} className="p-3 rounded-lg border border-slate-800 bg-slate-900/70 hover:bg-slate-900 transition">
              <div className="flex items-center justify-between mb-1.5">
                <div className="flex items-center gap-2">
                  {getStepIcon(log.step)}
                  <span className="text-xs font-bold text-slate-200 uppercase tracking-wide">
                    {log.step?.replace('_', ' ')}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  {log.router && (
                    <span className="text-[10px] px-2 py-0.5 rounded bg-purple-500/10 text-purple-300 border border-purple-500/20 font-mono">
                      {log.router}
                    </span>
                  )}
                  {log.model && (
                    <span className="text-[10px] px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700 font-mono">
                      {log.model}
                    </span>
                  )}
                </div>
              </div>
              <p className="text-xs text-slate-300 font-mono leading-relaxed">{log.message}</p>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
