import React, { useState, useEffect } from 'react';
import { 
  Network, 
  FolderGit2, 
  Cpu, 
  CheckSquare, 
  GitCommit, 
  FileText, 
  GitFork, 
  Sliders, 
  BookOpen, 
  Filter, 
  RefreshCw, 
  ArrowRight,
  Info,
  X
} from 'lucide-react';
import { KnowledgeGraphView as IKnowledgeGraphView, KnowledgeEntity, KnowledgeRelation, EntityType } from '../../types';
import { apiService } from '../../services/api';

const ENTITY_ICONS: Record<EntityType, React.ElementType> = {
  project: FolderGit2,
  technology: Cpu,
  task: CheckSquare,
  decision: GitCommit,
  document: FileText,
  workflow: GitFork,
  preference: Sliders,
  knowledge_item: BookOpen,
};

export const KnowledgeGraphView: React.FC = () => {
  const [graphData, setGraphData] = useState<IKnowledgeGraphView>({
    entities: [],
    relations: [],
    total_entities: 0,
    total_relations: 0
  });
  const [loading, setLoading] = useState<boolean>(true);
  const [selectedProject, setSelectedProject] = useState<string>('');
  const [selectedType, setSelectedType] = useState<string>('all');
  const [activeEntity, setActiveEntity] = useState<KnowledgeEntity | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const loadGraph = async () => {
    try {
      setLoading(true);
      setErrorMsg(null);
      const data = await apiService.getKnowledgeGraph(
        selectedProject.trim() || undefined,
        selectedType === 'all' ? undefined : selectedType
      );
      setGraphData(data);
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to load knowledge graph');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadGraph();
  }, [selectedProject, selectedType]);

  const entityMap = new Map<string, KnowledgeEntity>();
  graphData.entities.forEach(e => entityMap.set(e.id, e));

  return (
    <div className="space-y-4">
      {/* Filter Toolbar */}
      <div className="p-3.5 rounded-lg bg-nova-surface/60 border border-nova-border/70 backdrop-blur-md flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2 text-xs font-mono text-nova-cyan">
            <Filter className="w-3.5 h-3.5" />
            <span>FILTER GRAPH:</span>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-[11px] font-mono text-slate-400">Project:</span>
            <input
              type="text"
              value={selectedProject}
              onChange={(e) => setSelectedProject(e.target.value)}
              placeholder="e.g. Nova (or blank)"
              className="bg-nova-dark/80 border border-nova-border rounded px-2.5 py-1 text-xs text-slate-200 font-mono focus:outline-none focus:border-nova-cyan w-36"
            />
          </div>

          <div className="flex items-center gap-2">
            <span className="text-[11px] font-mono text-slate-400">Entity Type:</span>
            <select
              value={selectedType}
              onChange={(e) => setSelectedType(e.target.value)}
              className="bg-nova-dark/80 border border-nova-border rounded px-2.5 py-1 text-xs text-slate-200 font-mono focus:outline-none focus:border-nova-cyan"
            >
              <option value="all">All Types</option>
              <option value="project">Project</option>
              <option value="technology">Technology</option>
              <option value="task">Task</option>
              <option value="decision">Decision</option>
              <option value="document">Document</option>
              <option value="workflow">Workflow</option>
              <option value="preference">Preference</option>
              <option value="knowledge_item">Knowledge Item</option>
            </select>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <span className="text-[11px] font-mono text-slate-400">
            {graphData.total_entities} Entities · {graphData.total_relations} Relations
          </span>
          <button
            onClick={loadGraph}
            className="p-1.5 rounded text-slate-400 hover:text-nova-cyan hover:bg-nova-surface border border-transparent hover:border-nova-border transition-all"
            title="Refresh graph"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {errorMsg && (
        <div className="p-3 rounded bg-red-950/60 border border-red-500/40 text-red-200 text-xs font-mono">
          {errorMsg}
        </div>
      )}

      {/* Main Graph Content: Two-column layout (Entities list + Relationship flow) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* Left Column: Entities (5 cols) */}
        <div className="lg:col-span-5 space-y-2">
          <h3 className="text-xs font-mono text-nova-cyan uppercase tracking-wider flex items-center justify-between pb-1 border-b border-nova-border/60">
            <span>Discovered Entities</span>
            <span className="text-[10px] text-slate-500">{graphData.entities.length} items</span>
          </h3>

          {graphData.entities.length === 0 ? (
            <div className="p-6 text-center border border-dashed border-nova-border/50 rounded-lg text-slate-500 font-mono text-xs">
              No entities in graph matching filter.
            </div>
          ) : (
            <div className="space-y-2 max-h-[520px] overflow-y-auto pr-1 custom-scrollbar">
              {graphData.entities.map((entity) => {
                const IconComponent = ENTITY_ICONS[entity.entity_type] || BookOpen;
                const isSelected = activeEntity?.id === entity.id;

                return (
                  <div
                    key={entity.id}
                    onClick={() => setActiveEntity(entity)}
                    className={`p-2.5 rounded-lg border cursor-pointer transition-all ${
                      isSelected
                        ? 'bg-nova-surface border-nova-cyan/80 shadow-[0_0_12px_rgba(0,240,255,0.2)]'
                        : 'bg-nova-surface/40 hover:bg-nova-surface/80 border-nova-border/60'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-1">
                      <div className="flex items-center gap-2">
                        <IconComponent className={`w-3.5 h-3.5 ${isSelected ? 'text-nova-cyan' : 'text-slate-400'}`} />
                        <span className="font-mono text-xs font-semibold text-slate-200">
                          {entity.name}
                        </span>
                      </div>
                      <span className="text-[9px] font-mono px-1.5 py-0.2 rounded bg-nova-dark/80 border border-nova-border text-slate-400 uppercase">
                        {entity.entity_type}
                      </span>
                    </div>

                    <div className="flex items-center justify-between text-[10px] font-mono text-slate-500">
                      <span>{entity.project_id ? `Project: ${entity.project_id}` : 'Global Scope'}</span>
                      <span>Confidence: {(entity.confidence * 100).toFixed(0)}%</span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Right Column: Relationships and Selected Entity Details (7 cols) */}
        <div className="lg:col-span-7 space-y-4">
          {/* Entity Details Card (if selected) */}
          {activeEntity && (
            <div className="p-4 rounded-lg bg-nova-surface/60 border border-nova-cyan/40 shadow-lg space-y-2">
              <div className="flex items-center justify-between border-b border-nova-border/60 pb-2">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-sm font-bold text-nova-cyan">
                    {activeEntity.name}
                  </span>
                  <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-nova-dark border border-nova-border text-slate-300 uppercase">
                    {activeEntity.entity_type}
                  </span>
                </div>
                <button
                  onClick={() => setActiveEntity(null)}
                  className="text-slate-400 hover:text-slate-200"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              <div className="grid grid-cols-2 gap-2 text-[11px] font-mono text-slate-400">
                <div>Source: <span className="text-slate-200">{activeEntity.source}</span></div>
                <div>Confidence: <span className="text-slate-200">{(activeEntity.confidence * 100).toFixed(0)}%</span></div>
                <div className="col-span-2">
                  ID: <span className="text-slate-400 select-all font-mono text-[10px]">{activeEntity.id}</span>
                </div>
              </div>

              {Object.keys(activeEntity.properties || {}).length > 0 && (
                <div className="pt-2 border-t border-nova-border/40">
                  <span className="text-[10px] font-mono text-slate-500 block mb-1">PROPERTIES</span>
                  <pre className="p-2 rounded bg-nova-dark/90 text-nova-teal text-[10px] font-mono overflow-x-auto">
                    {JSON.stringify(activeEntity.properties, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          )}

          {/* Relations Flow */}
          <div className="space-y-2">
            <h3 className="text-xs font-mono text-nova-cyan uppercase tracking-wider flex items-center justify-between pb-1 border-b border-nova-border/60">
              <span>Knowledge Relations</span>
              <span className="text-[10px] text-slate-500">{graphData.relations.length} relations</span>
            </h3>

            {graphData.relations.length === 0 ? (
              <div className="p-6 text-center border border-dashed border-nova-border/50 rounded-lg text-slate-500 font-mono text-xs">
                No relations found in graph for current selection.
              </div>
            ) : (
              <div className="space-y-2 max-h-[440px] overflow-y-auto pr-1 custom-scrollbar">
                {graphData.relations.map((rel) => {
                  const sourceEntity = entityMap.get(rel.source_id);
                  const targetEntity = entityMap.get(rel.target_id);

                  const sourceName = sourceEntity?.name || rel.source_id;
                  const targetName = targetEntity?.name || rel.target_id;

                  const isHighlighted = activeEntity && (activeEntity.id === rel.source_id || activeEntity.id === rel.target_id);

                  return (
                    <div
                      key={rel.id}
                      className={`p-3 rounded-lg border flex items-center justify-between gap-3 text-xs font-mono transition-all ${
                        isHighlighted
                          ? 'bg-nova-surface border-nova-cyan/70 shadow-[0_0_10px_rgba(0,240,255,0.15)]'
                          : 'bg-nova-surface/30 hover:bg-nova-surface/60 border-nova-border/50'
                      }`}
                    >
                      {/* Source */}
                      <div className="flex-1 min-w-0">
                        <span className="font-semibold text-slate-200 truncate block">
                          {sourceName}
                        </span>
                        <span className="text-[9px] text-slate-500 uppercase">
                          {sourceEntity?.entity_type || 'Entity'}
                        </span>
                      </div>

                      {/* Relation Badge */}
                      <div className="flex flex-col items-center flex-shrink-0 px-2">
                        <div className="flex items-center gap-1 text-nova-teal text-[10px] font-bold">
                          <span>{rel.relation_type}</span>
                          <ArrowRight className="w-3 h-3" />
                        </div>
                        <span className="text-[8px] text-slate-500">{(rel.confidence * 100).toFixed(0)}% conf</span>
                      </div>

                      {/* Target */}
                      <div className="flex-1 min-w-0 text-right">
                        <span className="font-semibold text-slate-200 truncate block">
                          {targetName}
                        </span>
                        <span className="text-[9px] text-slate-500 uppercase">
                          {targetEntity?.entity_type || 'Entity'}
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
