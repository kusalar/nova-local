import React, { useState, useEffect, useMemo } from 'react';
import { 
  Database, 
  Search, 
  Plus, 
  Trash2, 
  Edit3, 
  FolderKanban, 
  Sparkles, 
  Layers, 
  CheckCircle2, 
  AlertCircle, 
  Clock, 
  Tag, 
  RefreshCw,
  X,
  Code2,
  Calendar,
  Zap,
  Cpu
} from 'lucide-react';
import { apiService } from '../../services/api';
import { 
  MemoryItem, 
  ProjectItem, 
  MemoryStatsResponse, 
  MemoryCategory 
} from '../../types';

interface MemoryCenterProps {
  onBackToDashboard?: () => void;
}

const CATEGORY_COLORS: Record<string, { bg: string; text: string; border: string; glow: string }> = {
  user_profile: { bg: 'bg-emerald-500/10', text: 'text-emerald-400', border: 'border-emerald-500/40', glow: '#10b981' },
  project: { bg: 'bg-cyan-500/10', text: 'text-cyan-400', border: 'border-cyan-500/40', glow: '#06b6d4' },
  conversation: { bg: 'bg-blue-500/10', text: 'text-blue-400', border: 'border-blue-500/40', glow: '#3b82f6' },
  task: { bg: 'bg-amber-500/10', text: 'text-amber-400', border: 'border-amber-500/40', glow: '#f59e0b' },
  knowledge: { bg: 'bg-purple-500/10', text: 'text-purple-400', border: 'border-purple-500/40', glow: '#a855f7' },
};

export const MemoryCenter: React.FC<MemoryCenterProps> = ({ onBackToDashboard }) => {
  const [activeCategory, setActiveCategory] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedProjectId, setSelectedProjectId] = useState<string>('all');
  
  // Data state
  const [stats, setStats] = useState<MemoryStatsResponse | null>(null);
  const [memories, setMemories] = useState<MemoryItem[]>([]);
  const [projects, setProjects] = useState<ProjectItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Modal state
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingMemory, setEditingMemory] = useState<MemoryItem | null>(null);
  const [modalForm, setModalForm] = useState({
    category: 'knowledge',
    content: '',
    project_id: '',
    tags: '',
  });

  // Extract memory direct modal
  const [extractInput, setExtractInput] = useState('');
  const [isExtracting, setIsExtracting] = useState(false);
  const [isExtractModalOpen, setIsExtractModalOpen] = useState(false);

  const loadAllData = async () => {
    setIsLoading(true);
    setErrorMsg(null);
    try {
      const [statsRes, memoriesRes, projectsRes] = await Promise.all([
        apiService.getMemoryStats(),
        apiService.getMemories({ limit: 100 }),
        apiService.getProjects(),
      ]);
      setStats(statsRes);
      setMemories(memoriesRes.memories || []);
      setProjects(projectsRes.projects || []);
    } catch (err: any) {
      console.error('Failed to load memory center data:', err);
      setErrorMsg(err.message || 'Error communicating with persistent memory engine.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadAllData();
  }, []);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) {
      loadAllData();
      return;
    }
    setIsLoading(true);
    try {
      const res = await apiService.searchMemories(
        searchQuery,
        activeCategory === 'all' ? undefined : activeCategory,
        selectedProjectId === 'all' ? undefined : selectedProjectId,
        50
      );
      setMemories(res.results.map((r) => r.memory));
    } catch (err: any) {
      console.error('Memory search error:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleDelete = async (memoryId: string) => {
    if (!window.confirm('Erase this neural memory node permanently?')) return;
    try {
      await apiService.deleteMemory(memoryId);
      setMemories((prev) => prev.filter((m) => m.id !== memoryId));
      if (stats) {
        setStats({
          ...stats,
          total_memories: Math.max(0, stats.total_memories - 1),
        });
      }
    } catch (err: any) {
      alert(`Failed to delete memory: ${err.message}`);
    }
  };

  const handleSaveModal = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!modalForm.content.trim()) return;

    try {
      const tagList = modalForm.tags
        .split(',')
        .map((t) => t.trim())
        .filter(Boolean);

      if (editingMemory) {
        const updated = await apiService.updateMemory(editingMemory.id, {
          content: modalForm.content,
          category: modalForm.category,
          project_id: modalForm.project_id || undefined,
          tags: tagList,
        });
        setMemories((prev) =>
          prev.map((m) => (m.id === editingMemory.id ? updated.memory : m))
        );
      } else {
        const created = await apiService.createMemory({
          category: modalForm.category,
          content: modalForm.content,
          project_id: modalForm.project_id || undefined,
          tags: tagList,
        });
        setMemories((prev) => [created.memory, ...prev]);
        if (stats) {
          setStats({
            ...stats,
            total_memories: stats.total_memories + 1,
          });
        }
      }
      setIsModalOpen(false);
      setEditingMemory(null);
    } catch (err: any) {
      alert(`Error saving memory: ${err.message}`);
    }
  };

  const handleRunExtraction = async () => {
    if (!extractInput.trim()) return;
    setIsExtracting(true);
    try {
      const res = await apiService.extractMemories(extractInput);
      alert(`Extraction complete! Discovered and retained ${res.extracted_count} memory items.`);
      setIsExtractModalOpen(false);
      setExtractInput('');
      loadAllData();
    } catch (err: any) {
      alert(`Extraction failed: ${err.message}`);
    } finally {
      setIsExtracting(false);
    }
  };

  // Filtered view
  const displayedMemories = useMemo(() => {
    return memories.filter((m) => {
      if (activeCategory !== 'all' && m.category !== activeCategory) return false;
      if (selectedProjectId !== 'all' && m.project_id !== selectedProjectId) return false;
      return true;
    });
  }, [memories, activeCategory, selectedProjectId]);

  // Constellation simulation nodes (top 8 memories)
  const constellationNodes = useMemo(() => {
    const subset = displayedMemories.slice(0, 8);
    const coords = [
      { x: 30, y: 35 },
      { x: 75, y: 20 },
      { x: 120, y: 40 },
      { x: 160, y: 25 },
      { x: 45, y: 80 },
      { x: 95, y: 70 },
      { x: 140, y: 85 },
      { x: 180, y: 60 },
    ];
    return subset.map((m, idx) => ({
      memory: m,
      x: coords[idx]?.x ?? (idx * 25 + 20),
      y: coords[idx]?.y ?? (40 + (idx % 2) * 30),
      color: CATEGORY_COLORS[m.category]?.glow || '#00f0ff',
    }));
  }, [displayedMemories]);

  return (
    <div className="flex-1 flex flex-col h-full overflow-hidden p-4 space-y-4 select-none">
      {/* Top Banner & Metrics HUD */}
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 bg-nova-surface/70 border border-nova-cyan/40 p-4 rounded-lg backdrop-blur-md shadow-[0_0_15px_rgba(0,240,255,0.08)]">
        <div>
          <div className="flex items-center gap-2">
            <Database className="w-5 h-5 text-nova-cyan animate-pulse" />
            <h1 className="font-display font-bold text-lg text-white tracking-widest uppercase">
              PERSISTENT MEMORY & INTELLIGENCE CENTER
            </h1>
            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-nova-cyan/20 text-nova-cyan border border-nova-cyan/40">
              v0.3 CORE
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1 font-mono">
            Autonomous local knowledge bank • BGE-Small-EN-v1.5 embeddings • Multi-Project Isolation
          </p>
        </div>

        {/* Quick Metric Badges */}
        <div className="flex items-center gap-3">
          <div className="hud-panel px-3 py-1.5 flex flex-col items-center">
            <span className="text-[10px] font-mono text-nova-cyanDim">TOTAL NODES</span>
            <span className="font-display font-bold text-base text-nova-cyan">
              {stats?.total_memories ?? memories.length}
            </span>
          </div>

          <div className="hud-panel px-3 py-1.5 flex flex-col items-center">
            <span className="text-[10px] font-mono text-nova-cyanDim">PROJECTS</span>
            <span className="font-display font-bold text-base text-white">
              {stats?.total_projects ?? projects.length}
            </span>
          </div>

          <div className="hud-panel px-3 py-1.5 flex flex-col items-center">
            <span className="text-[10px] font-mono text-nova-cyanDim">SUMMARIES</span>
            <span className="font-display font-bold text-base text-purple-400">
              {stats?.total_summaries ?? 0}
            </span>
          </div>

          <div className="flex gap-2 ml-2">
            <button
              onClick={() => {
                setEditingMemory(null);
                setModalForm({ category: 'knowledge', content: '', project_id: '', tags: '' });
                setIsModalOpen(true);
              }}
              className="hud-button flex items-center gap-1.5 text-xs py-2 px-3 font-semibold"
            >
              <Plus className="w-3.5 h-3.5" />
              <span>STORE FACT</span>
            </button>

            <button
              onClick={() => setIsExtractModalOpen(true)}
              className="hud-button flex items-center gap-1.5 text-xs py-2 px-3 border-purple-500/50 text-purple-400 hover:bg-purple-500/20 font-semibold"
            >
              <Sparkles className="w-3.5 h-3.5" />
              <span>AUTO-EXTRACT</span>
            </button>
          </div>
        </div>
      </div>

      {/* Main Grid: Neural Constellation & Project Explorer (Top) + Search & Table (Bottom) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4 flex-1 min-h-0 overflow-hidden">
        {/* Left Column: Neural Constellation Visualization + Project Workspaces */}
        <div className="lg:col-span-4 flex flex-col gap-4 overflow-y-auto custom-scrollbar">
          {/* Interactive Neural Constellation HUD */}
          <div className="hud-panel p-3.5 flex flex-col">
            <div className="flex items-center justify-between mb-2">
              <span className="font-display font-bold text-xs tracking-wider text-nova-cyan uppercase flex items-center gap-1.5">
                <Zap className="w-3.5 h-3.5 text-nova-cyan" />
                NEURAL CONSTELLATION GRAPH
              </span>
              <span className="text-[10px] font-mono text-nova-cyanDim">Active Cosine Space</span>
            </div>

            <div className="relative w-full h-44 bg-nova-dark/90 rounded border border-nova-cyan/20 overflow-hidden flex items-center justify-center">
              <svg className="w-full h-full" viewBox="0 0 210 110">
                {/* Simulated Constellation Connections */}
                {constellationNodes.map((n, i) =>
                  constellationNodes.slice(i + 1, i + 3).map((target, j) => (
                    <line
                      key={`line-${i}-${j}`}
                      x1={n.x}
                      y1={n.y}
                      x2={target.x}
                      y2={target.y}
                      stroke="#00f0ff"
                      strokeWidth="0.8"
                      opacity="0.3"
                      strokeDasharray="1 2"
                    />
                  ))
                )}

                {/* Animated Memory Points */}
                {constellationNodes.map((node, i) => (
                  <g key={`node-${i}`} className="cursor-pointer group">
                    <circle
                      cx={node.x}
                      cy={node.y}
                      r="4.5"
                      fill={node.color}
                      opacity="0.85"
                      className="group-hover:r-6 transition-all duration-300"
                    />
                    <circle
                      cx={node.x}
                      cy={node.y}
                      r="8"
                      stroke={node.color}
                      strokeWidth="0.8"
                      opacity="0.4"
                      className="animate-pulse"
                    />
                    <text
                      x={node.x + 6}
                      y={node.y + 3}
                      fill="#94a3b8"
                      fontSize="6.5"
                      fontFamily="monospace"
                    >
                      {node.memory.category.slice(0, 4).toUpperCase()}
                    </text>
                  </g>
                ))}
              </svg>

              {displayedMemories.length === 0 && (
                <span className="absolute text-xs font-mono text-slate-500">
                  No memory nodes matching current filter
                </span>
              )}
            </div>
            <div className="flex items-center justify-between mt-2 text-[10px] font-mono text-slate-400">
              <span>Embedding: {stats?.embedding_model || 'bge-small-en-v1.5'}</span>
              <span>Vector Dim: 384</span>
            </div>
          </div>

          {/* Project Intelligence Workspaces */}
          <div className="hud-panel p-3.5 flex flex-col flex-1">
            <div className="flex items-center justify-between mb-2">
              <span className="font-display font-bold text-xs tracking-wider text-white uppercase flex items-center gap-1.5">
                <FolderKanban className="w-3.5 h-3.5 text-nova-cyan" />
                PROJECT WORKSPACES ({projects.length})
              </span>
              <button
                onClick={() => setSelectedProjectId('all')}
                className={`text-[10px] font-mono uppercase px-1.5 py-0.5 rounded transition ${
                  selectedProjectId === 'all'
                    ? 'bg-nova-cyan text-black font-bold'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                All Projects
              </button>
            </div>

            <div className="space-y-2 overflow-y-auto max-h-60 pr-1 custom-scrollbar">
              {projects.map((proj) => {
                const isSelected = selectedProjectId === proj.id;
                return (
                  <div
                    key={proj.id}
                    onClick={() => setSelectedProjectId(isSelected ? 'all' : proj.id)}
                    className={`p-2.5 rounded border transition-all cursor-pointer ${
                      isSelected
                        ? 'bg-nova-cyan/15 border-nova-cyan shadow-[0_0_8px_rgba(0,240,255,0.25)]'
                        : 'bg-nova-surface/40 border-nova-border/60 hover:border-nova-cyan/40'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="font-display font-semibold text-xs text-white">
                        {proj.name}
                      </span>
                      <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-nova-cyan/10 text-nova-cyan border border-nova-cyan/30">
                        {proj.status.toUpperCase()}
                      </span>
                    </div>

                    <p className="text-[11px] text-slate-400 mt-1 line-clamp-2">
                      {proj.description || 'No description logged.'}
                    </p>

                    {/* Tech Stack Chips */}
                    {proj.tech_stack && proj.tech_stack.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-2">
                        {proj.tech_stack.map((tech, idx) => (
                          <span
                            key={idx}
                            className="text-[9px] font-mono px-1.5 py-0.2 rounded bg-slate-800 text-slate-300 border border-slate-700 flex items-center gap-1"
                          >
                            <Code2 className="w-2.5 h-2.5 text-nova-cyan" />
                            {tech}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Right Column: Search, Category Filters, and Memory Ledger */}
        <div className="lg:col-span-8 flex flex-col gap-3 min-h-0">
          {/* Filter Bar & Semantic Search Input */}
          <div className="hud-panel p-3 flex flex-col gap-3">
            <form onSubmit={handleSearch} className="flex items-center gap-2">
              <div className="relative flex-1">
                <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
                <input
                  type="text"
                  placeholder="Semantic inquiry or keyword retrieval (e.g. 'FastAPI tech stack', 'Tauri backend')..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full bg-nova-dark/80 border border-nova-border/70 rounded px-3 py-2 pl-9 text-xs font-mono text-slate-200 focus:outline-none focus:border-nova-cyan"
                />
              </div>

              <button
                type="submit"
                className="hud-button text-xs py-2 px-4 flex items-center gap-1.5 font-semibold"
              >
                <span>SEARCH</span>
              </button>

              <button
                type="button"
                onClick={() => {
                  setSearchQuery('');
                  loadAllData();
                }}
                className="p-2 border border-nova-border rounded text-slate-400 hover:text-white hover:border-nova-cyan/50"
                title="Reload memories"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
              </button>
            </form>

            {/* Category Pills */}
            <div className="flex flex-wrap items-center gap-2 pt-1 border-t border-nova-border/40">
              <span className="text-[10px] font-mono text-nova-textDim uppercase mr-1">
                CATEGORY:
              </span>
              {[
                { id: 'all', label: 'All Categories' },
                { id: 'user_profile', label: 'User Profile' },
                { id: 'project', label: 'Project Intelligence' },
                { id: 'conversation', label: 'Conversation' },
                { id: 'task', label: 'Tasks' },
                { id: 'knowledge', label: 'Knowledge' },
              ].map((cat) => {
                const isActive = activeCategory === cat.id;
                return (
                  <button
                    key={cat.id}
                    onClick={() => setActiveCategory(cat.id)}
                    className={`text-xs px-2.5 py-1 rounded-md font-mono transition-all ${
                      isActive
                        ? 'bg-nova-cyan text-black font-bold shadow-[0_0_8px_rgba(0,240,255,0.4)]'
                        : 'bg-nova-surface text-slate-300 hover:text-white border border-nova-border/60 hover:border-nova-cyan/40'
                    }`}
                  >
                    {cat.label}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Memory Node Feed / Ledger */}
          <div className="hud-panel p-3 flex-1 flex flex-col min-h-0 overflow-hidden">
            <div className="flex items-center justify-between pb-2 border-b border-nova-border/50 text-[11px] font-mono text-slate-400">
              <span>LEDGER ENTRIES ({displayedMemories.length})</span>
              <span>FILTER: {activeCategory.toUpperCase()} • PROJECT: {selectedProjectId.toUpperCase()}</span>
            </div>

            <div className="flex-1 overflow-y-auto space-y-2 mt-2 pr-1 custom-scrollbar">
              {displayedMemories.length === 0 ? (
                <div className="flex flex-col items-center justify-center h-48 text-center text-slate-500">
                  <Database className="w-8 h-8 mb-2 opacity-40 text-nova-cyan" />
                  <p className="text-xs font-mono">No persistent memory items registered in this segment.</p>
                  <p className="text-[11px] text-slate-600 mt-1">
                    Direct NOVA verbally or click 'Store Fact' to commit new neural state.
                  </p>
                </div>
              ) : (
                displayedMemories.map((mem) => {
                  const style = CATEGORY_COLORS[mem.category] || CATEGORY_COLORS.knowledge;
                  return (
                    <div
                      key={mem.id}
                      className="p-3 rounded bg-nova-surface/40 border border-nova-border/70 hover:border-nova-cyan/40 transition-all flex flex-col gap-2 group"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex items-center gap-2">
                          <span
                            className={`text-[10px] font-mono uppercase px-2 py-0.5 rounded border ${style.bg} ${style.text} ${style.border}`}
                          >
                            {mem.category.replace('_', ' ')}
                          </span>

                          {mem.project_id && (
                            <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-cyan-950/40 text-cyan-300 border border-cyan-800 flex items-center gap-1">
                              <FolderKanban className="w-2.5 h-2.5" />
                              {mem.project_id}
                            </span>
                          )}

                          <span className="text-[10px] font-mono text-slate-500">
                            ID: {mem.id.slice(0, 8)}
                          </span>
                        </div>

                        {/* Action buttons */}
                        <div className="flex items-center gap-1 opacity-70 group-hover:opacity-100 transition-opacity">
                          <button
                            onClick={() => {
                              setEditingMemory(mem);
                              setModalForm({
                                category: mem.category,
                                content: mem.content,
                                project_id: mem.project_id || '',
                                tags: (mem.tags || []).join(', '),
                              });
                              setIsModalOpen(true);
                            }}
                            className="p-1 text-slate-400 hover:text-nova-cyan rounded"
                            title="Edit memory"
                          >
                            <Edit3 className="w-3.5 h-3.5" />
                          </button>
                          <button
                            onClick={() => handleDelete(mem.id)}
                            className="p-1 text-slate-400 hover:text-red-400 rounded"
                            title="Delete memory"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </div>

                      {/* Content */}
                      <p className="text-xs text-slate-200 font-sans leading-relaxed">
                        {mem.content}
                      </p>

                      {/* Footer: Tags, Timestamp, Access count */}
                      <div className="flex items-center justify-between pt-1 border-t border-nova-border/30 text-[10px] font-mono text-slate-500">
                        <div className="flex items-center gap-1 flex-wrap">
                          {mem.tags && mem.tags.length > 0 && (
                            <>
                              <Tag className="w-2.5 h-2.5 text-nova-cyan" />
                              {mem.tags.map((t, idx) => (
                                <span key={idx} className="text-slate-400">
                                  #{t}
                                </span>
                              ))}
                            </>
                          )}
                        </div>

                        <div className="flex items-center gap-3">
                          <span>Accessed: {mem.access_count}x</span>
                          <span>
                            {new Date(mem.created_at).toLocaleDateString()} {new Date(mem.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                          </span>
                        </div>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Modal: Create / Edit Memory */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-nova-surface border border-nova-cyan/60 rounded-lg p-5 w-full max-w-lg shadow-[0_0_30px_rgba(0,240,255,0.2)]">
            <div className="flex items-center justify-between pb-3 border-b border-nova-border">
              <h2 className="font-display font-bold text-sm text-white tracking-wider flex items-center gap-2">
                <Database className="w-4 h-4 text-nova-cyan" />
                {editingMemory ? 'EDIT NEURAL MEMORY NODE' : 'STORE NEW MEMORY FACT'}
              </h2>
              <button
                onClick={() => setIsModalOpen(false)}
                className="text-slate-400 hover:text-white"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <form onSubmit={handleSaveModal} className="space-y-3 mt-4">
              <div>
                <label className="text-xs font-mono text-slate-300 block mb-1">
                  CATEGORY:
                </label>
                <select
                  value={modalForm.category}
                  onChange={(e) => setModalForm({ ...modalForm, category: e.target.value })}
                  className="w-full bg-nova-dark border border-nova-border rounded px-3 py-1.5 text-xs font-mono text-white focus:outline-none focus:border-nova-cyan"
                >
                  <option value="knowledge">Knowledge</option>
                  <option value="project">Project Intelligence</option>
                  <option value="user_profile">User Profile</option>
                  <option value="task">Task / Deadline</option>
                  <option value="conversation">Conversation Fact</option>
                </select>
              </div>

              <div>
                <label className="text-xs font-mono text-slate-300 block mb-1">
                  PROJECT SCOPE (OPTIONAL):
                </label>
                <input
                  type="text"
                  placeholder="e.g. 'nova', 'hirelens'"
                  value={modalForm.project_id}
                  onChange={(e) => setModalForm({ ...modalForm, project_id: e.target.value })}
                  className="w-full bg-nova-dark border border-nova-border rounded px-3 py-1.5 text-xs font-mono text-white focus:outline-none focus:border-nova-cyan"
                />
              </div>

              <div>
                <label className="text-xs font-mono text-slate-300 block mb-1">
                  MEMORY CONTENT:
                </label>
                <textarea
                  rows={4}
                  required
                  placeholder="Describe the exact detail, decision, tech stack, or fact to retain..."
                  value={modalForm.content}
                  onChange={(e) => setModalForm({ ...modalForm, content: e.target.value })}
                  className="w-full bg-nova-dark border border-nova-border rounded px-3 py-2 text-xs font-sans text-white focus:outline-none focus:border-nova-cyan resize-none"
                />
              </div>

              <div>
                <label className="text-xs font-mono text-slate-300 block mb-1">
                  TAGS (COMMA-SEPARATED):
                </label>
                <input
                  type="text"
                  placeholder="backend, tauri, fastembed, decision"
                  value={modalForm.tags}
                  onChange={(e) => setModalForm({ ...modalForm, tags: e.target.value })}
                  className="w-full bg-nova-dark border border-nova-border rounded px-3 py-1.5 text-xs font-mono text-white focus:outline-none focus:border-nova-cyan"
                />
              </div>

              <div className="flex items-center justify-end gap-2 pt-3 border-t border-nova-border">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-3 py-1.5 rounded text-xs font-mono text-slate-400 hover:text-white"
                >
                  CANCEL
                </button>
                <button
                  type="submit"
                  className="hud-button text-xs py-1.5 px-4 font-semibold"
                >
                  SAVE NODE
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Modal: Auto-Extract from text snippet */}
      {isExtractModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-nova-surface border border-purple-500/60 rounded-lg p-5 w-full max-w-lg shadow-[0_0_30px_rgba(168,85,247,0.2)]">
            <div className="flex items-center justify-between pb-3 border-b border-nova-border">
              <h2 className="font-display font-bold text-sm text-white tracking-wider flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-purple-400" />
                INTELLIGENT MEMORY EXTRACTION
              </h2>
              <button
                onClick={() => setIsExtractModalOpen(false)}
                className="text-slate-400 hover:text-white"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="mt-3 space-y-3">
              <p className="text-xs text-slate-400 font-sans">
                Paste any unstructured text or meeting notes. NOVA will automatically extract projects, tech stacks, tasks, and user preferences while filtering sensitive credentials.
              </p>

              <textarea
                rows={5}
                placeholder="Example: 'I am building HireLens AI using FastAPI and React. Current goal is deploying on AWS by Friday.'"
                value={extractInput}
                onChange={(e) => setExtractInput(e.target.value)}
                className="w-full bg-nova-dark border border-nova-border rounded px-3 py-2 text-xs font-sans text-white focus:outline-none focus:border-purple-500 resize-none"
              />

              <div className="flex items-center justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setIsExtractModalOpen(false)}
                  className="px-3 py-1.5 rounded text-xs font-mono text-slate-400 hover:text-white"
                >
                  CANCEL
                </button>
                <button
                  onClick={handleRunExtraction}
                  disabled={isExtracting || !extractInput.trim()}
                  className="hud-button text-xs py-1.5 px-4 font-semibold border-purple-500/50 text-purple-300 hover:bg-purple-500/20 disabled:opacity-50"
                >
                  {isExtracting ? 'ANALYZING...' : 'RUN EXTRACTION'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
