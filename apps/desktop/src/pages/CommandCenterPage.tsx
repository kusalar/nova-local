import React, { useState, useCallback } from 'react';
import { TopNav } from '../components/dashboard/TopNav';
import { LeftSidebar } from '../components/dashboard/LeftSidebar';
import { NovaOrb } from '../components/dashboard/NovaOrb';
import { AiCoreOverview } from '../components/dashboard/AiCoreOverview';
import { LiveFeed } from '../components/dashboard/LiveFeed';
import { ActiveAgents } from '../components/dashboard/ActiveAgents';
import { MissionTimeline } from '../components/dashboard/MissionTimeline';
import { QuickCommands } from '../components/dashboard/QuickCommands';
import { SystemMonitor } from '../components/dashboard/SystemMonitor';
import { MemoryInsights } from '../components/dashboard/MemoryInsights';
import { LlmStatus } from '../components/dashboard/LlmStatus';
import { BottomBar } from '../components/dashboard/BottomBar';
import { ChatConsoleModal } from '../components/chat/ChatConsoleModal';
import { SettingsModal } from '../components/dashboard/SettingsModal';
import { ExecutiveBriefingModal } from '../components/dashboard/ExecutiveBriefingModal';
import { MemoryCenter } from '../components/memory/MemoryCenter';
import { OperationsCenter } from '../components/operations/OperationsCenter';
import { VisionCenter } from '../components/vision/VisionCenter';
import { AgentCommandCenter } from '../components/agents/AgentCommandCenter';
import { AutomationCenter } from '../components/automation/AutomationCenter';
import { PersonalizationCenter } from '../components/personalization/PersonalizationCenter';
import { SystemReliabilityCenter } from '../components/diagnostics/SystemReliabilityCenter';
import { OnboardingWizard } from '../components/onboarding/OnboardingWizard';
import { apiService } from '../services/api';

import { useSystemStats } from '../hooks/useSystemStats';
import { useAiStatus } from '../hooks/useAiStatus';
import { useChat } from '../hooks/useChat';
import { useVoice } from '../hooks/useVoice';
import { NovaState } from '../types';

export const CommandCenterPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState('command-center');
  const [focusMode, setFocusMode] = useState(false);
  const [assistantState, setAssistantState] = useState<NovaState>('IDLE');
  const [statusMessage, setStatusMessage] = useState('NOVA SYSTEM ONLINE');
  
  // Modals
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [isBriefingOpen, setIsBriefingOpen] = useState(false);
  const [isOnboardingOpen, setIsOnboardingOpen] = useState(false);

  // Probe first-run onboarding status on initial mount
  React.useEffect(() => {
    let isMounted = true;
    apiService.getOnboardingStatus()
      .then((data) => {
        if (isMounted && data.is_first_run) {
          setIsOnboardingOpen(true);
        }
      })
      .catch((err) => console.warn('Could not check onboarding status:', err));
    return () => { isMounted = false; };
  }, []);

  // Real-time hooks
  const { data: systemStats, isBackendConnected } = useSystemStats(3000);
  const { status: aiStatus, changeModel } = useAiStatus(5000);

  const handleStateChange = useCallback((newState: NovaState, msg?: string) => {
    setAssistantState(newState);
    if (msg) setStatusMessage(msg);
  }, []);

  const {
    messages,
    isLoading: isChatLoading,
    sendMessage,
    clearMessages,
    voiceEnabled,
    setVoiceEnabled,
    reloadHistory
  } = useChat(handleStateChange);

  const handleSpeechRecognized = useCallback((text: string) => {
    console.log('[Voice STT Result]:', text);
    setStatusMessage(`HEARD: "${text}"`);
    reloadHistory();
  }, [reloadHistory]);

  const handleAssistantSpoke = useCallback((text: string, model?: string) => {
    console.log('[Voice Piper Spoken]:', text);
    reloadHistory();
  }, [reloadHistory]);

  // Real offline voice intelligence hook (v0.2)
  const voice = useVoice({
    onStateChange: handleStateChange,
    onSpeechRecognized: handleSpeechRecognized,
    onAssistantSpoke: handleAssistantSpoke
  });

  const handleMicToggle = () => {
    if (voice.isSpeaking) {
      voice.stopSpeaking();
      handleStateChange('IDLE', 'VOCAL PLAYBACK INTERRUPTED');
      return;
    }
    
    if (assistantState === 'LISTENING') {
      voice.stopListen();
      handleStateChange('IDLE', 'NOVA SYSTEM ONLINE');
    } else {
      voice.triggerListen();
    }
  };

  const handleOrbClick = () => {
    if (voice.isSpeaking) {
      voice.stopSpeaking();
      handleStateChange('IDLE', 'VOCAL PLAYBACK INTERRUPTED');
    } else if (assistantState === 'LISTENING') {
      voice.stopListen();
      handleStateChange('IDLE', 'NOVA SYSTEM ONLINE');
    } else {
      voice.triggerListen();
    }
  };

  const handleExecutiveBriefing = () => {
    setIsBriefingOpen(true);
  };

  return (
    <div className="flex flex-col h-screen w-screen overflow-hidden bg-nova-dark text-slate-100 select-none scanlines">
      {/* Top Navigation */}
      <TopNav
        onOpenSettings={() => setIsSettingsOpen(true)}
        onOpenChat={() => setIsChatOpen(true)}
        systemStatusText={systemStats.status.toUpperCase()}
        isBackendConnected={isBackendConnected}
      />

      {/* Main Workspace Body */}
      <div className="flex flex-1 overflow-hidden relative">
        {/* Left Navigation Sidebar (Hidden in full focus mode) */}
        {!focusMode && (
          <LeftSidebar
            activeTab={activeTab}
            setActiveTab={setActiveTab}
            assistantState={assistantState}
            onMicClick={handleMicToggle}
            onOpenChat={() => setIsChatOpen(true)}
            focusMode={focusMode}
            setFocusMode={setFocusMode}
            isVoiceRunning={voice.isVoiceRunning}
            wakeWordEnabled={voice.wakeWordEnabled}
            activeWakePhrase={voice.activeWakePhrase}
            audioLevel={voice.audioLevel}
          />
        )}

        {/* Dashboard Canvas Area, Memory Center, Operations Center, Vision Center, or Agent Command Center */}
        {activeTab === 'memory' ? (
          <MemoryCenter onBackToDashboard={() => setActiveTab('command-center')} />
        ) : activeTab === 'operations' || activeTab === 'tools-skills' || activeTab === 'tasks' ? (
          <OperationsCenter onBackToDashboard={() => setActiveTab('command-center')} />
        ) : activeTab === 'vision' ? (
          <VisionCenter 
            onBackToDashboard={() => setActiveTab('command-center')} 
            onSpeakText={(text) => apiService.speakText(text)}
          />
        ) : activeTab === 'agents' || activeTab === 'workflows' ? (
          <AgentCommandCenter onBackToDashboard={() => setActiveTab('command-center')} />
        ) : activeTab === 'automations' ? (
          <AutomationCenter />
        ) : activeTab === 'personalization' ? (
          <PersonalizationCenter onBackToDashboard={() => setActiveTab('command-center')} />
        ) : activeTab === 'reliability' || activeTab === 'diagnostics' ? (
          <SystemReliabilityCenter onBackToDashboard={() => setActiveTab('command-center')} />
        ) : (
          <main className="flex-1 overflow-y-auto p-4 space-y-3.5 custom-scrollbar">
            {/* Top Hero Section: AI Core Overview | Central Holographic Orb | Live Intelligence Feed */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-3.5 items-stretch">
              {/* Left AI Core Overview (col-span-3) */}
              <div className="lg:col-span-3 min-h-[290px]">
                <AiCoreOverview
                  aiStatus={aiStatus}
                  systemStats={systemStats}
                  onOpenLlmModal={() => setIsSettingsOpen(true)}
                />
              </div>

              {/* Center AI Orb (col-span-6) */}
              <div className="lg:col-span-6 flex items-center justify-center hud-panel min-h-[290px]">
                <NovaOrb
                  state={assistantState}
                  statusMessage={statusMessage}
                  onClick={handleOrbClick}
                  partialTranscript={voice.partialTranscript}
                  lastTranscript={voice.lastRecognizedText}
                  audioLevel={voice.audioLevel}
                />
              </div>

              {/* Right Live Intelligence Feed (col-span-3) */}
              <div className="lg:col-span-3 min-h-[290px]">
                <LiveFeed
                  onOpenFeed={() => setIsChatOpen(true)}
                  cpuPercent={systemStats.telemetry?.cpu?.percent ?? 15}
                />
              </div>
            </div>

            {/* Middle Row: Active Agents | Mission Timeline | Quick Commands */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-3.5 items-stretch">
              <div className="lg:col-span-6 min-h-[170px]">
                <ActiveAgents />
              </div>

              <div className="lg:col-span-4 min-h-[170px]">
                <MissionTimeline />
              </div>

              <div className="lg:col-span-2 min-h-[170px]">
                <QuickCommands
                  onStartChat={() => setIsChatOpen(true)}
                  onVoiceClick={handleMicToggle}
                  onNewTask={() => {
                    setIsChatOpen(true);
                    sendMessage('Start new operational task: Review NOVA architecture');
                  }}
                />
              </div>
            </div>

            {/* Bottom Row: System Monitor | Memory Insights | LLM Status */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-3.5 items-stretch">
              <div className="lg:col-span-4 min-h-[190px]">
                <SystemMonitor stats={systemStats} />
              </div>

              <div className="lg:col-span-4 min-h-[190px]">
                <MemoryInsights
                  stats={systemStats}
                  onOpenMemoryMap={() => setActiveTab('memory')}
                />
              </div>

              <div className="lg:col-span-4 min-h-[190px]">
                <LlmStatus
                  aiStatus={aiStatus}
                  onManageProviders={() => setIsSettingsOpen(true)}
                />
              </div>
            </div>
          </main>
        )}
      </div>

      {/* Persistent Bottom Bar with Location, Weather, Latency, and TALK TO NOVA capsule */}
      <BottomBar
        assistantState={assistantState}
        onTalkClick={handleMicToggle}
        onExecutiveBriefing={handleExecutiveBriefing}
        audioLevel={voice.audioLevel}
        wakeWordEnabled={voice.wakeWordEnabled}
        activeWakePhrase={voice.activeWakePhrase}
      />

      {/* Interactive Modals */}
      <ChatConsoleModal
        isOpen={isChatOpen}
        onClose={() => setIsChatOpen(false)}
        messages={messages}
        isLoading={isChatLoading}
        onSendMessage={sendMessage}
        onClearMessages={clearMessages}
        assistantState={assistantState}
        aiStatus={aiStatus}
        onChangeModel={changeModel}
        voiceEnabled={voiceEnabled}
        onToggleVoice={() => setVoiceEnabled(!voiceEnabled)}
      />

      <SettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
        aiStatus={aiStatus}
        voiceStatus={voice.voiceStatus}
        devices={voice.devices}
        onSaveModel={changeModel}
        onSaveVoiceSettings={voice.updateSettings}
        onOpenOnboarding={() => setIsOnboardingOpen(true)}
      />

      <OnboardingWizard
        isOpen={isOnboardingOpen}
        onClose={() => setIsOnboardingOpen(false)}
        onComplete={() => setIsOnboardingOpen(false)}
        devices={voice.devices}
      />

      <ExecutiveBriefingModal
        isOpen={isBriefingOpen}
        onClose={() => setIsBriefingOpen(false)}
        systemStats={systemStats}
        aiStatus={aiStatus}
        onSpeak={(text) => {
          // Play synthesized briefing through Piper TTS or browser audio
          voice.stopSpeaking();
          sendMessage(`Executive Briefing: ${text}`);
        }}
      />
    </div>
  );
};
