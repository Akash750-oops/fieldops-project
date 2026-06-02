/**
 * CountdownTimer.tsx
 * Visual countdown badge with color-coded urgency, pulse animations,
 * ARIA live region for accessibility, and a warning toast banner.
 */
import React, { useState, useEffect, useRef } from "react";
import { Clock, AlertTriangle } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import useCountdown from "../../hooks/useCountdown";
import type { CountdownTimerProps, UrgencyLevel } from "../../types/notifications";
// @ts-ignore
import "./notifications.css";

const pad = (n: number) => String(n).padStart(2, "0");

/** How often the ARIA live region updates (seconds) per urgency level */
const ANNOUNCE_INTERVALS: Record<UrgencyLevel, number> = {
  safe: 30,
  caution: 10,
  warning: 5,
  critical: 5,
};

export const CountdownTimer: React.FC<CountdownTimerProps> = ({
  expiresAt,
  onExpire,
  onWarning,
  jobId,
  hidden = false,
}) => {
  const { minutes, seconds, totalSeconds, isExpired, urgencyLevel } = useCountdown({
    expiresAt,
    onExpire,
    onWarning,
  });

  // Warning toast visibility
  const [showWarningToast, setShowWarningToast] = useState(false);
  const prevUrgencyRef = useRef<UrgencyLevel>(urgencyLevel);

  // Show warning toast when transitioning into "caution" from "safe"
  useEffect(() => {
    if (urgencyLevel === "caution" && prevUrgencyRef.current === "safe") {
      setShowWarningToast(true);
      const id = setTimeout(() => setShowWarningToast(false), 5000);
      return () => clearTimeout(id);
    }
    prevUrgencyRef.current = urgencyLevel;
  }, [urgencyLevel]);

  // ARIA live region — throttled announcements
  const [ariaText, setAriaText] = useState("");
  const lastAnnounceRef = useRef(0);

  useEffect(() => {
    const now = Date.now();
    const interval = ANNOUNCE_INTERVALS[urgencyLevel] * 1000;

    if (now - lastAnnounceRef.current >= interval) {
      lastAnnounceRef.current = now;
      if (isExpired) {
        setAriaText("Timer expired. Please respond immediately.");
      } else {
        setAriaText(`${minutes} minutes and ${seconds} seconds remaining.`);
      }
    }
  }, [totalSeconds, minutes, seconds, isExpired, urgencyLevel]);

  if (hidden || (isExpired && totalSeconds < -5)) return null;

  const pulseClass =
    urgencyLevel === "critical"
      ? "countdown-pulse-fast"
      : urgencyLevel === "warning"
        ? "countdown-pulse-slow"
        : "";

  return (
    <>
      {/* Screen reader announcements */}
      <div className="sr-only" aria-live="polite" aria-atomic="true" data-testid="countdown-aria">
        {ariaText}
      </div>

      {/* Timer badge */}
      <motion.div
        className={`countdown-timer countdown-${urgencyLevel} ${pulseClass}`}
        data-testid="countdown-timer"
        data-urgency={urgencyLevel}
        initial={{ opacity: 0, scale: 0.95 }}
        animate={{ opacity: 1, scale: 1 }}
        role="timer"
        aria-label={`${pad(minutes)}:${pad(seconds)} remaining for job ${jobId}`}
      >
        <Clock size={16} aria-hidden="true" />
        <span className="countdown-digits" data-testid="countdown-digits">
          {isExpired ? "00:00" : `${pad(minutes)}:${pad(seconds)}`}
        </span>
        <span className="countdown-label">
          {isExpired ? "Expired" : "remaining"}
        </span>
      </motion.div>

      {/* Warning toast banner */}
      <AnimatePresence>
        {showWarningToast && (
          <motion.div
            className="countdown-warning-toast"
            data-testid="countdown-warning-toast"
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            role="alert"
          >
            <AlertTriangle size={14} />
            <span>⏰ Only 2 minutes remaining to respond!</span>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
};

export default CountdownTimer;
