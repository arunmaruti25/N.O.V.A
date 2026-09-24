import { useState } from "react";
import { Settings, Mic, Palette, Cpu, Shield, Keyboard } from "lucide-react";
import { useNova } from "../context/useNova";

export default function SettingsView() {
  const {
    reducedMotion,
    setReducedMotion,
    isAutoRouting,
    setIsAutoRouting,
    addNotification,
  } = useNova();
  const [wakeWordEnabled, setWakeWordEnabled] = useState(true);
  const [strictPermissions, setStrictPermissions] = useState(true);
  const [activeTab, setActiveTab] = useState("general");

  const tabs = [
    { id: "general", label: "General & Voice", icon: Mic },
    { id: "appearance", label: "Appearance & Motion", icon: Palette },
    { id: "models", label: "AI Model Routing", icon: Cpu },
    { id: "security", label: "Safety & Permissions", icon: Shield },
    { id: "shortcuts", label: "Keyboard Shortcuts", icon: Keyboard },
  ];

  return (
    <div
      style={{
        flex: 1,
        padding: "24px 28px",
        overflowY: "auto",
        display: "flex",
        flexDirection: "column",
        gap: 20,
      }}
    >
      {/* Header */}
      <div>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
            marginBottom: 4,
          }}
        >
          <Settings size={20} color="var(--color-nova-primary)" />
          <h1
            style={{
              fontFamily: "var(--font-heading)",
              fontSize: 22,
              fontWeight: 600,
              color: "var(--color-text-primary)",
            }}
          >
            System Settings & Preferences
          </h1>
        </div>
        <p style={{ fontSize: 13, color: "var(--color-text-secondary)" }}>
          Configure voice perception, AI inference engine preferences, visual
          fidelity, and security rules.
        </p>
      </div>

      {/* Tabs Layout */}
      <div
        style={{ display: "grid", gridTemplateColumns: "220px 1fr", gap: 20 }}
      >
        {/* Navigation Sidebar inside Settings */}
        <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isSelected = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                type="button"
                onClick={() => setActiveTab(tab.id)}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 10,
                  padding: "10px 14px",
                  borderRadius: "var(--radius-md)",
                  background: isSelected
                    ? "rgba(123, 92, 240, 0.16)"
                    : "transparent",
                  border: isSelected
                    ? "1px solid rgba(123, 92, 240, 0.4)"
                    : "1px solid transparent",
                  color: isSelected
                    ? "var(--color-text-primary)"
                    : "var(--color-text-secondary)",
                  cursor: "pointer",
                  textAlign: "left",
                  fontSize: 13,
                  fontWeight: isSelected ? 600 : 400,
                }}
              >
                <Icon
                  size={16}
                  color={isSelected ? "var(--color-nova-cyan)" : "currentColor"}
                />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>

        {/* Content Box */}
        <div
          className="glass-card"
          style={{
            padding: 24,
            display: "flex",
            flexDirection: "column",
            gap: 20,
          }}
        >
          {activeTab === "general" && (
            <>
              <div>
                <h3
                  style={{
                    fontSize: 16,
                    fontFamily: "var(--font-heading)",
                    marginBottom: 6,
                  }}
                >
                  Voice & Wake Word
                </h3>
                <p
                  style={{ fontSize: 12, color: "var(--color-text-secondary)" }}
                >
                  Configure always-on voice recognition and wake word detection
                  parameters.
                </p>
              </div>

              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  padding: "12px 0",
                  borderTop: "var(--border-subtle)",
                }}
              >
                <div>
                  <div style={{ fontSize: 13, fontWeight: 500 }}>
                    Wake Word Activation ("Hey NOVA")
                  </div>
                  <div
                    style={{
                      fontSize: 11,
                      color: "var(--color-text-tertiary)",
                    }}
                  >
                    Passively listens for vocal activation trigger
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => {
                    setWakeWordEnabled(!wakeWordEnabled);
                    addNotification({
                      type: "info",
                      title: "Setting Updated",
                      message: `Wake word ${!wakeWordEnabled ? "enabled" : "disabled"}.`,
                    });
                  }}
                  className="btn btn-secondary"
                  style={{ fontSize: 12, padding: "4px 12px" }}
                >
                  {wakeWordEnabled ? "Enabled" : "Disabled"}
                </button>
              </div>

              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  padding: "12px 0",
                  borderTop: "var(--border-subtle)",
                }}
              >
                <div>
                  <div style={{ fontSize: 13, fontWeight: 500 }}>
                    Speech Synthesis Engine
                  </div>
                  <div
                    style={{
                      fontSize: 11,
                      color: "var(--color-text-tertiary)",
                    }}
                  >
                    Neural voice timbre and pacing profile
                  </div>
                </div>
                <span
                  className="badge"
                  style={{
                    background: "rgba(123, 92, 240, 0.15)",
                    color: "var(--color-nova-cyan)",
                  }}
                >
                  Futuristic Calm (Female/Low Pitch)
                </span>
              </div>
            </>
          )}

          {activeTab === "appearance" && (
            <>
              <div>
                <h3
                  style={{
                    fontSize: 16,
                    fontFamily: "var(--font-heading)",
                    marginBottom: 6,
                  }}
                >
                  Appearance & Motion
                </h3>
                <p
                  style={{ fontSize: 12, color: "var(--color-text-secondary)" }}
                >
                  Control futuristic visual effects, glassmorphic blur, and
                  accessibility options.
                </p>
              </div>

              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  padding: "12px 0",
                  borderTop: "var(--border-subtle)",
                }}
              >
                <div>
                  <div style={{ fontSize: 13, fontWeight: 500 }}>
                    Reduced Motion Mode
                  </div>
                  <div
                    style={{
                      fontSize: 11,
                      color: "var(--color-text-tertiary)",
                    }}
                  >
                    Removes continuous orb rotations, shakes, and fast scaling
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => {
                    setReducedMotion(!reducedMotion);
                    addNotification({
                      type: "info",
                      title: "Motion Mode",
                      message: `Reduced motion ${!reducedMotion ? "activated" : "deactivated"}.`,
                    });
                  }}
                  className="btn btn-secondary"
                  style={{ fontSize: 12, padding: "4px 12px" }}
                >
                  {reducedMotion ? "On (Static)" : "Off (Full Motion)"}
                </button>
              </div>

              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  padding: "12px 0",
                  borderTop: "var(--border-subtle)",
                }}
              >
                <div>
                  <div style={{ fontSize: 13, fontWeight: 500 }}>
                    Color Atmosphere Palette
                  </div>
                  <div
                    style={{
                      fontSize: 11,
                      color: "var(--color-text-tertiary)",
                    }}
                  >
                    Deep Void & Violet-Cyan Neon Accents
                  </div>
                </div>
                <span
                  className="badge"
                  style={{
                    background: "rgba(34, 211, 238, 0.15)",
                    color: "var(--color-nova-cyan)",
                  }}
                >
                  Dark Futuristic (Default)
                </span>
              </div>
            </>
          )}

          {activeTab === "models" && (
            <>
              <div>
                <h3
                  style={{
                    fontSize: 16,
                    fontFamily: "var(--font-heading)",
                    marginBottom: 6,
                  }}
                >
                  Inference Routing
                </h3>
                <p
                  style={{ fontSize: 12, color: "var(--color-text-secondary)" }}
                >
                  Manage autonomous model selection thresholds between fast
                  engines and deep reasoning backbones.
                </p>
              </div>

              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  padding: "12px 0",
                  borderTop: "var(--border-subtle)",
                }}
              >
                <div>
                  <div style={{ fontSize: 13, fontWeight: 500 }}>
                    Intelligent Auto-Routing
                  </div>
                  <div
                    style={{
                      fontSize: 11,
                      color: "var(--color-text-tertiary)",
                    }}
                  >
                    Routes coding to NVIDIA, quick chat to Groq, and vision to
                    Gemini
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => setIsAutoRouting(!isAutoRouting)}
                  className="btn btn-secondary"
                  style={{ fontSize: 12, padding: "4px 12px" }}
                >
                  {isAutoRouting ? "Active" : "Manual Selection"}
                </button>
              </div>
            </>
          )}

          {activeTab === "security" && (
            <>
              <div>
                <h3
                  style={{
                    fontSize: 16,
                    fontFamily: "var(--font-heading)",
                    marginBottom: 6,
                  }}
                >
                  Safety & System Protection
                </h3>
                <p
                  style={{ fontSize: 12, color: "var(--color-text-secondary)" }}
                >
                  Enforce strict user confirmation for irreversible actions.
                </p>
              </div>

              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  padding: "12px 0",
                  borderTop: "var(--border-subtle)",
                }}
              >
                <div>
                  <div style={{ fontSize: 13, fontWeight: 500 }}>
                    Strict Confirmation on Destructive Actions
                  </div>
                  <div
                    style={{
                      fontSize: 11,
                      color: "var(--color-text-tertiary)",
                    }}
                  >
                    Requires modal authorization before file deletes or power
                    shutdown
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => setStrictPermissions(!strictPermissions)}
                  className="btn btn-secondary"
                  style={{ fontSize: 12, padding: "4px 12px" }}
                >
                  {strictPermissions ? "Strict (Recommended)" : "Permissive"}
                </button>
              </div>
            </>
          )}

          {activeTab === "shortcuts" && (
            <>
              <div>
                <h3
                  style={{
                    fontSize: 16,
                    fontFamily: "var(--font-heading)",
                    marginBottom: 6,
                  }}
                >
                  Global Keyboard Shortcuts
                </h3>
                <p
                  style={{ fontSize: 12, color: "var(--color-text-secondary)" }}
                >
                  Instant control over NOVA across any active Windows
                  application.
                </p>
              </div>

              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  gap: 10,
                  borderTop: "var(--border-subtle)",
                  paddingTop: 12,
                }}
              >
                {[
                  { keys: "Ctrl + Shift + N", desc: "Activate Voice Input" },
                  { keys: "Ctrl + M", desc: "Toggle Minimized Floating Orb" },
                  { keys: "Esc", desc: "Interrupt NOVA / Cancel Active Task" },
                  { keys: "Enter / Space", desc: "Confirm Action in Dialog" },
                ].map((s) => (
                  <div
                    key={s.keys}
                    style={{
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      padding: "8px 12px",
                      background: "rgba(255, 255, 255, 0.02)",
                      borderRadius: "var(--radius-md)",
                      border: "var(--border-subtle)",
                    }}
                  >
                    <span
                      style={{
                        fontSize: 13,
                        color: "var(--color-text-primary)",
                      }}
                    >
                      {s.desc}
                    </span>
                    <span
                      style={{
                        fontFamily: "var(--font-mono)",
                        fontSize: 11,
                        background: "rgba(123, 92, 240, 0.15)",
                        color: "var(--color-nova-cyan)",
                        padding: "3px 8px",
                        borderRadius: 4,
                        border: "1px solid rgba(123, 92, 240, 0.3)",
                      }}
                    >
                      {s.keys}
                    </span>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
