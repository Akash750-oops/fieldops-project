import { useState } from "react";
import { Settings, Key, AlertCircle, CheckCircle } from "lucide-react";
import { changeCustomerPassword } from "../../services/customerPortalService";

export default function CustomerSettingsPage() {
  const [currentPw, setCurrentPw] = useState("");
  const [newPw, setNewPw] = useState("");
  const [confirmPw, setConfirmPw] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const handleChangePassword = async () => {
    setError("");
    setSuccess("");
    if (newPw.length < 8) {
      setError("New password must be at least 8 characters");
      return;
    }
    if (newPw !== confirmPw) {
      setError("Passwords do not match");
      return;
    }
    setSaving(true);
    try {
      await changeCustomerPassword({ current_password: currentPw, new_password: newPw, confirm_password: confirmPw });
      setSuccess("Password changed successfully");
      setCurrentPw("");
      setNewPw("");
      setConfirmPw("");
    } catch (e: any) {
      setError(e.response?.data?.detail || "Failed to change password");
    } finally {
      setSaving(false);
    }
  };

  const inputStyle = { width: "100%", padding: "10px 12px", border: "1.5px solid #D1D5DB", borderRadius: "8px", fontSize: "14px", boxSizing: "border-box" as const, outline: "none", fontFamily: "'Inter', sans-serif" };
  const labelStyle = { fontSize: "12px", fontWeight: 600, color: "#374151", marginBottom: "4px", display: "block" as const };

  return (
    <div style={{ padding: "24px", height: "100%", overflowY: "auto", background: "#EEF4F1", fontFamily: "'Inter', sans-serif" }}>
      <div style={{ background: "#fff", borderRadius: "14px", padding: "28px", maxWidth: "500px", margin: "0 auto", boxShadow: "0 2px 8px rgba(0,0,0,0.06)", border: "1px solid #E3ECE7" }}>
        <h2 style={{ fontSize: "22px", fontWeight: 700, color: "#1F2933", marginBottom: "20px", display: "flex", alignItems: "center", gap: "8px" }}>
          <Settings size={22} color="#7AAE8A" /> Settings
        </h2>
        <div style={{ fontSize: "15px", fontWeight: 700, color: "#2F4F3E", marginBottom: "16px", display: "flex", alignItems: "center", gap: "6px" }}>
          <Key size={16} /> Change Password
        </div>
        {error && (
          <div style={{ background: "#FEF2F2", border: "1px solid #FECACA", borderRadius: "8px", padding: "10px 14px", color: "#991B1B", fontSize: "13px", marginBottom: "16px", display: "flex", alignItems: "center", gap: "8px" }}>
            <AlertCircle size={16} /> {error}
          </div>
        )}
        {success && (
          <div style={{ background: "#F0FFF4", border: "1px solid #C6F6D5", borderRadius: "8px", padding: "10px 14px", color: "#22543D", fontSize: "13px", marginBottom: "16px", display: "flex", alignItems: "center", gap: "8px" }}>
            <CheckCircle size={16} /> {success}
          </div>
        )}
        <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
          <div>
            <label style={labelStyle}>Current Password</label>
            <input type="password" style={inputStyle} value={currentPw} onChange={(e) => setCurrentPw(e.target.value)} />
          </div>
          <div>
            <label style={labelStyle}>New Password (min 8 chars)</label>
            <input type="password" style={inputStyle} value={newPw} onChange={(e) => setNewPw(e.target.value)} />
          </div>
          <div>
            <label style={labelStyle}>Confirm New Password</label>
            <input type="password" style={inputStyle} value={confirmPw} onChange={(e) => setConfirmPw(e.target.value)} />
          </div>
          <button onClick={handleChangePassword} disabled={saving} style={{ padding: "12px", border: "none", borderRadius: "10px", fontSize: "14px", fontWeight: 700, cursor: "pointer", background: "#7AAE8A", color: "#fff", opacity: saving ? 0.7 : 1 }}>
            {saving ? "Changing..." : "Change Password"}
          </button>
        </div>
      </div>
    </div>
  );
}
