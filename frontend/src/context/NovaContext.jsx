import { useState, useEffect, useCallback, useRef } from "react";
import { NovaContext } from "./context";
import { NOVA_STATES, AVAILABLE_MODELS } from "./constants";

export function NovaProvider({ children }) {
  const [status, setStatus] = useState(NOVA_STATES.IDLE);
  const [statusDetail, setStatusDetail] = useState("");
  const [errorMessage, setErrorMessage] = useState("");

  // View navigation
  const [currentView, setCurrentView] = useState("home");
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [isMiniMode, setIsMiniMode] = useState(false);

  // Model routing
  const [activeModel, setActiveModel] = useState(AVAILABLE_MODELS[0]);
  const [isAutoRouting, setIsAutoRouting] = useState(true);

  // Voice interaction state
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [waveformBars, setWaveformBars] = useState([
    0.15, 0.2, 0.25, 0.2, 0.15,
  ]);

  // Backend live WebSocket connection
  const [isBackendConnected, setIsBackendConnected] = useState(false);
  const wsRef = useRef(null);

  // Task Manager State (Pause / Resume / Cancel)
  const [currentTask, setCurrentTask] = useState(null);

  // Permission modal
  const [permissionState, setPermissionState] = useState({
    isOpen: false,
    title: "",
    description: "",
    severity: "danger", // danger | warning | standard
    detail: "",
    onConfirm: null,
    onCancel: null,
  });

  // Notifications
  const [notifications, setNotifications] = useState([
    {
      id: 1,
      type: "info",
      title: "NOVA Initialized",
      message: "Neural core online and calibrated for Windows environment.",
    },
  ]);

  // Recent Activity Log
  const [activities, setActivities] = useState([
    {
      id: 1,
      action: "Vision Perception",
      detail: "Analyzed desktop screen viewport",
      time: "3m ago",
      status: "success",
      type: "vision",
    },
    {
      id: 2,
      action: "Web Intelligence",
      detail: "Synthesized quantum computing breakthroughs",
      time: "12m ago",
      status: "success",
      type: "web",
    },
    {
      id: 3,
      action: "App Control",
      detail: "Launched Visual Studio Code",
      time: "35m ago",
      status: "success",
      type: "computer",
    },
    {
      id: 4,
      action: "Skill Activated",
      detail: "Mounted Browser Automation Extension",
      time: "1h ago",
      status: "success",
      type: "skills",
    },
  ]);

  // Reduced motion preference
  const [reducedMotion, setReducedMotion] = useState(false);

  const timerRef = useRef(null);

  // Clear timers on unmount
  useEffect(() => {
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, []);

  const addNotification = useCallback((notif) => {
    const id = Date.now() + Math.random();
    setNotifications((prev) => [...prev, { id, ...notif }]);
    if (notif.duration !== 0) {
      setTimeout(() => {
        setNotifications((prev) => prev.filter((item) => item.id !== id));
      }, notif.duration || 4500);
    }
  }, []);

  const removeNotification = useCallback((id) => {
    setNotifications((prev) => prev.filter((item) => item.id !== id));
  }, []);

  const addActivity = useCallback((act) => {
    setActivities((prev) => [
      {
        id: Date.now(),
        time: "Just now",
        status: "success",
        ...act,
      },
      ...prev.slice(0, 19),
    ]);
  }, []);

  // Method to request dangerous action confirmation
  const requestPermission = useCallback(
    ({
      title,
      description,
      severity = "danger",
      detail = "",
      onConfirm,
    }) => {
      return new Promise((resolve) => {
        setStatus(NOVA_STATES.CONFIRMATION);
        setStatusDetail("ACTION AUTHORIZATION REQUIRED");
        setPermissionState({
          isOpen: true,
          title,
          description,
          severity,
          detail,
          onConfirm: () => {
            setPermissionState((p) => ({ ...p, isOpen: false }));
            if (onConfirm) onConfirm();
            resolve(true);
          },
          onCancel: () => {
            setPermissionState((p) => ({ ...p, isOpen: false }));
            setStatus(NOVA_STATES.IDLE);
            setStatusDetail("Operation declined by user");
            addNotification({
              type: "info",
              title: "Authorization Declined",
              message: `Cancelled: ${title}`,
            });
            resolve(false);
          },
        });
      });
    },
    [addNotification],
  );

  // Live WebSocket connector with automatic reconnect and fallback
  useEffect(() => {
    let socket = null;
    let reconnectTimeout = null;

    function connectWs() {
      try {
        socket = new WebSocket("ws://127.0.0.1:8000/ws/nova");
        wsRef.current = socket;

        socket.onopen = () => {
          setIsBackendConnected(true);
        };

        socket.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            const { type, payload } = data;

            if (type === "STATE_CHANGE") {
              if (payload.status) {
                setStatus(payload.status);
                setIsListening(payload.status === NOVA_STATES.LISTENING);
              }
              if (payload.detail !== undefined) setStatusDetail(payload.detail);
            } else if (type === "TRANSCRIPT") {
              if (payload.text) setTranscript(payload.text);
            } else if (type === "NOTIFICATION") {
              addNotification(payload);
            } else if (type === "SPEECH_FINISHED" || type === "INTERRUPTED") {
              setIsListening(false);
              setStatus(NOVA_STATES.IDLE);
              if (payload.detail) setStatusDetail(payload.detail);
            } else if (type === "ASSISTANT_RESPONSE") {
              if (payload.text) setTranscript(payload.text);
              if (payload.model) {
                const matched = AVAILABLE_MODELS.find(
                  (m) => m.provider.toLowerCase() === String(payload.model).toLowerCase(),
                );
                if (matched) setActiveModel(matched);
              }
            } else if (type === "MODEL_INFO") {
              if (payload.provider) {
                const matched = AVAILABLE_MODELS.find(
                  (m) => m.provider.toLowerCase() === String(payload.provider).toLowerCase(),
                );
                if (matched) setActiveModel(matched);
              }
            } else if (type === "PERMISSION_REQUEST") {
              requestPermission({
                title: payload.title,
                description: payload.description,
                detail: payload.detail,
                severity: "danger",
                onConfirm: () => {
                  if (socket && socket.readyState === WebSocket.OPEN) {
                    socket.send(
                      JSON.stringify({
                        type: "PERMISSION_DECISION",
                        payload: { action: payload.action, authorized: true },
                      }),
                    );
                  }
                },
              });
            } else if (type === "ACTIVITY_LOG") {
              addActivity(payload);
            } else if (type === "TASK_CREATED" || type === "TASK_STARTED") {
              setCurrentTask((prev) => ({ ...prev, ...payload, status: "RUNNING" }));
            } else if (type === "TASK_STEP") {
              setCurrentTask((prev) => ({ ...prev, ...payload, status: "RUNNING" }));
            } else if (type === "TASK_PAUSED") {
              setCurrentTask((prev) => ({ ...prev, ...payload, status: "PAUSED" }));
              setStatus(NOVA_STATES.PAUSED);
              setStatusDetail(payload.description || "Task Paused");
              addNotification({
                type: "info",
                title: "Task Paused",
                message: payload.description || "Task paused. Ready for new input.",
              });
            } else if (type === "TASK_RESUMED") {
              setCurrentTask((prev) => ({ ...prev, ...payload, status: "RUNNING" }));
              setStatus(NOVA_STATES.EXECUTING);
              setStatusDetail(payload.description || "Resuming task...");
              addNotification({
                type: "info",
                title: "Task Resumed",
                message: payload.description || "Resuming task execution.",
              });
            } else if (type === "TASK_CANCELLED") {
              setCurrentTask((prev) => ({ ...prev, ...payload, status: "CANCELLED" }));
              setStatus(NOVA_STATES.IDLE);
              setStatusDetail("Task cancelled");
              addNotification({
                type: "info",
                title: "Task Cancelled",
                message: payload.description || "Task execution cancelled.",
              });
            } else if (type === "TASK_COMPLETED") {
              setCurrentTask((prev) => ({ ...prev, ...payload, status: "COMPLETED" }));
              addNotification({
                type: "success",
                title: "Task Completed",
                message: payload.description || "Task completed successfully.",
              });
            } else if (type === "TASK_FAILED") {
              setCurrentTask((prev) => ({ ...prev, ...payload, status: "FAILED" }));
              setStatus(NOVA_STATES.ERROR);
              setStatusDetail(payload.error || "Task failed");
            } else if (type === "ERROR") {
              setIsListening(false);
              setStatus(NOVA_STATES.ERROR);
              setStatusDetail(payload.message || "Backend Error");
            }
          } catch {
            // ignore non-json
          }
        };

        socket.onclose = () => {
          setIsBackendConnected(false);
          reconnectTimeout = setTimeout(connectWs, 3500);
        };

        socket.onerror = () => {
          setIsBackendConnected(false);
        };
      } catch {
        setIsBackendConnected(false);
        reconnectTimeout = setTimeout(connectWs, 3500);
      }
    }

    connectWs();

    return () => {
      if (reconnectTimeout) clearTimeout(reconnectTimeout);
      if (socket) socket.close();
    };
  }, [addActivity, addNotification, requestPermission]);

  // Audio wave simulator for listening / speaking
  useEffect(() => {
    if (status !== NOVA_STATES.LISTENING && status !== NOVA_STATES.SPEAKING) {
      return;
    }
    const interval = setInterval(() => {
      setWaveformBars([
        0.2 + Math.random() * 0.7,
        0.3 + Math.random() * 0.65,
        0.4 + Math.random() * 0.6,
        0.3 + Math.random() * 0.68,
        0.2 + Math.random() * 0.6,
      ]);
    }, 90);
    return () => {
      clearInterval(interval);
      setWaveformBars([0.15, 0.2, 0.25, 0.2, 0.15]);
    };
  }, [status]);

  // Method to trigger voice command execution flow (real backend with mock fallback)
  const triggerVoiceCommand = useCallback(
    (cmdText) => {
      if (timerRef.current) clearTimeout(timerRef.current);

      // 1. If backend WebSocket is live, send real event
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        if (!cmdText) {
          // Trigger real microphone recording on backend
          setIsListening(true);
          setStatus(NOVA_STATES.LISTENING);
          setStatusDetail("LISTENING... SPEAK NOW");
          setTranscript("");

          wsRef.current.send(
            JSON.stringify({
              type: "START_LISTENING",
              payload: {
                model: activeModel.provider,
              },
            }),
          );
          return;
        }

        // Direct typed or chip command
        setIsListening(false);
        setStatus(NOVA_STATES.PROCESSING);
        setStatusDetail("PROCESSING COMMAND...");
        setTranscript(cmdText);

        wsRef.current.send(
          JSON.stringify({
            type: "USER_INPUT",
            payload: {
              text: cmdText,
              model: activeModel.provider,
            },
          }),
        );
        return;
      }

      // 2. Otherwise graceful client fallback
      setIsListening(true);
      setStatus(NOVA_STATES.LISTENING);
      setStatusDetail("LISTENING TO VOICE...");
      setTranscript("");

      const words = cmdText.split(" ");
      let currentIdx = 0;
      const textInterval = setInterval(() => {
        if (currentIdx < words.length) {
          setTranscript(words.slice(0, currentIdx + 1).join(" "));
          currentIdx++;
        } else {
          clearInterval(textInterval);

          setIsListening(false);
          setStatus(NOVA_STATES.PROCESSING);
          setStatusDetail("PARSING SEMANTIC INTENT...");

          timerRef.current = setTimeout(() => {
            setStatus(NOVA_STATES.THINKING);
            setStatusDetail("FORMULATING PLAN...");

            if (
              cmdText.toLowerCase().includes("screen") ||
              cmdText.toLowerCase().includes("what")
            ) {
              setActiveModel(AVAILABLE_MODELS[0]);
            } else if (
              cmdText.toLowerCase().includes("code") ||
              cmdText.toLowerCase().includes("script")
            ) {
              setActiveModel(AVAILABLE_MODELS[2]);
            } else if (
              cmdText.toLowerCase().includes("shut down") ||
              cmdText.toLowerCase().includes("delete")
            ) {
              setActiveModel(AVAILABLE_MODELS[3]);
            } else {
              setActiveModel(AVAILABLE_MODELS[1]);
            }

            timerRef.current = setTimeout(() => {
              if (
                cmdText.toLowerCase().includes("shut down") ||
                cmdText.toLowerCase().includes("delete")
              ) {
                requestPermission({
                  title: cmdText.toLowerCase().includes("shut down")
                    ? "System Power Action"
                    : "File System Deletion",
                  description: cmdText.toLowerCase().includes("shut down")
                    ? "NOVA requested permission to power down the host Windows workstation."
                    : "NOVA requested permission to remove requested directory and its contents.",
                  severity: "danger",
                  detail: cmdText.toLowerCase().includes("shut down")
                    ? "C:\\Windows\\System32\\shutdown.exe /s /t 0"
                    : "D:\\Projects\\TempCache\\*",
                  onConfirm: () => {
                    setStatus(NOVA_STATES.EXECUTING);
                    setStatusDetail(`EXECUTING: ${cmdText.toUpperCase()}`);
                    addActivity({
                      action: "System Execution",
                      detail: cmdText,
                      type: "computer",
                    });

                    setTimeout(() => {
                      setStatus(NOVA_STATES.SUCCESS);
                      setStatusDetail("COMMAND COMPLETED");
                      setTimeout(() => {
                        setStatus(NOVA_STATES.IDLE);
                        setStatusDetail("");
                        setTranscript("");
                      }, 2200);
                    }, 1800);
                  },
                });
              } else {
                setStatus(NOVA_STATES.EXECUTING);
                setStatusDetail(`EXECUTING: ${cmdText.toUpperCase()}`);
                addActivity({
                  action: cmdText.toLowerCase().includes("screen")
                    ? "Vision Capture"
                    : cmdText.toLowerCase().includes("search")
                      ? "Web Research"
                      : "System Command",
                  detail: cmdText,
                  type: cmdText.toLowerCase().includes("screen")
                    ? "vision"
                    : cmdText.toLowerCase().includes("search")
                      ? "web"
                      : "computer",
                });

                timerRef.current = setTimeout(() => {
                  setStatus(NOVA_STATES.SPEAKING);
                  setStatusDetail("RESPONDING");
                  setTranscript(
                    cmdText.toLowerCase().includes("screen")
                      ? "I analyzed your active workspace: IDE open with clean file structure."
                      : cmdText.toLowerCase().includes("chrome")
                        ? "Google Chrome launched successfully in your primary monitor."
                        : cmdText.toLowerCase().includes("volume")
                          ? "Windows audio output adjusted."
                          : `Completed request for: "${cmdText}".`,
                  );

                  timerRef.current = setTimeout(() => {
                    setStatus(NOVA_STATES.SUCCESS);
                    setStatusDetail("DONE");

                    timerRef.current = setTimeout(() => {
                      setStatus(NOVA_STATES.IDLE);
                      setStatusDetail("");
                      setTranscript("");
                    }, 1500);
                  }, 3000);
                }, 1800);
              }
            }, 1400);
          }, 1100);
        }
      }, 180);
    },
    [activeModel.provider, addActivity, requestPermission],
  );

  // Cancel any active operation and return to IDLE
  const cancelOperation = useCallback(() => {
    if (timerRef.current) clearTimeout(timerRef.current);
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(
        JSON.stringify({
          type: "INTERRUPT",
          payload: {},
        }),
      );
    }
    setIsListening(false);
    setStatus(NOVA_STATES.IDLE);
    setStatusDetail("");
    setPermissionState((p) => ({ ...p, isOpen: false }));
    addNotification({
      type: "info",
      title: "Operation Cancelled",
      message: "Returned to idle state.",
    });
  }, [addNotification]);

  // Task Manager controls (Pause / Resume / Cancel)
  const pauseTask = useCallback((taskId) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(
        JSON.stringify({
          type: "TASK_PAUSE",
          payload: { task_id: taskId },
        }),
      );
    }
  }, []);

  const resumeTask = useCallback((taskId) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(
        JSON.stringify({
          type: "TASK_RESUME",
          payload: { task_id: taskId },
        }),
      );
    }
  }, []);

  const cancelTask = useCallback((taskId) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(
        JSON.stringify({
          type: "TASK_CANCEL",
          payload: { task_id: taskId },
        }),
      );
    }
  }, []);

  return (
    <NovaContext.Provider
      value={{
        status,
        setStatus,
        statusDetail,
        setStatusDetail,
        errorMessage,
        setErrorMessage,
        currentView,
        setCurrentView,
        sidebarCollapsed,
        setSidebarCollapsed,
        isMiniMode,
        setIsMiniMode,
        activeModel,
        setActiveModel,
        isAutoRouting,
        setIsAutoRouting,
        availableModels: AVAILABLE_MODELS,
        isListening,
        setIsListening,
        transcript,
        setTranscript,
        waveformBars,
        permissionState,
        requestPermission,
        notifications,
        addNotification,
        removeNotification,
        activities,
        addActivity,
        reducedMotion,
        setReducedMotion,
        triggerVoiceCommand,
        cancelOperation,
        isBackendConnected,
        currentTask,
        pauseTask,
        resumeTask,
        cancelTask,
      }}
    >
      {children}
    </NovaContext.Provider>
  );
}
