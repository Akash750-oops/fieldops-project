/**
 * SLARiskBadge.tsx
 *
 * A reusable badge component that displays the SLA risk level based on the
 * time remaining until a specified deadline.
 * Features color coding, live tick every 60s, custom Framer Motion pulse on CRITICAL,
 * accessible ARIA labels, hover tooltips, and configurable beep alerts.
 */

import { useState, useEffect, useRef } from "react";
import { motion } from "framer-motion";
import { XCircle, AlertTriangle, CheckCircle } from "lucide-react";

export type SLARiskLevel = "CRITICAL" | "HIGH" | "MEDIUM" | "LOW";

export interface SLARiskBadgeProps {
  /** ISO8601 timestamp representing the SLA deadline */
  slaDeadline: string;
  /** Whether to show the minutes remaining text ("45 min left") */
  showMinutes?: boolean;
  /** Whether to apply Framer Motion pulse animation for CRITICAL risk */
  enablePulse?: boolean;
  /** Whether to play a warning sound alert when transitioning into CRITICAL risk */
  enableSound?: boolean;
  /** Badge dimensions */
  size?: "sm" | "md" | "lg";
}

/**
 * Calculates remaining minutes from deadline relative to reference date.
 */
export const computeMinutesRemaining = (deadlineStr: string, fromDate: Date = new Date()): number => {
  if (!deadlineStr) return 0;
  const deadline = new Date(deadlineStr);
  const diffMs = deadline.getTime() - fromDate.getTime();
  return Math.round(diffMs / 60000);
};

/**
 * Maps minutes remaining to SLA Risk Level.
 */
export const calculateRiskLevel = (minutes: number): SLARiskLevel => {
  if (minutes < 10) return "CRITICAL";
  if (minutes < 30) return "HIGH";
  if (minutes <= 60) return "MEDIUM";
  return "LOW";
};

const playSoundAlert = () => {
  try {
    const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
    if (!AudioContextClass) return;
    const audioCtx = new AudioContextClass();
    
    // Siren-like warning frequency (dual tone)
    const osc1 = audioCtx.createOscillator();
    const osc2 = audioCtx.createOscillator();
    const gainNode = audioCtx.createGain();

    osc1.connect(gainNode);
    osc2.connect(gainNode);
    gainNode.connect(audioCtx.destination);

    osc1.type = "sine";
    osc1.frequency.setValueAtTime(520, audioCtx.currentTime); // C5
    gainNode.gain.setValueAtTime(0.06, audioCtx.currentTime);
    osc1.start();
    osc1.stop(audioCtx.currentTime + 0.15);

    osc2.type = "sine";
    osc2.frequency.setValueAtTime(660, audioCtx.currentTime + 0.2); // E5
    osc2.start(audioCtx.currentTime + 0.2);
    osc2.stop(audioCtx.currentTime + 0.35);
  } catch (e) {
    console.warn("SLA Sound Alert playback blocked or unsupported:", e);
  }
};

const SLARiskBadge = ({
  slaDeadline,
  showMinutes = true,
  enablePulse = true,
  enableSound = false,
  size = "md",
}: SLARiskBadgeProps) => {
  // Update state every 60 seconds
  const [currentTime, setCurrentTime] = useState(new Date());
  const hasPlayedRef = useRef(false);

  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentTime(new Date());
    }, 60000);

    return () => clearInterval(interval);
  }, []);

  // Reset sound trigger flag when the deadline changes
  useEffect(() => {
    hasPlayedRef.current = false;
  }, [slaDeadline]);

  const minutesRemaining = computeMinutesRemaining(slaDeadline, currentTime);
  const riskLevel = calculateRiskLevel(minutesRemaining);
  const isBreached = minutesRemaining < 0;

  // Sound Alert Trigger
  useEffect(() => {
    if (riskLevel === "CRITICAL" && enableSound && !hasPlayedRef.current) {
      playSoundAlert();
      hasPlayedRef.current = true;
    } else if (riskLevel !== "CRITICAL") {
      hasPlayedRef.current = false;
    }
  }, [riskLevel, enableSound]);

  // Size styling configuration
  const sizeClasses = {
    sm: "text-xs px-2 py-0.5 rounded gap-1",
    md: "text-sm px-2.5 py-1 rounded gap-1.5",
    lg: "text-base px-3 py-1.5 rounded gap-2",
  };

  const iconSizes = {
    sm: 12,
    md: 14,
    lg: 16,
  };

  // Risk configurations
  const riskConfigs = {
    CRITICAL: {
      bg: "bg-red-100",
      text: "text-red-800",
      icon: XCircle,
      label: "CRITICAL",
    },
    HIGH: {
      bg: "bg-orange-100",
      text: "text-orange-800",
      icon: AlertTriangle,
      label: "HIGH",
    },
    MEDIUM: {
      bg: "bg-yellow-100",
      text: "text-yellow-800",
      icon: AlertTriangle,
      label: "MEDIUM",
    },
    LOW: {
      bg: "bg-green-100",
      text: "text-green-800",
      icon: CheckCircle,
      label: "LOW",
    },
  };

  const config = riskConfigs[riskLevel];
  const IconComponent = config.icon;

  // Render text based on showMinutes option and breach status
  let badgeText = "";
  if (isBreached) {
    badgeText = "BREACHED";
  } else if (showMinutes) {
    badgeText = `${minutesRemaining} min left`;
  } else {
    badgeText = config.label;
  }

  // Animation props using Framer Motion
  const isCritical = riskLevel === "CRITICAL";
  const animationProps = (enablePulse && isCritical) ? {
    animate: {
      scale: [1, 1.03, 1],
      opacity: [1, 0.85, 1],
    },
    transition: {
      duration: 1.5,
      repeat: Infinity,
      ease: "easeInOut",
    }
  } : {};

  const getIsoDeadline = () => {
    try {
      const d = new Date(slaDeadline);
      if (isNaN(d.getTime())) return slaDeadline;
      return d.toISOString();
    } catch {
      return slaDeadline;
    }
  };

  return (
    <motion.span
      role="status"
      aria-label={`SLA Risk: ${riskLevel}${isBreached ? ' (Breached)' : ''}. ${badgeText}`}
      title={getIsoDeadline()}
      className={`inline-flex items-center font-semibold border-0 ${config.bg} ${config.text} ${sizeClasses[size]}`}
      {...animationProps}
    >
      <IconComponent size={iconSizes[size]} className="flex-shrink-0" />
      <span>{badgeText}</span>
    </motion.span>
  );
};

export default SLARiskBadge;
