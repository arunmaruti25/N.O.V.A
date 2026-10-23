import { Component, lazy, Suspense, useEffect, useRef, useState } from 'react';
import { useReducedMotion } from 'framer-motion';
import { useNova } from '../context/useNova';
const Sculpture = lazy(() => import('./NovaSculpture'));
function Fallback() { return <div className="core-fallback" aria-hidden="true"><i /><i /><i /><i /></div>; }
class CoreBoundary extends Component {
 state = { failed: false };
 static getDerivedStateFromError() { return { failed: true }; }
 render() { return this.state.failed ? <Fallback /> : this.props.children; }
}
export default function NovaCore({ size = 380, isMini = false, onClick }) {
 const { status, reducedMotion, triggerVoiceCommand, cancelOperation, busy, statusDetail } = useNova();
 const systemReduced = useReducedMotion();
 const surface = useRef(null);
 const [visible, setVisible] = useState(!document.hidden);
 useEffect(() => { const update = () => setVisible(!document.hidden); document.addEventListener('visibilitychange', update); return () => document.removeEventListener('visibilitychange', update); }, []);
 const action = busy ? (status === 'LISTENING' ? 'Stop listening' : 'Stop operation') : 'Start listening';
 return <div ref={surface} className={`nova-core ${isMini ? 'mini-core' : ''}`} data-state={status.toLowerCase()} style={{ width: size, maxWidth: '100%', aspectRatio: '1' }}>
  <CoreBoundary><Suspense fallback={<Fallback />}><Sculpture status={status} reduced={reducedMotion || systemReduced} visible={visible} eventSource={surface} /></Suspense></CoreBoundary>
  <button type="button" className="core-interaction" aria-label={`NOVA: ${action}`} aria-pressed={status === 'LISTENING'} title={`${action} · ${statusDetail}`} onClick={onClick || (() => busy ? cancelOperation() : triggerVoiceCommand())} />
  <span className="sr-only" role="status">{statusDetail}</span>
 </div>;
}
