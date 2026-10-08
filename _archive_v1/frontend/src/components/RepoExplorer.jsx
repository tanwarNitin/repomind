import React, { useState } from 'react';
import { Folder, FileCode, Code, Layers, ChevronRight, ChevronDown, RefreshCw, FolderSearch, Eye, X, Github } from 'lucide-react';

const DEMO_GITHUB_REPOS = [
  "https://github.com/pallets/flask",
  "https://github.com/psf/requests"
];

export default function RepoExplorer({ treeData, basePath, onIngest, isIngesting }) {
  const [expandedFiles, setExpandedFiles] = useState({});
  const [customPath, setCustomPath] = useState('');
  const [selectedSymbol, setSelectedSymbol] = useState(null);
  const [symbolCode, setSymbolCode] = useState(null);
  const [isLoadingCode, setIsLoadingCode] = useState(false);

  const toggleFile = (path) => {
    setExpandedFiles(prev => ({ ...prev, [path]: !prev[path] }));
  };

  const handleIngestClick = (e) => {
    if (e) e.preventDefault();
    onIngest(customPath);
  };

  const handleQuickGithub = (url) => {
    setCustomPath(url);
    onIngest(url);
  };

  const handleSymbolClick = async (file_path, sym) => {
    setSelectedSymbol({ ...sym, file_path });
    setIsLoadingCode(true);
    try {
      const res = await fetch(`/api/symbol_code?file_path=${encodeURIComponent(file_path)}&start_line=${sym.start_line}&end_line=${sym.end_line}`);
      if (res.ok) {
        const data = await res.json();
        setSymbolCode(data.code_snippet);
      } else {
        setSymbolCode("// Unable to fetch AST snippet content.");
      }
    } catch (err) {
      setSymbolCode("// Error reading symbol from backend.");
    } finally {
      setIsLoadingCode(false);
    }
  };

  const getSymbolBadge = (type) => {
    switch (type) {
      case 'class':
      case 'struct':
        return <span className="px-1.5 py-0.5 text-[10px] font-semibold bg-purple-500/20 text-purple-300 border border-purple-500/30 rounded">class</span>;
      case 'method':
        return <span className="px-1.5 py-0.5 text-[10px] font-semibold bg-blue-500/20 text-blue-300 border border-blue-500/30 rounded">method</span>;
      case 'function':
        return <span className="px-1.5 py-0.5 text-[10px] font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 rounded">func</span>;
      default:
        return <span className="px-1.5 py-0.5 text-[10px] font-semibold bg-zinc-500/20 text-zinc-300 border border-zinc-500/30 rounded">{type}</span>;
    }
  };

  return (
    <div className="glass-panel rounded-xl p-4 flex flex-col h-full border border-slate-800 shadow-xl relative">
      <div className="flex items-center justify-between pb-3 mb-3 border-b border-slate-800">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <Layers className="w-4 h-4" />
          </div>
          <div>
            <h2 className="text-sm font-bold text-slate-100 uppercase tracking-wider">AST Symbol Explorer</h2>
            <p className="text-xs text-slate-400">Tree-sitter AST Graph Parser</p>
          </div>
        </div>
      </div>

      {/* Directory & GitHub URL Input Form */}
      <form onSubmit={handleIngestClick} className="mb-3 space-y-2">
        <div className="flex gap-1.5">
          <div className="relative flex-1">
            <FolderSearch className="w-3.5 h-3.5 text-slate-500 absolute left-2.5 top-2.5" />
            <input
              type="text"
              value={customPath}
              onChange={(e) => setCustomPath(e.target.value)}
              placeholder="Local folder or GitHub URL (https://github.com/owner/repo)"
              className="w-full pl-8 pr-2 py-1.5 text-xs font-mono bg-slate-950/80 text-slate-200 border border-slate-800 rounded-lg focus:outline-none focus:border-emerald-500/50"
            />
          </div>
          <button
            type="submit"
            disabled={isIngesting}
            className="flex items-center gap-1 px-3 py-1.5 text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded-lg transition disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isIngesting ? 'animate-spin text-emerald-400' : ''}`} />
            {isIngesting ? 'Cloning...' : 'Ingest'}
          </button>
        </div>

        <div className="flex items-center gap-1.5 pt-0.5">
          <Github className="w-3 h-3 text-slate-400" />
          <span className="text-[10px] text-slate-400">Quick GitHub Repos:</span>
          {DEMO_GITHUB_REPOS.map((url, idx) => (
            <button
              key={idx}
              type="button"
              onClick={() => handleQuickGithub(url)}
              className="text-[10px] px-2 py-0.5 rounded bg-slate-900 hover:bg-slate-800 text-emerald-400 border border-slate-800 font-mono transition"
            >
              {url.split('/').slice(-1)[0]}
            </button>
          ))}
        </div>

        {basePath && (
          <p className="text-[10px] text-emerald-400 font-mono truncate pt-0.5">
            Active: <span className="text-slate-300">{basePath}</span>
          </p>
        )}
      </form>

      <div className="flex-1 overflow-y-auto pr-1 space-y-2">
        {(!treeData || treeData.length === 0) ? (
          <div className="text-center py-8 text-slate-500 text-xs">
            No AST symbols parsed yet. Enter a GitHub URL or local path.
          </div>
        ) : (
          treeData.map((fileObj) => {
            const isExpanded = expandedFiles[fileObj.file_path] !== false;
            return (
              <div key={fileObj.file_path} className="rounded-lg border border-slate-800/80 bg-slate-900/60 overflow-hidden">
                <button
                  onClick={() => toggleFile(fileObj.file_path)}
                  className="w-full flex items-center justify-between p-2.5 hover:bg-slate-800/50 text-left transition duration-150"
                >
                  <div className="flex items-center gap-2 min-w-0">
                    {isExpanded ? <ChevronDown className="w-3.5 h-3.5 text-slate-400 flex-shrink-0" /> : <ChevronRight className="w-3.5 h-3.5 text-slate-400 flex-shrink-0" />}
                    <FileCode className="w-4 h-4 text-emerald-400 flex-shrink-0" />
                    <span className="text-xs font-mono text-slate-200 truncate">{fileObj.file_path}</span>
                  </div>
                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-slate-800 text-slate-400 border border-slate-700/60 flex-shrink-0">
                    {fileObj.symbols_count} symbols
                  </span>
                </button>

                {isExpanded && (
                  <div className="px-3 pb-2 pt-1 border-t border-slate-800/40 bg-slate-950/40 space-y-1.5">
                    {fileObj.symbols.length === 0 ? (
                      <p className="text-[11px] text-slate-500 italic pl-5">No symbols detected.</p>
                    ) : (
                      fileObj.symbols.map((sym, idx) => (
                        <div
                          key={idx}
                          onClick={() => handleSymbolClick(fileObj.file_path, sym)}
                          className="flex items-center justify-between text-xs py-1 px-2 rounded hover:bg-slate-800/60 cursor-pointer transition"
                          title="Click to view Tree-sitter AST symbol code"
                        >
                          <div className="flex items-center gap-2 min-w-0">
                            <Code className="w-3.5 h-3.5 text-slate-500 flex-shrink-0" />
                            <span className="font-mono text-slate-300 font-medium truncate">{sym.name}</span>
                            {getSymbolBadge(sym.type)}
                          </div>
                          <span className="text-[10px] font-mono text-slate-500 flex items-center gap-1">
                            L{sym.start_line}-{sym.end_line}
                            <Eye className="w-3 h-3 text-slate-400 hover:text-emerald-400" />
                          </span>
                        </div>
                      ))
                    )}
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>

      {/* Code Snippet Viewer Modal */}
      {selectedSymbol && (
        <div className="absolute inset-0 z-30 bg-slate-950/95 backdrop-blur border border-slate-700 rounded-xl p-4 flex flex-col animate-in fade-in duration-150">
          <div className="flex items-center justify-between pb-2 mb-2 border-b border-slate-800">
            <div className="flex items-center gap-2">
              <Code className="w-4 h-4 text-emerald-400" />
              <span className="text-xs font-bold text-slate-200 font-mono">{selectedSymbol.name}</span>
              <span className="text-[10px] px-1.5 py-0.5 bg-slate-800 text-slate-400 rounded">
                Lines {selectedSymbol.start_line}-{selectedSymbol.end_line}
              </span>
            </div>
            <button onClick={() => setSelectedSymbol(null)} className="text-slate-400 hover:text-white">
              <X className="w-4 h-4" />
            </button>
          </div>
          <p className="text-[11px] font-mono text-slate-400 mb-2 truncate">{selectedSymbol.file_path}</p>
          <div className="flex-1 overflow-y-auto bg-slate-900/90 p-3 rounded-lg border border-slate-800">
            {isLoadingCode ? (
              <p className="text-xs text-slate-400 italic">Extracting AST symbol code...</p>
            ) : (
              <pre className="text-xs font-mono text-emerald-300 leading-relaxed whitespace-pre-wrap">{symbolCode}</pre>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
