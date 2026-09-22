import React, { useState, useEffect } from 'react';
import { adminApi } from '../../api/client';
import { AlertTriangle, RotateCw, Trash2, RefreshCw, Eye, CheckCircle2 } from 'lucide-react';

export default function FailedTab() {
  const [failedFiles, setFailedFiles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedError, setSelectedError] = useState(null);

  const fetchFailed = async () => {
    setLoading(true);
    try {
      const res = await adminApi.failed.getFailedFiles();
      setFailedFiles(Array.isArray(res) ? res : (res?.items || []));
    } catch (err) {
      console.error('Failed to load DLQ files:', err);
      setFailedFiles([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchFailed();
  }, []);

  const handleRetry = async (id) => {
    try {
      await adminApi.failed.retry(id);
      fetchFailed();
    } catch (err) {
      alert(`Retry failed: ${err.message}`);
    }
  };

  const handleRetryAll = async () => {
    if (!window.confirm('Retry all failed files in dead-letter queue?')) return;
    try {
      await adminApi.failed.retryAll();
      fetchFailed();
    } catch (err) {
      alert(`Retry all failed: ${err.message}`);
    }
  };

  const handleDismiss = async (id) => {
    try {
      await adminApi.failed.dismiss(id);
      fetchFailed();
    } catch (err) {
      alert(`Dismiss failed: ${err.message}`);
    }
  };

  const handleClearAll = async () => {
    if (!window.confirm('Clear all dead-letter files?')) return;
    try {
      await adminApi.failed.clearAll();
      fetchFailed();
    } catch (err) {
      alert(`Clear failed: ${err.message}`);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white border border-[#EAEAEA] rounded-2xl p-6 shadow-subtle">
        <div>
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-xl bg-pastel-red flex items-center justify-center text-pastel-redText">
              <AlertTriangle className="w-4 h-4" />
            </div>
            <h2 className="text-base font-bold text-charcoal">
              Dead-Letter Queue (DLQ) & Failed Documents
            </h2>
          </div>
          <p className="text-xs text-muted mt-1">
            Corrupt PDFs, unsupported encodings, or OCR timeouts quarantined for administrative review.
          </p>
        </div>

        <div className="flex items-center gap-2 self-start">
          <button
            onClick={handleRetryAll}
            disabled={failedFiles.length === 0}
            className="px-3 py-1.5 bg-charcoal hover:bg-[#262626] text-white rounded-xl text-xs font-semibold transition flex items-center gap-1.5 disabled:opacity-50"
          >
            <RotateCw className="w-3.5 h-3.5" />
            <span>Retry All Failed</span>
          </button>
          <button
            onClick={handleClearAll}
            disabled={failedFiles.length === 0}
            className="px-3 py-1.5 border border-red-200 text-red-600 hover:bg-red-50 rounded-xl text-xs font-semibold transition disabled:opacity-50"
          >
            Clear All
          </button>
        </div>
      </div>

      {/* Table */}
      <div className="bg-white border border-[#EAEAEA] rounded-2xl shadow-subtle overflow-hidden">
        <div className="px-6 py-4 border-b border-[#EAEAEA] flex items-center justify-between">
          <h3 className="text-xs font-bold uppercase tracking-wider text-muted">
            Quarantined Documents ({failedFiles.length})
          </h3>
          <button onClick={fetchFailed} className="text-xs text-muted hover:text-charcoal flex items-center gap-1">
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Refresh</span>
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="bg-[#FBFBFA] border-b border-[#EAEAEA] text-[11px] font-semibold text-muted uppercase">
                <th className="py-3 px-6">File Path</th>
                <th className="py-3 px-6">Failure Reason</th>
                <th className="py-3 px-6">Retry Count</th>
                <th className="py-3 px-6">Failed At</th>
                <th className="py-3 px-6 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#EAEAEA]">
              {loading ? (
                <tr>
                  <td colSpan={5} className="py-8 text-center text-muted">Loading failed queue...</td>
                </tr>
              ) : failedFiles.length === 0 ? (
                <tr>
                  <td colSpan={5} className="py-12 text-center text-muted">
                    <CheckCircle2 className="w-6 h-6 text-emerald-600 mx-auto mb-2" />
                    <span>No failed files in queue! Ingestion pipeline healthy.</span>
                  </td>
                </tr>
              ) : (
                failedFiles.map((item) => (
                  <tr key={item.id} className="hover:bg-slate-50">
                    <td className="py-3 px-6 font-mono font-medium text-charcoal">{item.path || item.file_path}</td>
                    <td className="py-3 px-6 text-pastel-redText font-mono text-[11px] max-w-xs truncate">
                      {item.error_message || item.error || 'Unknown error'}
                    </td>
                    <td className="py-3 px-6 font-mono">{item.retry_count || 0}</td>
                    <td className="py-3 px-6 text-muted font-mono text-[11px]">
                      {item.failed_at ? new Date(item.failed_at).toLocaleString() : '—'}
                    </td>
                    <td className="py-3 px-6 text-right">
                      <div className="inline-flex items-center gap-1.5">
                        <button
                          onClick={() => setSelectedError(item)}
                          title="Inspect Error"
                          className="p-1.5 rounded-lg border border-slate-200 text-slate-700 hover:bg-slate-100"
                        >
                          <Eye className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={() => handleRetry(item.id)}
                          title="Retry File"
                          className="p-1.5 rounded-lg border border-slate-200 text-emerald-600 hover:bg-emerald-50"
                        >
                          <RotateCw className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={() => handleDismiss(item.id)}
                          title="Dismiss"
                          className="p-1.5 rounded-lg border border-red-200 text-red-600 hover:bg-red-50"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Inspect Error Modal */}
      {selectedError && (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white border border-[#EAEAEA] rounded-2xl max-w-lg w-full p-6 shadow-float space-y-3">
            <h3 className="text-sm font-bold text-charcoal">Failure Diagnostic Trace</h3>
            <div className="p-3 bg-slate-900 text-slate-100 rounded-xl font-mono text-[11px] max-h-60 overflow-y-auto">
              {selectedError.error_message || selectedError.error || 'No detailed trace available.'}
            </div>
            <div className="pt-2 flex justify-end">
              <button
                onClick={() => setSelectedError(null)}
                className="px-4 py-1.5 bg-charcoal text-white rounded-xl text-xs font-semibold"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
