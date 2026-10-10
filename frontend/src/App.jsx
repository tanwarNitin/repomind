import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, NavLink, useNavigate, useLocation } from 'react-router-dom';
import { getRepos, ingestRepo } from './api';
import TriageView from './views/Triage';
import DigestView from './views/Digest';
import HistoryView from './views/History';
import ExplainView from './views/Explain';
import { Database, GitFork, LayoutDashboard, History, Settings } from 'lucide-react';

function TopBar({ repos, currentRepo, setCurrentRepo, refreshRepos }) {
  const [ingestPath, setIngestPath] = useState('');
  const [ingesting, setIngesting] = useState(false);
  const [statusMsg, setStatusMsg] = useState({ text: '', type: '' });

  const handleIngest = async (e) => {
    e.preventDefault();
    if (!ingestPath) return;
    setIngesting(true);
    setStatusMsg({ text: '', type: '' });
    try {
      const res = await ingestRepo(ingestPath);
      await refreshRepos();
      if (res && res.repo_id) {
        setCurrentRepo(res.repo_id);
      }
      setIngestPath('');
      setStatusMsg({ text: 'Success!', type: 'success' });
      setTimeout(() => setStatusMsg({ text: '', type: '' }), 3000);
    } catch (err) {
      setStatusMsg({ text: 'Error: ' + err.message, type: 'error' });
    } finally {
      setIngesting(false);
    }
  };

  return (
    <div className="flex items-center justify-between px-6 py-3 bg-panel border-b border-border text-sm">
      <div className="flex items-center space-x-8">
        <div className="font-bold text-textMain tracking-widest flex items-center space-x-2">
          <Database size={16} />
          <span>REPOMIND</span>
        </div>
        
        <div className="flex items-center space-x-2">
          <span className="text-textMuted uppercase text-xs tracking-wider">Repo:</span>
          <select 
            value={currentRepo || ''} 
            onChange={(e) => setCurrentRepo(e.target.value)}
            className="bg-[#0A0A0A] border border-border text-textMain px-3 py-1 rounded focus:outline-none focus:border-textMuted transition-colors"
          >
            <option value="">Select a repository...</option>
            {Array.isArray(repos) && repos.map(r => (
              <option key={r.repo_id} value={r.repo_id}>{r.repo_id}</option>
            ))}
          </select>
        </div>

        <form onSubmit={handleIngest} className="flex items-center space-x-2 relative">
          <input 
            type="text" 
            placeholder="Local path or GitHub URL..." 
            value={ingestPath}
            onChange={(e) => setIngestPath(e.target.value)}
            className="bg-[#0A0A0A] border border-border text-textMain px-3 py-1 rounded w-72 focus:outline-none focus:border-textMuted transition-colors"
          />
          <button 
            type="submit" 
            disabled={ingesting || !ingestPath}
            className="bg-border hover:bg-textMuted text-textMain px-4 py-1 rounded disabled:opacity-50 transition-colors flex items-center space-x-2"
          >
            {ingesting ? (
              <>
                <svg className="animate-spin h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                <span>INGESTING...</span>
              </>
            ) : 'INGEST'}
          </button>
          {statusMsg.text && (
            <div className={`absolute -right-4 translate-x-full text-xs font-bold whitespace-nowrap ${statusMsg.type === 'error' ? 'text-accentFail' : 'text-accentVer'}`}>
              {statusMsg.text}
            </div>
          )}
        </form>
      </div>

      <nav className="flex items-center space-x-2">
        <NavLink to="/" className={({isActive}) => `px-4 py-1 rounded flex items-center space-x-2 transition-colors ${isActive ? 'bg-border text-textMain font-bold' : 'text-textMuted hover:text-textMain'}`}>
          <GitFork size={14} /> <span>Triage</span>
        </NavLink>
        <NavLink to="/digest" className={({isActive}) => `px-4 py-1 rounded flex items-center space-x-2 transition-colors ${isActive ? 'bg-border text-textMain font-bold' : 'text-textMuted hover:text-textMain'}`}>
          <LayoutDashboard size={14} /> <span>Digest</span>
        </NavLink>
        <NavLink to="/history" className={({isActive}) => `px-4 py-1 rounded flex items-center space-x-2 transition-colors ${isActive ? 'bg-border text-textMain font-bold' : 'text-textMuted hover:text-textMain'}`}>
          <History size={14} /> <span>History</span>
        </NavLink>
        <NavLink to="/explain" className={({isActive}) => `px-4 py-1 rounded flex items-center space-x-2 transition-colors ${isActive ? 'bg-border text-textMain font-bold' : 'text-textMuted hover:text-textMain'}`}>
          <Settings size={14} /> <span>Explain</span>
        </NavLink>
      </nav>
    </div>
  );
}

export default function App() {
  const [repos, setRepos] = useState([]);
  const [currentRepo, setCurrentRepo] = useState(null);

  const refreshRepos = async () => {
    try {
      const res = await getRepos();
      const reposArray = Array.isArray(res) ? res : [];
      setRepos(reposArray);
      if (reposArray.length > 0 && !currentRepo) {
        setCurrentRepo(reposArray[0].repo_id);
      }
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    refreshRepos();
  }, []);

  return (
    <BrowserRouter>
      <TopBar repos={repos} currentRepo={currentRepo} setCurrentRepo={setCurrentRepo} refreshRepos={refreshRepos} />
      <div className="flex-1 overflow-hidden">
        <Routes>
          <Route path="/" element={<TriageView currentRepo={currentRepo} />} />
          <Route path="/digest" element={<DigestView currentRepo={currentRepo} />} />
          <Route path="/history" element={<HistoryView />} />
          <Route path="/explain" element={<ExplainView currentRepo={currentRepo} />} />
        </Routes>
      </div>
    </BrowserRouter>
  );
}
