import React, { useState, useEffect } from 'react';
import { adminApi } from '../../api/client';
import { Key, Plus, Copy, Check, Power, Trash2, RefreshCw, AlertCircle } from 'lucide-react';

export default function ApiKeysTab() {
  const [keys, setKeys] = useState([]);
  const [loading, setLoading] = useState(true);
  const [name, setName] = useState('');
  const [role, setRole] = useState('student');
  const [department, setDepartment] = useState('');
  const [rateLimit, setRateLimit] = useState(60);
  const [createdKey, setCreatedKey] = useState(null);
  const [copied, setCopied] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const fetchKeys = async () => {
    setLoading(true);
    try {
      const data = await adminApi.apiKeys.getKeys();
      setKeys(data || []);
    } catch (err) {
      console.error('Failed to load API keys:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchKeys();
  }, []);

  const handleCreate = async (e) => {
    e.preventDefault();
    if (!name.trim()) return;
    setSubmitting(true);
    try {
      const res = await adminApi.apiKeys.createKey({
        name: name.trim(),
        role,
        department: department.trim() || null,
        rate_limit: rateLimit,
      });
      setCreatedKey(res);
      setName('');
      fetchKeys();
    } catch (err) {
      alert(`Error creating key: ${err.message}`);
    } finally {
      setSubmitting(false);
    }
  };

  const handleToggle = async (key) => {
    try {
      await adminApi.apiKeys.toggleStatus(key.id, !key.is_active);
      fetchKeys();
    } catch (err) {
      alert(`Status toggle error: ${err.message}`);
    }
  };

  const handleDelete = async (keyId, keyName) => {
    if (!window.confirm(`Revoke and delete API Key '${keyName}'?`)) return;
    try {
      await adminApi.apiKeys.deleteKey(keyId);
      fetchKeys();
    } catch (err) {
      alert(`Delete error: ${err.message}`);
    }
  };

  const handleCopy = (text) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="space-y-6">
      {/* Create Key Card */}
      <div className="bg-white border border-[#EAEAEA] rounded-2xl p-6 shadow-subtle space-y-4">
        <div className="flex items-center gap-2 pb-3 border-b border-[#EAEAEA]">
          <Key className="w-4 h-4 text-charcoal" />
          <h3 className="text-sm font-bold text-charcoal">Issue Scoped Multi-Tenant API Key</h3>
        </div>

        {createdKey && (
          <div className="p-4 bg-pastel-green/50 border border-[#C3E6CB] rounded-xl text-xs space-y-2">
            <div className="font-bold text-pastel-greenText">API Key Generated Successfully:</div>
            <p className="text-[11px] text-muted">
              Copy this token immediately. For security, it will never be displayed again.
            </p>
            <div className="flex items-center gap-2">
              <input
                type="text"
                readOnly
                value={createdKey.raw_key || createdKey.api_key}
                className="flex-1 px-3 py-2 bg-white border border-[#C3E6CB] rounded-lg font-mono text-xs font-bold"
              />
              <button
                onClick={() => handleCopy(createdKey.raw_key || createdKey.api_key)}
                className="px-3 py-2 bg-charcoal text-white rounded-lg text-xs font-semibold flex items-center gap-1"
              >
                {copied ? <Check className="w-3.5 h-3.5" /> : <Copy className="w-3.5 h-3.5" />}
                <span>{copied ? 'Copied' : 'Copy'}</span>
              </button>
            </div>
          </div>
        )}

        <form onSubmit={handleCreate} className="space-y-3.5">
          <div className="grid grid-cols-1 sm:grid-cols-4 gap-3">
            <div>
              <label className="block text-xs font-semibold text-charcoal mb-1">Key Name</label>
              <input
                type="text"
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g. Student Mobile App"
                className="w-full px-3 py-2 bg-white border border-[#EAEAEA] rounded-xl text-xs"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-charcoal mb-1">RBAC Role</label>
              <select
                value={role}
                onChange={(e) => setRole(e.target.value)}
                className="w-full px-3 py-2 bg-white border border-[#EAEAEA] rounded-xl text-xs"
              >
                <option value="student">Student (Read/Ask)</option>
                <option value="faculty">Faculty (Course Scope)</option>
                <option value="admin">Administrator (Full Access)</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-charcoal mb-1">Department Scope</label>
              <input
                type="text"
                value={department}
                onChange={(e) => setDepartment(e.target.value)}
                placeholder="All or e.g. CSE"
                className="w-full px-3 py-2 bg-white border border-[#EAEAEA] rounded-xl text-xs"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-charcoal mb-1">
                Rate Limit ({rateLimit} req/min)
              </label>
              <input
                type="range"
                min="10"
                max="600"
                step="10"
                value={rateLimit}
                onChange={(e) => setRateLimit(parseInt(e.target.value))}
                className="w-full mt-2"
              />
            </div>
          </div>

          <div className="pt-2 flex justify-end">
            <button
              type="submit"
              disabled={submitting}
              className="px-4 py-2 bg-charcoal hover:bg-[#262626] text-white rounded-xl text-xs font-semibold transition disabled:opacity-50"
            >
              {submitting ? 'Generating...' : 'Create API Key'}
            </button>
          </div>
        </form>
      </div>

      {/* Keys Table */}
      <div className="bg-white border border-[#EAEAEA] rounded-2xl shadow-subtle overflow-hidden">
        <div className="px-6 py-4 border-b border-[#EAEAEA] flex items-center justify-between">
          <h3 className="text-xs font-bold uppercase tracking-wider text-muted">
            Active Multi-Tenant Keys ({keys.length})
          </h3>
          <button onClick={fetchKeys} className="text-xs text-muted hover:text-charcoal flex items-center gap-1">
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Refresh</span>
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="bg-[#FBFBFA] border-b border-[#EAEAEA] text-[11px] font-semibold text-muted uppercase">
                <th className="py-3 px-6">Key Name</th>
                <th className="py-3 px-6">Prefix</th>
                <th className="py-3 px-6">Role</th>
                <th className="py-3 px-6">Rate Limit</th>
                <th className="py-3 px-6">Status</th>
                <th className="py-3 px-6 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#EAEAEA]">
              {loading ? (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-muted">Loading API keys...</td>
                </tr>
              ) : keys.length === 0 ? (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-muted">No API keys registered.</td>
                </tr>
              ) : (
                keys.map((k) => (
                  <tr key={k.id} className="hover:bg-slate-50">
                    <td className="py-3 px-6 font-bold text-charcoal">{k.name}</td>
                    <td className="py-3 px-6 font-mono text-[11px] text-muted">{k.key_prefix}...</td>
                    <td className="py-3 px-6 uppercase text-[10px] font-semibold">{k.role}</td>
                    <td className="py-3 px-6 font-mono">{k.rate_limit} req/m</td>
                    <td className="py-3 px-6">
                      <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                        k.is_active ? 'bg-pastel-green text-pastel-greenText' : 'bg-pastel-red text-pastel-redText'
                      }`}>
                        {k.is_active ? 'Active' : 'Disabled'}
                      </span>
                    </td>
                    <td className="py-3 px-6 text-right">
                      <div className="inline-flex items-center gap-1.5">
                        <button
                          onClick={() => handleToggle(k)}
                          title="Toggle active status"
                          className="p-1.5 rounded-lg border border-slate-200 text-slate-700 hover:bg-slate-100"
                        >
                          <Power className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={() => handleDelete(k.id, k.name)}
                          title="Revoke key"
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
    </div>
  );
}
