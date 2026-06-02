/**
 * WaitingState.tsx
 * Post-action feedback overlay with spinner, success, error, and timeout states.
 * Uses Framer Motion for smooth enter/exit transitions.
 */
import React from "react";
import { CheckCircle, XCircle, AlertTriangle, Loader2, RotateCcw, X } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import type { WaitingStateProps } from "../../types/notifications";
// @ts-ignore
import "./notifications.css";

export const WaitingState: React.FC<WaitingStateProps> = ({
  state,
  message = "",
  onRetry,
  onCancel,
}) => {
  if (state === "IDLE") return null;

  return (
    <AnimatePresence>
      <motion.div
        className="waiting-overlay"
        data-testid="waiting-state"
        data-state={state}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        aria-live="assertive"
        role="status"
      >
        <div className="waiting-content">
          {/* ─── LOADING ─────────────────────────────── */}
          {state === "LOADING" && (
            <motion.div
              className="waiting-inner"
              initial={{ scale: 0.9 }}
              animate={{ scale: 1 }}
              data-testid="waiting-loading"
            >
              <Loader2 size={36} className="waiting-spinner" aria-hidden="true" />
              <p className="waiting-text">{message}</p>
            </motion.div>
          )}

          {/* ─── SUCCESS ─────────────────────────────── */}
          {state === "SUCCESS" && (
            <motion.div
              className="waiting-inner waiting-success"
              initial={{ scale: 0.8, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              data-testid="waiting-success"
            >
              <CheckCircle size={40} className="waiting-success-icon" aria-hidden="true" />
              <p className="waiting-text">{message}</p>
            </motion.div>
          )}

          {/* ─── ERROR ───────────────────────────────── */}
          {state === "ERROR" && (
            <motion.div
              className="waiting-inner waiting-error"
              initial={{ scale: 0.8, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              data-testid="waiting-error"
            >
              <XCircle size={40} className="waiting-error-icon" aria-hidden="true" />
              <p className="waiting-text">{message}</p>
              <div className="waiting-actions">
                {onRetry && (
                  <button
                    type="button"
                    className="waiting-retry-btn"
                    onClick={onRetry}
                    data-testid="waiting-retry-btn"
                  >
                    <RotateCcw size={14} aria-hidden="true" />
                    Retry
                  </button>
                )}
                {onCancel && (
                  <button
                    type="button"
                    className="waiting-cancel-btn"
                    onClick={onCancel}
                    data-testid="waiting-cancel-btn"
                  >
                    <X size={14} aria-hidden="true" />
                    Cancel
                  </button>
                )}
              </div>
            </motion.div>
          )}

          {/* ─── TIMEOUT ─────────────────────────────── */}
          {state === "TIMEOUT" && (
            <motion.div
              className="waiting-inner waiting-timeout"
              initial={{ scale: 0.8, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              data-testid="waiting-timeout"
            >
              <AlertTriangle size={40} className="waiting-timeout-icon" aria-hidden="true" />
              <p className="waiting-text">{message}</p>
              <div className="waiting-actions">
                {onRetry && (
                  <button
                    type="button"
                    className="waiting-retry-btn"
                    onClick={onRetry}
                    data-testid="waiting-timeout-retry-btn"
                  >
                    <RotateCcw size={14} aria-hidden="true" />
                    Retry
                  </button>
                )}
                {onCancel && (
                  <button
                    type="button"
                    className="waiting-cancel-btn"
                    onClick={onCancel}
                    data-testid="waiting-timeout-cancel-btn"
                  >
                    <X size={14} aria-hidden="true" />
                    Cancel
                  </button>
                )}
              </div>
            </motion.div>
          )}
        </div>
      </motion.div>
    </AnimatePresence>
  );
};

export default WaitingState;
