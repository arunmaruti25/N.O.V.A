import { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  ChevronUp,
  ChevronDown,
  Sliders,
  Play,
  ShieldAlert,
  Sparkles,
} from "lucide-react";
import { useNova } from "../context/useNova";
import { NOVA_STATES } from "../context/constants";

const STATE_CONFIGS = [
  {
    id: NOVA_STATES.IDLE,
    label: "IDLE",
    key: "1",
    color: "#7b5cf0",
    detail: "",
  },
  {
    id: NOVA_STATES.LISTENING,
    label: "LISTENING",
    key: "2",
    color: "#2563eb",
    detail: "LISTENING TO AUDIO STREAM...",
  },
  {
    id: NOVA_STATES.PROCESSING,
    label: "PROCESSING",
    key: "3",
    color: "#8b5cf6",
    detail: "PARSING VECTOR EMBEDDINGS...",
  },
  {
    id: NOVA_STATES.THINKING,
    label: "THINKING",
    key: "4",
    color: "#7c3aed",
    detail: "PLANNING MULTI-STEP REASONING...",
  },
  {
    id: NOVA_STATES.EXECUTING,
    label: "EXECUTING",
    key: "5",
    color: "#0891b2",
    detail: "RUNNING SCRIPT AUTOMATION...",
  },
  {
    id: NOVA_STATES.SPEAKING,
    label: "SPEAKING",
    key: "6",
    color: "#4f46e5",
    detail: "SYNTHESIZING NEURAL AUDIO...",
  },
  {
    id: NOVA_STATES.CONFIRMATION,
    label: "CONFIRM",
    key: "7",
    color: "#d97706",
    detail: "WAITING FOR USER CONFIRMATION...",
  },
  {
    id: NOVA_STATES.SUCCESS,
    label: "SUCCESS",
    key: "8",
    color: "#059669",
    detail: "TASK EXECUTED SUCCESSFULLY",
  },
  {
    id: NOVA_STATES.ERROR,
    label: "ERROR",
    key: "9",
    color: "#dc2626",
    detail: "SYSTEM EXCEPTION CAPTURED",
  },
  {
    id: NOVA_STATES.OFFLINE,
    label: "OFFLINE",
    key: "0",
    color: "#475569",
    detail: "CONNECTION SEVERED",
  },
];

export default function StateDevBar() {
  const {
    status,
    setStatus,
    setStatusDetail,
    requestPermission,
    triggerVoiceCommand,
    isMiniMode,
    setIsMiniMode,
  } = useNova();

  const [isOpen, setIsOpen] = useState(false);

  const handleStateSelect = useCallback(
    (cfg) => {
      setStatus(cfg.id);
      setStatusDetail(cfg.detail);
    },
    [setStatus, setStatusDetail],
  );

  // Optional keyboard shortcuts 1-9, 0 when open
  useEffect(() => {
    function handleKeyDown(e) {
      if (!isOpen || e.ctrlKey || e.altKey || e.metaKey) return;
      const found = STATE_CONFIGS.find((c) => c.key === e.key);
      if (found) {
        handleStateSelect(found);
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, handleStateSelect]);

  return (
    <div
      style={{
        position: "fixed",
        bottom: 0,
        left: "50%",
        transform: "translateX(-50%)",
        zIndex: 9980,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
      }}
    >
      {/* Toggle Tab */}
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        style={{
          background: "rgba(13, 17, 26, 0.94)",
          border: "1px solid rgba(123, 92, 240, 0.35)",
          borderBottom: "none",
          borderRadius: "8px 8px 0 0",
          padding: "5px 16px",
          color: "var(--color-text-secondary)",
          fontSize: 11,
          fontFamily: "var(--font-mono)",
          cursor: "pointer",
          display: "flex",
          alignItems: "center",
          gap: 7,
          boxShadow: "0 -4px 14px rgba(0, 0, 0, 0.5)",
          backdropFilter: "blur(12px)",
        }}
      >
        <Sliders size={13} color="var(--color-nova-cyan)" />
        <span style={{ letterSpacing: "0.04em" }}>STATE INSPECTOR</span>
        <span
          style={{
            fontSize: 10,
            padding: "1px 6px",
            borderRadius: 4,
            background: "rgba(34, 211, 238, 0.15)",
            color: "var(--color-nova-cyan)",
            fontWeight: 600,
          }}
        >
          {status}
        </span>
        {isOpen ? <ChevronDown size={14} /> : <ChevronUp size={14} />}
      </button>

      {/* Expanded Control Tray */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 10 }}
            transition={{ duration: 0.15 }}
            className="glass-panel"
            style={{
              padding: "10px 18px",
              background: "rgba(9, 12, 20, 0.98)",
              borderTop: "1px solid rgba(123, 92, 240, 0.45)",
              boxShadow: "0 -10px 30px rgba(0, 0, 0, 0.8)",
              display: "flex",
              flexWrap: "wrap",
              alignItems: "center",
              justifyContent: "center",
              gap: 6,
              maxWidth: 960,
              backdropFilter: "blur(20px)",
            }}
          >
            {/* State Switcher Pills */}
            {STATE_CONFIGS.map((cfg) => {
              const isCurrent = status === cfg.id;
              return (
                <button
                  key={cfg.id}
                  type="button"
                  onClick={() => handleStateSelect(cfg)}
                  style={{
                    fontSize: 10,
                    fontFamily: "var(--font-mono)",
                    padding: "4px 9px",
                    borderRadius: "var(--radius-sm)",
                    cursor: "pointer",
                    border: isCurrent
                      ? `1px solid ${cfg.color}`
                      : "var(--border-subtle)",
                    background: isCurrent
                      ? `${cfg.color}28`
                      : "rgba(255, 255, 255, 0.03)",
                    color: isCurrent
                      ? "#ffffff"
                      : "var(--color-text-secondary)",
                    fontWeight: isCurrent ? 600 : 400,
                    display: "flex",
                    alignItems: "center",
                    gap: 5,
                    boxShadow: isCurrent ? `0 0 10px ${cfg.color}40` : "none",
                    transition: "all 0.15s ease",
                  }}
                  title={`Switch to ${cfg.id} (HotKey: ${cfg.key})`}
                >
                  <span
                    style={{
                      width: 5,
                      height: 5,
                      borderRadius: "50%",
                      backgroundColor: cfg.color,
                    }}
                  />
                  <span>{cfg.label}</span>
                  <span style={{ opacity: 0.5, fontSize: 9 }}>({cfg.key})</span>
                </button>
              );
            })}

            <div
              style={{
                width: 1,
                height: 20,
                background: "rgba(255, 255, 255, 0.12)",
                margin: "0 4px",
              }}
            />

            {/* Test Permission */}
            <button
              type="button"
              onClick={() => {
                requestPermission({
                  title: "Emergency System Shutdown",
                  description:
                    "NOVA has received a command to power down Windows workstation.",
                  severity: "danger",
                  detail: "shutdown /s /t 0 /f",
                  onConfirm: () => {
                    setStatus(NOVA_STATES.SUCCESS);
                    setStatusDetail("Shutdown signal authorized");
                  },
                });
              }}
              style={{
                fontSize: 10,
                fontFamily: "var(--font-mono)",
                padding: "4px 9px",
                borderRadius: "var(--radius-sm)",
                cursor: "pointer",
                border: "1px solid rgba(220, 38, 38, 0.5)",
                background: "rgba(220, 38, 38, 0.2)",
                color: "#fca5a5",
                display: "flex",
                alignItems: "center",
                gap: 5,
              }}
            >
              <ShieldAlert size={12} /> Test Permission
            </button>

            {/* Simulated Voice flow */}
            <button
              type="button"
              onClick={() => triggerVoiceCommand("NOVA, open Chrome")}
              style={{
                fontSize: 10,
                fontFamily: "var(--font-mono)",
                padding: "4px 9px",
                borderRadius: "var(--radius-sm)",
                cursor: "pointer",
                border: "1px solid rgba(123, 92, 240, 0.5)",
                background: "rgba(123, 92, 240, 0.2)",
                color: "#c4b5fd",
                display: "flex",
                alignItems: "center",
                gap: 5,
              }}
            >
              <Play size={11} /> Test Flow
            </button>

            {/* Mini mode toggle */}
            <button
              type="button"
              onClick={() => setIsMiniMode(!isMiniMode)}
              style={{
                fontSize: 10,
                fontFamily: "var(--font-mono)",
                padding: "4px 9px",
                borderRadius: "var(--radius-sm)",
                cursor: "pointer",
                border: "1px solid rgba(34, 211, 238, 0.5)",
                background: "rgba(34, 211, 238, 0.15)",
                color: "var(--color-nova-cyan)",
                display: "flex",
                alignItems: "center",
                gap: 5,
              }}
            >
              <Sparkles size={11} /> {isMiniMode ? "Exit Mini" : "Mini Mode"}
            </button>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
