import { motion } from "framer-motion";
import {
  Home,
  Eye,
  Globe,
  Cpu,
  Monitor,
  Brain,
  Activity,
  Settings,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { useNova } from "../context/useNova";

const NAV_ITEMS = [
  { id: "home", label: "Core", icon: Home },
  { id: "vision", label: "Vision", icon: Eye },
  { id: "web", label: "Web Intelligence", icon: Globe },
  { id: "skills", label: "Skills Hub", icon: Cpu },
  { id: "computer", label: "Computer Control", icon: Monitor },
  { id: "memory", label: "Memory", icon: Brain },
  { id: "activity", label: "Activity Log", icon: Activity },
  { id: "settings", label: "Settings", icon: Settings },
];

export default function Sidebar() {
  const { currentView, setCurrentView, sidebarCollapsed, setSidebarCollapsed } =
    useNova();

  return (
    <motion.aside
      className="glass-panel"
      animate={{ width: sidebarCollapsed ? 64 : 220 }}
      transition={{ duration: 0.25, ease: [0.4, 0, 0.2, 1] }}
      style={{
        height: "100%",
        display: "flex",
        flexDirection: "column",
        borderRight: "var(--border-subtle)",
        padding: "12px 8px",
        position: "relative",
        zIndex: 5,
        flexShrink: 0,
      }}
    >
      {/* Navigation List */}
      <nav
        style={{
          display: "flex",
          flexDirection: "column",
          gap: 6,
          flex: 1,
        }}
      >
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          const isActive = currentView === item.id;

          return (
            <motion.button
              key={item.id}
              type="button"
              onClick={() => setCurrentView(item.id)}
              whileHover={{ x: sidebarCollapsed ? 0 : 3 }}
              whileTap={{ scale: 0.98 }}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 12,
                padding: sidebarCollapsed ? "10px 0" : "10px 12px",
                justifyContent: sidebarCollapsed ? "center" : "flex-start",
                borderRadius: "var(--radius-md)",
                background: isActive
                  ? "rgba(123, 92, 240, 0.18)"
                  : "transparent",
                border: isActive
                  ? "1px solid rgba(123, 92, 240, 0.45)"
                  : "1px solid transparent",
                color: isActive
                  ? "var(--color-text-primary)"
                  : "var(--color-text-secondary)",
                cursor: "pointer",
                transition:
                  "background 0.15s ease, border-color 0.15s ease, color 0.15s ease",
                position: "relative",
                width: "100%",
                boxShadow: isActive
                  ? "0 2px 12px rgba(123, 92, 240, 0.25)"
                  : "none",
              }}
              title={sidebarCollapsed ? item.label : ""}
              onMouseEnter={(e) => {
                if (!isActive) {
                  e.currentTarget.style.background =
                    "rgba(255, 255, 255, 0.05)";
                  e.currentTarget.style.color = "var(--color-text-primary)";
                }
              }}
              onMouseLeave={(e) => {
                if (!isActive) {
                  e.currentTarget.style.background = "transparent";
                  e.currentTarget.style.color = "var(--color-text-secondary)";
                }
              }}
            >
              {/* Active bar indicator */}
              {isActive && (
                <motion.div
                  layoutId="sidebarActiveBar"
                  style={{
                    position: "absolute",
                    left: 0,
                    top: "20%",
                    bottom: "20%",
                    width: 3,
                    borderRadius: 2,
                    backgroundColor: "var(--color-nova-cyan)",
                    boxShadow: "0 0 8px var(--color-nova-cyan)",
                  }}
                />
              )}

              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  width: 24,
                  height: 24,
                  borderRadius: 6,
                  background: isActive
                    ? "rgba(34, 211, 238, 0.12)"
                    : "transparent",
                  flexShrink: 0,
                }}
              >
                <Icon
                  size={18}
                  color={isActive ? "var(--color-nova-cyan)" : "currentColor"}
                  style={{ flexShrink: 0 }}
                />
              </div>

              {!sidebarCollapsed && (
                <motion.span
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ duration: 0.15 }}
                  style={{
                    fontSize: 13,
                    fontWeight: isActive ? 600 : 400,
                    whiteSpace: "nowrap",
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    letterSpacing: isActive ? "0.01em" : "normal",
                  }}
                >
                  {item.label}
                </motion.span>
              )}
            </motion.button>
          );
        })}
      </nav>

      {/* Collapse / Expand toggle button at bottom */}
      <div
        style={{
          borderTop: "var(--border-subtle)",
          paddingTop: 8,
          display: "flex",
          justifyContent: sidebarCollapsed ? "center" : "flex-end",
        }}
      >
        <button
          type="button"
          onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
          className="btn-icon"
          style={{ width: 34, height: 34 }}
          title={sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}
        >
          {sidebarCollapsed ? (
            <ChevronRight size={16} />
          ) : (
            <ChevronLeft size={16} />
          )}
        </button>
      </div>
    </motion.aside>
  );
}
