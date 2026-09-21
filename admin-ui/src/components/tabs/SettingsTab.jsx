import React, { useState, useEffect } from 'react';
import { adminApi } from '../../api/client';
import { Sliders, Key, Zap, Flame, RefreshCw, CheckCircle2, Shield } from 'lucide-react';

export default function SettingsTab() {
  const [hfToken, setHfToken] = useState('');
  const [temperature, setTemperature] = useState(0.2);
  const [topK, setTopK] = useState(5);
  const [rerankerThreshold, setRerankerThreshold] = useState(0.35);
  const [modelStatus, setModelStatus] = useState(null);
  const [servicesHealth, setServicesHealth] = useState(null);
  const [savingToken, setSavingToken] = useState(false);
  const [flushing, setFlushing] = useState(false);

  const fetchSettings = async () => {
    try {
      const [m, h] = await Promise.all([
        adminApi.settings.getModelStatus().catch(() => null),
        adminApi.settings.getServicesHealth().catch(() => null),
      ]);
      setModelStatus(m);
      setServicesHealth(h);
    } catch (err) {
      console.error('Failed to load settings:', err);
    }
  };

  useEffect(() => {
    fetchSettings();
  }, []);

  const handleSaveHfToken = async (e) => {
    e.preventDefault();
    if (!hfToken.trim()) return;
    setSavingToken(true);
    try {
      await adminApi.settings.saveHfToken(hfToken.trim());
      alert('HuggingFace Token saved dynamically.');
      setHfToken('');
    } catch (err) {
      alert(`Save token error: ${err.message}`);
    } finally {
      setSavingToken(false);
    }
  };

  const handlePreload = async () => {
    try {
      await adminApi.settings.preloadModel();
      alert('Model warmup triggered.');
      fetchSettings();
    } catch (err) {
      alert(`Preload error: ${err.message}`);
    }
  };

  const handleFlushCuda = async () => {
    setFlushing(true);
    try {
      const res = await adminApi.settings.flushCuda();
      alert(res.message || 'CUDA VRAM cache cleared.');
      fetchSettings();
    } catch (err) {
      alert(`Flush error: ${err.message}`);
    } finally {
      setFlushing(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Model & GPU Controls */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {/* HF Token */}
        <div className="bg-white border border-[#EAEAEA] rounded-2xl p-6 shadow-subtle space-y-3">
          <div className="flex items-center gap-2">
            <Key className="w-4 h-4 text-charcoal" />
            <h3 className="text-sm font-bold text-charcoal">HuggingFace API Token</h3>
          </div>
          <p className="text-xs text-muted">
            Configure token for gated HuggingFace models without touching <code>.env</code>.
          </p>

          <form onSubmit={handleSaveHfToken} className="space-y-2.5">
            <input
              type="password"
              value={hfToken}
              onChange={(e) => setHfToken(e.target.value)}
              placeholder="hf_..."
              className="w-full px-3 py-2 bg-white border border-[#EAEAEA] rounded-xl text-xs font-mono"
            />
            <div className="flex justify-end">
              <button
                type="submit"
                disabled={savingToken || !hfToken.trim()}
                className="px-4 py-1.5 bg-charcoal text-white rounded-xl text-xs font-semibold disabled:opacity-50"
              >
                {savingToken ? 'Saving...' : 'Save Token'}
              </button>
            </div>
          </form>
        </div>

        {/* GPU Cache */}
        <div className="bg-white border border-[#EAEAEA] rounded-2xl p-6 shadow-subtle flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2">
              <Flame className="w-4 h-4 text-amber-500" />
              <h3 className="text-sm font-bold text-charcoal">GPU VRAM & Model Engine</h3>
            </div>
            <p className="text-xs text-muted mt-1 leading-relaxed">
              Flush GPU VRAM caches and recycle PyTorch CUDA memory buffers without restarting the server.
            </p>
          </div>

          <div className="flex items-center gap-2 pt-4 border-t border-[#EAEAEA]">
            <button
              onClick={handlePreload}
              className="px-3.5 py-2 bg-charcoal text-white rounded-xl text-xs font-semibold flex items-center gap-1.5"
            >
              <Zap className="w-3.5 h-3.5" />
              <span>Preload Models</span>
            </button>
            <button
              onClick={handleFlushCuda}
              disabled={flushing}
              className="px-3.5 py-2 border border-[#EAEAEA] text-muted hover:text-charcoal hover:bg-slate-50 rounded-xl text-xs font-semibold flex items-center gap-1.5"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${flushing ? 'animate-spin' : ''}`} />
              <span>Flush CUDA VRAM</span>
            </button>
          </div>
        </div>
      </div>

      {/* RAG Sliders */}
      <div className="bg-white border border-[#EAEAEA] rounded-2xl p-6 shadow-subtle space-y-4">
        <h3 className="text-sm font-bold text-charcoal pb-3 border-b border-[#EAEAEA]">
          RAG Hyperparameters & Inference Thresholds
        </h3>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
          <div>
            <div className="flex justify-between text-xs font-semibold mb-1">
              <span>LLM Temperature</span>
              <span className="font-mono text-indigo-600">{temperature}</span>
            </div>
            <input
              type="range"
              min="0.0"
              max="1.0"
              step="0.05"
              value={temperature}
              onChange={(e) => setTemperature(parseFloat(e.target.value))}
              className="w-full"
            />
            <p className="text-[11px] text-muted mt-1">Lower = factual, Higher = creative</p>
          </div>

          <div>
            <div className="flex justify-between text-xs font-semibold mb-1">
              <span>Retrieval Top-K Chunks</span>
              <span className="font-mono text-indigo-600">{topK}</span>
            </div>
            <input
              type="range"
              min="1"
              max="20"
              step="1"
              value={topK}
              onChange={(e) => setTopK(parseInt(e.target.value))}
              className="w-full"
            />
            <p className="text-[11px] text-muted mt-1">Max vector chunks fed to context</p>
          </div>

          <div>
            <div className="flex justify-between text-xs font-semibold mb-1">
              <span>Reranker Score Threshold</span>
              <span className="font-mono text-indigo-600">{rerankerThreshold}</span>
            </div>
            <input
              type="range"
              min="0.1"
              max="0.9"
              step="0.05"
              value={rerankerThreshold}
              onChange={(e) => setRerankerThreshold(parseFloat(e.target.value))}
              className="w-full"
            />
            <p className="text-[11px] text-muted mt-1">Cross-encoder relevance cutoff</p>
          </div>
        </div>
      </div>
    </div>
  );
}
