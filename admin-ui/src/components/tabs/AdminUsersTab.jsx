import React, { useState, useEffect } from 'react';
import { adminApi } from '../../api/client';
import { useAuth } from '../../context/AuthContext';
import { Users, UserPlus, Shield, CheckCircle2, XCircle, Trash2, Power, RefreshCw, AlertCircle } from 'lucide-react';
import CreateAdminModal from '../modals/CreateAdminModal';

export default function AdminUsersTab() {
  const { user: currentUser } = useAuth();
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [actionLoading, setActionLoading] = useState(null);

  const fetchUsers = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await adminApi.auth.getUsers();
      setUsers(data);
    } catch (err) {
      setError(err.message || 'Failed to fetch administrator accounts.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, []);

  const handleToggleStatus = async (user) => {
    if (user.username === currentUser?.username) {
      alert('You cannot deactivate your own account.');
      return;
    }

    const action = user.is_active ? 'deactivate' : 'activate';
    if (!window.confirm(`Are you sure you want to ${action} administrator '${user.username}'?`)) {
      return;
    }

    setActionLoading(user.id);
    try {
      await adminApi.auth.toggleUserStatus(user.id, !user.is_active);
      await fetchUsers();
    } catch (err) {
      alert(`Error toggling status: ${err.message}`);
    } finally {
      setActionLoading(null);
    }
  };

  const handleDelete = async (user) => {
    if (user.username === currentUser?.username) {
      alert('You cannot delete your own account.');
      return;
    }

    if (!window.confirm(`Permanently delete administrator account '${user.username}' (${user.email})? This action cannot be undone.`)) {
      return;
    }

    setActionLoading(user.id);
    try {
      await adminApi.auth.deleteUser(user.id);
      await fetchUsers();
    } catch (err) {
      alert(`Error deleting user: ${err.message}`);
    } finally {
      setActionLoading(null);
    }
  };

  const getRoleBadge = (role) => {
    switch (role) {
      case 'superadmin':
        return 'bg-pastel-purple text-pastel-purpleText border-[#D6BCFA]';
      case 'admin':
        return 'bg-pastel-blue text-pastel-blueText border-[#BEE3F8]';
      case 'auditor':
        return 'bg-pastel-yellow text-pastel-yellowText border-[#FFEBAA]';
      default:
        return 'bg-slate-100 text-slate-700 border-slate-200';
    }
  };

  return (
    <div className="space-y-6">
      {/* Header & Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white border border-[#EAEAEA] rounded-2xl p-6 shadow-subtle">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-charcoal text-white flex items-center justify-center">
              <Users className="w-4 h-4" />
            </div>
            <h2 className="text-base font-bold text-charcoal">
              Administrator Accounts & Multi-Tenant Governance
            </h2>
          </div>
          <p className="text-xs text-muted mt-1">
            Manage authorized staff identities, credential authentication, and RBAC authorization tiers.
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            onClick={fetchUsers}
            disabled={loading}
            className="px-3 py-2 border border-[#EAEAEA] rounded-xl text-xs font-semibold text-muted hover:text-charcoal hover:bg-slate-50 transition flex items-center gap-1.5"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>

          <button
            onClick={() => setIsCreateOpen(true)}
            className="px-4 py-2 bg-charcoal hover:bg-[#262626] text-white rounded-xl text-xs font-semibold shadow-subtle transition flex items-center gap-2"
          >
            <UserPlus className="w-3.5 h-3.5" />
            <span>Add Administrator</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="p-4 bg-pastel-red/60 border border-[#F5C2C7] rounded-2xl flex items-start gap-3 text-pastel-redText text-xs">
          <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
          <div>
            <span className="font-semibold">Error Loading Users:</span> {error}
          </div>
        </div>
      )}

      {/* Users Table */}
      <div className="bg-white border border-[#EAEAEA] rounded-2xl shadow-subtle overflow-hidden">
        <div className="px-6 py-4 border-b border-[#EAEAEA] flex items-center justify-between">
          <h3 className="text-xs font-bold uppercase tracking-wider text-muted">
            Registered Administrators ({users.length})
          </h3>
          <span className="text-[11px] text-muted">
            Salted PBKDF2-HMAC-SHA256 Multi-Admin Encryption
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="bg-[#FBFBFA] border-b border-[#EAEAEA] text-[11px] font-semibold text-muted uppercase tracking-wider">
                <th className="py-3 px-6">Administrator</th>
                <th className="py-3 px-6">Email Address</th>
                <th className="py-3 px-6">Role Tier</th>
                <th className="py-3 px-6">Status</th>
                <th className="py-3 px-6">Last Login</th>
                <th className="py-3 px-6">Created</th>
                <th className="py-3 px-6 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#EAEAEA]">
              {loading && users.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-12 text-center text-muted">
                    <RefreshCw className="w-5 h-5 animate-spin mx-auto mb-2 text-muted" />
                    <span>Loading administrator accounts...</span>
                  </td>
                </tr>
              ) : users.length === 0 ? (
                <tr>
                  <td colSpan={7} className="py-12 text-center text-muted">
                    No administrator accounts registered.
                  </td>
                </tr>
              ) : (
                users.map((u) => {
                  const isCurrent = u.username === currentUser?.username;
                  const isProcessing = actionLoading === u.id;

                  return (
                    <tr key={u.id} className="hover:bg-slate-50/70 transition">
                      <td className="py-3.5 px-6">
                        <div className="flex items-center gap-2.5">
                          <div className="w-7 h-7 rounded-lg bg-charcoal text-white flex items-center justify-center font-bold text-xs">
                            {u.username.charAt(0).toUpperCase()}
                          </div>
                          <div>
                            <div className="font-bold text-charcoal flex items-center gap-1.5">
                              <span>{u.username}</span>
                              {isCurrent && (
                                <span className="px-1.5 py-0.2 bg-pastel-blue text-pastel-blueText rounded-full text-[9px] font-bold">
                                  You
                                </span>
                              )}
                            </div>
                            <div className="text-[11px] text-muted">{u.full_name || '—'}</div>
                          </div>
                        </div>
                      </td>

                      <td className="py-3.5 px-6 font-mono text-[11px] text-charcoal">
                        {u.email}
                      </td>

                      <td className="py-3.5 px-6">
                        <span className={`inline-block px-2 py-0.5 rounded-full text-[10px] font-semibold border uppercase tracking-wider ${getRoleBadge(u.role)}`}>
                          {u.role}
                        </span>
                      </td>

                      <td className="py-3.5 px-6">
                        {u.is_active ? (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-pastel-green text-pastel-greenText border border-[#C3E6CB]">
                            <CheckCircle2 className="w-3 h-3" />
                            <span>Active</span>
                          </span>
                        ) : (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-pastel-red text-pastel-redText border border-[#F5C2C7]">
                            <XCircle className="w-3 h-3" />
                            <span>Deactivated</span>
                          </span>
                        )}
                      </td>

                      <td className="py-3.5 px-6 font-mono text-[11px] text-muted">
                        {u.last_login_at
                          ? new Date(u.last_login_at).toLocaleString()
                          : 'Never logged in'}
                      </td>

                      <td className="py-3.5 px-6 font-mono text-[11px] text-muted">
                        {new Date(u.created_at).toLocaleDateString()}
                      </td>

                      <td className="py-3.5 px-6 text-right">
                        <div className="inline-flex items-center gap-1.5">
                          <button
                            onClick={() => handleToggleStatus(u)}
                            disabled={isCurrent || isProcessing}
                            title={u.is_active ? 'Deactivate account' : 'Activate account'}
                            className={`p-1.5 rounded-lg border transition ${
                              u.is_active
                                ? 'text-amber-600 border-amber-200 hover:bg-amber-50'
                                : 'text-emerald-600 border-emerald-200 hover:bg-emerald-50'
                            } disabled:opacity-30 disabled:cursor-not-allowed`}
                          >
                            <Power className="w-3.5 h-3.5" />
                          </button>

                          <button
                            onClick={() => handleDelete(u)}
                            disabled={isCurrent || isProcessing}
                            title="Delete administrator account"
                            className="p-1.5 rounded-lg border border-red-200 text-red-600 hover:bg-red-50 transition disabled:opacity-30 disabled:cursor-not-allowed"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      <CreateAdminModal
        isOpen={isCreateOpen}
        onClose={() => setIsCreateOpen(false)}
        onCreated={fetchUsers}
      />
    </div>
  );
}
