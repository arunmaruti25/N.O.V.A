import { useContext } from "react";
import { NovaContext } from "./context";

export function useNova() {
  const ctx = useContext(NovaContext);
  if (!ctx) throw new Error("useNova must be used within a NovaProvider");
  return ctx;
}
