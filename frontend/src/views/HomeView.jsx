import { ArrowRight, BookOpen, Clock3, Code2, FolderSearch, Grid2X2, Layers3, Monitor, RefreshCw, ScanLine, Settings2, ShieldCheck, Volume2, Wifi, Zap } from 'lucide-react';
import NovaCore from '../components/NovaCore';
import VoiceBar from '../components/VoiceBar';
import { useNova } from '../context/useNova';

const quickActions = [
  { title: 'Open App', detail: 'Launch your favorite applications.', view: 'computer', icon: Grid2X2, tone: 'blue' },
  { title: 'Find Files', detail: 'Find your documents and folders.', view: 'files', icon: FolderSearch, tone: 'violet' },
  { title: 'System Control', detail: 'Manage your volume and system.', view: 'computer', icon: Settings2, tone: 'green' },
  { title: 'Screen Assistant', detail: 'Capture and explore your screen.', view: 'vision', icon: Monitor, tone: 'peach' },
];

function PanelHeading({ icon: Icon, title, action, onClick }) {
  return <div className="spatial-panel-heading"><h2><Icon size={19} strokeWidth={1.7} />{title}</h2>{action && <button className="panel-link" onClick={onClick}>{action}<ArrowRight size={14} /></button>}</div>;
}

function HealthGauge({ label, value, tone }) {
  const available = typeof value === 'number' && Number.isFinite(value);
  const percent = available ? Math.max(0, Math.min(100, value)) : 0;
  return <div className={`health-gauge ${tone}`}><div className="gauge-dial"><svg viewBox="0 0 100 100" aria-hidden="true"><circle className="gauge-track" cx="50" cy="50" r="41" /><circle className="gauge-value" cx="50" cy="50" r="41" strokeDasharray={`${percent * 2.576} 257.6`} /></svg><span>{available ? `${Math.round(value)}%` : <span aria-label="Not available">&mdash;</span>}</span></div><span className="gauge-label">{label}</span></div>;
}

export default function HomeView() {
  const { setCurrentView, isBackendConnected, activities, memories, tools, systemStatus, request, triggerVoiceCommand, busy, currentTask, status, statusDetail, isListening } = useNova();
  const metrics = isBackendConnected && systemStatus?.system && !systemStatus.system.error ? systemStatus.system : null;
  const canRun = isBackendConnected && !busy;
  const run = command => { if (triggerVoiceCommand(command)) setCurrentView('chat'); };
  const hour = new Date().getHours();

  return <section className="spatial-home" aria-label="Your NOVA workspace">
    <div className="spatial-grid">
      <div className="spatial-center">
        <div className="spatial-core-stage"><div className="core-aura" /><div className="core-orbit orbit-one" /><div className="core-orbit orbit-two" /><span className="orbit-bead bead-one" /><NovaCore size={380} /><span className="core-state" data-state={status.toLowerCase()}><span className={`status-dot ${isBackendConnected && status !== 'ERROR' ? 'connected' : ''}`} />{!isBackendConnected ? 'Connect NOVA to speak' : isListening ? 'Listening · click to transcribe' : busy ? statusDetail || 'Working on your request' : 'Ready when you are'}</span></div>
        <div className="spatial-welcome"><h1>Good {hour < 12 ? 'morning' : hour < 17 ? 'afternoon' : 'evening'}.</h1><p>What can I <span>help you</span> with?</p></div>
        <div className="spatial-command"><VoiceBar /><div className="spatial-quick-actions"><button disabled={!canRun} onClick={() => run('open VS Code')}><Code2 size={17} />Open VS Code</button><button onClick={() => setCurrentView('files')}><FolderSearch size={17} />Find my files</button><button disabled={!canRun} onClick={() => run('set volume to 30')}><Volume2 size={17} />Set volume to 30%</button><button disabled={!canRun} onClick={() => { if (request('CAPTURE_SCREEN')) setCurrentView('vision'); }}><ScanLine size={17} />Take a screenshot</button></div></div>
        <div className="home-action-grid">{quickActions.map(({ title, detail, view, icon: Icon, tone }) => <button className="home-action-card" key={title} onClick={() => setCurrentView(view)}><span className={`tile-icon ${tone}`}><Icon size={25} strokeWidth={1.8} /></span><strong>{title}</strong><span className="action-description">{detail}</span><span className="action-arrow"><ArrowRight size={17} /></span></button>)}</div>
        {currentTask && <button className="current-workflow" onClick={() => setCurrentView('automations')}><Zap size={16} /><span>{currentTask.description || 'Current workflow'}</span><small>{currentTask.status}</small><ArrowRight size={14} /></button>}
      </div>
      <aside className="spatial-column right-column" aria-label="Workspace overview">
        <section className="spatial-panel health-panel">
          <div className="spatial-panel-heading"><h2><Layers3 size={19} strokeWidth={1.7} />System Status</h2><button className="health-refresh" disabled={!canRun} onClick={() => request('SYSTEM_STATUS')} aria-label="Refresh system readings" title="Refresh system status"><RefreshCw size={13} />{metrics ? 'Refresh' : 'Read status'}</button></div>
          <div className="health-gauges"><HealthGauge label="CPU" value={metrics?.cpu_percent} tone="blue" /><HealthGauge label="Memory" value={metrics?.memory_percent} tone="violet" /><HealthGauge label="Disk" value={metrics?.disk_percent} tone="green" /></div>
          <div className="system-details"><div><Wifi size={17} /><span>Windows host</span><strong className={isBackendConnected ? 'text-success' : ''}>{isBackendConnected ? 'Connected' : 'Offline'}</strong></div><button onClick={() => setCurrentView('skills')}><Layers3 size={17} /><span>Available tools</span><strong>{isBackendConnected ? tools.length : '—'}</strong></button><button onClick={() => setCurrentView('memory')}><BookOpen size={17} /><span>Saved memories</span><strong>{memories.length}</strong></button><button onClick={() => setCurrentView('computer')}><ShieldCheck size={17} /><span>Assistant</span><strong>{isBackendConnected ? busy ? 'Working' : 'Ready' : 'Offline'}</strong></button></div>
        </section>
        <section className="spatial-panel recent-panel">
          <PanelHeading icon={Clock3} title="Recent Activity" action="See all" onClick={() => setCurrentView('activity')} />
          {activities.length ? <div className="recent-commands">{activities.slice(0, 4).map((activity, index) => <button className="recent-command" key={activity.id} onClick={() => setCurrentView('activity')}><span className={`tile-icon ${activity.status === 'error' ? 'pink' : ['blue', 'violet', 'peach', 'blue'][index]}`}><Zap size={20} /></span><span><strong>{activity.action}</strong><small>{activity.status === 'error' ? 'Failed' : activity.verified ? 'Verified' : activity.type || 'Host activity'}</small></span><time>{activity.time}</time></button>)}</div> : <div className="recent-empty"><span className="empty-orbit"><Clock3 size={25} strokeWidth={1.5} /></span><h3>A fresh start.</h3><p>Your activity will appear here as you use NOVA.</p><button className="panel-link" onClick={() => setCurrentView('chat')}>Start a conversation <ArrowRight size={14} /></button></div>}
        </section>
      </aside>
    </div>
  </section>;
}
