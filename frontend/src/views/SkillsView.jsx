import { useState } from "react";
import {
  Cpu,
  Search,
  Globe,
  FolderTree,
  Code2,
  Music,
  Terminal,
  Shield,
} from "lucide-react";
import { useNova } from "../context/useNova";

const SKILLS_DATA = [
  {
    id: "browser",
    name: "Browser Automation",
    category: "Automation",
    icon: Globe,
    color: "#3b82f6",
    desc: "Launch, navigate, fill forms, and scrape web pages via Chrome/Edge automation.",
    enabled: true,
    permissions: ["Network", "Browser Tabs"],
  },
  {
    id: "files",
    name: "File System Operations",
    category: "System",
    icon: FolderTree,
    color: "#f59e0b",
    desc: "Read, write, organize, and search files across local NTFS storage drives.",
    enabled: true,
    permissions: ["File Read/Write", "NTFS Full"],
  },
  {
    id: "coding",
    name: "Code Sandbox & REPL",
    category: "Developer",
    icon: Code2,
    color: "#8b5cf6",
    desc: "Execute Python, JavaScript, and shell commands in isolated runtimes.",
    enabled: true,
    permissions: ["Subprocess Spawn", "Local Socket"],
  },
  {
    id: "system",
    name: "Windows Hardware Control",
    category: "System",
    icon: Terminal,
    color: "#ef4444",
    desc: "Manage audio volume, screen brightness, processes, and power state.",
    enabled: true,
    permissions: ["Win32 API", "UAC Admin"],
  },
  {
    id: "media",
    name: "Media & Spotify Player",
    category: "Entertainment",
    icon: Music,
    color: "#ec4899",
    desc: "Control music playback, playlist queues, and media keys via audio session API.",
    enabled: false,
    permissions: ["Audio Session", "Media Keys"],
  },
];

export default function SkillsView() {
  const { addNotification } = useNova();
  const [skills, setSkills] = useState(SKILLS_DATA);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("All");

  const categories = [
    "All",
    "System",
    "Automation",
    "Developer",
    "Entertainment",
  ];

  const toggleSkill = (id) => {
    setSkills((prev) =>
      prev.map((s) => {
        if (s.id === id) {
          const nextState = !s.enabled;
          addNotification({
            type: nextState ? "success" : "info",
            title: `Skill ${nextState ? "Enabled" : "Disabled"}`,
            message: `${s.name} is now ${nextState ? "active and ready" : "deactivated"}.`,
          });
          return { ...s, enabled: nextState };
        }
        return s;
      }),
    );
  };

  const filtered = skills.filter((s) => {
    const matchesSearch =
      s.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      s.desc.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesCategory =
      selectedCategory === "All" || s.category === selectedCategory;
    return matchesSearch && matchesCategory;
  });

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
          <Cpu size={20} color="var(--color-nova-primary)" />
          <h1
            style={{
              fontFamily: "var(--font-heading)",
              fontSize: 22,
              fontWeight: 600,
              color: "var(--color-text-primary)",
            }}
          >
            Skills & Tool Hub
          </h1>
        </div>
        <p style={{ fontSize: 13, color: "var(--color-text-secondary)" }}>
          Modular capability plugins granting NOVA access to local system APIs,
          developer toolchains, and services.
        </p>
      </div>

      {/* Filter & Search Bar */}
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          gap: 12,
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <div
          className="glass-panel"
          style={{
            display: "flex",
            alignItems: "center",
            gap: 10,
            padding: "0 14px",
            height: 38,
            borderRadius: "var(--radius-md)",
            border: "var(--border-default)",
            minWidth: 260,
          }}
        >
          <Search size={16} color="var(--color-text-tertiary)" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search skills or permissions..."
            style={{
              flex: 1,
              background: "transparent",
              border: "none",
              outline: "none",
              color: "var(--color-text-primary)",
              fontSize: 13,
              fontFamily: "var(--font-body)",
            }}
          />
        </div>

        {/* Categories */}
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
          {categories.map((cat) => {
            const isSelected = selectedCategory === cat;
            return (
              <button
                key={cat}
                type="button"
                onClick={() => setSelectedCategory(cat)}
                className="badge"
                style={{
                  background: isSelected
                    ? "rgba(123, 92, 240, 0.2)"
                    : "rgba(255, 255, 255, 0.04)",
                  border: isSelected
                    ? "1px solid rgba(123, 92, 240, 0.5)"
                    : "var(--border-subtle)",
                  color: isSelected ? "#ffffff" : "var(--color-text-secondary)",
                  cursor: "pointer",
                  padding: "6px 12px",
                }}
              >
                {cat}
              </button>
            );
          })}
        </div>
      </div>

      {/* Skills Grid */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))",
          gap: 16,
        }}
      >
        {filtered.map((skill) => {
          const Icon = skill.icon;
          return (
            <div
              key={skill.id}
              className="glass-card"
              style={{
                padding: 18,
                display: "flex",
                flexDirection: "column",
                justifyContent: "space-between",
                gap: 14,
                opacity: skill.enabled ? 1 : 0.65,
                border: skill.enabled
                  ? "1px solid rgba(123, 92, 240, 0.25)"
                  : "var(--border-subtle)",
              }}
            >
              <div>
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    marginBottom: 12,
                  }}
                >
                  <div
                    style={{
                      width: 40,
                      height: 40,
                      borderRadius: "var(--radius-md)",
                      background: "rgba(255, 255, 255, 0.04)",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      border: "var(--border-subtle)",
                    }}
                  >
                    <Icon size={20} color={skill.color} />
                  </div>

                  {/* Enable / Disable Toggle Switch */}
                  <button
                    type="button"
                    onClick={() => toggleSkill(skill.id)}
                    style={{
                      width: 44,
                      height: 24,
                      borderRadius: 12,
                      background: skill.enabled
                        ? "var(--color-nova-primary)"
                        : "rgba(255, 255, 255, 0.15)",
                      border: "none",
                      cursor: "pointer",
                      position: "relative",
                      transition: "background 0.2s ease",
                      padding: 2,
                    }}
                    title={
                      skill.enabled ? "Click to disable" : "Click to enable"
                    }
                  >
                    <div
                      style={{
                        width: 20,
                        height: 20,
                        borderRadius: "50%",
                        backgroundColor: "#ffffff",
                        transform: skill.enabled
                          ? "translateX(20px)"
                          : "translateX(0px)",
                        transition: "transform 0.2s ease",
                        boxShadow: "0 1px 3px rgba(0,0,0,0.4)",
                      }}
                    />
                  </button>
                </div>

                <div
                  style={{
                    fontFamily: "var(--font-heading)",
                    fontSize: 16,
                    fontWeight: 600,
                    marginBottom: 6,
                  }}
                >
                  {skill.name}
                </div>
                <p
                  style={{
                    fontSize: 12,
                    color: "var(--color-text-secondary)",
                    lineHeight: 1.45,
                  }}
                >
                  {skill.desc}
                </p>
              </div>

              {/* Permissions List */}
              <div
                style={{ paddingTop: 10, borderTop: "var(--border-subtle)" }}
              >
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 6,
                    marginBottom: 6,
                  }}
                >
                  <Shield size={12} color="var(--color-text-tertiary)" />
                  <span
                    style={{
                      fontSize: 10,
                      fontFamily: "var(--font-mono)",
                      color: "var(--color-text-tertiary)",
                      textTransform: "uppercase",
                    }}
                  >
                    Required Permissions:
                  </span>
                </div>
                <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
                  {skill.permissions.map((perm) => (
                    <span
                      key={perm}
                      className="badge"
                      style={{
                        fontSize: 10,
                        background: "rgba(255, 255, 255, 0.03)",
                        color: "var(--color-text-secondary)",
                      }}
                    >
                      {perm}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
