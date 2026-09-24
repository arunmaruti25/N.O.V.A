import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Minimize2,
  Bell,
  Cpu,
  Check,
  ChevronDown,
  Sparkles,
  Wifi,
  Sliders,
} from "lucide-react";
import { useNova } from "../context/useNova";

export default function Header() {
  const {
    activeModel,
    setActiveModel,
    availableModels,
    isAutoRouting,
    setIsAutoRouting,
    setIsMiniMode,
    notifications,
    setCurrentView,
  } = useNova();

  const [isModelMenuOpen, setIsModelMenuOpen] = useState(false);
  const menuRef = useRef(null);

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event) {
      if (menuRef.current && !menuRef.current.contains(event.target)) {
        setIsModelMenuOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  return (
    <header
      className="glass-panel"
      style={{
        height: 52,
        width: "100%",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "0 20px",
        borderBottom: "var(--border-subtle)",
        position: "relative",
        zIndex: 10,
      }}
    >
      {/* Wordmark & Identity */}
      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <div
            style={{
              width: 10,
              height: 10,
              borderRadius: "50%",
              background: "linear-gradient(135deg, #7b5cf0 0%, #22d3ee 100%)",
              boxShadow: "0 0 10px rgba(123, 92, 240, 0.8)",
            }}
          />
          <span
            style={{
              fontFamily: "var(--font-heading)",
              fontSize: 18,
              fontWeight: 700,
              letterSpacing: "0.12em",
              color: "var(--color-text-primary)",
            }}
          >
            NOVA
          </span>
        </div>

        <span
          className="badge"
          style={{
            background: "rgba(123, 92, 240, 0.12)",
            color: "var(--color-text-accent)",
            border: "1px solid rgba(123, 92, 240, 0.25)",
            fontSize: 10,
            fontFamily: "var(--font-mono)",
          }}
        >
          v2.4 NEURAL
        </span>
      </div>

      {/* Center: Model Routing Pill & Popover */}
      <div style={{ position: "relative" }} ref={menuRef}>
        <button
          type="button"
          onClick={() => setIsModelMenuOpen(!isModelMenuOpen)}
          className="badge"
          style={{
            height: 32,
            padding: "0 14px",
            background: "rgba(255, 255, 255, 0.04)",
            border: "var(--border-default)",
            color: "var(--color-text-primary)",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            gap: 8,
            fontFamily: "var(--font-body)",
            transition: "all 0.15s ease",
          }}
          title="Click to view AI Model Routing details"
        >
          <span
            style={{
              width: 7,
              height: 7,
              borderRadius: "50%",
              backgroundColor: activeModel.color,
              boxShadow: `0 0 8px ${activeModel.color}`,
            }}
          />
          <span style={{ fontWeight: 600, fontSize: 12 }}>
            {activeModel.provider}
          </span>
          <span style={{ color: "var(--color-text-tertiary)", fontSize: 11 }}>
            —
          </span>
          <span style={{ color: "var(--color-text-secondary)", fontSize: 12 }}>
            {activeModel.mode}
          </span>
          <span
            style={{
              fontSize: 10,
              fontFamily: "var(--font-mono)",
              color: "var(--color-nova-cyan)",
              marginLeft: 4,
              opacity: 0.8,
            }}
          >
            {activeModel.latency}
          </span>
          <ChevronDown size={14} color="var(--color-text-tertiary)" />
        </button>

        {/* Model Routing Details Popover */}
        <AnimatePresence>
          {isModelMenuOpen && (
            <motion.div
              initial={{ opacity: 0, y: 8, scale: 0.96 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 4, scale: 0.96 }}
              transition={{ duration: 0.15 }}
              className="glass-card"
              style={{
                position: "absolute",
                top: 40,
                left: "50%",
                transform: "translateX(-50%)",
                width: 320,
                padding: 16,
                background: "rgba(13, 17, 26, 0.95)",
                boxShadow: "var(--shadow-modal)",
                border: "var(--border-strong)",
                zIndex: 100,
              }}
            >
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  marginBottom: 12,
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                  <Cpu size={15} color="var(--color-nova-primary)" />
                  <span
                    style={{
                      fontFamily: "var(--font-heading)",
                      fontSize: 12,
                      fontWeight: 600,
                      color: "var(--color-text-primary)",
                      letterSpacing: "0.04em",
                    }}
                  >
                    DYNAMIC MODEL ROUTER
                  </span>
                </div>
                <span
                  style={{
                    fontSize: 10,
                    color: isAutoRouting
                      ? "var(--color-state-success)"
                      : "var(--color-text-tertiary)",
                    fontFamily: "var(--font-mono)",
                  }}
                >
                  {isAutoRouting ? "AUTO-ROUTING" : "MANUAL"}
                </span>
              </div>

              <p
                style={{
                  fontSize: 12,
                  color: "var(--color-text-secondary)",
                  marginBottom: 14,
                }}
              >
                NOVA automatically matches task complexity to the optimal
                inference model.
              </p>

              <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                {availableModels.map((m) => {
                  const isSelected = activeModel.provider === m.provider;
                  return (
                    <button
                      key={m.provider}
                      type="button"
                      onClick={() => {
                        setActiveModel(m);
                        setIsAutoRouting(false);
                        setIsModelMenuOpen(false);
                      }}
                      style={{
                        padding: "8px 10px",
                        borderRadius: "var(--radius-md)",
                        background: isSelected
                          ? "rgba(123, 92, 240, 0.15)"
                          : "rgba(255, 255, 255, 0.02)",
                        border: isSelected
                          ? "1px solid rgba(123, 92, 240, 0.4)"
                          : "var(--border-subtle)",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                        cursor: "pointer",
                        textAlign: "left",
                      }}
                    >
                      <div
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: 8,
                        }}
                      >
                        <span
                          style={{
                            width: 8,
                            height: 8,
                            borderRadius: "50%",
                            backgroundColor: m.color,
                          }}
                        />
                        <div>
                          <div
                            style={{
                              fontSize: 12,
                              fontWeight: 600,
                              color: "var(--color-text-primary)",
                            }}
                          >
                            {m.provider}{" "}
                            <span
                              style={{
                                fontWeight: 400,
                                color: "var(--color-text-secondary)",
                              }}
                            >
                              ({m.mode})
                            </span>
                          </div>
                          <div
                            style={{
                              fontSize: 10,
                              color: "var(--color-text-tertiary)",
                            }}
                          >
                            {m.desc}
                          </div>
                        </div>
                      </div>
                      <div
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: 6,
                        }}
                      >
                        <span
                          style={{
                            fontSize: 10,
                            fontFamily: "var(--font-mono)",
                            color: "var(--color-text-tertiary)",
                          }}
                        >
                          {m.latency}
                        </span>
                        {isSelected && (
                          <Check size={14} color="var(--color-nova-primary)" />
                        )}
                      </div>
                    </button>
                  );
                })}
              </div>

              <div
                style={{
                  marginTop: 12,
                  paddingTop: 10,
                  borderTop: "var(--border-subtle)",
                  display: "flex",
                  justifyContent: "space-between",
                }}
              >
                <button
                  type="button"
                  onClick={() => setIsAutoRouting(true)}
                  style={{
                    background: "transparent",
                    border: "none",
                    fontSize: 11,
                    color: isAutoRouting
                      ? "var(--color-nova-cyan)"
                      : "var(--color-text-secondary)",
                    cursor: "pointer",
                    display: "flex",
                    alignItems: "center",
                    gap: 4,
                  }}
                >
                  <Sparkles size={12} /> Reset to Auto-Routing
                </button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Right Controls: Telemetry, Notifications, Minimize to Floating Mini NOVA */}
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 6,
            paddingRight: 10,
            borderRight: "var(--border-subtle)",
            fontSize: 11,
            color: "var(--color-text-secondary)",
            fontFamily: "var(--font-mono)",
          }}
        >
          <Wifi size={13} color="var(--color-state-success)" />
          <span>CONNECTED</span>
        </div>

        {/* Notifications Icon */}
        <button
          type="button"
          onClick={() => setCurrentView("activity")}
          className="btn-icon"
          title="Notifications & Activity"
          style={{ position: "relative" }}
        >
          <Bell size={17} />
          {notifications.length > 0 && (
            <span
              style={{
                position: "absolute",
                top: 8,
                right: 8,
                width: 6,
                height: 6,
                borderRadius: "50%",
                backgroundColor: "var(--color-state-error)",
              }}
            />
          )}
        </button>

        {/* Settings button */}
        <button
          type="button"
          onClick={() => setCurrentView("settings")}
          className="btn-icon"
          title="Settings"
        >
          <Sliders size={17} />
        </button>

        {/* Minimize to Mini NOVA Button */}
        <button
          type="button"
          onClick={() => setIsMiniMode(true)}
          className="btn-icon"
          title="Minimize to Floating Mini NOVA (Ctrl+M)"
          style={{ color: "var(--color-nova-cyan)" }}
        >
          <Minimize2 size={17} />
        </button>
      </div>
    </header>
  );
}
