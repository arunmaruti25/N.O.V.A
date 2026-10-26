import { useEffect, useRef } from 'react';
import { motion } from 'framer-motion';
import { House, AudioLines, Zap, Monitor, FolderOpen, Brain, Shapes, Settings2, ScanLine, Globe, History, Ellipsis, Search } from 'lucide-react';
import { useNova } from '../context/useNova';
const primary = [['home', 'Home', House], ['chat', 'Workspace', FolderOpen], ['automations', 'Automations', Zap], ['settings', 'Settings', Settings2]];
const quickAccess = [['computer', 'App Launcher', Search], ['files', 'Files', FolderOpen], ['vision', 'Screen Assistant', Monitor], ['computer', 'System Control', ScanLine]];
const secondary = [['voice', 'Voice assistant', AudioLines], ['skills', 'Skills', Shapes], ['memory', 'Memory', Brain], ['web', 'Web intelligence', Globe], ['activity', 'Recent activity', History]];
export default function Sidebar() {
  const { currentView, setCurrentView, isBackendConnected } = useNova();
  const menu = useRef(null);
  useEffect(() => {
    const dismiss = e => { if (menu.current && (!menu.current.contains(e.target) || e.key === 'Escape')) menu.current.open = false; };
    document.addEventListener('pointerdown', dismiss);
    document.addEventListener('keydown', dismiss);
    return () => { document.removeEventListener('pointerdown', dismiss); document.removeEventListener('keydown', dismiss); };
  }, []);
  return <aside className="dock-wrap">
    <button className="sidebar-brand" onClick={() => setCurrentView('home')} aria-label="NOVA home"><span className="brand-pearl" aria-hidden="true" /><span><strong>NOVA</strong><small>Spatial Intelligence</small></span></button>
    <nav className="floating-dock" aria-label="Main navigation">{primary.map(([id, label, Icon]) => <button key={id} className={`dock-item ${currentView === id ? 'active' : ''}`} onClick={() => setCurrentView(id)} aria-label={label} aria-current={currentView === id ? 'page' : undefined} title={label}>{currentView === id && <motion.span className="dock-active" layoutId="dock-active" transition={{ type: 'spring', stiffness: 380, damping: 30 }} />}<Icon size={21} strokeWidth={1.7} /><span>{label}</span></button>)}</nav>
    <div className="sidebar-quick"><span className="sidebar-section-label">Quick Access</span>{quickAccess.map(([id, label, Icon]) => <button key={label} onClick={() => setCurrentView(id)}><Icon size={20} strokeWidth={1.7} /><span>{label}</span></button>)}
      <details className="dock-more" ref={menu}><summary aria-label="More sections" title="More sections" className={secondary.some(([id]) => id === currentView) ? 'secondary-active' : ''}><Ellipsis size={20} /><span>More tools</span></summary><div className="dock-menu">{secondary.map(([id, label, Icon]) => <button key={id} aria-current={id === currentView ? 'page' : undefined} onClick={() => { setCurrentView(id); menu.current.open = false; }}><Icon size={17} /><span>{label}</span></button>)}</div></details>
    </div>
    <div className="sidebar-footer"><span className="brand-pearl" aria-hidden="true" /><span><strong>NOVA</strong><small>Your personal assistant</small></span><span className={`status-dot ${isBackendConnected ? 'connected' : ''}`} /><small>{isBackendConnected ? 'Ready' : 'Offline'}</small></div>
  </aside>;
}
