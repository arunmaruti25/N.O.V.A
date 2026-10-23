import { Maximize2, Mic, Square } from 'lucide-react';
import { useNova } from '../context/useNova';
import NovaCore from './NovaCore';
export default function MiniNova() {
 const { setIsMiniMode, statusDetail, busy, triggerVoiceCommand, cancelOperation } = useNova();
 return <aside className="mini-nova glass-card"><div className="mini-heading"><span>nova.</span><button className="icon-button" onClick={() => setIsMiniMode(false)} aria-label="Expand NOVA"><Maximize2 size={16} /></button></div><NovaCore size={190} isMini /><p>{statusDetail}</p><button className="btn-secondary" onClick={() => busy ? cancelOperation() : triggerVoiceCommand()}>{busy ? <Square size={15} /> : <Mic size={15} />}{busy ? 'Stop' : 'Talk to NOVA'}</button><button className="text-link" onClick={() => setIsMiniMode(false)}>Return to your space</button></aside>;
}
