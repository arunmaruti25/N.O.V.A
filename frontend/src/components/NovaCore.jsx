import { useMemo } from "react";
import { motion } from "framer-motion";
import { useNova } from "../context/useNova";
import { NOVA_STATES } from "../context/constants";

export default function NovaCore({ size = 240, isMini = false, onClick }) {
  const {
    status,
    statusDetail,
    waveformBars,
    reducedMotion,
    triggerVoiceCommand,
    cancelOperation,
  } = useNova();

  // State-specific visual styling parameters
  const stateTheme = useMemo(() => {
    switch (status) {
      case NOVA_STATES.LISTENING:
        return {
          glow: "var(--glow-listening)",
          primaryColor: "#2563eb",
          secondaryColor: "#38bdf8",
          ringColor: "rgba(56, 189, 248, 0.55)",
          speedMultiplier: 2.0,
          label: "LISTENING...",
          pulseDuration: 1.6,
          particleCount: 5,
        };
      case NOVA_STATES.PROCESSING:
        return {
          glow: "var(--glow-processing)",
          primaryColor: "#8b5cf6",
          secondaryColor: "#a78bfa",
          ringColor: "rgba(167, 139, 250, 0.6)",
          speedMultiplier: 2.4,
          label: "PROCESSING...",
          pulseDuration: 1.8,
          particleCount: 4,
        };
      case NOVA_STATES.THINKING:
        return {
          glow: "var(--glow-thinking)",
          primaryColor: "#7c3aed",
          secondaryColor: "#c084fc",
          ringColor: "rgba(192, 132, 252, 0.5)",
          speedMultiplier: 0.7,
          label: "THINKING...",
          pulseDuration: 4.0,
          particleCount: 6,
        };
      case NOVA_STATES.EXECUTING:
        return {
          glow: "var(--glow-executing)",
          primaryColor: "#0891b2",
          secondaryColor: "#22d3ee",
          ringColor: "rgba(34, 211, 238, 0.75)",
          speedMultiplier: 3.2,
          label: "EXECUTING...",
          pulseDuration: 1.1,
          particleCount: 6,
        };
      case NOVA_STATES.SPEAKING:
        return {
          glow: "var(--glow-speaking)",
          primaryColor: "#4f46e5",
          secondaryColor: "#818cf8",
          ringColor: "rgba(129, 140, 248, 0.55)",
          speedMultiplier: 1.4,
          label: "SPEAKING...",
          pulseDuration: 2.0,
          particleCount: 4,
        };
      case NOVA_STATES.CONFIRMATION:
        return {
          glow: "var(--glow-confirm)",
          primaryColor: "#d97706",
          secondaryColor: "#fbbf24",
          ringColor: "rgba(251, 191, 36, 0.65)",
          speedMultiplier: 0.45,
          label: "CONFIRM REQUIRED",
          pulseDuration: 1.5,
          particleCount: 3,
        };
      case NOVA_STATES.SUCCESS:
        return {
          glow: "var(--glow-success)",
          primaryColor: "#059669",
          secondaryColor: "#34d399",
          ringColor: "rgba(52, 211, 153, 0.6)",
          speedMultiplier: 1.1,
          label: "SUCCESS",
          pulseDuration: 2.8,
          particleCount: 4,
        };
      case NOVA_STATES.ERROR:
        return {
          glow: "var(--glow-error)",
          primaryColor: "#dc2626",
          secondaryColor: "#f87171",
          ringColor: "rgba(248, 113, 113, 0.6)",
          speedMultiplier: 0.35,
          label: "ERROR DETECTED",
          pulseDuration: 3.2,
          particleCount: 2,
        };
      case NOVA_STATES.OFFLINE:
        return {
          glow: "var(--glow-offline)",
          primaryColor: "#475569",
          secondaryColor: "#64748b",
          ringColor: "rgba(100, 116, 139, 0.25)",
          speedMultiplier: 0.1,
          label: "OFFLINE",
          pulseDuration: 6.5,
          particleCount: 0,
        };
      case NOVA_STATES.IDLE:
      default:
        return {
          glow: "var(--glow-idle)",
          primaryColor: "#7b5cf0",
          secondaryColor: "#93c5fd",
          ringColor: "rgba(123, 92, 240, 0.4)",
          speedMultiplier: 1.0,
          label: "READY",
          pulseDuration: 3.8,
          particleCount: 4,
        };
    }
  }, [status]);

  const handleClick = () => {
    if (onClick) {
      onClick();
      return;
    }
    if (status === NOVA_STATES.IDLE) {
      triggerVoiceCommand("NOVA, open Chrome");
    } else if (
      status === NOVA_STATES.LISTENING ||
      status === NOVA_STATES.THINKING ||
      status === NOVA_STATES.EXECUTING ||
      status === NOVA_STATES.SPEAKING
    ) {
      cancelOperation();
    }
  };

  // Animation values based on reduced motion
  const pulseScale = reducedMotion ? [1, 1] : [1, isMini ? 1.03 : 1.045, 1];
  const errorShake =
    reducedMotion || status !== NOVA_STATES.ERROR
      ? [0, 0]
      : [0, -6, 6, -4, 4, -2, 0];

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        position: "relative",
        cursor: "pointer",
      }}
      onClick={handleClick}
      role="button"
      tabIndex={0}
      aria-label={`NOVA Core, currently ${status}`}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          handleClick();
        }
      }}
    >
      {/* Container sizing */}
      <div
        style={{
          width: size,
          height: size,
          position: "relative",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        {/* Layer 1: Ambient Outer Atmosphere Bloom (Desktop only) */}
        {!isMini && !reducedMotion && (
          <motion.div
            animate={{
              scale: [1, 1.1, 1],
              opacity:
                status === NOVA_STATES.OFFLINE ? 0.04 : [0.35, 0.6, 0.35],
            }}
            transition={{
              duration: stateTheme.pulseDuration,
              repeat: Infinity,
              ease: "easeInOut",
            }}
            style={{
              position: "absolute",
              width: size * 1.65,
              height: size * 1.65,
              borderRadius: "50%",
              background: `radial-gradient(circle, ${stateTheme.primaryColor}28 0%, ${stateTheme.secondaryColor}10 45%, transparent 70%)`,
              pointerEvents: "none",
              filter: "blur(36px)",
              zIndex: 0,
            }}
          />
        )}

        {/* Acoustic Wave Ripple (Active only in LISTENING state) */}
        {!isMini && !reducedMotion && status === NOVA_STATES.LISTENING && (
          <motion.div
            initial={{ scale: 0.88, opacity: 0.8 }}
            animate={{ scale: 1.45, opacity: 0 }}
            transition={{ duration: 1.4, repeat: Infinity, ease: "easeOut" }}
            style={{
              position: "absolute",
              width: size * 0.9,
              height: size * 0.9,
              borderRadius: "50%",
              border: `1.5px solid ${stateTheme.secondaryColor}`,
              pointerEvents: "none",
              zIndex: 1,
            }}
          />
        )}

        {/* Layer 2: Outer Orbital Ring 1 (Tilted ellipse with rotating energy nodes) */}
        {!reducedMotion && (
          <motion.div
            animate={{
              rotate: 360,
            }}
            transition={{
              duration: 18 / stateTheme.speedMultiplier,
              repeat: Infinity,
              ease: "linear",
            }}
            style={{
              position: "absolute",
              width: size * 1.2,
              height: size * 1.2,
              borderRadius: "50%",
              borderWidth: 1,
              borderStyle: "solid",
              borderTopColor: "transparent",
              borderBottomColor: "transparent",
              borderLeftColor: stateTheme.ringColor,
              borderRightColor: stateTheme.ringColor,
              pointerEvents: "none",
              zIndex: 1,
            }}
          >
            {/* Energy Particle Node 1 on Ring */}
            {!isMini && (
              <div
                style={{
                  position: "absolute",
                  top: "12%",
                  left: "12%",
                  width: 5,
                  height: 5,
                  borderRadius: "50%",
                  backgroundColor: stateTheme.secondaryColor,
                  boxShadow: `0 0 10px ${stateTheme.secondaryColor}`,
                }}
              />
            )}
            {/* Energy Particle Node 2 on Ring */}
            {!isMini && (
              <div
                style={{
                  position: "absolute",
                  bottom: "12%",
                  right: "12%",
                  width: 4,
                  height: 4,
                  borderRadius: "50%",
                  backgroundColor: stateTheme.primaryColor,
                  boxShadow: `0 0 8px ${stateTheme.primaryColor}`,
                }}
              />
            )}
          </motion.div>
        )}

        {/* Layer 3: Outer Orbital Ring 2 (Counter-rotating tilted ellipse) */}
        {!reducedMotion && !isMini && (
          <motion.div
            animate={{
              rotate: -360,
            }}
            transition={{
              duration: 26 / stateTheme.speedMultiplier,
              repeat: Infinity,
              ease: "linear",
            }}
            style={{
              position: "absolute",
              width: size * 1.34,
              height: size * 1.15,
              borderRadius: "50%",
              borderWidth: 1,
              borderStyle: "dashed",
              borderLeftColor: "transparent",
              borderTopColor: stateTheme.ringColor,
              borderRightColor: stateTheme.ringColor,
              borderBottomColor: stateTheme.ringColor,
              pointerEvents: "none",
              zIndex: 1,
            }}
          >
            {/* Energy Particle Node 3 */}
            <div
              style={{
                position: "absolute",
                top: "50%",
                right: -2,
                transform: "translateY(-50%)",
                width: 5,
                height: 5,
                borderRadius: "50%",
                backgroundColor: "#ffffff",
                boxShadow: `0 0 12px ${stateTheme.secondaryColor}`,
              }}
            />
          </motion.div>
        )}

        {/* Layer 4: Core Sphere Body */}
        <motion.div
          animate={{
            scale: pulseScale,
            x: errorShake,
            boxShadow: stateTheme.glow,
          }}
          transition={{
            scale: {
              duration: stateTheme.pulseDuration,
              repeat: Infinity,
              ease: "easeInOut",
            },
            x: {
              duration: 0.45,
              ease: "easeInOut",
            },
            boxShadow: {
              duration: 0.55,
              ease: "easeInOut",
            },
          }}
          whileHover={{
            scale: 1.05,
            transition: { duration: 0.2 },
          }}
          style={{
            width: size * 0.88,
            height: size * 0.88,
            borderRadius: "50%",
            position: "relative",
            zIndex: 2,
            background: `radial-gradient(circle at 35% 28%, ${stateTheme.secondaryColor}dd 0%, ${stateTheme.primaryColor}f0 52%, #080a14 100%)`,
            border: `1px solid rgba(255, 255, 255, ${status === NOVA_STATES.OFFLINE ? 0.06 : 0.25})`,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            overflow: "hidden",
          }}
        >
          {/* Inner Light Shimmer Reflection Beam */}
          {!reducedMotion && status !== NOVA_STATES.OFFLINE && (
            <motion.div
              animate={{
                x: ["-140%", "140%"],
                opacity: [0, 0.45, 0],
              }}
              transition={{
                duration: 4.2 / stateTheme.speedMultiplier,
                repeat: Infinity,
                ease: "easeInOut",
              }}
              style={{
                position: "absolute",
                width: "65%",
                height: "150%",
                background:
                  "linear-gradient(90deg, transparent 0%, rgba(255,255,255,0.45) 50%, transparent 100%)",
                transform: "rotate(28deg)",
                pointerEvents: "none",
                zIndex: 3,
              }}
            />
          )}

          {/* Embedded Audio Waveform (LISTENING & SPEAKING) */}
          {(status === NOVA_STATES.LISTENING ||
            status === NOVA_STATES.SPEAKING) && (
            <div
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: isMini ? 3 : 6,
                zIndex: 4,
              }}
            >
              {waveformBars.map((bar, i) => (
                <motion.div
                  key={i}
                  animate={{
                    height: reducedMotion
                      ? 12
                      : Math.max(isMini ? 4 : 8, bar * (isMini ? 24 : 54)),
                  }}
                  transition={{
                    duration: 0.09,
                    ease: "easeOut",
                  }}
                  style={{
                    width: isMini ? 2 : 4,
                    backgroundColor: "#ffffff",
                    borderRadius: 3,
                    boxShadow: "0 0 10px rgba(255, 255, 255, 0.9)",
                  }}
                />
              ))}
            </div>
          )}

          {/* Active Process Indicator (Rotating Arc for Processing & Executing) */}
          {(status === NOVA_STATES.PROCESSING ||
            status === NOVA_STATES.EXECUTING) && (
            <motion.div
              animate={{ rotate: 360 }}
              transition={{
                duration: status === NOVA_STATES.EXECUTING ? 1.0 : 2.2,
                repeat: Infinity,
                ease: "linear",
              }}
              style={{
                position: "absolute",
                width: "76%",
                height: "76%",
                borderRadius: "50%",
                borderWidth: 2,
                borderStyle: "solid",
                borderTopColor: "#ffffff",
                borderRightColor: stateTheme.secondaryColor,
                borderBottomColor: "transparent",
                borderLeftColor: "transparent",
                zIndex: 4,
              }}
            />
          )}

          {/* Meditative Hexagonal Constellation Nodes for THINKING */}
          {status === NOVA_STATES.THINKING && !reducedMotion && (
            <motion.div
              animate={{ rotate: -360 }}
              transition={{ duration: 7, repeat: Infinity, ease: "linear" }}
              style={{
                position: "absolute",
                width: "72%",
                height: "72%",
                borderRadius: "50%",
                borderWidth: 1,
                borderStyle: "dashed",
                borderTopColor: "rgba(255, 255, 255, 0.45)",
                borderRightColor: "rgba(255, 255, 255, 0.45)",
                borderBottomColor: "rgba(255, 255, 255, 0.45)",
                borderLeftColor: "rgba(255, 255, 255, 0.45)",
                zIndex: 4,
              }}
            >
              <div
                style={{
                  position: "absolute",
                  top: 0,
                  left: "50%",
                  transform: "translateX(-50%)",
                  width: 4,
                  height: 4,
                  borderRadius: "50%",
                  backgroundColor: "#ffffff",
                  boxShadow: "0 0 8px #ffffff",
                }}
              />
              <div
                style={{
                  position: "absolute",
                  bottom: 0,
                  left: "50%",
                  transform: "translateX(-50%)",
                  width: 4,
                  height: 4,
                  borderRadius: "50%",
                  backgroundColor: "#ffffff",
                  boxShadow: "0 0 8px #ffffff",
                }}
              />
            </motion.div>
          )}
        </motion.div>
      </div>

      {/* State Status Typography Badge (Only when not in mini mode) */}
      {!isMini && (
        <div
          style={{
            marginTop: 18,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: 5,
            zIndex: 2,
          }}
        >
          <div
            className="glass-panel"
            style={{
              padding: "5px 14px",
              borderRadius: "var(--radius-full)",
              display: "flex",
              alignItems: "center",
              gap: 8,
              border: `1px solid ${stateTheme.ringColor}`,
              boxShadow: "0 2px 10px rgba(0, 0, 0, 0.3)",
            }}
          >
            <span
              style={{
                width: 7,
                height: 7,
                borderRadius: "50%",
                backgroundColor: stateTheme.primaryColor,
                boxShadow: `0 0 10px ${stateTheme.primaryColor}`,
                display: "inline-block",
              }}
            />
            <span
              style={{
                fontFamily: "var(--font-heading)",
                fontSize: 12,
                fontWeight: 600,
                letterSpacing: "0.12em",
                color: stateTheme.secondaryColor,
                textTransform: "uppercase",
              }}
            >
              {stateTheme.label}
            </span>
          </div>

          {statusDetail && (
            <motion.div
              initial={{ opacity: 0, y: -4 }}
              animate={{ opacity: 1, y: 0 }}
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: 11,
                color: "var(--color-text-secondary)",
                letterSpacing: "0.04em",
                maxWidth: 460,
                textAlign: "center",
              }}
            >
              {statusDetail}
            </motion.div>
          )}
        </div>
      )}
    </div>
  );
}
