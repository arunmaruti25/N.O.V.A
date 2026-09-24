import { useState } from "react";
import {
  Monitor,
  Volume2,
  Power,
  RotateCcw,
  Lock,
  ExternalLink,
  Sliders,
} from "lucide-react";
import { useNova } from "../context/useNova";
import { NOVA_STATES } from "../context/constants";

export default function ComputerView() {
  const {
    setStatus,
    setStatusDetail,
    requestPermission,
    addActivity,
    addNotification,
  } = useNova();
  const [volume, setVolume] = useState(40);

  const handleLaunchApp = (appName) => {
    setStatus(NOVA_STATES.EXECUTING);
    setStatusDetail(`SPAWNING PROCESS: ${appName.toUpperCase()}...`);

    setTimeout(() => {
      setStatus(NOVA_STATES.SUCCESS);
      setStatusDetail(`${appName} IS ACTIVE`);
      addActivity({
        action: "Application Launch",
        detail: `Opened ${appName}`,
        type: "computer",
      });
      addNotification({
        type: "success",
        title: "Process Launched",
        message: `${appName} opened successfully.`,
      });

      setTimeout(() => {
        setStatus(NOVA_STATES.IDLE);
        setStatusDetail("");
      }, 1800);
    }, 1200);
  };

  const handleShutdown = () => {
    requestPermission({
      title: "Host Workstation Shutdown",
      description:
        "You are about to initiate an immediate system shutdown on this Windows computer.",
      severity: "danger",
      detail: "shutdown /s /t 0",
      onConfirm: () => {
        setStatus(NOVA_STATES.EXECUTING);
        setStatusDetail("EXECUTING SHUTDOWN PROTOCOL...");
        addActivity({
          action: "System Power",
          detail: "Shutdown initiated",
          type: "computer",
        });
      },
    });
  };

  const handleRestart = () => {
    requestPermission({
      title: "Host Workstation Reboot",
      description:
        "NOVA requested permission to perform a clean system reboot.",
      severity: "warning",
      detail: "shutdown /r /t 0",
      onConfirm: () => {
        setStatus(NOVA_STATES.EXECUTING);
        setStatusDetail("INITIATING REBOOT SEQUENCE...");
        addActivity({
          action: "System Power",
          detail: "Reboot initiated",
          type: "computer",
        });
      },
    });
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
          <Monitor size={20} color="#34d399" />
          <h1
            style={{
              fontFamily: "var(--font-heading)",
              fontSize: 22,
              fontWeight: 600,
              color: "var(--color-text-primary)",
            }}
          >
            Computer & Windows Control
          </h1>
        </div>
        <p style={{ fontSize: 13, color: "var(--color-text-secondary)" }}>
          Direct system orchestration: application management, audio sessions,
          display state, and secure power options.
        </p>
      </div>

      {/* Control Grid */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))",
          gap: 16,
        }}
      >
        {/* Hardware & Audio Sliders */}
        <div className="glass-card" style={{ padding: 20 }}>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              marginBottom: 16,
            }}
          >
            <Volume2 size={18} color="var(--color-nova-cyan)" />
            <span
              style={{
                fontFamily: "var(--font-heading)",
                fontSize: 15,
                fontWeight: 600,
              }}
            >
              Master Audio Session
            </span>
            <span
              style={{
                marginLeft: "auto",
                fontFamily: "var(--font-mono)",
                fontSize: 13,
                color: "var(--color-nova-cyan)",
              }}
            >
              {volume}%
            </span>
          </div>

          <input
            type="range"
            min="0"
            max="100"
            value={volume}
            onChange={(e) => {
              const val = Number(e.target.value);
              setVolume(val);
              setStatus(NOVA_STATES.EXECUTING);
              setStatusDetail(`ADJUSTING AUDIO GAIN: ${val}%`);
              setTimeout(() => {
                setStatus(NOVA_STATES.IDLE);
                setStatusDetail("");
              }, 600);
            }}
            style={{
              width: "100%",
              accentColor: "var(--color-nova-cyan)",
              cursor: "pointer",
              marginBottom: 12,
            }}
          />

          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              fontSize: 11,
              color: "var(--color-text-tertiary)",
            }}
          >
            <span>Mute (0%)</span>
            <span>Balanced (50%)</span>
            <span>Max (100%)</span>
          </div>
        </div>

        {/* Quick App Launchers */}
        <div className="glass-card" style={{ padding: 20 }}>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              marginBottom: 14,
            }}
          >
            <Sliders size={18} color="var(--color-nova-primary)" />
            <span
              style={{
                fontFamily: "var(--font-heading)",
                fontSize: 15,
                fontWeight: 600,
              }}
            >
              Quick App Launch
            </span>
          </div>

          <div
            style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}
          >
            {[
              { name: "Google Chrome", target: "Chrome" },
              { name: "VS Code", target: "VS Code" },
              { name: "Windows Terminal", target: "Terminal" },
              { name: "Task Manager", target: "TaskMgr" },
            ].map((app) => (
              <button
                key={app.target}
                type="button"
                onClick={() => handleLaunchApp(app.name)}
                className="btn btn-secondary"
                style={{
                  padding: "8px 12px",
                  justifyContent: "flex-start",
                  fontSize: 12,
                  gap: 6,
                }}
              >
                <ExternalLink size={13} color="var(--color-nova-cyan)" />
                <span
                  style={{
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                  }}
                >
                  {app.name}
                </span>
              </button>
            ))}
          </div>
        </div>

        {/* Protected Power Actions */}
        <div
          className="glass-card"
          style={{ padding: 20, border: "1px solid rgba(220, 38, 38, 0.25)" }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              marginBottom: 14,
            }}
          >
            <Power size={18} color="var(--color-state-error)" />
            <span
              style={{
                fontFamily: "var(--font-heading)",
                fontSize: 15,
                fontWeight: 600,
              }}
            >
              System Power Protocols
            </span>
          </div>

          <p
            style={{
              fontSize: 12,
              color: "var(--color-text-secondary)",
              marginBottom: 14,
            }}
          >
            Potentially destructive operations require biometric or explicit
            modal authorization before execution.
          </p>

          <div style={{ display: "flex", gap: 10 }}>
            <button
              type="button"
              onClick={handleShutdown}
              className="btn btn-danger"
              style={{ flex: 1, gap: 6, fontSize: 12 }}
            >
              <Power size={14} /> Shut Down
            </button>
            <button
              type="button"
              onClick={handleRestart}
              className="btn btn-secondary"
              style={{
                flex: 1,
                gap: 6,
                fontSize: 12,
                borderColor: "rgba(217, 119, 6, 0.4)",
              }}
            >
              <RotateCcw size={14} color="var(--color-state-confirm)" /> Reboot
            </button>
            <button
              type="button"
              onClick={() => {
                addNotification({
                  type: "info",
                  title: "Workstation Locked",
                  message: "User session secured.",
                });
              }}
              className="btn btn-secondary"
              style={{ padding: "0 12px" }}
              title="Lock Screen"
            >
              <Lock size={14} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
