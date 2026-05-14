import { useState } from "react";
import JobCreationForm from "./components/JobCreationForm";
import TechnicianList from "./components/TechnicianList";
import "./App.css";

function App() {
  const [activeTab, setActiveTab] = useState("jobs");

  return (
    <div className="app-shell">
      {/* ── Left Sidebar ── */}
      <aside className="sidebar-nav">
        {/* Logo */}
        <div className="sidebar-brand">
          <span className="sidebar-logo">⚡</span>
          <span className="sidebar-title">FieldOps Commander</span>
        </div>

        {/* Profile Card */}
        <div className="sidebar-profile">
          <div className="profile-avatar">R</div>
          <div className="profile-info">
            <span className="profile-name">Rajesh</span>
            <span className="profile-role">Admin / Field Manager</span>
          </div>
        </div>

        {/* Navigation Menu */}
        <nav className="sidebar-menu">
          <p className="menu-section-label">Main Menu</p>
          <button
            className={`menu-item ${activeTab === "jobs" ? "active" : ""}`}
            onClick={() => setActiveTab("jobs")}
          >
            <span className="menu-icon">📋</span>
            <span>Jobs</span>
          </button>
          <button
            className={`menu-item ${activeTab === "technicians" ? "active" : ""}`}
            onClick={() => setActiveTab("technicians")}
          >
            <span className="menu-icon">👷</span>
            <span>Technicians</span>
          </button>
        </nav>

        {/* Help Footer */}
        <div className="sidebar-footer">
          <div className="help-card">
            <span className="help-icon">💬</span>
            <div>
              <p className="help-title">Need Help?</p>
              <a href="mailto:support@fieldops.com" className="help-link">Contact support</a>
            </div>
          </div>
        </div>
      </aside>

      {/* ── Right Panel ── */}
      <div className="main-panel">
        {/* Top Header */}
        <header className="top-header">
          <div className="header-left">
            <span className="header-page-label">
              {activeTab === "jobs" ? "📋 Job Management" : "👷 Technician Management"}
            </span>
          </div>
          <div className="header-right">
            <div className="status-indicator">
              <span className="status-dot"></span>
              <span className="status-text">System Online</span>
            </div>
          </div>
        </header>

        {/* Page Content */}
        <main className="page-content">
          {activeTab === "jobs" ? <JobCreationForm /> : <TechnicianList />}
        </main>
      </div>
    </div>
  );
}

export default App;