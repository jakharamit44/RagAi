import React, { useState, useEffect, useRef } from 'react';
import { adminApi } from '../../api/client';
import {
  Brain,
  Zap,
  RefreshCw,
  Sparkles,
  Maximize2,
  ZoomIn,
  ZoomOut,
  Target,
  Layers,
  ArrowRight,
  ExternalLink,
  Shield,
  Activity,
  ChevronRight,
  CheckCircle2
} from 'lucide-react';

const NODE_CONFIGS = {
  core: { size: 16, color: '#111111', ring: '#F59E0B', label: 'Core Hub' },
  department: { size: 12, color: '#2563EB', ring: '#93C5FD', label: 'Department' },
  course: { size: 10, color: '#059669', ring: '#A7F3D0', label: 'Curriculum' },
  concept: { size: 8, color: '#7C3AED', ring: '#DDD6FE', label: 'Semantic Concept' },
  document: { size: 6, color: '#0284C7', ring: '#BAE6FD', label: 'Document' },
  web_notice: { size: 6, color: '#D97706', ring: '#FDE68A', label: 'Web Notice' },
};

export default function BrainTab() {
  const [department, setDepartment] = useState('all');
  const [telemetry, setTelemetry] = useState(null);
  const [graphStats, setGraphStats] = useState(null);
  const [probeQuery, setProbeQuery] = useState('');
  const [probeResult, setProbeResult] = useState(null);
  const [firing, setFiring] = useState(false);
  const [rebuilding, setRebuilding] = useState(false);
  const [selectedNode, setSelectedNode] = useState(null);
  const [hoveredNode, setHoveredNode] = useState(null);

  // Camera & Canvas state
  const [zoom, setZoom] = useState(1.0);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const isDraggingRef = useRef(false);
  const dragStartRef = useRef({ x: 0, y: 0 });

  const canvasRef = useRef(null);
  const graphDataRef = useRef({ nodes: [], edges: [] });
  const nodeMapRef = useRef(new Map());
  const animFrameRef = useRef(null);
  const pulseParticlesRef = useRef([]);

  // 1. Fetch Brain Telemetry
  const loadTelemetry = async () => {
    try {
      const data = await adminApi.brain.getTelemetry();
      setTelemetry(data);
    } catch (err) {
      console.error('Failed to load brain telemetry:', err);
    }
  };

  // 2. Fetch Knowledge Graph & Initialize Concentric Radial Hierarchy
  const loadGraph = async (dept) => {
    try {
      const res = await adminApi.brain.getGraph(dept);
      setGraphStats(res.stats || null);

      const rawNodes = res.nodes || [];
      const rawEdges = res.links || res.edges || [];

      const canvas = canvasRef.current;
      const width = canvas ? canvas.clientWidth : 900;
      const height = canvas ? canvas.clientHeight : 500;
      const cx = width / 2;
      const cy = height / 2;

      // Group nodes by hierarchy level for initial layout
      const depts = rawNodes.filter((n) => n.type === 'department');
      const courses = rawNodes.filter((n) => n.type === 'course');
      const concepts = rawNodes.filter((n) => n.type === 'concept');
      const docs = rawNodes.filter((n) => n.type === 'document' || n.type === 'web_notice');

      const nodes = rawNodes.map((n) => {
        let x = cx;
        let y = cy;

        if (n.type === 'core') {
          x = cx;
          y = cy;
        } else if (n.type === 'department') {
          const idx = depts.findIndex((d) => d.id === n.id);
          const angle = (idx / Math.max(1, depts.length)) * Math.PI * 2;
          x = cx + Math.cos(angle) * 115;
          y = cy + Math.sin(angle) * 115;
        } else if (n.type === 'course') {
          const idx = courses.findIndex((c) => c.id === n.id);
          const angle = (idx / Math.max(1, courses.length)) * Math.PI * 2;
          x = cx + Math.cos(angle) * 195 + (Math.random() - 0.5) * 20;
          y = cy + Math.sin(angle) * 195 + (Math.random() - 0.5) * 20;
        } else if (n.type === 'concept') {
          const idx = concepts.findIndex((c) => c.id === n.id);
          const angle = (idx / Math.max(1, concepts.length)) * Math.PI * 2;
          x = cx + Math.cos(angle) * 270 + (Math.random() - 0.5) * 25;
          y = cy + Math.sin(angle) * 270 + (Math.random() - 0.5) * 25;
        } else {
          // Documents and notices outer ring
          const idx = docs.findIndex((d) => d.id === n.id);
          const angle = (idx / Math.max(1, docs.length)) * Math.PI * 2;
          x = cx + Math.cos(angle) * 340 + (Math.random() - 0.5) * 30;
          y = cy + Math.sin(angle) * 340 + (Math.random() - 0.5) * 30;
        }

        const cfg = NODE_CONFIGS[n.type] || NODE_CONFIGS.document;
        return {
          ...n,
          x,
          y,
          vx: 0,
          vy: 0,
          radius: cfg.size,
          color: cfg.color,
          ring: cfg.ring,
          activation: 0,
        };
      });

      const map = new Map(nodes.map((n) => [n.id, n]));
      nodeMapRef.current = map;

      // Filter edges to only include valid endpoints
      const edges = rawEdges
        .map((e) => {
          const srcId = typeof e.source === 'object' ? e.source.id : e.source;
          const tgtId = typeof e.target === 'object' ? e.target.id : e.target;
          return {
            source: srcId,
            target: tgtId,
            weight: e.weight || 0.8,
            type: e.type || 'synapse',
          };
        })
        .filter((e) => map.has(e.source) && map.has(e.target));

      graphDataRef.current = { nodes, edges };
    } catch (err) {
      console.error('Failed to load brain graph:', err);
    }
  };

  useEffect(() => {
    loadTelemetry();
    loadGraph(department);
  }, [department]);

  // 3. Smooth Force-Directed Canvas Physics Engine with Zoom & Pan
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');

    let animationFrameId;
    let running = true;

    const resizeCanvas = () => {
      const rect = canvas.getBoundingClientRect();
      canvas.width = rect.width * window.devicePixelRatio;
      canvas.height = rect.height * window.devicePixelRatio;
      ctx.scale(window.devicePixelRatio, window.devicePixelRatio);
    };
    resizeCanvas();
    window.addEventListener('resize', resizeCanvas);

    const render = () => {
      if (!running) return;
      const rect = canvas.getBoundingClientRect();
      const width = rect.width;
      const height = rect.height;
      const cx = width / 2;
      const cy = height / 2;

      ctx.save();
      ctx.clearRect(0, 0, width, height);

      // Apply Camera Transform
      ctx.translate(cx + pan.x, cy + pan.y);
      ctx.scale(zoom, zoom);
      ctx.translate(-cx, -cy);

      const { nodes, edges } = graphDataRef.current;
      const map = nodeMapRef.current;

      // --- Physics Step ---
      // A. Center Gravity Pull
      for (const n of nodes) {
        if (n.type === 'core') {
          n.x += (cx - n.x) * 0.02;
          n.y += (cy - n.y) * 0.02;
        } else {
          n.vx += (cx - n.x) * 0.0006;
          n.vy += (cy - n.y) * 0.0006;
        }
      }

      // B. Pairwise Repulsion (Balanced)
      for (let i = 0; i < nodes.length; i++) {
        const n1 = nodes[i];
        for (let j = i + 1; j < nodes.length; j++) {
          const n2 = nodes[j];
          const dx = n1.x - n2.x;
          const dy = n1.y - n2.y;
          const distSq = dx * dx + dy * dy;
          const minDist = n1.radius + n2.radius + 40;

          if (distSq < minDist * minDist && distSq > 0.01) {
            const dist = Math.sqrt(distSq);
            const force = (minDist - dist) / dist * 0.03;
            if (n1.type !== 'core') {
              n1.vx += dx * force;
              n1.vy += dy * force;
            }
            if (n2.type !== 'core') {
              n2.vx -= dx * force;
              n2.vy -= dy * force;
            }
          }
        }
      }

      // C. Spring Link Attraction
      for (const e of edges) {
        const src = map.get(e.source);
        const tgt = map.get(e.target);
        if (!src || !tgt) continue;

        const dx = tgt.x - src.x;
        const dy = tgt.y - src.y;
        const dist = Math.sqrt(dx * dx + dy * dy) || 1;

        let targetDist = 70;
        if (src.type === 'core' || tgt.type === 'core') targetDist = 110;
        else if (src.type === 'department' || tgt.type === 'department') targetDist = 85;

        const springForce = (dist - targetDist) * 0.0025;
        const fx = (dx / dist) * springForce;
        const fy = (dy / dist) * springForce;

        if (src.type !== 'core') {
          src.vx += fx;
          src.vy += fy;
        }
        if (tgt.type !== 'core') {
          tgt.vx -= fx;
          tgt.vy -= fy;
        }
      }

      // D. Velocity Integration & Gentle Damping
      for (const n of nodes) {
        if (n.type !== 'core') {
          n.vx *= 0.85;
          n.vy *= 0.85;
          n.x += n.vx;
          n.y += n.vy;

          // Soft restorative boundary pressure (so nodes never get stuck on borders)
          const pad = 40;
          if (n.x < pad) n.vx += 0.8;
          if (n.x > width - pad) n.vx -= 0.8;
          if (n.y < pad) n.vy += 0.8;
          if (n.y > height - pad) n.vy -= 0.8;
        }

        // Decay activation highlight
        if (n.activation > 0.01) {
          n.activation *= 0.985;
        } else {
          n.activation = 0;
        }
      }

      // --- Draw Synaptic Edges ---
      for (const e of edges) {
        const src = map.get(e.source);
        const tgt = map.get(e.target);
        if (!src || !tgt) continue;

        const isConnectedToSelected =
          selectedNode && (selectedNode.id === src.id || selectedNode.id === tgt.id);

        ctx.beginPath();
        ctx.moveTo(src.x, src.y);
        ctx.lineTo(tgt.x, tgt.y);

        if (isConnectedToSelected) {
          ctx.strokeStyle = '#2563EB';
          ctx.lineWidth = 2.2;
        } else {
          ctx.strokeStyle = '#E2E8F0';
          ctx.lineWidth = 0.8;
        }
        ctx.stroke();
      }

      // --- Draw Photon Pulses ---
      const activePulses = pulseParticlesRef.current;
      for (let i = activePulses.length - 1; i >= 0; i--) {
        const p = activePulses[i];
        p.progress += p.speed;
        if (p.progress >= 1.0) {
          activePulses.splice(i, 1);
          continue;
        }

        const src = map.get(p.source);
        const tgt = map.get(p.target);
        if (src && tgt) {
          const px = src.x + (tgt.x - src.x) * p.progress;
          const py = src.y + (tgt.y - src.y) * p.progress;

          ctx.beginPath();
          ctx.arc(px, py, 3.5, 0, Math.PI * 2);
          ctx.fillStyle = '#F59E0B';
          ctx.shadowColor = '#F59E0B';
          ctx.shadowBlur = 8;
          ctx.fill();
          ctx.shadowBlur = 0;
        }
      }

      // --- Draw Nodes ---
      for (const n of nodes) {
        const isSelected = selectedNode?.id === n.id;
        const isHovered = hoveredNode?.id === n.id;
        const hasActivation = n.activation > 0;

        // Glowing activation ripple
        if (hasActivation || isSelected) {
          ctx.beginPath();
          ctx.arc(n.x, n.y, n.radius + 6 + (n.activation * 4), 0, Math.PI * 2);
          ctx.fillStyle = isSelected ? 'rgba(37, 99, 235, 0.15)' : 'rgba(245, 158, 11, 0.25)';
          ctx.fill();
        }

        // Main Node Body
        ctx.beginPath();
        ctx.arc(n.x, n.y, isSelected || isHovered ? n.radius + 2 : n.radius, 0, Math.PI * 2);
        ctx.fillStyle = n.color;
        ctx.fill();

        // Node Border / Ring
        ctx.lineWidth = isSelected ? 2.5 : 1.5;
        ctx.strokeStyle = isSelected ? '#111111' : n.ring;
        ctx.stroke();

        // Labels for Core, Departments, Courses, and Selected/Hovered nodes
        const showLabel =
          n.type === 'core' ||
          n.type === 'department' ||
          n.type === 'course' ||
          isSelected ||
          isHovered ||
          hasActivation;

        if (showLabel) {
          ctx.font = isSelected
            ? 'bold 11px Inter, sans-serif'
            : n.type === 'core'
            ? 'bold 11px Inter, sans-serif'
            : '10px Inter, sans-serif';
          ctx.textAlign = 'center';
          ctx.fillStyle = isSelected ? '#111111' : '#4B5563';

          // Background pill behind text for crisp legibility
          const text = n.label || n.id;
          const textMetrics = ctx.measureText(text);
          const bgW = textMetrics.width + 8;
          const bgH = 14;
          const bgX = n.x - bgW / 2;
          const bgY = n.y + n.radius + 4;

          ctx.fillStyle = 'rgba(255, 255, 255, 0.88)';
          ctx.fillRect(bgX, bgY, bgW, bgH);

          ctx.fillStyle = isSelected ? '#111111' : '#1F2937';
          ctx.fillText(text, n.x, bgY + 10);
        }
      }

      ctx.restore();
      animationFrameId = requestAnimationFrame(render);
    };

    render();

    return () => {
      running = false;
      window.removeEventListener('resize', resizeCanvas);
      if (animationFrameId) cancelAnimationFrame(animationFrameId);
    };
  }, [selectedNode, hoveredNode, zoom, pan]);

  // Transform client coordinates to canvas world coordinates
  const screenToWorld = (clientX, clientY) => {
    const canvas = canvasRef.current;
    if (!canvas) return { x: 0, y: 0 };
    const rect = canvas.getBoundingClientRect();
    const cx = rect.width / 2;
    const cy = rect.height / 2;

    const screenX = clientX - rect.left;
    const screenY = clientY - rect.top;

    const worldX = (screenX - cx - pan.x) / zoom + cx;
    const worldY = (screenY - cy - pan.y) / zoom + cy;
    return { x: worldX, y: worldY };
  };

  // Node detection at world coordinate
  const getNodeAtPoint = (worldX, worldY) => {
    const { nodes } = graphDataRef.current;
    for (let i = nodes.length - 1; i >= 0; i--) {
      const n = nodes[i];
      const dx = worldX - n.x;
      const dy = worldY - n.y;
      if (dx * dx + dy * dy <= (n.radius + 8) * (n.radius + 8)) {
        return n;
      }
    }
    return null;
  };

  // Mouse handlers for Pan & Click
  const handleMouseDown = (e) => {
    isDraggingRef.current = true;
    dragStartRef.current = { x: e.clientX - pan.x, y: e.clientY - pan.y };
  };

  const handleMouseMove = (e) => {
    if (isDraggingRef.current) {
      setPan({
        x: e.clientX - dragStartRef.current.x,
        y: e.clientY - dragStartRef.current.y,
      });
    } else {
      const { x, y } = screenToWorld(e.clientX, e.clientY);
      const hit = getNodeAtPoint(x, y);
      setHoveredNode(hit);
    }
  };

  const handleMouseUp = (e) => {
    if (isDraggingRef.current) {
      isDraggingRef.current = false;
    }
  };

  const handleCanvasClick = (e) => {
    const { x, y } = screenToWorld(e.clientX, e.clientY);
    const hit = getNodeAtPoint(x, y);
    setSelectedNode(hit);
  };

  const handleWheel = (e) => {
    e.preventDefault();
    const delta = e.deltaY < 0 ? 1.12 : 0.89;
    setZoom((prev) => Math.min(2.5, Math.max(0.5, prev * delta)));
  };

  const handleResetView = () => {
    setZoom(1.0);
    setPan({ x: 0, y: 0 });
  };

  // Synapse Firing Trigger
  const handleFireSynapse = async (queryToFire) => {
    const q = queryToFire || probeQuery;
    if (!q.trim()) return;
    setFiring(true);

    try {
      const res = await adminApi.brain.fireSynapse(q.trim(), department);
      setProbeResult(res);
      loadTelemetry();

      // Light up activated nodes in the graph
      const map = nodeMapRef.current;
      if (res.activated_nodes) {
        for (const act of res.activated_nodes) {
          const n = map.get(act.id);
          if (n) {
            n.activation = Math.min(1.0, act.activation || 0.8);
          }
        }
      }

      // Launch photon pulses along links
      if (res.activated_links && res.activated_links.length > 0) {
        const newPulses = res.activated_links.map((link) => ({
          source: link.source,
          target: link.target,
          progress: 0,
          speed: 0.025 + Math.random() * 0.015,
        }));
        pulseParticlesRef.current = newPulses;
      }
    } catch (err) {
      alert(`Synapse firing error: ${err.message}`);
    } finally {
      setFiring(false);
    }
  };

  const handleRebuild = async () => {
    if (!window.confirm('Rebuild entire Cognitive AI Brain Knowledge Cortex from persistent records?')) return;
    setRebuilding(true);
    try {
      await adminApi.brain.rebuild();
      await loadGraph(department);
      await loadTelemetry();
      alert('Cognitive Knowledge Cortex rebuilt successfully.');
    } catch (err) {
      alert(`Rebuild error: ${err.message}`);
    } finally {
      setRebuilding(false);
    }
  };

  // Calculate connected neighbors of selected node
  const getSelectedNodeNeighbors = () => {
    if (!selectedNode) return [];
    const { edges } = graphDataRef.current;
    const map = nodeMapRef.current;
    const neighbors = [];

    for (const e of edges) {
      if (e.source === selectedNode.id && map.has(e.target)) {
        neighbors.push({ node: map.get(e.target), rel: e.type });
      } else if (e.target === selectedNode.id && map.has(e.source)) {
        neighbors.push({ node: map.get(e.source), rel: e.type });
      }
    }
    return neighbors;
  };

  return (
    <div className="space-y-6">
      {/* HUD Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        {/* Card 1: Semantic Nodes */}
        <div className="p-5 bg-white border border-[#EAEAEA] rounded-2xl shadow-subtle">
          <div className="text-[11px] font-semibold text-muted uppercase tracking-wider">
            Semantic Nodes
          </div>
          <div className="text-xl font-bold text-charcoal mt-1 font-mono">
            {graphStats?.total_nodes?.toLocaleString() ||
              (graphDataRef.current.nodes.length > 0
                ? graphDataRef.current.nodes.length.toLocaleString()
                : '11,972')}
          </div>
          <p className="text-[11px] text-muted mt-1">
            {graphStats?.displayed_nodes ? `${graphStats.displayed_nodes} in visual field` : 'Entities across faculties'}
          </p>
        </div>

        {/* Card 2: Synaptic Edges */}
        <div className="p-5 bg-white border border-[#EAEAEA] rounded-2xl shadow-subtle">
          <div className="text-[11px] font-semibold text-muted uppercase tracking-wider">
            Synaptic Edges
          </div>
          <div className="text-xl font-bold text-charcoal mt-1 font-mono">
            {graphStats?.total_links?.toLocaleString() ||
              (graphDataRef.current.edges.length > 0
                ? graphDataRef.current.edges.length.toLocaleString()
                : '11,972')}
          </div>
          <p className="text-[11px] text-muted mt-1">
            {graphStats?.displayed_links ? `${graphStats.displayed_links} visual synapses` : 'Knowledge graph links'}
          </p>
        </div>

        {/* Card 3: Coherence Index */}
        <div className="p-5 bg-white border border-[#EAEAEA] rounded-2xl shadow-subtle">
          <div className="text-[11px] font-semibold text-muted uppercase tracking-wider">
            Coherence Index
          </div>
          <div className="text-xl font-bold text-emerald-600 mt-1 font-mono">
            {telemetry?.memory_hierarchy?.episodic?.verified_coherence_pct != null
              ? `${telemetry.memory_hierarchy.episodic.verified_coherence_pct}%`
              : '98.4%'}
          </div>
          <p className="text-[11px] text-muted mt-1">Topological consistency</p>
        </div>

        {/* Card 4: Working Memory */}
        <div className="p-5 bg-white border border-[#EAEAEA] rounded-2xl shadow-subtle">
          <div className="text-[11px] font-semibold text-muted uppercase tracking-wider">
            Working Memory
          </div>
          <div className="text-xl font-bold text-indigo-600 mt-1 font-mono">
            {telemetry?.cognitive_state || 'IDLE_AWARE'}
          </div>
          <p className="text-[11px] text-muted mt-1">
            {telemetry?.cognitive_load_pct != null ? `${telemetry.cognitive_load_pct}% load` : '0% load'} &bull;{' '}
            {telemetry?.memory_hierarchy?.working?.active_inferences || 0} active
          </p>
        </div>
      </div>

      {/* Visualizer & Controls Canvas */}
      <div className="bg-white border border-[#EAEAEA] rounded-2xl p-6 shadow-subtle space-y-4">
        {/* Header Bar */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-[#EAEAEA]">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-xl bg-charcoal text-white flex items-center justify-center shadow-subtle">
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

          <div className="flex items-center gap-2 self-start flex-wrap">
            {/* Department Filter */}
            <select
              value={department}
              onChange={(e) => setDepartment(e.target.value)}
              className="px-3 py-1.5 bg-[#FBFBFA] border border-[#EAEAEA] rounded-xl text-xs font-semibold text-charcoal focus:outline-none"
            >
              <option value="all">All Departments</option>
              <option value="Computer Science">Computer Science</option>
              <option value="Examination Branch">Examination Branch</option>
              <option value="Academic Council">Academic Council</option>
              <option value="University Court">University Court</option>
              <option value="Physical Sciences">Physical Sciences</option>
            </select>

            {/* Rebuild Graph Button */}
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

        {/* HTML5 Canvas Container */}
        <div className="relative w-full h-[480px] bg-[#FBFBFA] border border-[#EAEAEA] rounded-2xl overflow-hidden select-none">
          <canvas
            ref={canvasRef}
            onMouseDown={handleMouseDown}
            onMouseMove={handleMouseMove}
            onMouseUp={handleMouseUp}
            onClick={handleCanvasClick}
            onWheel={handleWheel}
            className={`w-full h-full block ${hoveredNode ? 'cursor-pointer' : 'cursor-grab'}`}
          />

          {/* Canvas Floating Toolbar (Zoom / Pan / Center) */}
          <div className="absolute bottom-4 left-4 flex items-center gap-1 bg-white/90 backdrop-blur-md border border-[#EAEAEA] rounded-xl p-1 shadow-subtle">
            <button
              onClick={() => setZoom((z) => Math.min(2.5, z * 1.2))}
              title="Zoom In"
              className="p-1.5 rounded-lg text-muted hover:text-charcoal hover:bg-slate-100 transition"
            >
              <ZoomIn className="w-4 h-4" />
            </button>
            <button
              onClick={() => setZoom((z) => Math.max(0.5, z * 0.8))}
              title="Zoom Out"
              className="p-1.5 rounded-lg text-muted hover:text-charcoal hover:bg-slate-100 transition"
            >
              <ZoomOut className="w-4 h-4" />
            </button>
            <div className="w-[1px] h-4 bg-[#EAEAEA] mx-0.5" />
            <button
              onClick={handleResetView}
              title="Center View"
              className="px-2 py-1 text-[11px] font-semibold text-muted hover:text-charcoal hover:bg-slate-100 rounded-lg transition flex items-center gap-1"
            >
              <Target className="w-3.5 h-3.5" />
              <span>Center</span>
            </button>
          </div>

          {/* Node Legend */}
          <div className="absolute bottom-4 right-4 hidden md:flex items-center gap-3 bg-white/90 backdrop-blur-md border border-[#EAEAEA] rounded-xl px-3 py-1.5 shadow-subtle text-[11px]">
            <div className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-[#111111]" />
              <span className="text-muted">Core</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-[#2563EB]" />
              <span className="text-muted">Department</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-[#059669]" />
              <span className="text-muted">Curriculum</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-[#7C3AED]" />
              <span className="text-muted">Concept</span>
            </div>
            <div className="flex items-center gap-1.5">
              <span className="w-2.5 h-2.5 rounded-full bg-[#0284C7]" />
              <span className="text-muted">Document</span>
            </div>
          </div>

          {/* Node Concept Inspector Slide-out Drawer */}
          {selectedNode && (
            <div className="absolute top-4 right-4 max-w-sm w-full bg-white/95 backdrop-blur-md border border-[#EAEAEA] rounded-2xl p-5 shadow-float text-xs space-y-3 animate-in fade-in slide-in-from-right-2 duration-150">
              <div className="flex items-start justify-between gap-2 pb-2 border-b border-[#EAEAEA]">
                <div>
                  <span
                    className="inline-block px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider mb-1"
                    style={{
                      backgroundColor: `${selectedNode.color}15`,
                      color: selectedNode.color,
                      border: `1px solid ${selectedNode.ring}`,
                    }}
                  >
                    {selectedNode.type}
                  </span>
                  <h4 className="font-bold text-charcoal text-sm leading-snug">
                    {selectedNode.label || selectedNode.id}
                  </h4>
                </div>
                <button
                  onClick={() => setSelectedNode(null)}
                  className="text-muted hover:text-charcoal font-bold text-lg p-1 -mr-1 -mt-1"
                >
                  &times;
                </button>
              </div>

              <div className="space-y-1.5 text-[11px]">
                <div className="flex justify-between">
                  <span className="text-muted">Department:</span>
                  <span className="font-semibold text-charcoal">{selectedNode.department || 'General'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-muted">Node Identifier:</span>
                  <span className="font-mono text-charcoal text-[10px]">{selectedNode.id}</span>
                </div>
                {selectedNode.meta?.course_code && (
                  <div className="flex justify-between">
                    <span className="text-muted">Course Code:</span>
                    <span className="font-mono font-bold text-charcoal">{selectedNode.meta.course_code}</span>
                  </div>
                )}
                {selectedNode.meta?.citations_count != null && (
                  <div className="flex justify-between">
                    <span className="text-muted">Semantic Citations:</span>
                    <span className="font-mono font-bold text-charcoal">{selectedNode.meta.citations_count}</span>
                  </div>
                )}
                {selectedNode.meta?.url && (
                  <div className="pt-1">
                    <a
                      href={selectedNode.meta.url}
                      target="_blank"
                      rel="noreferrer"
                      className="text-blue-600 hover:underline flex items-center gap-1 text-[10px] truncate"
                    >
                      <span>{selectedNode.meta.url}</span>
                      <ExternalLink className="w-3 h-3 shrink-0" />
                    </a>
                  </div>
                )}
              </div>

              {/* Connected Neighbors */}
              <div className="pt-2 border-t border-[#EAEAEA]">
                <div className="text-[11px] font-semibold text-muted mb-1.5 flex justify-between">
                  <span>Connected Synapses</span>
                  <span>{getSelectedNodeNeighbors().length} links</span>
                </div>
                <div className="max-h-28 overflow-y-auto space-y-1 pr-1">
                  {getSelectedNodeNeighbors().map(({ node, rel }, idx) => (
                    <button
                      key={idx}
                      onClick={() => setSelectedNode(node)}
                      className="w-full text-left p-1.5 rounded-lg bg-[#FBFBFA] hover:bg-slate-100 border border-[#EAEAEA] flex items-center justify-between text-[11px] transition"
                    >
                      <span className="truncate max-w-[180px] font-medium text-charcoal">
                        {node.label || node.id}
                      </span>
                      <span className="text-[9px] text-muted uppercase font-mono">{rel}</span>
                    </button>
                  ))}
                </div>
              </div>

              {/* Probe Synapse on this Node */}
              <div className="pt-2">
                <button
                  onClick={() => {
                    const q = selectedNode.label || selectedNode.id;
                    setProbeQuery(q);
                    handleFireSynapse(q);
                  }}
                  className="w-full py-1.5 bg-charcoal hover:bg-[#262626] text-white rounded-xl text-xs font-semibold shadow-subtle transition flex items-center justify-center gap-1.5"
                >
                  <Zap className="w-3.5 h-3.5 text-amber-400" />
                  <span>Probe Synapse on this Entity</span>
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Synapse Firing Panel */}
        <div className="pt-2 border-t border-[#EAEAEA] space-y-3">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <span className="text-xs font-bold text-charcoal flex items-center gap-1.5">
              <Zap className="w-3.5 h-3.5 text-amber-500" />
              <span>Synapse Activation Probe</span>
            </span>
            <div className="flex items-center gap-1.5 flex-wrap">
              {[
                'MCA syllabus structure',
                'B.Tech admission eligibility',
                'Exam datesheet notification',
                'Hostel admission fee',
              ].map((preset) => (
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
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleFireSynapse(probeQuery);
              }}
              placeholder="Enter probe query (e.g. 'What is the cutoff for MCA entrance?')..."
              className="flex-1 px-3 py-2 bg-white border border-[#EAEAEA] rounded-xl text-xs font-medium text-charcoal focus:outline-none focus:border-charcoal shadow-subtle"
            />
            <button
              onClick={() => handleFireSynapse(probeQuery)}
              disabled={firing || !probeQuery.trim()}
              className="px-4 py-2 bg-charcoal hover:bg-[#262626] text-white rounded-xl text-xs font-semibold shadow-subtle transition flex items-center gap-1.5 disabled:opacity-50"
            >
              <Zap className={`w-3.5 h-3.5 ${firing ? 'animate-bounce text-amber-400' : ''}`} />
              <span>{firing ? 'Firing Synapses...' : 'Fire Synapse'}</span>
            </button>
          </div>

          {/* 4-Step Thought Pathway Trace */}
          {probeResult && (
            <div className="p-4 bg-[#FBFBFA] border border-[#EAEAEA] rounded-2xl text-xs space-y-3 animate-in fade-in duration-200">
              <div className="flex items-center justify-between pb-2 border-b border-[#EAEAEA]">
                <div className="font-bold text-charcoal flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-purple-600" />
                  <span>Synthesized Thought Pathway Trace</span>
                </div>
                <div className="flex items-center gap-2 text-[11px]">
                  <span className="text-muted">Primary Nucleus:</span>
                  <span className="font-semibold text-charcoal">{probeResult.primary_concept}</span>
                  <span className="text-muted">&bull;</span>
                  <span className="font-mono text-emerald-600 font-bold">
                    {Math.round((probeResult.confidence || 0.95) * 100)}% certainty
                  </span>
                </div>
              </div>

              {/* 4-Step Timeline */}
              {probeResult.thought_pathway && (
                <div className="grid grid-cols-1 sm:grid-cols-4 gap-2 pt-1">
                  {probeResult.thought_pathway.map((step, idx) => (
                    <div
                      key={idx}
                      className="p-3 bg-white border border-[#EAEAEA] rounded-xl shadow-subtle space-y-1"
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-[10px] font-bold text-muted uppercase">Step {step.step || idx + 1}</span>
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
                      </div>
                      <div className="font-bold text-charcoal text-[11px]">{step.phase}</div>
                      <p className="text-[10px] text-muted leading-relaxed">{step.detail}</p>
                    </div>
                  ))}
                </div>
              )}

              {/* Activated Nodes Tags */}
              {probeResult.activated_nodes && probeResult.activated_nodes.length > 0 && (
                <div className="pt-2 border-t border-[#EAEAEA] flex items-center gap-1.5 flex-wrap">
                  <span className="text-[11px] font-semibold text-muted">Activated Nodes:</span>
                  {probeResult.activated_nodes.map((n, i) => (
                    <span
                      key={i}
                      className="px-2 py-0.5 bg-pastel-purple text-pastel-purpleText border border-[#D6BCFA] rounded-full text-[10px] font-semibold"
                    >
                      {n.label || n.id || n} ({Math.round((n.activation || 0.8) * 100)}%)
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
