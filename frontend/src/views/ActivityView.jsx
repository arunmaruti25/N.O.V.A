import { History, CheckCircle2, CircleAlert, ArrowUpRight } from 'lucide-react';
import { useNova } from '../context/useNova';
import WorkspacePage from '../components/WorkspacePage';
export default function ActivityView() {
 const { activities, setCurrentView } = useNova();
 return <WorkspacePage title="A little clarity on everything." description="Your activity, exactly as it happened. Tool events and outcomes reported by your connected host.">{activities.length ? <div className="activity-timeline">{activities.map(a => { const failed = a.status === 'error' || a.result === 'failed'; const confirmed = a.verified || a.status === 'success' || a.result === 'success'; return <article className="activity-entry" key={a.id}><span className={`activity-icon ${failed ? 'failed' : ''}`}>{failed ? <CircleAlert size={18} /> : confirmed ? <CheckCircle2 size={18} /> : <History size={18} />}</span><div><h2>{a.action}</h2><p>{a.detail}</p></div><span className="badge">{failed ? 'Failed' : a.verified ? 'Verified' : confirmed ? 'Completed' : 'Recorded'}</span><time>{a.time}</time></article>; })}</div> : <div className="empty-state"><History size={30} /><h2>A fresh start.</h2><p>Your host activity will appear here as you use NOVA.</p><button className="text-link" onClick={() => setCurrentView('chat')}>Start a conversation <ArrowUpRight size={15} /></button></div>}</WorkspacePage>;
}
