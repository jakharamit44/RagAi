import React, { useState, useEffect } from 'react';
import { adminApi } from '../../api/client';
import {
  FileText,
  Search,
  Trash2,
  Eye,
  RefreshCw,
  AlertCircle,
  Layers,
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
  Filter,
  Sparkles,
  FileCode,
  CheckCircle2,
  HardDrive
} from 'lucide-react';

export default function DocsTab() {
  const [docs, setDocs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Search & Filter State
  const [search, setSearch] = useState('');
  const [submittedSearch, setSubmittedSearch] = useState('');
  const [department, setDepartment] = useState('');
  const [docType, setDocType] = useState('');

  // Server-Side Pagination State
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(1);

  // Chunks Inspection Modal
  const [selectedDocChunks, setSelectedDocChunks] = useState(null);
  const [loadingChunks, setLoadingChunks] = useState(false);
  const [deletingId, setDeletingId] = useState(null);

  const fetchDocs = async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      params.append('page', page.toString());
      params.append('page_size', pageSize.toString());
      if (submittedSearch.trim()) {
        params.append('search', submittedSearch.trim());
        params.append('query', submittedSearch.trim());
      }
      if (department && department !== 'all') {
        params.append('department', department);
      }
      if (docType && docType !== 'all') {
        params.append('doc_type', docType);
      }

      const res = await adminApi.docs.getDocuments(params.toString());

      if (res && typeof res === 'object' && Array.isArray(res.items)) {
        setDocs(res.items);
        setTotal(res.total || 0);
        setTotalPages(res.total_pages || 1);
      } else if (Array.isArray(res)) {
        setDocs(res);
        setTotal(res.length);
        setTotalPages(Math.max(1, Math.ceil(res.length / pageSize)));
      } else {
        setDocs([]);
        setTotal(0);
        setTotalPages(1);
      }
    } catch (err) {
      console.error('Failed to load documents:', err);
      setError(err.message || 'Failed to fetch registered documents.');
      setDocs([]);
      setTotal(0);
      setTotalPages(1);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDocs();
  }, [page, pageSize, department, docType, submittedSearch]);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    setPage(1);
    setSubmittedSearch(search);
  };

  const handleResetFilters = () => {
    setSearch('');
    setSubmittedSearch('');
    setDepartment('');
    setDocType('');
    setPage(1);
  };

  const handleViewChunks = async (doc) => {
    setSelectedDocChunks({ doc, chunks: [] });
    setLoadingChunks(true);
    try {
      const res = await adminApi.docs.getChunks(doc.id);
      setSelectedDocChunks({
        doc,
        chunks: Array.isArray(res) ? res : (res?.chunks || res?.items || []),
      });
    } catch (err) {
      alert(`Failed to load chunks: ${err.message}`);
    } finally {
      setLoadingChunks(false);
    }
  };

  const handleDelete = async (docId, title) => {
    if (!window.confirm(`Permanently delete document '${title}' and purge all corresponding vector embeddings?`)) {
      return;
    }
    setDeletingId(docId);
    try {
      await adminApi.docs.deleteDocument(docId);
      await fetchDocs();
    } catch (err) {
      alert(`Delete failed: ${err.message}`);
    } finally {
      setDeletingId(null);
    }
  };

  const handlePurgeAll = async () => {
    if (!window.confirm('CRITICAL ACTION: Are you sure you want to purge ALL indexed documents and vector collections? This action is irreversible.')) {
      return;
    }
    try {
      await adminApi.docs.purgeAll();
      setPage(1);
      fetchDocs();
      alert('All documents and vector collections have been purged successfully.');
    } catch (err) {
      alert(`Purge failed: ${err.message}`);
    }
  };

  const formatFileSize = (bytes) => {
    if (!bytes || bytes <= 0) return '—';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  // Pagination page range helper
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
                <FileText className="w-4 h-4" />
              </div>
              <div>
                <h2 className="text-base font-bold text-charcoal">
                  Document Corpus Registry & Vector Catalog
                </h2>
                <p className="text-xs text-muted">
                  Indexed academic course materials, curriculum syllabi, and administrative records.
                </p>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2.5 self-start">
            <button
              onClick={fetchDocs}
              disabled={loading}
              className="px-3 py-2 border border-[#EAEAEA] rounded-xl text-xs font-semibold text-muted hover:text-charcoal hover:bg-slate-50 transition flex items-center gap-1.5"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
              <span>Refresh</span>
            </button>

            <button
              onClick={handlePurgeAll}
              className="px-3.5 py-2 border border-red-200 text-red-600 hover:bg-red-50 rounded-xl text-xs font-semibold transition"
            >
              Purge All Corpus
            </button>
          </div>
        </div>

        {/* Filter Bar */}
        <div className="flex flex-wrap items-center gap-3 pt-2 border-t border-[#EAEAEA]">
          <form onSubmit={handleSearchSubmit} className="flex-1 min-w-[260px] flex items-center gap-2">
            <div className="relative flex-1">
              <Search className="w-4 h-4 text-muted absolute left-3 top-2.5" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search documents by title, department, course, or file path..."
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
              value={department}
              onChange={(e) => {
                setDepartment(e.target.value);
                setPage(1);
              }}
              className="px-3 py-2 bg-[#FBFBFA] border border-[#EAEAEA] rounded-xl text-xs text-charcoal focus:outline-none focus:border-charcoal"
            >
              <option value="">All Departments</option>
              <option value="Computer Science">Computer Science & AI</option>
              <option value="Law">Law & Legal Studies</option>
              <option value="Management">Management & Commerce</option>
              <option value="Pharmacy">Pharmacy & Health</option>
              <option value="Engineering">Engineering & Technology</option>
              <option value="General">General / Administrative</option>
            </select>

            <select
              value={docType}
              onChange={(e) => {
                setDocType(e.target.value);
                setPage(1);
              }}
              className="px-3 py-2 bg-[#FBFBFA] border border-[#EAEAEA] rounded-xl text-xs text-charcoal focus:outline-none focus:border-charcoal"
            >
              <option value="">All Formats</option>
              <option value="born_digital">Born-Digital Text</option>
              <option value="scanned">Scanned / OCR-Processed</option>
            </select>

            {(submittedSearch || department || docType) && (
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
          <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
          <div>
            <span className="font-semibold">Error Loading Corpus:</span> {error}
          </div>
        </div>
      )}

      {/* Documents Table */}
      <div className="bg-white border border-[#EAEAEA] rounded-2xl shadow-subtle overflow-hidden">
        <div className="px-6 py-4 border-b border-[#EAEAEA] flex items-center justify-between">
          <div className="flex items-center gap-2">
            <h3 className="text-xs font-bold uppercase tracking-wider text-muted">
              Corpus Files
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
                <th className="py-3 px-6">Document Title & Location</th>
                <th className="py-3 px-6">Academic Domain</th>
                <th className="py-3 px-6">Format & OCR</th>
                <th className="py-3 px-6">File Size</th>
                <th className="py-3 px-6">Vector Chunks</th>
                <th className="py-3 px-6">Indexed At</th>
                <th className="py-3 px-6 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#EAEAEA]">
              {loading ? (
                <tr>
                  <td colSpan={7} className="py-12 text-center text-muted">
                    <RefreshCw className="w-5 h-5 animate-spin mx-auto mb-2 text-muted" />
                    <span>Loading paginated documents...</span>
                  </td>
                </tr>
              ) : docs.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-12 text-center text-muted">
                    No documents found matching the search and filter criteria.
                  </td>
                </tr>
              ) : (
                docs.map((doc) => {
                  const isDeleting = deletingId === doc.id;
                  const docPath = doc.source_path || doc.file_path || doc.path || '';
                  const hasOcr = doc.ocr_applied || (doc.ocr_confidence !== null && doc.ocr_confidence !== undefined && doc.ocr_confidence > 0);

                  return (
                    <tr key={doc.id} className="hover:bg-slate-50/70 transition">
                      <td className="py-3.5 px-6 max-w-sm">
                        <div className="flex items-start gap-2.5">
                          <div className="w-7 h-7 rounded-lg bg-pastel-blue text-pastel-blueText flex items-center justify-center shrink-0 mt-0.5">
                            <FileText className="w-3.5 h-3.5" />
                          </div>
                          <div className="min-w-0">
                            <div className="font-bold text-charcoal truncate" title={doc.title || doc.filename}>
                              {doc.title || doc.filename || 'Untitled Document'}
                            </div>
                            {docPath && (
                              <div
                                className="font-mono text-[10px] text-muted truncate max-w-xs"
                                title={docPath}
                              >
                                {docPath}
                              </div>
                            )}
                          </div>
                        </div>
                      </td>

                      <td className="py-3.5 px-6">
                        <div className="space-y-1">
                          <span className="inline-block px-2 py-0.5 rounded-md text-[10px] font-semibold bg-pastel-purple text-pastel-purpleText border border-[#D6BCFA]">
                            {doc.department || 'General'}
                          </span>
                          {(doc.course || doc.semester) && (
                            <div className="text-[10px] text-muted font-mono">
                              {doc.course || 'Core'} {doc.semester && doc.semester !== 'All' ? `• Sem ${doc.semester}` : ''}
                            </div>
                          )}
                        </div>
                      </td>

                      <td className="py-3.5 px-6">
                        <div className="space-y-1">
                          <span className="inline-block px-2 py-0.5 rounded-md text-[10px] font-semibold bg-slate-100 text-slate-700 uppercase">
                            {doc.doc_type || 'Digital'}
                          </span>
                          {hasOcr ? (
                            <div className="text-[10px] text-emerald-700 flex items-center gap-1 font-mono">
                              <Sparkles className="w-3 h-3 text-emerald-500" />
                              <span>OCR: {Math.round((doc.ocr_confidence || 1.0) * 100)}%</span>
                            </div>
                          ) : (
                            <div className="text-[10px] text-muted font-mono">Native Text</div>
                          )}
                        </div>
                      </td>

                      <td className="py-3.5 px-6 font-mono text-[11px] text-muted">
                        {formatFileSize(doc.file_size_bytes || doc.file_size)}
                      </td>

                      <td className="py-3.5 px-6">
                        <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-[11px] font-mono font-bold bg-pastel-green text-pastel-greenText border border-[#C3E6CB]">
                          <Layers className="w-3 h-3" />
                          <span>{doc.chunk_count ?? doc.chunks?.length ?? 0}</span>
                        </span>
                      </td>

                      <td className="py-3.5 px-6 font-mono text-[11px] text-muted">
                        {doc.created_at ? new Date(doc.created_at).toLocaleDateString() : '—'}
                      </td>

                      <td className="py-3.5 px-6 text-right">
                        <div className="inline-flex items-center gap-1.5">
                          <button
                            onClick={() => handleViewChunks(doc)}
                            title="Inspect vector chunks"
                            className="p-1.5 rounded-lg border border-slate-200 text-slate-700 hover:bg-slate-100 hover:text-charcoal transition"
                          >
                            <Eye className="w-3.5 h-3.5" />
                          </button>
                          <button
                            onClick={() => handleDelete(doc.id, doc.title || doc.filename)}
                            disabled={isDeleting}
                            title="Delete document & vectors"
                            className="p-1.5 rounded-lg border border-red-200 text-red-600 hover:bg-red-50 transition disabled:opacity-40"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
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
            <span className="font-bold text-charcoal">{total.toLocaleString()}</span> documents
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

      {/* Chunks Inspection Modal */}
      {selectedDocChunks && (
        <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-white border border-[#EAEAEA] rounded-2xl max-w-2xl w-full p-6 shadow-float space-y-4 max-h-[85vh] flex flex-col">
            <div className="flex items-center justify-between pb-3 border-b border-[#EAEAEA]">
              <div>
                <h3 className="text-sm font-bold text-charcoal">
                  Chunks Inspector: {selectedDocChunks.doc.title || selectedDocChunks.doc.filename}
                </h3>
                <p className="text-[11px] text-muted font-mono">{selectedDocChunks.doc.id}</p>
              </div>
              <button
                onClick={() => setSelectedDocChunks(null)}
                className="p-1 rounded-lg text-muted hover:text-charcoal hover:bg-slate-100 transition"
              >
                &times;
              </button>
            </div>

            <div className="flex-1 overflow-y-auto space-y-3 pr-2">
              {loadingChunks ? (
                <div className="py-12 text-center text-muted">
                  <RefreshCw className="w-5 h-5 animate-spin mx-auto mb-2 text-muted" />
                  <span>Loading vector chunks from index...</span>
                </div>
              ) : selectedDocChunks.chunks.length === 0 ? (
                <div className="py-12 text-center text-muted">
                  No chunks found for this document.
                </div>
              ) : (
                selectedDocChunks.chunks.map((c, i) => (
                  <div key={i} className="p-3.5 bg-[#FBFBFA] border border-[#EAEAEA] rounded-xl text-xs space-y-1.5">
                    <div className="flex items-center justify-between text-[11px] text-muted font-mono border-b border-[#EAEAEA] pb-1">
                      <span className="font-bold text-charcoal">Chunk #{c.chunk_index ?? i + 1}</span>
                      <span>{c.char_count || c.content?.length || c.text?.length || 0} characters</span>
                    </div>
                    <p className="text-charcoal leading-relaxed font-mono text-[11px] whitespace-pre-wrap max-h-48 overflow-y-auto">
                      {c.content || c.text}
                    </p>
                  </div>
                ))
              )}
            </div>

            <div className="pt-3 border-t border-[#EAEAEA] flex justify-end">
              <button
                onClick={() => setSelectedDocChunks(null)}
                className="px-4 py-1.5 bg-charcoal text-white rounded-xl text-xs font-semibold hover:bg-[#262626] transition"
              >
                Done
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
