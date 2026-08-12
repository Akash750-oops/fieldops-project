import { useState, useEffect } from "react";
import { FileText, PlusCircle, XCircle, Edit3, AlertCircle, CheckCircle, X, Clock, Send } from "lucide-react";
import { getServiceRequests, createServiceRequest, updateServiceRequest, cancelServiceRequest } from "../../services/customerPortalService";

const badge = (status: string) => {
  const c: Record<string, string> = { PENDING: "#DD6B20", ASSIGNED: "#1E40AF", IN_PROGRESS: "#92400E", COMPLETED: "#065F46", CANCELLED: "#991B1B" };
  return { fontSize: "11px", fontWeight: 600, padding: "3px 10px", borderRadius: "20px", background: (c[status] || "#6B7280") + "18", color: c[status] || "#6B7280", display: "inline-block" };
};

export default function CustomerServiceRequestsPage() {
  const [requests, setRequests] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [editId, setEditId] = useState<number | null>(null);
  const [form, setForm] = useState({ title: "", description: "", service_type: "", priority: "MEDIUM", preferred_visit_date: "", location: "", contact_number: "" });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const load = () => { setLoading(true); getServiceRequests().then(r => setRequests(r.data || [])).catch(() => {}).finally(() => setLoading(false)); };
  useEffect(load, []);

  const reset = () => { setForm({ title: "", description: "", service_type: "", priority: "MEDIUM", preferred_visit_date: "", location: "", contact_number: "" }); setShowCreate(false); setEditId(null); setError(""); };

  const handleSubmit = async () => {
    setError(""); if (!form.title.trim() || form.description.length < 10) { setError("Title required, description min 10 chars"); return; }
    setSaving(true);
    try {
      const payload = { ...form, preferred_visit_date: form.preferred_visit_date || null };
      if (editId) { await updateServiceRequest(editId, payload); setSuccess("Request updated!"); }
      else { await createServiceRequest(payload); setSuccess("Request created!"); }
      reset(); load();
    } catch (e: any) { setError(e.response?.data?.detail || "Failed"); }
    finally { setSaving(false); }
  };

  const handleCancel = async (id: number) => {
    if (!confirm("Cancel this service request?")) return;
    try { await cancelServiceRequest(id); load(); } catch (e: any) { alert(e.response?.data?.detail || "Failed"); }
  };

  const startEdit = (sr: any) => {
    setForm({ title: sr.title, description: sr.description, service_type: sr.service_type || "", priority: sr.priority, preferred_visit_date: sr.preferred_visit_date || "", location: sr.location || "", contact_number: sr.contact_number || "" });
    setEditId(sr.id); setShowCreate(true);
  };

  const upd = (k: string, v: string) => setForm(f => ({ ...f, [k]: v }));
  const inputStyle = { width: "100%", padding: "10px 12px", border: "1.5px solid #D1D5DB", borderRadius: "8px", fontSize: "14px", boxSizing: "border-box" as const, outline: "none", fontFamily: "'Inter', sans-serif" };
  const labelStyle = { fontSize: "12px", fontWeight: 600, color: "#374151", marginBottom: "4px", display: "block" as const };

  return (
    <div style={{ padding: "24px", height: "100%", overflowY: "auto", background: "#EEF4F1", fontFamily: "'Inter', sans-serif" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "20px" }}>
        <h2 style={{ fontSize: "22px", fontWeight: 700, color: "#1F2933", display: "flex", alignItems: "center", gap: "8px" }}><FileText size={22} color="#7AAE8A" /> Service Requests</h2>
        <button onClick={() => { reset(); setShowCreate(true); }} style={{ padding: "10px 20px", border: "none", borderRadius: "10px", background: "#7AAE8A", color: "#fff", fontSize: "13px", fontWeight: 700, cursor: "pointer", display: "flex", alignItems: "center", gap: "6px" }}><PlusCircle size={16} /> New Request</button>
      </div>
      {success && <div style={{ background: "#F0FFF4", border: "1px solid #C6F6D5", borderRadius: "8px", padding: "10px 14px", color: "#22543D", fontSize: "13px", marginBottom: "16px", display: "flex", alignItems: "center", gap: "8px" }}><CheckCircle size={16} /> {success}</div>}

      {showCreate && (
        <div style={{ position: "fixed" as const, inset: 0, zIndex: 9999, display: "flex", alignItems: "center", justifyContent: "center" }}>
          <div style={{ position: "absolute" as const, inset: 0, background: "rgba(0,0,0,0.4)" }} onClick={reset} />
          <div style={{ position: "relative" as const, background: "#fff", borderRadius: "16px", padding: "28px", width: "90%", maxWidth: "520px", zIndex: 1, maxHeight: "90vh", overflowY: "auto" }}>
            <button onClick={reset} style={{ position: "absolute", top: "12px", right: "12px", background: "none", border: "none", cursor: "pointer" }}><X size={20} color="#6B7280" /></button>
            <h3 style={{ fontSize: "18px", fontWeight: 700, color: "#1F2933", marginBottom: "20px" }}>{editId ? "Edit Request" : "Create Service Request"}</h3>
            {error && <div style={{ background: "#FEF2F2", border: "1px solid #FECACA", borderRadius: "8px", padding: "10px", color: "#991B1B", fontSize: "13px", marginBottom: "14px", display: "flex", alignItems: "center", gap: "6px" }}><AlertCircle size={14} /> {error}</div>}
            <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
              <div><label style={labelStyle}>Title *</label><input style={inputStyle} value={form.title} onChange={e => upd("title", e.target.value)} placeholder="Brief title for your request" /></div>
              <div><label style={labelStyle}>Description * (min 10 chars)</label><textarea style={{ ...inputStyle, minHeight: "100px", resize: "vertical" } as any} value={form.description} onChange={e => upd("description", e.target.value)} placeholder="Describe the issue in detail..." /></div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                <div><label style={labelStyle}>Service Type</label><input style={inputStyle} value={form.service_type} onChange={e => upd("service_type", e.target.value)} placeholder="e.g. Plumbing" /></div>
                <div><label style={labelStyle}>Priority</label><select style={inputStyle} value={form.priority} onChange={e => upd("priority", e.target.value)}><option>LOW</option><option>MEDIUM</option><option>HIGH</option><option>CRITICAL</option></select></div>
                <div><label style={labelStyle}>Preferred Date</label><input type="date" style={inputStyle} value={form.preferred_visit_date} onChange={e => upd("preferred_visit_date", e.target.value)} /></div>
                <div><label style={labelStyle}>Contact Number</label><input style={inputStyle} value={form.contact_number} onChange={e => upd("contact_number", e.target.value)} /></div>
              </div>
              <div><label style={labelStyle}>Location / Address</label><input style={inputStyle} value={form.location} onChange={e => upd("location", e.target.value)} /></div>
              <div style={{ display: "flex", gap: "10px", justifyContent: "flex-end", marginTop: "8px" }}>
                <button onClick={reset} style={{ padding: "10px 20px", border: "1px solid #D1D5DB", borderRadius: "8px", background: "#fff", fontSize: "13px", fontWeight: 600, cursor: "pointer", color: "#374151" }}>Cancel</button>
                <button onClick={handleSubmit} disabled={saving} style={{ padding: "10px 20px", border: "none", borderRadius: "8px", background: "#7AAE8A", color: "#fff", fontSize: "13px", fontWeight: 700, cursor: "pointer", display: "flex", alignItems: "center", gap: "6px", opacity: saving ? 0.7 : 1 }}><Send size={14} /> {saving ? "Submitting..." : editId ? "Update" : "Submit"}</button>
              </div>
            </div>
          </div>
        </div>
      )}

      {loading ? <div style={{ textAlign: "center", padding: "48px", color: "#9CA3AF" }}>Loading...</div> :
       requests.length === 0 ? <div style={{ textAlign: "center", padding: "48px", color: "#9CA3AF" }}>No service requests yet. Create your first one!</div> :
       requests.map(sr => (
        <div key={sr.id} style={{ background: "#fff", borderRadius: "14px", padding: "18px", marginBottom: "12px", boxShadow: "0 2px 8px rgba(0,0,0,0.05)", border: "1px solid #E3ECE7" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "8px" }}>
            <div><span style={{ fontSize: "11px", color: "#9CA3AF" }}>{sr.request_number}</span><div style={{ fontSize: "15px", fontWeight: 700, color: "#1F2933" }}>{sr.title}</div></div>
            <span style={badge(sr.status) as any}>{sr.status}</span>
          </div>
          <div style={{ fontSize: "13px", color: "#6B7280", marginBottom: "8px", lineHeight: 1.5 }}>{sr.description}</div>
          <div style={{ display: "flex", gap: "14px", fontSize: "12px", color: "#9CA3AF", flexWrap: "wrap" }}>
            {sr.service_type && <span>Type: {sr.service_type}</span>}
            <span>Priority: {sr.priority}</span>
            <span><Clock size={12} style={{ verticalAlign: "middle" }} /> {new Date(sr.created_at).toLocaleDateString()}</span>
            {sr.linked_job_id && <span>Linked Job: #{sr.linked_job_id}</span>}
          </div>
          {sr.status === "PENDING" && (
            <div style={{ display: "flex", gap: "8px", marginTop: "12px", paddingTop: "10px", borderTop: "1px solid #F0F0F0" }}>
              <button onClick={() => startEdit(sr)} style={{ padding: "6px 14px", border: "1px solid #D1D5DB", borderRadius: "6px", background: "#fff", fontSize: "12px", fontWeight: 600, cursor: "pointer", display: "flex", alignItems: "center", gap: "4px", color: "#374151" }}><Edit3 size={12} /> Edit</button>
              <button onClick={() => handleCancel(sr.id)} style={{ padding: "6px 14px", border: "none", borderRadius: "6px", background: "#FEE2E2", fontSize: "12px", fontWeight: 600, cursor: "pointer", display: "flex", alignItems: "center", gap: "4px", color: "#991B1B" }}><XCircle size={12} /> Cancel</button>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
