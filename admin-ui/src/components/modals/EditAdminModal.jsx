import React, { useState, useEffect } from 'react';
import { adminApi } from '../../api/client';
import { Edit3, X, AlertCircle, CheckCircle2, KeyRound } from 'lucide-react';

export default function EditAdminModal({ isOpen, user, onClose, onUpdated }) {
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [role, setRole] = useState('admin');
  const [newPassword, setNewPassword] = useState('');
  const [isActive, setIsActive] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    if (user) {
      setFullName(user.full_name || '');
      setEmail(user.email || '');
      setRole(user.role || 'admin');
      setIsActive(user.is_active !== false);
      setNewPassword('');
      setError(null);
      setSuccess(false);
    }
  }, [user, isOpen]);

  if (!isOpen || !user) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setSuccess(false);

    if (!email.trim()) {
      setError('Email address is required.');
      return;
    }

    setLoading(true);
    try {
      const payload = {
        full_name: fullName.trim() || null,
        email: email.trim().toLowerCase(),
        role,
        is_active: isActive,
      };
      if (newPassword.trim()) {
        if (newPassword.length < 8) {
          throw new Error('Password must be at least 8 characters long.');
        }
        payload.password = newPassword;
      }

      await adminApi.auth.updateUser(user.id, payload);
      setSuccess(true);
      setTimeout(() => {
        onClose();
        if (onUpdated) onUpdated();
      }, 900);
    } catch (err) {
      setError(err.message || 'Failed to update administrator account.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-white border border-[#EAEAEA] rounded-2xl max-w-md w-full p-6 shadow-float animate-in fade-in duration-150">
        {/* Modal Header */}
        <div className="flex items-center justify-between pb-4 border-b border-[#EAEAEA]">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-charcoal text-white flex items-center justify-center">
              <Edit3 className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-charcoal">Edit Administrator Account</h3>
              <p className="text-[11px] text-muted">
                Modifying identity profile for <span className="font-mono font-bold text-charcoal">@{user.username}</span>
              </p>
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
            <CheckCircle2 className="w-4 h-4 shrink-0" />
            <span>Administrator profile updated successfully!</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="mt-4 space-y-3.5">
          <div>
            <label className="block text-xs font-semibold text-charcoal mb-1">
              Username (Immutable Identity)
            </label>
            <input
              type="text"
              disabled
              value={user.username}
              className="w-full px-3 py-2 bg-slate-50 border border-[#EAEAEA] rounded-xl text-xs font-mono text-muted cursor-not-allowed"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-charcoal mb-1">
              Full Name
            </label>
            <input
              type="text"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              placeholder="e.g. Prof. John Doe"
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
                <option value="superadmin">Superadmin (User & Infra)</option>
                <option value="auditor">Security Auditor (Read-Only)</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-charcoal mb-1">
                Account Status
              </label>
              <select
                value={isActive ? 'active' : 'inactive'}
                onChange={(e) => setIsActive(e.target.value === 'active')}
                className="w-full px-3 py-2 bg-white border border-[#EAEAEA] rounded-xl text-xs font-medium text-charcoal focus:outline-none focus:border-charcoal focus:ring-1 focus:ring-charcoal"
              >
                <option value="active">Active (Permitted)</option>
                <option value="inactive">Deactivated (Blocked)</option>
              </select>
            </div>
          </div>

          <div className="pt-1">
            <label className="block text-xs font-semibold text-charcoal mb-1 flex items-center gap-1.5">
              <KeyRound className="w-3.5 h-3.5 text-muted" />
              <span>Reset Password (Optional)</span>
            </label>
            <input
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              placeholder="Leave blank to keep existing password"
              className="w-full px-3 py-2 bg-white border border-[#EAEAEA] rounded-xl text-xs font-medium text-charcoal focus:outline-none focus:border-charcoal focus:ring-1 focus:ring-charcoal"
            />
            <p className="text-[11px] text-muted mt-1">
              Enter 8+ characters only if you want to reset this user's password.
            </p>
          </div>

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
              {loading ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
