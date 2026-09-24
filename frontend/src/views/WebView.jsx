import { useState } from "react";
import {
  Globe,
  Search,
  ExternalLink,
  Sparkles,
  BookOpen,
  Clock,
} from "lucide-react";
import { useNova } from "../context/useNova";
import { NOVA_STATES } from "../context/constants";

const INITIAL_SOURCES = [
  {
    title: "Neural Core Orchestration Architectures for Desktop Agents",
    domain: "arxiv.org",
    time: "2h ago",
    relevance: "98%",
  },
  {
    title: "Windows Subsystem API & Accessible Automation Guidelines",
    domain: "learn.microsoft.com",
    time: "1d ago",
    relevance: "95%",
  },
  {
    title: "High Frame-rate Glassmorphic UI in Modern Web Renderers",
    domain: "web.dev",
    time: "3d ago",
    relevance: "91%",
  },
];

export default function WebView() {
  const { setStatus, setStatusDetail, addActivity } = useNova();
  const [query, setQuery] = useState(
    "Next-generation multimodal desktop assistant design",
  );
  const [isSearching, setIsSearching] = useState(false);
  const [sources] = useState(INITIAL_SOURCES);

  const handleSearch = (e) => {
    e.preventDefault();
    if (!query.trim()) return;

    setIsSearching(true);
    setStatus(NOVA_STATES.PROCESSING);
    setStatusDetail(`QUERYING WEB INTELLIGENCE FOR: "${query.toUpperCase()}"`);

    setTimeout(() => {
      setStatus(NOVA_STATES.THINKING);
      setStatusDetail("SYNTHESIZING VERIFIED SOURCES...");

      setTimeout(() => {
        setIsSearching(false);
        setStatus(NOVA_STATES.SUCCESS);
        setStatusDetail("WEB INTELLIGENCE COMPILED");
        addActivity({ action: "Web Search", detail: query, type: "web" });

        setTimeout(() => {
          setStatus(NOVA_STATES.IDLE);
          setStatusDetail("");
        }, 2000);
      }, 1500);
    }, 1200);
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
          <Globe size={20} color="var(--color-nova-secondary)" />
          <h1
            style={{
              fontFamily: "var(--font-heading)",
              fontSize: 22,
              fontWeight: 600,
              color: "var(--color-text-primary)",
            }}
          >
            Web Intelligence
          </h1>
        </div>
        <p style={{ fontSize: 13, color: "var(--color-text-secondary)" }}>
          Autonomous web research, live citation retrieval, and synthesis
          without generic search clutter.
        </p>
      </div>

      {/* Query Bar */}
      <form onSubmit={handleSearch} style={{ display: "flex", gap: 10 }}>
        <div
          className="glass-panel"
          style={{
            flex: 1,
            display: "flex",
            alignItems: "center",
            gap: 10,
            padding: "0 16px",
            height: 44,
            borderRadius: "var(--radius-md)",
            border: "var(--border-default)",
          }}
        >
          <Search size={18} color="var(--color-text-tertiary)" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Ask NOVA to research any topic or find live documentation..."
            style={{
              flex: 1,
              background: "transparent",
              border: "none",
              outline: "none",
              color: "var(--color-text-primary)",
              fontSize: 14,
              fontFamily: "var(--font-body)",
            }}
          />
        </div>
        <button
          type="submit"
          disabled={isSearching}
          className="btn btn-primary"
          style={{ minWidth: 120 }}
        >
          {isSearching ? "Researching..." : "Research"}
        </button>
      </form>

      {/* Synthesized Answer Card */}
      <div
        className="glass-card"
        style={{
          padding: 22,
          border: "1px solid rgba(123, 92, 240, 0.35)",
          background: "rgba(19, 24, 38, 0.75)",
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
            marginBottom: 12,
          }}
        >
          <Sparkles size={16} color="var(--color-nova-cyan)" />
          <span
            style={{
              fontFamily: "var(--font-heading)",
              fontSize: 15,
              fontWeight: 600,
            }}
          >
            Synthesized Intelligence Summary
          </span>
          <span
            className="badge"
            style={{
              background: "rgba(16, 185, 129, 0.12)",
              color: "var(--color-state-success)",
              border: "1px solid rgba(16, 185, 129, 0.3)",
              marginLeft: "auto",
            }}
          >
            3 VERIFIED CITATIONS
          </span>
        </div>

        <p
          style={{
            fontSize: 14,
            color: "var(--color-text-primary)",
            lineHeight: 1.6,
            marginBottom: 16,
          }}
        >
          Next-generation personal AI assistants prioritize an unobtrusive,
          ambient presence with dedicated multimodal sensory channels (voice
          input, screen context, background listener). By utilizing
          high-velocity model routing between ultra-fast local engines and
          complex cloud reasoning backbones, NOVA achieves sub-100ms
          conversational loops while preserving user privacy and system
          security.
        </p>

        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <span
            className="badge"
            style={{
              background: "rgba(255, 255, 255, 0.05)",
              color: "var(--color-text-secondary)",
            }}
          >
            #MultimodalPerception
          </span>
          <span
            className="badge"
            style={{
              background: "rgba(255, 255, 255, 0.05)",
              color: "var(--color-text-secondary)",
            }}
          >
            #LowLatencyVoice
          </span>
          <span
            className="badge"
            style={{
              background: "rgba(255, 255, 255, 0.05)",
              color: "var(--color-text-secondary)",
            }}
          >
            #WindowsSubsystem
          </span>
        </div>
      </div>

      {/* Sources Grid */}
      <div>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 6,
            marginBottom: 12,
          }}
        >
          <BookOpen size={16} color="var(--color-text-secondary)" />
          <span
            style={{
              fontSize: 13,
              fontWeight: 600,
              color: "var(--color-text-secondary)",
              textTransform: "uppercase",
              letterSpacing: "0.04em",
            }}
          >
            Retrieved Primary Sources
          </span>
        </div>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
            gap: 12,
          }}
        >
          {sources.map((src, i) => (
            <div
              key={i}
              className="glass-card"
              style={{
                padding: 14,
                display: "flex",
                flexDirection: "column",
                justifyContent: "space-between",
                gap: 10,
              }}
            >
              <div>
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    marginBottom: 6,
                  }}
                >
                  <span
                    style={{
                      fontSize: 11,
                      fontFamily: "var(--font-mono)",
                      color: "var(--color-nova-cyan)",
                    }}
                  >
                    {src.domain}
                  </span>
                  <span
                    style={{
                      fontSize: 11,
                      color: "var(--color-state-success)",
                      fontFamily: "var(--font-mono)",
                    }}
                  >
                    {src.relevance} match
                  </span>
                </div>
                <div
                  style={{
                    fontSize: 13,
                    fontWeight: 500,
                    color: "var(--color-text-primary)",
                    lineHeight: 1.35,
                  }}
                >
                  {src.title}
                </div>
              </div>

              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  paddingTop: 8,
                  borderTop: "var(--border-subtle)",
                }}
              >
                <span
                  style={{
                    fontSize: 11,
                    color: "var(--color-text-tertiary)",
                    display: "flex",
                    alignItems: "center",
                    gap: 4,
                  }}
                >
                  <Clock size={12} /> {src.time}
                </span>
                <span
                  style={{
                    color: "var(--color-text-secondary)",
                    cursor: "pointer",
                    display: "flex",
                    alignItems: "center",
                    gap: 4,
                    fontSize: 11,
                  }}
                >
                  Inspect <ExternalLink size={12} />
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
