import { Component, lazy, Suspense, useEffect, useState } from 'react';
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
 const [visible, setVisible] = useState(!document.hidden);
 useEffect(() => { const update = () => setVisible(!document.hidden); document.addEventListener('visibilitychange', update); return () => document.removeEventListener('visibilitychange', update); }, []);
 return <div className={`nova-core ${isMini ? 'mini-core' : ''}`} style={{ width: size, maxWidth: '100%', aspectRatio: '1' }}><CoreBoundary><Suspense fallback={<Fallback />}><Sculpture status={status} reduced={reducedMotion || systemReduced} visible={visible} /></Suspense></CoreBoundary><button className="core-interaction" aria-label={`NOVA is ${status.toLowerCase()}. ${busy ? 'Stop operation' : 'Start listening'}`} title={statusDetail} onClick={onClick || (() => busy ? cancelOperation() : triggerVoiceCommand())} /><span className="sr-only" role="status">{statusDetail}</span></div>;
}
