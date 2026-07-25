import React, { useState } from "react";
import { X, Plus, Trash2, CheckCircle2, DollarSign, Image as ImageIcon } from "lucide-react";
import { closeJob, JobClosureData } from "../../services/planningService";

interface JobClosureModalProps {
  jobId: number | string;
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export const JobClosureModal: React.FC<JobClosureModalProps> = ({
  jobId,
  isOpen,
  onClose,
  onSuccess,
}) => {
  const [workSummary, setWorkSummary] = useState("");
  const [beforeImages, setBeforeImages] = useState<string[]>([]);
  const [afterImages, setAfterImages] = useState<string[]>([""]);
  const [labourCost, setLabourCost] = useState<number>(0);
  const [materialCost, setMaterialCost] = useState<number>(0);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const subtotal = (Number(labourCost) || 0) + (Number(materialCost) || 0);

  const handleAddBeforeImage = () => {
    setBeforeImages((prev) => [...prev, ""]);
  };

  const handleUpdateBeforeImage = (index: number, value: string) => {
    setBeforeImages((prev) => {
      const copy = [...prev];
      copy[index] = value;
      return copy;
    });
  };

  const handleRemoveBeforeImage = (index: number) => {
    setBeforeImages((prev) => prev.filter((_, i) => i !== index));
  };

  const handleAddAfterImage = () => {
    setAfterImages((prev) => [...prev, ""]);
  };

  const handleUpdateAfterImage = (index: number, value: string) => {
    setAfterImages((prev) => {
      const copy = [...prev];
      copy[index] = value;
      return copy;
    });
  };

  const handleRemoveAfterImage = (index: number) => {
    if (afterImages.length <= 1) return;
    setAfterImages((prev) => prev.filter((_, i) => i !== index));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!workSummary.trim()) {
      setError("Work summary is required.");
      return;
    }

    const filteredAfterImages = afterImages.map((img) => img.trim()).filter(Boolean);
    if (filteredAfterImages.length === 0) {
      setError("At least one after image URL / file path is required.");
      return;
    }

    const filteredBeforeImages = beforeImages.map((img) => img.trim()).filter(Boolean);

    setIsSubmitting(true);

    try {
      const payload: JobClosureData = {
        work_summary: workSummary.trim(),
        before_images: filteredBeforeImages,
        after_images: filteredAfterImages,
        labour_cost: Math.max(0, Number(labourCost) || 0),
        material_cost: Math.max(0, Number(materialCost) || 0),
      };

      await closeJob(jobId, payload);
      onSuccess();
      onClose();
    } catch (err: any) {
      const errMsg = err?.response?.data?.detail || err?.message || "Failed to complete job.";
      setError(typeof errMsg === "string" ? errMsg : JSON.stringify(errMsg));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div style={styles.overlay} onClick={onClose}>
      <div style={styles.modal} onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div style={styles.header}>
          <div style={styles.headerTitleWrap}>
            <CheckCircle2 size={20} color="#166534" />
            <h3 style={styles.headerTitle}>Complete Job #{jobId}</h3>
          </div>
          <button style={styles.closeBtn} onClick={onClose}>
            <X size={20} />
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} style={styles.body}>
          {error && <div style={styles.errorAlert}>{error}</div>}

          {/* Work Summary */}
          <div style={styles.formGroup}>
            <label style={styles.label}>
              Work Summary <span style={styles.req}>*</span>
            </label>
            <textarea
              style={styles.textarea}
              rows={4}
              value={workSummary}
              onChange={(e) => setWorkSummary(e.target.value)}
              placeholder="Describe work completed, tests run, and final status..."
              required
            />
          </div>

          {/* Before Images */}
          <div style={styles.formGroup}>
            <label style={styles.label}>Before Images (Optional)</label>
            {beforeImages.map((url, idx) => (
              <div key={idx} style={styles.imageRow}>
                <ImageIcon size={16} color="#64748b" />
                <input
                  type="text"
                  style={styles.input}
                  value={url}
                  onChange={(e) => handleUpdateBeforeImage(idx, e.target.value)}
                  placeholder="Image path or URL (e.g. /uploads/before1.jpg)"
                />
                <button
                  type="button"
                  style={styles.iconBtn}
                  onClick={() => handleRemoveBeforeImage(idx)}
                >
                  <Trash2 size={16} color="#ef4444" />
                </button>
              </div>
            ))}
            <button type="button" style={styles.addBtn} onClick={handleAddBeforeImage}>
              <Plus size={14} /> Add Before Image
            </button>
          </div>

          {/* After Images */}
          <div style={styles.formGroup}>
            <label style={styles.label}>
              After Images (Minimum 1 Required) <span style={styles.req}>*</span>
            </label>
            {afterImages.map((url, idx) => (
              <div key={idx} style={styles.imageRow}>
                <ImageIcon size={16} color="#166534" />
                <input
                  type="text"
                  style={styles.input}
                  value={url}
                  onChange={(e) => handleUpdateAfterImage(idx, e.target.value)}
                  placeholder="Image path or URL (e.g. /uploads/after1.jpg)"
                  required={idx === 0}
                />
                {afterImages.length > 1 && (
                  <button
                    type="button"
                    style={styles.iconBtn}
                    onClick={() => handleRemoveAfterImage(idx)}
                  >
                    <Trash2 size={16} color="#ef4444" />
                  </button>
                )}
              </div>
            ))}
            <button type="button" style={styles.addBtn} onClick={handleAddAfterImage}>
              <Plus size={14} /> Add After Image
            </button>
          </div>

          {/* Financial Breakdown */}
          <div style={styles.costGrid}>
            <div style={styles.formGroup}>
              <label style={styles.label}>Labour Cost ($)</label>
              <input
                type="number"
                step="0.01"
                min="0"
                style={styles.input}
                value={labourCost}
                onChange={(e) => setLabourCost(parseFloat(e.target.value) || 0)}
              />
            </div>

            <div style={styles.formGroup}>
              <label style={styles.label}>Material Cost ($)</label>
              <input
                type="number"
                step="0.01"
                min="0"
                style={styles.input}
                value={materialCost}
                onChange={(e) => setMaterialCost(parseFloat(e.target.value) || 0)}
              />
            </div>

            <div style={styles.formGroup}>
              <label style={styles.label}>Subtotal ($) [Auto-calculated]</label>
              <div style={styles.subtotalWrap}>
                <DollarSign size={16} color="#166534" />
                <input
                  type="text"
                  style={{ ...styles.input, backgroundColor: "#f1f5f9", fontWeight: 700 }}
                  value={subtotal.toFixed(2)}
                  readOnly
                  disabled
                />
              </div>
            </div>
          </div>

          {/* Footer Actions */}
          <div style={styles.footer}>
            <button type="button" style={styles.cancelBtn} onClick={onClose} disabled={isSubmitting}>
              Cancel
            </button>
            <button type="submit" style={styles.submitBtn} disabled={isSubmitting}>
              {isSubmitting ? "Submitting..." : "Submit Job Closure"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  overlay: {
    position: "fixed",
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: "rgba(15, 23, 42, 0.6)",
    backdropFilter: "blur(4px)",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    zIndex: 1100,
    padding: "16px",
  },
  modal: {
    backgroundColor: "#ffffff",
    borderRadius: "12px",
    width: "100%",
    maxWidth: "600px",
    maxHeight: "90vh",
    overflowY: "auto",
    boxShadow: "0 20px 25px -5px rgba(0,0,0,0.1), 0 8px 10px -6px rgba(0,0,0,0.1)",
    border: "1px solid #e2e8f0",
  },
  header: {
    padding: "16px 24px",
    borderBottom: "1px solid #e2e8f0",
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    backgroundColor: "#f8fafc",
  },
  headerTitleWrap: {
    display: "flex",
    alignItems: "center",
    gap: "8px",
  },
  headerTitle: {
    fontSize: "18px",
    fontWeight: 700,
    color: "#0f172a",
    margin: 0,
  },
  closeBtn: {
    background: "none",
    border: "none",
    color: "#64748b",
    cursor: "pointer",
    padding: "4px",
    borderRadius: "4px",
  },
  body: {
    padding: "24px",
    display: "flex",
    flexDirection: "column",
    gap: "18px",
  },
  errorAlert: {
    padding: "12px 16px",
    backgroundColor: "#fef2f2",
    color: "#991b1b",
    borderRadius: "8px",
    fontSize: "14px",
    border: "1px solid #fecaca",
  },
  formGroup: {
    display: "flex",
    flexDirection: "column",
    gap: "6px",
  },
  label: {
    fontSize: "14px",
    fontWeight: 600,
    color: "#334155",
  },
  req: {
    color: "#dc2626",
  },
  textarea: {
    padding: "10px 12px",
    borderRadius: "8px",
    border: "1px solid #cbd5e1",
    fontSize: "14px",
    outline: "none",
    fontFamily: "inherit",
  },
  input: {
    width: "100%",
    padding: "9px 12px",
    borderRadius: "8px",
    border: "1px solid #cbd5e1",
    fontSize: "14px",
    outline: "none",
    boxSizing: "border-box",
  },
  imageRow: {
    display: "flex",
    alignItems: "center",
    gap: "8px",
    marginBottom: "6px",
  },
  iconBtn: {
    background: "none",
    border: "none",
    cursor: "pointer",
    padding: "6px",
  },
  addBtn: {
    display: "inline-flex",
    alignItems: "center",
    gap: "4px",
    alignSelf: "flex-start",
    background: "#f1f5f9",
    border: "1px solid #cbd5e1",
    color: "#334155",
    padding: "6px 12px",
    borderRadius: "6px",
    fontSize: "13px",
    fontWeight: 500,
    cursor: "pointer",
    marginTop: "4px",
  },
  costGrid: {
    display: "grid",
    gridTemplateColumns: "1fr 1fr 1fr",
    gap: "12px",
  },
  subtotalWrap: {
    display: "flex",
    alignItems: "center",
    gap: "4px",
  },
  footer: {
    display: "flex",
    justifyContent: "flex-end",
    gap: "12px",
    marginTop: "12px",
    paddingTop: "16px",
    borderTop: "1px solid #e2e8f0",
  },
  cancelBtn: {
    padding: "10px 18px",
    borderRadius: "8px",
    border: "1px solid #cbd5e1",
    backgroundColor: "#ffffff",
    color: "#475569",
    fontWeight: 600,
    fontSize: "14px",
    cursor: "pointer",
  },
  submitBtn: {
    padding: "10px 20px",
    borderRadius: "8px",
    border: "none",
    backgroundColor: "#166534",
    color: "#ffffff",
    fontWeight: 600,
    fontSize: "14px",
    cursor: "pointer",
  },
};
