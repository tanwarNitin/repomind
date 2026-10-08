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

  const handleIngest = async (e) => {
    e.preventDefault();
    if (!ingestPath) return;
    setIngesting(true);
    try {
      await ingestRepo(ingestPath);
      await refreshRepos();
      setIngestPath('');
    } catch (err) {
      alert('Ingest failed: ' + err.message);
    } finally {
      setIngesting(false);
    }
  };

  return (
    <div className="flex items-center justify-between px-4 py-2 bg-panel border-b border-border text-sm">
      <div className="flex items-center space-x-6">
        <div className="font-bold text-textMain tracking-wide flex items-center space-x-2">
          <Database size={16} />
          <span>REPOMIND</span>
        </div>
        
        <div className="flex items-center space-x-2">
          <span className="text-textMuted">Repo:</span>
          <select 
            value={currentRepo || ''} 
            onChange={(e) => setCurrentRepo(e.target.value)}
            className="bg-bg border border-border text-textMain px-2 py-1 rounded focus:outline-none focus:border-textMuted"
          >
            <option value="">Select a repository...</option>
            {Array.isArray(repos) && repos.map(r => (
              <option key={r.repo_id} value={r.repo_id}>{r.repo_id}</option>
            ))}
          </select>
        </div>

        <form onSubmit={handleIngest} className="flex items-center space-x-2">
          <input 
            type="text" 
            placeholder="Local path or GitHub URL..." 
            value={ingestPath}
            onChange={(e) => setIngestPath(e.target.value)}
            className="bg-bg border border-border text-textMain px-2 py-1 rounded w-64 focus:outline-none focus:border-textMuted"
          />
          <button 
            type="submit" 
            disabled={ingesting || !ingestPath}
            className="bg-border hover:bg-textMuted text-textMain px-3 py-1 rounded disabled:opacity-50"
          >
            {ingesting ? 'Ingesting...' : 'Ingest'}
          </button>
        </form>
      </div>

      <nav className="flex items-center space-x-1">
        <NavLink to="/" className={({isActive}) => `px-3 py-1 rounded flex items-center space-x-1 ${isActive ? 'bg-border text-textMain' : 'text-textMuted hover:text-textMain'}`}>
          <GitFork size={14} /> <span>Triage</span>
        </NavLink>
        <NavLink to="/digest" className={({isActive}) => `px-3 py-1 rounded flex items-center space-x-1 ${isActive ? 'bg-border text-textMain' : 'text-textMuted hover:text-textMain'}`}>
          <LayoutDashboard size={14} /> <span>Digest</span>
        </NavLink>
        <NavLink to="/history" className={({isActive}) => `px-3 py-1 rounded flex items-center space-x-1 ${isActive ? 'bg-border text-textMain' : 'text-textMuted hover:text-textMain'}`}>
          <History size={14} /> <span>History</span>
        </NavLink>
        <NavLink to="/explain" className={({isActive}) => `px-3 py-1 rounded flex items-center space-x-1 ${isActive ? 'bg-border text-textMain' : 'text-textMuted hover:text-textMain'}`}>
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
      const reposArray = Array.isArray(res.data) ? res.data : [];
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
