import React, { useState, useEffect } from 'react';
import { adminApi } from '../../api/client';
import {
  Hash,
  CheckCircle2,
  RefreshCw,
  ShieldAlert,
  ShieldCheck,
  Search,
  Copy,
  Check,
  AlertTriangle,
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
  FileText
} from 'lucide-react';

export default function ManifestTab() {
  const [entries, setEntries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Search & Filter
  const [search, setSearch] = useState('');
  const [submittedSearch, setSubmittedSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('');

  // Pagination
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(1);

  // Verification & Copy Feedback
  const [verifying, setVerifying] = useState(false);
  const [verifyResult, setVerifyResult] = useState(null);
  const [copiedHash, setCopiedHash] = useState(null);

  const fetchManifest = async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      params.append('page', page.toString());
      params.append('page_size', pageSize.toString());
      if (statusFilter && statusFilter !== 'all') {
        params.append('status', statusFilter);
      }
      if (submittedSearch.trim()) {
        params.append('search', submittedSearch.trim());
      }

      const res = await adminApi.manifest.getEntries(params.toString());

      if (res && typeof res === 'object' && Array.isArray(res.items)) {
        setEntries(res.items);
        setTotal(res.total || 0);
        setTotalPages(res.total_pages || 1);
      } else if (Array.isArray(res)) {
        setEntries(res);
        setTotal(res.length);
        setTotalPages(Math.max(1, Math.ceil(res.length / pageSize)));
      } else {
        setEntries([]);
        setTotal(0);
        setTotalPages(1);
      }
    } catch (err) {
      console.error('Failed to load manifest:', err);
      setError(err.message || 'Failed to load change detection manifest.');
      setEntries([]);
      setTotal(0);
      setTotalPages(1);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchManifest();
  }, [page, pageSize, statusFilter, submittedSearch]);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    setPage(1);
    setSubmittedSearch(search);
  };

  const handleResetFilters = () => {
    setSearch('');
    setSubmittedSearch('');
    setStatusFilter('');
    setPage(1);
  };

  const handleVerify = async () => {
    setVerifying(true);
    setVerifyResult(null);
    try {
      const res = await adminApi.manifest.verifyIntegrity();
      setVerifyResult(res);
      fetchManifest();
    } catch (err) {
      alert(`Cryptographic verification error: ${err.message}`);
    } finally {
      setVerifying(false);
    }
  };

  const handleCopyHash = (hash) => {
    if (!hash) return;
    navigator.clipboard.writeText(hash);
    setCopiedHash(hash);
    setTimeout(() => setCopiedHash(null), 1800);
  };

  const formatFileSize = (bytes) => {
    if (!bytes || bytes <= 0) return '—';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  const getStatusBadge = (status) => {
    const s = (status || '').toLowerCase();
    switch (s) {
      case 'done':
      case 'indexed':
      case 'verified':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-pastel-green text-pastel-greenText border border-[#C3E6CB] uppercase">
            <CheckCircle2 className="w-3 h-3" />
            <span>Verified</span>
          </span>
        );
      case 'processing':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-pastel-blue text-pastel-blueText border border-[#BEE3F8] uppercase">
            <RefreshCw className="w-3 h-3 animate-spin" />
            <span>Processing</span>
          </span>
        );
      case 'failed':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-pastel-red text-pastel-redText border border-[#F5C2C7] uppercase">
            <ShieldAlert className="w-3 h-3" />
            <span>Failed</span>
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-slate-100 text-slate-700 uppercase">
            <span>{s || 'Pending'}</span>
          </span>
        );
    }
  };

  const getPageNumbers = () => {
    const pages = [];
    const maxVisible = 5;
    if (totalPages <= maxVisible) {
      for (let i = 1; i <= totalPages; i++) pages.push(i);
    } else {
      let start = Math.max(1, page - 2);
      let end = Math.min(totalPages, start + maxVisible - 1);
      if (end - start < maxVisible - 1) {
        start = Math.max(1, end - maxVisible + 1);
      }
      for (let i = start; i <= end; i++) pages.push(i);
    }
    return pages;
  };

  const startIdx = total > 0 ? (page - 1) * pageSize + 1 : 0;
  const endIdx = total > 0 ? Math.min(page * pageSize, total) : 0;

  return (
    <div className="space-y-6">
      {/* Header & Controls */}
      <div className="bg-white border border-[#EAEAEA] rounded-2xl p-6 shadow-subtle space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 rounded-xl bg-charcoal text-white flex items-center justify-center">
                <Hash className="w-4 h-4" />
              </div>
              <div>
                <h2 className="text-base font-bold text-charcoal">
                  Cryptographic Ingestion Manifest
                </h2>
                <p className="text-xs text-muted">
                  SHA-256 delta detection manifest protecting against silent document corruption or drift.
                </p>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2.5 self-start">
            <button
              onClick={fetchManifest}
              disabled={loading}
              className="px-3 py-2 border border-[#EAEAEA] rounded-xl text-xs font-semibold text-muted hover:text-charcoal hover:bg-slate-50 transition flex items-center gap-1.5"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
              <span>Refresh</span>
            </button>

            <button
              onClick={handleVerify}
              disabled={verifying}
              className="px-4 py-2 bg-charcoal hover:bg-[#262626] text-white rounded-xl text-xs font-semibold shadow-subtle transition flex items-center gap-2 disabled:opacity-50"
            >
              <ShieldCheck className={`w-3.5 h-3.5 ${verifying ? 'animate-pulse' : ''}`} />
              <span>{verifying ? 'Verifying Hashes...' : 'Verify Cryptographic Integrity'}</span>
            </button>
          </div>
        </div>

        {/* Verification Summary Banner */}
        {verifyResult && (
          <div className="p-4 bg-[#FBFBFA] border border-[#EAEAEA] rounded-xl text-xs flex items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-lg bg-emerald-100 text-emerald-800 flex items-center justify-center shrink-0">
                <ShieldCheck className="w-4 h-4" />
              </div>
              <div>
                <div className="font-bold text-charcoal">
                  Cryptographic Verification Complete: {verifyResult.message || 'All checksums validated'}
                </div>
                <div className="text-[11px] text-muted flex items-center gap-4 mt-0.5 font-mono">
                  <span>Total Files: {verifyResult.total_checked ?? total}</span>
                  <span className="text-emerald-700 font-bold">Passed: {verifyResult.verified_ok ?? total}</span>
                  {verifyResult.changed > 0 && <span className="text-amber-600 font-bold">Changed: {verifyResult.changed}</span>}
                  {verifyResult.missing > 0 && <span className="text-red-600 font-bold">Missing: {verifyResult.missing}</span>}
                </div>
              </div>
            </div>
            <button
              onClick={() => setVerifyResult(null)}
              className="text-xs text-muted hover:text-charcoal"
            >
              Dismiss
            </button>
          </div>
        )}

        {/* Search & Filter Bar */}
        <div className="flex flex-wrap items-center gap-3 pt-2 border-t border-[#EAEAEA]">
          <form onSubmit={handleSearchSubmit} className="flex-1 min-w-[260px] flex items-center gap-2">
            <div className="relative flex-1">
              <Search className="w-4 h-4 text-muted absolute left-3 top-2.5" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search manifest by file path, filename, or SHA-256 hash..."
                className="w-full pl-9 pr-3 py-2 bg-[#FBFBFA] border border-[#EAEAEA] rounded-xl text-xs text-charcoal focus:outline-none focus:border-charcoal focus:bg-white"
              />
            </div>
            <button
              type="submit"
              className="px-4 py-2 bg-charcoal text-white rounded-xl text-xs font-semibold hover:bg-[#262626] transition"
            >
              Search
            </button>
          </form>

          <div className="flex items-center gap-2">
            <select
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value);
                setPage(1);
              }}
              className="px-3 py-2 bg-[#FBFBFA] border border-[#EAEAEA] rounded-xl text-xs text-charcoal focus:outline-none focus:border-charcoal"
            >
              <option value="">All Statuses</option>
              <option value="done">Verified (Done)</option>
              <option value="processing">In Processing</option>
              <option value="failed">Failed / Corrupt</option>
              <option value="pending">Pending Ingest</option>
            </select>

            {(submittedSearch || statusFilter) && (
              <button
                onClick={handleResetFilters}
                className="px-3 py-2 text-xs text-muted hover:text-charcoal border border-[#EAEAEA] rounded-xl hover:bg-slate-50 transition"
              >
                Clear Filters
              </button>
            )}
          </div>
        </div>
      </div>

      {error && (
        <div className="p-4 bg-pastel-red/60 border border-[#F5C2C7] rounded-2xl flex items-start gap-3 text-pastel-redText text-xs">
          <ShieldAlert className="w-4 h-4 shrink-0 mt-0.5" />
          <div>
            <span className="font-semibold">Manifest Error:</span> {error}
          </div>
        </div>
      )}

      {/* Manifest Table */}
      <div className="bg-white border border-[#EAEAEA] rounded-2xl shadow-subtle overflow-hidden">
        <div className="px-6 py-4 border-b border-[#EAEAEA] flex items-center justify-between">
          <div className="flex items-center gap-2">
            <h3 className="text-xs font-bold uppercase tracking-wider text-muted">
              Manifest Registry Entries
            </h3>
            <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-slate-100 text-slate-700">
              {total.toLocaleString()} Total
            </span>
          </div>

          <div className="flex items-center gap-2 text-xs text-muted">
            <span>Show:</span>
            <select
              value={pageSize}
              onChange={(e) => {
                setPageSize(Number(e.target.value));
                setPage(1);
              }}
              className="px-2 py-1 bg-[#FBFBFA] border border-[#EAEAEA] rounded-lg text-xs text-charcoal focus:outline-none"
            >
              <option value={15}>15 per page</option>
              <option value={25}>25 per page</option>
              <option value={50}>50 per page</option>
              <option value={100}>100 per page</option>
            </select>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="bg-[#FBFBFA] border-b border-[#EAEAEA] text-[11px] font-semibold text-muted uppercase tracking-wider">
                <th className="py-3 px-6">Source File Path</th>
                <th className="py-3 px-6">SHA-256 Cryptographic Digest</th>
                <th className="py-3 px-6">File Size</th>
                <th className="py-3 px-6">Status</th>
                <th className="py-3 px-6 text-right">Last Verified</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#EAEAEA]">
              {loading ? (
                <tr>
                  <td colSpan={5} className="py-12 text-center text-muted">
                    <RefreshCw className="w-5 h-5 animate-spin mx-auto mb-2 text-muted" />
                    <span>Loading cryptographic manifest...</span>
                  </td>
                </tr>
              ) : entries.length === 0 ? (
                <tr>
                  <td colSpan={5} className="py-12 text-center text-muted">
                    No manifest entries found matching criteria.
                  </td>
                </tr>
              ) : (
                entries.map((item) => {
                  const hash = item.content_hash || item.file_hash || '';
                  const size = item.file_size_bytes || item.file_size || null;
                  const dateStr = item.updated_at || (item.mtime ? new Date(item.mtime * 1000).toLocaleString() : null);

                  return (
                    <tr key={item.id} className="hover:bg-slate-50/70 transition">
                      <td className="py-3.5 px-6 max-w-sm">
                        <div className="flex items-center gap-2">
                          <FileText className="w-3.5 h-3.5 text-muted shrink-0" />
                          <div className="font-mono font-medium text-charcoal truncate" title={item.path}>
                            {item.path}
                          </div>
                        </div>
                        {item.error && (
                          <div className="text-[10px] text-red-600 font-mono mt-0.5 flex items-center gap-1">
                            <AlertTriangle className="w-3 h-3 shrink-0" />
                            <span className="truncate">{item.error}</span>
                          </div>
                        )}
                      </td>

                      <td className="py-3.5 px-6">
                        {hash ? (
                          <div className="inline-flex items-center gap-1.5 font-mono text-[11px] text-muted">
                            <span>{hash.substring(0, 16)}...{hash.substring(hash.length - 8)}</span>
                            <button
                              onClick={() => handleCopyHash(hash)}
                              title="Copy full SHA-256 hash"
                              className="p-1 text-muted hover:text-charcoal rounded hover:bg-slate-100 transition"
                            >
                              {copiedHash === hash ? (
                                <Check className="w-3 h-3 text-emerald-600" />
                              ) : (
                                <Copy className="w-3 h-3" />
                              )}
                            </button>
                          </div>
                        ) : (
                          <span className="text-muted font-mono">—</span>
                        )}
                      </td>

                      <td className="py-3.5 px-6 font-mono text-[11px] text-muted">
                        {formatFileSize(size)}
                      </td>

                      <td className="py-3.5 px-6">
                        {getStatusBadge(item.status)}
                      </td>

                      <td className="py-3.5 px-6 text-right font-mono text-[11px] text-muted">
                        {dateStr ? (dateStr.includes('T') ? new Date(dateStr).toLocaleString() : dateStr) : '—'}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination Footer */}
        <div className="px-6 py-4 bg-[#FBFBFA] border-t border-[#EAEAEA] flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs text-muted">
          <div>
            Showing <span className="font-bold text-charcoal">{startIdx}</span> to{' '}
            <span className="font-bold text-charcoal">{endIdx}</span> of{' '}
            <span className="font-bold text-charcoal">{total.toLocaleString()}</span> entries
          </div>

          <div className="flex items-center gap-1">
            <button
              onClick={() => setPage(1)}
              disabled={page <= 1 || loading}
              className="p-1.5 border border-[#EAEAEA] rounded-lg hover:bg-white disabled:opacity-30 disabled:cursor-not-allowed transition"
              title="First page"
            >
              <ChevronsLeft className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page <= 1 || loading}
              className="p-1.5 border border-[#EAEAEA] rounded-lg hover:bg-white disabled:opacity-30 disabled:cursor-not-allowed transition"
              title="Previous page"
            >
              <ChevronLeft className="w-3.5 h-3.5" />
            </button>

            {getPageNumbers().map((pNum) => (
              <button
                key={pNum}
                onClick={() => setPage(pNum)}
                disabled={loading}
                className={`w-7 h-7 rounded-lg text-xs font-semibold transition ${
                  pNum === page
                    ? 'bg-charcoal text-white shadow-subtle'
                    : 'border border-[#EAEAEA] bg-white text-charcoal hover:bg-slate-50'
                }`}
              >
                {pNum}
              </button>
            ))}

            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages || loading}
              className="p-1.5 border border-[#EAEAEA] rounded-lg hover:bg-white disabled:opacity-30 disabled:cursor-not-allowed transition"
              title="Next page"
            >
              <ChevronRight className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => setPage(totalPages)}
              disabled={page >= totalPages || loading}
              className="p-1.5 border border-[#EAEAEA] rounded-lg hover:bg-white disabled:opacity-30 disabled:cursor-not-allowed transition"
              title="Last page"
            >
              <ChevronsRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
