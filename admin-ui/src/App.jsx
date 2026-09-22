import React, { useState } from 'react';
import { useAuth } from './context/AuthContext';
import LoginView from './components/auth/LoginView';
import Header from './components/layout/Header';
import Navigation from './components/layout/Navigation';

import BrainTab from './components/tabs/BrainTab';
import ConversationsTab from './components/tabs/ConversationsTab';
import IngestTab from './components/tabs/IngestTab';
import PipelineTab from './components/tabs/PipelineTab';
import FailedTab from './components/tabs/FailedTab';
import DocsTab from './components/tabs/DocsTab';
import ApiKeysTab from './components/tabs/ApiKeysTab';
import FirewallTab from './components/tabs/FirewallTab';
import ScraperTab from './components/tabs/ScraperTab';
import ManifestTab from './components/tabs/ManifestTab';
import SecurityTab from './components/tabs/SecurityTab';
import DiagnosticsTab from './components/tabs/DiagnosticsTab';
import SettingsTab from './components/tabs/SettingsTab';
import MigrationTab from './components/tabs/MigrationTab';
import AdminUsersTab from './components/tabs/AdminUsersTab';
import { Shield, RefreshCw } from 'lucide-react';

export default function App() {
  const { isAuthenticated, loading } = useAuth();
  const [activeTab, setActiveTab] = useState('brain');

  if (loading) {
    return (
      <div className="min-h-screen bg-[#FBFBFA] flex flex-col items-center justify-center text-muted">
        <div className="w-12 h-12 rounded-2xl bg-charcoal text-white flex items-center justify-center shadow-subtle mb-4">
          <Shield className="w-6 h-6" />
        </div>
        <div className="flex items-center gap-2 text-xs font-semibold text-charcoal">
          <RefreshCw className="w-4 h-4 animate-spin text-muted" />
          <span>Verifying Administrator Security Session...</span>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <LoginView />;
  }

  const renderActiveTab = () => {
    switch (activeTab) {
      case 'brain':
        return <BrainTab />;
      case 'conversations':
        return <ConversationsTab />;
      case 'ingest':
        return <IngestTab />;
      case 'pipeline':
        return <PipelineTab />;
      case 'failed':
        return <FailedTab />;
      case 'docs':
        return <DocsTab />;
      case 'apikeys':
        return <ApiKeysTab />;
      case 'firewall':
        return <FirewallTab />;
      case 'scraper':
        return <ScraperTab />;
      case 'manifest':
        return <ManifestTab />;
      case 'security':
        return <SecurityTab />;
      case 'diagnostics':
        return <DiagnosticsTab />;
      case 'settings':
        return <SettingsTab />;
      case 'migration':
        return <MigrationTab />;
      case 'admins':
        return <AdminUsersTab />;
      default:
        return <BrainTab />;
    }
  };

  return (
    <div className="min-h-screen bg-[#FBFBFA] flex flex-col selection:bg-slate-200">
      <Header />
      <Navigation activeTab={activeTab} onSelectTab={setActiveTab} />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {renderActiveTab()}
      </main>

      <footer className="border-t border-[#EAEAEA] bg-white py-6 text-center text-xs text-muted">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-2">
          <span>
            Maharshi Dayanand University (MDU Rohtak) &bull; Enterprise Cognitive AI Architecture
          </span>
          <span className="font-mono text-[11px]">
            v1.2.0-enterprise &bull; Phase 10 React SPA
          </span>
        </div>
      </footer>
    </div>
  );
}
