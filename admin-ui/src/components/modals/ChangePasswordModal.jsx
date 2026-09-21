import React, { useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { Lock, X, CheckCircle, AlertCircle, KeyRound } from 'lucide-react';

export default function ChangePasswordModal({ isOpen, onClose, onSuccess }) {
  const { changePassword } = useAuth();
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);

  if (!isOpen) return null;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setSuccessMsg(null);

    if (newPassword !== confirmPassword) {
      setError('New passwords do not match.');
      return;
    }

    if (newPassword === currentPassword) {
      setError('New password must be different from current password.');
      return;
    }

    setLoading(true);
    try {
      const res = await changePassword(currentPassword, newPassword);
      setSuccessMsg(res.message || 'Password changed successfully!');
      setTimeout(() => {
        onClose();
        if (onSuccess) onSuccess();
      }, 1200);
    } catch (err) {
      setError(err.message || 'Failed to change password.');
    } finally {
      setLoading(false);
    }
  };

  const hasLength = newPassword.length >= 8;
  const hasUpper = /[A-Z]/.test(newPassword);
  const hasLower = /[a-z]/.test(newPassword);
  const hasDigit = /[0-9]/.test(newPassword);
  const hasSpecial = /[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]/.test(newPassword);

  return (
    <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-white border border-[#EAEAEA] rounded-2xl max-w-md w-full p-6 shadow-float animate-in fade-in duration-150">
        <div className="flex items-center justify-between pb-4 border-b border-[#EAEAEA]">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-pastel-blue flex items-center justify-center text-pastel-blueText">
              <KeyRound className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-charcoal">Change Admin Password</h3>
              <p className="text-[11px] text-muted">Update your cryptographic access credentials</p>
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

        {successMsg && (
          <div className="mt-4 p-3 bg-pastel-green/60 border border-[#C3E6CB] rounded-xl flex items-center gap-2 text-pastel-greenText text-xs font-semibold">
            <CheckCircle className="w-4 h-4 shrink-0" />
            <span>{successMsg}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="mt-4 space-y-3.5">
          <div>
            <label className="block text-xs font-semibold text-charcoal mb-1">
              Current Password
            </label>
            <input
              type="password"
              required
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              placeholder="Enter current password"
              className="w-full px-3 py-2 bg-white border border-[#EAEAEA] rounded-xl text-xs font-medium text-charcoal focus:outline-none focus:border-charcoal focus:ring-1 focus:ring-charcoal"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-charcoal mb-1">
              New Password
            </label>
            <input
              type="password"
              required
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              placeholder="At least 8 chars, Aa1@..."
              className="w-full px-3 py-2 bg-white border border-[#EAEAEA] rounded-xl text-xs font-medium text-charcoal focus:outline-none focus:border-charcoal focus:ring-1 focus:ring-charcoal"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-charcoal mb-1">
              Confirm New Password
            </label>
            <input
              type="password"
              required
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder="Re-type new password"
              className="w-full px-3 py-2 bg-white border border-[#EAEAEA] rounded-xl text-xs font-medium text-charcoal focus:outline-none focus:border-charcoal focus:ring-1 focus:ring-charcoal"
            />
          </div>

          {/* Password Requirements Matrix */}
          <div className="p-3 bg-[#FBFBFA] border border-[#EAEAEA] rounded-xl space-y-1 text-[11px] text-muted">
            <div className="font-semibold text-charcoal mb-1">Security Standards:</div>
            <div className={`flex items-center gap-1.5 ${hasLength ? 'text-pastel-greenText font-medium' : ''}`}>
              <span>{hasLength ? '✓' : '•'}</span> At least 8 characters
            </div>
            <div className={`flex items-center gap-1.5 ${hasUpper && hasLower ? 'text-pastel-greenText font-medium' : ''}`}>
              <span>{hasUpper && hasLower ? '✓' : '•'}</span> Mixed case letters (A-Z & a-z)
            </div>
            <div className={`flex items-center gap-1.5 ${hasDigit ? 'text-pastel-greenText font-medium' : ''}`}>
              <span>{hasDigit ? '✓' : '•'}</span> At least one number (0-9)
            </div>
            <div className={`flex items-center gap-1.5 ${hasSpecial ? 'text-pastel-greenText font-medium' : ''}`}>
              <span>{hasSpecial ? '✓' : '•'}</span> At least one symbol (!@#$%^&*)
            </div>
          </div>

          <div className="pt-2 flex items-center justify-end gap-2 border-t border-[#EAEAEA]">
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
              {loading ? 'Updating...' : 'Update Password'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
