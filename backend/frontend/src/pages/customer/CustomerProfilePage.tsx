import { useState, useEffect } from "react";
import { User, Save, AlertCircle, CheckCircle } from "lucide-react";
import { getCustomerProfile, createCustomerProfile, updateCustomerProfile } from "../../services/customerPortalService";
import useAuthStore from "../../store/authStore";

const inputStyle = { width: "100%", padding: "10px 12px", border: "1.5px solid #D1D5DB", borderRadius: "8px", fontSize: "14px", fontFamily: "'Inter', sans-serif", outline: "none", boxSizing: "border-box" as const };
const labelStyle = { fontSize: "12px", fontWeight: 600, color: "#374151", marginBottom: "4px", display: "block" as const };

export default function CustomerProfilePage() {
  const { user } = useAuthStore();
  const [isNew, setIsNew] = useState(true);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [form, setForm] = useState({ full_name: "", mobile_number: "", address: "", city: "", state: "", pincode: "", company_name: "" });

  useEffect(() => {
    getCustomerProfile().then(r => {
      const p = r.data;
      if (p.profile_completed) {
        setIsNew(false);
        setForm({ full_name: p.full_name || "", mobile_number: p.mobile_number || "", address: p.address || "", city: p.city || "", state: p.state || "", pincode: p.pincode || "", company_name: p.company_name || "" });
      } else {
        setForm(f => ({ ...f, full_name: user ? `${user.first_name} ${user.last_name}` : "" }));
      }
    }).catch(() => {}).finally(() => setLoading(false));
  }, []);

  const handleSave = async () => {
    setError(""); setSuccess(""); setSaving(true);
    try {
      if (!form.full_name.trim()) { setError("Full name is required"); setSaving(false); return; }
      if (!form.mobile_number.trim()) { setError("Mobile number is required"); setSaving(false); return; }
      if (isNew) { await createCustomerProfile(form); setIsNew(false); setSuccess("Profile created!"); }
      else { await updateCustomerProfile(form); setSuccess("Profile updated!"); }
    } catch (e: any) { setError(e.response?.data?.detail || "Failed to save"); }
    finally { setSaving(false); }
  };

  const upd = (k: string, v: string) => setForm(f => ({ ...f, [k]: v }));
  if (loading) return <div style={{ padding: "24px", background: "#EEF4F1", height: "100%", textAlign: "center", paddingTop: "80px", color: "#9CA3AF" }}>Loading...</div>;

  return (
    <div style={{ padding: "24px", height: "100%", overflowY: "auto", background: "#EEF4F1", fontFamily: "'Inter', sans-serif" }}>
      <div style={{ background: "#fff", borderRadius: "14px", padding: "28px", maxWidth: "600px", margin: "0 auto", boxShadow: "0 2px 8px rgba(0,0,0,0.06)", border: "1px solid #E3ECE7" }}>
        <h2 style={{ fontSize: "22px", fontWeight: 700, color: "#1F2933", margin: "0 0 4px", display: "flex", alignItems: "center", gap: "10px" }}><User size={22} color="#7AAE8A" />{isNew ? "Complete Your Profile" : "Edit Profile"}</h2>
        <p style={{ fontSize: "13px", color: "#6B7280", marginBottom: "24px" }}>{isNew ? "Fill in your details to get started" : "Update your information"}</p>
        {error && <div style={{ background: "#FEF2F2", border: "1px solid #FECACA", borderRadius: "8px", padding: "10px 14px", color: "#991B1B", fontSize: "13px", marginBottom: "16px", display: "flex", alignItems: "center", gap: "8px" }}><AlertCircle size={16} /> {error}</div>}
        {success && <div style={{ background: "#F0FFF4", border: "1px solid #C6F6D5", borderRadius: "8px", padding: "10px 14px", color: "#22543D", fontSize: "13px", marginBottom: "16px", display: "flex", alignItems: "center", gap: "8px" }}><CheckCircle size={16} /> {success}</div>}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
          <div style={{ gridColumn: "1 / -1" }}><label style={labelStyle}>Full Name *</label><input style={inputStyle} value={form.full_name} onChange={e => upd("full_name", e.target.value)} /></div>
          <div><label style={labelStyle}>Mobile Number *</label><input style={inputStyle} value={form.mobile_number} onChange={e => upd("mobile_number", e.target.value)} /></div>
          <div><label style={labelStyle}>Email</label><input style={{ ...inputStyle, background: "#F3F4F6" }} value={user?.email || ""} disabled /></div>
          <div style={{ gridColumn: "1 / -1" }}><label style={labelStyle}>Address</label><textarea style={{ ...inputStyle, minHeight: "80px", resize: "vertical" } as any} value={form.address} onChange={e => upd("address", e.target.value)} /></div>
          <div><label style={labelStyle}>City</label><input style={inputStyle} value={form.city} onChange={e => upd("city", e.target.value)} /></div>
          <div><label style={labelStyle}>State</label><input style={inputStyle} value={form.state} onChange={e => upd("state", e.target.value)} /></div>
          <div><label style={labelStyle}>Pincode</label><input style={inputStyle} value={form.pincode} onChange={e => upd("pincode", e.target.value)} maxLength={6} /></div>
          <div><label style={labelStyle}>Company (optional)</label><input style={inputStyle} value={form.company_name} onChange={e => upd("company_name", e.target.value)} /></div>
        </div>
        <div style={{ marginTop: "24px", display: "flex", justifyContent: "flex-end" }}>
          <button onClick={handleSave} disabled={saving} style={{ padding: "12px 28px", border: "none", borderRadius: "10px", fontSize: "14px", fontWeight: 700, cursor: "pointer", background: "#7AAE8A", color: "#fff", display: "flex", alignItems: "center", gap: "8px", opacity: saving ? 0.7 : 1 }}><Save size={16} /> {saving ? "Saving..." : isNew ? "Complete Profile" : "Save Changes"}</button>
        </div>
      </div>
    </div>
  );
}
