import { ArrowRight, BookOpen, Clock3, Code2, FileSearch, FolderOpen, Globe, Layers3, Leaf, MessageSquare, Monitor, Music2, RefreshCw, Search, ShieldCheck, Sparkles, Sun, Workflow, Zap } from 'lucide-react';
import NovaCore from '../components/NovaCore';
import VoiceBar from '../components/VoiceBar';
import { useNova } from '../context/useNova';

const appShortcuts = [
  { name: 'VS Code', icon: Code2, command: 'open VS Code', tone: 'blue' },
  { name: 'Notepad', icon: BookOpen, command: 'open Notepad', tone: 'violet' },
  { name: 'Music', icon: Music2, command: 'open Spotify', tone: 'green' },
  { name: 'Chrome', icon: Globe, command: 'open Chrome', tone: 'peach' },
  { name: 'Files', icon: FolderOpen, command: 'open Downloads', tone: 'peach' },
  { name: 'Terminal', icon: Monitor, command: 'open terminal', tone: 'blue' },
];
const ideas = [
  { title: 'Morning, made simple', detail: 'Open Chrome and Notepad', command: 'open Chrome and open Notepad', icon: Sun, tone: 'peach' },
  { title: 'Find your next thought', detail: 'Search your documents for PDFs', command: 'search files for *.pdf', icon: FileSearch, tone: 'violet' },
  { title: 'A quieter workspace', detail: 'Set your system volume to 20%', command: 'set volume to 20', icon: Music2, tone: 'pink' },
];

function PanelHeading({ icon: Icon, title, action, onClick }) {
  return <div className="spatial-panel-heading"><h2><Icon size={19} strokeWidth={1.7} />{title}</h2>{action && <button className="panel-link" onClick={onClick}>{action}<ArrowRight size={13} /></button>}</div>;
}

function HealthGauge({ label, value, tone }) {
  const available = typeof value === 'number' && Number.isFinite(value);
  const percent = available ? Math.max(0, Math.min(100, value)) : 0;
  return <div className={`health-gauge ${tone}`}><div className="gauge-dial"><svg viewBox="0 0 100 100" aria-hidden="true"><circle className="gauge-track" cx="50" cy="50" r="41" /><circle className="gauge-value" cx="50" cy="50" r="41" strokeDasharray={`${percent * 2.576} 257.6`} /></svg><span>{available ? `${Math.round(value)}%` : <span aria-label="Not available">&mdash;</span>}</span></div><span className="gauge-label">{label}</span></div>;
}

export default function HomeView() {
  const { setCurrentView, isBackendConnected, activities, memories, tools, systemStatus, request, triggerVoiceCommand, busy, currentTask, status, statusDetail } = useNova();
  const metrics = isBackendConnected && systemStatus?.system && !systemStatus.system.error ? systemStatus.system : null;
  const canRun = isBackendConnected && !busy;
  const launchAvailable = tools.some(tool => tool.name === 'app.launch');
  const run = command => { if (triggerVoiceCommand(command)) setCurrentView('chat'); };

  return <section className="spatial-home" aria-label="Your NOVA workspace">
    <div className="spatial-topline"><span><Sparkles size={12} /> YOUR DAY, WITH A LITTLE MORE POSSIBILITY.</span><span>PERSONAL SPACE <i /> 01</span></div>
    <div className="spatial-grid">
      <aside className="spatial-column left-column">
        <section className="spatial-panel recent-panel">
          <PanelHeading icon={Clock3} title="Recent commands" action="See all" onClick={() => setCurrentView('activity')} />
          {activities.length ? <div className="recent-commands">{activities.slice(0, 4).map(activity => <button className="recent-command" key={activity.id} onClick={() => setCurrentView('activity')}><span className={`tile-icon ${activity.status === 'error' ? 'pink' : 'violet'}`}><Zap size={17} /></span><span><strong>{activity.action}</strong><small>{activity.status === 'error' ? 'Failed' : activity.verified ? 'Verified' : 'Recorded on your host'}</small></span><time>{activity.time}</time></button>)}</div> : <div className="recent-empty"><span className="empty-orbit"><Clock3 size={25} strokeWidth={1.3} /></span><h3>A fresh start.</h3><p>Your commands will find<br />their place here.</p><button className="panel-link" onClick={() => setCurrentView('chat')}>Start a conversation <ArrowRight size={13} /></button></div>}
        </section>
        <section className="spatial-panel apps-panel">
          <PanelHeading icon={Layers3} title="Your app launchpad" action="Tools" onClick={() => setCurrentView('skills')} />
          <div className="apps-grid">{appShortcuts.map(({ name, icon: Icon, command, tone }) => <button key={name} className="app-tile" onClick={() => run(command)} disabled={!canRun} aria-label={`Launch ${name} on your Windows host`} title={`Ask NOVA to open ${name}`}><span className={`tile-icon ${tone}`}><Icon size={27} strokeWidth={1.7} /></span><span>{name}</span></button>)}</div>
          <div className="panel-footnote"><span className={`status-dot ${isBackendConnected && launchAvailable ? 'connected' : ''}`} /><span>{isBackendConnected ? launchAvailable ? 'Host app launcher available' : 'App launcher not registered' : 'Connect your Windows host to launch apps'}</span></div>
        </section>
      </aside>

      <div className="spatial-center">
        <div className="spatial-core-stage"><div className="core-aura" /><div className="core-orbit orbit-one" /><div className="core-orbit orbit-two" /><span className="orbit-bead bead-one" /><span className="orbit-bead bead-two" /><NovaCore size={510} /><span className="core-state" data-state={status.toLowerCase()}><span className={`status-dot ${isBackendConnected && status !== 'ERROR' ? 'connected' : ''}`} />{!isBackendConnected ? 'Connect NOVA to speak' : status === 'LISTENING' ? 'Listening · click to stop' : busy ? `${status.toLowerCase()} · click to stop` : 'Click the core to speak'}</span></div>
        <div className="spatial-welcome"><span className="welcome-eyebrow">A LITTLE INTELLIGENCE. ENDLESS POSSIBILITY.</span><h1>What can I do for you <em>today?</em></h1><p>Your personal AI assistant. A little more focus, a little more flow.</p></div>
        <div className="spatial-command"><VoiceBar /><div className="spatial-quick-actions"><button disabled={!canRun} onClick={() => run('open VS Code')}><Code2 size={16} />Open VS Code</button><button onClick={() => setCurrentView('files')}><Search size={16} />Search files</button><button onClick={() => setCurrentView('vision')}><Monitor size={16} />My screen</button></div></div>
      </div>

      <aside className="spatial-column right-column">
        <section className="spatial-panel health-panel">
          <div className="spatial-panel-heading"><h2><Workflow size={19} strokeWidth={1.7} />System health</h2><button className="health-refresh" disabled={!canRun} onClick={() => request('SYSTEM_STATUS')} aria-label="Refresh system readings" title="Read current system status"><RefreshCw size={13} />{metrics ? 'Refresh' : 'Read host'}</button></div>
          <div className="health-gauges"><HealthGauge label="CPU" value={metrics?.cpu_percent} tone="violet" /><HealthGauge label="Memory" value={metrics?.memory_percent} tone="peach" /><HealthGauge label="Disk" value={metrics?.disk_percent} tone="pink" /></div>
          <button className="health-summary" onClick={() => setCurrentView('computer')}><span className="tile-icon green">{metrics ? <Leaf size={19} /> : <ShieldCheck size={19} />}</span><span><strong>{metrics ? 'Your host, at a glance' : 'Your computer. Your control.'}</strong><small>{metrics ? 'Last requested readings. Refresh for an update.' : isBackendConnected ? 'Read your host for current system information.' : 'System readings appear when connected.'}</small></span><ArrowRight size={14} /></button>
        </section>
        <section className="spatial-panel automations-panel">
          <PanelHeading icon={Zap} title="Automations" action="Explore" onClick={() => setCurrentView('automations')} />
          {currentTask && <button className="current-workflow" onClick={() => setCurrentView('automations')}><span className="status-dot connected" /><span>{currentTask.description || 'Current workflow'}</span><small>{currentTask.status}</small></button>}
          <div className="automation-ideas">{ideas.map(({ title, detail, command, icon: Icon, tone }) => <button key={title} disabled={!canRun} onClick={() => run(command)} className="automation-idea"><span className={`tile-icon ${tone}`}><Icon size={19} strokeWidth={1.6} /></span><span><strong>{title}</strong><small>{detail}</small></span><ArrowRight size={14} /></button>)}</div>
          <span className="automation-caption">Thoughtful starting points. Run when you choose.</span>
        </section>
      </aside>
    </div>

    <section className="spatial-panel memory-panel">
      <PanelHeading icon={BookOpen} title="Memory" action="See all" onClick={() => setCurrentView('memory')} />
      <div className="memory-content"><button className="memory-intro" onClick={() => setCurrentView('memory')}><span className="memory-art" aria-hidden="true"><i /><i /><i /><i /></span><span><strong>NOVA remembers.<br />So you can move forward.</strong><small>Your preferences, projects, and little details.<br />A little continuity for everything you do.</small></span></button><div className="memory-notes">{memories.length ? memories.slice(0, 3).map((memory, index) => <button className="memory-note" key={memory.id} onClick={() => setCurrentView('memory')}><span className={`tile-icon ${['peach', 'violet', 'pink'][index]}`}><BookOpen size={17} /></span><span>{memory.text}</span><small>{memory.category}</small></button>) : <button className="memory-empty" onClick={() => setCurrentView('memory')}><span className="tile-icon violet"><MessageSquare size={22} strokeWidth={1.5} /></span><span><strong>Good things are worth remembering.</strong><small>Add your first memory and make this space yours.</small></span><ArrowRight size={16} /></button>}</div></div>
    </section>
    <p className="spatial-availability"><span className={`status-dot ${isBackendConnected ? 'connected' : ''}`} />{isBackendConnected ? statusDetail || 'Connected to your Windows host' : 'Your Windows host is offline. Your memories, tools, and readings will appear when connected.'}</p>
  </section>;
}
