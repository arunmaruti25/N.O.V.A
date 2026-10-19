import { useState, useEffect, useCallback, useRef } from "react";
import { NovaContext } from "./context";
import { AVAILABLE_MODELS } from "./constants";

function stored(key, fallback) {
  try { return JSON.parse(localStorage.getItem(`nova.${key}`)) ?? fallback; }
  catch { return fallback; }
}
function usePreference(key, fallback) {
  const [value, setValue] = useState(() => stored(key, fallback));
  useEffect(() => { localStorage.setItem(`nova.${key}`, JSON.stringify(value)); }, [key, value]);
  return [value, setValue];
}

export function NovaProvider({ children }) {
  const [status, setStatus] = useState("OFFLINE");
  const [statusDetail, setStatusDetail] = useState("Connecting to backend");
  const [errorMessage, setErrorMessage] = useState("");
  const [currentView, setCurrentView] = useState("home");
  const [sidebarCollapsed, setSidebarCollapsed] = usePreference("sidebarCollapsed", false);
  const [isMiniMode, setIsMiniMode] = useState(false);
  const [activeModel, setActiveModel] = usePreference("model", AVAILABLE_MODELS[0]);
  const [isAutoRouting, setIsAutoRouting] = usePreference("autoRouting", true);
  const [speechEnabled, setSpeechEnabled] = usePreference("speechEnabled", false);
  const [reducedMotion, setReducedMotion] = usePreference("reducedMotion", false);
  const [transcript, setTranscript] = useState("");
  const [isBackendConnected, setIsBackendConnected] = useState(false);
  const [currentTask, setCurrentTask] = useState(null);
  const [permissionState, setPermissionState] = useState({ isOpen: false });
  const [notifications, setNotifications] = useState([]);
  const [activities, setActivities] = useState([]);
  const [memories, setMemories] = useState([]);
  const [tools, setTools] = useState([]);
  const [modelConfig, setModelConfig] = useState([]);
  const [systemStatus, setSystemStatus] = useState(null);
  const [webResult, setWebResult] = useState(null);
  const [visionResult, setVisionResult] = useState(null);
  const wsRef = useRef(null);
  const toastTimers = useRef(new Set());
  const addNotification = useCallback((item) => {
    const id = crypto.randomUUID();
    setNotifications((prev) => [...prev.slice(-4), { ...item, id }]);
    const timer = setTimeout(() => {
      setNotifications((prev) => prev.filter((n) => n.id !== id));
      toastTimers.current.delete(timer);
    }, item.duration || 6000);
    toastTimers.current.add(timer);
  }, []);
  const removeNotification = useCallback((id) => setNotifications((prev) => prev.filter((n) => n.id !== id)), []);
  const addActivity = useCallback((item) => setActivities((prev) => [{ ...item, id: crypto.randomUUID(), time: new Date().toLocaleTimeString() }, ...prev].slice(0, 200)), []);
  const send = useCallback((type, payload = {}) => {
    if (wsRef.current?.readyState !== WebSocket.OPEN) {
      setStatus("OFFLINE");
      setErrorMessage("Backend disconnected. Start the NOVA server and try again.");
      setStatusDetail("Backend disconnected");
      return false;
    }
    setErrorMessage("");
    wsRef.current.send(JSON.stringify({ type, payload }));
    return true;
  }, []);
  useEffect(() => {
    let disposed = false;
    let reconnectTimer;
    let socket;
    const timers = toastTimers.current;
    function connect() {
      if (disposed) return;
      const protocol = location.protocol === "https:" ? "wss:" : "ws:";
      const host = import.meta.env.VITE_BACKEND_URL || `${protocol}//${location.port === "5173" ? `${location.hostname}:8000` : location.host}`;
      socket = new WebSocket(`${host.replace(/\/$/, "")}/ws/nova`);
      wsRef.current = socket;
      socket.onopen = () => { if (!disposed) setIsBackendConnected(true); };
      socket.onmessage = ({ data }) => {
        if (disposed) return;
        let message;
        try { message = JSON.parse(data); } catch { return; }
        const { type, payload: p = {} } = message;
        if (type === "STATE_CHANGE") { setStatus(p.status); setStatusDetail(p.detail || ""); }
        else if (type === "TRANSCRIPT" || type === "ASSISTANT_RESPONSE") setTranscript(p.text || "");
        else if (type === "MEMORY_SYNC") setMemories(p.memories || []);
        else if (type === "SKILLS_SYNC") setTools(p.tools || []);
        else if (type === "MODEL_CONFIG") setModelConfig(p.models || []);
        else if (type === "SYSTEM_STATUS") setSystemStatus(p);
        else if (type === "WEB_RESULT") setWebResult(p);
        else if (type === "VISION_RESULT") setVisionResult(p);
        else if (type === "NOTIFICATION") addNotification(p);
        else if (type === "ACTIVITY_LOG") addActivity(p);
        else if (type === "ERROR") { setStatus("ERROR"); setStatusDetail(p.message); setErrorMessage(p.message); }
        else if (type === "PERMISSION_REQUEST") {
          const decide = (authorized) => {
            send("PERMISSION_DECISION", { approval_id: p.approval_id, authorized });
            setPermissionState({ isOpen: false });
          };
          setPermissionState({ ...p, isOpen: true, onConfirm: () => decide(true), onCancel: () => decide(false) });
        } else if (type.startsWith("TASK_")) {
          const states = { TASK_CREATED: "RUNNING", TASK_STARTED: "RUNNING", TASK_STEP: "RUNNING", TASK_PAUSED: "PAUSED", TASK_COMPLETED: "COMPLETED", TASK_CANCELLED: "CANCELLED", TASK_FAILED: "FAILED" };
          if (states[type]) setCurrentTask((prev) => ({ ...prev, ...p, status: states[type] }));
          if (type === "TASK_PAUSED") setStatus("PAUSED");
          if (type === "TASK_CANCELLED") { setStatus("IDLE"); setPermissionState({ isOpen: false }); }
        }
      };
      socket.onclose = () => {
        if (disposed) return;
        setIsBackendConnected(false); setStatus("OFFLINE"); setStatusDetail("Backend disconnected; reconnecting");
        setPermissionState({ isOpen: false }); setCurrentTask(null);
        reconnectTimer = setTimeout(connect, 2500);
      };
      socket.onerror = () => socket.close();
    }
    connect();
    return () => {
      disposed = true; clearTimeout(reconnectTimer);
      for (const timer of timers) clearTimeout(timer);
      socket?.close(); wsRef.current = null;
    };
  }, [send, addActivity, addNotification]);
  const request = useCallback((type, payload = {}) => {
    const sent = send(type, { model: isAutoRouting ? "auto" : activeModel.provider, speech_enabled: speechEnabled, ...payload });
    if (sent) { setStatus("PROCESSING"); setStatusDetail("Working on your request"); }
    return sent;
  }, [send, activeModel.provider, isAutoRouting, speechEnabled]);
  const triggerVoiceCommand = useCallback((text) => {
    if (text?.trim()) {
      const command = text.trim();
      if (/^(?:nova[, ]+)?(?:stop|cancel)(?: task)?[.!]?$/i.test(command)) return send("INTERRUPT");
      if (/^(?:nova[, ]+)?pause(?: task)?[.!]?$/i.test(command)) return send("TASK_PAUSE");
      if (/^(?:nova[, ]+)?resume(?: task)?[.!]?$/i.test(command)) return request("TASK_RESUME");
      if (request("USER_INPUT", { text: command })) setTranscript(command);
    } else request("START_LISTENING");
  }, [request, send]);
  const cancelOperation = useCallback(() => { send("INTERRUPT"); setPermissionState({ isOpen: false }); }, [send]);
  const pauseTask = useCallback((task_id) => send("TASK_PAUSE", { task_id }), [send]);
  const resumeTask = useCallback((task_id) => request("TASK_RESUME", { task_id }), [request]);
  const cancelTask = useCallback((task_id) => send("TASK_CANCEL", { task_id }), [send]);
  const busy = ["PROCESSING", "THINKING", "EXECUTING", "RECOVERING", "SPEAKING", "LISTENING", "CONFIRMATION"].includes(status);
  const availableModels = AVAILABLE_MODELS.map((m) => ({ ...m, ...modelConfig.find((c) => c.provider === m.provider) }));
  return <NovaContext.Provider value={{
    status, setStatus, statusDetail, setStatusDetail, errorMessage, setErrorMessage,
    currentView, setCurrentView, sidebarCollapsed, setSidebarCollapsed, isMiniMode, setIsMiniMode,
    activeModel, setActiveModel, isAutoRouting, setIsAutoRouting, availableModels,
    speechEnabled, setSpeechEnabled, reducedMotion, setReducedMotion,
    isListening: status === "LISTENING", transcript, setTranscript, waveformBars: [0.2, 0.4, 0.7, 0.4, 0.2],
    permissionState, notifications, addNotification, removeNotification, activities, addActivity,
    triggerVoiceCommand, cancelOperation, isBackendConnected, currentTask, pauseTask, resumeTask, cancelTask,
    request, send, busy, memories, tools, systemStatus, webResult, visionResult,
  }}>{children}</NovaContext.Provider>;
}
