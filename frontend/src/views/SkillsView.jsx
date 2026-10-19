import { useState } from "react";
import { useNova } from "../context/useNova";
import WorkspacePage from "../components/WorkspacePage";

export default function SkillsView() {
  const { tools } = useNova();
  const [query, setQuery] = useState("");
  const filtered = tools.filter((t) => `${t.name} ${t.description}`.toLowerCase().includes(query.toLowerCase()));
  return <WorkspacePage title="Tool registry" description="These are the tools registered by the running backend. Permission labels show which actions require confirmation.">
    <label>Find a tool<input type="search" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Search available tools" /></label>
    <p>{tools.length} registered tools</p>
    <div className="workspace-grid">{filtered.map((t) => <article className="glass-card workspace-card" key={t.name}>
      <span className="badge">{t.category}</span><h2>{t.name}</h2><p>{t.description}</p>
      <small>{t.permission_level === "SAFE" ? "Available" : t.permission_level.replaceAll("_", " ")}</small>
    </article>)}</div>
    {!filtered.length && <p>No matching tools available.</p>}
  </WorkspacePage>;
}
