import { useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { AlertTriangle, ShieldAlert, X } from "lucide-react";
import { useNova } from "../context/useNova";

export default function PermissionModal() {
  const { permissionState } = useNova();
  const { isOpen, title, description, detail, onConfirm, onCancel } =
    permissionState;

  // Keyboard accessibility: Escape to cancel
  useEffect(() => {
    function handleKeyDown(e) {
      if (e.key === "Escape" && isOpen && onCancel) {
        onCancel();
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onCancel]);

  if (!isOpen) return null;

  return (
    <AnimatePresence>
      <div
        style={{
          position: "fixed",
          inset: 0,
          backgroundColor: "rgba(3, 4, 9, 0.78)",
          backdropFilter: "blur(8px)",
          WebkitBackdropFilter: "blur(8px)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          zIndex: 10000,
          padding: 20,
        }}
        onClick={onCancel}
        role="dialog"
        aria-modal="true"
        aria-labelledby="perm-modal-title"
      >
        <motion.div
          initial={{ scale: 0.92, opacity: 0, y: 15 }}
          animate={{ scale: 1, opacity: 1, y: 0 }}
          exit={{ scale: 0.94, opacity: 0, y: 10 }}
          transition={{ duration: 0.2, ease: "easeOut" }}
          className="glass-card"
          style={{
            width: "100%",
            maxWidth: 440,
            padding: 24,
            background: "rgba(17, 21, 32, 0.98)",
            border: "1px solid rgba(220, 38, 38, 0.4)",
            boxShadow: "0 0 50px rgba(220, 38, 38, 0.25), var(--shadow-modal)",
            position: "relative",
          }}
          onClick={(e) => e.stopPropagation()}
        >
          {/* Close button */}
          <button
            type="button"
            onClick={onCancel}
            className="btn-icon"
            style={{
              position: "absolute",
              top: 16,
              right: 16,
              width: 28,
              height: 28,
            }}
            title="Cancel and dismiss"
          >
            <X size={16} />
          </button>

          {/* Warning Icon Badge */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 12,
              marginBottom: 16,
            }}
          >
            <div
              style={{
                width: 44,
                height: 44,
                borderRadius: "var(--radius-md)",
                backgroundColor: "rgba(220, 38, 38, 0.15)",
                border: "1px solid rgba(220, 38, 38, 0.35)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "var(--color-state-error)",
                boxShadow: "0 0 16px rgba(220, 38, 38, 0.2)",
              }}
            >
              <ShieldAlert size={24} />
            </div>
            <div>
              <div
                style={{
                  fontFamily: "var(--font-mono)",
                  fontSize: 10,
                  color: "var(--color-state-confirm)",
                  letterSpacing: "0.1em",
                  textTransform: "uppercase",
                }}
              >
                PERMISSION AUTHORIZATION REQUIRED
              </div>
              <h2
                id="perm-modal-title"
                style={{
                  fontFamily: "var(--font-heading)",
                  fontSize: 18,
                  fontWeight: 600,
                  color: "var(--color-text-primary)",
                  margin: 0,
                }}
              >
                {title || "Confirm Action"}
              </h2>
            </div>
          </div>

          {/* Description */}
          <p
            style={{
              fontSize: 13,
              color: "var(--color-text-secondary)",
              lineHeight: 1.5,
              marginBottom: 16,
            }}
          >
            {description}
          </p>

          {/* Technical Target Box */}
          {detail && (
            <div
              style={{
                background: "rgba(3, 4, 9, 0.65)",
                border: "var(--border-subtle)",
                borderRadius: "var(--radius-md)",
                padding: "10px 12px",
                marginBottom: 20,
                display: "flex",
                alignItems: "flex-start",
                gap: 8,
              }}
            >
              <AlertTriangle
                size={15}
                color="var(--color-state-confirm)"
                style={{ flexShrink: 0, marginTop: 2 }}
              />
              <div style={{ overflow: "hidden" }}>
                <div
                  style={{
                    fontSize: 10,
                    color: "var(--color-text-tertiary)",
                    textTransform: "uppercase",
                    marginBottom: 2,
                  }}
                >
                  Command Target:
                </div>
                <code
                  style={{
                    fontSize: 12,
                    fontFamily: "var(--font-mono)",
                    color: "var(--color-nova-cyan)",
                    wordBreak: "break-all",
                    display: "block",
                  }}
                >
                  {detail}
                </code>
              </div>
            </div>
          )}

          {/* Modal Buttons */}
          <div style={{ display: "flex", justifyContent: "flex-end", gap: 10 }}>
            <button
              type="button"
              onClick={onCancel}
              className="btn btn-secondary"
              style={{ minWidth: 100 }}
              autoFocus
            >
              Decline
            </button>
            <button
              type="button"
              onClick={onConfirm}
              className="btn btn-danger"
              style={{ minWidth: 120 }}
            >
              Authorize Action
            </button>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
}
