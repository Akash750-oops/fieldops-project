import { useState, useEffect } from "react";
import { History, Clock, CheckCircle, XCircle } from "lucide-react";
import { getServiceHistory } from "../../services/customerPortalService";

export default function CustomerServiceHistoryPage() {
  const [history, setHistory] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getServiceHistory()
      .then((r) => setHistory(r.data || []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  return (
    <div style={{ padding: "24px", height: "100%", overflowY: "auto", background: "#EEF4F1", fontFamily: "'Inter', sans-serif" }}>
      <h2 style={{ fontSize: "22px", fontWeight: 700, color: "#1F2933", marginBottom: "20px", display: "flex", alignItems: "center", gap: "8px" }}>
        <History size={22} color="#7AAE8A" /> Service History
      </h2>
      {loading ? (
        <div style={{ textAlign: "center", padding: "48px", color: "#9CA3AF" }}>Loading...</div>
      ) : history.length === 0 ? (
        <div style={{ textAlign: "center", padding: "48px", color: "#9CA3AF", background: "#fff", borderRadius: "14px", border: "1px solid #E3ECE7" }}>
          No completed or cancelled service requests yet.
        </div>
      ) : (
        history.map((sr) => (
          <div key={sr.id} style={{ background: "#fff", borderRadius: "14px", padding: "18px", marginBottom: "12px", boxShadow: "0 2px 8px rgba(0,0,0,0.05)", border: "1px solid #E3ECE7" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
              <div>
                <span style={{ fontSize: "11px", color: "#9CA3AF" }}>{sr.request_number}</span>
                <div style={{ fontSize: "15px", fontWeight: 700, color: "#1F2933" }}>{sr.title}</div>
              </div>
              <span
                style={{
                  fontSize: "11px",
                  fontWeight: 600,
                  padding: "3px 10px",
                  borderRadius: "20px",
                  background: sr.status === "COMPLETED" ? "#D1FAE5" : "#FEE2E2",
                  color: sr.status === "COMPLETED" ? "#065F46" : "#991B1B",
                }}
              >
                {sr.status === "COMPLETED" ? <CheckCircle size={12} style={{ verticalAlign: "middle", marginRight: "3px" }} /> : <XCircle size={12} style={{ verticalAlign: "middle", marginRight: "3px" }} />}
                {sr.status}
              </span>
            </div>
            <div style={{ fontSize: "13px", color: "#6B7280", marginBottom: "8px" }}>{sr.description}</div>
            <div style={{ fontSize: "12px", color: "#9CA3AF" }}>
              <Clock size={12} style={{ verticalAlign: "middle" }} /> Updated: {new Date(sr.updated_at).toLocaleDateString()}
            </div>
          </div>
        ))
      )}
    </div>
  );
}
