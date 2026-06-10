import React, { useEffect, useState } from "react";
import { Bell, BellOff, Check, MessageSquare, Info, Settings } from "lucide-react";
import { PermissionRequestProps } from "../../types/notifications.ts";

const COOLDOWN_DAYS = 7;

const styles = {
  container: {
    boxSizing: "border-box",
  } as React.CSSProperties,

  permissionCard: {
    backgroundColor: "#ffffff",
    border: "1px solid #e2e8f0",
    borderRadius: "12px",
    padding: "20px",
    boxShadow: "0 2px 8px rgba(15, 23, 42, 0.04)",
    maxWidth: "600px",
    marginLeft: "auto",
    marginRight: "auto",
    boxSizing: "border-box",
  } as React.CSSProperties,

  permissionHeader: {
    display: "flex",
    alignItems: "flex-start",
    gap: "12px",
    marginBottom: "14px",
  } as React.CSSProperties,

  permissionIconWrapper: {
    color: "#3b82f6",
    flexShrink: 0,
    marginTop: "2px",
  } as React.CSSProperties,

  permissionTitle: {
    fontSize: "15px",
    fontWeight: 600,
    color: "#1e293b",
    margin: "0 0 4px 0",
  } as React.CSSProperties,

  permissionText: {
    fontSize: "13px",
    color: "#64748b",
    margin: 0,
    lineHeight: 1.4,
  } as React.CSSProperties,

  permissionActions: {
    display: "flex",
    gap: "10px",
    flexWrap: "wrap",
    justifyContent: "flex-end",
  } as React.CSSProperties,

  btnPrimary: {
    height: "36px",
    padding: "0 14px",
    fontSize: "13px",
    fontWeight: 600,
    color: "#ffffff",
    backgroundColor: "#3b82f6",
    border: "none",
    borderRadius: "6px",
    cursor: "pointer",
    transition: "background-color 0.2s",
  } as React.CSSProperties,

  btnSecondary: {
    height: "36px",
    padding: "0 14px",
    fontSize: "13px",
    fontWeight: 600,
    color: "#64748b",
    backgroundColor: "#f1f5f9",
    border: "none",
    borderRadius: "6px",
    cursor: "pointer",
    transition: "all 0.2s",
  } as React.CSSProperties,

  compactPill: {
    display: "inline-flex",
    alignItems: "center",
    gap: "8px",
    backgroundColor: "#eff6ff",
    border: "1px solid #bfdbfe",
    padding: "4px 10px",
    borderRadius: "20px",
    fontSize: "12px",
    fontWeight: 600,
    color: "#1e3a8a",
    height: "30px",
    boxShadow: "0 1px 2px rgba(0, 0, 0, 0.05)",
  } as React.CSSProperties,

  compactBtnEnable: {
    backgroundColor: "#2563eb",
    color: "#ffffff",
    border: "none",
    borderRadius: "12px",
    padding: "2px 8px",
    fontSize: "11px",
    fontWeight: 700,
    cursor: "pointer",
    transition: "background-color 0.2s",
    height: "20px",
    display: "flex",
    alignItems: "center",
    lineHeight: 1,
  } as React.CSSProperties,

  compactBtnDismiss: {
    background: "transparent",
    border: "none",
    color: "#94a3b8",
    cursor: "pointer",
    fontSize: "14px",
    padding: "0 2px",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    lineHeight: 1,
  } as React.CSSProperties,

  smsContainer: {
    marginTop: "14px",
    paddingTop: "14px",
    borderTop: "1px dashed #e2e8f0",
    display: "flex",
    flexDirection: "column",
    gap: "8px",
  } as React.CSSProperties,
};

const localCss = `
  @keyframes pulseIcon {
    0% { transform: scale(0.95); opacity: 0.85; }
    50% { transform: scale(1.15); opacity: 1; }
    100% { transform: scale(0.95); opacity: 0.85; }
  }
  .pulse-icon-style {
    animation: pulseIcon 2s infinite;
  }
  .btn-primary-style:hover { background-color: #2563eb !important; }
  .btn-secondary-style:hover { background-color: #e2e8f0 !important; color: #1e293b !important; }
  .compact-btn-enable-style:hover { background-color: #1d4ed8 !important; }
  .compact-btn-dismiss-style:hover { color: #64748b !important; }
  
  @media (max-width: 640px) {
    .permission-card-responsive {
      padding: 16px !important;
      margin: 12px !important;
    }
  }
`;

export const PermissionRequest: React.FC<PermissionRequestProps> = ({
  onPermissionChange,
  className = "",
  compact = false
}) => {
  const [permission, setPermission] = useState<string>("default");
  const [isSupported, setIsSupported] = useState<boolean>(true);
  const [isIOSDevice, setIsIOSDevice] = useState<boolean>(false);
  const [isAppStandalone, setIsAppStandalone] = useState<boolean>(false);
  const [inCooldown, setInCooldown] = useState<boolean>(false);
  const [showSMSForm, setShowSMSForm] = useState<boolean>(false);
  const [phoneNumber, setPhoneNumber] = useState<string>("");
  const [smsRegistered, setSmsRegistered] = useState<boolean>(false);
  const [dismissed, setDismissed] = useState<boolean>(false);

  useEffect(() => {
    // Detect environment support
    if (typeof window === "undefined") return;

    const hasNotificationSupport = "Notification" in window;
    setIsSupported(hasNotificationSupport);

    if (hasNotificationSupport) {
      setPermission(Notification.permission);
    } else {
      setPermission("unsupported");
    }

    // Detect iOS
    const userAgent = window.navigator.userAgent;
    const isIOS = /iPad|iPhone|iPod/.test(userAgent) && !(window as any).MSStream;
    setIsIOSDevice(isIOS);

    const isStandalone = window.matchMedia("(display-mode: standalone)").matches || (window.navigator as any).standalone;
    setIsAppStandalone(!!isStandalone);

    // Check localStorage state and cooldown
    const savedStatus = localStorage.getItem("push_permission_status");
    if (savedStatus) {
      setPermission(savedStatus);
    }

    const deniedAt = localStorage.getItem("push_permission_denied_at");
    if (deniedAt) {
      const diffTime = Math.abs(Date.now() - new Date(deniedAt).getTime());
      const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
      if (diffDays <= COOLDOWN_DAYS) {
        setInCooldown(true);
      }
    }

    const maybeLaterAt = localStorage.getItem("push_permission_maybe_later_at");
    if (maybeLaterAt) {
      const diffTime = Math.abs(Date.now() - new Date(maybeLaterAt).getTime());
      const diffHours = Math.ceil(diffTime / (1000 * 60 * 60));
      if (diffHours < 24) {
        setDismissed(true); // hide for 24 hours on maybe later
      }
    }
  }, []);

  const requestPermission = async () => {
    if (typeof window === "undefined" || !isSupported) return;

    try {
      const result = await Notification.requestPermission();
      setPermission(result);
      localStorage.setItem("push_permission_status", result);

      if (result === "granted") {
        localStorage.removeItem("push_permission_denied_at");
        localStorage.removeItem("push_permission_maybe_later_at");
        const mockToken = "mock_fcm_token_" + Math.random().toString(36).substring(7);
        localStorage.setItem("push_fcm_token", mockToken);
        if (onPermissionChange) onPermissionChange("granted");
      } else if (result === "denied") {
        localStorage.setItem("push_permission_denied_at", new Date().toISOString());
        setInCooldown(true);
        if (onPermissionChange) onPermissionChange("denied");
      }
    } catch (error) {
      console.error("Error requesting notification permission:", error);
    }
  };

  const handleMaybeLater = () => {
    localStorage.setItem("push_permission_maybe_later_at", new Date().toISOString());
    setDismissed(true);
  };

  const handleRegisterSMS = (e: React.FormEvent) => {
    e.preventDefault();
    if (phoneNumber.trim()) {
      localStorage.setItem("sms_notification_phone", phoneNumber);
      setSmsRegistered(true);
      setTimeout(() => setShowSMSForm(false), 2000);
    }
  };

  const resetPermissionDemo = () => {
    localStorage.removeItem("push_permission_status");
    localStorage.removeItem("push_permission_denied_at");
    localStorage.removeItem("push_permission_maybe_later_at");
    setPermission(isSupported ? "default" : "unsupported");
    setInCooldown(false);
    setDismissed(false);
    if (onPermissionChange) onPermissionChange("default");
  };

  if (dismissed || (inCooldown && permission === "denied")) {
    if (compact) return null;
    return (
      <div style={styles.container} className={`noc-module ${className}`} style={{ marginBottom: "16px", textAlign: "right" }}>
        <style>{localCss}</style>
        <button
          type="button"
          className="btn-secondary-style"
          style={{ ...styles.btnSecondary, fontSize: "11px", height: "26px", padding: "0 8px" }}
          onClick={resetPermissionDemo}
        >
          Reset Demo Status
        </button>
      </div>
    );
  }

  // State: Unsupported
  if (!isSupported || permission === "unsupported") {
    if (compact) {
      return (
        <div style={styles.container} className={`noc-module ${className}`}>
          <style>{localCss}</style>
          <div 
            style={{ ...styles.compactPill, backgroundColor: "#f8fafc", borderColor: "#e2e8f0", color: "#475569" }}
            title="Push notifications not supported on this browser"
          >
            <BellOff size={14} />
            <span>Notifications Unsupported</span>
          </div>
        </div>
      );
    }
    return (
      <div style={styles.container} className={`noc-module ${className}`}>
        <style>{localCss}</style>
        <div style={styles.permissionCard} className="permission-card-responsive">
          <div style={styles.permissionHeader}>
            <div style={{ ...styles.permissionIconWrapper, color: "#ef4444" }}>
              <BellOff size={22} />
            </div>
            <div>
              <h3 style={styles.permissionTitle}>Push Notifications Not Supported</h3>
              <p style={styles.permissionText}>
                Your browser or system does not support push notifications. You can still use SMS alerts instead.
              </p>
            </div>
          </div>
          <div style={styles.permissionActions}>
            <button
              type="button"
              className="btn-primary-style"
              style={styles.btnPrimary}
              onClick={() => setShowSMSForm(!showSMSForm)}
            >
              Use SMS Instead
            </button>
          </div>
          {showSMSForm && renderSMSForm()}
        </div>
      </div>
    );
  }

  // State: iOS safari but not standalone
  if (isIOSDevice && !isAppStandalone && permission === "default") {
    if (compact) {
      return (
        <div style={styles.container} className={`noc-module ${className}`}>
          <style>{localCss}</style>
          <div 
            style={{ ...styles.compactPill, backgroundColor: "#f8fafc", borderColor: "#e2e8f0", color: "#475569" }}
            title="To enable alerts, tap Share -> Add to Home Screen"
          >
            <Info size={14} />
            <span>iOS Safari: Add to Home Screen</span>
          </div>
        </div>
      );
    }
    return (
      <div style={styles.container} className={`noc-module ${className}`}>
        <style>{localCss}</style>
        <div style={styles.permissionCard} className="permission-card-responsive">
          <div style={styles.permissionHeader}>
            <div style={{ ...styles.permissionIconWrapper, color: "#f59e0b" }}>
              <Info size={22} />
            </div>
            <div>
              <h3 style={styles.permissionTitle}>iOS Notification Requirements</h3>
              <p style={styles.permissionText}>
                To receive job alerts on iOS Safari, tap the Share button and select <strong>"Add to Home Screen"</strong>, then open the app from your home screen.
              </p>
            </div>
          </div>
          <div style={styles.permissionActions}>
            <button type="button" className="btn-secondary-style" style={styles.btnSecondary} onClick={handleMaybeLater}>
              Maybe Later
            </button>
            <button type="button" className="btn-primary-style" style={styles.btnPrimary} onClick={() => setShowSMSForm(!showSMSForm)}>
              Use SMS Fallback
            </button>
          </div>
          {showSMSForm && renderSMSForm()}
        </div>
      </div>
    );
  }

  // State: Granted
  if (permission === "granted") {
    if (compact) {
      return (
        <div style={styles.container} className={`noc-module ${className}`}>
          <style>{localCss}</style>
          <div 
            style={{ ...styles.compactPill, backgroundColor: "#f0fdf4", borderColor: "#bbf7d0", color: "#166534", cursor: "pointer" }}
            onClick={resetPermissionDemo} 
            title="Click to reset (demo)"
          >
            <Check size={14} />
            <span>Notifications Active</span>
          </div>
        </div>
      );
    }
    return (
      <div style={styles.container} className={`noc-module ${className}`}>
        <style>{localCss}</style>
        <div style={{ ...styles.permissionCard, borderColor: "#10b981", backgroundColor: "#f0fdf4" }} className="permission-card-responsive">
          <div style={styles.permissionHeader}>
            <div style={{ ...styles.permissionIconWrapper, color: "#10b981" }}>
              <Check size={22} />
            </div>
            <div>
              <h3 style={{ ...styles.permissionTitle, color: "#065f46" }}>Push Notifications Enabled</h3>
              <p style={{ ...styles.permissionText, color: "#047857" }}>
                You will receive real-time updates and job assignments immediately.
              </p>
            </div>
          </div>
          <div style={styles.permissionActions}>
            <button
              type="button"
              className="btn-secondary-style"
              style={{ ...styles.btnSecondary, color: "#047857", backgroundColor: "#d1fae5" }}
              onClick={resetPermissionDemo}
            >
              Reset Permissions
            </button>
          </div>
        </div>
      </div>
    );
  }

  // State: Denied
  if (permission === "denied") {
    if (compact) {
      return (
        <div style={styles.container} className={`noc-module ${className}`}>
          <style>{localCss}</style>
          <div 
            style={{ ...styles.compactPill, backgroundColor: "#fef2f2", borderColor: "#fecaca", color: "#991b1b", cursor: "pointer" }}
            onClick={resetPermissionDemo} 
            title="Push notifications blocked. Click to reset demo."
          >
            <BellOff size={14} />
            <span>Notifications Blocked</span>
          </div>
        </div>
      );
    }
    return (
      <div style={styles.container} className={`noc-module ${className}`}>
        <style>{localCss}</style>
        <div style={{ ...styles.permissionCard, borderColor: "#fca5a5" }} className="permission-card-responsive">
          <div style={styles.permissionHeader}>
            <div style={{ ...styles.permissionIconWrapper, color: "#ef4444" }}>
              <BellOff size={22} />
            </div>
            <div>
              <h3 style={styles.permissionTitle}>Push Notifications Blocked</h3>
              <p style={styles.permissionText}>
                Notifications are blocked. You can re-enable them in your browser settings to receive job alerts, or activate SMS fallback.
              </p>
              <div style={{ display: "flex", alignItems: "center", gap: "6px", marginTop: "8px", fontSize: "12px", color: "#64748b" }}>
                <Settings size={14} />
                <span>To unblock: Click the lock/settings icon in the URL bar and change notifications to 'Allow'.</span>
              </div>
            </div>
          </div>
          <div style={styles.permissionActions}>
            <button
              type="button"
              className="btn-primary-style"
              style={styles.btnPrimary}
              onClick={() => setShowSMSForm(!showSMSForm)}
            >
              Use SMS Instead
            </button>
            <button type="button" className="btn-secondary-style" style={styles.btnSecondary} onClick={resetPermissionDemo}>
              Reset Demo
            </button>
          </div>
          {showSMSForm && renderSMSForm()}
        </div>
      </div>
    );
  }

  // State: Default
  if (compact) {
    return (
      <div style={styles.container} className={`noc-module ${className}`}>
        <style>{localCss}</style>
        <div style={styles.compactPill}>
          <Bell size={14} className="pulse-icon-style" />
          <span>Enable Notifications?</span>
          <button type="button" className="compact-btn-enable-style" style={styles.compactBtnEnable} onClick={requestPermission}>Enable</button>
          <button type="button" className="compact-btn-dismiss-style" style={styles.compactBtnDismiss} onClick={handleMaybeLater} title="Maybe Later">×</button>
        </div>
      </div>
    );
  }

  return (
    <div style={styles.container} className={`noc-module ${className}`}>
      <style>{localCss}</style>
      <div style={styles.permissionCard} className="permission-card-responsive">
        <div style={styles.permissionHeader}>
          <div style={styles.permissionIconWrapper}>
            <Bell size={22} />
          </div>
          <div>
            <h3 style={styles.permissionTitle}>Enable Push Notifications</h3>
            <p style={styles.permissionText}>
              Get instant alerts for new jobs. Never miss an assignment.
            </p>
          </div>
        </div>
        <div style={styles.permissionActions}>
          <button type="button" className="btn-secondary-style" style={styles.btnSecondary} onClick={handleMaybeLater}>
            Maybe Later
          </button>
          <button type="button" className="btn-primary-style" style={styles.btnPrimary} onClick={requestPermission}>
            Enable Notifications
          </button>
        </div>
      </div>
    </div>
  );

  function renderSMSForm() {
    return (
      <div style={styles.smsContainer}>
        <p style={{ fontSize: "13px", fontWeight: 600, color: "#334155", margin: "0 0 4px 0" }}>
          SMS Alerts Subscription
        </p>
        {smsRegistered ? (
          <div style={{ display: "flex", alignItems: "center", gap: "6px", color: "#166534", fontSize: "13px" }}>
            <Check size={14} /> Registered phone number successfully!
          </div>
        ) : (
          <form onSubmit={handleRegisterSMS} style={{ display: "flex", gap: "8px" }}>
            <input
              type="tel"
              placeholder="+91 98765-43210"
              style={{
                height: "36px",
                padding: "10px",
                border: "1px solid #cbd5e1",
                borderRadius: "6px",
                fontFamily: "inherit",
                fontSize: "14px",
                resize: "none",
                boxSizing: "border-box",
                marginBottom: 0,
                flex: 1,
              }}
              value={phoneNumber}
              onChange={(e) => setPhoneNumber(e.target.value)}
              required
            />
            <button
              type="submit"
              className="btn-primary-style"
              style={{ ...styles.btnPrimary, height: "36px", display: "flex", alignItems: "center", gap: "4px" }}
            >
              <MessageSquare size={14} /> Subscribe
            </button>
          </form>
        )}
      </div>
    );
  }
};

export default PermissionRequest;
