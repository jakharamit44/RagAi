import React, { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import { adminApi } from '../../api/client';
import { Shield, KeyRound, LogOut, Activity, User, Server } from 'lucide-react';
import ChangePasswordModal from '../modals/ChangePasswordModal';

export default function Header() {
  const { user, logout } = useAuth();
  const [isPwModalOpen, setIsPwModalOpen] = useState(false);
  const [sourceTelemetry, setSourceTelemetry] = useState(null);

  useEffect(() => {
    let mounted = true;
    adminApi.migration.getSourceStatus()
      .then((data) => {
        if (mounted) setSourceTelemetry(data);
      })
      .catch(() => {});
    return () => { mounted = false; };
  }, []);

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
    <>
      <header className="sticky top-0 z-40 bg-white/90 backdrop-blur-md border-b border-[#EAEAEA]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            {/* Left: Branding */}
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-charcoal text-white flex items-center justify-center shadow-subtle">
                <Shield className="w-5 h-5 text-white" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <h1 className="text-sm font-bold tracking-tight text-charcoal">
                    MDU RAG AI
                  </h1>
                  <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase tracking-wider bg-pastel-blue text-pastel-blueText border border-[#BEE3F8]">
                    Enterprise Hub
                  </span>
                </div>
                <p className="text-[11px] text-muted font-medium">
                  Autonomous Multi-Source Academic Cognitive Infrastructure
                </p>
              </div>
            </div>

            {/* Right: Telemetry & Admin Profile */}
            <div className="flex items-center gap-3">
              {/* Telemetry pill */}
              {sourceTelemetry && (
                <div className="hidden md:flex items-center gap-2 px-3 py-1.5 bg-[#FBFBFA] border border-[#EAEAEA] rounded-xl text-xs">
                  <span className="flex h-2 w-2 relative">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                  </span>
                  <span className="font-mono text-charcoal text-[11px] font-medium">
                    VM: {sourceTelemetry.source_host || sourceTelemetry.host || sourceTelemetry.vector_store_host || '192.168.81.150'}
                  </span>
                  <span className="text-muted text-[11px]">&bull;</span>
                  <span className="text-muted text-[11px]">
                    {(sourceTelemetry.total_rows || sourceTelemetry.total_db_rows || 0).toLocaleString()} rows
                  </span>
                  <span className="text-muted text-[11px]">&bull;</span>
                  <span className="text-muted text-[11px]">
                    {(sourceTelemetry.qdrant_points_count || sourceTelemetry.total_vectors || 0).toLocaleString()} vectors
                  </span>
                </div>
              )}

              {/* Admin Profile & Actions */}
              {user && (
                <div className="flex items-center gap-2 pl-2 border-l border-[#EAEAEA]">
                  <div className="flex items-center gap-2 px-2.5 py-1 bg-[#FBFBFA] border border-[#EAEAEA] rounded-xl">
                    <div className="w-6 h-6 rounded-lg bg-charcoal text-white flex items-center justify-center text-xs font-bold">
                      {user.username.charAt(0).toUpperCase()}
                    </div>
                    <div className="text-left">
                      <div className="text-xs font-semibold text-charcoal leading-tight">
                        {user.username}
                      </div>
                      <span className={`inline-block px-1.5 py-0.2 rounded-full text-[9px] font-semibold border ${getRoleBadge(user.role)}`}>
                        {user.role}
                      </span>
                    </div>
                  </div>

                  <button
                    onClick={() => setIsPwModalOpen(true)}
                    title="Change Password"
                    className="p-2 text-muted hover:text-charcoal hover:bg-slate-100 rounded-xl border border-transparent hover:border-[#EAEAEA] transition"
                  >
                    <KeyRound className="w-4 h-4" />
                  </button>

                  <button
                    onClick={logout}
                    title="Sign Out"
                    className="p-2 text-muted hover:text-pastel-redText hover:bg-pastel-red/40 rounded-xl border border-transparent hover:border-[#F5C2C7] transition"
                  >
                    <LogOut className="w-4 h-4" />
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      </header>

      <ChangePasswordModal
        isOpen={isPwModalOpen}
        onClose={() => setIsPwModalOpen(false)}
      />
    </>
  );
}
