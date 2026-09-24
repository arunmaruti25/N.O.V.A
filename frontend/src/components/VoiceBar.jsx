import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Mic, Sparkles, X, Volume2, CornerDownLeft, Pause, Play, Square } from "lucide-react";
import { useNova } from "../context/useNova";
import { NOVA_STATES } from "../context/constants";

const SUGGESTIONS = [
  { text: "NOVA, open Chrome", hint: "App Launch" },
  { text: "NOVA, what's on my screen?", hint: "Vision HUD" },
  { text: "NOVA, search web for quantum AI", hint: "Research" },
  { text: "NOVA, shut down my laptop", hint: "Power Safety" },
];

export default function VoiceBar() {
  const {
    status,
    isListening,
    transcript,
    waveformBars,
    triggerVoiceCommand,
    cancelOperation,
    currentTask,
    pauseTask,
    resumeTask,
    cancelTask,
  } = useNova();

  const [inputVal, setInputVal] = useState("");

  const handleMicClick = () => {
    if (status === NOVA_STATES.IDLE) {
      triggerVoiceCommand();
    } else {
      cancelOperation();
    }
  };

  const handleFormSubmit = (e) => {
    e.preventDefault();
    if (!inputVal.trim()) return;
    triggerVoiceCommand(inputVal.trim());
    setInputVal("");
  };

  return (
    <div
      style={{
        width: "100%",
        maxWidth: 740,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: 14,
        position: "relative",
      }}
    >
      {/* Live Transcript / Response Stream Bubble */}
      <AnimatePresence>
        {transcript && (
          <motion.div
            initial={{ opacity: 0, y: 10, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 6, scale: 0.98 }}
            transition={{ duration: 0.2 }}
            className="glass-card"
            style={{
              width: "100%",
              padding: "14px 18px",
              display: "flex",
              alignItems: "center",
              gap: 14,
              border: "1px solid rgba(123, 92, 240, 0.45)",
              background: "rgba(17, 21, 34, 0.92)",
              boxShadow:
                "0 8px 32px rgba(0, 0, 0, 0.6), 0 0 20px rgba(123, 92, 240, 0.2)",
            }}
          >
            <div
              style={{
                width: 32,
                height: 32,
                borderRadius: "50%",
                background: "rgba(123, 92, 240, 0.25)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "var(--color-nova-cyan)",
                flexShrink: 0,
                boxShadow: "0 0 12px rgba(34, 211, 238, 0.3)",
              }}
            >
              {status === NOVA_STATES.SPEAKING ? (
                <Volume2 size={17} />
              ) : (
                <Sparkles size={17} />
              )}
            </div>

            <div style={{ flex: 1, minWidth: 0 }}>
              <div
                style={{
                  fontSize: 10,
                  fontFamily: "var(--font-mono)",
                  color: "var(--color-text-secondary)",
                  textTransform: "uppercase",
                  letterSpacing: "0.1em",
                  marginBottom: 3,
                }}
              >
                {status === NOVA_STATES.SPEAKING
                  ? "NOVA Spoken Audio"
                  : "Voice Input Stream"}
              </div>
              <div
                style={{
                  fontSize: 14,
                  color: "var(--color-text-primary)",
                  lineHeight: 1.45,
                  fontWeight: 500,
                }}
              >
                {transcript}
              </div>
            </div>

            <button
              type="button"
              onClick={cancelOperation}
              className="btn-icon"
              style={{ width: 28, height: 28 }}
              title="Clear transcript"
            >
              <X size={15} />
            </button>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Main Command Bar Container */}
      <form
        onSubmit={handleFormSubmit}
        className="glass-panel"
        style={{
          width: "100%",
          borderRadius: "var(--radius-xl)",
          padding: "6px 8px 6px 18px",
          display: "flex",
          alignItems: "center",
          gap: 14,
          background: "rgba(13, 17, 28, 0.85)",
          boxShadow: isListening
            ? "0 0 35px rgba(37, 99, 235, 0.4), 0 4px 24px rgba(0, 0, 0, 0.5)"
            : "0 4px 24px rgba(0, 0, 0, 0.5), 0 0 0 1px rgba(123, 92, 240, 0.15)",
          border: isListening
            ? "1px solid rgba(34, 211, 238, 0.6)"
            : "1px solid rgba(148, 163, 184, 0.18)",
          transition: "all 0.25s ease",
        }}
      >
        {/* Dynamic Waveform Visualizer */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 3.5,
            height: 26,
            paddingRight: 6,
          }}
          title={isListening ? "Audio input active" : "Audio input standby"}
        >
          {waveformBars.map((val, idx) => (
            <motion.div
              key={idx}
              animate={{ height: isListening ? Math.max(6, val * 24) : 6 }}
              style={{
                width: 3,
                backgroundColor: isListening
                  ? "var(--color-nova-cyan)"
                  : "var(--color-text-tertiary)",
                borderRadius: 2,
                boxShadow: isListening
                  ? "0 0 8px var(--color-nova-cyan)"
                  : "none",
                transition: "background-color 0.2s",
              }}
            />
          ))}
        </div>

        {/* Text Input for Keyboard-first interaction */}
        <input
          type="text"
          value={inputVal}
          onChange={(e) => setInputVal(e.target.value)}
          placeholder={
            isListening
              ? "Listening... speak now or type instructions"
              : "Ask NOVA anything or tap mic to speak..."
          }
          style={{
            flex: 1,
            background: "transparent",
            border: "none",
            outline: "none",
            color: "var(--color-text-primary)",
            fontFamily: "var(--font-body)",
            fontSize: 14,
            letterSpacing: "0.01em",
          }}
        />

        {/* Send Button if input is typed */}
        {inputVal.trim() && (
          <motion.button
            type="submit"
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            className="btn-icon"
            style={{ width: 34, height: 34, color: "var(--color-nova-cyan)" }}
            title="Execute (Enter)"
          >
            <CornerDownLeft size={16} />
          </motion.button>
        )}

        {/* Primary Interactive Mic Button with Multi-Ring Pulse */}
        <div style={{ position: "relative" }}>
          {isListening && (
            <motion.div
              animate={{ scale: [1, 1.35, 1], opacity: [0.6, 0, 0.6] }}
              transition={{ duration: 1.5, repeat: Infinity, ease: "easeOut" }}
              style={{
                position: "absolute",
                inset: -4,
                borderRadius: "50%",
                border: "1.5px solid var(--color-nova-cyan)",
                pointerEvents: "none",
              }}
            />
          )}

          <motion.button
            type="button"
            onClick={handleMicClick}
            whileHover={{ scale: 1.06 }}
            whileTap={{ scale: 0.94 }}
            style={{
              width: 44,
              height: 44,
              borderRadius: "50%",
              background: isListening
                ? "linear-gradient(135deg, #2563eb 0%, #0891b2 100%)"
                : "linear-gradient(135deg, #7b5cf0 0%, #5b21b6 100%)",
              border: isListening
                ? "1px solid rgba(255, 255, 255, 0.6)"
                : "1px solid rgba(255, 255, 255, 0.25)",
              color: "#ffffff",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              cursor: "pointer",
              boxShadow: isListening
                ? "0 0 24px rgba(34, 211, 238, 0.7)"
                : "0 4px 16px rgba(123, 92, 240, 0.45)",
              transition: "all 0.2s ease",
            }}
            title={
              isListening
                ? "Click to stop listening"
                : "Click to speak to NOVA (or press Space)"
            }
          >
            <Mic size={20} />
          </motion.button>
        </div>
      </form>

      {/* Minimal Task Status & Controls */}
      <AnimatePresence>
        {currentTask && (currentTask.status === "RUNNING" || currentTask.status === "PAUSED") && (
          <motion.div
            initial={{ opacity: 0, y: -6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -6 }}
            className="glass-card"
            style={{
              width: "100%",
              padding: "8px 16px",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              gap: 12,
              background: "rgba(17, 21, 34, 0.95)",
              border:
                currentTask.status === "PAUSED"
                  ? "1px solid rgba(245, 158, 11, 0.45)"
                  : "1px solid rgba(34, 211, 238, 0.45)",
              borderRadius: "var(--radius-lg)",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 10, minWidth: 0 }}>
              <span
                className="badge"
                style={{
                  background:
                    currentTask.status === "PAUSED"
                      ? "rgba(245, 158, 11, 0.15)"
                      : "rgba(34, 211, 238, 0.15)",
                  color:
                    currentTask.status === "PAUSED" ? "#f59e0b" : "var(--color-nova-cyan)",
                  border:
                    currentTask.status === "PAUSED"
                      ? "1px solid rgba(245, 158, 11, 0.3)"
                      : "1px solid rgba(34, 211, 238, 0.3)",
                  fontSize: 10,
                  fontFamily: "var(--font-mono)",
                  fontWeight: 600,
                  textTransform: "uppercase",
                }}
              >
                {currentTask.status}
              </span>
              <span
                style={{
                  fontSize: 12,
                  color: "var(--color-text-secondary)",
                  fontFamily: "var(--font-mono)",
                }}
              >
                Step {currentTask.current_step || 1} / {currentTask.total_steps || 1}
              </span>
              <span
                style={{
                  fontSize: 13,
                  color: "var(--color-text-primary)",
                  overflow: "hidden",
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                }}
              >
                {currentTask.description || currentTask.original_request || "Active Task"}
              </span>
            </div>

            <div style={{ display: "flex", alignItems: "center", gap: 6, flexShrink: 0 }}>
              {currentTask.status === "RUNNING" ? (
                <button
                  type="button"
                  onClick={() => pauseTask(currentTask.task_id)}
                  className="badge"
                  style={{
                    cursor: "pointer",
                    background: "rgba(245, 158, 11, 0.12)",
                    color: "#f59e0b",
                    border: "1px solid rgba(245, 158, 11, 0.35)",
                    display: "flex",
                    alignItems: "center",
                    gap: 5,
                    padding: "4px 10px",
                  }}
                  title="Pause task execution"
                >
                  <Pause size={12} />
                  <span>Pause</span>
                </button>
              ) : (
                <button
                  type="button"
                  onClick={() => resumeTask(currentTask.task_id)}
                  className="badge"
                  style={{
                    cursor: "pointer",
                    background: "rgba(16, 185, 129, 0.12)",
                    color: "#10b981",
                    border: "1px solid rgba(16, 185, 129, 0.35)",
                    display: "flex",
                    alignItems: "center",
                    gap: 5,
                    padding: "4px 10px",
                  }}
                  title="Resume task execution"
                >
                  <Play size={12} />
                  <span>Resume</span>
                </button>
              )}

              <button
                type="button"
                onClick={() => cancelTask(currentTask.task_id)}
                className="badge"
                style={{
                  cursor: "pointer",
                  background: "rgba(239, 68, 68, 0.12)",
                  color: "#ef4444",
                  border: "1px solid rgba(239, 68, 68, 0.35)",
                  display: "flex",
                  alignItems: "center",
                  gap: 5,
                  padding: "4px 10px",
                }}
                title="Cancel task"
              >
                <Square size={11} />
                <span>Cancel</span>
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Suggestion Prompts Row */}
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          gap: 8,
          justifyContent: "center",
        }}
      >
        {SUGGESTIONS.map((item) => (
          <motion.button
            key={item.text}
            type="button"
            onClick={() => triggerVoiceCommand(item.text)}
            whileHover={{ y: -2, scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            className="badge"
            style={{
              background: "rgba(255, 255, 255, 0.04)",
              border: "1px solid rgba(148, 163, 184, 0.12)",
              color: "var(--color-text-secondary)",
              cursor: "pointer",
              padding: "6px 14px",
              fontFamily: "var(--font-body)",
              display: "flex",
              alignItems: "center",
              gap: 8,
              transition: "all 0.15s ease",
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.borderColor = "rgba(123, 92, 240, 0.45)";
              e.currentTarget.style.color = "var(--color-text-primary)";
              e.currentTarget.style.background = "rgba(123, 92, 240, 0.12)";
              e.currentTarget.style.boxShadow =
                "0 2px 10px rgba(123, 92, 240, 0.2)";
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = "rgba(148, 163, 184, 0.12)";
              e.currentTarget.style.color = "var(--color-text-secondary)";
              e.currentTarget.style.background = "rgba(255, 255, 255, 0.04)";
              e.currentTarget.style.boxShadow = "none";
            }}
          >
            <Sparkles size={11} color="var(--color-nova-primary)" />
            <span>{item.text}</span>
            <span
              style={{
                fontSize: 9,
                fontFamily: "var(--font-mono)",
                color: "var(--color-nova-cyan)",
                opacity: 0.8,
                background: "rgba(34, 211, 238, 0.1)",
                padding: "1px 5px",
                borderRadius: 3,
              }}
            >
              {item.hint}
            </span>
          </motion.button>
        ))}
      </div>
    </div>
  );
}
