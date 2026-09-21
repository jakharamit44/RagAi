import React, { useState, useEffect } from 'react';
import { adminApi } from '../../api/client';
import { Hash, CheckCircle2, RefreshCw, ShieldAlert, ShieldCheck } from 'lucide-react';

export default function ManifestTab() {
  const [entries, setEntries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('');
  const [verifying, setVerifying] = useState(false);

  const fetchManifest = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (statusFilter) params.append('status', statusFilter);
      const res = await adminApi.manifest.getEntries(params.toString());
      setEntries(res?.items || res || []);
    } catch (err) {
      console.error('Failed to load manifest:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchManifest();
  }, [statusFilter]);

  const handleVerify = async () => {
    setVerifying(true);
    try {
      const res = await adminApi.manifest.verifyIntegrity();
      alert(res.message || 'Cryptographic integrity verified.');
      fetchManifest();
    } catch (err) {
      alert(`Verification error: ${err.message}`);
    } finally {
      setVerifying(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white border border-[#EAEAEA] rounded-2xl p-6 shadow-subtle">
        <div>
          <div className="flex items-center gap-2">
            <Hash className="w-4 h-4 text-charcoal" />
            <h2 className="text-base font-bold text-charcoal">
              Cryptographic Ingestion Manifest
            </h2>
          </div>
          <p className="text-xs text-muted mt-1">
            SHA-256 integrity verification protecting against silent document corruption or drift.
          </p>
        </div>

        <div className="flex items-center gap-2 self-start">
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="px-3 py-1.5 bg-[#FBFBFA] border border-[#EAEAEA] rounded-xl text-xs"
          >
            <option value="">All Statuses</option>
            <option value="indexed">Indexed (Verified)</option>
            <option value="pending">Pending Scan</option>
            <option value="changed">Content Changed</option>
          </select>

          <button
            onClick={handleVerify}
            disabled={verifying}
            className="px-4 py-2 bg-charcoal text-white rounded-xl text-xs font-semibold flex items-center gap-1.5 disabled:opacity-50"
          >
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>{verifying ? 'Verifying...' : 'Verify Cryptographic Integrity'}</span>
          </button>
        </div>
      </div>

      <div className="bg-white border border-[#EAEAEA] rounded-2xl shadow-subtle overflow-hidden">
        <div className="px-6 py-4 border-b border-[#EAEAEA] flex items-center justify-between">
          <h3 className="text-xs font-bold uppercase tracking-wider text-muted">
            Manifest Log ({entries.length})
          </h3>
          <button onClick={fetchManifest} className="text-xs text-muted hover:text-charcoal flex items-center gap-1">
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Refresh</span>
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="bg-[#FBFBFA] border-b border-[#EAEAEA] text-[11px] font-semibold text-muted uppercase">
                <th className="py-3 px-6">File Path</th>
                <th className="py-3 px-6">SHA-256 Cryptographic Hash</th>
                <th className="py-3 px-6">File Size</th>
                <th className="py-3 px-6">Status</th>
                <th className="py-3 px-6 text-right">Last Verified</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#EAEAEA]">
              {loading ? (
                <tr>
                  <td colSpan={5} className="py-8 text-center text-muted">Loading manifest...</td>
                </tr>
              ) : entries.length === 0 ? (
                <tr>
                  <td colSpan={5} className="py-8 text-center text-muted">No manifest entries recorded.</td>
                </tr>
              ) : (
                entries.map((item) => (
                  <tr key={item.id} className="hover:bg-slate-50">
                    <td className="py-3 px-6 font-mono font-medium text-charcoal">{item.path}</td>
                    <td className="py-3 px-6 font-mono text-[11px] text-muted">
                      {item.file_hash ? `${item.file_hash.substring(0, 18)}...` : '—'}
                    </td>
                    <td className="py-3 px-6 font-mono">
                      {item.file_size ? `${(item.file_size / 1024).toFixed(1)} KB` : '—'}
                    </td>
                    <td className="py-3 px-6">
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-pastel-green text-pastel-greenText uppercase">
                        {item.status || 'verified'}
                      </span>
                    </td>
                    <td className="py-3 px-6 text-right font-mono text-[11px] text-muted">
                      {item.updated_at ? new Date(item.updated_at).toLocaleDateString() : '—'}
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
