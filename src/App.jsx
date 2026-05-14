import { useState } from "react";
import JobCreationForm from "./components/JobCreationForm";
import TechnicianList from "./components/TechnicianList";
import "./App.css";

function App() {
  const [activeTab, setActiveTab] = useState("jobs");

  return (
    <div className="app-shell">
      {/* Top Navigation Bar */}
      <nav className="top-nav">
        <div className="nav-brand">
          <span className="nav-logo">⚡</span>
          <span className="nav-name">FieldOps Commander</span>
        </div>

        <div className="nav-tabs">
          <button
            className={`nav-tab ${activeTab === "jobs" ? "active" : ""}`}
            onClick={() => setActiveTab("jobs")}
          >
            <span>📋</span> Jobs
          </button>
          <button
            className={`nav-tab ${activeTab === "technicians" ? "active" : ""}`}
            onClick={() => setActiveTab("technicians")}
          >
            <span>👷</span> Technicians
          </button>
        </div>

        <div className="nav-right">
          <span className="nav-status-dot"></span>
          <span className="nav-status-text">System Online</span>
        </div>
      </nav>

      {/* Page Content */}
      <main className="app-main">
        {activeTab === "jobs" ? <JobCreationForm /> : <TechnicianList />}
      </main>
    </div>
  );
}

export default App;