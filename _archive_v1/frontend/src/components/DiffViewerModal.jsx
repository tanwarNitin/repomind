import React, { useState } from 'react';
import { GitPullRequest, Check, X, Edit3, ShieldAlert, FileText, CheckCircle2 } from 'lucide-react';

export default function DiffViewerModal({ patchText, onApprove, isOpen, onClose }) {
  const [isEditing, setIsEditing] = useState(false);
  const [editedPatch, setEditedPatch] = useState(patchText || '');

  if (!isOpen) return null;

  const handleApprove = () => {
    onApprove('APPROVED', isEditing ? editedPatch : patchText);
  };

  const handleEditSubmit = () => {
    onApprove('EDITED', editedPatch);
  };

  const handleReject = () => {
    onApprove('REJECTED', '');
  };

  const renderFormattedDiff = (diffStr) => {
    if (!diffStr) return <p className="text-slate-500 italic p-4 text-xs">No patch available.</p>;

    const lines = diffStr.split('\n');
    return lines.map((line, idx) => {
      let bgClass = 'text-slate-300';
      if (line.startsWith('+') && !line.startsWith('+++')) {
        bgClass = 'bg-emerald-950/40 text-emerald-300 font-medium';
      } else if (line.startsWith('-') && !line.startsWith('---')) {
        bgClass = 'bg-rose-950/40 text-rose-300 font-medium';
      } else if (line.startsWith('@@') || line.startsWith('---') || line.startsWith('+++')) {
        bgClass = 'text-purple-400 font-semibold bg-purple-950/20';
      }

      return (
        <div key={idx} className={`px-4 py-0.5 font-mono text-xs whitespace-pre ${bgClass}`}>
          {line}
        </div>
      );
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md animate-in fade-in duration-200">
      <div className="glass-panel w-full max-w-4xl max-h-[90vh] rounded-2xl border border-slate-700 shadow-2xl flex flex-col overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-slate-800 bg-slate-900/90">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
              <GitPullRequest className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-base font-bold text-slate-100">Human-In-The-Loop Maintainer Review</h2>
              <p className="text-xs text-slate-400">Review, edit, or approve the generated git patch</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content Body */}
        <div className="flex-1 overflow-y-auto bg-slate-950/90 p-4 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
              <FileText className="w-4 h-4 text-emerald-400" />
              Unified Git Diff Patch
            </span>
            <button
              onClick={() => setIsEditing(!isEditing)}
              className="text-xs px-3 py-1 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 flex items-center gap-1.5 transition"
            >
              <Edit3 className="w-3.5 h-3.5 text-purple-400" />
              {isEditing ? 'Cancel Editing' : 'Edit Patch'}
            </button>
          </div>

          {isEditing ? (
            <textarea
              value={editedPatch}
              onChange={(e) => setEditedPatch(e.target.value)}
              className="w-full h-80 p-4 text-xs font-mono bg-slate-900 text-emerald-300 border border-purple-500/40 rounded-xl focus:outline-none focus:ring-1 focus:ring-purple-500 resize-none"
            />
          ) : (
            <div className="border border-slate-800 rounded-xl overflow-hidden bg-slate-900/60 divide-y divide-slate-800/40 max-h-96 overflow-y-auto py-2">
              {renderFormattedDiff(patchText)}
            </div>
          )}
        </div>

        {/* Action Controls Footer */}
        <div className="p-4 border-t border-slate-800 bg-slate-900/90 flex items-center justify-between">
          <button
            onClick={handleReject}
            className="flex items-center gap-2 px-4 py-2 text-xs font-semibold bg-rose-950/60 hover:bg-rose-900/80 text-rose-300 border border-rose-800/60 rounded-xl transition shadow-lg"
          >
            <X className="w-4 h-4" />
            Reject Patch
          </button>

          <div className="flex items-center gap-3">
            {isEditing ? (
              <button
                onClick={handleEditSubmit}
                className="flex items-center gap-2 px-5 py-2 text-xs font-semibold bg-purple-600 hover:bg-purple-500 text-white rounded-xl transition shadow-lg shadow-purple-900/30"
              >
                <Check className="w-4 h-4" />
                Submit Edited Patch
              </button>
            ) : (
              <button
                onClick={handleApprove}
                className="flex items-center gap-2 px-5 py-2 text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl transition shadow-lg shadow-emerald-900/30"
              >
                <CheckCircle2 className="w-4 h-4" />
                Approve & Merge Patch
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
