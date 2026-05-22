/**
 * StatusBadge.stories.jsx
 * Visual stories / demo gallery for the StatusBadge component.
 * Open this file's route in the app to preview all variants.
 * (Adapted for plain React — no Storybook installed in this project)
 *
 * Add route in App.jsx:
 *   import StatusBadgeStories from "./components/common/StatusBadge.stories.jsx";
 *   {activeTab === "badge-demo" && <StatusBadgeStories />}
 */

import React from "react";
import StatusBadge, { TECHNICIAN_STATUSES } from "./StatusBadge";

const ALL_STATUSES = TECHNICIAN_STATUSES;
const SIZES = ["sm", "md", "lg"];

const sectionStyle = {
  fontFamily: "'Inter', sans-serif",
  marginBottom: 36,
};
const titleStyle = {
  fontSize: 11,
  fontWeight: 700,
  textTransform: "uppercase",
  letterSpacing: "0.07em",
  color: "#6B7280",
  marginBottom: 14,
};
const rowStyle = {
  display: "flex",
  flexWrap: "wrap",
  gap: 10,
  alignItems: "center",
};
const pageStyle = {
  padding: "32px 28px",
  background: "#EEF4F1",
  minHeight: "100vh",
  fontFamily: "'Inter', sans-serif",
};
const h1Style = {
  fontSize: 22,
  fontWeight: 700,
  color: "#2F4F3E",
  marginBottom: 6,
};
const subStyle = {
  fontSize: 13,
  color: "#6B7280",
  marginBottom: 32,
};
const cardStyle = {
  background: "#FFFFFF",
  borderRadius: 12,
  padding: "22px 24px",
  border: "1px solid #E3ECE7",
  boxShadow: "0 1px 4px rgba(47,79,62,.07)",
  marginBottom: 20,
};

export default function StatusBadgeStories() {
  return (
    <div style={pageStyle}>
      <h1 style={h1Style}>StatusBadge — Component Gallery</h1>
      <p style={subStyle}>All variants of the reusable technician status badge component.</p>

      {/* ── All Statuses (md, with icon) ── */}
      <div style={cardStyle}>
        <p style={titleStyle}>All Statuses — Default (md, icon visible)</p>
        <div style={rowStyle}>
          {ALL_STATUSES.map(s => <StatusBadge key={s} status={s} />)}
        </div>
      </div>

      {/* ── Without icons ── */}
      <div style={cardStyle}>
        <p style={titleStyle}>Without Icons</p>
        <div style={rowStyle}>
          {ALL_STATUSES.map(s => <StatusBadge key={s} status={s} showIcon={false} />)}
        </div>
      </div>

      {/* ── Size Variants ── */}
      <div style={cardStyle}>
        <p style={titleStyle}>Size Variants</p>
        {SIZES.map(size => (
          <div key={size} style={{ marginBottom: 14 }}>
            <p style={{ fontSize: 10, color: "#A0B5A8", marginBottom: 8, fontWeight: 600, textTransform: "uppercase" }}>{size}</p>
            <div style={rowStyle}>
              {ALL_STATUSES.map(s => <StatusBadge key={s} status={s} size={size} />)}
            </div>
          </div>
        ))}
      </div>

      {/* ── Individual ── */}
      <div style={cardStyle}>
        <p style={titleStyle}>Individual — Available</p>
        <div style={rowStyle}>
          <StatusBadge status="AVAILABLE" size="sm" />
          <StatusBadge status="AVAILABLE" size="md" />
          <StatusBadge status="AVAILABLE" size="lg" />
          <StatusBadge status="AVAILABLE" pulse />
        </div>
      </div>

      <div style={cardStyle}>
        <p style={titleStyle}>Individual — En Route (pulse by default)</p>
        <div style={rowStyle}>
          <StatusBadge status="EN_ROUTE" size="sm" />
          <StatusBadge status="EN_ROUTE" size="md" />
          <StatusBadge status="EN_ROUTE" size="lg" />
          <StatusBadge status="EN_ROUTE" pulse={false} />
        </div>
      </div>

      <div style={cardStyle}>
        <p style={titleStyle}>Individual — Offline (reduced opacity)</p>
        <div style={rowStyle}>
          <StatusBadge status="OFFLINE" size="sm" />
          <StatusBadge status="OFFLINE" size="md" />
          <StatusBadge status="OFFLINE" size="lg" />
          <StatusBadge status="OFFLINE" showIcon={false} />
        </div>
      </div>

      <div style={cardStyle}>
        <p style={titleStyle}>Individual — Suspended</p>
        <div style={rowStyle}>
          <StatusBadge status="SUSPENDED" size="sm" />
          <StatusBadge status="SUSPENDED" size="md" />
          <StatusBadge status="SUSPENDED" size="lg" />
        </div>
      </div>

      <div style={cardStyle}>
        <p style={titleStyle}>Individual — Busy / On Site / On Break</p>
        <div style={rowStyle}>
          <StatusBadge status="BUSY" />
          <StatusBadge status="ON_SITE" />
          <StatusBadge status="ON_BREAK" />
        </div>
      </div>

      {/* ── Pulse on non-default ── */}
      <div style={cardStyle}>
        <p style={titleStyle}>Pulse Animation — forced on any status</p>
        <div style={rowStyle}>
          {ALL_STATUSES.map(s => <StatusBadge key={s} status={s} pulse />)}
        </div>
      </div>

      {/* ── Custom className ── */}
      <div style={cardStyle}>
        <p style={titleStyle}>Custom className (bold border override)</p>
        <div style={rowStyle}>
          <StatusBadge status="AVAILABLE" className="custom-badge-override" />
          <StatusBadge status="BUSY" className="custom-badge-override" />
        </div>
        <p style={{ fontSize: 11, color: "#A0B5A8", marginTop: 10 }}>
          className prop safely merged with base classes.
        </p>
      </div>

      {/* ── Dark mode preview ── */}
      <div style={{ background: "#1F2937", borderRadius: 12, padding: "22px 24px", border: "1px solid #374151", marginBottom: 20 }}>
        <p style={{ ...titleStyle, color: "#9CA3AF" }}>Dark Mode Preview (simulated)</p>
        <p style={{ fontSize: 11, color: "#6B7280", marginBottom: 12 }}>
          Add <code style={{ background: "#374151", padding: "1px 6px", borderRadius: 4 }}>prefers-color-scheme: dark</code> or use OS dark mode to see auto dark styles.
        </p>
        <div style={rowStyle}>
          {ALL_STATUSES.map(s => <StatusBadge key={s} status={s} />)}
        </div>
      </div>
    </div>
  );
}
{ ALL_STATUSES.map(s => <StatusBadge key={s} status={s} />) }
        </div >
      </div >
    </div >
  );
}
