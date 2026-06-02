import React from "react";
import { X, Briefcase, Clock, RefreshCw, Info, CheckCheck } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { NotificationDrawerProps, TechnicianNotification } from "../../types/notifications.ts";
import "./notifications.css";

const formatAgo = (ts: string) => {
  if (!ts) return "";
  try {
    const diff = Math.round((Date.now() - new Date(ts).getTime()) / 60000);
    if (diff < 1) return "just now";
    if (diff < 60) return `${diff}m ago`;
    const h = Math.round(diff / 60);
    if (h < 24) return `${h}h ago`;
    return new Date(ts).toLocaleDateString();
  } catch {
    return String(ts);
  }
};

const getTypeIcon = (type: string) => {
  switch (type) {
    case "JOB_ASSIGNED":
      return <Briefcase size={18} />;
    case "SLA_WARNING":
      return <Clock size={18} />;
    case "JOB_UPDATED":
      return <RefreshCw size={18} />;
    case "SYSTEM":
    default:
      return <Info size={18} />;
  }
};

const getTypeClass = (type: string) => {
  switch (type) {
    case "JOB_ASSIGNED":
      return "icon-job_assigned";
    case "SLA_WARNING":
      return "icon-sla_warning";
    case "JOB_UPDATED":
      return "icon-job_updated";
    case "SYSTEM":
    default:
      return "icon-system";
  }
};

export const NotificationDrawer: React.FC<NotificationDrawerProps> = ({
  isOpen,
  onClose,
  notifications,
  onNotificationClick,
  onMarkAllAsRead,
  loading = false
}) => {
  // Check if screen is mobile size for animation style
  const isMobile = typeof window !== "undefined" && window.innerWidth <= 640;

  const drawerVariants = {
    hidden: isMobile ? { y: "100%", x: 0 } : { x: "100%", y: 0 },
    visible: { y: 0, x: 0, transition: { type: "tween", duration: 0.3 } },
    exit: isMobile ? { y: "100%", x: 0 } : { x: "100%", y: 0, transition: { type: "tween", duration: 0.25 } }
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="noc-module">
          {/* Backdrop */}
          <motion.div
            className="notification-drawer-backdrop"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
          />

          {/* Drawer container */}
          <motion.div
            className="notification-drawer"
            role="dialog"
            aria-modal="true"
            aria-label="Notification center"
            variants={drawerVariants}
            initial="hidden"
            animate="visible"
            exit="exit"
          >
            <div className="notification-drawer-header">
              <h2>Notifications</h2>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                {onMarkAllAsRead && notifications.some((n) => !n.isRead) && (
                  <button
                    type="button"
                    className="permission-btn-secondary"
                    style={{ height: "30px", fontSize: "12px", display: "flex", alignItems: "center", gap: "4px" }}
                    onClick={onMarkAllAsRead}
                    title="Mark all as read"
                  >
                    <CheckCheck size={14} /> Mark all read
                  </button>
                )}
                <button
                  type="button"
                  className="close-btn"
                  onClick={onClose}
                  aria-label="Close notifications panel"
                >
                  <X size={20} />
                </button>
              </div>
            </div>

            <div className="notification-drawer-content">
              {loading ? (
                <div className="notification-drawer-empty">
                  <div className="tld-refresh-spinner" style={{ marginBottom: "12px" }} />
                  <span>Loading notifications…</span>
                </div>
              ) : notifications.length === 0 ? (
                <div className="notification-drawer-empty">
                  <div className="notification-drawer-empty-icon">
                    <Briefcase size={36} />
                  </div>
                  <p>All caught up!</p>
                  <span>You have no new notifications.</span>
                </div>
              ) : (
                <div style={{ paddingBottom: "20px" }}>
                  {notifications.map((notification) => (
                    <button
                      key={notification.id}
                      type="button"
                      className={`notification-item ${!notification.isRead ? "notification-item-unread" : ""}`}
                      onClick={() => onNotificationClick(notification)}
                      style={{ width: "100%", borderStyle: "solid" }}
                    >
                      <div className={`notification-item-icon-wrapper ${getTypeClass(notification.type)}`}>
                        {getTypeIcon(notification.type)}
                      </div>
                      <div className="notification-item-details">
                        <p className="notification-item-title">{notification.title}</p>
                        <p className="notification-item-message">{notification.message}</p>
                        <span className="notification-item-time">{formatAgo(notification.createdAt)}</span>
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
};

export default NotificationDrawer;
