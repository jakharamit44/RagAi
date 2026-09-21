import React, { useState, useEffect } from 'react';
import { adminApi } from '../../api/client';
import { ShieldCheck, Plus, Trash2, Power, RefreshCw, CheckCircle2, XCircle } from 'lucide-react';

export default function FirewallTab() {
  const [rules, setRules] = useState([]);
  const [loading, setLoading] = useState(true);
  const [pattern, setPattern] = useState('');
  const [action, setAction] = useState('BLOCK');
  const [desc, setDesc] = useState('');
  const [testUrl, setTestUrl] = useState('');
  const [testResult, setTestResult] = useState(null);

  const fetchRules = async () => {
    setLoading(true);
    try {
      const data = await adminApi.firewall.getRules();
      setRules(data || []);
    } catch (err) {
      console.error('Failed to load rules:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchRules();
  }, []);

  const handleCreate = async (e) => {
    e.preventDefault();
    if (!pattern.trim()) return;
    try {
      await adminApi.firewall.createRule({
        pattern: pattern.trim(),
        action,
        description: desc.trim() || null,
      });
      setPattern('');
      setDesc('');
      fetchRules();
    } catch (err) {
      alert(`Create rule error: ${err.message}`);
    }
  };

  const handleToggle = async (rule) => {
    try {
      await adminApi.firewall.toggleStatus(rule.id, !rule.is_active);
      fetchRules();
    } catch (err) {
      alert(`Toggle status error: ${err.message}`);
    }
  };

  const handleDelete = async (ruleId) => {
    if (!window.confirm('Delete this firewall rule?')) return;
    try {
      await adminApi.firewall.deleteRule(ruleId);
      fetchRules();
    } catch (err) {
      alert(`Delete error: ${err.message}`);
    }
  };

  const handleTest = async (e) => {
    e.preventDefault();
    if (!testUrl.trim()) return;
    try {
      const res = await adminApi.firewall.testRule(testUrl.trim());
      setTestResult(res);
    } catch (err) {
      alert(`Test error: ${err.message}`);
    }
  };

  return (
    <div className="space-y-6">
      {/* Rule Creator */}
      <div className="bg-white border border-[#EAEAEA] rounded-2xl p-6 shadow-subtle space-y-4">
        <div className="flex items-center gap-2 pb-3 border-b border-[#EAEAEA]">
          <ShieldCheck className="w-4 h-4 text-charcoal" />
          <h3 className="text-sm font-bold text-charcoal">Define URL Security Firewall Rule</h3>
        </div>

        <form onSubmit={handleCreate} className="space-y-3">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div>
              <label className="block text-xs font-semibold text-charcoal mb-1">URL Match Pattern</label>
              <input
                type="text"
                required
                value={pattern}
                onChange={(e) => setPattern(e.target.value)}
                placeholder="e.g. *facebook.com* or *.exe"
                className="w-full px-3 py-2 bg-white border border-[#EAEAEA] rounded-xl text-xs font-mono"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-charcoal mb-1">Firewall Action</label>
              <select
                value={action}
                onChange={(e) => setAction(e.target.value)}
                className="w-full px-3 py-2 bg-white border border-[#EAEAEA] rounded-xl text-xs"
              >
                <option value="BLOCK">BLOCK (Reject & Log)</option>
                <option value="ALLOW">ALLOW (Bypass Inspection)</option>
                <option value="SCRAPE_ONLY">SCRAPE_ONLY (Crawler Allowed)</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-charcoal mb-1">Description</label>
              <input
                type="text"
                value={desc}
                onChange={(e) => setDesc(e.target.value)}
                placeholder="e.g. Block social media tracking"
                className="w-full px-3 py-2 bg-white border border-[#EAEAEA] rounded-xl text-xs"
              />
            </div>
          </div>

          <div className="pt-1 flex justify-end">
            <button
              type="submit"
              className="px-4 py-2 bg-charcoal hover:bg-[#262626] text-white rounded-xl text-xs font-semibold"
            >
              Add Security Rule
            </button>
          </div>
        </form>
      </div>

      {/* Rules Table */}
      <div className="bg-white border border-[#EAEAEA] rounded-2xl shadow-subtle overflow-hidden">
        <div className="px-6 py-4 border-b border-[#EAEAEA] flex items-center justify-between">
          <h3 className="text-xs font-bold uppercase tracking-wider text-muted">
            Active Security Rules ({rules.length})
          </h3>
          <button onClick={fetchRules} className="text-xs text-muted hover:text-charcoal flex items-center gap-1">
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Refresh</span>
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="bg-[#FBFBFA] border-b border-[#EAEAEA] text-[11px] font-semibold text-muted uppercase">
                <th className="py-3 px-6">Match Pattern</th>
                <th className="py-3 px-6">Action</th>
                <th className="py-3 px-6">Description</th>
                <th className="py-3 px-6">Status</th>
                <th className="py-3 px-6 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#EAEAEA]">
              {loading ? (
                <tr>
                  <td colSpan={5} className="py-8 text-center text-muted">Loading firewall rules...</td>
                </tr>
              ) : rules.length === 0 ? (
                <tr>
                  <td colSpan={5} className="py-8 text-center text-muted">No firewall rules defined.</td>
                </tr>
              ) : (
                rules.map((r) => (
                  <tr key={r.id} className="hover:bg-slate-50">
                    <td className="py-3 px-6 font-mono font-medium text-charcoal">{r.pattern}</td>
                    <td className="py-3 px-6">
                      <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                        r.action === 'BLOCK' ? 'bg-pastel-red text-pastel-redText' : 'bg-pastel-green text-pastel-greenText'
                      }`}>
                        {r.action}
                      </span>
                    </td>
                    <td className="py-3 px-6 text-muted">{r.description || '—'}</td>
                    <td className="py-3 px-6">
                      <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                        r.is_active ? 'bg-pastel-green text-pastel-greenText' : 'bg-pastel-red text-pastel-redText'
                      }`}>
                        {r.is_active ? 'Active' : 'Disabled'}
                      </span>
                    </td>
                    <td className="py-3 px-6 text-right">
                      <div className="inline-flex items-center gap-1.5">
                        <button
                          onClick={() => handleToggle(r)}
                          className="p-1.5 rounded-lg border border-slate-200 text-slate-700 hover:bg-slate-100"
                        >
                          <Power className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={() => handleDelete(r.id)}
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

      {/* Simulator */}
      <div className="bg-white border border-[#EAEAEA] rounded-2xl p-6 shadow-subtle space-y-3">
        <h4 className="text-xs font-bold text-charcoal uppercase tracking-wider">
          Firewall Simulator & URL Rule Evaluator
        </h4>
        <form onSubmit={handleTest} className="flex gap-2">
          <input
            type="text"
            value={testUrl}
            onChange={(e) => setTestUrl(e.target.value)}
            placeholder="Enter URL to test (e.g. https://mdu.ac.in/notice.pdf)..."
            className="flex-1 px-3 py-2 bg-white border border-[#EAEAEA] rounded-xl text-xs font-mono"
          />
          <button
            type="submit"
            className="px-4 py-2 bg-charcoal text-white rounded-xl text-xs font-semibold"
          >
            Evaluate
          </button>
        </form>

        {testResult && (
          <div className="p-3 bg-[#FBFBFA] border border-[#EAEAEA] rounded-xl text-xs font-mono space-y-1">
            <div>Outcome: <strong className={testResult.allowed ? 'text-emerald-600' : 'text-red-600'}>{testResult.allowed ? 'ALLOWED' : 'BLOCKED'}</strong></div>
            <div className="text-[11px] text-muted">Matched Rule: {testResult.matched_rule?.pattern || 'Default policy'}</div>
          </div>
        )}
      </div>
    </div>
  );
}
