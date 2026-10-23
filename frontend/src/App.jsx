import { useEffect } from 'react';
import { AnimatePresence, motion, MotionConfig } from 'framer-motion';
import { NovaProvider } from './context/NovaContext';
import { useNova } from './context/useNova';
import Header from './components/Header';
import Sidebar from './components/Sidebar';
import MiniNova from './components/MiniNova';
import PermissionModal from './components/PermissionModal';
import NotificationToast from './components/NotificationToast';
import HomeView from './views/HomeView';
import VisionView from './views/VisionView';
import WebView from './views/WebView';
import SkillsView from './views/SkillsView';
import ComputerView from './views/ComputerView';
import MemoryView from './views/MemoryView';
import ActivityView from './views/ActivityView';
import SettingsView from './views/SettingsView';
import AssistantView from './views/AssistantView';
import './styles/nova.css';
import './styles/spatial.css';

const views = { home: HomeView, vision: VisionView, web: WebView, skills: SkillsView, computer: ComputerView, memory: MemoryView, activity: ActivityView, settings: SettingsView, chat: AssistantView, voice: AssistantView, automations: AssistantView, files: AssistantView };
function NovaMainApp() {
  const { currentView, isMiniMode, setIsMiniMode, triggerVoiceCommand, cancelOperation, permissionState, reducedMotion } = useNova();
  useEffect(() => {
    const handler = (e) => {
      if (e.ctrlKey && e.key.toLowerCase() === 'm') { e.preventDefault(); setIsMiniMode(v => !v); }
      if (e.ctrlKey && e.shiftKey && e.key.toLowerCase() === 'n') { e.preventDefault(); triggerVoiceCommand(); }
      if (e.key === 'Escape' && !permissionState.isOpen) cancelOperation();
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') { e.preventDefault(); document.getElementById('universal-command')?.focus(); }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [setIsMiniMode, triggerVoiceCommand, cancelOperation, permissionState.isOpen]);
  const View = views[currentView] || HomeView;
  return <MotionConfig reducedMotion={reducedMotion ? 'always' : 'user'}><div className="nova-app" data-reduced-motion={reducedMotion}>
    <a className="skip-link" href="#main-content">Skip to content</a>
    <AnimatePresence>{isMiniMode && <MiniNova />}</AnimatePresence>
    {!isMiniMode && <><Header /><main id="main-content" className="main-content"><AnimatePresence mode="wait"><motion.div className="view-container" key={currentView} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -6 }} transition={{ type: 'spring', stiffness: 240, damping: 28 }}><View /></motion.div></AnimatePresence></main><Sidebar /><footer className="app-footer"><span>NOVA SPATIAL ATELIER</span><span>Your space. Your intelligence.</span><span>CTRL + SHIFT + N <i /> TALK TO NOVA</span></footer></>}
    <PermissionModal /><NotificationToast />
  </div></MotionConfig>;
}
export default function App() { return <NovaProvider><NovaMainApp /></NovaProvider>; }
