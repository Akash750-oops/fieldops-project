import React, { useEffect, useState } from "react";
import { Eye, Pencil, Trash2 } from "lucide-react";
import api from "../services/api";
import LoadingSpinner from "../components/ui/LoadingSpinner";
import StatusBadge from "../components/ui/StatusBadge";
import EmptyState from "../components/ui/EmptyState";

const TECH_PAGE_SIZE = 8;

interface TechFormData {
  technician_name: string;
  technician_skill: string;
  technician_location: string;
  technician_status: string;
}

const initialTechFormData: TechFormData = {
  technician_name: "",
  technician_skill: "",
  technician_location: "",
  technician_status: "Available",
};

interface Technician {
  technician_id: number;
  technician_name: string;
  technician_skill: string;
  technician_location: string;
  technician_status: string;
  current_jobs: number;
  max_jobs: number;
}

const skills = [
  "HVAC Repair", "Electrical", "Plumbing", "Network Support", "General Maintenance"
];

const styles = {
  techPage: {
    fontFamily: "'Inter', sans-serif",
    background: "#EEF4F1",
    minHeight: "100vh",
    padding: "14px",
    color: "#1F2933",
    position: "relative",
    display: "flex",
    flexDirection: "column",
    boxSizing: "border-box",
  } as React.CSSProperties,

  toastMessage: {
    position: "fixed",
    bottom: "24px",
    right: "24px",
    zIndex: 9999,
    padding: "12px 18px",
    borderRadius: "8px",
    fontSize: "13px",
    fontWeight: 700,
    boxShadow: "0 10px 15px -3px rgba(0, 0, 0, 0.1)",
    display: "flex",
    alignItems: "center",
    gap: "8px",
    animation: "slideUp 0.3s cubic-bezier(0.16, 1, 0.3, 1)",
  } as React.CSSProperties,

  toastSuccess: {
    background: "#EDFAF1",
    border: "1px solid #B0D4BC",
    color: "#2F4F3E",
  } as React.CSSProperties,

  toastError: {
    background: "#FDF2F2",
    border: "1px solid #F5C6C6",
    color: "#9B3A3A",
  } as React.CSSProperties,

  mainContentRow: {
    display: "grid",
    gap: "20px",
    alignItems: "start",
    gridTemplateColumns: "1fr",
  } as React.CSSProperties,

  contentCard: {
    background: "#FFFFFF",
    borderRadius: "12px",
    padding: "22px",
    boxShadow: "0 1px 4px rgba(47,79,62,.07)",
    border: "1px solid #E3ECE7",
    boxSizing: "border-box",
  } as React.CSSProperties,

  cardHeader: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    flexWrap: "wrap",
    gap: "12px",
    marginBottom: "16px",
    paddingBottom: "14px",
    borderBottom: "1px solid #E3ECE7",
    boxSizing: "border-box",
  } as React.CSSProperties,

  sectionBadge: {
    display: "inline-block",
    background: "#DDEEE5",
    color: "#2F4F3E",
    fontSize: "9px",
    fontWeight: 700,
    padding: "2px 6px",
    borderRadius: "20px",
    letterSpacing: ".05em",
    textTransform: "uppercase",
    marginBottom: "6px",
  } as React.CSSProperties,

  cardSubtitle: {
    fontSize: "11px",
    color: "#6B7280",
    marginTop: "3px",
  } as React.CSSProperties,

  headerActionsRow: {
    display: "flex",
    gap: "8px",
  } as React.CSSProperties,

  refreshIconBtn: {
    background: "#FFFFFF",
    border: "1px solid #E3ECE7",
    color: "#2F4F3E",
    padding: "7px 14px",
    borderRadius: "8px",
    fontWeight: 600,
    fontSize: "11px",
    cursor: "pointer",
    transition: "all .2s",
    boxShadow: "0 1px 3px rgba(47,79,62,.06)",
  } as React.CSSProperties,

  addTechBtn: {
    background: "#7AAE8A",
    color: "#fff",
    border: "none",
    padding: "7px 16px",
    borderRadius: "8px",
    fontWeight: 700,
    fontSize: "11px",
    cursor: "pointer",
    transition: "background .2s",
    boxShadow: "0 2px 6px rgba(122,174,138,.3)",
  } as React.CSSProperties,

  techFiltersRow: {
    display: "flex",
    alignItems: "flex-end",
    gap: "10px",
    marginBottom: "14px",
    flexWrap: "wrap",
  } as React.CSSProperties,

  filterGroup: {
    display: "flex",
    flexDirection: "column",
    gap: "4px",
  } as React.CSSProperties,

  filterLabel: {
    fontSize: "9px",
    fontWeight: 700,
    color: "#6B7280",
    textTransform: "uppercase",
    letterSpacing: ".05em",
  } as React.CSSProperties,

  filterInput: {
    padding: "7px 10px",
    border: "1.5px solid #E3ECE7",
    borderRadius: "8px",
    fontSize: "11px",
    color: "#1F2933",
    fontFamily: "'Inter', sans-serif",
    outline: "none",
    transition: "border-color .2s",
    minWidth: "150px",
    background: "#FFFFFF",
  } as React.CSSProperties,

  resultsCount: {
    fontSize: "10px",
    color: "#6B7280",
    fontWeight: 500,
    marginBottom: "14px",
  } as React.CSSProperties,

  alertError: {
    background: "#FDF2F2",
    color: "#9B3A3A",
    border: "1px solid #F5C6C6",
    borderRadius: "8px",
    padding: "10px 14px",
    fontTheme: "11px",
    fontWeight: 500,
    marginBottom: "14px",
  } as React.CSSProperties,

  tableContainer: {
    overflowX: "auto",
  } as React.CSSProperties,

  dashboardTable: {
    width: "100%",
    borderCollapse: "collapse",
  } as React.CSSProperties,

  dashboardTableTh: {
    background: "#F6FAF8",
    padding: "6px 8px",
    textAlign: "left",
    fontSize: "9.5px",
    fontWeight: 700,
    color: "#6B7280",
    textTransform: "uppercase",
    letterSpacing: "0.05em",
    borderBottom: "1px solid #E3ECE7",
  } as React.CSSProperties,

  dashboardTableTd: {
    padding: "6px 8px",
    fontSize: "11.5px",
    color: "#1F2933",
    borderBottom: "1px solid #F0F6F2",
    verticalAlign: "middle",
  } as React.CSSProperties,

  techAvatar: {
    width: "32px",
    height: "32px",
    minWidth: "32px",
    background: "#7AAE8A",
    color: "#fff",
    borderRadius: "50%",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontSize: "12px",
    fontWeight: 700,
  } as React.CSSProperties,

  techName: {
    fontSize: "12px",
    fontWeight: 700,
    color: "#2F4F3E",
    marginBottom: "3px",
  } as React.CSSProperties,

  availabilityControl: {
    borderTop: "none",
    paddingTop: 0,
    display: "flex",
    alignItems: "center",
    gap: "10px",
  } as React.CSSProperties,

  selectWrapper: {
    display: "flex",
    alignItems: "center",
    gap: "6px",
    flex: 1,
  } as React.CSSProperties,

  statusSelect: {
    flex: 1,
    padding: "6px 10px",
    borderRadius: "8px",
    border: "1.5px solid #E3ECE7",
    fontWeight: 600,
    fontSize: "11px",
    fontFamily: "'Inter', sans-serif",
    outline: "none",
    cursor: "pointer",
    transition: "all .2s",
  } as React.CSSProperties,

  workloadInfo: {
    display: "flex",
    flexDirection: "column",
    gap: "4px",
    width: "120px",
  } as React.CSSProperties,

  workloadBar: {
    background: "#E3ECE7",
    height: "6px",
    borderRadius: "3px",
    overflow: "hidden",
  } as React.CSSProperties,

  workloadFill: {
    height: "100%",
    borderRadius: "3px",
    transition: "width .4s",
  } as React.CSSProperties,

  workloadText: {
    fontSize: "10px",
    color: "#6B7280",
  } as React.CSSProperties,

  jobItemActions: {
    display: "flex",
    gap: "6px",
    border: "none",
    padding: 0,
    background: "none",
    margin: 0,
  } as React.CSSProperties,

  iconActionBtn: {
    background: "none",
    border: "none",
    cursor: "pointer",
    padding: "4px",
    display: "inline-flex",
    alignItems: "center",
    justifyContent: "center",
    borderRadius: "4px",
    transition: "transform .15s, opacity .15s",
    outline: "none",
  } as React.CSSProperties,

  techPagination: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    padding: "14px 0 0 0",
    borderTop: "1px solid #E3ECE7",
    flexWrap: "wrap",
    gap: "8px",
    marginTop: "14px",
    boxSizing: "border-box",
  } as React.CSSProperties,

  techPageInfo: {
    fontSize: "11px",
    color: "#6B7280",
    fontWeight: 500,
  } as React.CSSProperties,

  techPageControls: {
    display: "flex",
    alignItems: "center",
    gap: "6px",
  } as React.CSSProperties,

  techPageBtn: {
    padding: "5px 12px",
    background: "#FFFFFF",
    border: "1.5px solid #E3ECE7",
    borderRadius: "7px",
    fontSize: "11px",
    fontWeight: 600,
    color: "#2F4F3E",
    cursor: "pointer",
    transition: "all .2s",
  } as React.CSSProperties,

  techPageNumbers: {
    display: "flex",
    gap: "4px",
  } as React.CSSProperties,

  techPageNum: {
    width: "26px",
    height: "26px",
    borderRadius: "7px",
    border: "1.5px solid #E3ECE7",
    background: "#FFFFFF",
    fontSize: "11px",
    fontWeight: 600,
    color: "#6B7280",
    cursor: "pointer",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    transition: "all .2s",
  } as React.CSSProperties,

  techPageNumActive: {
    background: "#7AAE8A",
    borderColor: "#7AAE8A",
    color: "#fff",
  } as React.CSSProperties,

  popupOverlay: {
    position: "fixed",
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    background: "rgba(47,79,62,0.4)",
    backdropFilter: "blur(4px)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    zIndex: 3000,
  } as React.CSSProperties,

  viewJobModal: {
    background: "#FFFFFF",
    borderRadius: "16px",
    padding: 0,
    maxWidth: "460px",
    width: "94%",
    boxShadow: "0 20px 50px rgba(47,79,62,.18)",
    overflow: "hidden",
    boxSizing: "border-box",
  } as React.CSSProperties,

  viewModalHeader: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    padding: "18px 22px 14px",
    borderBottom: "1px solid #E3ECE7",
    background: "#F6FAF8",
    boxSizing: "border-box",
  } as React.CSSProperties,

  viewModalHeaderH3: {
    fontSize: "15px",
    fontWeight: 700,
    color: "#2F4F3E",
    margin: 0,
  } as React.CSSProperties,

  viewModalBody: {
    padding: "18px 22px 22px",
    display: "flex",
    flexDirection: "column",
    gap: "10px",
    boxSizing: "border-box",
  } as React.CSSProperties,

  viewDetailRow: {
    display: "flex",
    alignItems: "flex-start",
    gap: "10px",
  } as React.CSSProperties,

  viewLabel: {
    minWidth: "110px",
    fontSize: "11px",
    fontWeight: 600,
    color: "#9CA3AF",
    textTransform: "uppercase",
    letterSpacing: ".03em",
    paddingTop: "2px",
  } as React.CSSProperties,

  viewValue: {
    fontSize: "13px",
    color: "#1F2937",
    fontWeight: 500,
    flex: 1,
  } as React.CSSProperties,

  techFormSidebar: {
    position: "fixed",
    top: 0,
    height: "100vh",
    width: "420px",
    background: "#FFFFFF",
    boxShadow: "-4px 0 24px rgba(47,79,62,.1)",
    zIndex: 1000,
    transition: "right 0.4s cubic-bezier(0.4, 0, 0.2, 1)",
    display: "flex",
    flexDirection: "column",
    boxSizing: "border-box",
  } as React.CSSProperties,

  sidebarHeader: {
    padding: "22px 24px",
    borderBottom: "1px solid #E3ECE7",
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    background: "#F8FBF9",
    boxSizing: "border-box",
  } as React.CSSProperties,

  sidebarHeaderH3: {
    fontSize: "14.5px",
    fontWeight: 700,
    color: "#2F4F3E",
    margin: 0,
  } as React.CSSProperties,

  closeSidebar: {
    background: "none",
    border: "none",
    fontSize: "18px",
    color: "#6B7280",
    cursor: "pointer",
    width: "32px",
    height: "32px",
    borderRadius: "6px",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    transition: "background .15s",
  } as React.CSSProperties,

  sidebarContent: {
    flex: 1,
    padding: "24px",
    overflowY: "auto",
    boxSizing: "border-box",
  } as React.CSSProperties,

  sidebarOverlay: {
    position: "fixed",
    top: 0,
    left: 0,
    width: "100vw",
    height: "100vh",
    background: "rgba(31,41,51,.35)",
    backdropFilter: "blur(2px)",
    zIndex: 999,
    transition: "opacity 0.3s",
  } as React.CSSProperties,

  techForm: {
    display: "flex",
    flexDirection: "column",
    gap: "12px",
  } as React.CSSProperties,

  formGroup: {
    display: "flex",
    flexDirection: "column",
    gap: "4px",
    marginBottom: "14px",
  } as React.CSSProperties,

  formGroupLabel: {
    fontSize: "11px",
    fontWeight: 600,
    color: "#2F4F3E",
  } as React.CSSProperties,

  formGroupInput: {
    padding: "9px 12px",
    border: "1.5px solid #E3ECE7",
    borderRadius: "8px",
    fontSize: "11.5px",
    fontFamily: "'Inter', sans-serif",
    color: "#1F2933",
    background: "#FFFFFF",
    transition: "border-color .2s, box-shadow .2s",
    outline: "none",
    width: "100%",
    boxSizing: "border-box",
  } as React.CSSProperties,

  req: {
    color: "#D96C6C",
  } as React.CSSProperties,

  fieldError: {
    fontSize: "10px",
    color: "#D96C6C",
    marginTop: "2px",
  } as React.CSSProperties,

  formActions: {
    display: "flex",
    gap: "12px",
    marginKind: "24px",
    marginTop: "24px",
  } as React.CSSProperties,

  btnPrimary: {
    flex: 2,
    background: "#7AAE8A",
    color: "#fff",
    border: "none",
    padding: "12px",
    borderRadius: "8px",
    fontWeight: 700,
    cursor: "pointer",
    transition: "background 0.2s",
    boxShadow: "0 2px 6px rgba(122,174,138,.25)",
  } as React.CSSProperties,

  btnSecondary: {
    flex: 1,
    background: "#F6FAF8",
    color: "#2F4F3E",
    border: "1.5px solid #E3ECE7",
    padding: "12px",
    borderRadius: "8px",
    fontWeight: 600,
    cursor: "pointer",
  } as React.CSSProperties,
};

const localCss = `
  .refresh-icon-btn-style:hover {
    background-color: #F6FAF8 !important;
    border-color: #7AAE8A !important;
  }
  .add-tech-btn-style:hover {
    background-color: #5C9470 !important;
  }
  .filter-input-style:focus, .filter-select-style:focus {
    border-color: #7AAE8A !important;
    box-shadow: 0 0 0 2px rgba(122,174,138,.12) !important;
  }
  .status-select-style:focus {
    border-color: #7AAE8A !important;
    box-shadow: 0 0 0 2px rgba(122,174,138,.12) !important;
  }
  .icon-action-btn-style {
    transition: transform .15s, opacity .15s !important;
  }
  .icon-action-btn-style:hover {
    transform: scale(1.2) !important;
    opacity: .85 !important;
  }
  .icon-action-btn-style:active {
    transform: scale(0.9) !important;
  }
  .tech-page-btn-style:hover:not(:disabled) {
    background-color: #EAF4EE !important;
    border-color: #7AAE8A !important;
  }
  .tech-page-num-style:hover {
    border-color: #7AAE8A !important;
    color: #2F4F3E !important;
  }
  .close-sidebar-style:hover {
    background-color: #EAF4EE !important;
    color: #2F4F3E !important;
  }
  .form-group-input-style:focus, .form-group-select-style:focus {
    border-color: #7AAE8A !important;
    box-shadow: 0 0 0 3px rgba(122,174,138,.15) !important;
  }
  .btn-primary-style:hover {
    background-color: #5C9470 !important;
  }
  .btn-secondary-style:hover {
    background-color: #EAF4EE !important;
  }
  .dashboard-table-row:hover td {
    background-color: #F8FBF9 !important;
  }

  @keyframes slideUp {
    from {
      opacity: 0;
      transform: translateY(16px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  @media (max-width: 768px) {
    .tech-filters-row-responsive {
      flex-direction: column !important;
      align-items: stretch !important;
    }
    .filter-group-responsive {
      width: 100% !important;
    }
    .filter-input-style, .filter-select-style {
      width: 100% !important;
    }
    .card-header-responsive {
      flex-direction: column !important;
      align-items: flex-start !important;
      gap: 12px !important;
    }
    .header-actions-responsive {
      width: 100% !important;
      justify-content: space-between !important;
    }
  }
`;

const getStatusSelectStyle = (status: string): React.CSSProperties => {
  const s = (status || "").toLowerCase().trim();
  const base: React.CSSProperties = {
    ...styles.statusSelect
  };
  if (s === "available") {
    return { ...base, background: "#DDEEE5", color: "#2F4F3E", borderColor: "#B0D4BC" };
  }
  if (s === "busy") {
    return { ...base, background: "#FEF0D6", color: "#7A5120", borderColor: "#F0D09A" };
  }
  if (s === "offline") {
    return { ...base, background: "#F0F4F2", color: "#6B7280", borderColor: "#D0DCD4" };
  }
  if (s === "assigned") {
    return { ...base, background: "#E0F2FE", color: "#0369A1", borderColor: "#7DD3FC" };
  }
  return base;
};

function TechnicianList() {
  const [technicians, setTechnicians] = useState<Technician[]>([]);
  const [loading, setLoading] = useState(false);
  const [fetchError, setFetchError] = useState("");
  const [techFormData, setTechFormData] = useState<TechFormData>(initialTechFormData);
  const [formErrors, setFormErrors] = useState<Partial<Record<keyof TechFormData, string>>>({});
  const [formLoading, setFormLoading] = useState(false);
  const [updatingId, setUpdatingId] = useState<number | null>(null);
  const [message, setMessage] = useState({ text: "", type: "" });
  const [searchTerm, setSearchTerm] = useState("");
  const [statusFilter, setStatusFilter] = useState("ALL");
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [techPage, setTechPage] = useState(1);
  const [isEditing, setIsEditing] = useState(false);
  const [editingTechId, setEditingTechId] = useState<number | null>(null);
  const [viewTech, setViewTech] = useState<Technician | null>(null);

  useEffect(() => {
    setTechPage(1);
  }, [searchTerm, statusFilter]);

  const fetchTechnicians = async () => {
    try {
      setLoading(true);
      const response = await api.get("/technicians/");
      setTechnicians(response.data);
      setFetchError("");
    } catch (error) {
      console.error(error);
      setFetchError("Unable to fetch technicians. Please check backend API.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchTechnicians(); }, []);

  const showMessage = (text: string, type: string) => {
    setMessage({ text, type });
    setTimeout(() => setMessage({ text: "", type: "" }), 4000);
  };

  const handleStatusChange = async (technicianId: number, newStatus: string) => {
    try {
      setUpdatingId(technicianId);
      await api.put(`/technicians/${technicianId}/availability`, {
        technician_status: newStatus
      });
      showMessage("Availability updated successfully", "success");
      setTechnicians(prev => prev.map(t =>
        t.technician_id === technicianId ? { ...t, technician_status: newStatus } : t
      ));
    } catch (error: any) {
      console.error(error);
      const errorMsg = error.response?.data?.error || error.response?.data?.detail || "Unable to update availability. Please try again.";
      showMessage(errorMsg, "error");
    } finally {
      setUpdatingId(null);
    }
  };

  const validateForm = () => {
    const errors: Partial<Record<keyof TechFormData, string>> = {};
    if (!techFormData.technician_name.trim()) errors.technician_name = "Name is required";
    if (!techFormData.technician_skill.trim()) errors.technician_skill = "Skill is required";
    if (!techFormData.technician_location.trim()) errors.technician_location = "Location is required";
    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleFormChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setTechFormData(prev => ({ ...prev, [name]: value }));
    setFormErrors(prev => ({ ...prev, [name]: "" }));
  };

  const resetForm = () => {
    setTechFormData(initialTechFormData);
    setFormErrors({});
    setIsEditing(false);
    setEditingTechId(null);
    setIsFormOpen(false);
  };

  const handleEdit = (tech: Technician) => {
    setIsEditing(true);
    setEditingTechId(tech.technician_id);
    setTechFormData({
      technician_name: tech.technician_name || "",
      technician_skill: tech.technician_skill || "",
      technician_location: tech.technician_location || "",
      technician_status: normalizeStatus(tech.technician_status) || "Available",
    });
    setIsFormOpen(true);
  };

  const handleDelete = async (id: number) => {
    const tech = technicians.find(t => t.technician_id === id);
    const name = tech?.technician_name || `Technician #${id}`;
    if (!window.confirm(`Are you sure you want to delete "${name}"?`)) return;
    try {
      setLoading(true);
      await api.delete(`/technicians/${id}`);
      showMessage("Technician deleted successfully", "success");
      fetchTechnicians();
    } catch (error: any) {
      console.error(error);
      const errorMsg = error.response?.data?.error || error.response?.data?.detail || "Unable to delete technician. Please try again.";
      showMessage(errorMsg, "error");
    } finally {
      setLoading(false);
    }
  };

  const handleFormSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validateForm()) return;
    try {
      setFormLoading(true);
      if (isEditing && editingTechId !== null) {
        await api.put(`/technicians/${editingTechId}`, techFormData);
        showMessage("Technician updated successfully", "success");
      } else {
        await api.post("/technicians/", techFormData);
        showMessage("Technician added successfully", "success");
      }
      resetForm();
      fetchTechnicians();
    } catch (error: any) {
      console.error(error);
      const errorMsg = error.response?.data?.error || error.response?.data?.detail || "Unable to save technician. Please try again.";
      showMessage(errorMsg, "error");
    } finally {
      setFormLoading(false);
    }
  };

  const normalizeStatus = (s: string) => {
    const lower = (s || "").toLowerCase();
    if (lower === "available") return "Available";
    if (lower === "busy") return "Busy";
    if (lower === "assigned") return "Assigned";
    if (lower === "offline") return "Offline";
    return s;
  };

  const filteredTechnicians = technicians
    .filter(t => statusFilter === "ALL" || normalizeStatus(t.technician_status) === statusFilter)
    .filter(t => {
      const s = searchTerm.toLowerCase();
      return (
        (t.technician_name && t.technician_name.toLowerCase().includes(s)) ||
        (t.technician_skill && t.technician_skill.toLowerCase().includes(s)) ||
        (t.technician_location && t.technician_location.toLowerCase().includes(s))
      );
    });

  const techTotalPages = Math.max(1, Math.ceil(filteredTechnicians.length / TECH_PAGE_SIZE));
  const safeTechPage = Math.min(techPage, techTotalPages);
  const paginatedTechnicians = filteredTechnicians.slice((safeTechPage - 1) * TECH_PAGE_SIZE, safeTechPage * TECH_PAGE_SIZE);

  useEffect(() => {
    const total = Math.max(1, Math.ceil(filteredTechnicians.length / TECH_PAGE_SIZE));
    if (techPage > total) {
      setTechPage(total);
    }
  }, [filteredTechnicians.length, techPage]);

  const getTechPageNums = () => {
    const nums: number[] = [];
    const delta = 2;
    for (let i = Math.max(1, safeTechPage - delta); i <= Math.min(techTotalPages, safeTechPage + delta); i++) {
      nums.push(i);
    }
    return nums;
  };

  return (
    <div style={styles.techPage}>
      <style>{localCss}</style>

      {/* Toast */}
      {message.text && (
        <div
          style={{
            ...styles.toastMessage,
            ...(message.type === "success" ? styles.toastSuccess : styles.toastError)
          }}
        >
          {message.type === "success" ? "✓" : "✕"} {message.text}
        </div>
      )}

      {/* Main Content Area: Grid Only */}
      <div style={styles.mainContentRow}>
        {/* Technicians Grid & Filters */}
        <div style={styles.contentCard}>
          <div className="card-header-responsive" style={styles.cardHeader}>
            <div>
              <span style={styles.sectionBadge}>Registry</span>
              <p style={styles.cardSubtitle}>Manage field technicians and update their availability</p>
            </div>
            <div style={styles.headerActionsRow}>
              <button className="refresh-icon-btn-style" style={styles.refreshIconBtn} onClick={fetchTechnicians} title="Refresh">⟳ Refresh</button>
              <button className="add-tech-btn-style" style={styles.addTechBtn} onClick={() => { resetForm(); setIsFormOpen(true); }}>+ Add Technician</button>
            </div>
          </div>

          {/* Filters */}
          <div className="tech-filters-row-responsive" style={styles.techFiltersRow}>
            <div className="filter-group-responsive" style={styles.filterGroup}>
              <label style={styles.filterLabel}>Search</label>
              <input
                type="text"
                placeholder="Name, skill, location..."
                value={searchTerm}
                onChange={e => setSearchTerm(e.target.value)}
                className="filter-input-style"
                style={styles.filterInput}
              />
            </div>
            <div className="filter-group-responsive" style={styles.filterGroup}>
              <label style={styles.filterLabel}>Status</label>
              <select
                value={statusFilter}
                onChange={e => setStatusFilter(e.target.value)}
                className="filter-select-style"
                style={styles.filterInput}
              >
                <option value="ALL">All Statuses</option>
                <option value="Available">Available</option>
                <option value="Busy">Busy</option>
                <option value="Assigned">Assigned</option>
                <option value="Offline">Offline</option>
              </select>
            </div>
          </div>

          <p style={styles.resultsCount}>{filteredTechnicians.length} technician{filteredTechnicians.length !== 1 ? "s" : ""} found</p>

          {fetchError && <div style={styles.alertError}>{fetchError}</div>}

          {loading ? (
            <LoadingSpinner message="Loading technicians..." />
          ) : filteredTechnicians.length === 0 ? (
            <EmptyState
              title={
                searchTerm.trim() || statusFilter !== "ALL"
                  ? "No technicians match your filters"
                  : "No technicians found"
              }
              description={
                searchTerm.trim() || statusFilter !== "ALL"
                  ? "Try adjusting your search terms or filters."
                  : "Add field technicians to get started."
              }
              action={
                searchTerm.trim() || statusFilter !== "ALL" ? (
                  <button
                    className="refresh-icon-btn-style"
                    style={styles.refreshIconBtn}
                    onClick={() => {
                      setSearchTerm("");
                      setStatusFilter("ALL");
                    }}
                  >
                    Clear Filters
                  </button>
                ) : (
                  <button
                    className="add-tech-btn-style"
                    style={styles.addTechBtn}
                    onClick={() => {
                      resetForm();
                      setIsFormOpen(true);
                    }}
                  >
                    + Add Technician
                  </button>
                )
              }
            />
          ) : (
            <div style={styles.tableContainer}>
              <table style={styles.dashboardTable}>
                <thead>
                  <tr>
                    <th style={styles.dashboardTableTh}>Technician</th>
                    <th style={styles.dashboardTableTh}>Skill</th>
                    <th style={styles.dashboardTableTh}>Location</th>
                    <th style={styles.dashboardTableTh}>Status</th>
                    <th style={styles.dashboardTableTh}>Workload</th>
                    <th style={styles.dashboardTableTh}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {paginatedTechnicians.map(tech => {
                    const pct = tech.max_jobs > 0 ? Math.min((tech.current_jobs / tech.max_jobs) * 100, 100) : 0;
                    return (
                      <tr key={tech.technician_id} className="dashboard-table-row">
                        <td style={styles.dashboardTableTd}>
                          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                            <div style={styles.techAvatar}>
                              {tech.technician_name.charAt(0).toUpperCase()}
                            </div>
                            <strong>{tech.technician_name}</strong>
                          </div>
                        </td>
                        <td style={styles.dashboardTableTd}>{tech.technician_skill}</td>
                        <td style={styles.dashboardTableTd}>{tech.technician_location}</td>
                        <td style={styles.dashboardTableTd}>
                          <div style={styles.availabilityControl}>
                            <div style={styles.selectWrapper}>
                              <select
                                value={normalizeStatus(tech.technician_status)}
                                onChange={e => handleStatusChange(tech.technician_id, e.target.value)}
                                disabled={updatingId === tech.technician_id}
                                className="status-select-style"
                                style={getStatusSelectStyle(tech.technician_status)}
                              >
                                <option value="Available">Available</option>
                                <option value="Busy">Busy</option>
                                <option value="Assigned">Assigned</option>
                                <option value="Offline">Offline</option>
                              </select>
                            </div>
                          </div>
                        </td>
                        <td style={styles.dashboardTableTd}>
                          <div style={styles.workloadInfo}>
                            <div style={styles.workloadBar}>
                              <div
                                style={{
                                  ...styles.workloadFill,
                                  width: `${pct}%`,
                                  background: tech.current_jobs >= tech.max_jobs ? "#D96C6C" : "#7AAE8A"
                                }}
                              />
                            </div>
                            <span style={styles.workloadText}>
                              {tech.current_jobs}/{tech.max_jobs} jobs
                            </span>
                          </div>
                        </td>
                        <td style={styles.dashboardTableTd}>
                          <div style={styles.jobItemActions}>
                            <button
                              className="icon-action-btn-style"
                              style={{ ...styles.iconActionBtn, color: '#16a34a' }}
                              onClick={() => setViewTech(tech)}
                              title="View technician details"
                              aria-label="View technician"
                            >
                              <Eye size={15} />
                            </button>
                            <button
                              className="icon-action-btn-style"
                              style={{ ...styles.iconActionBtn, color: '#ca8a04' }}
                              onClick={() => handleEdit(tech)}
                              title="Edit technician"
                              aria-label="Edit technician"
                            >
                              <Pencil size={15} />
                            </button>
                            <button
                              className="icon-action-btn-style"
                              style={{ ...styles.iconActionBtn, color: '#dc2626' }}
                              onClick={() => handleDelete(tech.technician_id)}
                              title="Delete technician"
                              aria-label="Delete technician"
                            >
                              <Trash2 size={15} />
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}

          {/* Pagination */}
          {!loading && (
            <div style={styles.techPagination}>
              <span style={styles.techPageInfo}>
                Page <strong>{safeTechPage}</strong> of <strong>{techTotalPages}</strong> · {filteredTechnicians.length} results
              </span>
              <div style={styles.techPageControls}>
                <button className="tech-page-btn-style" style={styles.techPageBtn} type="button" onClick={() => setTechPage(1)} disabled={safeTechPage === 1}>«</button>
                <button className="tech-page-btn-style" style={styles.techPageBtn} type="button" onClick={() => setTechPage(p => Math.max(1, p - 1))} disabled={safeTechPage === 1}>‹ Prev</button>
                <div style={styles.techPageNumbers}>
                  {getTechPageNums().map(n => (
                    <button
                      key={n}
                      type="button"
                      className={`tech-page-num-style ${n === safeTechPage ? "active" : ""}`}
                      style={{
                        ...styles.techPageNum,
                        ...(n === safeTechPage ? styles.techPageNumActive : {})
                      }}
                      onClick={() => setTechPage(n)}
                    >
                      {n}
                    </button>
                  ))}
                </div>
                <button className="tech-page-btn-style" style={styles.techPageBtn} type="button" onClick={() => setTechPage(p => Math.min(techTotalPages, p + 1))} disabled={safeTechPage === techTotalPages}>Next ›</button>
                <button className="tech-page-btn-style" style={styles.techPageBtn} type="button" onClick={() => setTechPage(techTotalPages)} disabled={safeTechPage === techTotalPages}>»</button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* View Technician Modal */}
      {viewTech && (
        <div style={styles.popupOverlay} onClick={() => setViewTech(null)}>
          <div style={styles.viewJobModal} onClick={e => e.stopPropagation()}>
            <div style={styles.viewModalHeader}>
              <h3 style={styles.viewModalHeaderH3}>Technician Details</h3>
              <button onClick={() => setViewTech(null)} style={{ background: 'none', border: 'none', fontSize: 22, cursor: 'pointer', color: '#6b7280' }}>×</button>
            </div>
            <div style={styles.viewModalBody}>
              <div style={styles.viewDetailRow}><span style={styles.viewLabel}>Technician ID</span><span style={styles.viewValue}>#{viewTech.technician_id}</span></div>
              <div style={styles.viewDetailRow}><span style={styles.viewLabel}>Name</span><span style={styles.viewValue}>{viewTech.technician_name}</span></div>
              <div style={styles.viewDetailRow}><span style={styles.viewLabel}>Skill</span><span style={styles.viewValue}>{viewTech.technician_skill}</span></div>
              <div style={styles.viewDetailRow}><span style={styles.viewLabel}>Location / Zone</span><span style={styles.viewValue}>{viewTech.technician_location}</span></div>
              <div style={styles.viewDetailRow}><span style={styles.viewLabel}>Status</span><StatusBadge status={viewTech.technician_status as any} size="md" /></div>
              <div style={styles.viewDetailRow}><span style={styles.viewLabel}>Active Jobs</span><span style={styles.viewValue}>{viewTech.current_jobs} / {viewTech.max_jobs}</span></div>
            </div>
          </div>
        </div>
      )}

      {/* Sliding Sidebar for Technician Form */}
      <div 
        style={{
          ...styles.techFormSidebar,
          right: isFormOpen ? "0" : "-420px"
        }}
      >
        <div style={styles.sidebarHeader}>
          <h3 style={styles.sidebarHeaderH3}>{isEditing ? "Edit Technician" : "Add New Technician"}</h3>
          <button className="close-sidebar-style" style={styles.closeSidebar} onClick={resetForm}>×</button>
        </div>
        <div style={styles.sidebarContent}>
          <form style={styles.techForm} onSubmit={(e) => {
            handleFormSubmit(e);
            if (validateForm()) setIsFormOpen(false);
          }}>
            <div style={styles.formGroup}>
              <label style={styles.formGroupLabel}>Full Name <span style={styles.req}>*</span></label>
              <input
                type="text"
                name="technician_name"
                value={techFormData.technician_name}
                onChange={handleFormChange}
                placeholder="e.g. Rajesh Kumar"
                className="form-group-input-style"
                style={{
                  ...styles.formGroupInput,
                  borderColor: formErrors.technician_name ? "#D96C6C" : "#E3ECE7"
                }}
              />
              {formErrors.technician_name && <span style={styles.fieldError}>{formErrors.technician_name}</span>}
            </div>

            <div style={styles.formGroup}>
              <label style={styles.formGroupLabel}>Skill <span style={styles.req}>*</span></label>
              <input
                type="text"
                name="technician_skill"
                value={techFormData.technician_skill}
                onChange={handleFormChange}
                placeholder="e.g. Electrical, HVAC"
                className="form-group-input-style"
                style={{
                  ...styles.formGroupInput,
                  borderColor: formErrors.technician_skill ? "#D96C6C" : "#E3ECE7"
                }}
                list="skill-suggestions"
              />
              <datalist id="skill-suggestions">
                {skills.map(s => <option key={s} value={s} />)}
              </datalist>
              {formErrors.technician_skill && <span style={styles.fieldError}>{formErrors.technician_skill}</span>}
            </div>

            <div style={styles.formGroup}>
              <label style={styles.formGroupLabel}>Location <span style={styles.req}>*</span></label>
              <input
                type="text"
                name="technician_location"
                value={techFormData.technician_location}
                onChange={handleFormChange}
                placeholder="e.g. Mumbai, Delhi"
                className="form-group-input-style"
                style={{
                  ...styles.formGroupInput,
                  borderColor: formErrors.technician_location ? "#D96C6C" : "#E3ECE7"
                }}
              />
              {formErrors.technician_location && <span style={styles.fieldError}>{formErrors.technician_location}</span>}
            </div>

            <div style={styles.formGroup}>
              <label style={styles.formGroupLabel}>{isEditing ? "Status" : "Initial Status"}</label>
              <select
                name="technician_status"
                value={techFormData.technician_status}
                onChange={handleFormChange}
                className="form-group-select-style"
                style={styles.formGroupInput}
              >
                <option value="Available">Available</option>
                <option value="Busy">Busy</option>
                <option value="Assigned">Assigned</option>
                <option value="Offline">Offline</option>
              </select>
            </div>

            <div style={styles.formActions}>
              <button type="submit" className="btn-primary-style" style={styles.btnPrimary} disabled={formLoading}>
                {formLoading ? "Saving..." : isEditing ? "Update Technician" : "Add Technician"}
              </button>
              <button type="button" className="btn-secondary-style" style={styles.btnSecondary} onClick={resetForm}>
                Cancel
              </button>
            </div>
          </form>
        </div>
      </div>
      {isFormOpen && <div style={styles.sidebarOverlay} onClick={resetForm}></div>}
    </div>
  );
}

export default TechnicianList;
