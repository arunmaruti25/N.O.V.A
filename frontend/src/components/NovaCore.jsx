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
 const { status, reducedMotion, triggerVoiceCommand, cancelOperation, isListening, busy, statusDetail, isMiniMode } = useNova();
 const systemReduced = useReducedMotion();
 const surface = useRef(null);
 const [visible, setVisible] = useState(!document.hidden);
 useEffect(() => {
  let inViewport = true;
  const update = () => setVisible(!document.hidden && inViewport);
  const observer = new IntersectionObserver(([entry]) => { inViewport = entry.isIntersecting; update(); });
  observer.observe(surface.current);
  document.addEventListener('visibilitychange', update);
  return () => { observer.disconnect(); document.removeEventListener('visibilitychange', update); };
 }, []);
 const rendering = visible && !isMiniMode;
 const action = busy ? (isListening ? 'Finish speaking' : 'Stop operation') : 'Start listening';
 return <div ref={surface} className={`nova-core ${isMini ? 'mini-core' : ''}`} data-state={status.toLowerCase()} data-rendering={rendering && !isMini} style={{ width: size, maxWidth: '100%', aspectRatio: '1' }}>
  {isMini ? <Fallback /> : <CoreBoundary><Suspense fallback={<Fallback />}><Sculpture status={status} reduced={reducedMotion || systemReduced} visible={rendering} eventSource={surface} /></Suspense></CoreBoundary>}
  <button type="button" className="core-interaction" aria-label={`NOVA: ${action}`} aria-pressed={isListening} title={`${action} · ${statusDetail}`} onClick={onClick || (() => isListening ? triggerVoiceCommand() : busy ? cancelOperation() : triggerVoiceCommand())} />
  <span className="sr-only" role="status">{statusDetail}</span>
 </div>;
}
