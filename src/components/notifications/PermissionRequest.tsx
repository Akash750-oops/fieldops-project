import React, { useEffect, useState } from "react";
import { Bell, BellOff, Check, MessageSquare, AlertCircle, Info, Settings } from "lucide-react";
import { PermissionRequestProps } from "../../types/notifications.ts";
import "./notifications.css";

const COOLDOWN_DAYS = 7;

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
      <div className={`noc-module ${className}`} style={{ marginBottom: "16px", textAlign: "right" }}>
        <button
          type="button"
          className="permission-btn-secondary"
          onClick={resetPermissionDemo}
          style={{ fontSize: "11px", height: "26px", padding: "0 8px" }}
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
        <div className={`noc-module ${className}`}>
          <div className="compact-permission-pill unsupported" title="Push notifications not supported on this browser">
            <BellOff size={14} />
            <span>Notifications Unsupported</span>
          </div>
        </div>
      );
    }
    return (
      <div className={`noc-module ${className}`}>
        <div className="permission-card">
          <div className="permission-header">
            <div className="permission-icon-wrapper" style={{ color: "#ef4444" }}>
              <BellOff size={22} />
            </div>
            <div>
              <h3 className="permission-title">Push Notifications Not Supported</h3>
              <p className="permission-text">
                Your browser or system does not support push notifications. You can still use SMS alerts instead.
              </p>
            </div>
          </div>
          <div className="permission-actions">
            <button
              type="button"
              className="permission-btn-primary"
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
        <div className={`noc-module ${className}`}>
          <div className="compact-permission-pill unsupported" title="To enable alerts, tap Share -> Add to Home Screen">
            <Info size={14} />
            <span>iOS Safari: Add to Home Screen</span>
          </div>
        </div>
      );
    }
    return (
      <div className={`noc-module ${className}`}>
        <div className="permission-card">
          <div className="permission-header">
            <div className="permission-icon-wrapper" style={{ color: "#f59e0b" }}>
              <Info size={22} />
            </div>
            <div>
              <h3 className="permission-title">iOS Notification Requirements</h3>
              <p className="permission-text">
                To receive job alerts on iOS Safari, tap the Share button and select <strong>"Add to Home Screen"</strong>, then open the app from your home screen.
              </p>
            </div>
          </div>
          <div className="permission-actions">
            <button type="button" className="permission-btn-secondary" onClick={handleMaybeLater}>
              Maybe Later
            </button>
            <button type="button" className="permission-btn-primary" onClick={() => setShowSMSForm(!showSMSForm)}>
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
        <div className={`noc-module ${className}`}>
          <div className="compact-permission-pill granted" onClick={resetPermissionDemo} style={{ cursor: "pointer" }} title="Click to reset (demo)">
            <Check size={14} />
            <span>Notifications Active</span>
          </div>
        </div>
      );
    }
    return (
      <div className={`noc-module ${className}`}>
        <div className="permission-card" style={{ borderColor: "#10b981", backgroundColor: "#f0fdf4" }}>
          <div className="permission-header">
            <div className="permission-icon-wrapper" style={{ color: "#10b981" }}>
              <Check size={22} />
            </div>
            <div>
              <h3 className="permission-title" style={{ color: "#065f46" }}>Push Notifications Enabled</h3>
              <p className="permission-text" style={{ color: "#047857" }}>
                You will receive real-time updates and job assignments immediately.
              </p>
            </div>
          </div>
          <div className="permission-actions">
            <button
              type="button"
              className="permission-btn-secondary"
              style={{ color: "#047857", backgroundColor: "#d1fae5" }}
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
        <div className={`noc-module ${className}`}>
          <div className="compact-permission-pill blocked" onClick={resetPermissionDemo} title="Push notifications blocked. Click to reset demo.">
            <BellOff size={14} />
            <span>Notifications Blocked</span>
          </div>
        </div>
      );
    }
    return (
      <div className={`noc-module ${className}`}>
        <div className="permission-card" style={{ borderColor: "#fca5a5" }}>
          <div className="permission-header">
            <div className="permission-icon-wrapper" style={{ color: "#ef4444" }}>
              <BellOff size={22} />
            </div>
            <div>
              <h3 className="permission-title">Push Notifications Blocked</h3>
              <p className="permission-text">
                Notifications are blocked. You can re-enable them in your browser settings to receive job alerts, or activate SMS fallback.
              </p>
              <div style={{ display: "flex", alignItems: "center", gap: "6px", marginTop: "8px", fontSize: "12px", color: "#64748b" }}>
                <Settings size={14} />
                <span>To unblock: Click the lock/settings icon in the URL bar and change notifications to 'Allow'.</span>
              </div>
            </div>
          </div>
          <div className="permission-actions">
            <button
              type="button"
              className="permission-btn-primary"
              onClick={() => setShowSMSForm(!showSMSForm)}
            >
              Use SMS Instead
            </button>
            <button type="button" className="permission-btn-secondary" onClick={resetPermissionDemo}>
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
      <div className={`noc-module ${className}`}>
        <div className="compact-permission-pill">
          <Bell size={14} className="pulse-icon" />
          <span>Enable Notifications?</span>
          <button type="button" className="compact-btn-enable" onClick={requestPermission}>Enable</button>
          <button type="button" className="compact-btn-dismiss" onClick={handleMaybeLater} title="Maybe Later">×</button>
        </div>
      </div>
    );
  }

  return (
    <div className={`noc-module ${className}`}>
      <div className="permission-card">
        <div className="permission-header">
          <div className="permission-icon-wrapper">
            <Bell size={22} />
          </div>
          <div>
            <h3 className="permission-title">Enable Push Notifications</h3>
            <p className="permission-text">
              Get instant alerts for new jobs. Never miss an assignment.
            </p>
          </div>
        </div>
        <div className="permission-actions">
          <button type="button" className="permission-btn-secondary" onClick={handleMaybeLater}>
            Maybe Later
          </button>
          <button type="button" className="permission-btn-primary" onClick={requestPermission}>
            Enable Notifications
          </button>
        </div>
      </div>
    </div>
  );

  function renderSMSForm() {
    return (
      <div className="sms-fallback-container">
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
              className="rejection-textarea"
              placeholder="+91 98765-43210"
              style={{ height: "36px", marginBottom: 0, flex: 1 }}
              value={phoneNumber}
              onChange={(e) => setPhoneNumber(e.target.value)}
              required
            />
            <button
              type="submit"
              className="permission-btn-primary"
              style={{ height: "36px", display: "flex", alignItems: "center", gap: "4px" }}
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
