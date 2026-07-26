import React, { useState, useEffect, useRef } from "react";
import { ChevronDown } from "lucide-react";

interface SkillComboSelectProps {
  value: string;
  onChange: (val: string) => void;
  placeholder?: string;
  inputStyle?: React.CSSProperties;
  className?: string;
  hasError?: boolean;
  name?: string;
}

const DEFAULT_SUGGESTIONS = [
  "HVAC Repair",
  "Electrical",
  "Plumbing",
  "Network Support",
  "General Maintenance",
  "Appliance Repair",
  "CCTV & Security",
  "Roofing & Carpentry",
];

export const SkillComboSelect: React.FC<SkillComboSelectProps> = ({
  value,
  onChange,
  placeholder = "e.g. Electrical, HVAC",
  inputStyle,
  className = "",
  hasError = false,
  name,
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleSelectSuggestion = (suggestion: string) => {
    if (!value) {
      onChange(suggestion);
    } else {
      const parts = value.split(",").map((p) => p.trim()).filter(Boolean);
      if (!parts.includes(suggestion)) {
        onChange([...parts, suggestion].join(", "));
      }
    }
    setIsOpen(false);
  };

  return (
    <div ref={dropdownRef} style={{ position: "relative", width: "100%" }}>
      <div style={{ position: "relative", display: "flex", alignItems: "center", width: "100%" }}>
        <input
          type="text"
          name={name}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onFocus={() => setIsOpen(true)}
          placeholder={placeholder}
          className={className}
          style={{
            ...inputStyle,
            width: "100%",
            paddingRight: "34px",
            borderColor: hasError ? "#ef4444" : inputStyle?.borderColor || "#e2e8f0",
            boxSizing: "border-box",
          }}
        />
        <button
          type="button"
          onClick={() => setIsOpen(!isOpen)}
          tabIndex={-1}
          style={{
            position: "absolute",
            right: "8px",
            top: "50%",
            transform: "translateY(-50%)",
            background: "none",
            border: "none",
            cursor: "pointer",
            color: "#64748B",
            display: "flex",
            alignItems: "center",
            padding: "4px",
            zIndex: 2,
          }}
        >
          <ChevronDown size={16} />
        </button>
      </div>

      {isOpen && (
        <div
          style={{
            position: "absolute",
            top: "calc(100% + 4px)",
            left: 0,
            right: 0,
            background: "#FFFFFF",
            borderRadius: "10px",
            border: "1px solid #E2E8F0",
            boxShadow: "0 10px 25px rgba(0, 0, 0, 0.12)",
            zIndex: 9999,
            maxHeight: "220px",
            overflowY: "auto",
            padding: "4px 0",
          }}
        >
          {DEFAULT_SUGGESTIONS.map((s) => {
            const isSelected = value
              .split(",")
              .map((p) => p.trim())
              .includes(s);

            return (
              <div
                key={s}
                onClick={() => handleSelectSuggestion(s)}
                onMouseEnter={(e) => (e.currentTarget.style.background = "#F1F5F9")}
                onMouseLeave={(e) => (e.currentTarget.style.background = "#FFFFFF")}
                style={{
                  padding: "8px 14px",
                  fontSize: "13px",
                  fontWeight: 600,
                  color: "#1E293B",
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  transition: "background 0.15s",
                }}
              >
                <span>{s}</span>
                {isSelected && (
                  <span style={{ fontSize: "11px", color: "#16A34A", fontWeight: 700 }}>
                    ✓ Selected
                  </span>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
