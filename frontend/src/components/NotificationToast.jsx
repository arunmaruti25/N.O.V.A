import { motion, AnimatePresence } from "framer-motion";
import {
  Info,
  CheckCircle2,
  AlertCircle,
  AlertTriangle,
  X,
} from "lucide-react";
import { useNova } from "../context/useNova";

export default function NotificationToast() {
  const { notifications, removeNotification } = useNova();

  return (
    <div
      style={{
        position: "fixed",
        bottom: 20,
        right: 20,
        display: "flex",
        flexDirection: "column",
        gap: 8,
        zIndex: 9990,
        pointerEvents: "none",
      }}
    >
      <AnimatePresence>
        {notifications.map((notif) => {
          let Icon = Info;
          let iconColor = "var(--color-nova-cyan)";
          let borderColor = "rgba(34, 211, 238, 0.3)";

          if (notif.type === "success") {
            Icon = CheckCircle2;
            iconColor = "var(--color-state-success)";
            borderColor = "rgba(5, 150, 105, 0.4)";
          } else if (notif.type === "error") {
            Icon = AlertCircle;
            iconColor = "var(--color-state-error)";
            borderColor = "rgba(220, 38, 38, 0.4)";
          } else if (notif.type === "warning") {
            Icon = AlertTriangle;
            iconColor = "var(--color-state-confirm)";
            borderColor = "rgba(217, 119, 6, 0.4)";
          }

          return (
            <motion.div
              key={notif.id}
              initial={{ opacity: 0, x: 40, scale: 0.95 }}
              animate={{ opacity: 1, x: 0, scale: 1 }}
              exit={{ opacity: 0, x: 30, scale: 0.95 }}
              transition={{ duration: 0.2 }}
              className="glass-card"
              style={{
                width: 320,
                padding: "12px 14px",
                background: "rgba(13, 17, 26, 0.94)",
                border: `1px solid ${borderColor}`,
                boxShadow: "var(--shadow-modal)",
                display: "flex",
                alignItems: "flex-start",
                gap: 10,
                pointerEvents: "auto",
              }}
            >
              <Icon
                size={18}
                color={iconColor}
                style={{ flexShrink: 0, marginTop: 2 }}
              />
              <div style={{ flex: 1, minWidth: 0 }}>
                <div
                  style={{
                    fontSize: 13,
                    fontWeight: 600,
                    color: "var(--color-text-primary)",
                  }}
                >
                  {notif.title}
                </div>
                {notif.message && (
                  <div
                    style={{
                      fontSize: 12,
                      color: "var(--color-text-secondary)",
                      marginTop: 2,
                      lineHeight: 1.35,
                    }}
                  >
                    {notif.message}
                  </div>
                )}
              </div>
              <button
                type="button"
                onClick={() => removeNotification(notif.id)}
                className="btn-icon"
                style={{ width: 22, height: 22, flexShrink: 0 }}
              >
                <X size={14} />
              </button>
            </motion.div>
          );
        })}
      </AnimatePresence>
    </div>
  );
}
