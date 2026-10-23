import { motion, AnimatePresence } from 'framer-motion';
import { Info, CheckCircle2, AlertCircle, X } from 'lucide-react';
import { useNova } from '../context/useNova';
export default function NotificationToast() {
 const { notifications, removeNotification } = useNova();
 return <div className="toast-stack" aria-live="polite"><AnimatePresence>{notifications.map(n => { const Icon = n.type === 'success' ? CheckCircle2 : n.type === 'error' ? AlertCircle : Info; return <motion.div key={n.id} className="notification-toast glass-card" initial={{ opacity:0, x:20 }} animate={{ opacity:1,x:0 }} exit={{ opacity:0,x:20 }}><Icon size={18} /><div>{n.title && <strong>{n.title}</strong>}<p>{n.message || n.description}</p></div><button className="icon-button" onClick={() => removeNotification(n.id)} aria-label="Dismiss notification"><X size={15} /></button></motion.div>; })}</AnimatePresence></div>;
}
