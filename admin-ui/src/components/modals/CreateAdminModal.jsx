import React, { useState } from 'react';
import { adminApi } from '../../api/client';
import { UserPlus, X, AlertCircle, CheckCircle } from 'lucide-react';

export default function CreateAdminModal({ isOpen, onClose, onCreated }) {
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [fullName, setFullName] = useState('');
  const [role, setRole] = useState('admin');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);

  if (!isOpen) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setSuccess(false);

    setLoading(true);
    try {
      const payload = {
        username: username.trim(),
        email: email.trim(),
        full_name: fullName.trim() || null,
        role,
        password,
      };
      await adminApi.auth.createUser(payload);
      setSuccess(true);
      setTimeout(() => {
        onClose();
        if (onCreated) onCreated();
      }, 1000);
    } catch (err) {
      setError(err.message || 'Failed to create administrator account.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-white border border-[#EAEAEA] rounded-2xl max-w-md w-full p-6 shadow-float animate-in fade-in duration-150">
        <div className="flex items-center justify-between pb-4 border-b border-[#EAEAEA]">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-pastel-green flex items-center justify-center text-pastel-greenText">
              <UserPlus className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-charcoal">Provision New Admin Account</h3>
              <p className="text-[11px] text-muted">Grant enterprise administrative authorization</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-muted hover:text-charcoal hover:bg-slate-100 transition"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {error && (
          <div className="mt-4 p-3 bg-pastel-red/60 border border-[#F5C2C7] rounded-xl flex items-start gap-2 text-pastel-redText text-xs">
            <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}

        {success && (
          <div className="mt-4 p-3 bg-pastel-green/60 border border-[#C3E6CB] rounded-xl flex items-center gap-2 text-pastel-greenText text-xs font-semibold">
            <CheckCircle className="w-4 h-4 shrink-0" />
            <span>Administrator successfully registered!</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="mt-4 space-y-3">
          <div>
            <label className="block text-xs font-semibold text-charcoal mb-1">
              Username <span className="text-red-500">*</span>
            </label>
            <input
              type="text"
              required
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="e.g. jdoe_admin"
              className="w-full px-3 py-2 bg-white border border-[#EAEAEA] rounded-xl text-xs font-medium text-charcoal focus:outline-none focus:border-charcoal focus:ring-1 focus:ring-charcoal"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-charcoal mb-1">
              Email Address <span className="text-red-500">*</span>
            </label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="e.g. jdoe@mdu.ac.in"
              className="w-full px-3 py-2 bg-white border border-[#EAEAEA] rounded-xl text-xs font-medium text-charcoal focus:outline-none focus:border-charcoal focus:ring-1 focus:ring-charcoal"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-charcoal mb-1">
              Full Name (Optional)
            </label>
            <input
              type="text"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              placeholder="e.g. Prof. John Doe"
              className="w-full px-3 py-2 bg-white border border-[#EAEAEA] rounded-xl text-xs font-medium text-charcoal focus:outline-none focus:border-charcoal focus:ring-1 focus:ring-charcoal"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-charcoal mb-1">
                Role Tier
              </label>
              <select
                value={role}
                onChange={(e) => setRole(e.target.value)}
                className="w-full px-3 py-2 bg-white border border-[#EAEAEA] rounded-xl text-xs font-medium text-charcoal focus:outline-none focus:border-charcoal focus:ring-1 focus:ring-charcoal"
              >
                <option value="admin">Administrator (Full Access)</option>
                <option value="superadmin">Superadmin (User & Infra Access)</option>
                <option value="auditor">Security Auditor (Read/Audit)</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-charcoal mb-1">
                Initial Password <span className="text-red-500">*</span>
              </label>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="At least 8 chars"
                className="w-full px-3 py-2 bg-white border border-[#EAEAEA] rounded-xl text-xs font-medium text-charcoal focus:outline-none focus:border-charcoal focus:ring-1 focus:ring-charcoal"
              />
            </div>
          </div>

          <p className="text-[11px] text-muted pt-1">
            New administrators will be marked with a <code>must_change_password</code> requirement on initial sign-in.
          </p>

          <div className="pt-3 flex items-center justify-end gap-2 border-t border-[#EAEAEA]">
            <button
              type="button"
              onClick={onClose}
              className="px-3 py-1.5 border border-[#EAEAEA] rounded-xl text-xs font-semibold text-muted hover:text-charcoal hover:bg-slate-50 transition"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-4 py-1.5 bg-charcoal hover:bg-[#262626] text-white rounded-xl text-xs font-semibold transition disabled:opacity-50"
            >
              {loading ? 'Creating...' : 'Create Admin ID'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
