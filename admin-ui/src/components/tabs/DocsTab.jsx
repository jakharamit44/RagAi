import React, { useState, useEffect } from 'react';
import { adminApi } from '../../api/client';
import { FileText, Search, Trash2, Eye, RefreshCw, AlertCircle, Layers } from 'lucide-react';

export default function DocsTab() {
  const [docs, setDocs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [department, setDepartment] = useState('');
  const [selectedDocChunks, setSelectedDocChunks] = useState(null);
  const [loadingChunks, setLoadingChunks] = useState(false);

  const fetchDocs = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (search) params.append('query', search);
      if (department) params.append('department', department);
      const res = await adminApi.docs.getDocuments(params.toString());
      setDocs(res?.items || res || []);
    } catch (err) {
      console.error('Failed to load documents:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDocs();
  }, [department]);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    fetchDocs();
  };

  const handleViewChunks = async (doc) => {
    setSelectedDocChunks({ doc, chunks: [] });
    setLoadingChunks(true);
    try {
      const res = await adminApi.docs.getChunks(doc.id);
      setSelectedDocChunks({ doc, chunks: res || [] });
    } catch (err) {
      alert(`Failed to load chunks: ${err.message}`);
    } finally {
      setLoadingChunks(false);
    }
  };

  const handleDelete = async (docId, title) => {
    if (!window.confirm(`Delete document '${title}' and remove its vector embeddings?`)) return;
    try {
      await adminApi.docs.deleteDocument(docId);
      fetchDocs();
    } catch (err) {
      alert(`Delete failed: ${err.message}`);
    }
  };

  const handlePurgeAll = async () => {
    if (!window.confirm('DANGER: Purge all documents and clear vector collections?')) return;
    try {
      await adminApi.docs.purgeAll();
      fetchDocs();
      alert('All documents purged.');
    } catch (err) {
      alert(`Purge failed: ${err.message}`);
    }
  };

  return (
    <div className="space-y-6">
      {/* Search & Actions Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white border border-[#EAEAEA] rounded-2xl p-6 shadow-subtle">
        <form onSubmit={handleSearchSubmit} className="flex flex-1 items-center gap-2 max-w-md">
          <div className="relative w-full">
            <Search className="w-4 h-4 text-muted absolute left-3 top-2.5" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search document registry by name or path..."
              className="w-full pl-9 pr-3 py-2 bg-white border border-[#EAEAEA] rounded-xl text-xs text-charcoal focus:outline-none focus:border-charcoal"
            />
          </div>
          <button
            type="submit"
            className="px-3.5 py-2 bg-charcoal text-white rounded-xl text-xs font-semibold"
          >
            Search
          </button>
        </form>

        <div className="flex items-center gap-2 self-start">
          <select
            value={department}
            onChange={(e) => setDepartment(e.target.value)}
            className="px-3 py-2 bg-[#FBFBFA] border border-[#EAEAEA] rounded-xl text-xs text-charcoal"
          >
            <option value="">All Departments</option>
            <option value="Computer Science">Computer Science</option>
            <option value="Law">Law</option>
            <option value="Management">Management</option>
            <option value="Pharmacy">Pharmacy</option>
          </select>

          <button
            onClick={handlePurgeAll}
            className="px-3 py-2 border border-red-200 text-red-600 hover:bg-red-50 rounded-xl text-xs font-semibold"
          >
            Purge All
          </button>
        </div>
      </div>

      {/* Documents Table */}
      <div className="bg-white border border-[#EAEAEA] rounded-2xl shadow-subtle overflow-hidden">
        <div className="px-6 py-4 border-b border-[#EAEAEA] flex items-center justify-between">
          <h3 className="text-xs font-bold uppercase tracking-wider text-muted">
            Document Corpus Registry ({docs.length})
          </h3>
          <button onClick={fetchDocs} className="text-xs text-muted hover:text-charcoal flex items-center gap-1">
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Refresh</span>
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="bg-[#FBFBFA] border-b border-[#EAEAEA] text-[11px] font-semibold text-muted uppercase">
                <th className="py-3 px-6">Document Title / Path</th>
                <th className="py-3 px-6">Department</th>
                <th className="py-3 px-6">Chunks</th>
                <th className="py-3 px-6">Indexed At</th>
                <th className="py-3 px-6 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#EAEAEA]">
              {loading ? (
                <tr>
                  <td colSpan={5} className="py-8 text-center text-muted">Loading documents...</td>
                </tr>
              ) : docs.length === 0 ? (
                <tr>
                  <td colSpan={5} className="py-8 text-center text-muted">No documents found matching criteria.</td>
                </tr>
              ) : (
                docs.map((doc) => (
                  <tr key={doc.id} className="hover:bg-slate-50">
                    <td className="py-3 px-6">
                      <div className="font-bold text-charcoal">{doc.title || doc.filename || 'Untitled'}</div>
                      <div className="font-mono text-[11px] text-muted truncate max-w-sm">{doc.file_path || doc.path}</div>
                    </td>
                    <td className="py-3 px-6">{doc.department || '—'}</td>
                    <td className="py-3 px-6 font-mono font-semibold">{doc.chunk_count || doc.chunks?.length || 0}</td>
                    <td className="py-3 px-6 font-mono text-muted text-[11px]">
                      {doc.created_at ? new Date(doc.created_at).toLocaleDateString() : '—'}
                    </td>
                    <td className="py-3 px-6 text-right">
                      <div className="inline-flex items-center gap-1.5">
                        <button
                          onClick={() => handleViewChunks(doc)}
                          title="Inspect chunks"
                          className="p-1.5 rounded-lg border border-slate-200 text-slate-700 hover:bg-slate-100"
                        >
                          <Eye className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={() => handleDelete(doc.id, doc.title || doc.filename)}
                          title="Delete document"
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
                className="text-muted hover:text-charcoal font-bold text-base"
              >
                &times;
              </button>
            </div>

            <div className="flex-1 overflow-y-auto space-y-3 pr-2">
              {loadingChunks ? (
                <div className="py-12 text-center text-muted">Loading vector chunks...</div>
              ) : selectedDocChunks.chunks.length === 0 ? (
                <div className="py-12 text-center text-muted">No chunks found for this document.</div>
              ) : (
                selectedDocChunks.chunks.map((c, i) => (
                  <div key={i} className="p-3.5 bg-[#FBFBFA] border border-[#EAEAEA] rounded-xl text-xs space-y-1">
                    <div className="flex items-center justify-between text-[11px] text-muted font-mono">
                      <span>Chunk #{c.chunk_index ?? i + 1}</span>
                      <span>{c.char_count || c.content?.length || 0} chars</span>
                    </div>
                    <p className="text-charcoal leading-relaxed font-mono text-[11px] whitespace-pre-wrap">
                      {c.content || c.text}
                    </p>
                  </div>
                ))
              )}
            </div>

            <div className="pt-2 border-t border-[#EAEAEA] flex justify-end">
              <button
                onClick={() => setSelectedDocChunks(null)}
                className="px-4 py-1.5 bg-charcoal text-white rounded-xl text-xs font-semibold"
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
