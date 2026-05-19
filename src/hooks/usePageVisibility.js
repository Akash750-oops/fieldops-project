/**
 * usePageVisibility.js
 * Tracks whether the browser tab is currently active.
 * Returns true when visible, false when hidden.
 * Cleans up the event listener on unmount.
 */
import { useState, useEffect } from "react";

export default function usePageVisibility() {
  const [isVisible, setIsVisible] = useState(
    typeof document !== "undefined"
      ? document.visibilityState === "visible"
      : true
  );

  useEffect(() => {
    const handler = () => {
      setIsVisible(document.visibilityState === "visible");
    };
    document.addEventListener("visibilitychange", handler);
    return () => document.removeEventListener("visibilitychange", handler);
  }, []);

  return isVisible;
}
