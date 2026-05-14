import { useState } from "react";
import JobCreationForm from "./components/JobCreationForm";
import TechnicianList from "./components/TechnicianList";
import "./App.css";

function App() {
  const [activeTab, setActiveTab] = useState("jobs");

  return (
    <div className="app-shell">
      {/* ── Left Sidebar ── */}
      <aside className="sidebar">
        {/* Logo */}
        <div className="sidebar-brand">
          <span className="brand-icon">⚡</span>
          <span className="brand-name">FieldOps</span>
        </div>

        {/* Nav Menu */}
        <nav className="sidebar-nav">
          <span className="nav-group-label">MAIN MENU</span>
          <button
            className={`nav-item ${activeTab === "jobs" ? "nav-active" : ""}`}
            onClick={() => setActiveTab("jobs")}
          >
            <span className="nav-icon">📋</span>Jobs
          </button>
          <button
            className={`nav-item ${activeTab === "technicians" ? "nav-active" : ""}`}
            onClick={() => setActiveTab("technicians")}
          >
            <span className="nav-icon">👷</span>Technicians
          </button>
        </nav>

        {/* Help */}
        <div className="sidebar-help">
          <span className="help-icon-sm">💬</span>
          <div>
            <p className="help-title">Need Help?</p>
            <a href="mailto:support@fieldops.com" className="help-link">Contact support</a>
          </div>
        </div>

        {/* Admin Profile – compact at bottom */}
        <div className="sidebar-profile-mini">
          <div className="mini-avatar">R</div>
          <div className="mini-info">
            <span className="mini-name">Rajesh</span>
            <span className="mini-role">Admin</span>
          </div>
        </div>
      </aside>

      {/* ── Main Area ── */}
      <div className="main-area">
        {/* Top Header */}
        <header className="top-header">
          <span className="header-title">
            {activeTab === "jobs" ? "Job Management" : "Technician Management"}
          </span>
          <div className="header-actions">
            <div className="status-pill">
              <span className="status-dot" />
              System Online
            </div>
          </div>
        </header>

        {/* Page */}
        <main className="page-wrap">
          {activeTab === "jobs" ? <JobCreationForm /> : <TechnicianList />}
        </main>
      </div>
    </div>
  );
}

export default App;