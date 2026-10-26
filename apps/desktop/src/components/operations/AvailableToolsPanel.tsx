import React, { useState } from 'react';
import { 
  Wrench, 
  Search, 
  ShieldAlert, 
  ShieldCheck, 
  Shield, 
  Terminal, 
  Clock, 
  RotateCcw,
  CheckCircle2,
  Cpu,
  FolderTree,
  Globe,
  AppWindow
} from 'lucide-react';
import { ToolDefinition, ToolCategory, PermissionLevel } from '../../types';

interface AvailableToolsPanelProps {
  tools: ToolDefinition[];
  isLoading?: boolean;
}

export const AvailableToolsPanel: React.FC<AvailableToolsPanelProps> = ({
  tools,
  isLoading = false
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('ALL');
  const [selectedPermission, setSelectedPermission] = useState<string>('ALL');
  const [expandedToolId, setExpandedToolId] = useState<string | null>(null);

  const getCategoryIcon = (category: ToolCategory) => {
    switch (category) {
      case 'APPLICATION': return <AppWindow className="w-3.5 h-3.5 text-blue-400" />;
      case 'FILE_SYSTEM': return <FolderTree className="w-3.5 h-3.5 text-emerald-400" />;
      case 'SYSTEM_CONTROL': return <Cpu className="w-3.5 h-3.5 text-purple-400" />;
      case 'BROWSER': return <Globe className="w-3.5 h-3.5 text-cyan-400" />;
      default: return <Wrench className="w-3.5 h-3.5 text-slate-400" />;
    }
  };

  const getPermissionBadge = (level: PermissionLevel) => {
    switch (level) {
      case 'READ_ONLY':
        return (
          <span className="flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono bg-cyan-950/40 text-cyan-400 border border-cyan-500/30">
            <ShieldCheck className="w-3 h-3" />
            READ-ONLY
          </span>
        );
      case 'LOW_RISK':
        return (
          <span className="flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono bg-blue-950/40 text-blue-400 border border-blue-500/30">
            <Shield className="w-3 h-3" />
            LOW-RISK
          </span>
        );
      case 'CONFIRMATION_REQUIRED':
        return (
          <span className="flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono bg-amber-950/40 text-amber-400 border border-amber-500/30">
            <ShieldAlert className="w-3 h-3" />
            CONFIRMATION REQUIRED
          </span>
        );
      case 'BLOCKED':
        return (
          <span className="flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-mono bg-rose-950/40 text-rose-400 border border-rose-500/30">
            BLOCKED
          </span>
        );
    }
  };

  const filteredTools = tools.filter((tool) => {
    const matchesSearch = 
      tool.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      tool.id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      tool.description.toLowerCase().includes(searchTerm.toLowerCase());

    const matchesCategory = selectedCategory === 'ALL' || tool.category === selectedCategory;
    const matchesPermission = selectedPermission === 'ALL' || tool.permission_level === selectedPermission;

    return matchesSearch && matchesCategory && matchesPermission;
  });

  return (
    <div className="flex flex-col h-full space-y-3 font-sans">
      {/* Controls Bar: Search & Filters */}
      <div className="flex flex-wrap items-center justify-between gap-3 p-3 bg-nova-surface/60 rounded-xl border border-nova-border/60">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-2.5 w-4 h-4 text-slate-400" />
          <input
            type="text"
            placeholder="Search registered tools by name, ID, or keywords..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full bg-nova-dark/80 border border-nova-border/70 rounded-lg pl-9 pr-3 py-1.5 text-xs text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-nova-cyan/60"
          />
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {/* Category Filter */}
          <select
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value)}
            className="bg-nova-dark/80 border border-nova-border/70 rounded-lg px-2.5 py-1.5 text-xs text-slate-300 focus:outline-none focus:border-nova-cyan/60"
          >
            <option value="ALL">All Categories ({tools.length})</option>
            <option value="APPLICATION">Application Control</option>
            <option value="FILE_SYSTEM">File Intelligence</option>
            <option value="SYSTEM_CONTROL">System Control</option>
            <option value="BROWSER">Browser Operations</option>
          </select>

          {/* Permission Filter */}
          <select
            value={selectedPermission}
            onChange={(e) => setSelectedPermission(e.target.value)}
            className="bg-nova-dark/80 border border-nova-border/70 rounded-lg px-2.5 py-1.5 text-xs text-slate-300 focus:outline-none focus:border-nova-cyan/60"
          >
            <option value="ALL">All Permissions</option>
            <option value="READ_ONLY">Read-Only</option>
            <option value="LOW_RISK">Low-Risk</option>
            <option value="CONFIRMATION_REQUIRED">Confirmation Required</option>
          </select>
        </div>
      </div>

      {/* Tools Grid */}
      <div className="flex-1 overflow-y-auto space-y-2.5 pr-1 custom-scrollbar">
        {isLoading ? (
          <div className="flex items-center justify-center p-12 text-xs text-slate-400 font-mono">
            Loading verified tool definitions...
          </div>
        ) : filteredTools.length === 0 ? (
          <div className="flex flex-col items-center justify-center p-12 text-slate-400 border border-dashed border-nova-border/60 rounded-xl">
            <Wrench className="w-8 h-8 text-slate-600 mb-2" />
            <p className="text-xs">No registered tools match current filters.</p>
          </div>
        ) : (
          filteredTools.map((tool) => {
            const isExpanded = expandedToolId === tool.id;

            return (
              <div
                key={tool.id}
                className="bg-nova-surface/40 hover:bg-nova-surface/70 border border-nova-border/60 rounded-xl p-3.5 transition-all shadow-sm"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-start gap-2.5 flex-1">
                    <div className="p-2 rounded-lg bg-nova-dark/70 border border-nova-border/60 mt-0.5">
                      {getCategoryIcon(tool.category)}
                    </div>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <h3 className="text-xs font-bold text-slate-100 font-display tracking-wide">
                          {tool.name}
                        </h3>
                        <span className="text-[10px] font-mono text-nova-cyan bg-nova-cyan/10 px-1.5 py-0.5 rounded border border-nova-cyan/30">
                          {tool.id}
                        </span>
                        {tool.is_reversible && (
                          <span className="flex items-center gap-1 text-[9px] font-mono text-emerald-400 bg-emerald-950/30 px-1.5 py-0.5 rounded border border-emerald-500/30">
                            <RotateCcw className="w-2.5 h-2.5" />
                            REVERSIBLE
                          </span>
                        )}
                      </div>

                      <p className="text-xs text-slate-400 mt-1 leading-relaxed">
                        {tool.description}
                      </p>
                    </div>
                  </div>

                  <div className="flex flex-col items-end gap-1.5 flex-shrink-0">
                    {getPermissionBadge(tool.permission_level)}
                    <span className="flex items-center gap-1 text-[10px] font-mono text-slate-500">
                      <Clock className="w-2.5 h-2.5" />
                      {tool.timeout_seconds}s timeout
                    </span>
                  </div>
                </div>

                {/* Parameters Toggle */}
                {tool.parameters.length > 0 && (
                  <div className="mt-3 pt-2.5 border-t border-nova-border/40">
                    <button
                      onClick={() => setExpandedToolId(isExpanded ? null : tool.id)}
                      className="text-[11px] text-nova-cyan hover:text-nova-cyan/80 font-mono flex items-center gap-1 transition-colors"
                    >
                      <Terminal className="w-3 h-3" />
                      {isExpanded ? 'Hide Parameter Schema' : `View Schema (${tool.parameters.length} params)`}
                    </button>

                    {isExpanded && (
                      <div className="mt-2.5 p-2.5 bg-nova-dark/80 rounded-lg border border-nova-border/60 font-mono text-[11px] space-y-2">
                        <div className="text-[10px] text-slate-400 uppercase tracking-wider font-semibold">
                          Validated Arguments
                        </div>
                        <div className="space-y-1.5">
                          {tool.parameters.map((param) => (
                            <div key={param.name} className="flex items-start justify-between gap-2 border-b border-nova-border/20 pb-1">
                              <div>
                                <span className="text-nova-cyan font-bold">{param.name}</span>
                                <span className="text-slate-500 text-[10px] ml-1.5">({param.type})</span>
                                <p className="text-[10px] text-slate-400 font-sans mt-0.5">{param.description}</p>
                              </div>
                              <span className={`text-[9px] px-1.5 py-0.5 rounded ${
                                param.required ? 'bg-rose-950/40 text-rose-300' : 'bg-slate-800 text-slate-400'
                              }`}>
                                {param.required ? 'Required' : 'Optional'}
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
