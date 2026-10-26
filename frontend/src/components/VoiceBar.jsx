import { useState } from 'react';
import { ArrowUp, Mic, Square, Pause, Play, Sparkles } from 'lucide-react';
import { useNova } from '../context/useNova';
export default function VoiceBar({ showResponse = true, active = true }) {
 const { transcript, triggerVoiceCommand, cancelOperation, isListening, currentTask, pauseTask, resumeTask, cancelTask, busy, isBackendConnected, errorMessage } = useNova();
 const [value, setValue] = useState('');
 const submit = e => { e.preventDefault(); if (value.trim() && triggerVoiceCommand(value)) setValue(''); };
 return <div className="voice-bar-wrap">
  {showResponse && transcript && <div className="inline-response" aria-live="polite"><Sparkles size={17} /><p>{transcript}</p></div>}
  <form className={`command-surface ${isListening ? 'listening' : ''}`} onSubmit={submit}><span className="command-symbol" aria-hidden="true"><Sparkles size={23} /></span><input id={active ? 'universal-command' : undefined} aria-label="Ask NOVA" placeholder={isListening ? 'Listening on your Windows host…' : 'Ask NOVA anything or give a command...'} value={value} onChange={e => setValue(e.target.value)} /><span className="input-separator" /><button type="button" className="icon-button" aria-label={isListening ? 'Finish speaking' : busy ? 'Stop operation' : 'Start listening'} onClick={() => isListening ? triggerVoiceCommand() : busy ? cancelOperation() : triggerVoiceCommand()}>{busy ? <Square size={17} /> : <Mic size={19} />}</button><button className="send-button" disabled={!value.trim() || busy || !isBackendConnected} aria-label="Send command"><ArrowUp size={21} /></button></form>
  {errorMessage && <p className="notice error" role="alert">{errorMessage}</p>}
  {currentTask && <div className="task-inline"><span>{currentTask.goal || 'Current task'} · {currentTask.status}</span>{currentTask.status === 'PAUSED' ? <button className="icon-button" aria-label="Resume task" onClick={() => resumeTask(currentTask.task_id)}><Play size={15} /></button> : currentTask.status === 'RUNNING' ? <button className="icon-button" aria-label="Pause task" onClick={() => pauseTask(currentTask.task_id)}><Pause size={15} /></button> : null}{['RUNNING','PAUSED'].includes(currentTask.status) && <button className="icon-button" aria-label="Cancel task" onClick={() => cancelTask(currentTask.task_id)}><Square size={15} /></button>}</div>}
 </div>;
}
