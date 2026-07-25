import { useState, useEffect } from "react";
import { History, MapPin, Clock, CheckCircle } from "lucide-react";
import { getTechnicianJobHistory } from "../../services/technicianPortalService";

export default function TechnicianJobHistoryPage() {
  const [jobs, setJobs] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getTechnicianJobHistory().then(r => setJobs(r.data || [])).catch(() => {}).finally(() => setLoading(false));
  }, []);

  return (
    <div style={{ padding: "24px", height: "100%", overflowY: "auto", background: "#EEF4F1", fontFamily: "'Inter', sans-serif" }}>
      <h2 style={{ fontSize: "22px", fontWeight: 700, color: "#1F2933", marginBottom: "20px", display: "flex", alignItems: "center", gap: "8px" }}><History size={22} color="#7AAE8A" />Job History</h2>
      {loading ? <div style={{ textAlign: "center", padding: "48px", color: "#9CA3AF" }}>Loading...</div> :
       jobs.length === 0 ? <div style={{ textAlign: "center", padding: "48px", color: "#9CA3AF" }}>No completed jobs yet</div> :
       jobs.map(job => (
        <div key={job.id} style={{ background: "#fff", borderRadius: "14px", padding: "18px", marginBottom: "12px", boxShadow: "0 2px 8px rgba(0,0,0,0.05)", border: "1px solid #E3ECE7" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
            <div><span style={{ fontSize: "11px", color: "#9CA3AF" }}>JOB #{job.id}</span><div style={{ fontSize: "15px", fontWeight: 700, color: "#1F2933" }}>{job.service_type || "Service"}</div></div>
            <span style={{ fontSize: "11px", fontWeight: 600, padding: "3px 10px", borderRadius: "20px", background: "#D1FAE5", color: "#065F46" }}><CheckCircle size={12} style={{ verticalAlign: "middle", marginRight: "3px" }} />{job.status}</span>
          </div>
          <div style={{ display: "flex", gap: "16px", fontSize: "13px", color: "#6B7280" }}>
            <span style={{ display: "flex", alignItems: "center", gap: "4px" }}><MapPin size={13} /> {job.location || "N/A"}</span>
            <span style={{ display: "flex", alignItems: "center", gap: "4px" }}><Clock size={13} /> {job.completed_at ? new Date(job.completed_at).toLocaleDateString() : "N/A"}</span>
          </div>
          {job.customer_name && <div style={{ fontSize: "13px", color: "#6B7280", marginTop: "4px" }}>Customer: {job.customer_name}</div>}
        </div>
      ))}
    </div>
  );
}
