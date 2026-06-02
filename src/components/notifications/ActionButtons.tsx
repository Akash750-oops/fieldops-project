/**
 * ActionButtons.tsx
 * Accept / Reject / Reassign button group with confirmation modals,
 * form validation, loading states, and full keyboard accessibility.
 */
import React, { useState, useEffect } from "react";
import { CheckCircle, X, Shuffle, Loader2, Search, User } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import StatusBadge from "../common/StatusBadge";
import type { ActionButtonsProps } from "../../types/notifications";
// @ts-ignore
import "./notifications.css";

const MIN_REASON_LENGTH = 10;

interface ColleagueOption {
  technician_id: number;
  technician_name: string;
  technician_status: string;
  technician_skill: string;
}

export const ActionButtons: React.FC<ActionButtonsProps> = ({
  onAccept,
  onReject,
  onReassign,
  jobId,
  disabled = false,
}) => {
  // Modal states
  const [isRejectModalOpen, setIsRejectModalOpen] = useState(false);
  const [isReassignModalOpen, setIsReassignModalOpen] = useState(false);

  // Reject modal
  const [rejectReason, setRejectReason] = useState("");
  const [rejectLoading, setRejectLoading] = useState(false);

  // Reassign modal
  const [reassignSearch, setReassignSearch] = useState("");
  const [reassignReason, setReassignReason] = useState("");
  const [selectedColleague, setSelectedColleague] = useState<number | null>(null);
  const [reassignLoading, setReassignLoading] = useState(false);
  const [colleagues, setColleagues] = useState<ColleagueOption[]>([]);
  const [colleaguesLoading, setColleaguesLoading] = useState(false);

  // Accept loading
  const [acceptLoading, setAcceptLoading] = useState(false);

  // Track if any action completed
  const [actioned, setActioned] = useState(false);

  const anyLoading = acceptLoading || rejectLoading || reassignLoading;
  const isDisabled = disabled || actioned || anyLoading;

  // Fetch colleagues for reassign modal
  useEffect(() => {
    if (!isReassignModalOpen) return;
    let cancelled = false;
    const fetchColleagues = async () => {
      setColleaguesLoading(true);
      try {
        const res = await fetch("http://localhost:8000/technicians/available");
        if (!res.ok) throw new Error("Failed to fetch");
        const data = await res.json();
        if (!cancelled) {
          setColleagues(
            data.map((t: any) => ({
              technician_id: t.id || t.technician_id,
              technician_name: t.technician || t.technician_name,
              technician_status: t.status || t.technician_status || "AVAILABLE",
              technician_skill: t.skill || t.technician_skill || "",
            }))
          );
        }
      } catch {
        if (!cancelled) setColleagues([]);
      } finally {
        if (!cancelled) setColleaguesLoading(false);
      }
    };
    fetchColleagues();
    return () => { cancelled = true; };
  }, [isReassignModalOpen]);

  const filteredColleagues = colleagues.filter((c) =>
    c.technician_name.toLowerCase().includes(reassignSearch.toLowerCase())
  );

  // ─── Handlers ───────────────────────────────────────────

  const handleAccept = async () => {
    setAcceptLoading(true);
    try {
      await onAccept(jobId);
      setActioned(true);
    } finally {
      setAcceptLoading(false);
    }
  };

  const handleRejectConfirm = async () => {
    setRejectLoading(true);
    try {
      await onReject(jobId, rejectReason);
      setActioned(true);
      setIsRejectModalOpen(false);
      setRejectReason("");
    } finally {
      setRejectLoading(false);
    }
  };

  const handleReassignConfirm = async () => {
    setReassignLoading(true);
    try {
      await onReassign(jobId, selectedColleague ?? undefined);
      setActioned(true);
      setIsReassignModalOpen(false);
      setSelectedColleague(null);
      setReassignReason("");
      setReassignSearch("");
    } finally {
      setReassignLoading(false);
    }
  };

  const reasonValid = rejectReason.trim().length >= MIN_REASON_LENGTH;

  return (
    <>
      {/* Button Group */}
      <div className="action-btn-group" data-testid="action-buttons" role="group" aria-label="Job response actions">
        <button
          type="button"
          className="action-btn action-btn-accept"
          onClick={handleAccept}
          disabled={isDisabled}
          aria-label="Accept this job assignment"
          data-testid="accept-btn"
        >
          {acceptLoading ? (
            <Loader2 size={16} className="action-btn-spinner" aria-hidden="true" />
          ) : (
            <CheckCircle size={16} aria-hidden="true" />
          )}
          <span>Accept Job</span>
        </button>

        <button
          type="button"
          className="action-btn action-btn-reject"
          onClick={() => setIsRejectModalOpen(true)}
          disabled={isDisabled}
          aria-label="Reject this job assignment"
          data-testid="reject-btn"
        >
          <X size={16} aria-hidden="true" />
          <span>Reject</span>
        </button>

        <button
          type="button"
          className="action-btn action-btn-reassign"
          onClick={() => setIsReassignModalOpen(true)}
          disabled={isDisabled}
          aria-label="Reassign this job to a colleague"
          data-testid="reassign-btn"
        >
          <Shuffle size={16} aria-hidden="true" />
          <span>Reassign</span>
        </button>
      </div>

      {/* ─── Reject Modal ─────────────────────────────────────── */}
      <AnimatePresence>
        {isRejectModalOpen && (
          <div
            className="rejection-modal-backdrop"
            data-testid="reject-modal-backdrop"
            onClick={(e) => {
              if (e.target === e.currentTarget && !rejectLoading) {
                setIsRejectModalOpen(false);
                setRejectReason("");
              }
            }}
          >
            <motion.div
              className="rejection-modal"
              data-testid="reject-modal"
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              role="dialog"
              aria-modal="true"
              aria-labelledby="reject-modal-title"
            >
              <h3 id="reject-modal-title">Reject Assignment</h3>
              <p style={{ fontSize: "13px", color: "#64748b", margin: "0 0 12px 0" }}>
                Please provide a reason for rejecting this assignment (min. {MIN_REASON_LENGTH} characters).
              </p>
              <textarea
                className="rejection-textarea"
                placeholder="Reason (e.g. Travel distance too long, lack of parts…)"
                value={rejectReason}
                onChange={(e) => setRejectReason(e.target.value)}
                disabled={rejectLoading}
                aria-label="Rejection reason"
                data-testid="reject-reason-input"
              />
              <div className={`char-count ${!reasonValid && rejectReason.length > 0 ? "char-count-error" : ""}`}>
                {rejectReason.trim().length}/{MIN_REASON_LENGTH} characters
              </div>
              <div className="rejection-modal-actions">
                <button
                  type="button"
                  className="rejection-cancel"
                  onClick={() => {
                    setIsRejectModalOpen(false);
                    setRejectReason("");
                  }}
                  disabled={rejectLoading}
                  data-testid="reject-cancel-btn"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  className="rejection-submit"
                  onClick={handleRejectConfirm}
                  disabled={rejectLoading || !reasonValid}
                  data-testid="reject-confirm-btn"
                >
                  {rejectLoading ? (
                    <>
                      <Loader2 size={14} className="action-btn-spinner" aria-hidden="true" />
                      Rejecting…
                    </>
                  ) : (
                    "Confirm Rejection"
                  )}
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* ─── Reassign Modal ───────────────────────────────────── */}
      <AnimatePresence>
        {isReassignModalOpen && (
          <div
            className="rejection-modal-backdrop"
            data-testid="reassign-modal-backdrop"
            onClick={(e) => {
              if (e.target === e.currentTarget && !reassignLoading) {
                setIsReassignModalOpen(false);
                setSelectedColleague(null);
                setReassignSearch("");
                setReassignReason("");
              }
            }}
          >
            <motion.div
              className="reassign-modal"
              data-testid="reassign-modal"
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              role="dialog"
              aria-modal="true"
              aria-labelledby="reassign-modal-title"
            >
              <h3 id="reassign-modal-title">Reassign to Colleague</h3>
              <p style={{ fontSize: "13px", color: "#64748b", margin: "0 0 12px 0" }}>
                Search and select a colleague to reassign this job.
              </p>

              {/* Search */}
              <div className="reassign-search">
                <Search size={14} aria-hidden="true" />
                <input
                  type="text"
                  placeholder="Search technicians…"
                  value={reassignSearch}
                  onChange={(e) => setReassignSearch(e.target.value)}
                  disabled={reassignLoading}
                  aria-label="Search colleagues"
                  data-testid="reassign-search-input"
                />
              </div>

              {/* Colleague list */}
              <div className="reassign-tech-list" role="listbox" aria-label="Available technicians" data-testid="reassign-tech-list">
                {colleaguesLoading ? (
                  <div className="reassign-loading">
                    <Loader2 size={18} className="action-btn-spinner" />
                    <span>Loading technicians…</span>
                  </div>
                ) : filteredColleagues.length === 0 ? (
                  <div className="reassign-empty">No technicians found</div>
                ) : (
                  filteredColleagues.map((c) => (
                    <button
                      key={c.technician_id}
                      type="button"
                      className={`reassign-tech-item ${selectedColleague === c.technician_id ? "reassign-tech-selected" : ""}`}
                      onClick={() => setSelectedColleague(c.technician_id)}
                      role="option"
                      aria-selected={selectedColleague === c.technician_id}
                      data-testid={`reassign-tech-${c.technician_id}`}
                    >
                      <div className="reassign-tech-avatar">
                        <User size={14} aria-hidden="true" />
                      </div>
                      <div className="reassign-tech-info">
                        <span className="reassign-tech-name">{c.technician_name}</span>
                        <span className="reassign-tech-skill">{c.technician_skill}</span>
                      </div>
                      <StatusBadge status={c.technician_status as any} size="sm" />
                    </button>
                  ))
                )}
              </div>

              {/* Optional reason */}
              <textarea
                className="rejection-textarea"
                placeholder="Reason for reassignment (optional)"
                value={reassignReason}
                onChange={(e) => setReassignReason(e.target.value)}
                disabled={reassignLoading}
                style={{ height: "60px", marginTop: "12px" }}
                aria-label="Reassignment reason"
                data-testid="reassign-reason-input"
              />

              <div className="rejection-modal-actions">
                <button
                  type="button"
                  className="rejection-cancel"
                  onClick={() => {
                    setIsReassignModalOpen(false);
                    setSelectedColleague(null);
                    setReassignSearch("");
                    setReassignReason("");
                  }}
                  disabled={reassignLoading}
                  data-testid="reassign-cancel-btn"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  className="reassign-confirm-btn"
                  onClick={handleReassignConfirm}
                  disabled={reassignLoading || selectedColleague === null}
                  data-testid="reassign-confirm-btn"
                >
                  {reassignLoading ? (
                    <>
                      <Loader2 size={14} className="action-btn-spinner" aria-hidden="true" />
                      Reassigning…
                    </>
                  ) : (
                    "Confirm Reassign"
                  )}
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </>
  );
};

export default ActionButtons;
