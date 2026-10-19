import { useNova } from "../context/useNova";

export default function WorkspacePage({ title, description, children }) {
  const { errorMessage, isBackendConnected, statusDetail, busy } = useNova();
  return <section className="workspace-page">
    <header><h1>{title}</h1><p>{description}</p></header>
    {!isBackendConnected && <p className="notice" role="status">Backend disconnected. Start the server to use these controls.</p>}
    {errorMessage && <p className="notice error" role="alert">{errorMessage}</p>}
    {busy && <p className="notice" role="status">{statusDetail}</p>}
    {children}
  </section>;
}
