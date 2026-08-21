import { useState } from "react";
import {
  Settings,
  LockKeyhole,
  AlertCircle,
  CheckCircle,
  Eye,
  EyeOff,
} from "lucide-react";
import { changeCustomerPassword } from "../../services/customerPortalService";

export default function CustomerSettingsPage() {
  const [currentPw, setCurrentPw] = useState("");
  const [newPw, setNewPw] = useState("");
  const [confirmPw, setConfirmPw] = useState("");

  const [showCurrentPw, setShowCurrentPw] = useState(false);
  const [showNewPw, setShowNewPw] = useState(false);

  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const validatePassword = (password: string): string | null => {
    if (!password) {
      return "New password is required";
    }

    if (password.length < 8) {
      return "New password must be at least 8 characters";
    }

    if (!/[A-Z]/.test(password)) {
      return "New password must contain at least one uppercase letter";
    }

    if (!/[a-z]/.test(password)) {
      return "New password must contain at least one lowercase letter";
    }

    if (!/[0-9]/.test(password)) {
      return "New password must contain at least one number";
    }

    if (!/[!@#$%^&*(),.?":{}|<>_\-\\[\]/;'`~+=]/.test(password)) {
      return "New password must contain at least one special character";
    }

    return null;
  };

  const handleChangePassword = async () => {
    setError("");
    setSuccess("");

    // Current password required
    if (!currentPw.trim()) {
      setError("Current password is required");
      return;
    }

    // New password validation
    const passwordError = validatePassword(newPw);

    if (passwordError) {
      setError(passwordError);
      return;
    }

    // New password should be different
    // from current password
    if (currentPw === newPw) {
      setError("New password must be different from current password");
      return;
    }

    // Confirm password required
    if (!confirmPw) {
      setError("Confirm new password is required");
      return;
    }

    // Confirm password must match
    if (newPw !== confirmPw) {
      setError("Passwords do not match");
      return;
    }

    setSaving(true);

    try {
      await changeCustomerPassword({
        current_password: currentPw,
        new_password: newPw,
        confirm_password: confirmPw,
      });

      setSuccess("Password changed successfully");

      setCurrentPw("");
      setNewPw("");
      setConfirmPw("");

      setShowCurrentPw(false);
      setShowNewPw(false);
    } catch (e: any) {
      setError(e.response?.data?.detail || "Failed to change password");
    } finally {
      setSaving(false);
    }
  };

  const inputStyle = {
    width: "100%",
    height: "44px",
    padding: "10px 44px 10px 12px",
    border: "1.5px solid #D1D5DB",
    borderRadius: "8px",
    fontSize: "14px",
    boxSizing: "border-box" as const,
    outline: "none",
    fontFamily: "'Inter', sans-serif",
    color: "#1F2933",
    background: "#FFFFFF",
  };

  const labelStyle = {
    fontSize: "13px",
    fontWeight: 600,
    color: "#1F2937",
    marginBottom: "6px",
    display: "block" as const,
  };

  const eyeButtonStyle = {
    position: "absolute" as const,
    right: "12px",
    top: "50%",
    transform: "translateY(-50%)",
    border: "none",
    background: "transparent",
    padding: "2px",
    margin: 0,
    cursor: "pointer",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    color: "#374151",
  };

  return (
    <div
      style={{
        padding: "24px",
        height: "100%",
        overflowY: "auto",
        background: "#EEF4F1",
        fontFamily: "'Inter', sans-serif",
      }}
    >
      <div
        style={{
          background: "#FFFFFF",
          borderRadius: "14px",
          padding: "28px",
          maxWidth: "500px",
          margin: "0 auto",
          boxShadow: "0 2px 8px rgba(0,0,0,0.06)",
          border: "1px solid #E3ECE7",
        }}
      >
        {/* PAGE TITLE */}
        <h2
          style={{
            fontSize: "22px",
            fontWeight: 700,
            color: "#1F2933",
            marginBottom: "20px",
            display: "flex",
            alignItems: "center",
            gap: "8px",
          }}
        >
          <Settings size={22} color="#7AAE8A" />
          Settings
        </h2>

        {/* CHANGE PASSWORD TITLE */}
        <div
          style={{
            fontSize: "15px",
            fontWeight: 700,
            color: "#244536",
            marginBottom: "18px",
            display: "flex",
            alignItems: "center",
            gap: "7px",
          }}
        >
          <LockKeyhole size={17} color="#2F4F3E" />
          Change Password
        </div>

        {/* ERROR MESSAGE */}
        {error && (
          <div
            style={{
              background: "#FEF2F2",
              border: "1px solid #FECACA",
              borderRadius: "8px",
              padding: "10px 14px",
              color: "#991B1B",
              fontSize: "13px",
              marginBottom: "16px",
              display: "flex",
              alignItems: "center",
              gap: "8px",
            }}
          >
            <AlertCircle size={16} />
            <span>{error}</span>
          </div>
        )}

        {/* SUCCESS MESSAGE */}
        {success && (
          <div
            style={{
              background: "#F0FFF4",
              border: "1px solid #C6F6D5",
              borderRadius: "8px",
              padding: "10px 14px",
              color: "#22543D",
              fontSize: "13px",
              marginBottom: "16px",
              display: "flex",
              alignItems: "center",
              gap: "8px",
            }}
          >
            <CheckCircle size={16} />
            <span>{success}</span>
          </div>
        )}

        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: "14px",
          }}
        >
          {/* CURRENT PASSWORD */}
          <div>
            <label style={labelStyle}>
              Current Password <span style={{ color: "#DC2626" }}>*</span>
            </label>

            <div style={{ position: "relative" }}>
              <input
                type={showCurrentPw ? "text" : "password"}
                style={inputStyle}
                value={currentPw}
                onChange={(e) => {
                  setCurrentPw(e.target.value);
                  setError("");
                  setSuccess("");
                }}
              />

              <button
                type="button"
                onClick={() => setShowCurrentPw((prev) => !prev)}
                style={eyeButtonStyle}
                aria-label={
                  showCurrentPw
                    ? "Hide current password"
                    : "Show current password"
                }
              >
                {showCurrentPw ? <Eye size={19} /> : <EyeOff size={19} />}
              </button>
            </div>
          </div>

          {/* NEW PASSWORD */}
          <div>
            <label style={labelStyle}>
              New Password <span style={{ color: "#DC2626" }}>*</span>
            </label>

            <div style={{ position: "relative" }}>
              <input
                type={showNewPw ? "text" : "password"}
                style={inputStyle}
                value={newPw}
                onChange={(e) => {
                  setNewPw(e.target.value);
                  setError("");
                  setSuccess("");
                }}
              />

              <button
                type="button"
                onClick={() => setShowNewPw((prev) => !prev)}
                style={eyeButtonStyle}
                aria-label={
                  showNewPw ? "Hide new password" : "Show new password"
                }
              >
                {showNewPw ? <Eye size={19} /> : <EyeOff size={19} />}
              </button>
            </div>
          </div>

          {/* CONFIRM NEW PASSWORD */}
          <div>
            <label style={labelStyle}>
              Confirm New Password <span style={{ color: "#DC2626" }}>*</span>
            </label>

            <input
              type="password"
              style={{
                ...inputStyle,
                paddingRight: "12px",
              }}
              value={confirmPw}
              onChange={(e) => {
                setConfirmPw(e.target.value);
                setError("");
                setSuccess("");
              }}
            />
          </div>

          {/* CHANGE PASSWORD BUTTON */}
          <button
            type="button"
            onClick={handleChangePassword}
            disabled={saving}
            style={{
              padding: "12px",
              border: "none",
              borderRadius: "10px",
              fontSize: "14px",
              fontWeight: 700,
              cursor: saving ? "not-allowed" : "pointer",
              background: "#7AAE8A",
              color: "#FFFFFF",
              opacity: saving ? 0.7 : 1,
              marginTop: "2px",
            }}
          >
            {saving ? "Changing..." : "Change Password"}
          </button>
        </div>
      </div>
    </div>
  );
}
