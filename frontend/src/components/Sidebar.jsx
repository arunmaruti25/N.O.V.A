import { useEffect, useRef } from 'react';
import { motion } from 'framer-motion';
import { House, MessagesSquare, AudioLines, Zap, Monitor, FolderOpen, Brain, Shapes, Settings2, Eye, Globe, History, Ellipsis } from 'lucide-react';
import { useNova } from '../context/useNova';
const primary = [['home','Home',House], ['chat','Chat',MessagesSquare], ['automations','Automations',Zap], ['files','Files',FolderOpen], ['skills','Skills',Shapes], ['settings','Settings',Settings2]];
const secondary = [['voice','Voice assistant',AudioLines], ['computer','System controls',Monitor], ['memory','Memory',Brain], ['vision','Screen capture',Eye], ['web','Web intelligence',Globe], ['activity','Recent activity',History]];
export default function Sidebar() {
  const { currentView, setCurrentView } = useNova();
  const menu = useRef(null);
  useEffect(() => {
    const dismiss = e => { if (menu.current && (!menu.current.contains(e.target) || e.key === 'Escape')) menu.current.open = false; };
    document.addEventListener('pointerdown', dismiss);
    document.addEventListener('keydown', dismiss);
    return () => { document.removeEventListener('pointerdown', dismiss); document.removeEventListener('keydown', dismiss); };
  }, []);
  return <div className="dock-wrap"><nav className="floating-dock" aria-label="Main navigation">{primary.map(([id,label,Icon]) => <button key={id} className={`dock-item ${currentView === id ? 'active' : ''}`} onClick={() => setCurrentView(id)} aria-label={label} aria-current={currentView === id ? 'page' : undefined} title={label}>{currentView === id && <motion.span className="dock-active" layoutId="dock-active" transition={{ type:'spring', stiffness:380, damping:30 }} />}<Icon size={21} strokeWidth={1.7} /><span>{label}</span></button>)}<details className="dock-more" ref={menu}><summary aria-label="More sections" title="More sections" className={secondary.some(([id]) => id === currentView) ? 'secondary-active' : ''}><Ellipsis size={20} /><span>More</span></summary><div className="dock-menu">{secondary.map(([id,label,Icon]) => <button key={id} aria-current={id === currentView ? 'page' : undefined} onClick={() => { setCurrentView(id); menu.current.open = false; }}><Icon size={17} /><span>{label}</span></button>)}</div></details></nav></div>;
}
