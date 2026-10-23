import { useEffect, useRef } from 'react';
import { ShieldCheck, X } from 'lucide-react';
import { useNova } from '../context/useNova';
export default function PermissionModal() {
 const { permissionState } = useNova();
 const { isOpen, title, description, detail, onConfirm, onCancel } = permissionState;
 const dialog = useRef(null);
 useEffect(() => {
  if (!isOpen) return;
  const previous = document.activeElement;
  dialog.current?.focus();
  const handler = e => {
   if(e.key === 'Escape') { e.preventDefault(); onCancel?.(); }
   if(e.key === 'Tab') {
    const buttons = dialog.current?.querySelectorAll('button');
    if(!buttons?.length) return;
    const first = buttons[0], last = buttons[buttons.length-1];
    if(e.shiftKey && (document.activeElement === first || document.activeElement === dialog.current)) { e.preventDefault(); last.focus(); }
    else if(!e.shiftKey && (document.activeElement === last || document.activeElement === dialog.current)) { e.preventDefault(); first.focus(); }
   }
  };
  document.addEventListener('keydown',handler);
  return () => { document.removeEventListener('keydown',handler); previous?.focus(); };
 },[isOpen,onCancel]);
 if(!isOpen) return null;
 return <div className="permission-backdrop" onClick={onCancel}><section ref={dialog} tabIndex={-1} role="dialog" aria-modal="true" aria-labelledby="perm-modal-title" className="permission-dialog glass-card" onClick={e => e.stopPropagation()}><div className="permission-heading"><ShieldCheck size={26} /><span>YOU’RE IN CONTROL</span><button className="icon-button" aria-label="Dismiss permission request" onClick={onCancel}><X size={18} /></button></div><h2 id="perm-modal-title">{title || 'A moment for your approval.'}</h2><p>{description}</p>{detail && <pre>{typeof detail === 'string' ? detail : JSON.stringify(detail,null,2)}</pre>}<div className="workspace-actions"><button className="btn-secondary" onClick={onCancel}>Cancel</button><button className="btn-primary" onClick={onConfirm}>Approve action</button></div></section></div>;
}
