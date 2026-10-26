import { 
  SystemStatusResponse, 
  AiStatusResponse, 
  ChatMessage, 
  ActivityEvent, 
  NovaState,
  VoiceStatusResponse,
  AudioDevice,
  MemoryItem,
  ProjectItem,
  ConversationSummaryItem,
  MemoryStatsResponse,
  MemorySearchResponse,
  ToolDefinition,
  TaskPlan,
  ExecutionRecord,
  VisionStatus,
  WindowInfo,
  CaptureMetadata,
  OcrResult,
  VisionSettings,
  VisualAnalysisRequest,
  VisualAnalysisResponse,
  CaptureTarget,
  ImageFormat,
  AgentMetadata,
  WorkflowPlan,
  WorkflowStep,
  WorkflowEvent,
  WorkflowReport,
  WorkflowSummary,
  AutomationRule,
  AutomationCreate,
  AutomationUpdate,
  AutomationHistoryRecord,
  NotificationItem,
  ReminderItem,
  AutomationStatusResponse,
  RoutineTemplate,
  UserPreference,
  PreferenceCategory,
  PreferenceSource,
  Recommendation,
  KnowledgeGraphView,
  ResolvedContext,
  FeedbackRecord,
  FeedbackType,
  PersonalizationPrivacySettings,
  PersonalizationStatus,
  SystemHealthSummary,
  DatabaseStatus,
  BackupMetadata,
  RestorePreview,
  RecentErrorItem,
  OnboardingStatusResponse,
  OnboardingCompletePayload,
  UnifiedSettings
} from '../types';

const API_BASE = '/api';

export const apiService = {
  async getHealth() {
    const res = await fetch(`${API_BASE}/health`);
    if (!res.ok) throw new Error(`Health check failed: ${res.statusText}`);
    return res.json();
  },

  async getSystemStatus(): Promise<SystemStatusResponse> {
    const res = await fetch(`${API_BASE}/system/status`);
    if (!res.ok) throw new Error(`System status failed: ${res.statusText}`);
    return res.json();
  },

  async getAiStatus(): Promise<AiStatusResponse> {
    const res = await fetch(`${API_BASE}/ai/status`);
    if (!res.ok) throw new Error(`AI status failed: ${res.statusText}`);
    return res.json();
  },

  async selectModel(modelName: string): Promise<{ success: boolean; active_model: string }> {
    const res = await fetch(`${API_BASE}/ai/select-model`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ model_name: modelName }),
    });
    if (!res.ok) throw new Error(`Select model failed: ${res.statusText}`);
    return res.json();
  },

  async sendChat(
    message: string, 
    history: ChatMessage[] = [], 
    model?: string,
    sessionId: string = 'default'
  ) {
    const res = await fetch(`${API_BASE}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message,
        history: history.map(h => ({ role: h.role, content: h.content })),
        model,
        session_id: sessionId
      }),
    });
    if (!res.ok) throw new Error(`Chat request failed: ${res.statusText}`);
    return res.json();
  },

  async sendChatStream(
    message: string,
    history: ChatMessage[] = [],
    model?: string,
    onToken?: (token: string) => void,
    sessionId: string = 'default',
    signal?: AbortSignal
  ): Promise<{ success: boolean; response: string; model?: string; metrics?: any; request_id?: string }> {
    const res = await fetch(`${API_BASE}/chat/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message,
        history: history.map(h => ({ role: h.role, content: h.content })),
        model,
        session_id: sessionId
      }),
      signal
    });
    if (!res.ok || !res.body) {
      throw new Error(`Chat stream failed: ${res.statusText}`);
    }
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let assembled = '';
    let modelName = model;
    let metrics: any = undefined;
    let requestId: string | undefined;
    let success = true;
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';
      for (const line of lines) {
        if (!line.trim()) continue;
        try {
          const event = JSON.parse(line);
          if (event.type === 'token' && event.content) {
            assembled += event.content;
            onToken?.(event.content);
          }
          if (event.model) modelName = event.model;
          if (event.metrics) metrics = event.metrics;
          if (event.request_id) requestId = event.request_id;
          if (event.type === 'error') success = false;
        } catch {
          // ignore partial JSON
        }
      }
    }
    return { success, response: assembled, model: modelName, metrics, request_id: requestId };
  },

  async cancelChat(): Promise<void> {
    await fetch(`${API_BASE}/chat/cancel`, { method: 'POST' });
  },

  async updateInferenceSettings(payload: Record<string, unknown>): Promise<any> {
    const res = await fetch(`${API_BASE}/system/settings`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (!res.ok) throw new Error(`Failed to update inference settings: ${res.statusText}`);
    return res.json();
  },

  async getChatHistory(sessionId: string = 'default'): Promise<{ messages: ChatMessage[] }> {
    const res = await fetch(`${API_BASE}/chat/history?session_id=${sessionId}`);
    if (!res.ok) throw new Error(`Failed to load chat history: ${res.statusText}`);
    return res.json();
  },

  async clearChatHistory(sessionId: string = 'default'): Promise<boolean> {
    const res = await fetch(`${API_BASE}/chat/history?session_id=${sessionId}`, {
      method: 'DELETE',
    });
    return res.ok;
  },

  async setAssistantState(state: NovaState, message?: string) {
    const res = await fetch(`${API_BASE}/chat/state`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ state, message }),
    });
    return res.json();
  },

  async getRecentActivities(): Promise<{ activities: ActivityEvent[] }> {
    const res = await fetch(`${API_BASE}/activity/recent`);
    if (!res.ok) throw new Error(`Failed to load activities: ${res.statusText}`);
    return res.json();
  },

  // Voice Intelligence v0.2 API
  async getVoiceStatus(): Promise<VoiceStatusResponse> {
    const res = await fetch(`${API_BASE}/voice/status`);
    if (!res.ok) throw new Error(`Failed to get voice status: ${res.statusText}`);
    return res.json();
  },

  async startVoicePipeline(): Promise<{ success: boolean; running: boolean; message: string }> {
    const res = await fetch(`${API_BASE}/voice/start`, { method: 'POST' });
    if (!res.ok) throw new Error(`Failed to start voice: ${res.statusText}`);
    return res.json();
  },

  async stopVoicePipeline(): Promise<{ success: boolean; running: boolean; message: string }> {
    const res = await fetch(`${API_BASE}/voice/stop`, { method: 'POST' });
    if (!res.ok) throw new Error(`Failed to stop voice: ${res.statusText}`);
    return res.json();
  },

  async triggerListen(): Promise<{ success: boolean; mode: string }> {
    const res = await fetch(`${API_BASE}/voice/trigger-listen`, { method: 'POST' });
    if (!res.ok) throw new Error(`Failed to trigger listening: ${res.statusText}`);
    return res.json();
  },

  async stopListen(): Promise<{ success: boolean; mode: string }> {
    const res = await fetch(`${API_BASE}/voice/stop-listen`, { method: 'POST' });
    if (!res.ok) throw new Error(`Failed to stop listening: ${res.statusText}`);
    return res.json();
  },

  async speakText(text: string): Promise<{ success: boolean; text: string }> {
    const res = await fetch(`${API_BASE}/voice/speak`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text })
    });
    if (!res.ok) throw new Error(`Failed to speak text: ${res.statusText}`);
    return res.json();
  },

  async getAudioDevices(): Promise<{ inputs: AudioDevice[]; outputs: AudioDevice[] }> {
    const res = await fetch(`${API_BASE}/voice/devices`);
    if (!res.ok) throw new Error(`Failed to load audio devices: ${res.statusText}`);
    return res.json();
  },

  async updateVoiceSettings(payload: {
    wake_word_enabled?: boolean;
    wake_word_threshold?: number;
    input_device?: number;
    output_device?: number;
    tts_speech_rate?: number;
    tts_volume?: number;
    voice_mode?: string;
  }): Promise<{ success: boolean; settings: VoiceStatusResponse }> {
    const res = await fetch(`${API_BASE}/voice/settings`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error(`Failed to update voice settings: ${res.statusText}`);
    return res.json();
  },

  // Memory Intelligence v0.3 API
  async getMemoryStats(): Promise<MemoryStatsResponse> {
    const res = await fetch(`${API_BASE}/memory/stats`);
    if (!res.ok) throw new Error(`Failed to get memory stats: ${res.statusText}`);
    return res.json();
  },

  async getMemories(params?: { category?: string; project_id?: string; limit?: number }): Promise<{ total: number; memories: MemoryItem[] }> {
    const searchParams = new URLSearchParams();
    if (params?.category) searchParams.set('category', params.category);
    if (params?.project_id) searchParams.set('project_id', params.project_id);
    if (params?.limit) searchParams.set('limit', params.limit.toString());
    const query = searchParams.toString() ? `?${searchParams.toString()}` : '';
    const res = await fetch(`${API_BASE}/memory${query}`);
    if (!res.ok) throw new Error(`Failed to list memories: ${res.statusText}`);
    return res.json();
  },

  async searchMemories(query: string, category?: string, projectId?: string, limit?: number): Promise<MemorySearchResponse> {
    const searchParams = new URLSearchParams({ q: query });
    if (category) searchParams.set('category', category);
    if (projectId) searchParams.set('project_id', projectId);
    if (limit) searchParams.set('limit', limit.toString());
    const res = await fetch(`${API_BASE}/memory/search?${searchParams.toString()}`);
    if (!res.ok) throw new Error(`Failed to search memories: ${res.statusText}`);
    return res.json();
  },

  async createMemory(payload: {
    category: string;
    content: string;
    project_id?: string;
    tags?: string[];
    confidence?: number;
    metadata?: Record<string, any>;
  }): Promise<{ success: boolean; memory: MemoryItem }> {
    const res = await fetch(`${API_BASE}/memory`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error(`Failed to create memory: ${res.statusText}`);
    return res.json();
  },

  async updateMemory(memoryId: string, payload: {
    content?: string;
    category?: string;
    project_id?: string;
    tags?: string[];
  }): Promise<{ success: boolean; memory: MemoryItem }> {
    const res = await fetch(`${API_BASE}/memory/${memoryId}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error(`Failed to update memory: ${res.statusText}`);
    return res.json();
  },

  async deleteMemory(memoryId: string): Promise<{ success: boolean; message: string }> {
    const res = await fetch(`${API_BASE}/memory/${memoryId}`, { method: 'DELETE' });
    if (!res.ok) throw new Error(`Failed to delete memory: ${res.statusText}`);
    return res.json();
  },

  async getProjects(): Promise<{ total: number; projects: ProjectItem[] }> {
    const res = await fetch(`${API_BASE}/memory/projects`);
    if (!res.ok) throw new Error(`Failed to get projects: ${res.statusText}`);
    return res.json();
  },

  async getProject(projectId: string): Promise<ProjectItem> {
    const res = await fetch(`${API_BASE}/memory/projects/${projectId}`);
    if (!res.ok) throw new Error(`Failed to get project: ${res.statusText}`);
    return res.json();
  },

  async createProject(payload: {
    id: string;
    name: string;
    description?: string;
    tech_stack?: string[];
    status?: string;
  }): Promise<{ success: boolean; project: ProjectItem }> {
    const res = await fetch(`${API_BASE}/memory/projects`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error(`Failed to create project: ${res.statusText}`);
    return res.json();
  },

  async deleteProject(projectId: string): Promise<{ success: boolean; message: string }> {
    const res = await fetch(`${API_BASE}/memory/projects/${projectId}`, { method: 'DELETE' });
    if (!res.ok) throw new Error(`Failed to delete project: ${res.statusText}`);
    return res.json();
  },

  async extractMemories(text: string, projectId?: string): Promise<{ success: boolean; extracted_count: number; memories: MemoryItem[] }> {
    const res = await fetch(`${API_BASE}/memory/extract`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, project_id: projectId }),
    });
    if (!res.ok) throw new Error(`Failed to extract memories: ${res.statusText}`);
    return res.json();
  },

  async forgetMemory(query: string, projectId?: string): Promise<{ success: boolean; deleted_count: number; message: string }> {
    const res = await fetch(`${API_BASE}/memory/forget`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, project_id: projectId }),
    });
    if (!res.ok) throw new Error(`Failed to forget memory: ${res.statusText}`);
    return res.json();
  },

  // =========================================================================
  // Operational Tools & Execution v0.4 API
  // =========================================================================

  async getTools(category?: string, permission?: string): Promise<ToolDefinition[]> {
    const params = new URLSearchParams();
    if (category) params.append('category', category);
    if (permission) params.append('permission', permission);
    const qs = params.toString() ? `?${params.toString()}` : '';
    const res = await fetch(`${API_BASE}/tools${qs}`);
    if (!res.ok) throw new Error(`Failed to load tools: ${res.statusText}`);
    return res.json();
  },

  async getTool(toolId: string): Promise<ToolDefinition> {
    const res = await fetch(`${API_BASE}/tools/${toolId}`);
    if (!res.ok) throw new Error(`Failed to get tool '${toolId}': ${res.statusText}`);
    return res.json();
  },

  async planTask(prompt: string, projectId?: string, autoExecute: boolean = false): Promise<TaskPlan> {
    const res = await fetch(`${API_BASE}/tasks/plan`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prompt, project_id: projectId, auto_execute: autoExecute }),
    });
    if (!res.ok) throw new Error(`Task planning failed: ${res.statusText}`);
    return res.json();
  },

  async executeTask(taskId?: string, plan?: TaskPlan): Promise<TaskPlan> {
    const res = await fetch(`${API_BASE}/tasks/execute`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ task_id: taskId, plan }),
    });
    if (!res.ok) throw new Error(`Task execution failed: ${res.statusText}`);
    return res.json();
  },

  async approveTask(taskId: string): Promise<TaskPlan> {
    const res = await fetch(`${API_BASE}/tasks/${taskId}/approve`, {
      method: 'POST',
    });
    if (!res.ok) throw new Error(`Task approval failed: ${res.statusText}`);
    return res.json();
  },

  async rejectTask(taskId: string): Promise<TaskPlan> {
    const res = await fetch(`${API_BASE}/tasks/${taskId}/reject`, {
      method: 'POST',
    });
    if (!res.ok) throw new Error(`Task rejection failed: ${res.statusText}`);
    return res.json();
  },

  async cancelTask(taskId: string): Promise<TaskPlan> {
    const res = await fetch(`${API_BASE}/tasks/${taskId}/cancel`, {
      method: 'POST',
    });
    if (!res.ok) throw new Error(`Task cancellation failed: ${res.statusText}`);
    return res.json();
  },

  async listTasks(limit: number = 50): Promise<any[]> {
    const res = await fetch(`${API_BASE}/tasks?limit=${limit}`);
    if (!res.ok) throw new Error(`Failed to list tasks: ${res.statusText}`);
    return res.json();
  },

  async getTask(taskId: string): Promise<TaskPlan> {
    const res = await fetch(`${API_BASE}/tasks/${taskId}`);
    if (!res.ok) throw new Error(`Failed to get task: ${res.statusText}`);
    return res.json();
  },

  async listExecutions(limit: number = 50): Promise<ExecutionRecord[]> {
    const res = await fetch(`${API_BASE}/executions?limit=${limit}`);
    if (!res.ok) throw new Error(`Failed to list executions: ${res.statusText}`);
    return res.json();
  },

  async rollbackExecution(executionId: string): Promise<{ success: boolean; detail: string; action: string }> {
    const res = await fetch(`${API_BASE}/executions/${executionId}/rollback`, {
      method: 'POST',
    });
    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData.detail || `Rollback failed: ${res.statusText}`);
    }
    return res.json();
  },

  // Vision Intelligence v0.5 Endpoints
  async getVisionStatus(): Promise<VisionStatus> {
    const res = await fetch(`${API_BASE}/vision/status`);
    if (!res.ok) throw new Error(`Vision status failed: ${res.statusText}`);
    return res.json();
  },

  async listDesktopWindows(): Promise<WindowInfo[]> {
    const res = await fetch(`${API_BASE}/vision/windows`);
    if (!res.ok) throw new Error(`List windows failed: ${res.statusText}`);
    return res.json();
  },

  async captureScreen(
    target: CaptureTarget = 'PRIMARY',
    monitorIndex?: number,
    format: ImageFormat = 'PNG'
  ): Promise<CaptureMetadata> {
    let url = `${API_BASE}/vision/capture?target=${target}&format=${format}`;
    if (monitorIndex !== undefined && monitorIndex !== null) {
      url += `&monitor_index=${monitorIndex}`;
    }
    const res = await fetch(url, { method: 'POST' });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Screen capture failed: ${res.statusText}`);
    }
    return res.json();
  },

  async analyzeScreen(request: VisualAnalysisRequest): Promise<VisualAnalysisResponse> {
    const res = await fetch(`${API_BASE}/vision/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request)
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Visual analysis failed: ${res.statusText}`);
    }
    return res.json();
  },

  async extractOcr(captureId?: string): Promise<OcrResult> {
    const url = captureId ? `${API_BASE}/vision/ocr?capture_id=${encodeURIComponent(captureId)}` : `${API_BASE}/vision/ocr`;
    const res = await fetch(url, { method: 'POST' });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `OCR extraction failed: ${res.statusText}`);
    }
    return res.json();
  },

  async getVisionSettings(): Promise<VisionSettings> {
    const res = await fetch(`${API_BASE}/vision/settings`);
    if (!res.ok) throw new Error(`Failed to get vision settings: ${res.statusText}`);
    return res.json();
  },

  async updateVisionSettings(updates: Partial<VisionSettings>): Promise<VisionSettings> {
    const res = await fetch(`${API_BASE}/vision/settings`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(updates)
    });
    if (!res.ok) throw new Error(`Failed to update vision settings: ${res.statusText}`);
    return res.json();
  },

  async clearTemporaryCaptures(): Promise<{ status: string; cleared_count: number }> {
    const res = await fetch(`${API_BASE}/vision/clear`, { method: 'POST' });
    if (!res.ok) throw new Error(`Clear captures failed: ${res.statusText}`);
    return res.json();
  },

  // Agentic Workflows v0.6 Endpoints
  async listAgents(): Promise<AgentMetadata[]> {
    const res = await fetch(`${API_BASE}/agents`);
    if (!res.ok) throw new Error(`Failed to list agents: ${res.statusText}`);
    return res.json();
  },

  async getAgentById(agentId: string): Promise<AgentMetadata> {
    const res = await fetch(`${API_BASE}/agents/${agentId}`);
    if (!res.ok) throw new Error(`Failed to get agent ${agentId}: ${res.statusText}`);
    return res.json();
  },

  async getAgentStatus(): Promise<{ agents: Record<string, any>; active_workflows_count: number }> {
    const res = await fetch(`${API_BASE}/agents/status`);
    if (!res.ok) throw new Error(`Failed to get agent status: ${res.statusText}`);
    return res.json();
  },

  async listWorkflows(limit: number = 20): Promise<WorkflowSummary[]> {
    const res = await fetch(`${API_BASE}/workflows?limit=${limit}`);
    if (!res.ok) throw new Error(`Failed to list workflows: ${res.statusText}`);
    return res.json();
  },

  async getWorkflowById(workflowId: string): Promise<WorkflowPlan> {
    const res = await fetch(`${API_BASE}/workflows/${workflowId}`);
    if (!res.ok) throw new Error(`Failed to get workflow: ${res.statusText}`);
    return res.json();
  },

  async planWorkflow(objective: string, projectId?: string): Promise<WorkflowPlan> {
    const res = await fetch(`${API_BASE}/workflows/plan`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ objective, project_id: projectId })
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Failed to plan workflow: ${res.statusText}`);
    }
    return res.json();
  },

  async executeWorkflow(workflowId: string): Promise<WorkflowPlan> {
    const res = await fetch(`${API_BASE}/workflows/execute`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ workflow_id: workflowId })
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Failed to execute workflow: ${res.statusText}`);
    }
    return res.json();
  },

  async approveWorkflowStep(workflowId: string, stepId: number): Promise<WorkflowPlan> {
    const res = await fetch(`${API_BASE}/workflows/${workflowId}/approve`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ step_id: stepId })
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Failed to approve step: ${res.statusText}`);
    }
    return res.json();
  },

  async rejectWorkflowStep(workflowId: string, stepId: number, reason: string = 'Rejected by user'): Promise<WorkflowPlan> {
    const res = await fetch(`${API_BASE}/workflows/${workflowId}/reject`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ step_id: stepId, reason })
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Failed to reject step: ${res.statusText}`);
    }
    return res.json();
  },

  async cancelWorkflow(workflowId: string): Promise<WorkflowPlan> {
    const res = await fetch(`${API_BASE}/workflows/${workflowId}/cancel`, {
      method: 'POST'
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Failed to cancel workflow: ${res.statusText}`);
    }
    return res.json();
  },

  async resumeWorkflow(workflowId: string): Promise<WorkflowPlan> {
    const res = await fetch(`${API_BASE}/workflows/${workflowId}/resume`, {
      method: 'POST'
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Failed to resume workflow: ${res.statusText}`);
    }
    return res.json();
  },

  async getWorkflowEvents(workflowId: string): Promise<WorkflowEvent[]> {
    const res = await fetch(`${API_BASE}/workflows/${workflowId}/events`);
    if (!res.ok) throw new Error(`Failed to load workflow events: ${res.statusText}`);
    return res.json();
  },

  async getWorkflowReport(workflowId: string): Promise<WorkflowReport> {
    const res = await fetch(`${API_BASE}/workflows/${workflowId}/report`);
    if (!res.ok) throw new Error(`Failed to get workflow report: ${res.statusText}`);
    return res.json();
  },

  // ==================== v0.7 AUTOMATION & NOTIFICATIONS ====================

  async listAutomations(): Promise<AutomationRule[]> {
    const res = await fetch(`${API_BASE}/automations`);
    if (!res.ok) throw new Error(`Failed to list automations: ${res.statusText}`);
    return res.json();
  },

  async createAutomation(data: AutomationCreate): Promise<AutomationRule> {
    const res = await fetch(`${API_BASE}/automations`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Failed to create automation: ${res.statusText}`);
    }
    return res.json();
  },

  async getAutomation(id: string): Promise<AutomationRule> {
    const res = await fetch(`${API_BASE}/automations/${id}`);
    if (!res.ok) throw new Error(`Failed to get automation: ${res.statusText}`);
    return res.json();
  },

  async updateAutomation(id: string, updates: AutomationUpdate): Promise<AutomationRule> {
    const res = await fetch(`${API_BASE}/automations/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(updates)
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Failed to update automation: ${res.statusText}`);
    }
    return res.json();
  },

  async deleteAutomation(id: string): Promise<{ status: string; id: string }> {
    const res = await fetch(`${API_BASE}/automations/${id}`, {
      method: 'DELETE'
    });
    if (!res.ok) throw new Error(`Failed to delete automation: ${res.statusText}`);
    return res.json();
  },

  async enableAutomation(id: string): Promise<AutomationRule> {
    const res = await fetch(`${API_BASE}/automations/${id}/enable`, {
      method: 'POST'
    });
    if (!res.ok) throw new Error(`Failed to enable automation: ${res.statusText}`);
    return res.json();
  },

  async disableAutomation(id: string): Promise<AutomationRule> {
    const res = await fetch(`${API_BASE}/automations/${id}/disable`, {
      method: 'POST'
    });
    if (!res.ok) throw new Error(`Failed to disable automation: ${res.statusText}`);
    return res.json();
  },

  async runAutomation(id: string): Promise<{ status: string; result: any }> {
    const res = await fetch(`${API_BASE}/automations/${id}/run`, {
      method: 'POST'
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Failed to run automation: ${res.statusText}`);
    }
    return res.json();
  },

  async getAutomationHistory(id: string, limit: number = 50): Promise<AutomationHistoryRecord[]> {
    const res = await fetch(`${API_BASE}/automations/${id}/history?limit=${limit}`);
    if (!res.ok) throw new Error(`Failed to get history: ${res.statusText}`);
    return res.json();
  },

  async getAutomationStatus(): Promise<AutomationStatusResponse> {
    const res = await fetch(`${API_BASE}/automation/status`);
    if (!res.ok) throw new Error(`Failed to get automation status: ${res.statusText}`);
    return res.json();
  },

  async pauseAllAutomations(): Promise<{ status: string; message: string }> {
    const res = await fetch(`${API_BASE}/automation/pause-all`, {
      method: 'POST'
    });
    if (!res.ok) throw new Error(`Failed to pause automations: ${res.statusText}`);
    return res.json();
  },

  async resumeAllAutomations(): Promise<{ status: string; message: string }> {
    const res = await fetch(`${API_BASE}/automation/resume-all`, {
      method: 'POST'
    });
    if (!res.ok) throw new Error(`Failed to resume automations: ${res.statusText}`);
    return res.json();
  },

  async getRoutineTemplates(): Promise<RoutineTemplate[]> {
    const res = await fetch(`${API_BASE}/automation/templates`);
    if (!res.ok) throw new Error(`Failed to get templates: ${res.statusText}`);
    return res.json();
  },

  // Notifications
  async listNotifications(unreadOnly: boolean = false, limit: number = 50): Promise<NotificationItem[]> {
    const res = await fetch(`${API_BASE}/notifications?unread_only=${unreadOnly}&limit=${limit}`);
    if (!res.ok) throw new Error(`Failed to list notifications: ${res.statusText}`);
    return res.json();
  },

  async markNotificationRead(id: number): Promise<any> {
    const res = await fetch(`${API_BASE}/notifications/${id}/read`, {
      method: 'POST'
    });
    if (!res.ok) throw new Error(`Failed to mark read: ${res.statusText}`);
    return res.json();
  },

  async dismissNotification(id: number): Promise<any> {
    const res = await fetch(`${API_BASE}/notifications/${id}/dismiss`, {
      method: 'POST'
    });
    if (!res.ok) throw new Error(`Failed to dismiss: ${res.statusText}`);
    return res.json();
  },

  async snoozeNotification(id: number, minutes: number = 15): Promise<any> {
    const res = await fetch(`${API_BASE}/notifications/${id}/snooze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ minutes })
    });
    if (!res.ok) throw new Error(`Failed to snooze: ${res.statusText}`);
    return res.json();
  },

  async getNotificationPreferences(): Promise<any> {
    const res = await fetch(`${API_BASE}/notifications/preferences`);
    if (!res.ok) throw new Error(`Failed to get preferences: ${res.statusText}`);
    return res.json();
  },

  async updateNotificationPreferences(data: any): Promise<any> {
    const res = await fetch(`${API_BASE}/notifications/preferences`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    if (!res.ok) throw new Error(`Failed to update preferences: ${res.statusText}`);
    return res.json();
  },

  // Reminders
  async listReminders(pendingOnly: boolean = true): Promise<ReminderItem[]> {
    const res = await fetch(`${API_BASE}/reminders?pending_only=${pendingOnly}`);
    if (!res.ok) throw new Error(`Failed to list reminders: ${res.statusText}`);
    return res.json();
  },

  async createReminder(text: string, dueAt?: string, recurringCron?: string, projectId?: string): Promise<ReminderItem> {
    const res = await fetch(`${API_BASE}/reminders`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, due_at: dueAt, recurring_cron: recurringCron, project_id: projectId })
    });
    if (!res.ok) throw new Error(`Failed to create reminder: ${res.statusText}`);
    return res.json();
  },

  async completeReminder(id: number): Promise<any> {
    const res = await fetch(`${API_BASE}/reminders/${id}/complete`, {
      method: 'POST'
    });
    if (!res.ok) throw new Error(`Failed to complete reminder: ${res.statusText}`);
    return res.json();
  },

  async snoozeReminder(id: number, untilIso: string): Promise<any> {
    const res = await fetch(`${API_BASE}/reminders/${id}/snooze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ until_iso: untilIso })
    });
    if (!res.ok) throw new Error(`Failed to snooze reminder: ${res.statusText}`);
    return res.json();
  },

  async deleteReminder(id: number): Promise<any> {
    const res = await fetch(`${API_BASE}/reminders/${id}`, {
      method: 'DELETE'
    });
    if (!res.ok) throw new Error(`Failed to delete reminder: ${res.statusText}`);
    return res.json();
  },

  // ==========================================
  // NOVA v0.8 Personalization Engine
  // ==========================================
  async getPersonalizationStatus(): Promise<PersonalizationStatus> {
    const res = await fetch(`${API_BASE}/personalization/status`);
    if (!res.ok) throw new Error(`Failed to get personalization status: ${res.statusText}`);
    return res.json();
  },

  async getPreferences(category?: string, explicitOnly: boolean = false): Promise<UserPreference[]> {
    let url = `${API_BASE}/personalization/preferences?explicit_only=${explicitOnly}`;
    if (category) url += `&category=${category}`;
    const res = await fetch(url);
    if (!res.ok) throw new Error(`Failed to get preferences: ${res.statusText}`);
    return res.json();
  },

  async setPreference(pref: {
    key: string;
    category: PreferenceCategory;
    value: any;
    is_explicit?: boolean;
    source?: PreferenceSource;
    confidence?: number;
    context_scope?: string;
  }): Promise<UserPreference> {
    const res = await fetch(`${API_BASE}/personalization/preferences`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(pref),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Failed to set preference: ${res.statusText}`);
    }
    return res.json();
  },

  async updatePreference(id: number, update: { value?: any; confidence?: number; context_scope?: string }): Promise<UserPreference> {
    const res = await fetch(`${API_BASE}/personalization/preferences/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(update),
    });
    if (!res.ok) throw new Error(`Failed to update preference: ${res.statusText}`);
    return res.json();
  },

  async deletePreference(id: number): Promise<any> {
    const res = await fetch(`${API_BASE}/personalization/preferences/${id}`, {
      method: 'DELETE',
    });
    if (!res.ok) throw new Error(`Failed to delete preference: ${res.statusText}`);
    return res.json();
  },

  async getPersonalizationContext(conversationText?: string, explicitProject?: string): Promise<ResolvedContext> {
    let url = `${API_BASE}/personalization/context`;
    const params = new URLSearchParams();
    if (conversationText) params.append('conversation_text', conversationText);
    if (explicitProject) params.append('explicit_project', explicitProject);
    if (params.toString()) url += `?${params.toString()}`;
    const res = await fetch(url);
    if (!res.ok) throw new Error(`Failed to get context: ${res.statusText}`);
    return res.json();
  },

  async getRecommendations(limit: number = 10, includeDismissed: boolean = false): Promise<Recommendation[]> {
    const res = await fetch(`${API_BASE}/personalization/recommendations?limit=${limit}&include_dismissed=${includeDismissed}`);
    if (!res.ok) throw new Error(`Failed to get recommendations: ${res.statusText}`);
    return res.json();
  },

  async submitRecommendationFeedback(id: string, feedback: {
    feedback_type: FeedbackType;
    user_correction?: string;
  }): Promise<any> {
    const res = await fetch(`${API_BASE}/personalization/recommendations/${id}/feedback`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(feedback),
    });
    if (!res.ok) throw new Error(`Failed to submit feedback: ${res.statusText}`);
    return res.json();
  },

  async getKnowledgeGraph(projectId?: string, entityType?: string): Promise<KnowledgeGraphView> {
    let url = `${API_BASE}/personalization/knowledge-graph`;
    const params = new URLSearchParams();
    if (projectId) params.append('project_id', projectId);
    if (entityType) params.append('entity_type', entityType);
    if (params.toString()) url += `?${params.toString()}`;
    const res = await fetch(url);
    if (!res.ok) throw new Error(`Failed to get knowledge graph: ${res.statusText}`);
    return res.json();
  },

  async getKnowledgeGraphEntity(entityId: string): Promise<any> {
    const res = await fetch(`${API_BASE}/personalization/knowledge-graph/${entityId}`);
    if (!res.ok) throw new Error(`Failed to get entity: ${res.statusText}`);
    return res.json();
  },

  async refreshPersonalization(): Promise<any> {
    const res = await fetch(`${API_BASE}/personalization/refresh`, {
      method: 'POST',
    });
    if (!res.ok) throw new Error(`Failed to refresh personalization: ${res.statusText}`);
    return res.json();
  },

  async disablePersonalization(): Promise<any> {
    const res = await fetch(`${API_BASE}/personalization/disable`, {
      method: 'POST',
    });
    if (!res.ok) throw new Error(`Failed to disable personalization: ${res.statusText}`);
    return res.json();
  },

  async enablePersonalization(): Promise<any> {
    const res = await fetch(`${API_BASE}/personalization/enable`, {
      method: 'POST',
    });
    if (!res.ok) throw new Error(`Failed to enable personalization: ${res.statusText}`);
    return res.json();
  },

  async getPersonalizationPrivacySettings(): Promise<PersonalizationPrivacySettings> {
    const res = await fetch(`${API_BASE}/personalization/privacy/settings`);
    if (!res.ok) throw new Error(`Failed to get privacy settings: ${res.statusText}`);
    return res.json();
  },

  async updatePersonalizationPrivacySettings(settings: Partial<PersonalizationPrivacySettings>): Promise<PersonalizationPrivacySettings> {
    const res = await fetch(`${API_BASE}/personalization/privacy/settings`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(settings),
    });
    if (!res.ok) throw new Error(`Failed to update privacy settings: ${res.statusText}`);
    return res.json();
  },

  async clearPersonalizationData(includeExplicitPreferences: boolean = false): Promise<any> {
    const res = await fetch(`${API_BASE}/personalization/privacy/clear?include_explicit_preferences=${includeExplicitPreferences}`, {
      method: 'POST',
    });
    if (!res.ok) throw new Error(`Failed to clear personalization data: ${res.statusText}`);
    return res.json();
  },

  async getFeedbackHistory(limit: number = 50): Promise<FeedbackRecord[]> {
    const res = await fetch(`${API_BASE}/personalization/feedback/history?limit=${limit}`);
    if (!res.ok) throw new Error(`Failed to get feedback history: ${res.statusText}`);
    return res.json();
  },

  // ==========================================
  // NOVA v0.9 Reliability, Database & Security
  // ==========================================
  async getDetailedHealth(forceRefresh: boolean = false): Promise<SystemHealthSummary> {
    const res = await fetch(`${API_BASE}/system/health/detailed?force_refresh=${forceRefresh}`);
    if (!res.ok) throw new Error(`Failed to load system health: ${res.statusText}`);
    return res.json();
  },

  async getDiagnosticsSummary(): Promise<any> {
    const res = await fetch(`${API_BASE}/system/diagnostics`);
    if (!res.ok) throw new Error(`Failed to load diagnostics summary: ${res.statusText}`);
    return res.json();
  },

  async getResourceMetrics(): Promise<any> {
    const res = await fetch(`${API_BASE}/system/resources`);
    if (!res.ok) throw new Error(`Failed to load resource metrics: ${res.statusText}`);
    return res.json();
  },

  async getRecentErrors(limit: number = 20): Promise<RecentErrorItem[]> {
    const res = await fetch(`${API_BASE}/system/errors/recent?limit=${limit}`);
    if (!res.ok) throw new Error(`Failed to load recent errors: ${res.statusText}`);
    const data = await res.json();
    return data.errors || [];
  },

  async getDatabaseStatus(): Promise<DatabaseStatus> {
    const res = await fetch(`${API_BASE}/system/database/status`);
    if (!res.ok) throw new Error(`Failed to load database status: ${res.statusText}`);
    return res.json();
  },

  async listDatabaseBackups(): Promise<BackupMetadata[]> {
    const res = await fetch(`${API_BASE}/system/database/backups`);
    if (!res.ok) throw new Error(`Failed to list backups: ${res.statusText}`);
    return res.json();
  },

  async createDatabaseBackup(description?: string): Promise<{ success: boolean; backup: BackupMetadata }> {
    const res = await fetch(`${API_BASE}/system/database/backups`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ description })
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Failed to create backup: ${res.statusText}`);
    }
    return res.json();
  },

  async validateDatabaseBackup(backupId: string): Promise<any> {
    const res = await fetch(`${API_BASE}/system/database/backups/validate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ backup_id: backupId })
    });
    if (!res.ok) throw new Error(`Failed to validate backup: ${res.statusText}`);
    return res.json();
  },

  async previewDatabaseRestore(backupId: string): Promise<RestorePreview> {
    const res = await fetch(`${API_BASE}/system/database/restore/preview`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ backup_id: backupId })
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Failed to preview restore: ${res.statusText}`);
    }
    return res.json();
  },

  async executeDatabaseRestore(backupId: string, confirmed: boolean = true): Promise<any> {
    const res = await fetch(`${API_BASE}/system/database/restore/execute`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ backup_id: backupId, confirmed })
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Failed to restore database: ${res.statusText}`);
    }
    return res.json();
  },

  async exportDiagnostics(includeLogs: boolean = false): Promise<any> {
    const res = await fetch(`${API_BASE}/system/diagnostics/export`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ include_logs: includeLogs })
    });
    if (!res.ok) throw new Error(`Failed to export diagnostics: ${res.statusText}`);
    return res.json();
  },

  // ==========================================
  // NOVA v1.0 Release Onboarding & Settings
  // ==========================================
  async getOnboardingStatus(): Promise<OnboardingStatusResponse> {
    const res = await fetch(`${API_BASE}/system/onboarding/status`);
    if (!res.ok) throw new Error(`Failed to get onboarding status: ${res.statusText}`);
    return res.json();
  },

  async completeOnboarding(payload: OnboardingCompletePayload): Promise<any> {
    const res = await fetch(`${API_BASE}/system/onboarding/complete`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (!res.ok) throw new Error(`Failed to complete onboarding: ${res.statusText}`);
    return res.json();
  },

  async getUnifiedSettings(): Promise<UnifiedSettings> {
    const res = await fetch(`${API_BASE}/system/settings`);
    if (!res.ok) throw new Error(`Failed to get unified settings: ${res.statusText}`);
    return res.json();
  },

  async exportSettings(): Promise<any> {
    const res = await fetch(`${API_BASE}/system/settings/export`);
    if (!res.ok) throw new Error(`Failed to export settings: ${res.statusText}`);
    return res.json();
  },

  async importSettings(config: Record<string, any>): Promise<any> {
    const res = await fetch(`${API_BASE}/system/settings/import`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config)
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Failed to import settings: ${res.statusText}`);
    }
    return res.json();
  }
};
