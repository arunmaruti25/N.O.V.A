import { useState } from "react";
import { useNova } from "../context/useNova";
import WorkspacePage from "../components/WorkspacePage";

export default function MemoryView() {
  const { memories, request, busy, isBackendConnected } = useNova();
  const [text, setText] = useState("");
  const [category, setCategory] = useState("User Note");
  const [filter, setFilter] = useState("");
  const visible = memories.filter((m) => `${m.category} ${m.text}`.toLowerCase().includes(filter.toLowerCase()));
  function save(e) {
    e.preventDefault();
    if (text.trim() && request("MEMORY_SAVE", { text: text.trim(), category })) setText("");
  }
  return <WorkspacePage title="Memory" description="Notes stored in your local SQLite database. They stay here after you restart NOVA.">
    <form className="glass-card workspace-form" onSubmit={save}>
      <label>Category<input value={category} maxLength={100} onChange={(e) => setCategory(e.target.value)} /></label>
      <label>New memory<textarea value={text} onChange={(e) => setText(e.target.value)} maxLength={16000} required placeholder="Something NOVA should remember" /></label>
      <button className="btn-primary" disabled={busy || !isBackendConnected || !text.trim()}>Save memory</button>
    </form>
    <label>Filter memories<input type="search" value={filter} onChange={(e) => setFilter(e.target.value)} placeholder="Search saved notes" /></label>
    <p>{memories.length} saved memories</p>
    <div className="workspace-grid">{visible.map((m) => <article className="glass-card workspace-card" key={m.id}>
      <span className="badge">{m.category}</span><p style={{ whiteSpace: "pre-wrap" }}>{m.text}</p>
      <small>{m.created_at}</small>
      <button className="btn-secondary" disabled={busy || !isBackendConnected} onClick={() => request("MEMORY_DELETE", { id: m.id })}>Delete memory</button>
    </article>)}</div>
    {!visible.length && <p>No memories to display.</p>}
  </WorkspacePage>;
}
