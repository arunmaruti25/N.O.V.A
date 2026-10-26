import { useState } from 'react';
import { Search, Mic, Settings2, Minimize2, ArrowUpRight } from 'lucide-react';
import { useNova } from '../context/useNova';
export default function Header() {
  const { currentView, setCurrentView, status, isBackendConnected, triggerVoiceCommand, setIsMiniMode, isListening } = useNova();
  const [query, setQuery] = useState('');
  const hasComposer = ['home', 'chat', 'voice', 'automations', 'files'].includes(currentView);
  return <header className="topbar">
    <button className="wordmark" onClick={() => setCurrentView('home')} aria-label="NOVA home"><span className="brand-pearl" aria-hidden="true" /><span>NOVA</span></button>
    {!hasComposer && <form className="universal-search" onSubmit={e => { e.preventDefault(); if (query.trim() && triggerVoiceCommand(query)) { setCurrentView('chat'); setQuery(''); } }}><Search size={19} strokeWidth={1.7} /><input id="universal-command" aria-label="Universal command" placeholder="Ask NOVA anything..." value={query} onChange={e => setQuery(e.target.value)} /><kbd>Ctrl</kbd><kbd>K</kbd></form>}
    <div className="header-controls"><button className="icon-button header-mic" onClick={() => triggerVoiceCommand()} aria-label={isListening ? 'Finish speaking' : 'Start listening'}><Mic size={19} strokeWidth={1.7} /></button><button className="icon-button" onClick={() => setCurrentView('settings')} aria-label="Open settings"><Settings2 size={19} strokeWidth={1.7} /></button><span className="header-divider" /><div className="header-status"><span className={`status-dot ${isBackendConnected ? 'connected' : ''}`} />{isBackendConnected ? status.toLowerCase() : 'Offline'}</div><button className="profile-button" onClick={() => setCurrentView('settings')} aria-label="Your preferences">N<ArrowUpRight size={10} /></button><button className="icon-button mini-toggle" onClick={() => setIsMiniMode(true)} aria-label="Minimize NOVA" title="Compact mode (Ctrl+M). Running tasks continue."><Minimize2 size={17} /><span className="minimize-label">Minimize</span></button></div>
  </header>;
}
