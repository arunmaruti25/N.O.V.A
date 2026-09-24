import { useState } from "react";
import { motion } from "framer-motion";
import {
  Eye,
  Camera,
  RefreshCw,
  Layers,
  CheckCircle,
  Sparkles,
} from "lucide-react";
import { useNova } from "../context/useNova";
import { NOVA_STATES } from "../context/constants";

export default function VisionView() {
  const { setStatus, setStatusDetail, addActivity } = useNova();
  const [isScanning, setIsScanning] = useState(false);
  const [lastScanTime, setLastScanTime] = useState("Just now");

  const handleCapture = () => {
    setIsScanning(true);
    setStatus(NOVA_STATES.THINKING);
    setStatusDetail("CAPTURING & PROCESSING DISPLAY BUFFER...");

    setTimeout(() => {
      setIsScanning(false);
      setStatus(NOVA_STATES.SPEAKING);
      setStatusDetail("MULTIMODAL PERCEPTION SYNTHESIZED");
      setLastScanTime("Just now");
      addActivity({
        action: "Screen Perception",
        detail: "Desktop viewport analyzed",
        type: "vision",
      });

      setTimeout(() => {
        setStatus(NOVA_STATES.IDLE);
        setStatusDetail("");
      }, 2500);
    }, 1800);
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
      {/* View Header */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <div>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              marginBottom: 4,
            }}
          >
            <Eye size={20} color="var(--color-nova-cyan)" />
            <h1
              style={{
                fontFamily: "var(--font-heading)",
                fontSize: 22,
                fontWeight: 600,
                color: "var(--color-text-primary)",
              }}
            >
              Vision & Screen Intelligence
            </h1>
          </div>
          <p style={{ fontSize: 13, color: "var(--color-text-secondary)" }}>
            Real-time visual comprehension of your active Windows display and
            application context.
          </p>
        </div>

        <button
          type="button"
          onClick={handleCapture}
          disabled={isScanning}
          className="btn btn-primary"
          style={{ gap: 8 }}
        >
          {isScanning ? (
            <>
              <RefreshCw size={16} className="animate-spin" />
              <span>Scanning...</span>
            </>
          ) : (
            <>
              <Camera size={16} />
              <span>Capture Screen</span>
            </>
          )}
        </button>
      </div>

      {/* Screen Preview & HUD Viewfinder */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1.4fr 1fr",
          gap: 20,
        }}
      >
        {/* Left: Viewfinder Display */}
        <div
          className="glass-panel"
          style={{
            borderRadius: "var(--radius-lg)",
            border: "var(--border-default)",
            overflow: "hidden",
            position: "relative",
            background: "#0a0d15",
            minHeight: 340,
            display: "flex",
            flexDirection: "column",
          }}
        >
          {/* Top Bar of Screen Window */}
          <div
            style={{
              padding: "8px 14px",
              borderBottom: "var(--border-subtle)",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              background: "rgba(255, 255, 255, 0.02)",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <span
                style={{
                  width: 8,
                  height: 8,
                  borderRadius: "50%",
                  background: "#ef4444",
                }}
              />
              <span
                style={{
                  width: 8,
                  height: 8,
                  borderRadius: "50%",
                  background: "#f59e0b",
                }}
              />
              <span
                style={{
                  width: 8,
                  height: 8,
                  borderRadius: "50%",
                  background: "#10b981",
                }}
              />
              <span
                style={{
                  fontSize: 11,
                  fontFamily: "var(--font-mono)",
                  color: "var(--color-text-secondary)",
                  marginLeft: 8,
                }}
              >
                DISPLAY 1 (1920×1080 @ 144Hz)
              </span>
            </div>
            <span
              style={{
                fontSize: 10,
                fontFamily: "var(--font-mono)",
                color: "var(--color-nova-cyan)",
              }}
            >
              ACTIVE HUD
            </span>
          </div>

          {/* Viewfinder Content Mockup */}
          <div
            style={{
              flex: 1,
              position: "relative",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              padding: 20,
              background:
                "radial-gradient(circle at center, #111728 0%, #080a11 100%)",
            }}
          >
            {/* Animated Laser Scanning Line */}
            {isScanning && (
              <motion.div
                initial={{ top: "0%" }}
                animate={{ top: "100%" }}
                transition={{ duration: 1.6, repeat: Infinity, ease: "linear" }}
                style={{
                  position: "absolute",
                  left: 0,
                  right: 0,
                  height: 2,
                  background:
                    "linear-gradient(90deg, transparent 0%, var(--color-nova-cyan) 50%, transparent 100%)",
                  boxShadow: "0 0 15px var(--color-nova-cyan)",
                  zIndex: 10,
                }}
              />
            )}

            {/* Simulated Desktop Application Regions */}
            <div
              style={{
                width: "100%",
                height: 240,
                display: "grid",
                gridTemplateColumns: "1fr 1fr",
                gap: 12,
              }}
            >
              {/* Region 1: VS Code */}
              <div
                style={{
                  border: "1px dashed rgba(34, 211, 238, 0.4)",
                  borderRadius: "var(--radius-md)",
                  background: "rgba(34, 211, 238, 0.04)",
                  padding: 12,
                  position: "relative",
                }}
              >
                <div
                  className="badge"
                  style={{
                    position: "absolute",
                    top: -10,
                    left: 10,
                    background: "var(--color-bg-base)",
                    border: "1px solid rgba(34, 211, 238, 0.6)",
                    color: "var(--color-nova-cyan)",
                    fontSize: 10,
                  }}
                >
                  REGION: CODE_EDITOR (ACTIVE)
                </div>
                <div
                  style={{
                    fontSize: 11,
                    fontFamily: "var(--font-mono)",
                    color: "var(--color-text-secondary)",
                    marginTop: 8,
                  }}
                >
                  File: D:\N.O.V.A\frontend\src\App.jsx
                  <br />
                  State: React 19.2 + Framer Motion
                </div>
              </div>

              {/* Region 2: Terminal / Browser */}
              <div
                style={{
                  border: "1px dashed rgba(123, 92, 240, 0.4)",
                  borderRadius: "var(--radius-md)",
                  background: "rgba(123, 92, 240, 0.04)",
                  padding: 12,
                  position: "relative",
                }}
              >
                <div
                  className="badge"
                  style={{
                    position: "absolute",
                    top: -10,
                    left: 10,
                    background: "var(--color-bg-base)",
                    border: "1px solid rgba(123, 92, 240, 0.6)",
                    color: "var(--color-nova-primary)",
                    fontSize: 10,
                  }}
                >
                  REGION: TERMINAL_EXEC
                </div>
                <div
                  style={{
                    fontSize: 11,
                    fontFamily: "var(--font-mono)",
                    color: "var(--color-text-secondary)",
                    marginTop: 8,
                  }}
                >
                  Status: Vite Dev Server running
                  <br />
                  Port: 5173 / Localhost
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Right: Vision Insights & Semantic Extraction */}
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <div className="glass-card" style={{ padding: 18 }}>
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                marginBottom: 10,
              }}
            >
              <Sparkles size={16} color="var(--color-nova-cyan)" />
              <div
                style={{
                  fontFamily: "var(--font-heading)",
                  fontSize: 14,
                  fontWeight: 600,
                }}
              >
                Multimodal Analysis
              </div>
            </div>

            <p
              style={{
                fontSize: 13,
                color: "var(--color-text-secondary)",
                lineHeight: 1.5,
                marginBottom: 12,
              }}
            >
              Active window is Visual Studio Code editing the NOVA UI frontend.
              No errors or blocking warnings are visible on screen.
            </p>

            <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  fontSize: 12,
                  color: "var(--color-text-primary)",
                }}
              >
                <CheckCircle size={14} color="var(--color-state-success)" />
                <span>React JSX layout with Framer Motion detected</span>
              </div>
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  fontSize: 12,
                  color: "var(--color-text-primary)",
                }}
              >
                <CheckCircle size={14} color="var(--color-state-success)" />
                <span>Vite compiler running without syntax issues</span>
              </div>
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  fontSize: 12,
                  color: "var(--color-text-primary)",
                }}
              >
                <Layers size={14} color="var(--color-nova-secondary)" />
                <span>OCR text confidence: 99.4%</span>
              </div>
            </div>
          </div>

          <div className="glass-card" style={{ padding: 16 }}>
            <div
              style={{
                fontSize: 11,
                fontFamily: "var(--font-mono)",
                color: "var(--color-text-tertiary)",
                textTransform: "uppercase",
                marginBottom: 4,
              }}
            >
              Metadata
            </div>
            <div style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>
              Last analyzed: {lastScanTime} · Model: Gemini 2.5 Pro Vision
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
