import React from 'react';
import {
  Brain,
  FolderInput,
  Activity,
  AlertTriangle,
  FileText,
  Key,
  ShieldCheck,
  Globe,
  Hash,
  ShieldAlert,
  Stethoscope,
  Sliders,
  Server,
  Users,
} from 'lucide-react';

export const TABS = [
  { id: 'brain', label: 'Brain Cortex', icon: Brain, badge: 'Live' },
  { id: 'ingest', label: 'Ingest & Watchers', icon: FolderInput },
  { id: 'pipeline', label: 'Pipeline', icon: Activity },
  { id: 'failed', label: 'Failed DLQ', icon: AlertTriangle },
  { id: 'docs', label: 'Documents', icon: FileText },
  { id: 'apikeys', label: 'API Keys', icon: Key },
  { id: 'firewall', label: 'URL Firewall', icon: ShieldCheck },
  { id: 'scraper', label: 'Web Scraper', icon: Globe },
  { id: 'manifest', label: 'Manifest', icon: Hash },
  { id: 'security', label: 'Security SOC', icon: ShieldAlert },
  { id: 'diagnostics', label: 'Diagnostics Clinic', icon: Stethoscope },
  { id: 'settings', label: 'System & Models', icon: Sliders },
  { id: 'migration', label: 'Server Migration', icon: Server, badge: 'VM Sync' },
  { id: 'admins', label: 'Admin Users', icon: Users, badge: 'RBAC' },
];

export default function Navigation({ activeTab, onSelectTab }) {
  return (
    <div className="bg-white border-b border-[#EAEAEA] sticky top-16 z-30 shadow-subtle">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <nav className="flex space-x-1 overflow-x-auto py-2.5 scrollbar-none" aria-label="Tabs">
          {TABS.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;

            return (
              <button
                key={tab.id}
                onClick={() => onSelectTab(tab.id)}
                className={`flex items-center gap-2 px-3 py-1.5 rounded-xl text-xs font-semibold whitespace-nowrap transition border ${
                  isActive
                    ? 'bg-charcoal text-white border-charcoal shadow-subtle'
                    : 'bg-[#FBFBFA] text-muted hover:text-charcoal hover:bg-slate-100 border-transparent hover:border-[#EAEAEA]'
                }`}
              >
                <Icon className={`w-3.5 h-3.5 ${isActive ? 'text-white' : 'text-muted'}`} />
                <span>{tab.label}</span>
                {tab.badge && (
                  <span
                    className={`ml-0.5 px-1.5 py-0.2 rounded-full text-[9px] font-bold uppercase tracking-wider ${
                      isActive
                        ? 'bg-white/20 text-white'
                        : tab.badge === 'VM Sync'
                        ? 'bg-pastel-purple text-pastel-purpleText'
                        : tab.badge === 'Live'
                        ? 'bg-pastel-green text-pastel-greenText'
                        : 'bg-pastel-blue text-pastel-blueText'
                    }`}
                  >
                    {tab.badge}
                  </span>
                )}
              </button>
            );
          })}
        </nav>
      </div>
    </div>
  );
}
