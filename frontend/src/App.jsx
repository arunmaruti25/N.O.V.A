import { useEffect } from "react";
import { AnimatePresence, motion, MotionConfig } from "framer-motion";
import { NovaProvider } from "./context/NovaContext";
import { useNova } from "./context/useNova";
import Header from "./components/Header";
import Sidebar from "./components/Sidebar";
import MiniNova from "./components/MiniNova";
import PermissionModal from "./components/PermissionModal";
import NotificationToast from "./components/NotificationToast";

import HomeView from "./views/HomeView";
import VisionView from "./views/VisionView";
import WebView from "./views/WebView";
import SkillsView from "./views/SkillsView";
import ComputerView from "./views/ComputerView";
import MemoryView from "./views/MemoryView";
import ActivityView from "./views/ActivityView";
import SettingsView from "./views/SettingsView";
import "./styles/nova.css";

function NovaMainApp() {
  const {
    currentView,
    isMiniMode,
    setIsMiniMode,
    triggerVoiceCommand,
    cancelOperation,
    permissionState,
    reducedMotion,
    errorMessage,
  } = useNova();

  // Global keyboard shortcuts
  useEffect(() => {
    function handleKeyDown(e) {
      // Ctrl + M to toggle mini mode
      if (e.ctrlKey && (e.key === "m" || e.key === "M")) {
        e.preventDefault();
        setIsMiniMode((prev) => !prev);
      }
      // Ctrl + Shift + N to trigger voice
      if (e.ctrlKey && e.shiftKey && (e.key === "n" || e.key === "N")) {
        e.preventDefault();
        triggerVoiceCommand();
      }
      // Esc to interrupt
      if (e.key === "Escape" && !permissionState.isOpen) {
        cancelOperation();
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [setIsMiniMode, triggerVoiceCommand, cancelOperation, permissionState.isOpen]);

  return (
    <MotionConfig reducedMotion={reducedMotion ? "always" : "user"}><div
      style={{
        width: "100vw",
        height: "100vh",
        display: "flex",
        flexDirection: "column",
        position: "relative",
        overflow: "hidden",
      }}
    >
      {/* Background ambient lighting */}
      <div className="nova-ambient-glow" />

      {/* Floating Minimized Mode */}
      <AnimatePresence>{isMiniMode && <MiniNova />}</AnimatePresence>

      {/* Full UI Layout (hidden or collapsed when in mini mode) */}
      {!isMiniMode && (
        <motion.div
          initial={{ opacity: 0, scale: 0.98 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.98 }}
          transition={{ duration: 0.25 }}
          style={{
            display: "flex",
            flexDirection: "column",
            width: "100%",
            height: "100%",
            position: "relative",
            zIndex: 1,
          }}
        >
          {/* Header Bar */}
          <Header />
          {errorMessage && currentView === "home" && <p role="alert" className="notice error">{errorMessage}</p>}

          {/* Main workspace (Sidebar + Active View) */}
          <div style={{ flex: 1, display: "flex", overflow: "hidden" }}>
            <Sidebar />

            <main
              style={{
                flex: 1,
                display: "flex",
                position: "relative",
                overflow: "hidden",
              }}
            >
              <AnimatePresence mode="wait">
                <motion.div
                  key={currentView}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -6 }}
                  transition={{ duration: 0.2, ease: "easeOut" }}
                  style={{
                    flex: 1,
                    display: "flex",
                    flexDirection: "column",
                    overflow: "hidden",
                  }}
                >
                  {currentView === "home" && <HomeView />}
                  {currentView === "vision" && <VisionView />}
                  {currentView === "web" && <WebView />}
                  {currentView === "skills" && <SkillsView />}
                  {currentView === "computer" && <ComputerView />}
                  {currentView === "memory" && <MemoryView />}
                  {currentView === "activity" && <ActivityView />}
                  {currentView === "settings" && <SettingsView />}
                </motion.div>
              </AnimatePresence>
            </main>
          </div>
        </motion.div>
      )}

      {/* Overlays */}
      <PermissionModal />
      <NotificationToast />
    </div>
    </MotionConfig>
  );
}

export default function App() {
  return (
    <NovaProvider>
      <NovaMainApp />
    </NovaProvider>
  );
}
