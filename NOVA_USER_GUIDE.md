# NOVA v1.0 — User Operational Guide

Welcome to **NOVA (Neural Operational Virtual Assistant) v1.0**, an offline-first Windows desktop personal AI assistant. NOVA runs 100% locally on your PC, ensuring complete privacy, zero telemetry leakage, and fast responsiveness.

---

## 1. Quick Start

### Starting NOVA
- Double-click the **NOVA** icon on your Windows Desktop or in the Start Menu.
- The NOVA Command Center will load at `http://localhost:1420`.
- The central holographic Orb indicates NOVA's active state:
  - **Cyan Pulse (IDLE)**: NOVA is ready for instructions.
  - **Teal Glow (LISTENING)**: Microphone is capturing speech.
  - **Rotating Core (THINKING)**: Local model is reasoning through your prompt.
  - **Purple Orbit (EXECUTING)**: Executing an approved desktop tool or workflow.
  - **Blue Radiance (SPEAKING)**: Piper TTS is speaking.

---

## 2. Conversational Intelligence & Local Models

### Text Chat
- Click the central **Orb** or the **Chat** icon in the top navigation bar to open the Chat Console.
- Type any question, code request, or instruction.
- Chat messages and session turns are saved permanently in local SQLite storage.

### Changing Local Models
- Open **Settings** (gear icon) -> **AI Neural Engine**.
- Select or enter the model name installed in your local Ollama instance (e.g. `qwen2.5:3b`, `qwen2.5:1.5b`, `llama3.2:3b`).
- Adjust generation parameters:
  - **Inference Temperature**: Lower values (0.2–0.5) produce deterministic, factual answers; higher values (0.7–0.9) encourage creative brainstorming.
  - **Max Generation Tokens**: Control maximum response length (default: 2,048 tokens).

---

## 3. Voice Interaction & Wake Words

### Wake-Word Detection
- By default, NOVA listens in the background for the wake phrase:
  ```
  "Hey Jarvis"
  ```
  *(Powered by the built-in openWakeWord ONNX acoustic model).*
- When detected, NOVA will emit a subtle chime, transition to **LISTENING** state, and transcribe your speech.
- **Microphone Sensitivity**: Adjust the detection threshold slider in **Settings -> Voice & Audio**.
- **Optional Custom Model**: If a trained `models/wake_words/hey_nova.onnx` file is installed, NOVA automatically switches to native `"Hey NOVA"` detection.

### Push-to-Talk (Manual Trigger)
- Click the large circular **Microphone Button** in the bottom-left sidebar.
- Speak your instruction immediately without saying the wake word.

### Interruption (Barge-In)
- If NOVA is speaking through Piper TTS and you want it to stop immediately:
  - Click the **Microphone Button**, OR
  - Click the **Orb**, OR
  - Issue another wake word phrase.

---

## 4. Project-Aware Memory & Knowledge Base

NOVA features persistent long-term memory with semantic vector search (powered by local FastEmbed BGE embeddings).

### Managing Project Workspaces
1. Click **Memory & Knowledge** in the left sidebar.
2. Select an active project (e.g. `Nova`, `HireLens`, or create a new project).
3. Memories stored under a project remain strictly isolated to that project.
4. When chatting with a project selected, NOVA automatically retrieves relevant architecture decisions, known issues, and tech stack notes without cross-contaminating other projects.

### Storing Facts Explicitly
- Tell NOVA in conversation: `"Remember that our production database port is 5432."`
- Or use the Memory Center UI to add, search, edit, or purge memories.

---

## 5. Desktop Operations & Safe Tool Execution

NOVA can control Windows applications, manage files, and inspect system telemetry safely.

### Available Tools (23 Built-in Operations)
- **Application Control**: Open registered apps (`app_open`), detect installed software (`app_detect_installed`).
- **Filesystem**: Search files by name/extension, read text files, copy/move/rename files, list directories, organize preview.
- **System Monitoring**: CPU/RAM usage, battery status, disk space, network interfaces, volume control, workstation lock.
- **Web Navigation**: Open URLs in default browser, perform web searches.

### Safety Confirmation Gate
- **Destructive or Sensitive Operations** (e.g. locking workstation, deleting files, system modifications) are gated by **single-use cryptographic approval tokens**.
- NOVA will display an **Action Preview** dialog detailing:
  - Tool to be executed.
  - Target path or command.
  - Potential impact.
- You must click **Approve** or say **"Yes, proceed"** to execute. Tokens expire within 5 minutes and cannot be replayed.

---

## 6. Visual Intelligence & Screen Understanding

NOVA can inspect your active desktop windows and read on-screen text without transmitting images to cloud servers.

### Inspecting Your Screen
1. Click **Vision Intelligence** in the left sidebar.
2. Choose capture mode:
   - **Primary Display**: Captures full screen.
   - **Active Window**: Targets only the currently focused application window.
3. Click **Capture & Analyze**.
4. NOVA performs local Windows OCR and extracts structured text.

### Privacy Safeguards
- **Sensitive Window Blocking**: Windows belonging to password managers (1Password, Bitwarden, KeePass) or authenticator apps are automatically blocked from capture.
- **Credential Masking**: API keys, bearer tokens, passwords, and credit card numbers are redacted before text is ingested into conversation.

---

## 7. Multi-Agent Workflows

For complex tasks requiring planning and specialization, NOVA orchestrates 5 agent personas:
- **Researcher Agent**: Gathers context from memory and files.
- **Developer Agent**: Drafts code, plans architecture, inspects syntax.
- **System Agent**: Executes system telemetry and verified desktop tools.
- **Vision Agent**: Analyzes screenshots and OCR data.
- **Memory Agent**: Synthesizes and indexes long-term knowledge.

### Running a Workflow
1. Navigate to **Agents & Workflows**.
2. Enter an objective (e.g. `"Audit project health and verify memory state"`).
3. NOVA generates a DAG (Directed Acyclic Graph) of steps.
4. Steps requiring user permission pause for approval.
5. On completion, NOVA renders an **Executive Reflection Report**.

---

## 8. Proactive Automations & Reminders

NOVA can perform routine background tasks without manual prompting.

### Configuring Automations
1. Open **Automations & Routines** in the left sidebar.
2. Click **Create Automation Rule**:
   - **Schedule Triggers**: Run daily at a specified time (e.g. 08:30 AM).
   - **Event Triggers**: Trigger when system events fire (e.g. `system.ready`).
   - **Interval Triggers**: Periodic checks every N minutes.
3. Choose Autonomy Level:
   - `NOTIFY_ONLY`: Sends a notification without executing actions.
   - `EXECUTE_LOW_RISK`: Executes safe read-only tools automatically.
   - `REQUIRE_APPROVAL`: Always requests confirmation before proceeding.

### Reminders & Notifications
- You can create reminders in chat (e.g. `"Remind me to review the pull request at 3 PM"`).
- Dismiss, snooze, or mark notifications as read from the Notification Center.

---

## 9. Personalization & Privacy Controls

NOVA adapts to your preferred communication style, explanation depth, and programming languages.

### Explicit vs. Inferred Preferences
- **Explicit Preferences**: Directly configured by you (e.g. `"Always keep answers concise"`). Explicit preferences **always take absolute priority**.
- **Inferred Preferences**: Subtle behavioral patterns identified from permitted interaction history.
- To disable learning: Open **Settings -> Privacy & Security** and uncheck **"Adaptive Personalization"**.
- To purge learned data: Go to **Personalization -> Privacy -> Clear Personalization Data**.

---

## 10. Database Backups & System Diagnostics

### Automated Database Backups
- NOVA maintains an SQLite database (`nova_memory.db`) in WAL mode with a 5,000 ms busy timeout.
- Go to **System Reliability -> Backups**:
  - Click **Create Backup** to generate a timestamped `.db` snapshot in `D:\Nova\backups\`.
  - Validate backup file integrity and SHA-256 checksums with one click.
  - Preview dry-run restoration before committing any rollback.

### Diagnostics Center
- View detailed health across all 10 subsystems (AI Core, Voice, Audio Device, Memory, Database, Tools, Vision, Agents, Automation, Security).
- Export sanitized system diagnostics reports for troubleshooting.
