import { useState } from "react";
import JobCreationForm from "./components/JobCreationForm.jsx";
import TechnicianList from "./components/TechnicianList.jsx";
import PlanningDashboard from "./components/PlanningDashboard.jsx";
import logo from "./assets/logo.png";
import "./App.css";

function App() {
  const [activeTab, setActiveTab] = useState("jobs");

  return (
    <div className="app-shell">
      {/* ── Left Sidebar ── */}
      <aside className="sidebar">
        {/* Logo */}
        <div className="sidebar-brand">
          <div className="brand-logo-wrap">
            <img src={logo} alt="FieldOps Logo" className="brand-logo-img" />

          </div>

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
          <button
            className={`nav-item ${activeTab === "planning" ? "nav-active" : ""}`}
            onClick={() => setActiveTab("planning")}
          >
            <span className="nav-icon">📅</span>Planning
          </button>
        </nav>

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
            {activeTab === "jobs" ? "Job Management" :
              activeTab === "technicians" ? "Technician Management" :
                "Planning Dashboard"}
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
          {activeTab === "jobs" && <JobCreationForm />}
          {activeTab === "technicians" && <TechnicianList />}
          {activeTab === "planning" && <PlanningDashboard />}
        </main>
      </div>
    </div>
  );
}

export default App;