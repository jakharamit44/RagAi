import React, { useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { Shield, Lock, User, Eye, EyeOff, AlertCircle, ArrowRight } from 'lucide-react';

export default function LoginView() {
  const { login } = useAuth();
  const [username, setUsername] = useState('admin');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!username.trim() || !password.trim()) {
      setError('Please enter both your username and password.');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      await login(username.trim(), password);
    } catch (err) {
      setError(err.message || 'Authentication failed. Please check credentials.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#FBFBFA] flex flex-col justify-center items-center px-4 py-12 selection:bg-slate-200">
      <div className="w-full max-w-md">
        {/* Brand Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-charcoal text-white shadow-subtle mb-4">
            <Shield className="w-7 h-7 text-white" />
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-charcoal">
            Enterprise Admin Hub
          </h1>
          <p className="text-xs font-medium text-muted mt-1.5 uppercase tracking-wider">
            Maharshi Dayanand University &bull; Cognitive AI Cortex
          </p>
        </div>

        {/* Login Card */}
        <div className="bg-white border border-[#EAEAEA] rounded-2xl p-8 shadow-subtle">
          <div className="mb-6">
            <h2 className="text-base font-semibold text-charcoal">Sign In to Admin Portal</h2>
            <p className="text-xs text-muted mt-1">
              Requires administrative credentials with multi-tenant RBAC privilege.
            </p>
          </div>

          {error && (
            <div className="mb-5 p-3.5 bg-pastel-red/60 border border-[#F5C2C7] rounded-xl flex items-start gap-2.5 text-pastel-redText text-xs leading-relaxed animate-in fade-in duration-200">
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
              <div>
                <span className="font-semibold">Authentication Failed:</span> {error}
              </div>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-charcoal mb-1.5">
                Admin Username or Email
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-muted">
                  <User className="w-4 h-4" />
                </div>
                <input
                  type="text"
                  required
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="admin or admin@mdu.ac.in"
                  className="w-full pl-9 pr-3 py-2.5 bg-white border border-[#EAEAEA] rounded-xl text-sm font-medium text-charcoal placeholder-muted/60 focus:outline-none focus:border-charcoal focus:ring-1 focus:ring-charcoal transition"
                />
              </div>
            </div>

            <div>
              <div className="flex items-center justify-between mb-1.5">
                <label className="block text-xs font-semibold text-charcoal">
                  Admin Password
                </label>
              </div>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-muted">
                  <Lock className="w-4 h-4" />
                </div>
                <input
                  type={showPassword ? 'text' : 'password'}
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter administrator password"
                  className="w-full pl-9 pr-10 py-2.5 bg-white border border-[#EAEAEA] rounded-xl text-sm font-medium text-charcoal placeholder-muted/60 focus:outline-none focus:border-charcoal focus:ring-1 focus:ring-charcoal transition"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute inset-y-0 right-0 pr-3 flex items-center text-muted hover:text-charcoal transition"
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            <div className="pt-2">
              <button
                type="submit"
                disabled={loading}
                className="w-full py-2.5 px-4 bg-charcoal hover:bg-[#262626] active:scale-[0.99] text-white rounded-xl text-xs font-semibold tracking-wide shadow-subtle transition flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? (
                  <span>Authenticating...</span>
                ) : (
                  <>
                    <span>Sign In Securely</span>
                    <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </button>
            </div>
          </form>

          <div className="mt-6 pt-5 border-t border-[#EAEAEA] text-center">
            <button
              type="button"
              onClick={() => {
                setUsername('admin');
                setPassword('Admin@MDU2026!');
              }}
              title="Click to fill default administrator credentials"
              className="inline-flex items-center gap-1.5 px-3 py-1 bg-pastel-yellow/60 hover:bg-pastel-yellow border border-[#FFEBAA] rounded-full text-[11px] text-pastel-yellowText font-medium transition cursor-pointer"
            >
              <span>Default Initial Setup:</span>
              <code className="font-bold">admin / Admin@MDU2026!</code>
            </button>
          </div>
        </div>

        {/* Security Notice Footer */}
        <p className="text-center text-[11px] text-muted mt-6 leading-relaxed">
          &copy; {new Date().getFullYear()} Maharshi Dayanand University &bull; Internal Administration Only.<br />
          All authentication attempts are cryptographically audited with OWASP PBKDF2-HMAC-SHA256.
        </p>
      </div>
    </div>
  );
}
