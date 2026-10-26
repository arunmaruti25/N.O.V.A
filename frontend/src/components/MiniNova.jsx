import { Maximize2, Mic, Square } from 'lucide-react';
import { useEffect, useRef } from 'react';
import { useNova } from '../context/useNova';
import NovaCore from './NovaCore';
export default function MiniNova() {
 const { setIsMiniMode, statusDetail, busy, triggerVoiceCommand, cancelOperation, isListening, isBackendConnected, transcript, taskModel } = useNova();
 const expandButton = useRef(null);
 useEffect(() => { expandButton.current?.focus(); }, []);
 const expand = () => {
  setIsMiniMode(false);
  requestAnimationFrame(() => document.querySelector('.mini-toggle')?.focus());
 };
 return <aside className="mini-nova glass-card" aria-label="NOVA compact mode"><div className="mini-heading"><span>NOVA</span><button ref={expandButton} className="icon-button" onClick={expand} aria-label="Expand NOVA"><Maximize2 size={16} /></button></div><span className="mini-connection"><span className={`status-dot ${isBackendConnected ? 'connected' : ''}`} />{isBackendConnected ? 'Connected' : 'Backend disconnected'}{taskModel?.provider && <span>{taskModel.provider}</span>}</span><NovaCore size={160} isMini /><p role="status">{statusDetail || (busy ? 'Working on your task' : 'Ready when you are')}</p>{transcript && <div className="mini-response" aria-live="polite">{transcript}</div>}<button className="btn-secondary" disabled={!isBackendConnected} onClick={() => isListening ? triggerVoiceCommand() : busy ? cancelOperation() : triggerVoiceCommand()}>{busy ? <Square size={15} /> : <Mic size={15} />}{isListening ? 'Finish speaking' : busy ? 'Stop' : 'Talk to NOVA'}</button><p className="mini-background-note">Tasks continue while the browser is minimized. Keep this tab and the NOVA server open.</p><button className="text-link" onClick={expand}>Return to your space</button></aside>;
}
