import { useState } from "react";
import { useNova } from "../context/useNova";
import WorkspacePage from "../components/WorkspacePage";

export default function ComputerView() {
  const { request, triggerVoiceCommand, systemStatus, busy, isBackendConnected } = useNova();
  const [volume, setVolume] = useState(50);
  const [app, setApp] = useState("notepad");
  const disabled = busy || !isBackendConnected;
  return <WorkspacePage title="Computer control" description="Run registered Windows actions. Results come from the host computer; power actions require confirmation.">
    <div className="workspace-grid">
      <article className="glass-card workspace-card"><h2>System information</h2>
        <button className="btn-secondary" disabled={disabled} onClick={() => request("SYSTEM_STATUS")}>Refresh system status</button>
        {systemStatus ? <pre>{JSON.stringify(systemStatus, null, 2)}</pre> : <p>Refresh to read the current system and audio state.</p>}
      </article>
      <form className="glass-card workspace-form" onSubmit={(e) => { e.preventDefault(); triggerVoiceCommand(`open ${app}`); }}><h2>Open an application</h2>
        <label>Application name<input value={app} onChange={(e) => setApp(e.target.value)} required /></label>
        <button className="btn-primary" disabled={disabled || !app.trim()}>Open application</button>
      </form>
      <article className="glass-card workspace-card"><h2>Audio</h2>
        <label>Target volume: {volume}%<input type="range" min="0" max="100" value={volume} onChange={(e) => setVolume(Number(e.target.value))} /></label>
        <div className="workspace-actions"><button className="btn-secondary" disabled={disabled} onClick={() => triggerVoiceCommand(`set volume to ${volume}`)}>Apply volume</button>
        <button className="btn-secondary" disabled={disabled} onClick={() => triggerVoiceCommand("mute volume")}>Mute</button>
        <button className="btn-secondary" disabled={disabled} onClick={() => triggerVoiceCommand("unmute volume")}>Unmute</button></div>
      </article>
      <article className="glass-card workspace-card"><h2>Power</h2><p>Review the confirmation before continuing.</p>
        <div className="workspace-actions"><button className="btn-secondary" disabled={disabled} onClick={() => triggerVoiceCommand("restart computer")}>Restart</button>
        <button className="btn-secondary" disabled={disabled} onClick={() => triggerVoiceCommand("shutdown computer")}>Shut down</button></div>
      </article>
    </div>
  </WorkspacePage>;
}
