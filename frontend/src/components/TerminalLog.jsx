import React, { useEffect, useRef } from 'react';
import { format } from 'date-fns';

export default function TerminalLog({ logs }) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  return (
    <div className="font-mono text-xs text-gray-300 space-y-1 pb-4">
      {Array.isArray(logs) && logs.map((log, idx) => {
        const time = log.timestamp ? format(new Date(log.timestamp), 'HH:mm:ss.SSS') : '00:00:00.000';
        
        let content = null;
        if (log.type === 'node_start') {
          content = <span className="text-accentRev font-bold">[NODE START] {log.node}</span>;
        } else if (log.type === 'tool_call') {
          content = (
            <div className="pl-4 border-l border-textMuted my-1">
              <span className="text-blue-400 font-bold">$ {log.tool}</span>
              <div className="text-gray-500 whitespace-pre-wrap">{JSON.stringify(log.args, null, 2)}</div>
            </div>
          );
        } else if (log.type === 'tool_result') {
          content = (
            <div className="pl-4 border-l border-accentVer my-1 text-gray-400 whitespace-pre-wrap">
              {log.result}
            </div>
          );
        } else if (log.type === 'message') {
          content = <span className="text-textMain">{log.content}</span>;
        } else if (log.type === 'error') {
          content = <span className="text-accentFail font-bold">[ERROR] {log.error}</span>;
        } else {
          content = <span>{JSON.stringify(log)}</span>;
        }

        return (
          <div key={idx} className="flex space-x-2">
            <span className="text-textMuted shrink-0">[{time}]</span>
            <div className="flex-1 overflow-hidden">{content}</div>
          </div>
        );
      })}
      {logs.length === 0 && <div className="text-textMuted italic">Waiting for execution to start...</div>}
      <div ref={bottomRef} />
    </div>
  );
}
