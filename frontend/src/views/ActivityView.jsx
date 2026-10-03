import {
  Activity,
  CheckCircle2,
  Clock,
  Eye,
  Globe,
  Monitor,
  Cpu,
} from "lucide-react";
import { useNova } from "../context/useNova";

export default function ActivityView() {
  const { activities } = useNova();

  const getIcon = (type) => {
    switch (type) {
      case "vision":
        return <Eye size={16} color="var(--color-nova-cyan)" />;
      case "web":
        return <Globe size={16} color="var(--color-nova-secondary)" />;
      case "computer":
        return <Monitor size={16} color="#34d399" />;
      case "skills":
        return <Cpu size={16} color="var(--color-text-accent)" />;
      default:
        return <Activity size={16} color="var(--color-nova-primary)" />;
    }
  };

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
          <Activity size={20} color="var(--color-nova-cyan)" />
          <h1
            style={{
              fontFamily: "var(--font-heading)",
              fontSize: 22,
              fontWeight: 600,
              color: "var(--color-text-primary)",
            }}
          >
            System Activity Log
          </h1>
        </div>
        <p style={{ fontSize: 13, color: "var(--color-text-secondary)" }}>
          Audit trail of perception, tool invocations, and autonomous actions
          executed by NOVA.
        </p>
      </div>

      {/* Activity Timeline List */}
      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        {activities.map((act) => (
          <div
            key={act.id}
            className="glass-card"
            style={{
              padding: "14px 18px",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              gap: 16,
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
              <div
                style={{
                  width: 36,
                  height: 36,
                  borderRadius: "var(--radius-md)",
                  background: "rgba(255, 255, 255, 0.04)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  border: "var(--border-subtle)",
                }}
              >
                {getIcon(act.type)}
              </div>

              <div>
                <div
                  style={{
                    fontSize: 14,
                    fontWeight: 600,
                    color: "var(--color-text-primary)",
                  }}
                >
                  {act.action}
                </div>
                <div
                  style={{
                    fontSize: 12,
                    color: "var(--color-text-secondary)",
                    marginTop: 2,
                  }}
                >
                  {act.detail}
                </div>
              </div>
            </div>

            <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
              <span
                className="badge"
                style={{
                  background: act.verified
                    ? "rgba(6, 182, 212, 0.16)"
                    : act.result === "failed"
                    ? "rgba(239, 68, 68, 0.16)"
                    : "rgba(16, 185, 129, 0.12)",
                  color: act.verified
                    ? "var(--color-nova-cyan)"
                    : act.result === "failed"
                    ? "var(--color-state-error)"
                    : "var(--color-state-success)",
                  border: act.verified
                    ? "1px solid rgba(6, 182, 212, 0.4)"
                    : act.result === "failed"
                    ? "1px solid rgba(239, 68, 68, 0.3)"
                    : "1px solid rgba(16, 185, 129, 0.3)",
                  gap: 4,
                }}
              >
                <CheckCircle2 size={12} /> {act.verified ? "Verified" : (act.result === "failed" ? "Failed" : "Success")}
              </span>
              <span
                style={{
                  fontSize: 12,
                  color: "var(--color-text-tertiary)",
                  display: "flex",
                  alignItems: "center",
                  gap: 4,
                }}
              >
                <Clock size={12} /> {act.time}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
