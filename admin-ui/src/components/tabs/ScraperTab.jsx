import React, { useState, useEffect, useRef } from 'react';
import { adminApi } from '../../api/client';
import {
  Globe,
  Play,
  Square,
  RefreshCw,
  Trash2,
  Link as LinkIcon,
  CheckCircle2,
  AlertCircle,
  FileText,
  Layers,
  Database,
  Terminal,
  Activity,
  ExternalLink,
  Clock,
  Radio,
  Sliders,
  Sparkles
} from 'lucide-react';

export default function ScraperTab() {
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [singleUrl, setSingleUrl] = useState('');
  const [dept, setDept] = useState('Computer Science');
  const [crawlingSingle, setCrawlingSingle] = useState(false);
  const [cleaning, setCleaning] = useState(false);

  // Live Crawler Telemetry State
  const [crawlerStatus, setCrawlerStatus] = useState({
    is_running: false,
    current_job_id: null,
    job_name: '',
    current_url: '',
    stats: {},
    activity_logs: [],
  });

  // Terminal Controls
  const [autoScroll, setAutoScroll] = useState(true);
  const terminalEndRef = useRef(null);

  // Fetch status and jobs
  const fetchCrawlerStatus = async () => {
    try {
      const data = await adminApi.scraper.getStatus();
      if (data && typeof data === 'object') {
        setCrawlerStatus(data);
      }
    } catch (err) {
      console.warn('Status poll note:', err);
    }
  };

  const fetchJobs = async () => {
    setLoading(true);
    try {
      const [jobsData, statusData] = await Promise.allSettled([
        adminApi.scraper.getJobs(),
        adminApi.scraper.getStatus(),
      ]);

      if (jobsData.status === 'fulfilled') {
        const d = jobsData.value;
        setJobs(Array.isArray(d) ? d : d?.jobs || []);
      }
      if (statusData.status === 'fulfilled' && statusData.value) {
        setCrawlerStatus(statusData.value);
      }
    } catch (err) {
      console.error('Failed to load scraper data:', err);
      setJobs([]);
    } finally {
      setLoading(false);
    }
  };

  // Initial load and adaptive polling (2.5s if running, 8s if idle)
  useEffect(() => {
    fetchJobs();
  }, []);

  useEffect(() => {
    const intervalMs = crawlerStatus.is_running ? 2500 : 8000;
    const timer = setInterval(() => {
      fetchCrawlerStatus();
    }, intervalMs);
    return () => clearInterval(timer);
  }, [crawlerStatus.is_running]);

  // Terminal autoscroll
  useEffect(() => {
    if (autoScroll && terminalEndRef.current) {
      terminalEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [crawlerStatus.activity_logs, autoScroll]);

  const handleRunJob = async (jobId) => {
    try {
      await adminApi.scraper.runJob(jobId);
      await fetchJobs();
    } catch (err) {
      alert(`Run error: ${err.message}`);
    }
  };

  const handleStop = async () => {
    try {
      await adminApi.scraper.stopJob();
      await fetchJobs();
    } catch (err) {
      alert(`Stop error: ${err.message}`);
    }
  };

  const handleCrawlSingle = async (e) => {
    e.preventDefault();
    if (!singleUrl.trim()) return;
    setCrawlingSingle(true);
    try {
      await adminApi.scraper.crawlSingle(singleUrl.trim(), dept, '1', 'Web Gazette');
      alert('URL ingested successfully into RAG corpus.');
      setSingleUrl('');
      fetchJobs();
    } catch (err) {
      alert(`Crawl failed: ${err.message}`);
    } finally {
      setCrawlingSingle(false);
    }
  };

  const handleCleanup = async () => {
    if (!window.confirm('Safely clean orphaned temporary scraper files?')) return;
    setCleaning(true);
    try {
      const res = await adminApi.scraper.cleanupTemp();
      alert(res.message || 'Scraper temp files cleaned.');
    } catch (err) {
      alert(`Cleanup error: ${err.message}`);
    } finally {
      setCleaning(false);
    }
  };

  const stats = crawlerStatus.stats || {};
  const isRunning = Boolean(crawlerStatus.is_running);

  // Compute batch progress
  const batchProcessed = stats.batch_urls_processed || 0;
  const batchSize = stats.batch_size || 50;
  const batchPercent = Math.min(100, Math.round((batchProcessed / (batchSize || 1)) * 100));

  return (
    <div className="space-y-6">
      {/* 1. Live Crawler HUD / Active Target Banner */}
      <div className="bg-white border border-[#EAEAEA] rounded-2xl p-6 shadow-subtle space-y-5">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className={`w-3.5 h-3.5 rounded-full flex items-center justify-center ${isRunning ? 'bg-emerald-500 ring-4 ring-emerald-100 animate-pulse' : 'bg-slate-300'}`} />
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-sm font-bold text-charcoal">
                  {isRunning ? 'Live Continuous Crawler Active' : 'Crawler Engine Standby'}
                </h3>
                <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold uppercase tracking-wider ${isRunning ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-100 text-slate-600'}`}>
                  {isRunning ? 'Running' : 'Idle'}
                </span>
              </div>
              <p className="text-xs text-muted mt-0.5">
                {crawlerStatus.job_name ? `Target: ${crawlerStatus.job_name}` : 'MDU Rohtak Academic Portal & Gazette Discovery'}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {isRunning ? (
              <button
                onClick={handleStop}
                className="px-3.5 py-1.5 bg-red-50 hover:bg-red-100 border border-red-200 text-red-700 rounded-xl text-xs font-semibold flex items-center gap-1.5 transition-colors"
              >
                <Square className="w-3.5 h-3.5" />
                <span>Halt Active Crawler</span>
              </button>
            ) : (
              jobs.length > 0 && (
                <button
                  onClick={() => handleRunJob(jobs[0].id)}
                  className="px-3.5 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-semibold flex items-center gap-1.5 shadow-sm transition-colors"
                >
                  <Play className="w-3.5 h-3.5 fill-current" />
                  <span>Resume Crawl Run</span>
                </button>
              )
            )}
            <button
              onClick={fetchJobs}
              className="p-1.5 text-muted hover:text-charcoal hover:bg-slate-50 border border-[#EAEAEA] rounded-xl transition-colors"
              title="Refresh Telemetry"
            >
              <RefreshCw className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>

        {/* Active URL Tracker */}
        {crawlerStatus.current_url && (
          <div className="bg-[#FBFBFA] border border-[#EAEAEA] rounded-xl p-3 flex items-center justify-between text-xs">
            <div className="flex items-center gap-2 min-w-0 pr-4">
              <Radio className="w-3.5 h-3.5 text-emerald-600 flex-shrink-0 animate-pulse" />
              <span className="text-muted font-medium flex-shrink-0">Active URL:</span>
              <span className="font-mono text-charcoal truncate" title={crawlerStatus.current_url}>
                {crawlerStatus.current_url}
              </span>
            </div>
            <a
              href={crawlerStatus.current_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-muted hover:text-charcoal flex-shrink-0 flex items-center gap-1 text-[11px]"
            >
              <span>Visit</span>
              <ExternalLink className="w-3 h-3" />
            </a>
          </div>
        )}

        {/* Continuous Batch Progress Bar */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between text-xs">
            <span className="font-semibold text-charcoal flex items-center gap-1.5">
              <Activity className="w-3.5 h-3.5 text-muted" />
              <span>Batch {stats.current_batch || 1} Progress: {batchProcessed} / {batchSize} URLs</span>
            </span>
            <span className="font-mono text-muted text-[11px]">
              {stats.queue_remaining ? `${stats.queue_remaining.toLocaleString()} URLs in queue` : 'Queue empty'}
            </span>
          </div>
          <div className="w-full bg-[#EAEAEA] rounded-full h-2 overflow-hidden">
            <div
              className={`h-full transition-all duration-500 rounded-full ${isRunning ? 'bg-emerald-500' : 'bg-slate-400'}`}
              style={{ width: `${batchPercent}%` }}
            />
          </div>
        </div>
      </div>

      {/* 2. Live Telemetry Bento Cards (4-Grid) */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="bg-white border border-[#EAEAEA] rounded-2xl p-4 shadow-subtle">
          <div className="flex items-center justify-between text-muted mb-1">
            <span className="text-[11px] font-semibold uppercase tracking-wider">Pages Scraped</span>
            <FileText className="w-4 h-4 text-emerald-600" />
          </div>
          <div className="text-2xl font-bold text-charcoal font-mono">
            {(stats.pages_scraped || 0).toLocaleString()}
          </div>
          <p className="text-[11px] text-muted mt-1">HTML & ASPX portals</p>
        </div>

        <div className="bg-white border border-[#EAEAEA] rounded-2xl p-4 shadow-subtle">
          <div className="flex items-center justify-between text-muted mb-1">
            <span className="text-[11px] font-semibold uppercase tracking-wider">Documents Ingested</span>
            <Layers className="w-4 h-4 text-blue-600" />
          </div>
          <div className="text-2xl font-bold text-charcoal font-mono">
            {(stats.documents_downloaded || 0).toLocaleString()}
          </div>
          <p className="text-[11px] text-muted mt-1">PDFs, Syllabi & Notices</p>
        </div>

        <div className="bg-white border border-[#EAEAEA] rounded-2xl p-4 shadow-subtle">
          <div className="flex items-center justify-between text-muted mb-1">
            <span className="text-[11px] font-semibold uppercase tracking-wider">Delta Skipped</span>
            <CheckCircle2 className="w-4 h-4 text-emerald-600" />
          </div>
          <div className="text-2xl font-bold text-charcoal font-mono">
            {(stats.skipped_unchanged || 0).toLocaleString()}
          </div>
          <p className="text-[11px] text-muted mt-1">Unchanged 304 / SHA-256</p>
        </div>

        <div className="bg-white border border-[#EAEAEA] rounded-2xl p-4 shadow-subtle">
          <div className="flex items-center justify-between text-muted mb-1">
            <span className="text-[11px] font-semibold uppercase tracking-wider">Queue Remaining</span>
            <Database className="w-4 h-4 text-purple-600" />
          </div>
          <div className="text-2xl font-bold text-charcoal font-mono">
            {(stats.queue_remaining || 0).toLocaleString()}
          </div>
          <p className="text-[11px] text-muted mt-1">Discovered URLs pending</p>
        </div>
      </div>

      {/* 3. Live Activity Stream / Terminal Console */}
      <div className="bg-[#18181B] border border-slate-800 rounded-2xl overflow-hidden shadow-subtle">
        <div className="px-5 py-3 border-b border-slate-800 flex items-center justify-between text-xs">
          <div className="flex items-center gap-2 text-slate-300 font-semibold font-mono">
            <Terminal className="w-4 h-4 text-emerald-400" />
            <span>Crawler Activity Stream</span>
            <span className="text-[10px] bg-slate-800 text-slate-400 px-2 py-0.5 rounded-full font-sans">
              {(crawlerStatus.activity_logs || []).length} events
            </span>
          </div>

          <div className="flex items-center gap-3 text-slate-400 text-[11px]">
            <label className="flex items-center gap-1.5 cursor-pointer hover:text-slate-200">
              <input
                type="checkbox"
                checked={autoScroll}
                onChange={(e) => setAutoScroll(e.target.checked)}
                className="rounded border-slate-700 bg-slate-800 text-emerald-500 focus:ring-0 w-3 h-3"
              />
              <span>Auto-scroll</span>
            </label>
          </div>
        </div>

        <div className="p-4 font-mono text-[11px] h-52 overflow-y-auto space-y-1.5 scrollbar-thin scrollbar-thumb-slate-700">
          {(crawlerStatus.activity_logs || []).length === 0 ? (
            <div className="text-slate-500 text-center py-16">
              No recent crawler logs. Start a crawl job to view real-time scraping telemetry.
            </div>
          ) : (
            crawlerStatus.activity_logs.map((log, idx) => (
              <div key={idx} className="flex items-start gap-2 leading-relaxed">
                <span className="text-slate-500 flex-shrink-0 select-none">[{log.timestamp}]</span>
                <span
                  className={`text-[9px] px-1.5 py-0.2 rounded font-bold uppercase flex-shrink-0 ${
                    log.level === 'error'
                      ? 'bg-red-950 text-red-400 border border-red-800'
                      : log.level === 'warning'
                      ? 'bg-amber-950 text-amber-400 border border-amber-800'
                      : 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                  }`}
                >
                  {log.level || 'info'}
                </span>
                <span className="text-slate-200 break-all">{log.message}</span>
              </div>
            ))
          )}
          <div ref={terminalEndRef} />
        </div>
      </div>

      {/* 4. Scheduled Crawl Targets Table */}
      <div className="bg-white border border-[#EAEAEA] rounded-2xl shadow-subtle overflow-hidden">
        <div className="px-6 py-4 border-b border-[#EAEAEA] flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Globe className="w-4 h-4 text-charcoal" />
            <h3 className="text-xs font-bold uppercase tracking-wider text-muted">
              Scheduled Crawl Targets ({jobs.length})
            </h3>
          </div>
          <button onClick={fetchJobs} className="text-xs text-muted hover:text-charcoal flex items-center gap-1">
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Refresh</span>
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="bg-[#FBFBFA] border-b border-[#EAEAEA] text-[11px] font-semibold text-muted uppercase">
                <th className="py-3 px-6">Job Name</th>
                <th className="py-3 px-6">Base Domain</th>
                <th className="py-3 px-6">Telemetry & Progress</th>
                <th className="py-3 px-6">Interval</th>
                <th className="py-3 px-6">Status</th>
                <th className="py-3 px-6 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#EAEAEA]">
              {loading ? (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-muted">Loading crawler jobs...</td>
                </tr>
              ) : jobs.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-muted">No scheduled jobs registered.</td>
                </tr>
              ) : (
                jobs.map((job) => {
                  const jStats = job.stats || {};
                  const isThisJobRunning = isRunning && crawlerStatus.current_job_id === job.id;

                  return (
                    <tr key={job.id} className="hover:bg-slate-50">
                      <td className="py-3 px-6">
                        <div className="font-bold text-charcoal">{job.name}</div>
                        <div className="text-[11px] text-muted">
                          {job.max_pages ? `Batch size: ${job.max_pages} URLs` : 'Continuous crawl'}
                        </div>
                      </td>
                      <td className="py-3 px-6 font-mono text-[11px] text-muted">{job.base_url}</td>
                      <td className="py-3 px-6">
                        <div className="font-semibold text-charcoal">
                          {(jStats.pages_scraped || 0).toLocaleString()} pages · {(jStats.documents_downloaded || 0).toLocaleString()} docs
                        </div>
                        <div className="text-[11px] text-muted font-mono">
                          {jStats.total_urls_visited ? `Total visited: ${jStats.total_urls_visited.toLocaleString()}` : '0 visited'}
                        </div>
                      </td>
                      <td className="py-3 px-6 font-mono">{job.crawl_interval_minutes}m</td>
                      <td className="py-3 px-6">
                        <span
                          className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full font-semibold text-[11px] capitalize ${
                            isThisJobRunning || job.status === 'running'
                              ? 'bg-emerald-100 text-emerald-800'
                              : 'bg-slate-100 text-slate-700'
                          }`}
                        >
                          {(isThisJobRunning || job.status === 'running') && (
                            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                          )}
                          {isThisJobRunning ? 'Running' : job.status || 'idle'}
                        </span>
                      </td>
                      <td className="py-3 px-6 text-right">
                        {isThisJobRunning ? (
                          <button
                            onClick={handleStop}
                            className="p-1.5 rounded-lg border border-red-200 text-red-600 hover:bg-red-50"
                            title="Halt Crawler"
                          >
                            <Square className="w-3.5 h-3.5" />
                          </button>
                        ) : (
                          <button
                            onClick={() => handleRunJob(job.id)}
                            className="p-1.5 rounded-lg border border-slate-200 text-emerald-600 hover:bg-emerald-50"
                            title="Start Crawl"
                          >
                            <Play className="w-3.5 h-3.5 fill-current" />
                          </button>
                        )}
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* 5. Quick Single-URL Ingest & Operations Hygiene */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {/* Quick Ingest */}
        <div className="bg-white border border-[#EAEAEA] rounded-2xl p-6 shadow-subtle space-y-3">
          <div className="flex items-center gap-2">
            <LinkIcon className="w-4 h-4 text-charcoal" />
            <h3 className="text-sm font-bold text-charcoal">Quick Single-URL Ingest</h3>
          </div>
          <p className="text-xs text-muted">Directly scrape and vectorize a single MDU page or gazette PDF.</p>

          <form onSubmit={handleCrawlSingle} className="space-y-2.5">
            <input
              type="url"
              required
              value={singleUrl}
              onChange={(e) => setSingleUrl(e.target.value)}
              placeholder="https://mdu.ac.in/notice-123.pdf"
              className="w-full px-3 py-2 bg-white border border-[#EAEAEA] rounded-xl text-xs font-mono"
            />
            <div className="flex items-center justify-between">
              <select
                value={dept}
                onChange={(e) => setDept(e.target.value)}
                className="px-3 py-1.5 bg-[#FBFBFA] border border-[#EAEAEA] rounded-xl text-xs"
              >
                <option value="Computer Science">Computer Science</option>
                <option value="Law">Law</option>
                <option value="General">General / University-Wide</option>
              </select>
              <button
                type="submit"
                disabled={crawlingSingle}
                className="px-4 py-2 bg-charcoal text-white rounded-xl text-xs font-semibold disabled:opacity-50"
              >
                {crawlingSingle ? 'Crawling...' : 'Scrape & Ingest'}
              </button>
            </div>
          </form>
        </div>

        {/* Maintenance */}
        <div className="bg-white border border-[#EAEAEA] rounded-2xl p-6 shadow-subtle flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2">
              <Globe className="w-4 h-4 text-charcoal" />
              <h3 className="text-sm font-bold text-charcoal">Crawler Operations & Hygiene</h3>
            </div>
            <p className="text-xs text-muted mt-1">
              Stop running crawlers or purge temporary download caches after indexing.
            </p>
          </div>

          <div className="flex items-center gap-2 pt-4 border-t border-[#EAEAEA]">
            <button
              onClick={handleStop}
              className="px-3.5 py-2 border border-red-200 text-red-600 hover:bg-red-50 rounded-xl text-xs font-semibold flex items-center gap-1.5"
            >
              <Square className="w-3.5 h-3.5" />
              <span>Halt Active Crawler</span>
            </button>
            <button
              onClick={handleCleanup}
              disabled={cleaning}
              className="px-3.5 py-2 border border-[#EAEAEA] text-muted hover:text-charcoal hover:bg-slate-50 rounded-xl text-xs font-semibold flex items-center gap-1.5"
            >
              <Trash2 className="w-3.5 h-3.5" />
              <span>Clean Scraper Temp</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
