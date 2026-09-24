import { motion } from "framer-motion";
import {
  Eye,
  Globe,
  Monitor,
  Cpu,
  Activity,
  ShieldCheck,
  Zap,
} from "lucide-react";
import NovaCore from "../components/NovaCore";
import VoiceBar from "../components/VoiceBar";
import { useNova } from "../context/useNova";

export default function HomeView() {
  const { setCurrentView, triggerVoiceCommand, activeModel } = useNova();

  const quickActions = [
    {
      title: "Analyze Screen",
      desc: "Multimodal vision perception",
      badge: "VISION HUD",
      icon: Eye,
      color: "var(--color-nova-cyan)",
      bgGradient:
        "linear-gradient(135deg, rgba(34, 211, 238, 0.15) 0%, rgba(14, 116, 144, 0.05) 100%)",
      borderColor: "rgba(34, 211, 238, 0.3)",
      action: () => triggerVoiceCommand("NOVA, what's on my screen?"),
    },
    {
      title: "Web Intelligence",
      desc: "Real-time research & synthesis",
      badge: "LIVE WEB",
      icon: Globe,
      color: "var(--color-nova-secondary)",
      bgGradient:
        "linear-gradient(135deg, rgba(91, 141, 239, 0.15) 0%, rgba(30, 58, 138, 0.05) 100%)",
      borderColor: "rgba(91, 141, 239, 0.3)",
      action: () => setCurrentView("web"),
    },
    {
      title: "Computer Control",
      desc: "Windows system orchestration",
      badge: "SYSTEM API",
      icon: Monitor,
      color: "#34d399",
      bgGradient:
        "linear-gradient(135deg, rgba(52, 211, 153, 0.15) 0%, rgba(6, 78, 59, 0.05) 100%)",
      borderColor: "rgba(52, 211, 153, 0.3)",
      action: () => setCurrentView("computer"),
    },
    {
      title: "Skills Hub",
      desc: "Tool plugins & permissions",
      badge: "EXTENSIBLE",
      icon: Cpu,
      color: "var(--color-text-accent)",
      bgGradient:
        "linear-gradient(135deg, rgba(167, 139, 250, 0.15) 0%, rgba(76, 29, 149, 0.05) 100%)",
      borderColor: "rgba(167, 139, 250, 0.3)",
      action: () => setCurrentView("skills"),
    },
  ];

  return (
    <div
      style={{
        flex: 1,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: "20px 24px",
        position: "relative",
        overflowY: "auto",
        overflowX: "hidden",
        gap: 22,
      }}
    >
      {/* Central NOVA Core Orb Hero Zone */}
      <motion.div
        initial={{ scale: 0.94, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ duration: 0.35, ease: "easeOut" }}
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          marginTop: 6,
        }}
      >
        <NovaCore size={210} />
      </motion.div>

      {/* Voice Interaction & Input Command Area */}
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35, delay: 0.08 }}
        style={{ width: "100%", display: "flex", justifyContent: "center" }}
      >
        <VoiceBar />
      </motion.div>

      {/* Polished Quick Action Launchpad Grid */}
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35, delay: 0.15 }}
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
          gap: 12,
          width: "100%",
          maxWidth: 860,
        }}
      >
        {quickActions.map((act) => {
          const Icon = act.icon;
          return (
            <motion.button
              key={act.title}
              type="button"
              onClick={act.action}
              whileHover={{ y: -3, scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              className="glass-card"
              style={{
                padding: "14px 16px",
                display: "flex",
                flexDirection: "column",
                gap: 10,
                cursor: "pointer",
                textAlign: "left",
                border: `1px solid ${act.borderColor}`,
                background: act.bgGradient,
                position: "relative",
                overflow: "hidden",
              }}
            >
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                }}
              >
                <div
                  style={{
                    width: 36,
                    height: 36,
                    borderRadius: "var(--radius-md)",
                    background: "rgba(255, 255, 255, 0.06)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    flexShrink: 0,
                    boxShadow: "0 2px 8px rgba(0, 0, 0, 0.3)",
                  }}
                >
                  <Icon size={18} color={act.color} />
                </div>

                <span
                  style={{
                    fontSize: 9,
                    fontFamily: "var(--font-mono)",
                    color: act.color,
                    letterSpacing: "0.08em",
                    background: "rgba(255, 255, 255, 0.04)",
                    padding: "2px 6px",
                    borderRadius: 4,
                  }}
                >
                  {act.badge}
                </span>
              </div>

              <div>
                <div
                  style={{
                    fontSize: 13,
                    fontWeight: 600,
                    color: "var(--color-text-primary)",
                    fontFamily: "var(--font-heading)",
                    marginBottom: 2,
                  }}
                >
                  {act.title}
                </div>
                <div
                  style={{
                    fontSize: 11,
                    color: "var(--color-text-secondary)",
                    lineHeight: 1.35,
                  }}
                >
                  {act.desc}
                </div>
              </div>
            </motion.button>
          );
        })}
      </motion.div>

      {/* Bottom Telemetry & Status Bar */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.4, delay: 0.22 }}
        style={{
          display: "flex",
          alignItems: "center",
          gap: 18,
          fontSize: 11,
          fontFamily: "var(--font-mono)",
          color: "var(--color-text-tertiary)",
          padding: "6px 16px",
          borderRadius: "var(--radius-full)",
          background: "rgba(255, 255, 255, 0.02)",
          border: "var(--border-subtle)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <Zap size={12} color="var(--color-nova-cyan)" />
          <span>
            INFERENCE: {activeModel.provider.toUpperCase()} (
            {activeModel.latency})
          </span>
        </div>
        <div
          style={{
            width: 4,
            height: 4,
            borderRadius: "50%",
            backgroundColor: "rgba(255, 255, 255, 0.15)",
          }}
        />
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <ShieldCheck size={12} color="var(--color-state-success)" />
          <span>SAFETY SHIELD: ACTIVE</span>
        </div>
        <div
          style={{
            width: 4,
            height: 4,
            borderRadius: "50%",
            backgroundColor: "rgba(255, 255, 255, 0.15)",
          }}
        />
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <Activity size={12} color="var(--color-nova-primary)" />
          <span>WINDOWS IPC: READY</span>
        </div>
      </motion.div>
    </div>
  );
}
