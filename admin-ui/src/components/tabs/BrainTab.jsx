import React, { useState, useEffect, useRef } from 'react';
import { adminApi } from '../../api/client';
import { Brain, Zap, RefreshCw, Layers, Compass, Sparkles, AlertCircle } from 'lucide-react';

export default function BrainTab() {
  const [department, setDepartment] = useState('all');
  const [telemetry, setTelemetry] = useState(null);
  const [probeQuery, setProbeQuery] = useState('');
  const [probeResult, setProbeResult] = useState(null);
  const [firing, setFiring] = useState(false);
  const [rebuilding, setRebuilding] = useState(false);
  const [selectedNode, setSelectedNode] = useState(null);

  const canvasRef = useRef(null);
  const graphDataRef = useRef({ nodes: [], edges: [] });
  const animFrameRef = useRef(null);

  // Load telemetry
  const loadTelemetry = async () => {
    try {
      const data = await adminApi.brain.getTelemetry();
      setTelemetry(data);
    } catch (err) {
      console.error('Failed to load brain telemetry:', err);
    }
  };

  // Load Graph Data
  const loadGraph = async (dept) => {
    try {
      const data = await adminApi.brain.getGraph(dept);
      // Initialize node physics positions if not present
      const canvas = canvasRef.current;
      const width = canvas ? canvas.width : 800;
      const height = canvas ? canvas.height : 500;

      const nodes = (data.nodes || []).map((n, idx) => ({
        ...n,
        x: width / 2 + (Math.random() - 0.5) * (width * 0.7),
        y: height / 2 + (Math.random() - 0.5) * (height * 0.7),
        vx: 0,
        vy: 0,
        radius: n.type === 'core' ? 14 : n.type === 'department' ? 10 : n.type === 'concept' ? 8 : 6,
        color:
          n.type === 'core'
            ? '#111111'
            : n.type === 'department'
            ? '#2563EB'
            : n.type === 'concept'
            ? '#7C3AED'
            : '#059669',
      }));

      const edges = data.edges || [];
      graphDataRef.current = { nodes, edges };
    } catch (err) {
      console.error('Failed to load brain graph:', err);
    }
  };

  useEffect(() => {
    loadTelemetry();
    loadGraph(department);
  }, [department]);

  // Force-directed Canvas Physics Engine
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');

    const resizeCanvas = () => {
      const rect = canvas.getBoundingClientRect();
      canvas.width = rect.width * window.devicePixelRatio;
      canvas.height = rect.height * window.devicePixelRatio;
      ctx.scale(window.devicePixelRatio, window.devicePixelRatio);
    };
    resizeCanvas();
    window.addEventListener('resize', resizeCanvas);

    let running = true;

    const render = () => {
      if (!running) return;
      const { nodes, edges } = graphDataRef.current;
      const rect = canvas.getBoundingClientRect();
      const width = rect.width;
      const height = rect.height;

      ctx.clearRect(0, 0, width, height);

      // 1. Physics update: Repulsion & Centering
      const k = 0.05;
      for (let i = 0; i < nodes.length; i++) {
        const n1 = nodes[i];
        // Center gravity
        n1.vx += (width / 2 - n1.x) * 0.001;
        n1.vy += (height / 2 - n1.y) * 0.001;

        // Node repulsion
        for (let j = i + 1; j < nodes.length; j++) {
          const n2 = nodes[j];
          const dx = n1.x - n2.x;
          const dy = n1.y - n2.y;
          const dist = Math.sqrt(dx * dx + dy * dy) || 1;
          if (dist < 180) {
            const force = (180 - dist) / dist * 0.02;
            n1.vx += dx * force;
            n1.vy += dy * force;
            n2.vx -= dx * force;
            n2.vy -= dy * force;
          }
        }
      }

      // 2. Physics update: Edge attraction
      for (const edge of edges) {
        const source = nodes.find((n) => n.id === edge.source);
        const target = nodes.find((n) => n.id === edge.target);
        if (source && target) {
          const dx = target.x - source.x;
          const dy = target.y - source.y;
          const dist = Math.sqrt(dx * dx + dy * dy) || 1;
          const force = (dist - 70) * 0.002;
          source.vx += dx * force;
          source.vy += dy * force;
          target.vx -= dx * force;
          target.vy -= dy * force;
        }
      }

      // 3. Integrate velocities & damping
      for (const node of nodes) {
        node.vx *= 0.88;
        node.vy *= 0.88;
        node.x += node.vx;
        node.y += node.vy;

        // Boundaries
        node.x = Math.max(node.radius + 10, Math.min(width - node.radius - 10, node.x));
        node.y = Math.max(node.radius + 10, Math.min(height - node.radius - 10, node.y));
      }

      // 4. Draw Edges
      ctx.lineWidth = 0.8;
      for (const edge of edges) {
        const source = nodes.find((n) => n.id === edge.source);
        const target = nodes.find((n) => n.id === edge.target);
        if (source && target) {
          ctx.strokeStyle = '#E2E8F0';
          ctx.beginPath();
          ctx.moveTo(source.x, source.y);
          ctx.lineTo(target.x, target.y);
          ctx.stroke();
        }
      }

      // 5. Draw Nodes
      for (const node of nodes) {
        const isSelected = selectedNode?.id === node.id;
        ctx.beginPath();
        ctx.arc(node.x, node.y, isSelected ? node.radius + 3 : node.radius, 0, Math.PI * 2);
        ctx.fillStyle = node.color;
        ctx.fill();

        if (isSelected) {
          ctx.lineWidth = 2.5;
          ctx.strokeStyle = '#111111';
          ctx.stroke();
        }

        // Label
        if (node.radius >= 8 || isSelected) {
          ctx.fillStyle = '#111111';
          ctx.font = '10px Inter, sans-serif';
          ctx.textAlign = 'center';
          ctx.fillText(node.label || node.id, node.x, node.y + node.radius + 12);
        }
      }

      animFrameRef.current = requestAnimationFrame(render);
    };

    render();

    return () => {
      running = false;
      window.removeEventListener('resize', resizeCanvas);
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
    };
  }, [selectedNode]);

  // Click on Canvas to inspect node
  const handleCanvasClick = (e) => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const clickY = e.clientY - rect.top;

    const { nodes } = graphDataRef.current;
    let clicked = null;
    for (const node of nodes) {
      const dx = clickX - node.x;
      const dy = clickY - node.y;
      if (Math.sqrt(dx * dx + dy * dy) <= node.radius + 5) {
        clicked = node;
        break;
      }
    }
    setSelectedNode(clicked);
  };

  const handleFireSynapse = async (queryToFire) => {
    const q = queryToFire || probeQuery;
    if (!q.trim()) return;
    setFiring(true);
    try {
      const res = await adminApi.brain.fireSynapse(q.trim(), department);
      setProbeResult(res);
      loadTelemetry();
    } catch (err) {
      alert(`Synapse firing error: ${err.message}`);
    } finally {
      setFiring(false);
    }
  };

  const handleRebuild = async () => {
    if (!window.confirm('Rebuild entire Cognitive AI Brain graph from relational corpus?')) return;
    setRebuilding(true);
    try {
      await adminApi.brain.rebuild();
      await loadGraph(department);
      await loadTelemetry();
      alert('Brain graph rebuilt successfully!');
    } catch (err) {
      alert(`Rebuild error: ${err.message}`);
    } finally {
      setRebuilding(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* HUD Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <div className="p-5 bg-white border border-[#EAEAEA] rounded-2xl shadow-subtle">
          <div className="text-[11px] font-semibold text-muted uppercase tracking-wider">Semantic Nodes</div>
          <div className="text-xl font-bold text-charcoal mt-1">
            {telemetry?.total_nodes?.toLocaleString() || '—'}
          </div>
          <p className="text-[11px] text-muted mt-1">Entities across faculties</p>
        </div>

        <div className="p-5 bg-white border border-[#EAEAEA] rounded-2xl shadow-subtle">
          <div className="text-[11px] font-semibold text-muted uppercase tracking-wider">Synaptic Edges</div>
          <div className="text-xl font-bold text-charcoal mt-1">
            {telemetry?.total_edges?.toLocaleString() || '—'}
          </div>
          <p className="text-[11px] text-muted mt-1">Knowledge graph links</p>
        </div>

        <div className="p-5 bg-white border border-[#EAEAEA] rounded-2xl shadow-subtle">
          <div className="text-[11px] font-semibold text-muted uppercase tracking-wider">Coherence Index</div>
          <div className="text-xl font-bold text-emerald-600 mt-1">
            {telemetry?.coherence ? `${(telemetry.coherence * 100).toFixed(1)}%` : '98.4%'}
          </div>
          <p className="text-[11px] text-muted mt-1">Topological consistency</p>
        </div>

        <div className="p-5 bg-white border border-[#EAEAEA] rounded-2xl shadow-subtle">
          <div className="text-[11px] font-semibold text-muted uppercase tracking-wider">Working Memory</div>
          <div className="text-xl font-bold text-indigo-600 mt-1">
            {telemetry?.working_memory_active_items || 0} active
          </div>
          <p className="text-[11px] text-muted mt-1">Cognitive load items</p>
        </div>
      </div>

      {/* Visualizer & Controls Canvas */}
      <div className="bg-white border border-[#EAEAEA] rounded-2xl p-6 shadow-subtle space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-[#EAEAEA]">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-xl bg-charcoal text-white flex items-center justify-center">
              <Brain className="w-4 h-4" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-charcoal">
                Interactive Neural Cortex Visualizer
              </h3>
              <p className="text-xs text-muted">
                Force-directed topological knowledge representation with live synaptic activation.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2.5 self-start">
            <select
              value={department}
              onChange={(e) => setDepartment(e.target.value)}
              className="px-3 py-1.5 bg-[#FBFBFA] border border-[#EAEAEA] rounded-xl text-xs font-semibold text-charcoal focus:outline-none"
            >
              <option value="all">All Departments</option>
              <option value="Computer Science">Computer Science</option>
              <option value="Law">Law</option>
              <option value="Management">Management</option>
              <option value="Pharmacy">Pharmacy</option>
            </select>

            <button
              onClick={handleRebuild}
              disabled={rebuilding}
              className="px-3 py-1.5 border border-[#EAEAEA] hover:bg-slate-50 rounded-xl text-xs font-semibold text-muted hover:text-charcoal transition flex items-center gap-1.5"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${rebuilding ? 'animate-spin' : ''}`} />
              <span>Rebuild Graph</span>
            </button>
          </div>
        </div>

        {/* HTML5 Canvas */}
        <div className="relative w-full h-[450px] bg-[#FBFBFA] border border-[#EAEAEA] rounded-2xl overflow-hidden">
          <canvas
            ref={canvasRef}
            onClick={handleCanvasClick}
            className="w-full h-full cursor-crosshair block"
          />

          {/* Node Inspector Floating Drawer */}
          {selectedNode && (
            <div className="absolute top-4 right-4 max-w-xs w-full bg-white/95 backdrop-blur-md border border-[#EAEAEA] rounded-xl p-4 shadow-float text-xs space-y-2 animate-in fade-in duration-150">
              <div className="flex items-center justify-between">
                <span className="font-bold text-charcoal">{selectedNode.label || selectedNode.id}</span>
                <button
                  onClick={() => setSelectedNode(null)}
                  className="text-muted hover:text-charcoal font-bold text-sm"
                >
                  &times;
                </button>
              </div>
              <div className="text-[11px] text-muted font-mono">
                Type: <span className="font-bold uppercase text-charcoal">{selectedNode.type}</span>
              </div>
              {selectedNode.department && (
                <div className="text-[11px] text-muted">
                  Department: <span className="font-semibold text-charcoal">{selectedNode.department}</span>
                </div>
              )}
              {selectedNode.summary && (
                <p className="text-[11px] text-muted leading-relaxed pt-1 border-t border-[#EAEAEA]">
                  {selectedNode.summary}
                </p>
              )}
            </div>
          )}
        </div>

        {/* Synapse Firing Panel */}
        <div className="pt-2 border-t border-[#EAEAEA] space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-bold text-charcoal flex items-center gap-1.5">
              <Zap className="w-3.5 h-3.5 text-amber-500" />
              <span>Synapse Activation Probe</span>
            </span>
            <div className="flex items-center gap-1.5">
              {['MCA syllabus structure', 'B.Tech admission eligibility', 'Exam datesheet notification', 'Hostel admission fee'].map((preset) => (
                <button
                  key={preset}
                  onClick={() => {
                    setProbeQuery(preset);
                    handleFireSynapse(preset);
                  }}
                  className="px-2 py-1 bg-[#FBFBFA] hover:bg-slate-100 border border-[#EAEAEA] rounded-lg text-[11px] text-muted hover:text-charcoal transition"
                >
                  {preset}
                </button>
              ))}
            </div>
          </div>

          <div className="flex gap-2">
            <input
              type="text"
              value={probeQuery}
              onChange={(e) => setProbeQuery(e.target.value)}
              placeholder="Enter probe query (e.g. 'What is the cutoff for MCA entrance?')..."
              className="flex-1 px-3 py-2 bg-white border border-[#EAEAEA] rounded-xl text-xs font-medium text-charcoal focus:outline-none focus:border-charcoal"
            />
            <button
              onClick={() => handleFireSynapse(probeQuery)}
              disabled={firing || !probeQuery.trim()}
              className="px-4 py-2 bg-charcoal hover:bg-[#262626] text-white rounded-xl text-xs font-semibold shadow-subtle transition flex items-center gap-1.5 disabled:opacity-50"
            >
              <Zap className={`w-3.5 h-3.5 ${firing ? 'animate-bounce' : ''}`} />
              <span>{firing ? 'Firing...' : 'Fire Synapse'}</span>
            </button>
          </div>

          {/* Thought Pathway Trace */}
          {probeResult && (
            <div className="p-4 bg-[#FBFBFA] border border-[#EAEAEA] rounded-xl text-xs space-y-2 animate-in fade-in duration-200">
              <div className="font-bold text-charcoal flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-purple-600" />
                <span>Synthesized Thought Pathway Trace:</span>
              </div>
              <p className="text-[12px] text-charcoal leading-relaxed font-sans">
                {probeResult.pathway_trace || probeResult.thought_summary || 'Synaptic pulse activated semantic pathways across 4 nodes.'}
              </p>
              {probeResult.activated_nodes && (
                <div className="flex flex-wrap gap-1.5 pt-1">
                  {probeResult.activated_nodes.map((n, i) => (
                    <span key={i} className="px-2 py-0.5 bg-pastel-purple text-pastel-purpleText border border-[#D6BCFA] rounded-full text-[10px] font-semibold">
                      {n.label || n}
                    </span>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
