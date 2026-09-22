import React, { useState, useEffect, useRef } from 'react';
import { adminApi, getStoredToken } from '../../api/client';
import {
  Activity,
  Terminal,
  CheckCircle2,
  RefreshCw,
  Cpu,
  Layers,
  Play,
  Square,
  FileText,
  Sparkles,
  ShieldCheck,
  Database,
  ArrowRight,
  AlertTriangle,
  FolderOpen
} from 'lucide-react';

const PIPELINE_STAGES = [
  { id: 'checksum', name: '1. Checksum & Deduplication', icon: ShieldCheck, desc: 'SHA-256 delta detection' },
  { id: 'tagging', name: '2. Path & Metadata Tagging', icon: FolderOpen, desc: 'Academic taxonomy hierarchy' },
  { id: 'extract_ocr', name: '3. Text Extraction & OCR', icon: FileText, desc: 'PyMuPDF, pdfplumber & OCR' },
  { id: 'chunk', name: '4. Semantic Chunking', icon: Layers, desc: 'Recursive header-aware chunker' },
  { id: 'embed', name: '5. Dense Vector Embedding', icon: Cpu, desc: 'MiniLM / BGE 384-d encoding' },
  { id: 'store', name: '6. Dual Storage Indexing', icon: Database, desc: 'Qdrant vectors & SQLite corpus' },
];

export default function PipelineTab() {
  // Ingestion Trigger Form
  const [folderPath, setFolderPath] = useState('data/sample_courses');
  const [department, setDepartment] = useState('Computer Science');
  const [course, setCourse] = useState('');
  const [semester, setSemester] = useState('1');
  const [forceReprocess, setForceReprocess] = useState(false);

  // Execution & Telemetry State
  const [isIngesting, setIsIngesting] = useState(false);
  const [currentStage, setCurrentStage] = useState(null);
  const [activeFile, setActiveFile] = useState(null);
  const [stageMessage, setStageMessage] = useState('');
  const [progressPercent, setProgressPercent] = useState(0);
  const [filesProcessed, setFilesProcessed] = useState(0);
  const [totalFiles, setTotalFiles] = useState(0);
  const [itemsPerSecond, setItemsPerSecond] = useState(0);

  // Terminal Logs
  const [logs, setLogs] = useState([]);
  const abortControllerRef = useRef(null);
  const terminalEndRef = useRef(null);
  const eventSourceRef = useRef(null);

  const addLog = (text, type = 'info') => {
    const timestamp = new Date().toLocaleTimeString();
    setLogs((prev) => [...prev.slice(-300), { timestamp, text, type }]);
  };

  // Auto-scroll terminal
  useEffect(() => {
    if (terminalEndRef.current) {
      terminalEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs]);

  // Passive background monitoring for folder watcher / background jobs
  useEffect(() => {
    const token = getStoredToken();
    const streamUrl = `/api/v1/admin/ingest/stream${token ? `?token=${encodeURIComponent(token)}` : ''}`;

    try {
      const es = new EventSource(streamUrl);
      eventSourceRef.current = es;

      es.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'heartbeat' && !isIngesting) {
            // Heartbeat received
          } else if (data.log) {
            addLog(data.log, 'info');
          }
        } catch {
          if (event.data && !isIngesting) {
            addLog(event.data, 'info');
          }
        }
      };

      es.onerror = () => {
        // Silent recovery
      };
    } catch {
      // EventSource fallback
    }

    return () => {
      if (eventSourceRef.current) eventSourceRef.current.close();
    };
  }, [isIngesting]);

  // Trigger manual streaming ingestion via POST
  const handleStartIngest = async (e) => {
    e.preventDefault();
    if (!folderPath.trim()) {
      alert('Please specify a folder path to ingest.');
      return;
    }

    setIsIngesting(true);
    setCurrentStage('checksum');
    setActiveFile('Initializing ingestion job...');
    setStageMessage('Scanning directory and discovering documents...');
    setProgressPercent(0);
    setFilesProcessed(0);
    setTotalFiles(0);
    setItemsPerSecond(0);

    addLog(`[JOB_START] Initiating streaming ingestion on: ${folderPath.trim()}`, 'job');

    const controller = new AbortController();
    abortControllerRef.current = controller;

    const token = getStoredToken();
    const startTime = Date.now();

    try {
      const response = await fetch('/api/v1/admin/ingest/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          folder_path: folderPath.trim(),
          department: department.trim() || undefined,
          course: course.trim() || undefined,
          semester: semester.trim() || undefined,
          force_reprocess: forceReprocess,
        }),
        signal: controller.signal,
      });

      if (!response.ok) {
        throw new Error(`HTTP Error ${response.status}: ${response.statusText}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop(); // Keep partial line in buffer

        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed || !trimmed.startsWith('data:')) continue;

          const jsonStr = trimmed.replace(/^data:\s*/, '');
          try {
            const event = JSON.parse(jsonStr);
            handleStreamEvent(event, startTime);
          } catch {
            // Non-JSON line
            if (jsonStr) addLog(jsonStr, 'info');
          }
        }
      }

      addLog('[JOB_COMPLETE] Streaming ingestion completed successfully.', 'success');
    } catch (err) {
      if (err.name === 'AbortError') {
        addLog('[ABORT] Ingestion stream canceled by operator.', 'warn');
      } else {
        addLog(`[ERROR] Ingestion error: ${err.message}`, 'error');
      }
    } finally {
      setIsIngesting(false);
      setCurrentStage(null);
      setActiveFile(null);
      setStageMessage('');
      abortControllerRef.current = null;
    }
  };

  const handleStreamEvent = (event, startTime) => {
    switch (event.type) {
      case 'job_start':
        setTotalFiles(event.total || 0);
        addLog(`[JOB] Target documents discovered: ${event.total || 0} files.`, 'job');
        break;

      case 'file_start':
        setActiveFile(event.name || event.file);
        setStageMessage(`Processing file (${(event.index ?? 0) + 1}/${totalFiles || '?'}): ${event.name}`);
        setCurrentStage('checksum');
        addLog(`[FILE] >>> Ingesting: ${event.name} (${Math.round((event.size || 0) / 1024)} KB)`, 'info');
        break;

      case 'stage':
        setCurrentStage(event.stage || 'checksum');
        setStageMessage(event.message || `Executing ${event.stage}...`);
        addLog(`  [STAGE] ${event.stage.toUpperCase()}: ${event.message}`, 'stage');
        break;

      case 'file_skipped':
        setFilesProcessed((prev) => {
          const next = prev + 1;
          if (totalFiles > 0) setProgressPercent(Math.round((next / totalFiles) * 100));
          return next;
        });
        addLog(`  [SKIP] ${event.reason}: ${event.message} (${event.duration_ms || 0}ms)`, 'skip');
        break;

      case 'file_done':
        setFilesProcessed((prev) => {
          const next = prev + 1;
          if (totalFiles > 0) setProgressPercent(Math.round((next / totalFiles) * 100));
          const elapsedSec = (Date.now() - startTime) / 1000;
          if (elapsedSec > 0) setItemsPerSecond(Math.round((next / elapsedSec) * 10) / 10);
          return next;
        });
        setCurrentStage('store');
        addLog(`  [DONE] ✓ Generated ${event.chunks || 0} chunks in ${event.duration_ms || 0}ms`, 'success');
        break;

      case 'file_error':
        addLog(`  [ERROR] ✗ Failed: ${event.file} — ${event.error}`, 'error');
        break;

      case 'job_complete':
        setProgressPercent(100);
        if (event.summary) {
          addLog(
            `[SUMMARY] Completed ${event.summary.succeeded} succeeded, ${event.summary.skipped} skipped, ${event.summary.failed} failed in ${event.summary.duration_s}s.`,
            'job'
          );
        }
        break;

      default:
        break;
    }
  };

  const handleStop = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
  };

  const getStageStatus = (stageId) => {
    if (!isIngesting) return 'idle';
    const stageOrder = ['checksum', 'tagging', 'extract_ocr', 'chunk', 'embed', 'store'];
    const currentIndex = stageOrder.indexOf(currentStage);
    const targetIndex = stageOrder.indexOf(stageId);

    if (currentIndex > targetIndex) return 'completed';
    if (currentIndex === targetIndex) return 'active';
    return 'pending';
  };

  return (
    <div className="space-y-6">
      {/* Telemetry HUD */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="p-5 bg-white border border-[#EAEAEA] rounded-2xl shadow-subtle">
          <div className="text-[11px] font-semibold text-muted uppercase">Engine Status</div>
          <div className="text-xl font-bold text-charcoal mt-1 capitalize flex items-center gap-2">
            <span
              className={`w-2.5 h-2.5 rounded-full ${
                isIngesting ? 'bg-emerald-500 animate-ping' : 'bg-slate-300'
              }`}
            />
            <span>{isIngesting ? 'Ingesting' : 'Ready'}</span>
          </div>
          <p className="text-[11px] text-muted mt-1">Multi-stage vector pipeline</p>
        </div>

        <div className="p-5 bg-white border border-[#EAEAEA] rounded-2xl shadow-subtle">
          <div className="text-[11px] font-semibold text-muted uppercase">Throughput</div>
          <div className="text-xl font-bold text-indigo-600 mt-1 font-mono">
            {itemsPerSecond > 0 ? `${itemsPerSecond} files/s` : '0 items/s'}
          </div>
          <p className="text-[11px] text-muted mt-1">Chunk & embedding velocity</p>
        </div>

        <div className="p-5 bg-white border border-[#EAEAEA] rounded-2xl shadow-subtle">
          <div className="text-[11px] font-semibold text-muted uppercase">Files Processed</div>
          <div className="text-xl font-bold text-emerald-600 mt-1 font-mono">
            {filesProcessed} {totalFiles > 0 ? `/ ${totalFiles}` : 'files'}
          </div>
          <p className="text-[11px] text-muted mt-1">Indexed this session</p>
        </div>

        <div className="p-5 bg-white border border-[#EAEAEA] rounded-2xl shadow-subtle">
          <div className="text-[11px] font-semibold text-muted uppercase">Active Target</div>
          <div className="text-xs font-mono font-bold text-charcoal mt-1 truncate" title={activeFile}>
            {activeFile || 'Idle (Waiting for triggers)'}
          </div>
          <p className="text-[11px] text-muted mt-1 truncate">{stageMessage || 'Pipeline standing by'}</p>
        </div>
      </div>

      {/* Manual Ingestion Trigger Panel */}
      <div className="bg-white border border-[#EAEAEA] rounded-2xl p-6 shadow-subtle space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-[#EAEAEA]">
          <div className="flex items-center gap-2">
            <Play className="w-4 h-4 text-charcoal" />
            <h3 className="text-sm font-bold text-charcoal">
              Streaming Ingestion Pipeline Controller
            </h3>
          </div>
          <span className="text-[11px] text-muted">
            Direct SSE Execution with Real-Time Progress Telemetry
          </span>
        </div>

        <form onSubmit={handleStartIngest} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
            <div className="md:col-span-2">
              <label className="block text-xs font-semibold text-charcoal mb-1">
                Target Folder or File Directory <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                required
                value={folderPath}
                onChange={(e) => setFolderPath(e.target.value)}
                placeholder="e.g. data/sample_courses or D:/data/syllabus"
                className="w-full px-3 py-2 bg-[#FBFBFA] border border-[#EAEAEA] rounded-xl text-xs font-mono text-charcoal focus:outline-none focus:border-charcoal focus:bg-white"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-charcoal mb-1">
                Department Override
              </label>
              <select
                value={department}
                onChange={(e) => setDepartment(e.target.value)}
                className="w-full px-3 py-2 bg-[#FBFBFA] border border-[#EAEAEA] rounded-xl text-xs text-charcoal focus:outline-none focus:border-charcoal"
              >
                <option value="Computer Science">Computer Science</option>
                <option value="Law">Law</option>
                <option value="Management">Management</option>
                <option value="Pharmacy">Pharmacy</option>
                <option value="Engineering">Engineering</option>
                <option value="General">General / Other</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-charcoal mb-1">
                Course / Module Name
              </label>
              <input
                type="text"
                value={course}
                onChange={(e) => setCourse(e.target.value)}
                placeholder="Auto-inferred from path"
                className="w-full px-3 py-2 bg-[#FBFBFA] border border-[#EAEAEA] rounded-xl text-xs text-charcoal focus:outline-none focus:border-charcoal"
              />
            </div>
          </div>

          <div className="flex flex-wrap items-center justify-between gap-4 pt-1">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={forceReprocess}
                onChange={(e) => setForceReprocess(e.target.checked)}
                className="rounded border-[#EAEAEA] text-charcoal focus:ring-charcoal"
              />
              <span className="text-xs text-charcoal font-medium">
                Force Reprocess (Bypass SHA-256 deduplication cache)
              </span>
            </label>

            <div className="flex items-center gap-2">
              {isIngesting ? (
                <button
                  type="button"
                  onClick={handleStop}
                  className="px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-xl text-xs font-semibold shadow-subtle transition flex items-center gap-1.5"
                >
                  <Square className="w-3.5 h-3.5" />
                  <span>Abort Ingestion</span>
                </button>
              ) : (
                <button
                  type="submit"
                  className="px-5 py-2 bg-charcoal hover:bg-[#262626] text-white rounded-xl text-xs font-semibold shadow-subtle transition flex items-center gap-2"
                >
                  <Play className="w-3.5 h-3.5 fill-current" />
                  <span>Start Streaming Ingestion</span>
                </button>
              )}
            </div>
          </div>
        </form>

        {/* Progress Bar */}
        {isIngesting && (
          <div className="space-y-1.5 pt-2">
            <div className="flex items-center justify-between text-xs font-mono">
              <span className="text-charcoal font-bold">
                Progress: {progressPercent}% ({filesProcessed}/{totalFiles} files)
              </span>
              <span className="text-muted">{stageMessage}</span>
            </div>
            <div className="w-full h-2 bg-slate-100 rounded-full overflow-hidden">
              <div
                className="h-full bg-charcoal transition-all duration-300 ease-out"
                style={{ width: `${Math.max(progressPercent, 4)}%` }}
              />
            </div>
          </div>
        )}
      </div>

      {/* Visual 6-Stage Pipeline Stepper */}
      <div className="bg-white border border-[#EAEAEA] rounded-2xl p-6 shadow-subtle space-y-4">
        <h3 className="text-xs font-bold uppercase tracking-wider text-muted">
          6-Stage Processing Architecture
        </h3>

        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
          {PIPELINE_STAGES.map((stage) => {
            const Icon = stage.icon;
            const status = getStageStatus(stage.id);

            let borderClass = 'border-[#EAEAEA] bg-[#FBFBFA]';
            let iconClass = 'text-muted bg-white';
            let badgeText = 'Idle';
            let badgeClass = 'text-muted bg-slate-100';

            if (status === 'active') {
              borderClass = 'border-charcoal bg-white shadow-subtle ring-1 ring-charcoal';
              iconClass = 'text-white bg-charcoal';
              badgeText = 'Running';
              badgeClass = 'text-emerald-700 bg-emerald-50 border border-emerald-200 animate-pulse';
            } else if (status === 'completed') {
              borderClass = 'border-[#C3E6CB] bg-[#F4FBF6]';
              iconClass = 'text-pastel-greenText bg-pastel-green';
              badgeText = 'Done';
              badgeClass = 'text-pastel-greenText bg-pastel-green';
            }

            return (
              <div
                key={stage.id}
                className={`p-3.5 rounded-xl border transition flex flex-col justify-between space-y-3 ${borderClass}`}
              >
                <div className="flex items-center justify-between">
                  <div className={`w-7 h-7 rounded-lg flex items-center justify-center ${iconClass}`}>
                    <Icon className="w-3.5 h-3.5" />
                  </div>
                  <span className={`px-1.5 py-0.5 rounded text-[9px] font-bold uppercase ${badgeClass}`}>
                    {badgeText}
                  </span>
                </div>

                <div>
                  <div className="font-bold text-charcoal text-xs leading-tight">
                    {stage.name}
                  </div>
                  <div className="text-[10px] text-muted mt-1 leading-normal">
                    {stage.desc}
                  </div>
                </div>
              </div>
            );
          })}
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
            className="px-2.5 py-1 text-xs border border-[#EAEAEA] rounded-lg text-muted hover:text-charcoal hover:bg-slate-50 transition"
          >
            Clear Console
          </button>
        </div>

        <div className="p-4 bg-slate-900 text-slate-100 rounded-xl font-mono text-[11px] h-80 overflow-y-auto space-y-1">
          {logs.length === 0 ? (
            <div className="text-slate-500 italic">
              [SYSTEM] Pipeline event listener connected. Start an ingestion above or watch for folder triggers...
            </div>
          ) : (
            logs.map((logItem, i) => {
              let tagColor = 'text-slate-400';
              if (logItem.type === 'job') tagColor = 'text-amber-400 font-bold';
              else if (logItem.type === 'stage') tagColor = 'text-cyan-400';
              else if (logItem.type === 'success') tagColor = 'text-emerald-400 font-bold';
              else if (logItem.type === 'skip') tagColor = 'text-slate-400 italic';
              else if (logItem.type === 'error') tagColor = 'text-red-400 font-bold';
              else if (logItem.type === 'warn') tagColor = 'text-amber-300';

              return (
                <div key={i} className="leading-relaxed flex items-start gap-2">
                  <span className="text-slate-500 shrink-0 select-none">[{logItem.timestamp}]</span>
                  <span className={tagColor}>{logItem.text}</span>
                </div>
              );
            })
          )}
          <div ref={terminalEndRef} />
        </div>
      </div>
    </div>
  );
}
