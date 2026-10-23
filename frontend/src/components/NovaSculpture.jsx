import { useEffect, useMemo, useRef, useState } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { Environment, Lightformer, PerformanceMonitor } from '@react-three/drei';
import { BufferGeometry, Float32BufferAttribute, MathUtils, Vector3 } from 'three';
// A broad, softly rounded ribbon with a twisting oval cross section.
// Generated locally so the sculpture needs no model or texture downloads.
function createRibbon(segments) {
 const positions = [], indices = [];
 const sides = 12;
 const center = t => new Vector3(1.13 * Math.cos(t), 1.18 * Math.sin(t), .35 * Math.sin(2 * t));
 for (let i = 0; i <= segments; i++) {
  const t = i / segments * Math.PI * 2;
  const point = center(t);
  const tangent = center(t + .001).sub(point).normalize();
  const normal = new Vector3(Math.cos(t), Math.sin(t), 0).normalize();
  const binormal = new Vector3().crossVectors(tangent, normal).normalize();
  normal.crossVectors(binormal, tangent).normalize();
  const twist = t * 2 + .3;
  const width = .32 + .095 * Math.sin(t * 3);
  for (let j = 0; j <= sides; j++) {
   const a = j / sides * Math.PI * 2;
   const x = Math.cos(a) * width, y = Math.sin(a) * .075;
   const u = x * Math.cos(twist) - y * Math.sin(twist);
   const v = x * Math.sin(twist) + y * Math.cos(twist);
   positions.push(point.x + normal.x*u + binormal.x*v, point.y + normal.y*u + binormal.y*v, point.z + normal.z*u + binormal.z*v);
   if (i < segments && j < sides) {
    const n = i * (sides + 1) + j;
    indices.push(n, n+1, n+sides+1, n+1, n+sides+2, n+sides+1);
   }
  }
 }
 const geometry = new BufferGeometry();
 geometry.setAttribute('position', new Float32BufferAttribute(positions, 3));
 geometry.setIndex(indices);
 geometry.computeVertexNormals();
 return geometry;
}
function fluidMaterial(shader) {
 shader.uniforms.novaTime = { value: 0 };
 shader.vertexShader = 'uniform float novaTime;\n' + shader.vertexShader.replace('#include <begin_vertex>', '#include <begin_vertex>\n transformed += normal * sin(position.y * 3.0 + position.x * 2.0 + novaTime) * 0.035;');
 this.userData.novaShader = shader;
}
function Ribbons({ status, reduced, lowQuality }) {
 const group = useRef();
 const time = useRef(0);
 const geometry = useMemo(() => createRibbon(lowQuality ? 100 : 200), [lowQuality]);
 useEffect(() => () => geometry.dispose(), [geometry]);
 const active = ['THINKING','PROCESSING','EXECUTING','RECOVERING'].includes(status);
 useFrame(({ pointer }, delta) => {
  if (!group.current || reduced) return;
  const step = Math.min(delta, .05);
  time.current += step;
  const t = time.current;
  group.current.rotation.y = MathUtils.damp(group.current.rotation.y, pointer.x * .32 + Math.sin(t * .16) * .2, 3, step);
  group.current.rotation.x = MathUtils.damp(group.current.rotation.x, -.18 - pointer.y * .17, 3, step);
  group.current.rotation.z = MathUtils.damp(group.current.rotation.z, -.25 + (status === 'EXECUTING' ? .35 : Math.sin(t * .22) * .07), 3, step);
  group.current.position.y = Math.sin(t * .65) * .085;
  const pulse = status === 'SPEAKING' ? Math.sin(t*5)*.035 : status === 'LISTENING' ? .045 + Math.sin(t*2.5)*.028 : status === 'SUCCESS' ? .045 : Math.sin(t)*.012;
  group.current.scale.setScalar(1+pulse);
  group.current.children.forEach((child,i) => {
   if (i < 3) {
    child.rotation.z = i * 1.12 + Math.sin(t*(active ? .8 : .25)+i)*.15;
    if (child.material.userData.novaShader) child.material.userData.novaShader.uniforms.novaTime.value = t * (active ? 1.5 : .45);
    child.material.color.set(status === 'ERROR' ? '#dba5a1' : status === 'SUCCESS' ? '#c0d7c9' : i === 0 ? '#c8a4f2' : i === 1 ? '#ffcfad' : '#e9c2f1');
   }
  });
 });
 return <group ref={group} rotation={[-.18,.2,-.25]}>
  {[0,1,2].map(i => <mesh key={i} geometry={geometry} rotation={[i*.85+.3,i*.85,i*1.12]} scale={[1,1.08,.94]}><meshPhysicalMaterial onBeforeCompile={fluidMaterial} color={status === 'ERROR' ? '#dba5a1' : status === 'SUCCESS' ? '#c0d7c9' : i === 0 ? '#c8a4f2' : i === 1 ? '#ffcfad' : '#e9c2f1'} metalness={.2} roughness={.13} clearcoat={1} clearcoatRoughness={.08} iridescence={1} iridescenceIOR={1.4} iridescenceThicknessRange={[100,420]} transmission={lowQuality ? 0 : .28} thickness={.45} envMapIntensity={1.7} emissive={i === 1 ? '#e8a074' : '#ad7ede'} emissiveIntensity={.1} /></mesh>)}
  <mesh position={[1.85,.7,.1]} rotation={[.4,.5,.2]}><octahedronGeometry args={[.095,1]} /><meshStandardMaterial color="#d7c9b7" metalness={.9} roughness={.18} /></mesh>
  <mesh position={[-1.6,-.95,.3]}><sphereGeometry args={[.06,12,12]} /><meshStandardMaterial color="#9b89b0" metalness={.85} roughness={.2} /></mesh>
 </group>;
}
export default function NovaSculpture({ status, reduced, visible, eventSource }) {
 const [lowQuality,setLowQuality] = useState(() => (navigator.hardwareConcurrency || 4) <= 4);
 return <Canvas eventSource={eventSource} camera={{ position:[0,0,6.6], fov:38 }} dpr={lowQuality ? 1 : [1,1.5]} frameloop={!visible ? 'never' : reduced ? 'demand' : 'always'} gl={{ antialias:true, alpha:true, powerPreference:'low-power' }} fallback={<div className="core-fallback"><i /><i /><i /></div>}><ambientLight intensity={.7} /><directionalLight position={[3,5,4]} intensity={2.8} color="#fff6ee" /><directionalLight position={[-4,-2,2]} intensity={1.6} color="#cab9ff" /><Environment resolution={128}><Lightformer intensity={4} position={[0,4,-2]} scale={[10,4,1]} /><Lightformer intensity={3} position={[-4,1,3]} rotation={[0,Math.PI/3,0]} scale={[2,8,1]} /><Lightformer intensity={2} color="#f0c8b9" position={[4,-2,1]} scale={[3,6,1]} /></Environment><PerformanceMonitor onDecline={() => setLowQuality(true)} flipflops={1} onFallback={() => setLowQuality(true)} /><Ribbons status={status} reduced={reduced} lowQuality={lowQuality} /></Canvas>;
}
