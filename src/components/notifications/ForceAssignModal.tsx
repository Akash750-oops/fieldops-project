import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { 
  X, 
  Search, 
  User, 
  MapPin, 
  Briefcase, 
  Clock, 
  AlertCircle, 
  CheckCircle, 
  ShieldAlert 
} from "lucide-react";
import { getAvailableTechnicians, forceAssignJob, getJob } from "../../services/planningService";

interface ForceAssignModalProps {
  jobId: number;
  jobTitle: string;
  initialJobLocation?: string;
  currentUserRole?: string;
  onClose: () => void;
  onSuccess: () => void;
}

interface Technician {
  technician_id: number;
  technician: string;
  skill: string;
  location: string;
  status: string;
  current_jobs: number;
  max_jobs: number;
  eligible_for_assignment: boolean;
}

// Haversine distance calculation in kilometers
function calculateDistance(loc1?: string, loc2?: string): number | null {
  if (!loc1 || !loc2) return null;
  const parts1 = loc1.split(",");
  const parts2 = loc2.split(",");
  if (parts1.length !== 2 || parts2.length !== 2) return null;
  
  const lat1 = parseFloat(parts1[0].trim());
  const lon1 = parseFloat(parts1[1].trim());
  const lat2 = parseFloat(parts2[0].trim());
  const lon2 = parseFloat(parts2[1].trim());
  
  if (isNaN(lat1) || isNaN(lon1) || isNaN(lat2) || isNaN(lon2)) return null;

  const R = 6371; // Earth radius in km
  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLon = ((lon2 - lon1) * Math.PI) / 180;
  
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos((lat1 * Math.PI) / 180) *
      Math.cos((lat2 * Math.PI) / 180) *
      Math.sin(dLon / 2) *
      Math.sin(dLon / 2);
  
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c;
}

export default function ForceAssignModal({
  jobId,
  jobTitle,
  initialJobLocation,
  currentUserRole = "dispatcher",
  onClose,
  onSuccess
}: ForceAssignModalProps) {
  const [jobLocation, setJobLocation] = useState(initialJobLocation || "");
  const [searchQuery, setSearchQuery] = useState("");
  const [technicians, setTechnicians] = useState<Technician[]>([]);
  const [loadingTechs, setLoadingTechs] = useState(true);
  const [justification, setJustification] = useState("");
  const [selectedTech, setSelectedTech] = useState<Technician | null>(null);
  
  // Interactive role selector to test authentication logic in mockup
  const [simulatedRole, setSimulatedRole] = useState(currentUserRole);
  
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const [successMsg, setSuccessMsg] = useState("");

  // Fetch job location if not provided
  useEffect(() => {
    if (!jobLocation) {
      getJob(jobId)
        .then(res => {
          if (res.data && res.data.location) {
            setJobLocation(res.data.location);
          }
        })
        .catch(err => {
          console.warn("Failed to fetch job location coordinates", err);
        });
    }
  }, [jobId, jobLocation]);

  // Fetch available technicians
  useEffect(() => {
    const fetchTechs = async () => {
      try {
        setLoadingTechs(true);
        const res = await getAvailableTechnicians();
        if (res && res.data) {
          setTechnicians(res.data);
        }
      } catch (err) {
        setError("Failed to load technicians list. Make sure backend is running.");
      } finally {
        setLoadingTechs(false);
      }
    };
    fetchTechs();
  }, []);

  // Filter technicians based on search query
  const filteredTechs = technicians.filter(tech => {
    const q = searchQuery.toLowerCase();
    return (
      tech.technician.toLowerCase().includes(q) ||
      tech.skill.toLowerCase().includes(q) ||
      tech.location.toLowerCase().includes(q)
    );
  });

  // Role authorization validation check (admin/dispatcher only)
  const isAuthorized = 
    simulatedRole.toLowerCase() === "admin" || 
    simulatedRole.toLowerCase() === "dispatcher" || 
    simulatedRole.toLowerCase() === "manager";

  // Justification validation check (minimum 50 characters, FR-025)
  const isJustificationValid = justification.trim().length >= 50;

  // Final form validation
  const canConfirm = 
    selectedTech !== null && 
    isAuthorized && 
    isJustificationValid && 
    !submitting;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!canConfirm || !selectedTech) return;

    try {
      setSubmitting(true);
      setError("");
      
      const response = await forceAssignJob(
        jobId, 
        selectedTech.technician_id, 
        justification, 
        simulatedRole
      );

      if (response && response.status >= 200 && response.status < 300) {
        setSuccessMsg("Immediate assignment applied successfully! Bypassed all automated cooldowns and planning constraints.");
        setTimeout(() => {
          onSuccess();
          onClose();
        }, 2000);
      } else {
        throw new Error(response?.data?.detail || "Override assignment request failed");
      }
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || "Failed to force assign technician.";
      setError(msg);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[300] flex items-center justify-center bg-slate-950/70 backdrop-blur-md p-4 animate-fadeIn">
      <motion.div 
        initial={{ opacity: 0, scale: 0.95, y: 20 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.95, y: 20 }}
        transition={{ type: "spring", duration: 0.4 }}
        className="w-full max-w-4xl bg-white rounded-2xl shadow-2xl overflow-hidden border border-slate-100 flex flex-col max-h-[90vh]"
        style={{ fontFamily: "'Inter', sans-serif" }}
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-title"
      >
        {/* Modal Header */}
        <div className="p-6 bg-slate-900 text-white flex justify-between items-center relative">
          <div>
            <div className="flex items-center gap-2">
              <ShieldAlert className="text-amber-500 w-5 h-5 shrink-0" />
              <h2 id="modal-title" className="text-lg font-bold tracking-tight">Manual Intervention: Force Assign</h2>
            </div>
            <p className="text-slate-400 text-xs mt-1">
              Job: <span className="font-semibold text-slate-200">{jobTitle}</span> (ID: #{jobId})
            </p>
          </div>
          <button 
            onClick={onClose}
            className="p-1.5 rounded-full hover:bg-white/10 text-slate-400 hover:text-white transition"
            aria-label="Close modal"
          >
            <X size={20} />
          </button>
        </div>

        {/* Role Simulator Panel */}
        <div className="bg-slate-100 border-b border-slate-200 px-6 py-2.5 flex flex-wrap items-center justify-between gap-3 text-xs font-semibold text-slate-700">
          <div className="flex items-center gap-1.5">
            <span className="text-slate-500">Simulate Dispatcher Role:</span>
            <select
              value={simulatedRole}
              onChange={(e) => {
                setSimulatedRole(e.target.value);
                setError("");
              }}
              className="bg-white border border-slate-300 rounded px-2 py-0.5 font-bold focus:outline-none"
              aria-label="Simulated role selector"
            >
              <option value="dispatcher">Dispatcher (Authorized)</option>
              <option value="admin">Admin (Authorized)</option>
              <option value="manager">Manager (Authorized)</option>
              <option value="technician">Technician (Unauthorized)</option>
            </select>
          </div>
          {!isAuthorized && (
            <span className="text-rose-600 flex items-center gap-1">
              <ShieldAlert size={12} />
              Unauthorized Role. Force Assign is restricted to Dispatchers/Managers.
            </span>
          )}
        </div>

        {/* Modal Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6 flex flex-col min-h-0">
          {error && (
            <div className="p-3.5 bg-rose-50 border border-rose-100 text-rose-700 rounded-xl text-sm font-semibold flex items-start gap-2 animate-shake">
              <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" />
              <span>{error}</span>
            </div>
          )}

          {successMsg && (
            <div className="p-3.5 bg-emerald-50 border border-emerald-100 text-emerald-700 rounded-xl text-sm font-semibold flex items-start gap-2">
              <CheckCircle className="w-5 h-5 shrink-0 mt-0.5" />
              <span>{successMsg}</span>
            </div>
          )}

          {/* Technician Selection Section */}
          <div className="flex-1 min-h-[250px] flex flex-col min-h-0">
            <div className="flex justify-between items-center mb-3">
              <h3 className="text-sm font-bold text-slate-800 uppercase tracking-wider">
                Select Technician
              </h3>
              
              {/* Search Bar */}
              <div className="relative w-64">
                <Search size={14} className="absolute left-3 top-2.5 text-slate-400" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search by name, skill, zone..."
                  className="w-full bg-slate-50 border border-slate-200 rounded-lg pl-8 pr-3 py-1.5 text-xs font-semibold focus:outline-none focus:ring-1 focus:ring-slate-800"
                  aria-label="Search technicians"
                />
              </div>
            </div>

            {loadingTechs ? (
              <div className="flex-1 flex flex-col items-center justify-center py-12">
                <div className="w-8 h-8 border-4 border-slate-200 border-t-slate-900 rounded-full animate-spin"></div>
                <p className="text-xs text-slate-500 font-medium mt-3">Loading available technicians...</p>
              </div>
            ) : filteredTechs.length === 0 ? (
              <div className="flex-1 flex flex-col items-center justify-center py-12 border border-dashed border-slate-200 rounded-xl bg-slate-50">
                <User size={32} className="text-slate-300" />
                <p className="text-xs text-slate-400 font-bold mt-2">No matching technicians found</p>
                <p className="text-[10px] text-slate-400">Try refining search parameters.</p>
              </div>
            ) : (
              <div className="flex-1 overflow-y-auto border border-slate-100 rounded-xl shadow-sm min-h-0">
                <table className="min-w-full bg-white divide-y divide-slate-100 text-left text-xs">
                  <thead className="bg-slate-50 text-slate-500 font-bold uppercase tracking-wider sticky top-0 z-10">
                    <tr>
                      <th className="px-4 py-2.5 w-10"></th>
                      <th className="px-4 py-2.5">Technician</th>
                      <th className="px-4 py-2.5">Core Skill</th>
                      <th className="px-4 py-2.5 text-center">Active Workload</th>
                      <th className="px-4 py-2.5 text-center">Calculated Distance</th>
                      <th className="px-4 py-2.5 text-center">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100 font-medium text-slate-700">
                    {filteredTechs.map(tech => {
                      const isSelected = selectedTech?.technician_id === tech.technician_id;
                      const distance = calculateDistance(jobLocation, tech.location);
                      const displayDist = distance !== null ? `${distance.toFixed(1)} km` : "-";
                      const isUnderLimit = tech.current_jobs < tech.max_jobs;

                      return (
                        <tr 
                          key={tech.technician_id} 
                          onClick={() => setSelectedTech(tech)}
                          className={`cursor-pointer transition ${
                            isSelected 
                              ? "bg-slate-900 text-white hover:bg-slate-800" 
                              : "hover:bg-slate-50"
                          }`}
                        >
                          <td className="px-4 py-3 text-center">
                            <input
                              type="radio"
                              name="selected-tech"
                              checked={isSelected}
                              onChange={() => setSelectedTech(tech)}
                              className="accent-slate-900 cursor-pointer"
                              aria-label={`Select ${tech.technician}`}
                            />
                          </td>
                          <td className="px-4 py-3 font-bold">
                            {tech.technician}
                          </td>
                          <td className="px-4 py-3">
                            <span className={`px-2 py-0.5 rounded text-[10px] uppercase font-bold ${
                              isSelected ? "bg-slate-800 text-white" : "bg-slate-100 text-slate-700"
                            }`}>
                              {tech.skill}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-center font-bold">
                            <span className={!isUnderLimit ? "text-rose-500" : ""}>
                              {tech.current_jobs}
                            </span>
                            <span className={isSelected ? "text-slate-400" : "text-slate-400"}>
                              /{tech.max_jobs} jobs
                            </span>
                          </td>
                          <td className="px-4 py-3 text-center font-semibold">
                            {displayDist}
                          </td>
                          <td className="px-4 py-3 text-center">
                            <span className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase ${
                              tech.status.toLowerCase() === "available" 
                                ? "bg-emerald-100 text-emerald-800 border border-emerald-200" 
                                : "bg-sky-100 text-sky-800 border border-sky-200"
                            }`}>
                              {tech.status}
                            </span>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Justification & Override Controls */}
          <div className="bg-slate-50 p-4 rounded-xl border border-slate-200 space-y-4">
            <div>
              <div className="flex justify-between items-center mb-1">
                <label 
                  htmlFor="justification-textarea" 
                  className="block text-xs font-bold text-slate-700 uppercase tracking-wider"
                >
                  Justification (Requirement FR-025)
                </label>
                <span className={`text-xs font-semibold ${isJustificationValid ? "text-emerald-600" : "text-amber-600"}`}>
                  {justification.trim().length} / 50 characters minimum
                </span>
              </div>
              <textarea
                id="justification-textarea"
                value={justification}
                onChange={(e) => setJustification(e.target.value)}
                placeholder="Enter justification detailing why this planning rules override is required (min 50 characters required)..."
                rows={3}
                className={`w-full bg-white border rounded-lg p-3 text-xs font-semibold focus:outline-none transition ${
                  justification.trim().length > 0 && !isJustificationValid
                    ? "border-amber-400 focus:ring-1 focus:ring-amber-500"
                    : "border-slate-200 focus:ring-1 focus:ring-slate-800"
                }`}
                required
              />
            </div>
          </div>
        </div>

        {/* Footer controls */}
        <div className="p-4 bg-slate-100 border-t border-slate-200 flex flex-col sm:flex-row justify-between items-center gap-3">
          <div className="text-xs text-slate-500 font-semibold flex items-center gap-1">
            <ShieldAlert size={14} className="text-slate-400" />
            <span>Override logs directly to Audit log automatically.</span>
          </div>

          <div className="flex gap-2.5 w-full sm:w-auto justify-end">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 rounded-lg text-xs font-bold transition"
            >
              Cancel
            </button>
            <button
              onClick={handleSubmit}
              disabled={!canConfirm}
              className="px-5 py-2 bg-slate-900 hover:bg-slate-800 text-white rounded-lg text-xs font-bold transition disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-1.5"
            >
              {submitting ? "Applying Override..." : "Confirm Force Assign"}
            </button>
          </div>
        </div>
      </motion.div>
    </div>
  );
}
