import React, { useState } from "react";
import { LucideIcon, Inbox } from "lucide-react";

interface EmptyStateProps {
  icon?: LucideIcon;
  title: string;
  description?: string | React.ReactNode;
  action?: React.ReactNode;
  className?: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  icon: Icon = Inbox,
  title,
  description,
  action,
  className = "",
}) => {
  const [isHovered, setIsHovered] = useState(false);

  const containerStyle: React.CSSProperties = {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    justifyContent: "center",
    padding: "56px 24px",
    textAlign: "center",
    width: "100%",
    boxSizing: "border-box",
  };

  const iconWrapStyle: React.CSSProperties = {
    width: "64px",
    height: "64px",
    borderRadius: "50%",
    background: "#EEF4F1",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    marginBottom: "16px",
    transition: "transform 0.25s cubic-bezier(0.4, 0, 0.2, 1)",
    flexShrink: 0,
    transform: isHovered ? "scale(1.08)" : "scale(1)",
  };

  const titleStyle: React.CSSProperties = {
    fontSize: "15px",
    fontWeight: 700,
    color: "#2F4F3E",
    margin: "0 0 6px",
    fontFamily: "'Inter', sans-serif",
    lineHeight: 1.2,
  };

  const descriptionStyle: React.CSSProperties = {
    fontSize: "13px",
    color: "#6B7280",
    margin: 0,
    fontFamily: "'Inter', sans-serif",
    maxWidth: "340px",
    lineHeight: 1.5,
  };

  const actionStyle: React.CSSProperties = {
    marginTop: "16px",
    display: "flex",
    justifyContent: "center",
    gap: "8px",
  };

  return (
    <div 
      style={containerStyle} 
      className={`empty-state-container ${className}`}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      <div style={iconWrapStyle} className="empty-state-icon-wrap">
        <Icon size={28} style={{ color: "#7AAE8A" }} />
      </div>
      <h3 style={titleStyle} className="empty-state-title">{title}</h3>
      {description && <p style={descriptionStyle} className="empty-state-description">{description}</p>}
      {action && <div style={actionStyle} className="empty-state-action">{action}</div>}
    </div>
  );
};

export default EmptyState;
