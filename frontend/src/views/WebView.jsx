import { useState } from "react";
import { useNova } from "../context/useNova";
import WorkspacePage from "../components/WorkspacePage";

export default function WebView() {
  const { request, webResult, busy, isBackendConnected, activeModel, isAutoRouting } = useNova();
  const [query, setQuery] = useState("");
  const local = !isAutoRouting && activeModel.provider === "Ollama";
  return <WorkspacePage title="Web search" description="Search the web and open the original sources. Results are retrieved live, with no generated citations.">
    <form className="workspace-form glass-card" onSubmit={(e) => { e.preventDefault(); request("WEB_SEARCH", { text: query }); }}>
      <label>Search query<input type="search" value={query} onChange={(e) => setQuery(e.target.value)} required placeholder="What would you like to find?" /></label>
      <button className="btn-primary" disabled={busy || !isBackendConnected || local || !query.trim()}>Search web</button>
      {local && <p>Web search is disabled while local mode is selected.</p>}
    </form>
    {webResult && <div aria-live="polite"><p>{webResult.summary || webResult.error}</p>
      {(webResult.results || []).map((r, i) => <article className="glass-card workspace-card" key={r.url || i}>
        <h2><a href={/^https?:\/\//i.test(r.url) ? r.url : undefined} target="_blank" rel="noreferrer">{r.title}</a></h2>
        <p>{r.snippet || r.description}</p><small>{r.url}</small>
      </article>)}
    </div>}
  </WorkspacePage>;
}
