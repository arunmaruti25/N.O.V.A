import { useNova } from "../context/useNova";
import WorkspacePage from "../components/WorkspacePage";

export default function SettingsView() {
  const { isAutoRouting, setIsAutoRouting, activeModel, setActiveModel, availableModels, speechEnabled, setSpeechEnabled, reducedMotion, setReducedMotion } = useNova();
  return <WorkspacePage title="Settings" description="Preferences are saved in this browser. API keys and model identifiers are configured in the backend .env file.">
    <div className="glass-card workspace-form">
      <label className="check-label"><input type="checkbox" checked={isAutoRouting} onChange={(e) => setIsAutoRouting(e.target.checked)} /> Choose a provider automatically</label>
      <label>Preferred provider<select value={activeModel.provider} disabled={isAutoRouting} onChange={(e) => setActiveModel(availableModels.find((m) => m.provider === e.target.value))}>
        {availableModels.map((m) => <option key={m.provider}>{m.provider}</option>)}
      </select></label>
      <p>Ollama mode keeps inference local and disables online speech and web search. In cloud mode, unavailable providers may fall back to another configured provider.</p>
      <label className="check-label"><input type="checkbox" checked={speechEnabled} onChange={(e) => setSpeechEnabled(e.target.checked)} /> Read responses aloud using online text-to-speech</label>
      <p>The microphone uses push-to-talk and Google speech recognition. Ctrl+Shift+N starts listening; Escape cancels. Audio uses the computer running the backend.</p>
      <label className="check-label"><input type="checkbox" checked={reducedMotion} onChange={(e) => setReducedMotion(e.target.checked)} /> Reduce animation</label>
    </div>
    <div className="workspace-grid">{availableModels.map((m) => <article className="glass-card workspace-card" key={m.provider}>
      <h2>{m.provider}</h2><code>{m.tag}</code><p>{m.provider === "Ollama" ? "Requires a running local Ollama service and downloaded model." : m.configured ? "API key configured; availability checked when used." : "No API key configured."}</p>
    </article>)}</div>
  </WorkspacePage>;
}
