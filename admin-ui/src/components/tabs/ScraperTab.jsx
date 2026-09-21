import React, { useState, useEffect } from 'react';
import { adminApi } from '../../api/client';
import { Globe, Play, Square, RefreshCw, Trash2, Link, CheckCircle2, AlertCircle } from 'lucide-react';

export default function ScraperTab() {
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [singleUrl, setSingleUrl] = useState('');
  const [dept, setDept] = useState('Computer Science');
  const [crawlingSingle, setCrawlingSingle] = useState(false);
  const [cleaning, setCleaning] = useState(false);

  const fetchJobs = async () => {
    setLoading(true);
    try {
      const data = await adminApi.scraper.getJobs();
      setJobs(data || []);
    } catch (err) {
      console.error('Failed to load scraper jobs:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchJobs();
  }, []);

  const handleRunJob = async (jobId) => {
    try {
      await adminApi.scraper.runJob(jobId);
      alert('Crawler job triggered.');
      fetchJobs();
    } catch (err) {
      alert(`Run error: ${err.message}`);
    }
  };

  const handleStop = async () => {
    try {
      await adminApi.scraper.stopJob();
      alert('Crawler stopped.');
      fetchJobs();
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

  return (
    <div className="space-y-6">
      {/* Crawler Actions & Quick Ingest */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {/* Quick Ingest */}
        <div className="bg-white border border-[#EAEAEA] rounded-2xl p-6 shadow-subtle space-y-3">
          <div className="flex items-center gap-2">
            <Link className="w-4 h-4 text-charcoal" />
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

      {/* Scraper Jobs Table */}
      <div className="bg-white border border-[#EAEAEA] rounded-2xl shadow-subtle overflow-hidden">
        <div className="px-6 py-4 border-b border-[#EAEAEA] flex items-center justify-between">
          <h3 className="text-xs font-bold uppercase tracking-wider text-muted">
            Scheduled Crawl Targets ({jobs.length})
          </h3>
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
                <th className="py-3 px-6">Interval</th>
                <th className="py-3 px-6">Status</th>
                <th className="py-3 px-6 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#EAEAEA]">
              {loading ? (
                <tr>
                  <td colSpan={5} className="py-8 text-center text-muted">Loading crawler jobs...</td>
                </tr>
              ) : jobs.length === 0 ? (
                <tr>
                  <td colSpan={5} className="py-8 text-center text-muted">No scheduled jobs registered.</td>
                </tr>
              ) : (
                jobs.map((job) => (
                  <tr key={job.id} className="hover:bg-slate-50">
                    <td className="py-3 px-6 font-bold text-charcoal">{job.name}</td>
                    <td className="py-3 px-6 font-mono text-[11px] text-muted">{job.base_url}</td>
                    <td className="py-3 px-6 font-mono">{job.crawl_interval_minutes}m</td>
                    <td className="py-3 px-6 capitalize font-semibold">{job.status || 'idle'}</td>
                    <td className="py-3 px-6 text-right">
                      <button
                        onClick={() => handleRunJob(job.id)}
                        className="p-1.5 rounded-lg border border-slate-200 text-emerald-600 hover:bg-emerald-50"
                      >
                        <Play className="w-3.5 h-3.5" />
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
