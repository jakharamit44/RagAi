import React, { useState, useEffect, useRef } from 'react';
import { adminApi } from '../../api/client';
import {
  Server,
  Activity,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Play,
  RotateCcw,
  Zap,
  RefreshCw,
  Terminal,
  ShieldCheck,
  Layers,
} from 'lucide-react';

export default function MigrationTab() {
  const [sourceStatus, setSourceStatus] = useState(null);
  const [loadingSource, setLoadingSource] = useState(false);

  // Target Spec
  const [targetSpec, setTargetSpec] = useState({
    host: '192.168.81.160',
    postgres_port: 5432,
    postgres_db: 'university_rag',
    postgres_user: 'ragai',
    postgres_password: '9wtbai4u6xHovYkSnl2TVApBI0ZjJMK1',
    redis_port: 6379,
    redis_password: '9wtbai4u6xHovYkSnl2TVApBI0ZjJMK1',
    qdrant_port: 6333,
    qdrant_api_key: '9wtbai4u6xHovYkSnl2TVApBI0ZjJMK1',
    qdrant_https: false,
    tei_port: 8080,
    minio_port: 9000,
    minio_user: 'minioadmin',
    minio_password: '9wtbai4u6xHovYkSnl2TVApBI0ZjJMK1',
  });

  // Probe
  const [probeResult, setProbeResult] = useState(null);
  const [probing, setProbing] = useState(false);

  // Migration Runner
  const [migrationStatus, setMigrationStatus] = useState(null);
  const [migrating, setMigrating] = useState(false);
  const [logs, setLogs] = useState([]);
  const pollIntervalRef = useRef(null);

  // Parity Report
  const [parityReport, setParityReport] = useState(null);

  // Cutover / Rollback Modals
  const [showCutoverModal, setShowCutoverModal] = useState(false);
  const [showRollbackModal, setShowRollbackModal] = useState(false);
  const [cutoverLoading, setCutoverLoading] = useState(false);
  const [rollbackLoading, setRollbackLoading] = useState(false);

  const fetchSourceStatus = async () => {
    setLoadingSource(true);
    try {
      const data = await adminApi.migration.getSourceStatus();
      setSourceStatus(data);
    } catch (err) {
      console.error('Failed to load source telemetry:', err);
    } finally {
      setLoadingSource(false);
    }
  };

  useEffect(() => {
    fetchSourceStatus();
    return () => {
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
    };
  }, []);

  const handleQuickFill = () => {
    const currentHost = targetSpec.host || '192.168.81.160';
    setTargetSpec({
      host: currentHost,
      postgres_port: 5432,
      postgres_db: 'university_rag',
      postgres_user: 'ragai',
      postgres_password: '9wtbai4u6xHovYkSnl2TVApBI0ZjJMK1',
      redis_port: 6379,
      redis_password: '9wtbai4u6xHovYkSnl2TVApBI0ZjJMK1',
      qdrant_port: 6333,
      qdrant_api_key: '9wtbai4u6xHovYkSnl2TVApBI0ZjJMK1',
      qdrant_https: false,
      tei_port: 8080,
      minio_port: 9000,
      minio_user: 'minioadmin',
      minio_password: '9wtbai4u6xHovYkSnl2TVApBI0ZjJMK1',
    });
  };

  const handleProbe = async () => {
    if (!targetSpec.host.trim()) {
      alert('Please enter a target host IP.');
      return;
    }
    setProbing(true);
    setProbeResult(null);
    try {
      const res = await adminApi.migration.probeTarget(targetSpec);
      setProbeResult(res);
    } catch (err) {
      alert(`Probe failed: ${err.message}`);
    } finally {
      setProbing(false);
    }
  };

  const startMigration = async () => {
    if (!window.confirm(`Initiate complete streaming migration to ${targetSpec.host}?`)) {
      return;
    }
    setMigrating(true);
    setLogs([]);
    try {
      await adminApi.migration.startMigration(targetSpec);
      pollMigration();
    } catch (err) {
      alert(`Could not start migration: ${err.message}`);
      setMigrating(false);
    }
  };

  const pollMigration = () => {
    if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
    pollIntervalRef.current = setInterval(async () => {
      try {
        const stat = await adminApi.migration.getStatus();
        setMigrationStatus(stat);
        if (stat.logs) setLogs(stat.logs);

        if (stat.status === 'completed') {
          clearInterval(pollIntervalRef.current);
          setMigrating(false);
          loadParity();
        } else if (stat.status === 'failed' || stat.status === 'cancelled') {
          clearInterval(pollIntervalRef.current);
          setMigrating(false);
        }
      } catch (err) {
        console.error('Polling error:', err);
      }
    }, 1500);
  };

  const cancelMigration = async () => {
    try {
      await adminApi.migration.cancelMigration();
    } catch (err) {
      alert(`Cancel error: ${err.message}`);
    }
  };

  const loadParity = async () => {
    try {
      const p = await adminApi.migration.getParity();
      setParityReport(p);
    } catch (err) {
      console.warn('Parity not yet ready:', err);
    }
  };

  const executeCutover = async () => {
    setCutoverLoading(true);
    try {
      const res = await adminApi.migration.cutover(targetSpec);
      alert(`Live cutover successful!\nActive host is now: ${res.new_host}`);
      setShowCutoverModal(false);
      fetchSourceStatus();
    } catch (err) {
      alert(`Cutover failed: ${err.message}`);
    } finally {
      setCutoverLoading(false);
    }
  };

  const executeRollback = async () => {
    setRollbackLoading(true);
    try {
      const res = await adminApi.migration.rollback();
      alert(`Rollback successful!\nReverted to: ${res.restored_host}`);
      setShowRollbackModal(false);
      fetchSourceStatus();
    } catch (err) {
      alert(`Rollback failed: ${err.message}`);
    } finally {
      setRollbackLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Active Telemetry Banner */}
      <div className="bg-white border border-[#EAEAEA] rounded-2xl p-6 shadow-subtle">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="flex h-2.5 w-2.5 relative">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500"></span>
              </span>
              <h2 className="text-base font-bold text-charcoal">
                Active Source Infrastructure Telemetry
              </h2>
            </div>
            <p className="text-xs text-muted mt-1">
              Live production services running on Ubuntu VM stack. Preserved strictly read-only during migration.
            </p>
          </div>

          <button
            onClick={fetchSourceStatus}
            disabled={loadingSource}
            className="px-3 py-1.5 border border-[#EAEAEA] rounded-xl text-xs font-semibold text-muted hover:text-charcoal hover:bg-slate-50 transition flex items-center gap-1.5 self-start"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loadingSource ? 'animate-spin' : ''}`} />
            <span>Refresh Telemetry</span>
          </button>
        </div>

        {sourceStatus && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-5">
            <div className="p-4 bg-[#FBFBFA] border border-[#EAEAEA] rounded-xl">
              <div className="text-[11px] font-semibold text-muted uppercase">Active VM Host</div>
              <div className="text-sm font-bold font-mono text-charcoal mt-1">
                {sourceStatus.source_host}
              </div>
            </div>

            <div className="p-4 bg-[#FBFBFA] border border-[#EAEAEA] rounded-xl">
              <div className="text-[11px] font-semibold text-muted uppercase">PostgreSQL Total Rows</div>
              <div className="text-sm font-bold font-mono text-charcoal mt-1">
                {sourceStatus.total_rows?.toLocaleString() || 0}
              </div>
            </div>

            <div className="p-4 bg-[#FBFBFA] border border-[#EAEAEA] rounded-xl">
              <div className="text-[11px] font-semibold text-muted uppercase">Qdrant Vectors</div>
              <div className="text-sm font-bold font-mono text-charcoal mt-1">
                {sourceStatus.qdrant_points_count?.toLocaleString() || 0}
              </div>
            </div>

            <div className="p-4 bg-[#FBFBFA] border border-[#EAEAEA] rounded-xl">
              <div className="text-[11px] font-semibold text-muted uppercase">Rollback Archive</div>
              <div className="text-sm font-bold mt-1">
                {sourceStatus.rollback_available ? (
                  <span className="text-pastel-greenText font-semibold">Available</span>
                ) : (
                  <span className="text-muted font-normal">None archived</span>
                )}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Target VM Connection Form */}
      <div className="bg-white border border-[#EAEAEA] rounded-2xl p-6 shadow-subtle space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-[#EAEAEA]">
          <div>
            <h3 className="text-sm font-bold text-charcoal">
              Target Ubuntu VM Connection Specification
            </h3>
            <p className="text-xs text-muted">
              Enter network and credential details of the target Ubuntu VM.
            </p>
          </div>
          <button
            onClick={handleQuickFill}
            className="px-3 py-1.5 bg-[#FBFBFA] hover:bg-slate-100 border border-[#EAEAEA] rounded-xl text-xs font-semibold text-charcoal transition self-start"
          >
            Quick-Fill Standard VM Defaults
          </button>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div>
            <label className="block text-xs font-semibold text-charcoal mb-1">
              Target Host / IP Address <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              value={targetSpec.host}
              onChange={(e) => setTargetSpec({ ...targetSpec, host: e.target.value })}
              className="w-full px-3 py-2 bg-white border border-[#EAEAEA] rounded-xl text-xs font-mono font-medium text-charcoal"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-charcoal mb-1">
              PostgreSQL Port & Database
            </label>
            <div className="grid grid-cols-2 gap-2">
              <input
                type="number"
                value={targetSpec.postgres_port}
                onChange={(e) => setTargetSpec({ ...targetSpec, postgres_port: parseInt(e.target.value) })}
                className="w-full px-3 py-2 bg-white border border-[#EAEAEA] rounded-xl text-xs font-mono"
              />
              <input
                type="text"
                value={targetSpec.postgres_db}
                onChange={(e) => setTargetSpec({ ...targetSpec, postgres_db: e.target.value })}
                className="w-full px-3 py-2 bg-white border border-[#EAEAEA] rounded-xl text-xs font-mono"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-charcoal mb-1">
              PostgreSQL User & Password
            </label>
            <div className="grid grid-cols-2 gap-2">
              <input
                type="text"
                value={targetSpec.postgres_user}
                onChange={(e) => setTargetSpec({ ...targetSpec, postgres_user: e.target.value })}
                className="w-full px-3 py-2 bg-white border border-[#EAEAEA] rounded-xl text-xs font-mono"
              />
              <input
                type="password"
                value={targetSpec.postgres_password}
                onChange={(e) => setTargetSpec({ ...targetSpec, postgres_password: e.target.value })}
                className="w-full px-3 py-2 bg-white border border-[#EAEAEA] rounded-xl text-xs font-mono"
              />
            </div>
          </div>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 pt-2">
          <div>
            <label className="block text-xs font-semibold text-charcoal mb-1">Qdrant Port</label>
            <input
              type="number"
              value={targetSpec.qdrant_port}
              onChange={(e) => setTargetSpec({ ...targetSpec, qdrant_port: parseInt(e.target.value) })}
              className="w-full px-3 py-2 bg-white border border-[#EAEAEA] rounded-xl text-xs font-mono"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-charcoal mb-1">Redis Port</label>
            <input
              type="number"
              value={targetSpec.redis_port}
              onChange={(e) => setTargetSpec({ ...targetSpec, redis_port: parseInt(e.target.value) })}
              className="w-full px-3 py-2 bg-white border border-[#EAEAEA] rounded-xl text-xs font-mono"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-charcoal mb-1">TEI GPU Port</label>
            <input
              type="number"
              value={targetSpec.tei_port}
              onChange={(e) => setTargetSpec({ ...targetSpec, tei_port: parseInt(e.target.value) })}
              className="w-full px-3 py-2 bg-white border border-[#EAEAEA] rounded-xl text-xs font-mono"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-charcoal mb-1">MinIO Port</label>
            <input
              type="number"
              value={targetSpec.minio_port}
              onChange={(e) => setTargetSpec({ ...targetSpec, minio_port: parseInt(e.target.value) })}
              className="w-full px-3 py-2 bg-white border border-[#EAEAEA] rounded-xl text-xs font-mono"
            />
          </div>
        </div>

        <div className="pt-2 flex items-center justify-between border-t border-[#EAEAEA]">
          <div className="text-[11px] text-muted">
            Click Probe to test network ports and authenticate against all 5 target containers.
          </div>
          <button
            onClick={handleProbe}
            disabled={probing}
            className="px-4 py-2 bg-charcoal hover:bg-[#262626] text-white rounded-xl text-xs font-semibold transition flex items-center gap-2 disabled:opacity-50"
          >
            <Activity className={`w-3.5 h-3.5 ${probing ? 'animate-spin' : ''}`} />
            <span>{probing ? 'Probing Target Services...' : 'Pre-Flight Probe Target VM'}</span>
          </button>
        </div>

        {/* Probe Matrix */}
        {probeResult && (
          <div className="mt-4 p-4 bg-[#FBFBFA] border border-[#EAEAEA] rounded-xl">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-bold text-charcoal">
                Pre-Flight Health Matrix ({probeResult.host})
              </span>
              <span
                className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${
                  probeResult.all_ok
                    ? 'bg-pastel-green text-pastel-greenText border border-[#C3E6CB]'
                    : 'bg-pastel-red text-pastel-redText border border-[#F5C2C7]'
                }`}
              >
                {probeResult.all_ok ? 'All 5 Services Healthy' : 'Action Required'}
              </span>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
              {Object.entries(probeResult.services).map(([name, s]) => (
                <div key={name} className="p-3 bg-white border border-[#EAEAEA] rounded-xl text-xs">
                  <div className="flex items-center justify-between">
                    <span className="font-semibold uppercase text-charcoal">{name}</span>
                    {s.ok ? (
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                    ) : (
                      <XCircle className="w-3.5 h-3.5 text-red-600" />
                    )}
                  </div>
                  <div className="mt-1 text-[11px] font-mono text-muted">
                    {s.ok ? `${s.latency_ms} ms` : s.error || 'Failed'}
                  </div>
                </div>
              ))}
            </div>

            {probeResult.all_ok && !migrating && (
              <div className="mt-4 pt-3 border-t border-[#EAEAEA] flex justify-end">
                <button
                  onClick={startMigration}
                  className="px-5 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-bold shadow-subtle transition flex items-center gap-2"
                >
                  <Play className="w-3.5 h-3.5" />
                  <span>Start Full Data Migration</span>
                </button>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Migration Progress & Logs */}
      {(migrating || migrationStatus) && (
        <div className="bg-white border border-[#EAEAEA] rounded-2xl p-6 shadow-subtle space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-sm font-bold text-charcoal">
                Data Streaming Pipeline Runner
              </h3>
              <p className="text-xs text-muted">
                {migrationStatus?.current_task || 'Streaming in progress...'}
              </p>
            </div>
            {migrating && (
              <button
                onClick={cancelMigration}
                className="px-3 py-1.5 border border-red-200 text-red-600 hover:bg-red-50 rounded-xl text-xs font-semibold"
              >
                Cancel Migration
              </button>
            )}
          </div>

          {/* Progress Bar */}
          <div className="w-full bg-[#EAEAEA] rounded-full h-3 overflow-hidden">
            <div
              className="bg-charcoal h-3 rounded-full transition-all duration-300"
              style={{ width: `${migrationStatus?.progress_percent || 0}%` }}
            ></div>
          </div>
          <div className="flex justify-between text-[11px] font-mono text-muted">
            <span>Stage: {migrationStatus?.stage || 'idle'}</span>
            <span>{migrationStatus?.progress_percent?.toFixed(1) || 0}% Complete</span>
          </div>

          {/* Monospace Terminal Logs */}
          <div className="p-3 bg-slate-900 text-slate-100 rounded-xl font-mono text-[11px] h-48 overflow-y-auto space-y-1">
            {logs.map((log, idx) => (
              <div key={idx} className="text-slate-300">
                &gt; {log}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Parity Report */}
      {parityReport && (
        <div className="bg-white border border-[#EAEAEA] rounded-2xl p-6 shadow-subtle space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-[#EAEAEA]">
            <div>
              <h3 className="text-sm font-bold text-charcoal">
                Data Parity Audit Report (Source vs Target)
              </h3>
              <p className="text-xs text-muted">
                Table-by-table row and vector count verification.
              </p>
            </div>
            <span
              className={`px-2.5 py-1 rounded-full text-xs font-bold uppercase tracking-wider ${
                parityReport.overall_parity
                  ? 'bg-pastel-green text-pastel-greenText border border-[#C3E6CB]'
                  : 'bg-pastel-red text-pastel-redText border border-[#F5C2C7]'
              }`}
            >
              {parityReport.overall_parity ? '100% Parity Confirmed' : 'Discrepancy Detected'}
            </span>
          </div>

          <div className="overflow-x-auto max-h-60 overflow-y-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="bg-[#FBFBFA] border-b border-[#EAEAEA] text-[11px] font-semibold text-muted uppercase">
                  <th className="py-2 px-4">Entity</th>
                  <th className="py-2 px-4">Source Count</th>
                  <th className="py-2 px-4">Target Count</th>
                  <th className="py-2 px-4 text-right">Parity Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#EAEAEA]">
                {parityReport.items.map((item) => (
                  <tr key={item.name} className="hover:bg-slate-50">
                    <td className="py-2 px-4 font-mono font-medium">{item.name}</td>
                    <td className="py-2 px-4 font-mono">{item.source_count.toLocaleString()}</td>
                    <td className="py-2 px-4 font-mono">{item.target_count.toLocaleString()}</td>
                    <td className="py-2 px-4 text-right">
                      {item.parity ? (
                        <span className="text-emerald-600 font-bold">MATCH</span>
                      ) : (
                        <span className="text-red-600 font-bold">MISMATCH</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Cutover & Rollback Controls */}
          <div className="pt-4 border-t border-[#EAEAEA] flex flex-wrap items-center justify-between gap-3">
            <button
              onClick={() => setShowRollbackModal(true)}
              className="px-4 py-2 border border-amber-300 text-amber-800 hover:bg-amber-50 rounded-xl text-xs font-bold transition flex items-center gap-1.5"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>Rollback to Previous Server</span>
            </button>

            <button
              onClick={() => setShowCutoverModal(true)}
              disabled={!parityReport.overall_parity}
              className="px-5 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-bold shadow-subtle transition flex items-center gap-1.5 disabled:opacity-50"
            >
              <Zap className="w-3.5 h-3.5" />
              <span>Switch Active Infrastructure (Atomic Cutover)</span>
            </button>
          </div>
        </div>
      )}

      {/* Cutover Modal */}
      {showCutoverModal && (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white border border-[#EAEAEA] rounded-2xl max-w-lg w-full p-6 shadow-float space-y-4">
            <h3 className="text-base font-bold text-charcoal">Confirm Live Infrastructure Cutover</h3>
            <p className="text-xs text-muted">
              You are about to switch active production backend connections to <strong>{targetSpec.host}</strong>.
              Active .env will be updated, backup created, and database pools hot-reloaded in memory.
            </p>
            <div className="pt-2 flex justify-end gap-2 border-t border-[#EAEAEA]">
              <button
                onClick={() => setShowCutoverModal(false)}
                className="px-3 py-1.5 border border-[#EAEAEA] rounded-xl text-xs font-semibold text-muted"
              >
                Cancel
              </button>
              <button
                onClick={executeCutover}
                disabled={cutoverLoading}
                className="px-4 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-bold transition"
              >
                {cutoverLoading ? 'Switching...' : 'Confirm Live Cutover'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Rollback Modal */}
      {showRollbackModal && (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white border border-[#EAEAEA] rounded-2xl max-w-lg w-full p-6 shadow-float space-y-4">
            <h3 className="text-base font-bold text-charcoal">Confirm Infrastructure Rollback</h3>
            <p className="text-xs text-muted">
              Revert active .env and hot-rebind connections back to the previously archived host.
            </p>
            <div className="pt-2 flex justify-end gap-2 border-t border-[#EAEAEA]">
              <button
                onClick={() => setShowRollbackModal(false)}
                className="px-3 py-1.5 border border-[#EAEAEA] rounded-xl text-xs font-semibold text-muted"
              >
                Cancel
              </button>
              <button
                onClick={executeRollback}
                disabled={rollbackLoading}
                className="px-4 py-1.5 bg-amber-600 hover:bg-amber-700 text-white rounded-xl text-xs font-bold transition"
              >
                {rollbackLoading ? 'Reverting...' : 'Confirm Rollback'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
