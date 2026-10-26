# NOVA v1.0.1 — Voice Latency & Ollama CPU Optimization Audit

Date of measurements: 2026-10-21  
Target hardware: Intel Core i3-1115G4 class (2P/4T), ~12 GB RAM, Windows, local Ollama.  
Model used in live runs: `qwen2.5:1.5b` (pulled during this audit; it was not present at the start of the session — only `gemma2:2b` and `qwen3:4b` were installed).

This document records a software investigation, the fixes that shipped, and **measured** numbers. CPU inference of a 1.5B model on two physical cores is still inherently heavy; the work below removes extra requests, extra context, and extra microphone load so that time-to-first-token and time-to-first-audio improve.

---

## 1. Root cause identified

Several **software** defects stacked on top of **CPU inference**:

1. **Blocking, non-streaming Ollama calls.** `OllamaProvider.chat` posted `stream: false` with `num_ctx=2048`, `num_thread=4`, `num_predict=512`. The UI and Piper waited for the **entire** completion before showing or speaking anything.
2. **Four Ollama threads on a 4-logical-core i3** left no headroom for Vosk, openWakeWord, Piper, embeddings, or the desktop UI, so the machine sat at ~100% CPU for the whole generation.
3. **Voice conversation path crashed before a correct memory call.** `AudioManager._dispatch_to_brain` called `build_augmented_context(user_message=..., max_items=5)` but the method only accepted `user_query`. Ordinary speech either errored or never took the compact path.
4. **Chat still ran Ollama for explicit memory questions** (“what do you remember…”) even though the memory engine already had an answer (0 extra tokens of value, 1 extra inference).
5. **Memory extraction and embedding search ran before or beside inference.** `process_turn_and_extract` computes FastEmbed vectors; voice also spun a background extract thread that competed with generation.
6. **Oversized prompt.** Text chat injected project memory, personalization, and sanitizer wrappers (measured **397 prompt-eval tokens / 1822 chars** vs **38 tokens** for a direct Ollama chat). Prompt evaluation, not decode, dominated NOVA text TTFT.
7. **Broad agent trigger `"inspect"`** could send a casual utterance into `AgentPlanner` (a second LLM call) instead of the lightweight voice reply path.
8. **Continuous microphone capture** ran whenever the voice pipeline was “started”, including when wake-word was disabled. Push-to-talk did not actually release the mic.
9. **No cancellation** of an in-flight generate when the user interrupted speech.
10. **Settings UI `maxTokens` / temperature were not wired** into Ollama options.

**Not a software defect:** generating tokens with `qwen2.5:1.5b` on CPU still pegs cores for the duration of decode. After the fixes, decode is ~23–28 tok/s and ~9-token replies finish in a few hundred milliseconds of eval; **load + prompt-eval** remain the large delays unless the model is already resident (`keep_alive=10m`).

One spoken command that takes the lightweight path now issues **one** Ollama `/api/chat` stream. Transcription is **not** sent through a second LLM. Planner / reflection / summarizer do not run on ordinary replies. Frontend `onSpeechRecognized` only reloads history; it does **not** POST `/api/chat` again.

---

## 2. Files inspected

- `backend/app/ai/ollama_provider.py`, `model_manager.py`, `model_provider.py`
- `backend/app/api/chat.py`, `voice.py`, `system.py`, `ai.py`
- `backend/app/voice/audio_manager.py`, `text_to_speech.py`, `speech_recognition.py`, `wake_word.py`
- `backend/app/config.py`
- `backend/app/reliability/resource_coordinator.py`
- `backend/app/memory/memory_manager.py`, `memory_extractor.py`, `conversation_summarizer.py`, `semantic_search.py`
- `backend/app/agents/agent_orchestrator.py`, `agent_planner.py`, `agent_reflection.py`
- `backend/app/tools/task_planner.py`
- `apps/desktop/src/hooks/useVoice.ts`, `useChat.ts`
- `apps/desktop/src/pages/CommandCenterPage.tsx`
- `apps/desktop/src/components/dashboard/SettingsModal.tsx`, `LeftSidebar.tsx`
- `apps/desktop/src/services/api.ts`, `types/index.ts`
- `backend/tests/test_voice.py`, `test_e2e_v10.py`, `test_agents_v06.py`

---

## 3. Files changed

| File | Change |
| --- | --- |
| `backend/app/config.py` | Version `1.0.1`; default model `qwen2.5:1.5b`; inference profile settings |
| `backend/app/ai/inference_config.py` | **New** runtime-safe Ollama options |
| `backend/app/ai/inference_tracer.py` | **New** request IDs + timings (no prompts/audio) |
| `backend/app/ai/ollama_provider.py` | Streaming chat, `keep_alive`, cancel, options from config |
| `backend/app/ai/model_manager.py` | `chat_stream`, `cancel_active`, profile passthrough |
| `backend/app/ai/model_provider.py` | `**kwargs` on `chat` |
| `backend/app/api/chat.py` | Stream endpoint, memory short-circuit, extract-after-infer, history trim |
| `backend/app/api/voice.py` | PTT vs wake-word, cancel action |
| `backend/app/api/system.py` | Unified inference settings GET/POST |
| `backend/app/memory/memory_manager.py` | Compact voice context; accept voice kwargs |
| `backend/app/voice/audio_manager.py` | PTT mic lifecycle, one-flight stream, sentence TTS, timings, narrower agent triggers |
| `backend/app/voice/text_to_speech.py` | Sentence queue for streamed Piper chunks |
| `apps/desktop/src/hooks/useChat.ts` | Stream tokens into the console immediately |
| `apps/desktop/src/hooks/useVoice.ts` | Cancel inference; token/speaking states |
| `apps/desktop/src/services/api.ts` | Stream + inference settings |
| `apps/desktop/src/components/dashboard/SettingsModal.tsx` | PTT + num_ctx / threads / keep_alive |
| `apps/desktop/src/components/dashboard/LeftSidebar.tsx` | Listening / thinking / PTT labels |
| `apps/desktop/src/types/index.ts` | Inference settings types |
| `apps/desktop/package.json`, `src-tauri/tauri.conf.json` | Version 1.0.1 |
| `backend/tests/test_voice_performance_v101.py` | **New** regression tests |
| `backend/tests/test_voice.py`, `test_vision_v05.py` | Align with PTT default / active model |
| `scripts/benchmark_v101_voice.py` | **New** A/B/C/D harness |
| `benchmark_v101_results.json` | Raw run output |

---

## 4. Before-and-after benchmarks

**Method.** Short public prompt: “Reply with one short sentence: what is 2 plus 2?”. Ollama 0.35.1, `qwen2.5:1.5b`, `keep_alive=10m`. Numbers are from this machine on 2026-10-21. `ollama_cpu_percent` sampled **after** the request returned (so it is near idle); generation still saturates CPU while tokens run.

There is **no honest “old NOVA voice” wall-clock** because the previous voice kwargs were invalid and streaming did not exist. “Before” Ollama **options** were re-run directly against `/api/chat`.

### Direct Ollama (path A) — option profile comparison

| Profile | Model loaded? | TTFT (ms) | Prompt-eval (ms) | Eval (ms) | tok/s | Prompt tokens | Gen tokens |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| v1.0 options `num_ctx=2048`, `num_thread=4`, `num_predict=512` (reload) | no (`load_ms≈1662`) | 4431 | 379 | 317 | **28.4** | 38 | 9 |
| v1.0.1 `1024/2/96` immediately after option change (reload) | no (`load_ms≈1675`) | 4416 | 410 | 392 | 22.9 | 38 | 9 |
| v1.0.1 `1024/2/96` **warm repeat** | **yes** (`load_ms=5`) | **2352** | **52** | 368 | 24.5 | 38 | 9 |
| Warm `num_thread=2` (earlier series) | yes | 2766 | 375 | 365 | 24.7 | 38 | 9 |
| Warm omit `num_thread` (Ollama auto) | reload (`load_ms≈1662`) | 4421 | 400 | 400 | 22.5 | 38 | 9 |

**Thread finding:** on this 9-token reply, **4 threads decoded slightly faster** (28 tok/s) than **2 threads** (~25 tok/s). Auto was not faster than 2 once reload cost is included. Changing `num_thread` or `num_ctx` often costs ~1.6 s of graph reload. Default remains **2 threads** so Vosk/Piper/UI can share the i3; Settings can switch to auto.

### NOVA-integrated (paths B, C)

| Path | TTFT (ms) | Total (ms) | Prompt tokens | tok/s | Ollama requests | Loaded? |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| B. NOVA text `/api/chat/stream` (first after other runs) | 6614 | 7048 | **397** | 22.6 | 1 | no (`load_ms=1875`) |
| B. NOVA text **warm** | 4583 | 5073 | **397** | 18.1 | 1 | yes (`load_ms=6`) |
| C. NOVA voice PTT dispatch, STT skipped, TTS mocked | **1212** | 1666 | **131** | 24.1 | **1** | yes (`load_ms=7`) |

Voice compact context (~568 chars / 131 tokens) is why C beats B. Text still wraps memory/personalization (~1822 chars / 397 tokens) → ~3.3 s prompt-eval when warm.

### Idle CPU (path D)

| Mode | Mic open | System CPU % (1.2 s sample) |
| --- | --- | ---: |
| Push-to-talk standby | **no** | **1.9** |
| Wake-word capture | yes | 5.0 |

RAM during these runs was ~74–79% of 12 GB (~8.7–9.3 GB used), with the Ollama runner process showing ~33 MB RSS in `psutil` (weights live in related processes; this is **not** the full model footprint).

---

## 5. Inference request trace (one spoken command, lightweight path)

```
mic (PTT open) → Vosk → AudioManager._dispatch_to_brain
  → deterministic tools / memory / agent gates (no LLM)
  → compact memory (no embeddings)
  → resource_coordinator (max 1)
  → OllamaProvider.chat_stream  (exactly 1 HTTP POST /api/chat)
  → token_delta WebSocket + Piper sentence queue
  → memory extract AFTER speech
```

Recorded voice trace (`inf_95b2d74ffbcc`):

| Field | Value |
| --- | --- |
| request_id | `inf_95b2d74ffbcc` |
| source | voice |
| ollama_calls | 1 |
| prompt_chars | 568 |
| prompt_eval_count | 131 |
| eval_count | 9 |
| tokens_per_sec | 24.073 |
| ttft_ms | 1211.69 |
| prompt_eval_ms | 639.74 |
| eval_ms | 373.87 |
| load_ms | 7.33 (already loaded) |
| options | `num_ctx=1024`, `num_predict=96`, `num_thread=2`, `keep_alive=10m` |

**Not on this path:** transcription LLM, reflection engine, conversation summarizer, duplicate frontend `/chat`.

**On other paths (unchanged architecture, still gated):** desktop tools, vision, explicit workflow phrases such as “inspect my nova project”, “plan my work”, “run tests”.

---

## 6. Voice pipeline timing breakdown

| Stage | What we measure | Observed in C (STT mocked) |
| --- | --- | --- |
| Audio capture | Mic open only while PTT listening / wake-word | PTT idle: mic closed |
| Wake-word | Optional; skipped in PTT | n/a for C |
| Vosk | `stt_ms` on `listening_stopped` | 0 (injected text) |
| Prompt construction | compact memory + system line | **2.24 ms** |
| Ollama queue wait | inference semaphore | 0 ms |
| Prompt evaluation | `prompt_eval_ms` | 640 ms (131 tokens, warm) |
| Token generation | `eval_ms` / tok/s | 374 ms / 24 tok/s |
| Time to first visible token | `ttft_ms` (first stream chunk) | **1212 ms** |
| Piper | sentence chunks after `.?!` | not audible in C (TTS mocked); queue is wired |
| Time to first audible | first enqueued sentence | null in C because the 9-token reply had no sentence flush before mock |

End-to-end with real Vosk will add the listen window (silence timeout ~1.6 s plus speech). That is **acoustic**, not Ollama.

---

## 7. Regression test results

```
python -m pytest tests -q
141 passed
```

Frontend: `npm run build` in `apps/desktop` — **success** (`tsc && vite build`).

New tests in `backend/tests/test_voice_performance_v101.py`:

- Default CPU inference profile
- Settings round-trip (`thread_mode=auto` then restore)
- History trim
- Explicit memory → **0** Ollama calls
- Text chat → **1** Ollama call
- PTT `start()` does not open `InputStream`
- Two voice utterances → two streams (not 4)
- Cancel endpoint
- `/api/chat/stream` emits token events

---

## 8. Remaining bottlenecks

1. **CPU decode of 1.5B weights** — ~23–28 tok/s on this i3. Longer answers still take seconds. `num_predict=96` caps voice length; it cannot create a GPU.
2. **Model reload (~1.6 s)** whenever `num_ctx` / `num_thread` change, and whenever the model is not kept alive.
3. **Text-chat prompt-eval (~3.3 s warm)** from ~397 tokens of system/memory wrapping vs 38 for a bare prompt. Voice compact path is better; further shrinking text memory injection would help Command Console more than Piper.
4. **Vosk + listen window** still dominate perceived latency before the first token on a real utterance.
5. **Piper on CPU** after generation; chunking helps first audio but does not make ONNX TTS free.
6. **FastEmbed** still runs after speech for persistence; it no longer overlaps the generate, but it costs CPU when the turn ends.
7. **`psutil` Ollama CPU** after completion is not a good proxy for mid-generate load; expect high CPU **during** eval regardless of NOVA.

---

## 9. Recommended default settings (this hardware)

| Setting | Value | Why |
| --- | --- | --- |
| Model | `qwen2.5:1.5b` (or `gemma2:2b` if already warm) | Smallest capable local chat model |
| Voice mode | **Push-to-talk** | Mic closed when idle |
| Wake-word | Optional off | Keep available; +~3–5% idle CPU when on |
| `num_ctx` | 1024 | Enough for short voice + 2 memory lines |
| `num_predict` (text) | 256 | Console answers |
| `num_predict` (voice) | 96 | 1–3 spoken sentences |
| `num_thread` | **2** (manual) | Leaves 2 logical cores for STT/TTS/UI; auto/4 is slightly faster decode alone but reloads if you switch |
| `keep_alive` | 10m | Avoid 1.6–1.9 s load on every turn |
| Max concurrent inference | 1 | Already enforced |
| History | 4 text turns / 2 voice | Do not resubmit the full SQLite log |

---

## Phase checklist (what shipped)

| Item | Status |
| --- | --- |
| Trace one voice request | Done — one stream on the lightweight path |
| Structured timings + request IDs | `nova.ai.trace` / `inference_tracer` (no audio/secrets) |
| Configurable ctx/predict/threads/keep_alive | Settings → AI Neural Engine |
| Max concurrent = 1 | `resource_coordinator` used by chat and voice |
| PTT without continuous mic | Default; wake-word optional |
| Lightweight voice path | Compact memory, no pre-infer extract, no summarizer |
| Streaming UI | `/api/chat/stream` + token WebSocket |
| Piper chunks | Sentence queue |
| Cancel on interrupt | `cancel_inference` / mic tap while speaking |
| No duplicate LLM for one utterance | Regression tests |
| Architecture / permissions preserved | Tools, vision, agents, SQLite, Piper, Vosk retained |
