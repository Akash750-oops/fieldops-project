import React, { useState, useEffect } from "react";
import { Clock, MapPin, Phone, User, DollarSign, Brain, Navigation, ChevronRight, X, AlertTriangle } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { NotificationDetailProps, JobNotificationDetail } from "../../types/notifications.ts";
// @ts-ignore: allow importing CSS side-effect without module declarations
import "./notifications.css";

const calculateTimeRemaining = (deadline?: string) => {
  if (!deadline) return { total: 0, hours: 0, minutes: 0, seconds: 0, overdue: true };
  const total = new Date(deadline).getTime() - Date.now();
  const overdue = total < 0;
  const absTotal = Math.abs(total);
  const seconds = Math.floor((absTotal / 1000) % 60);
  const minutes = Math.floor((absTotal / 1000 / 60) % 60);
  const hours = Math.floor((absTotal / (1000 * 60 * 60)) % 24);
  const days = Math.floor(absTotal / (1000 * 60 * 60 * 24));
  return {
    total,
    hours: hours + days * 24,
    minutes,
    seconds,
    overdue
  };
};

export const NotificationDetail: React.FC<NotificationDetailProps> = ({
  notification,
  job,
  loading = false,
  error,
  onAccept,
  onReject,
  onReassign,
  onClose
}) => {
  const jobData = job || notification.job;
  const [timeLeft, setTimeLeft] = useState(() => calculateTimeRemaining(jobData?.sla_deadline));
  const [isRejectModalOpen, setIsRejectModalOpen] = useState(false);
  const [rejectReason, setRejectReason] = useState("");
  const [actionProcessing, setActionProcessing] = useState(false);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  useEffect(() => {
    if (!jobData?.sla_deadline) return;
    const interval = setInterval(() => {
      setTimeLeft(calculateTimeRemaining(jobData.sla_deadline));
    }, 1000);
    return () => clearInterval(interval);
  }, [jobData?.sla_deadline]);

  if (loading) {
    return (
      <div className="noc-module">
        <div className="notification-detail-card" style={{ display: "flex", justifyContent: "center", alignItems: "center", height: "300px" }}>
          <div className="tld-refresh-spinner" />
          <span style={{ marginLeft: "12px", color: "#64748b" }}>Loading job details…</span>
        </div>
      </div>
    );
  }

  if (error || !jobData) {
    return (
      <div className="noc-module">
        <div className="notification-detail-card" style={{ textAlign: "center", padding: "40px" }}>
          <AlertTriangle size={40} color="#ef4444" style={{ margin: "0 auto 12px auto" }} />
          <p style={{ fontWeight: 600, color: "#1e293b", margin: "0 0 8px 0" }}>Failed to load job details</p>
          <p style={{ fontSize: "14px", color: "#64748b", margin: "0 0 20px 0" }}>{error || "Job data could not be found."}</p>
          <button type="button" className="permission-btn-secondary" onClick={onClose}>Close Detail</button>
        </div>
      </div>
    );
  }

  const formatCountdown = () => {
    const pad = (n: number) => String(n).padStart(2, "0");
    const label = timeLeft.overdue ? "Overdue by: " : "Time Remaining: ";
    return `${label}${pad(timeLeft.hours)}h ${pad(timeLeft.minutes)}m ${pad(timeLeft.seconds)}s`;
  };

  const handleAction = async (type: "accept" | "reject" | "reassign") => {
    setActionProcessing(true);
    setActionSuccess(null);
    setActionError(null);
    try {
      if (type === "accept") {
        await onAccept(jobData.id);
        setActionSuccess("Job accepted successfully!");
      } else if (type === "reject") {
        await onReject(jobData.id, rejectReason);
        setIsRejectModalOpen(false);
        setRejectReason("");
        setActionSuccess("Job rejected successfully.");
      } else if (type === "reassign") {
        await onReassign(jobData.id);
        setActionSuccess("Reassignment requested.");
      }
    } catch (err: any) {
      setActionError(err?.message || `Failed to ${type} job.`);
    } finally {
      setActionProcessing(false);
    }
  };

  return (
    <div className="noc-module">
      <motion.div
        className="notification-detail-card"
        drag="x"
        dragConstraints={{ left: 0, right: 300 }}
        dragElastic={{ left: 0.1, right: 0.5 }}
        onDragEnd={(e, info) => {
          if (info.offset.x > 150) {
            onClose();
          }
        }}
        initial={{ opacity: 0, y: 15 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0 }}
      >
        <div className="detail-header">
          <div>
            <span className="detail-grid-label" style={{ display: "block", marginBottom: "2px" }}>
              Job ID: #{jobData.id}
            </span>
            <h2 className="detail-header-title">{jobData.title}</h2>
          </div>
          <span className={`detail-priority-badge priority-${(jobData.priority || "medium").toLowerCase()}`}>
            {jobData.priority} Priority
          </span>
        </div>

        {/* Action success/error banners */}
        {actionSuccess && (
          <div style={{ padding: "10px 14px", backgroundColor: "#f0fdf4", border: "1px solid #bbf7d0", color: "#166534", borderRadius: "8px", fontSize: "14px", fontWeight: 500, marginBottom: "16px" }}>
            {actionSuccess}
          </div>
        )}
        {actionError && (
          <div style={{ padding: "10px 14px", backgroundColor: "#fdf2f2", border: "1px solid #fde8e8", color: "#9b1c1c", borderRadius: "8px", fontSize: "14px", fontWeight: 500, marginBottom: "16px" }}>
            {actionError}
          </div>
        )}

        {/* SLA Countdown Timer */}
        <div className={`sla-countdown ${timeLeft.overdue ? "overdue" : ""}`}>
          <Clock size={16} />
          <span>{formatCountdown()}</span>
        </div>

        {/* Job Details Grid */}
        <div className="detail-row-grid">
          <div className="detail-grid-item">
            <span className="detail-grid-label">Customer</span>
            <span className="detail-grid-value" style={{ display: "flex", alignItems: "center", gap: "6px" }}>
              <User size={14} color="#64748b" /> {jobData.customer_name}
            </span>
          </div>
          <div className="detail-grid-item">
            <span className="detail-grid-label">Contact</span>
            <span className="detail-grid-value">
              <a href={`tel:${jobData.customer_phone}`} style={{ display: "flex", alignItems: "center", gap: "6px", color: "#3b82f6", textDecoration: "none" }}>
                <Phone size={14} /> {jobData.customer_phone}
              </a>
            </span>
          </div>
          <div className="detail-grid-item">
            <span className="detail-grid-label">Distance</span>
            <span className="detail-grid-value" style={{ display: "flex", alignItems: "center", gap: "6px" }}>
              <Navigation size={14} color="#64748b" /> {jobData.distance_km} km away
            </span>
          </div>
          <div className="detail-grid-item">
            <span className="detail-grid-label">Est. Value</span>
            <span className="detail-grid-value" style={{ display: "flex", alignItems: "center", gap: "2px", fontWeight: 700, color: "#10b981" }}>
              <DollarSign size={14} />{jobData.estimated_value}
            </span>
          </div>
        </div>

        <div className="detail-section-title">Job Description</div>
        <p style={{ fontSize: "14px", color: "#475569", lineHeight: 1.5, margin: "0 0 16px 0" }}>
          {jobData.description}
        </p>

        <div className="detail-section-title">Required Skills</div>
        <div className="skills-container">
          {jobData.required_skills?.map((skill: string) => (
            <span key={skill} className="skill-chip">
              {skill}
            </span>
          ))}
        </div>

        {/* Visual Map Placeholder */}
        <div className="detail-section-title">Location Map</div>
        <div className="map-placeholder">
          <MapPin size={24} color="#ef4444" />
          <span style={{ fontWeight: 600, color: "#1e293b", fontSize: "13px" }}>{jobData.location}</span>
          <span style={{ fontSize: "11px", color: "#94a3b8" }}>(Static map preview)</span>
        </div>

        {/* Action Buttons */}
        <div className="notification-actions">
          <button
            type="button"
            className="accept-btn"
            onClick={() => handleAction("accept")}
            disabled={actionProcessing || !!actionSuccess}
          >
            Accept
          </button>
          <button
            type="button"
            className="reject-btn"
            onClick={() => setIsRejectModalOpen(true)}
            disabled={actionProcessing || !!actionSuccess}
          >
            Reject
          </button>
          <button
            type="button"
            className="reassign-btn"
            onClick={() => handleAction("reassign")}
            disabled={actionProcessing || !!actionSuccess}
          >
            Reassign
          </button>
          <button
            type="button"
            className="permission-btn-secondary"
            onClick={onClose}
            style={{ flex: "none", width: "42px", height: "42px", display: "flex", alignItems: "center", justifyContent: "center", padding: 0 }}
            title="Close Details"
          >
            <ChevronRight size={18} />
          </button>
        </div>
      </motion.div>

      {/* Reject Reason Modal */}
      <AnimatePresence>
        {isRejectModalOpen && (
          <div className="rejection-modal-backdrop">
            <motion.div
              className="rejection-modal"
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
            >
              <h3>Reject Assignment</h3>
              <p style={{ fontSize: "13px", color: "#64748b", margin: "0 0 12px 0" }}>
                Please provide a reason for rejecting this assignment.
              </p>
              <textarea
                className="rejection-textarea"
                placeholder="Reason (e.g. Travel distance too long, lack of parts…)"
                value={rejectReason}
                onChange={(e) => setRejectReason(e.target.value)}
              />
              <div className="rejection-modal-actions">
                <button
                  type="button"
                  className="rejection-cancel"
                  onClick={() => {
                    setIsRejectModalOpen(false);
                    setRejectReason("");
                  }}
                  disabled={actionProcessing}
                >
                  Cancel
                </button>
                <button
                  type="button"
                  className="rejection-submit"
                  onClick={() => handleAction("reject")}
                  disabled={actionProcessing || !rejectReason.trim()}
                >
                  Confirm Rejection
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
};