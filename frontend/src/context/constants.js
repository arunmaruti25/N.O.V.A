export const NOVA_STATES = Object.fromEntries([
  "IDLE", "LISTENING", "SPEECH_DETECTED", "WAITING_FOR_CONTINUATION", "FINALIZING",
  "PROCESSING", "THINKING", "EXECUTING", "VERIFYING", "RECOVERING", "PAUSED",
  "SPEAKING", "CONFIRMATION", "SUCCESS", "ERROR", "OFFLINE",
].map((s) => [s, s]));
export const AVAILABLE_MODELS = [
  { provider: "Gemini", mode: "Reasoning", tag: "Configured by server", color: "#4285F4", latency: "—", desc: "Reasoning and visual understanding" },
  { provider: "Groq", mode: "Fast", tag: "Configured by server", color: "#F55036", latency: "—", desc: "Conversational inference" },
  { provider: "NVIDIA", mode: "Coding", tag: "Configured by server", color: "#76B900", latency: "—", desc: "Code and technical tasks" },
  { provider: "Ollama", mode: "Local", tag: "Configured by server", color: "#94A3B8", latency: "—", desc: "Local inference without cloud fallback" },
];
