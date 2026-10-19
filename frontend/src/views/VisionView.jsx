import { useNova } from "../context/useNova";
import WorkspacePage from "../components/WorkspacePage";

export default function VisionView() {
  const { request, visionResult, busy, isBackendConnected } = useNova();
  return <WorkspacePage title="Screen capture" description="Capture the primary monitor on the computer running NOVA. The preview stays local; capture does not send it to an AI provider.">
    <div><button className="btn-primary" disabled={busy || !isBackendConnected} onClick={() => request("CAPTURE_SCREEN")}>Capture screen</button></div>
    {visionResult?.success ? <figure className="glass-card workspace-card">
      <img className="screen-preview" src={`data:image/jpeg;base64,${visionResult.base64_preview}`} alt="Captured primary monitor" />
      <figcaption>{visionResult.width} × {visionResult.height} pixels</figcaption>
    </figure> : <p>{visionResult?.error || "No capture yet. Click Capture screen to take a snapshot."}</p>}
  </WorkspacePage>;
}
