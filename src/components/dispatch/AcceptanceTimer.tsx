/**
 * AcceptanceTimer.tsx
 * Live countdown timer for dispatch queue rows.
 * Shows remaining time for technician acceptance with color-coded urgency.
 *
 * Green  : > 5 min remaining
 * Yellow : 2–5 min remaining
 * Red    : < 2 min remaining (pulses)
 * EXPIRED: ≤ 0 remaining
 */

import { useState, useEffect, useRef, useCallback } from "react";
import { Clock, AlertTriangle } from "lucide-react";

interface AcceptanceTimerProps {
  /** ISO timestamp when the job was assigned */
  assignedAt: string | null;
  /** ISO timestamp when the acceptance window expires (preferred) */
  expiresAt: string | null;
  /** Current job status */
  status: string;
  /** Acceptance window in minutes (fallback when expiresAt is null) */
  windowMinutes?: number;
}

const formatTime = (totalSeconds: number): string => {
  if (totalSeconds <= 0) return "00:00";
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return `${String(minutes).padStart(2, "0")}:${String(seconds).padStart(2, "0")}`;
};

const getTimerClass = (seconds: number): string => {
  if (seconds <= 0) return "timer-expired";
  if (seconds < 120) return "timer-red";
  if (seconds < 300) return "timer-yellow";
  return "timer-green";
};

const AcceptanceTimer = ({
  assignedAt,
  expiresAt,
  status,
  windowMinutes = 10,
}: AcceptanceTimerProps) => {
  const computeRemaining = useCallback((): number => {
    // Only show timer for ASSIGNED status
    if (status !== "ASSIGNED") return -1;

    let expiresDate: Date;

    if (expiresAt) {
      expiresDate = new Date(expiresAt);
    } else if (assignedAt) {
      // Fallback: simulate window from assigned_at
      expiresDate = new Date(
        new Date(assignedAt).getTime() + windowMinutes * 60 * 1000
      );
    } else {
      return -1;
    }

    const now = Date.now();
    return Math.max(0, Math.floor((expiresDate.getTime() - now) / 1000));
  }, [assignedAt, expiresAt, status, windowMinutes]);

  const [remaining, setRemaining] = useState<number>(computeRemaining);
  const [isPaused, setIsPaused] = useState(false);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Reset when props change
  useEffect(() => {
    setRemaining(computeRemaining());
  }, [computeRemaining]);

  // Tick every second
  useEffect(() => {
    if (status !== "ASSIGNED" || remaining <= 0 || isPaused) {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
      return;
    }

    intervalRef.current = setInterval(() => {
      setRemaining((prev) => {
        if (prev <= 1) {
          if (intervalRef.current) clearInterval(intervalRef.current);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [status, remaining > 0, isPaused]); // eslint-disable-line react-hooks/exhaustive-deps

  // QUEUED jobs: no timer
  if (status === "QUEUED") {
    return (
      <span className="timer-badge timer-queued" title="Awaiting assignment">
        <Clock size={12} />
        <span>Pending</span>
      </span>
    );
  }

  // EN_ROUTE / ON_SITE: accepted
  if (status === "EN_ROUTE" || status === "ON_SITE") {
    return (
      <span className="timer-badge timer-accepted" title="Accepted">
        <span className="timer-check">✓</span>
        <span>Accepted</span>
      </span>
    );
  }

  // ASSIGNED with no valid time data
  if (remaining < 0) {
    return (
      <span className="timer-badge timer-queued">
        <Clock size={12} />
        <span>—</span>
      </span>
    );
  }

  const timerClass = getTimerClass(remaining);
  const isExpired = remaining <= 0;

  return (
    <span
      className={`timer-badge ${timerClass}`}
      title={
        isExpired
          ? "Acceptance window expired"
          : `${formatTime(remaining)} remaining`
      }
      onMouseEnter={() => setIsPaused(true)}
      onMouseLeave={() => setIsPaused(false)}
    >
      {isExpired ? (
        <>
          <AlertTriangle size={12} />
          <span>EXPIRED</span>
        </>
      ) : (
        <>
          <Clock size={12} />
          <span className="timer-digits">{formatTime(remaining)}</span>
          {isPaused && (
            <span className="timer-paused-indicator" title="Paused on hover">
              ⏸
            </span>
          )}
        </>
      )}
    </span>
  );
};

export default AcceptanceTimer;
