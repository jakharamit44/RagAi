import React, { useRef, useState, useEffect } from 'react';
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
  MessageSquare,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';

export const TABS = [
  { id: 'brain', label: 'Brain Cortex', icon: Brain, badge: 'Live' },
  { id: 'conversations', label: 'Conversations', icon: MessageSquare, badge: 'History' },
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
  const navRef = useRef(null);
  const [canScrollLeft, setCanScrollLeft] = useState(false);
  const [canScrollRight, setCanScrollRight] = useState(false);

  const checkScroll = () => {
    const el = navRef.current;
    if (!el) return;
    setCanScrollLeft(el.scrollLeft > 4);
    setCanScrollRight(el.scrollLeft < el.scrollWidth - el.clientWidth - 4);
  };

  useEffect(() => {
    checkScroll();
    window.addEventListener('resize', checkScroll);
    return () => window.removeEventListener('resize', checkScroll);
  }, []);

  const scrollBy = (offset) => {
    if (navRef.current) {
      navRef.current.scrollBy({ left: offset, behavior: 'smooth' });
    }
  };

  const handleWheel = (e) => {
    if (navRef.current && e.deltaY !== 0) {
      navRef.current.scrollLeft += e.deltaY;
      checkScroll();
    }
  };

  return (
    <div className="bg-white border-b border-[#EAEAEA] sticky top-16 z-30 shadow-subtle">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative flex items-center">
        {/* Left Scroll Button */}
        {canScrollLeft && (
          <button
            onClick={() => scrollBy(-220)}
            aria-label="Scroll Left"
            className="absolute left-2 z-10 p-1.5 bg-white/95 border border-[#EAEAEA] rounded-full shadow-subtle hover:bg-slate-50 transition text-charcoal"
          >
            <ChevronLeft className="w-3.5 h-3.5" />
          </button>
        )}

        {/* Tab List */}
        <nav
          ref={navRef}
          onScroll={checkScroll}
          onWheel={handleWheel}
          className="flex space-x-1 overflow-x-auto py-2.5 scrollbar-none scroll-smooth w-full px-2"
          aria-label="Tabs"
        >
          {TABS.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;

            return (
              <button
                key={tab.id}
                onClick={() => onSelectTab(tab.id)}
                className={`flex items-center gap-2 px-3 py-1.5 rounded-xl text-xs font-semibold whitespace-nowrap transition border shrink-0 ${
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

        {/* Right Scroll Button */}
        {canScrollRight && (
          <button
            onClick={() => scrollBy(220)}
            aria-label="Scroll Right"
            className="absolute right-2 z-10 p-1.5 bg-white/95 border border-[#EAEAEA] rounded-full shadow-subtle hover:bg-slate-50 transition text-charcoal"
          >
            <ChevronRight className="w-3.5 h-3.5" />
          </button>
        )}
      </div>
    </div>
  );
}
