import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Maximize2, Mic, X, Sparkles, GripHorizontal } from "lucide-react";
import { useNova } from "../context/useNova";
import { NOVA_STATES } from "../context/constants";
import NovaCore from "./NovaCore";

export default function MiniNova() {
  const {
    status,
    statusDetail,
    transcript,
    setIsMiniMode,
    triggerVoiceCommand,
    cancelOperation,
  } = useNova();

  const [showStatusPopup, setShowStatusPopup] = useState(true);

  const handleOrbClick = () => {
    if (status === NOVA_STATES.IDLE) {
      triggerVoiceCommand();
    } else {
      cancelOperation();
    }
  };

  return (
    <motion.div
      drag
      dragConstraints={{ left: -800, right: 20, top: -700, bottom: 20 }}
      dragElastic={0.08}
      initial={{ scale: 0.6, opacity: 0, y: 35 }}
      animate={{ scale: 1, opacity: 1, y: 0 }}
      exit={{ scale: 0.6, opacity: 0, y: 35 }}
      transition={{ type: "spring", stiffness: 360, damping: 25 }}
      style={{
        position: "fixed",
        bottom: 24,
        right: 24,
        zIndex: 9999,
        display: "flex",
        flexDirection: "column",
        alignItems: "flex-end",
        gap: 10,
        userSelect: "none",
      }}
    >
      {/* Floating Status / Spoken response bubble above mini orb */}
      <AnimatePresence>
        {showStatusPopup && (statusDetail || transcript) && (
          <motion.div
            initial={{ opacity: 0, y: 10, scale: 0.92 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 8, scale: 0.92 }}
            className="glass-card"
            style={{
              padding: "10px 14px",
              maxWidth: 260,
              background: "rgba(13, 17, 28, 0.96)",
              border: "1px solid rgba(123, 92, 240, 0.45)",
              boxShadow:
                "var(--shadow-modal), 0 0 20px rgba(123, 92, 240, 0.25)",
              borderRadius: "var(--radius-lg)",
              position: "relative",
            }}
          >
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                marginBottom: 4,
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: 5 }}>
                <Sparkles size={12} color="var(--color-nova-cyan)" />
                <span
                  style={{
                    fontSize: 10,
                    fontFamily: "var(--font-mono)",
                    color: "var(--color-nova-cyan)",
                    letterSpacing: "0.08em",
                  }}
                >
                  {status}
                </span>
              </div>
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  setShowStatusPopup(false);
                }}
                className="btn-icon"
                style={{ width: 16, height: 16 }}
                title="Dismiss status"
              >
                <X size={12} />
              </button>
            </div>
            <div
              style={{
                fontSize: 12,
                color: "var(--color-text-primary)",
                lineHeight: 1.4,
                fontWeight: 500,
              }}
            >
              {transcript || statusDetail}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Floating Mini Widget Bar */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          background: "rgba(10, 14, 24, 0.92)",
          backdropFilter: "blur(24px)",
          WebkitBackdropFilter: "blur(24px)",
          border: "1px solid rgba(123, 92, 240, 0.4)",
          borderRadius: "var(--radius-full)",
          padding: "6px 10px 6px 6px",
          boxShadow: "var(--shadow-mini), 0 0 25px rgba(123, 92, 240, 0.3)",
          cursor: "grab",
        }}
      >
        {/* Subtle drag handle grip */}
        <div
          style={{
            color: "rgba(255, 255, 255, 0.25)",
            display: "flex",
            alignItems: "center",
            marginLeft: 2,
          }}
        >
          <GripHorizontal size={14} />
        </div>

        {/* Miniature NOVA Core Orb */}
        <div title="Click to speak / cancel in background mode">
          <NovaCore size={54} isMini={true} onClick={handleOrbClick} />
        </div>

        {/* Quick Voice Trigger */}
        <motion.button
          type="button"
          onClick={() => triggerVoiceCommand("NOVA, what is on my screen?")}
          whileHover={{ scale: 1.1 }}
          whileTap={{ scale: 0.92 }}
          className="btn-icon"
          style={{
            width: 32,
            height: 32,
            borderRadius: "50%",
            background: "rgba(255, 255, 255, 0.08)",
          }}
          title="Voice command test"
        >
          <Mic size={15} color="var(--color-nova-cyan)" />
        </motion.button>

        {/* Restore Full UI Button */}
        <motion.button
          type="button"
          onClick={() => setIsMiniMode(false)}
          whileHover={{ scale: 1.1 }}
          whileTap={{ scale: 0.92 }}
          className="btn-icon"
          style={{
            width: 32,
            height: 32,
            borderRadius: "50%",
            background: "linear-gradient(135deg, #7b5cf0 0%, #6342e8 100%)",
            color: "#ffffff",
            boxShadow: "0 2px 8px rgba(123, 92, 240, 0.5)",
          }}
          title="Expand to Full Interface (Ctrl+M)"
        >
          <Maximize2 size={14} />
        </motion.button>
      </div>
    </motion.div>
  );
}
