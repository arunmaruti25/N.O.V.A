import { useState } from "react";
import { Brain, Trash2, Plus, Sparkles } from "lucide-react";
import { useNova } from "../context/useNova";

const INITIAL_MEMORIES = [
  {
    id: 1,
    category: "Preferences",
    text: "Prefers dark futuristic visual themes across all tools and workspaces.",
  },
  {
    id: 2,
    category: "Workstation",
    text: "Primary display is 1920×1080 running Windows environment on D:\\ drive.",
  },
  {
    id: 3,
    category: "Project",
    text: "Currently developing NOVA — Next-generation personal AI assistant for Windows.",
  },
  {
    id: 4,
    category: "Workflow",
    text: "Prefers concise, actionable code implementations over theoretical walkthroughs.",
  },
  {
    id: 5,
    category: "Voice",
    text: "Responds best to calm, immediate voice synthesis without generic conversational fillers.",
  },
];

export default function MemoryView() {
  const { addNotification } = useNova();
  const [memories, setMemories] = useState(INITIAL_MEMORIES);
  const [activeCategory, setActiveCategory] = useState("All");
  const [newMemoryText, setNewMemoryText] = useState("");

  const categories = [
    "All",
    "Preferences",
    "Project",
    "Workstation",
    "Workflow",
    "Voice",
  ];

  const handleForget = (id, text) => {
    setMemories((prev) => prev.filter((m) => m.id !== id));
    addNotification({
      type: "info",
      title: "Memory Removed",
      message: `NOVA has forgotten: "${text.slice(0, 32)}..."`,
    });
  };

  const handleAddMemory = (e) => {
    e.preventDefault();
    if (!newMemoryText.trim()) return;

    const newMem = {
      id: Date.now(),
      category: activeCategory === "All" ? "Preferences" : activeCategory,
      text: newMemoryText.trim(),
    };
    setMemories([newMem, ...memories]);
    setNewMemoryText("");
    addNotification({
      type: "success",
      title: "Memory Stored",
      message: "New personal context committed to memory.",
    });
  };

  const filtered = memories.filter(
    (m) => activeCategory === "All" || m.category === activeCategory,
  );

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
          <Brain size={20} color="var(--color-nova-primary)" />
          <h1
            style={{
              fontFamily: "var(--font-heading)",
              fontSize: 22,
              fontWeight: 600,
              color: "var(--color-text-primary)",
            }}
          >
            Long-Term Memory & Context
          </h1>
        </div>
        <p style={{ fontSize: 13, color: "var(--color-text-secondary)" }}>
          NOVA retains persistent knowledge of your habits, workstation
          environment, and active projects.
        </p>
      </div>

      {/* Memory Capacity Status */}
      <div
        className="glass-card"
        style={{
          padding: 16,
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <Sparkles size={18} color="var(--color-nova-cyan)" />
          <div>
            <div
              style={{
                fontSize: 13,
                fontWeight: 600,
                color: "var(--color-text-primary)",
              }}
            >
              {memories.length} Active Context Items Stored
            </div>
            <div
              style={{
                fontSize: 11,
                color: "var(--color-text-tertiary)",
                marginTop: 2,
              }}
            >
              Zero external data leakage · Local storage isolation
            </div>
          </div>
        </div>

        <button
          type="button"
          onClick={() => {
            setMemories([]);
            addNotification({
              type: "warning",
              title: "Memory Reset",
              message: "All personal context cleared.",
            });
          }}
          className="btn btn-secondary"
          style={{ fontSize: 12, height: 32 }}
        >
          Clear All Context
        </button>
      </div>

      {/* Add Memory Form */}
      <form onSubmit={handleAddMemory} style={{ display: "flex", gap: 10 }}>
        <input
          type="text"
          value={newMemoryText}
          onChange={(e) => setNewMemoryText(e.target.value)}
          placeholder="Teach NOVA a new preference or project detail..."
          style={{
            flex: 1,
            background: "rgba(255, 255, 255, 0.04)",
            border: "var(--border-default)",
            borderRadius: "var(--radius-md)",
            padding: "0 16px",
            color: "var(--color-text-primary)",
            fontSize: 13,
            outline: "none",
          }}
        />
        <button
          type="submit"
          className="btn btn-primary"
          style={{ gap: 6, minWidth: 120 }}
        >
          <Plus size={16} /> Remember
        </button>
      </form>

      {/* Filter Tabs */}
      <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
        {categories.map((cat) => {
          const isSelected = activeCategory === cat;
          return (
            <button
              key={cat}
              type="button"
              onClick={() => setActiveCategory(cat)}
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

      {/* Memory Cards List */}
      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        {filtered.map((mem) => (
          <div
            key={mem.id}
            className="glass-card"
            style={{
              padding: "14px 18px",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              gap: 16,
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <span
                className="badge"
                style={{
                  background: "rgba(123, 92, 240, 0.15)",
                  color: "var(--color-nova-cyan)",
                  border: "1px solid rgba(123, 92, 240, 0.3)",
                  fontSize: 10,
                  fontFamily: "var(--font-mono)",
                  flexShrink: 0,
                }}
              >
                {mem.category}
              </span>
              <span
                style={{
                  fontSize: 13,
                  color: "var(--color-text-primary)",
                  lineHeight: 1.4,
                }}
              >
                {mem.text}
              </span>
            </div>

            <button
              type="button"
              onClick={() => handleForget(mem.id, mem.text)}
              className="btn-icon"
              style={{ width: 32, height: 32, flexShrink: 0 }}
              title="Forget this memory"
            >
              <Trash2 size={15} color="var(--color-text-tertiary)" />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
