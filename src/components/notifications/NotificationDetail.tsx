/**
 * NotificationDetail.tsx
 * Refactored to use modular CountdownTimer, ActionButtons, and WaitingState components.
 */
import React, { useState, useEffect } from "react";
import { MapPin, Phone, User, DollarSign, Navigation, AlertTriangle, X } from "lucide-react";
import { motion } from "framer-motion";
import { NotificationDetailProps } from "../../types/notifications";
import CountdownTimer from "./CountdownTimer";
import ActionButtons from "./ActionButtons";
import WaitingState from "./WaitingState";
import useActionState from "../../hooks/useActionState";
import { getOverrideHistory } from "../../services/planningService";
import OverrideWarning from "./OverrideWarning";
import OverrideHistory from "./OverrideHistory";
import { io } from "socket.io-client";
// @ts-ignore: allow importing CSS side-effect without module declarations
import "./notifications.css";

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
  const { state: actionState, message: actionMessage, execute, retry, reset } = useActionState();
  const [overrideLogs, setOverrideLogs] = useState<any[]>([]);
  const [showHistory, setShowHistory] = useState(false);

  useEffect(() => {
    if (!jobData?.id) return;

    const fetchHistory = async () => {
      try {
        const res = await getOverrideHistory(jobData.id);
        if (res && res.data) {
          setOverrideLogs(res.data);
        }
      } catch (err) {
        console.warn("Failed to fetch override history in detail view", err);
      }
    };

    fetchHistory();

    const socket = io("http://localhost:8000", {
      transports: ["websocket", "polling"]
    });

    socket.on("override:new", (data: any) => {
      if (data && (data.job_id === jobData.id || data.job_id === String(jobData.id))) {
        const newOverride = data.override || data;
        setOverrideLogs(prev => {
          if (prev.some(item => item.id === newOverride.id)) return prev;
          return [newOverride, ...prev];
        });
      }
    });

    return () => {
      socket.disconnect();
    };
  }, [jobData?.id]);

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

  // Wrap parent callbacks with useActionState lifecycle
  const handleAccept = async (jobId: string | number) => {
    await execute(() => onAccept(jobId), "Job accepted");
  };

  const handleReject = async (jobId: string | number, reason: string) => {
    await execute(() => onReject(jobId, reason), "Job rejected");
  };

  const handleReassign = async (jobId: string | number) => {
    await execute(() => onReassign(jobId), "Reassignment requested");
  };

  const handleExpire = () => {
    console.warn(`Timer expired for job ${jobData.id}`);
  };

  const handleWarning = () => {
    console.warn(`2 minutes remaining for job ${jobData.id}`);
  };

  const isActioned = actionState === "SUCCESS";

  return (
    <div className="notification-detail-backdrop" onClick={onClose}>
      <motion.div
        className="notification-detail-card"
        style={{ position: "relative" }}
        onClick={(e) => e.stopPropagation()}
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
        {/* Close Button */}
        <button
          type="button"
          onClick={onClose}
          className="detail-close-btn"
          aria-label="Close details"
          title="Close details"
        >
          <X size={18} />
        </button>

        {/* Waiting State Overlay */}
        <WaitingState
          state={actionState}
          message={actionMessage}
          onRetry={retry}
          onCancel={reset}
        />

        {/* Card Body */}
        <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
          {/* Header */}
          <div className="detail-header" style={{ padding: "0 24px 0 0", borderBottom: "none", gap: "4px", marginBottom: "4px" }}>
            <div>
              <span className="detail-grid-label" style={{ display: "block", marginBottom: "2px", fontSize: "10px" }}>
                Job ID: #{jobData.id}
              </span>
              <h2 className="detail-header-title" style={{ fontSize: "17px", fontWeight: 700 }}>{jobData.title}</h2>
            </div>
            <span className={`detail-priority-badge priority-${(jobData.priority || "medium").toLowerCase()}`} style={{ padding: "2px 6px", fontSize: "10px" }}>
              {jobData.priority}
            </span>
          </div>

          {/* Override Warning Banner */}
          {overrideLogs.length > 0 && (
            <div style={{ marginBottom: "4px" }}>
              <OverrideWarning
                actorName={overrideLogs[0].actor_name}
                actorRole={overrideLogs[0].actor_role}
                assignedAt={overrideLogs[0].created_at}
                reason={overrideLogs[0].justification}
                onViewHistory={() => setShowHistory(true)}
              />
            </div>
          )}

          {/* Countdown Timer */}
          {jobData.sla_deadline && (
            <CountdownTimer
              expiresAt={jobData.sla_deadline}
              onExpire={handleExpire}
              onWarning={handleWarning}
              jobId={jobData.id}
              hidden={isActioned}
            />
          )}

          {/* Job Details Grid */}
          <div className="detail-row-grid" style={{ marginBottom: "8px" }}>
            <div className="detail-grid-item">
              <span className="detail-grid-label">Customer</span>
              <span className="detail-grid-value" style={{ display: "flex", alignItems: "center", gap: "4px", fontSize: "12px" }}>
                <User size={12} color="#64748b" /> {jobData.customer_name}
              </span>
            </div>
            <div className="detail-grid-item">
              <span className="detail-grid-label">Contact</span>
              <span className="detail-grid-value" style={{ fontSize: "12px" }}>
                <a href={`tel:${jobData.customer_phone}`} style={{ display: "flex", alignItems: "center", gap: "4px", color: "#3b82f6", textDecoration: "none" }}>
                  <Phone size={12} /> {jobData.customer_phone}
                </a>
              </span>
            </div>
            <div className="detail-grid-item">
              <span className="detail-grid-label">Distance</span>
              <span className="detail-grid-value" style={{ display: "flex", alignItems: "center", gap: "4px", fontSize: "12px" }}>
                <Navigation size={12} color="#64748b" /> {jobData.distance_km} km
              </span>
            </div>
            <div className="detail-grid-item">
              <span className="detail-grid-label">Est. Value</span>
              <span className="detail-grid-value" style={{ display: "flex", alignItems: "center", gap: "2px", fontWeight: 700, color: "#10b981", fontSize: "12px" }}>
                ${jobData.estimated_value}
              </span>
            </div>
          </div>

          {/* Compact Description */}
          <p className="detail-description">
            {jobData.description}
          </p>

          {/* Inline Location Address (No huge map placeholder!) */}
          <div style={{ display: "flex", alignItems: "center", gap: "6px", margin: "2px 0 6px 0" }}>
            <MapPin size={14} color="#ef4444" className="flex-shrink-0" />
            <span style={{ fontSize: "12px", color: "#475569", fontWeight: 500, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }} title={jobData.location}>
              {jobData.location}
            </span>
          </div>

          {/* Compact Skills Chips */}
          <div className="skills-container" style={{ gap: "4px", marginBottom: "4px" }}>
            {jobData.required_skills?.map((skill: string) => (
              <span key={skill} className="skill-chip" style={{ padding: "2px 6px", fontSize: "10.5px" }}>
                {skill}
              </span>
            ))}
          </div>
        </div>

        {/* Action Buttons (Fixed Footer) */}
        <div style={{ borderTop: "1px solid #f1f5f9", paddingTop: "12px", marginTop: "4px" }}>
          <ActionButtons
            onAccept={handleAccept}
            onReject={handleReject}
            onReassign={handleReassign}
            jobId={jobData.id}
            disabled={actionState !== "IDLE"}
          />
        </div>
      </motion.div>

      {showHistory && (
        <OverrideHistory
          jobId={jobData.id}
          jobTitle={jobData.title}
          onClose={() => setShowHistory(false)}
        />
      )}
    </div>
  );
};

export default NotificationDetail;