/**
 * admin-ui/src/context/AuthContext.jsx
 * Global Authentication Context Provider for Enterprise Administration.
 */

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { adminApi, getStoredToken, setStoredToken } from '../api/client';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchProfile = useCallback(async () => {
    const token = getStoredToken();
    if (!token) {
      setUser(null);
      setLoading(false);
      return null;
    }

    try {
      const profile = await adminApi.auth.getMe();
      setUser(profile);
      setError(null);
      return profile;
    } catch (err) {
      console.warn('Failed to load admin profile, clearing token:', err.message);
      setStoredToken('');
      setUser(null);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchProfile();

    const handleSessionExpired = () => {
      setUser(null);
      setError('Session expired. Please sign in again.');
    };

    window.addEventListener('ragai-session-expired', handleSessionExpired);
    return () => {
      window.removeEventListener('ragai-session-expired', handleSessionExpired);
    };
  }, [fetchProfile]);

  const login = async (username, password) => {
    setError(null);
    try {
      const res = await adminApi.auth.login(username, password);
      setStoredToken(res.access_token);
      setUser(res.user);
      return res.user;
    } catch (err) {
      setError(err.message || 'Login failed');
      throw err;
    }
  };

  const logout = () => {
    setStoredToken('');
    setUser(null);
    setError(null);
  };

  const changePassword = async (currentPassword, newPassword) => {
    const res = await adminApi.auth.changePassword(currentPassword, newPassword);
    // Refresh profile to update must_change_password flag
    await fetchProfile();
    return res;
  };

  const value = {
    user,
    loading,
    error,
    isAuthenticated: !!user,
    login,
    logout,
    changePassword,
    refreshProfile: fetchProfile,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
