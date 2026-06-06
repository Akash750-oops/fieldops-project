/**
 * ToastNotification.tsx
 * Single animated toast card with:
 * - Color-coded border & icon per type
 * - Hover-to-pause auto-dismiss progress bar
 * - Manual dismiss (X button)
 * - Batch count badge
 * - Click-to-navigate callback
 * - ARIA live region support
 * - Framer Motion enter/exit animations
 */

import { useState, useEffect, useRef, useCallback } from 'react';
import { motion } from 'framer-motion';
import {
  Info,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Navigation,
  X,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import type { ToastItem } from '../../types/notifications';

// ─── Config ──────────────────────────────────────────────────────────

const VARIANTS = {
  success: {
    border: 'border-l-emerald-500',
    icon: CheckCircle2,
    iconColor: 'text-emerald-500',
    bg: 'bg-emerald-50',
    title: 'text-emerald-800',
    badge: 'bg-emerald-100 text-emerald-700',
    progress: 'bg-emerald-400',
  },
  warning: {
    border: 'border-l-amber-500',
    icon: AlertTriangle,
    iconColor: 'text-amber-500',
    bg: 'bg-amber-50',
    title: 'text-amber-800',
    badge: 'bg-amber-100 text-amber-700',
    progress: 'bg-amber-400',
  },
  error: {
    border: 'border-l-red-500',
    icon: XCircle,
    iconColor: 'text-red-500',
    bg: 'bg-red-50',
    title: 'text-red-800',
    badge: 'bg-red-100 text-red-700',
    progress: 'bg-red-400',
  },
  info: {
    border: 'border-l-blue-500',
    icon: Info,
    iconColor: 'text-blue-500',
    bg: 'bg-blue-50',
    title: 'text-blue-800',
    badge: 'bg-blue-100 text-blue-700',
    progress: 'bg-blue-400',
  },
};

// Override icon for en_route
function resolveIcon(toast: ToastItem) {
  if (toast.eventType === 'job.en_route') return Navigation;
  return VARIANTS[toast.type].icon;
}

// ─── Props ────────────────────────────────────────────────────────────

interface ToastNotificationProps {
  toast: ToastItem;
  onDismiss: (id: string) => void;
  onPause: (id: string) => void;
  onResume: (id: string) => void;
  onNavigate?: (jobId: string | number) => void;
}

// ─── Component ────────────────────────────────────────────────────────

export default function ToastNotification({
  toast,
  onDismiss,
  onPause,
  onResume,
  onNavigate,
}: ToastNotificationProps) {
  const v = VARIANTS[toast.type];
  const Icon = resolveIcon(toast);
  const isCritical = toast.priority === 'critical';

  // Progress bar — counts down from 100 to 0
  const [progress, setProgress] = useState(100);
  const [paused, setPaused] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const startTimeRef = useRef<number>(Date.now());
  const elapsedRef = useRef<number>(0);

  const hasBatch = (toast.batchCount ?? 1) > 1;
  const hasAutoDismiss = toast.autoDismiss > 0;

  // Progress countdown
  const startProgress = useCallback(() => {
    if (!hasAutoDismiss) return;
    if (intervalRef.current) clearInterval(intervalRef.current);
    startTimeRef.current = Date.now();

    intervalRef.current = setInterval(() => {
      const totalElapsed = elapsedRef.current + (Date.now() - startTimeRef.current);
      const pct = Math.max(0, 100 - (totalElapsed / toast.autoDismiss) * 100);
      setProgress(pct);
      if (pct <= 0) {
        clearInterval(intervalRef.current!);
      }
    }, 50);
  }, [toast.autoDismiss, hasAutoDismiss]);

  const stopProgress = useCallback(() => {
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
    elapsedRef.current += Date.now() - startTimeRef.current;
  }, []);

  useEffect(() => {
    startProgress();
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const handleMouseEnter = () => {
    setPaused(true);
    stopProgress();
    onPause(toast.id);
  };

  const handleMouseLeave = () => {
    setPaused(false);
    startProgress();
    onResume(toast.id);
  };

  const handleClick = () => {
    if (toast.jobId && onNavigate) {
      onNavigate(toast.jobId);
      onDismiss(toast.id);
    }
  };

  return (
    <motion.div
      layout
      initial={{ opacity: 0, x: 80, scale: 0.94 }}
      animate={{ opacity: 1, x: 0, scale: 1 }}
      exit={{ opacity: 0, x: 80, scale: 0.94 }}
      transition={{ type: 'spring', stiffness: 380, damping: 30 }}
      role={isCritical ? 'alert' : 'status'}
      aria-live={isCritical ? 'assertive' : 'polite'}
      aria-atomic="true"
      className={`
        relative w-80 max-w-[calc(100vw-2rem)] overflow-hidden rounded-xl border border-l-4 bg-white shadow-xl
        ${v.border}
        ${toast.jobId ? 'cursor-pointer' : ''}
      `}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
    >
      {/* Clickable body */}
      <div
        className="pl-4 pr-9 pt-3.5 pb-2.5"
        onClick={handleClick}
      >
        <div className="flex items-start gap-3">
          {/* Icon */}
          <div className={`mt-0.5 flex-none rounded-full p-1.5 ${v.bg}`}>
            <Icon size={16} className={v.iconColor} />
          </div>

          {/* Content */}
          <div className="min-w-0 flex-1">
            <p className={`text-sm font-bold leading-tight ${v.title}`}>
              {toast.title}
              {hasBatch && (
                <span
                  className={`ml-2 inline-flex h-5 min-w-5 items-center justify-center rounded-full px-1.5 text-[10px] font-bold ${v.badge}`}
                  aria-label={`${toast.batchCount} grouped notifications`}
                >
                  {toast.batchCount}
                </span>
              )}
            </p>

            <p className="mt-1 text-xs text-gray-600 leading-snug line-clamp-2">
              {toast.message}
            </p>

            <p className="mt-1.5 text-[10px] text-gray-400">{toast.timestamp}</p>
          </div>
        </div>

        {/* Batch expand */}
        {hasBatch && toast.batchItems && toast.batchItems.length > 1 && (
          <div className="mt-2">
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                setExpanded((x) => !x);
              }}
              className={`flex items-center gap-1 text-[11px] font-semibold ${v.title} hover:underline`}
            >
              {expanded ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
              {expanded ? 'Hide' : `Show ${toast.batchItems.length} events`}
            </button>

            {expanded && (
              <ul className="mt-1.5 space-y-1 rounded-lg bg-gray-50 px-3 py-2">
                {toast.batchItems.map((item, i) => (
                  <li key={i} className="text-xs text-gray-600 leading-snug">
                    <span className="font-medium text-gray-800">{item.title}</span>
                    {' — '}
                    {item.message}
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
      </div>

      {/* Dismiss button */}
      <button
        type="button"
        onClick={(e) => {
          e.stopPropagation();
          onDismiss(toast.id);
        }}
        aria-label="Dismiss notification"
        className="absolute top-3.5 right-3.5 rounded-md p-1 text-gray-400 transition hover:bg-gray-100 hover:text-gray-600 focus:outline-none focus:ring-2 focus:ring-gray-300 z-10"
      >
        <X size={13} />
      </button>

      {/* Progress bar */}
      {hasAutoDismiss && (
        <div className="h-1 w-full bg-gray-100">
          <motion.div
            className={`h-full ${v.progress}`}
            style={{ width: `${progress}%` }}
            transition={{ ease: 'linear' }}
          />
        </div>
      )}

      {/* Paused indicator */}
      {paused && (
        <div className="absolute right-3.5 bottom-2">
          <span className="rounded-full bg-gray-200 px-1.5 py-0.5 text-[9px] font-bold text-gray-500">
            PAUSED
          </span>
        </div>
      )}
    </motion.div>
  );
}
