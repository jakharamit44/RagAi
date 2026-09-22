import React, { useState, useEffect } from 'react';
import { adminApi } from '../../api/client';
import {
  MessageSquare,
  Search,
  RefreshCw,
  Trash2,
  ThumbsUp,
  ThumbsDown,
  AlertTriangle,
  Sparkles,
  Bot,
  User,
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
  FileText,
  Clock,
  Zap,
  ShieldAlert,
  CheckCircle2,
  XCircle,
  Copy,
  Check,
  Filter,
  Layers,
  Award
} from 'lucide-react';

export default function ConversationsTab() {
  const [sessions, setSessions] = useState([]);
  const [selectedSessionId, setSelectedSessionId] = useState(null);
  const [sessionDetail, setSessionDetail] = useState(null);
  const [stats, setStats] = useState(null);
  const [loadingList, setLoadingList] = useState(true);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [loadingStats, setLoadingStats] = useState(true);
  const [error, setError] = useState(null);

  // Filters
  const [search, setSearch] = useState('');
  const [submittedSearch, setSubmittedSearch] = useState('');
  const [department, setDepartment] = useState('all');
  const [feedbackFilter, setFeedbackFilter] = useState('all');

  // Pagination
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(1);

  // Self-Improvement Cycle Execution State
  const [optimizing, setOptimizing] = useState(false);
  const [optimizationResult, setOptimizationResult] = useState(null);

  // Copy indicator
  const [copiedId, setCopiedId] = useState(null);

  // Purge Modal State
  const [showPurgeModal, setShowPurgeModal] = useState(false);
  const [purging, setPurging] = useState(false);

  // Load stats
  const fetchStats = async () => {
    try {
      setLoadingStats(true);
      const data = await adminApi.conversations.getStats();
      setStats(data);
    } catch (err) {
      console.warn('Failed to load conversation stats:', err);
    } finally {
      setLoadingStats(false);
    }
  };

  // Load session list
  const fetchSessions = async () => {
    setLoadingList(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      params.append('page', page.toString());
      params.append('page_size', pageSize.toString());
      if (submittedSearch.trim()) {
        params.append('search', submittedSearch.trim());
      }
      if (department && department !== 'all') {
        params.append('department', department);
      }
      if (feedbackFilter && feedbackFilter !== 'all') {
        params.append('feedback_filter', feedbackFilter);
      }

      const res = await adminApi.conversations.getSessions(params.toString());
      setSessions(res.items || []);
      setTotal(res.total || 0);
      setTotalPages(res.total_pages || 1);

      // Auto-select first session if none selected or current not in list
      if (res.items && res.items.length > 0) {
        if (!selectedSessionId || !res.items.some(s => s.session_id === selectedSessionId)) {
          setSelectedSessionId(res.items[0].session_id);
        }
      } else {
        setSelectedSessionId(null);
        setSessionDetail(null);
      }
    } catch (err) {
      setError(err.message || 'Failed to load conversations.');
    } finally {
      setLoadingList(false);
    }
  };

  // Load session detail
  const fetchSessionDetail = async (sessionId) => {
    if (!sessionId) {
      setSessionDetail(null);
      return;
    }
    setLoadingDetail(true);
    try {
      const res = await adminApi.conversations.getSessionDetail(sessionId);
      setSessionDetail(res);
    } catch (err) {
      console.warn('Failed to load session detail:', err);
    } finally {
      setLoadingDetail(false);
    }
  };

  useEffect(() => {
    fetchStats();
  }, []);

  useEffect(() => {
    fetchSessions();
  }, [page, pageSize, submittedSearch, department, feedbackFilter]);

  useEffect(() => {
    if (selectedSessionId) {
      fetchSessionDetail(selectedSessionId);
    }
  }, [selectedSessionId]);

  const handleSearchSubmit = (e) => {
    e.preventDefault();
    setPage(1);
    setSubmittedSearch(search);
  };

  const handleResetFilters = () => {
    setSearch('');
    setSubmittedSearch('');
    setDepartment('all');
    setFeedbackFilter('all');
    setPage(1);
  };

  const handleDeleteSession = async (sessionId, e) => {
    if (e) e.stopPropagation();
    if (!window.confirm(`Are you sure you want to delete session '${sessionId}' and all its messages?`)) {
      return;
    }
    try {
      await adminApi.conversations.deleteSession(sessionId);
      if (selectedSessionId === sessionId) {
        setSelectedSessionId(null);
      }
      fetchSessions();
      fetchStats();
    } catch (err) {
      alert(`Delete failed: ${err.message}`);
    }
  };

  const handlePurge = async (olderThanDays) => {
    try {
      setPurging(true);
      const res = await adminApi.conversations.purgeSessions({ older_than_days: olderThanDays });
      alert(`Purged ${res.purged_count} sessions.`);
      setShowPurgeModal(false);
      setSelectedSessionId(null);
      fetchSessions();
      fetchStats();
    } catch (err) {
      alert(`Purge failed: ${err.message}`);
    } finally {
      setPurging(false);
    }
  };

  const handleTriggerSelfImprovement = async () => {
    setOptimizing(true);
    setOptimizationResult(null);
    try {
      const res = await adminApi.conversations.optimizeFromFailures();
      setOptimizationResult(res.optimization_result || res);
      fetchStats();
    } catch (err) {
      alert(`Self-Improvement failed: ${err.message}`);
    } finally {
      setOptimizing(false);
    }
  };

  const copyToClipboard = (text, id) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  return (
    <div className="space-y-6">
      {/* HEADER SECTION */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-charcoal flex items-center gap-2">
            <MessageSquare className="w-5 h-5 text-indigo-600" />
            <span>Chat Session Persistence & Conversation Inspector</span>
          </h1>
          <p className="text-xs text-muted mt-1">
            Browse complete student & user conversation history, audit verified citations, track feedback ratings, and feed real failure cases into the AI Self-Improver.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => { fetchStats(); fetchSessions(); }}
            disabled={loadingList}
            className="flex items-center gap-1.5 px-3 py-2 text-xs font-semibold text-charcoal bg-white border border-[#EAEAEA] rounded-xl hover:bg-slate-50 transition shadow-subtle"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loadingList ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>

          <button
            onClick={() => setShowPurgeModal(true)}
            className="flex items-center gap-1.5 px-3 py-2 text-xs font-semibold text-rose-600 bg-rose-50 border border-rose-200 rounded-xl hover:bg-rose-100 transition shadow-subtle"
          >
            <Trash2 className="w-3.5 h-3.5" />
            <span>Purge Sessions</span>
          </button>

          <button
            onClick={handleTriggerSelfImprovement}
            disabled={optimizing}
            className="flex items-center gap-1.5 px-3.5 py-2 text-xs font-semibold text-white bg-indigo-600 rounded-xl hover:bg-indigo-700 transition shadow-subtle disabled:opacity-50"
          >
            <Sparkles className={`w-3.5 h-3.5 ${optimizing ? 'animate-spin' : ''}`} />
            <span>{optimizing ? 'Optimizing AI Prompt...' : 'Run AI Self-Improvement'}</span>
          </button>
        </div>
      </div>

      {/* TOP METRICS BENTO HUD */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white border border-[#EAEAEA] rounded-2xl p-4 shadow-subtle flex items-center justify-between">
          <div>
            <p className="text-[11px] font-semibold text-muted uppercase tracking-wider">Total Conversations</p>
            <h3 className="text-2xl font-bold text-charcoal mt-1">
              {loadingStats ? '...' : (stats?.total_sessions?.toLocaleString() || 0)}
            </h3>
            <p className="text-[10px] text-muted mt-0.5">Recorded user sessions</p>
          </div>
          <div className="p-3 bg-indigo-50 border border-indigo-100 rounded-xl text-indigo-600">
            <MessageSquare className="w-5 h-5" />
          </div>
        </div>

        <div className="bg-white border border-[#EAEAEA] rounded-2xl p-4 shadow-subtle flex items-center justify-between">
          <div>
            <p className="text-[11px] font-semibold text-muted uppercase tracking-wider">Total Exchanges</p>
            <h3 className="text-2xl font-bold text-charcoal mt-1">
              {loadingStats ? '...' : (stats?.total_messages?.toLocaleString() || 0)}
            </h3>
            <p className="text-[10px] text-muted mt-0.5">Prompt-response turns</p>
          </div>
          <div className="p-3 bg-slate-50 border border-[#EAEAEA] rounded-xl text-charcoal">
            <Layers className="w-5 h-5" />
          </div>
        </div>

        <div className="bg-white border border-[#EAEAEA] rounded-2xl p-4 shadow-subtle flex items-center justify-between">
          <div>
            <p className="text-[11px] font-semibold text-muted uppercase tracking-wider">User Satisfaction</p>
            <div className="flex items-baseline gap-1.5 mt-1">
              <h3 className="text-2xl font-bold text-emerald-600">
                {loadingStats ? '...' : `${stats?.satisfaction_rate_pct || 100}%`}
              </h3>
              <span className="text-[10px] font-medium text-muted">
                ({stats?.positive_feedback_count || 0} 👍 / {stats?.negative_feedback_count || 0} 👎)
              </span>
            </div>
            <p className="text-[10px] text-emerald-600 mt-0.5 font-medium">Positive feedback ratio</p>
          </div>
          <div className="p-3 bg-emerald-50 border border-emerald-100 rounded-xl text-emerald-600">
            <ThumbsUp className="w-5 h-5" />
          </div>
        </div>

        <div className="bg-white border border-[#EAEAEA] rounded-2xl p-4 shadow-subtle flex items-center justify-between">
          <div>
            <p className="text-[11px] font-semibold text-muted uppercase tracking-wider">Flagged for AI Training</p>
            <h3 className="text-2xl font-bold text-amber-600 mt-1">
              {loadingStats ? '...' : (stats?.low_confidence_count || 0)}
            </h3>
            <p className="text-[10px] text-amber-600 mt-0.5 font-medium">Low-confidence / Thumbs-down</p>
          </div>
          <div className="p-3 bg-amber-50 border border-amber-100 rounded-xl text-amber-600">
            <AlertTriangle className="w-5 h-5" />
          </div>
        </div>
      </div>

      {/* OPTIMIZATION RESULT BANNER */}
      {optimizationResult && (
        <div className="bg-gradient-to-r from-indigo-50 via-white to-purple-50 border border-indigo-200 rounded-2xl p-4 shadow-subtle">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-2.5">
              <div className="p-2 bg-indigo-600 text-white rounded-xl">
                <Sparkles className="w-4 h-4" />
              </div>
              <div>
                <h4 className="text-xs font-bold text-indigo-900">
                  Autonomous AI Self-Improvement Cycle Completed ({optimizationResult.status})
                </h4>
                <p className="text-xs text-slate-600 mt-0.5">
                  Harvested <b>{optimizationResult.harvested_count || 0}</b> real conversation failure queries from database.
                </p>
              </div>
            </div>
            <button
              onClick={() => setOptimizationResult(null)}
              className="text-xs text-slate-400 hover:text-slate-600"
            >
              ✕
            </button>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mt-3 pt-3 border-t border-indigo-100 text-xs">
            <div>
              <span className="text-slate-500 block text-[10px] uppercase font-semibold">Baseline Benchmark</span>
              <span className="font-mono font-bold text-slate-800">{optimizationResult.baseline_score}%</span>
            </div>
            <div>
              <span className="text-slate-500 block text-[10px] uppercase font-semibold">Mutated Benchmark</span>
              <span className="font-mono font-bold text-indigo-600">{optimizationResult.new_score}%</span>
            </div>
            <div>
              <span className="text-slate-500 block text-[10px] uppercase font-semibold">Decision Outcome</span>
              <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-bold ${
                optimizationResult.status === 'ACCEPTED' ? 'bg-emerald-100 text-emerald-800' : 'bg-slate-100 text-slate-700'
              }`}>
                {optimizationResult.status === 'ACCEPTED' ? '✓ Mutation Accepted & Deployed' : '↺ Mutation Rolled Back (Guarded)'}
              </span>
            </div>
          </div>

          {optimizationResult.mutation_applied && (
            <div className="mt-2.5 bg-white/80 p-2.5 rounded-xl border border-indigo-100 text-xs">
              <span className="font-semibold text-indigo-900">Applied Rule: </span>
              <span className="text-slate-700 italic">"{optimizationResult.mutation_applied}"</span>
            </div>
          )}
        </div>
      )}

      {/* FILTER TOOLBAR */}
      <div className="bg-white border border-[#EAEAEA] rounded-2xl p-4 shadow-subtle">
        <form onSubmit={handleSearchSubmit} className="flex flex-col md:flex-row items-center gap-3">
          <div className="relative flex-1 w-full">
            <Search className="w-4 h-4 text-muted absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search conversations by title, student question, or session ID..."
              className="w-full pl-9 pr-4 py-2 bg-slate-50 border border-[#EAEAEA] rounded-xl text-xs text-charcoal focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:bg-white transition"
            />
          </div>

          <div className="flex flex-wrap items-center gap-2 w-full md:w-auto">
            <select
              value={department}
              onChange={(e) => { setDepartment(e.target.value); setPage(1); }}
              className="px-3 py-2 bg-slate-50 border border-[#EAEAEA] rounded-xl text-xs text-charcoal focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="all">All Departments</option>
              {stats?.departments_breakdown && Object.keys(stats.departments_breakdown).map((dept) => (
                <option key={dept} value={dept}>{dept}</option>
              ))}
            </select>

            <select
              value={feedbackFilter}
              onChange={(e) => { setFeedbackFilter(e.target.value); setPage(1); }}
              className="px-3 py-2 bg-slate-50 border border-[#EAEAEA] rounded-xl text-xs text-charcoal focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="all">All Feedback Ratings</option>
              <option value="negative">👎 Thumbs Down (Needs Review)</option>
              <option value="low_confidence">⚠️ Low Confidence (&lt;70%)</option>
              <option value="positive">👍 Positive Rating</option>
            </select>

            <button
              type="submit"
              className="px-4 py-2 bg-charcoal text-white text-xs font-semibold rounded-xl hover:bg-black transition shadow-subtle"
            >
              Filter
            </button>

            {(submittedSearch || department !== 'all' || feedbackFilter !== 'all') && (
              <button
                type="button"
                onClick={handleResetFilters}
                className="px-3 py-2 bg-slate-100 text-slate-700 text-xs font-semibold rounded-xl hover:bg-slate-200 transition"
              >
                Reset
              </button>
            )}
          </div>
        </form>
      </div>

      {/* MASTER-DETAIL CONVERSATION WORKSPACE */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 min-h-[620px]">
        {/* LEFT COLUMN: SESSION LIST */}
        <div className="lg:col-span-5 bg-white border border-[#EAEAEA] rounded-2xl shadow-subtle flex flex-col overflow-hidden">
          <div className="p-3.5 border-b border-[#EAEAEA] bg-slate-50/50 flex items-center justify-between text-xs">
            <span className="font-bold text-charcoal flex items-center gap-1.5">
              <MessageSquare className="w-3.5 h-3.5 text-indigo-600" />
              <span>Conversation Threads</span>
              <span className="px-2 py-0.5 bg-slate-200 text-slate-700 rounded-full text-[10px]">
                {total}
              </span>
            </span>
            <span className="text-[11px] text-muted">
              Page {page} of {totalPages}
            </span>
          </div>

          <div className="flex-1 overflow-y-auto divide-y divide-[#EAEAEA] max-h-[580px]">
            {loadingList ? (
              <div className="p-8 text-center text-xs text-muted flex flex-col items-center justify-center gap-2">
                <RefreshCw className="w-4 h-4 animate-spin text-muted" />
                <span>Loading conversation sessions...</span>
              </div>
            ) : sessions.length === 0 ? (
              <div className="p-8 text-center text-xs text-muted">
                <MessageSquare className="w-8 h-8 mx-auto text-slate-300 mb-2" />
                <p className="font-semibold text-charcoal">No conversations found</p>
                <p className="mt-1">Queries from /chat or /api/v1/ask will appear here automatically.</p>
              </div>
            ) : (
              sessions.map((s) => {
                const isSelected = selectedSessionId === s.session_id;
                return (
                  <div
                    key={s.session_id}
                    onClick={() => setSelectedSessionId(s.session_id)}
                    className={`p-3.5 cursor-pointer transition border-l-4 ${
                      isSelected
                        ? 'bg-indigo-50/50 border-indigo-600'
                        : 'border-transparent hover:bg-slate-50/80'
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <h4 className="text-xs font-bold text-charcoal truncate flex-1" title={s.title}>
                        {s.title || `Chat ${s.session_id.substring(0, 10)}`}
                      </h4>
                      <button
                        onClick={(e) => handleDeleteSession(s.session_id, e)}
                        title="Delete session"
                        className="text-slate-400 hover:text-rose-600 p-1 rounded transition opacity-60 hover:opacity-100"
                      >
                        <Trash2 className="w-3 h-3" />
                      </button>
                    </div>

                    {s.last_message_preview && (
                      <p className="text-[11px] text-slate-500 line-clamp-1 mt-1 font-normal">
                        "{s.last_message_preview}"
                      </p>
                    )}

                    <div className="flex flex-wrap items-center gap-1.5 mt-2 text-[10px]">
                      <span className="px-1.5 py-0.5 bg-slate-100 text-slate-700 rounded font-medium">
                        {s.message_count} msgs
                      </span>
                      {s.department && (
                        <span className="px-1.5 py-0.5 bg-slate-100 text-slate-700 rounded truncate max-w-[110px]">
                          {s.department}
                        </span>
                      )}

                      {s.has_negative_feedback && (
                        <span className="px-1.5 py-0.5 bg-rose-100 text-rose-800 rounded font-bold flex items-center gap-0.5">
                          <ThumbsDown className="w-2.5 h-2.5" /> Thumbs Down
                        </span>
                      )}

                      {s.has_low_confidence && !s.has_negative_feedback && (
                        <span className="px-1.5 py-0.5 bg-amber-100 text-amber-800 rounded font-bold flex items-center gap-0.5">
                          <AlertTriangle className="w-2.5 h-2.5" /> Low Conf
                        </span>
                      )}

                      {s.feedback_score > 0 && (
                        <span className="px-1.5 py-0.5 bg-emerald-100 text-emerald-800 rounded font-bold flex items-center gap-0.5">
                          <ThumbsUp className="w-2.5 h-2.5" /> +{s.feedback_score}
                        </span>
                      )}

                      <span className="text-slate-400 ml-auto font-mono text-[9px]">
                        {s.created_at ? new Date(s.created_at).toLocaleDateString() : ''}
                      </span>
                    </div>
                  </div>
                );
              })
            )}
          </div>

          {/* LIST PAGINATION BAR */}
          <div className="p-3 border-t border-[#EAEAEA] bg-slate-50/50 flex items-center justify-between text-xs">
            <span className="text-muted text-[11px]">
              {total} Total Sessions
            </span>
            <div className="flex items-center gap-1">
              <button
                onClick={() => setPage(1)}
                disabled={page <= 1}
                className="p-1 rounded bg-white border border-[#EAEAEA] disabled:opacity-40 hover:bg-slate-50 transition"
              >
                <ChevronsLeft className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page <= 1}
                className="p-1 rounded bg-white border border-[#EAEAEA] disabled:opacity-40 hover:bg-slate-50 transition"
              >
                <ChevronLeft className="w-3.5 h-3.5" />
              </button>
              <span className="px-2 font-mono text-[11px] font-semibold text-charcoal">
                {page} / {totalPages}
              </span>
              <button
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                disabled={page >= totalPages}
                className="p-1 rounded bg-white border border-[#EAEAEA] disabled:opacity-40 hover:bg-slate-50 transition"
              >
                <ChevronRight className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={() => setPage(totalPages)}
                disabled={page >= totalPages}
                className="p-1 rounded bg-white border border-[#EAEAEA] disabled:opacity-40 hover:bg-slate-50 transition"
              >
                <ChevronsRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        </div>

        {/* RIGHT COLUMN: TRANSCRIPT DETAIL VIEWER */}
        <div className="lg:col-span-7 bg-white border border-[#EAEAEA] rounded-2xl shadow-subtle flex flex-col overflow-hidden">
          {!selectedSessionId ? (
            <div className="flex-1 flex flex-col items-center justify-center p-8 text-center text-muted">
              <MessageSquare className="w-12 h-12 text-slate-200 mb-3" />
              <h3 className="text-sm font-bold text-charcoal">No Session Selected</h3>
              <p className="text-xs text-muted max-w-sm mt-1">
                Select a conversation thread on the left to inspect student questions, verified citations, confidence meters, and feedback ratings.
              </p>
            </div>
          ) : loadingDetail ? (
            <div className="flex-1 flex flex-col items-center justify-center p-8 text-center text-muted gap-2">
              <RefreshCw className="w-5 h-5 animate-spin text-muted" />
              <span className="text-xs font-semibold">Loading transcript...</span>
            </div>
          ) : !sessionDetail ? (
            <div className="flex-1 flex flex-col items-center justify-center p-8 text-center text-muted">
              <p className="text-xs text-rose-600 font-semibold">Failed to load session details.</p>
            </div>
          ) : (
            <>
              {/* TRANSCRIPT HEADER */}
              <div className="p-4 border-b border-[#EAEAEA] bg-slate-50/50 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="text-sm font-bold text-charcoal truncate max-w-md">
                      {sessionDetail.session.title}
                    </h3>
                    {sessionDetail.session.has_negative_feedback && (
                      <span className="px-2 py-0.5 bg-rose-100 text-rose-800 rounded-full text-[10px] font-bold">
                        Thumbs Down Flagged
                      </span>
                    )}
                  </div>
                  <div className="flex flex-wrap items-center gap-2 mt-1 text-[11px] text-muted">
                    <span className="font-mono bg-white px-2 py-0.5 rounded border border-[#EAEAEA] flex items-center gap-1">
                      ID: {sessionDetail.session.session_id.substring(0, 14)}...
                      <button
                        onClick={() => copyToClipboard(sessionDetail.session.session_id, 'sess_id')}
                        className="hover:text-charcoal"
                      >
                        {copiedId === 'sess_id' ? <Check className="w-3 h-3 text-emerald-600" /> : <Copy className="w-3 h-3" />}
                      </button>
                    </span>
                    <span>User: <b>{sessionDetail.session.user_identifier}</b></span>
                    {sessionDetail.session.department && <span>Dept: <b>{sessionDetail.session.department}</b></span>}
                    {sessionDetail.session.created_at && (
                      <span>Time: {new Date(sessionDetail.session.created_at).toLocaleString()}</span>
                    )}
                  </div>
                </div>

                <div className="flex items-center gap-2 self-end sm:self-auto">
                  <button
                    onClick={() => handleDeleteSession(sessionDetail.session.session_id)}
                    className="flex items-center gap-1 px-2.5 py-1.5 text-xs text-rose-600 hover:bg-rose-50 rounded-lg border border-rose-200 transition"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                    <span>Delete</span>
                  </button>
                </div>
              </div>

              {/* TRANSCRIPT CHAT BUBBLES */}
              <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-5 max-h-[520px] bg-[#FBFBFA]/60">
                {sessionDetail.messages.length === 0 ? (
                  <div className="p-8 text-center text-xs text-muted">
                    No messages recorded in this session.
                  </div>
                ) : (
                  sessionDetail.messages.map((m) => {
                    const isUser = m.sender === 'user';
                    return (
                      <div
                        key={m.id}
                        className={`flex items-start gap-3 ${isUser ? 'justify-end' : 'justify-start'}`}
                      >
                        {!isUser && (
                          <div className="w-8 h-8 rounded-full bg-indigo-600 text-white flex items-center justify-center font-bold text-xs shrink-0 shadow-subtle">
                            AI
                          </div>
                        )}

                        <div className={`max-w-[85%] rounded-2xl p-4 text-xs leading-relaxed ${
                          isUser
                            ? 'bg-charcoal text-white rounded-tr-none shadow-subtle'
                            : 'bg-white border border-[#EAEAEA] text-charcoal rounded-tl-none shadow-subtle'
                        }`}>
                          {/* Message Body */}
                          <div className="whitespace-pre-wrap font-normal">
                            {m.content}
                          </div>

                          {/* Assistant Metadata Footers */}
                          {!isUser && (
                            <div className="mt-3 pt-3 border-t border-[#EAEAEA] space-y-2">
                              {/* Citations list */}
                              {m.citations && m.citations.length > 0 && (
                                <div>
                                  <span className="text-[10px] font-bold text-muted uppercase tracking-wider block mb-1.5 flex items-center gap-1">
                                    <FileText className="w-3 h-3 text-indigo-600" />
                                    <span>Verified Citations ({m.citations.length})</span>
                                  </span>
                                  <div className="space-y-1.5">
                                    {m.citations.map((c, idx) => (
                                      <div
                                        key={idx}
                                        className="bg-slate-50 border border-[#EAEAEA] rounded-xl p-2 text-[11px]"
                                      >
                                        <div className="flex items-center justify-between font-semibold text-charcoal">
                                          <span className="truncate max-w-[220px]">📄 {c.title || 'Course Material'}</span>
                                          <span className="text-[9px] font-mono bg-indigo-100 text-indigo-800 px-1.5 py-0.2 rounded">
                                            p. {c.page_number || 1}
                                          </span>
                                        </div>
                                        {c.snippet && (
                                          <p className="text-slate-600 text-[10px] italic mt-1 line-clamp-2">
                                            "{c.snippet}"
                                          </p>
                                        )}
                                      </div>
                                    ))}
                                  </div>
                                </div>
                              )}

                              {/* Performance & Quality Telemetry Badges */}
                              <div className="flex flex-wrap items-center gap-2 text-[10px] pt-1">
                                {m.latency_ms && (
                                  <span className="px-2 py-0.5 bg-slate-100 text-slate-700 rounded-md font-mono flex items-center gap-1">
                                    <Clock className="w-2.5 h-2.5" />
                                    <span>{m.latency_ms} ms</span>
                                  </span>
                                )}

                                {m.served_by && (
                                  <span className="px-2 py-0.5 bg-indigo-50 text-indigo-700 border border-indigo-200 rounded-md font-medium">
                                    {m.served_by === 'cache' ? '⚡ Semantic Cache Hit' : '🖥️ Local LLM (RTX 3060)'}
                                  </span>
                                )}

                                {m.confidence !== null && m.confidence !== undefined && (
                                  <span className={`px-2 py-0.5 rounded-md font-medium ${
                                    m.confidence >= 0.75
                                      ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                                      : 'bg-amber-50 text-amber-800 border border-amber-200'
                                  }`}>
                                    Confidence: {Math.round(m.confidence * 100)}%
                                  </span>
                                )}

                                {m.feedback && (
                                  <span className={`px-2 py-0.5 rounded-md font-bold flex items-center gap-1 ${
                                    m.feedback === 'up'
                                      ? 'bg-emerald-100 text-emerald-800'
                                      : 'bg-rose-100 text-rose-800'
                                  }`}>
                                    {m.feedback === 'up' ? <ThumbsUp className="w-2.5 h-2.5" /> : <ThumbsDown className="w-2.5 h-2.5" />}
                                    <span>Feedback: {m.feedback === 'up' ? 'Helpful' : 'Not Helpful'}</span>
                                  </span>
                                )}

                                {m.created_at && (
                                  <span className="text-muted ml-auto font-mono text-[9px]">
                                    {new Date(m.created_at).toLocaleTimeString()}
                                  </span>
                                )}
                              </div>
                            </div>
                          )}
                        </div>

                        {isUser && (
                          <div className="w-8 h-8 rounded-full bg-slate-200 text-slate-700 flex items-center justify-center font-bold text-xs shrink-0 shadow-subtle">
                            You
                          </div>
                        )}
                      </div>
                    );
                  })
                )}
              </div>
            </>
          )}
        </div>
      </div>

      {/* PURGE SESSIONS MODAL */}
      {showPurgeModal && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-xs flex items-center justify-center z-50 p-4">
          <div className="bg-white border border-[#EAEAEA] rounded-2xl max-w-md w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-charcoal flex items-center gap-2">
                <Trash2 className="w-4 h-4 text-rose-600" />
                <span>Purge Conversation History</span>
              </h3>
              <button
                onClick={() => setShowPurgeModal(false)}
                className="text-xs text-muted hover:text-charcoal"
              >
                ✕
              </button>
            </div>

            <p className="text-xs text-muted leading-relaxed">
              Purge old chat sessions to reclaim database storage. Deleted conversation messages cannot be recovered.
            </p>

            <div className="space-y-2 pt-2">
              <button
                onClick={() => handlePurge(30)}
                disabled={purging}
                className="w-full text-left px-4 py-2.5 bg-slate-50 hover:bg-slate-100 rounded-xl text-xs font-semibold text-charcoal border border-[#EAEAEA] transition flex items-center justify-between"
              >
                <span>Purge sessions older than 30 days</span>
                <span className="text-muted text-[10px]">Safe</span>
              </button>

              <button
                onClick={() => handlePurge(7)}
                disabled={purging}
                className="w-full text-left px-4 py-2.5 bg-slate-50 hover:bg-slate-100 rounded-xl text-xs font-semibold text-charcoal border border-[#EAEAEA] transition flex items-center justify-between"
              >
                <span>Purge sessions older than 7 days</span>
                <span className="text-muted text-[10px]">Moderate</span>
              </button>

              <button
                onClick={() => handlePurge(null)}
                disabled={purging}
                className="w-full text-left px-4 py-2.5 bg-rose-50 hover:bg-rose-100 rounded-xl text-xs font-semibold text-rose-700 border border-rose-200 transition flex items-center justify-between"
              >
                <span>Purge ALL conversation sessions (Factory Clean)</span>
                <span className="text-rose-600 text-[10px] font-bold">Destructive</span>
              </button>
            </div>

            <div className="pt-2 flex justify-end">
              <button
                onClick={() => setShowPurgeModal(false)}
                className="px-4 py-2 bg-slate-100 text-slate-700 rounded-xl text-xs font-semibold hover:bg-slate-200 transition"
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
