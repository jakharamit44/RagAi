import React, { useState, useEffect, useRef } from 'react';
import { adminApi, getStoredToken } from '../../api/client';
import { Activity, Terminal, CheckCircle2, RefreshCw, Cpu, Layers } from 'lucide-react';

export default function PipelineTab() {
  const [pipelineState, setPipelineState] = useState({
    status: 'idle',
    active_file: null,
    items_per_second: 0,
    progress_percent: 0,
    files_processed: 0,
  });
  const [logs, setLogs] = useState([]);
  const eventSourceRef = useRef(null);

  useEffect(() => {
    // Connect to Server-Sent Events / streaming ingest endpoint
    const token = getStoredToken();
    const streamUrl = `/api/v1/admin/ingest/stream${token ? `?token=${encodeURIComponent(token)}` : ''}`;

    try {
      const es = new EventSource(streamUrl);
      eventSourceRef.current = es;

      es.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.status) setPipelineState((prev) => ({ ...prev, ...data }));
          if (data.log) {
            setLogs((prev) => [...prev.slice(-200), data.log]);
          }
        } catch {
          if (event.data) {
            setLogs((prev) => [...prev.slice(-200), event.data]);
          }
        }
      };

      es.onerror = () => {
        // Fallback or retry
      };
    } catch {
      // EventSource fallback
    }

    return () => {
      if (eventSourceRef.current) eventSourceRef.current.close();
    };
  }, []);

  return (
    <div className="space-y-6">
      {/* Telemetry HUD */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="p-5 bg-white border border-[#EAEAEA] rounded-2xl shadow-subtle">
          <div className="text-[11px] font-semibold text-muted uppercase">Ingestion Engine</div>
          <div className="text-xl font-bold text-charcoal mt-1 capitalize">
            {pipelineState.status}
          </div>
          <p className="text-[11px] text-muted mt-1">Real-time worker state</p>
        </div>

        <div className="p-5 bg-white border border-[#EAEAEA] rounded-2xl shadow-subtle">
          <div className="text-[11px] font-semibold text-muted uppercase">Throughput</div>
          <div className="text-xl font-bold text-indigo-600 mt-1 font-mono">
            {pipelineState.items_per_second || 0} items/s
          </div>
          <p className="text-[11px] text-muted mt-1">Chunk & embedding rate</p>
        </div>

        <div className="p-5 bg-white border border-[#EAEAEA] rounded-2xl shadow-subtle">
          <div className="text-[11px] font-semibold text-muted uppercase">Processed Files</div>
          <div className="text-xl font-bold text-emerald-600 mt-1 font-mono">
            {pipelineState.files_processed || 0} files
          </div>
          <p className="text-[11px] text-muted mt-1">Indexed this session</p>
        </div>

        <div className="p-5 bg-white border border-[#EAEAEA] rounded-2xl shadow-subtle">
          <div className="text-[11px] font-semibold text-muted uppercase">Active File</div>
          <div className="text-xs font-mono font-bold text-charcoal mt-1 truncate">
            {pipelineState.active_file || 'Idle (Waiting for events)'}
          </div>
          <p className="text-[11px] text-muted mt-1">Currently in processing</p>
        </div>
      </div>

      {/* Terminal Activity Logs */}
      <div className="bg-white border border-[#EAEAEA] rounded-2xl p-6 shadow-subtle space-y-3">
        <div className="flex items-center justify-between pb-3 border-b border-[#EAEAEA]">
          <div className="flex items-center gap-2">
            <Terminal className="w-4 h-4 text-charcoal" />
            <h3 className="text-sm font-bold text-charcoal">
              Live Ingestion Pipeline Event Stream
            </h3>
          </div>
          <button
            onClick={() => setLogs([])}
            className="px-2.5 py-1 text-xs border border-[#EAEAEA] rounded-lg text-muted hover:text-charcoal"
          >
            Clear Console
          </button>
        </div>

        <div className="p-4 bg-slate-900 text-slate-100 rounded-xl font-mono text-[11px] h-80 overflow-y-auto space-y-1">
          {logs.length === 0 ? (
            <div className="text-slate-500 italic">
              [SYSTEM] Pipeline event listener connected. Logs will stream here during directory scans or file ingestion...
            </div>
          ) : (
            logs.map((log, i) => (
              <div key={i} className="text-slate-300">
                {typeof log === 'string' ? log : JSON.stringify(log)}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
