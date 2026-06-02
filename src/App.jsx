import { useState, useEffect } from "react";
import JobCreationForm from "./components/JobCreationForm.jsx";
import TechnicianList from "./components/TechnicianList.jsx";
import TechnicianListPage from "./components/TechnicianListPage.jsx";
import PlanningDashboard from "./components/PlanningDashboard.jsx";
import Dashboard from "./components/Dashboard.jsx";
import logo from "./assets/logo.png";
import "./App.css";
import { ChevronDown, ChevronRight, ChevronsLeft, ChevronsRight, LayoutDashboard, Briefcase, Users, Wrench, ClipboardList, Calendar } from "lucide-react";

// Import notification modules
import NotificationBell from "./components/notifications/NotificationBell";
import NotificationDrawer from "./components/notifications/NotificationDrawer";
import NotificationDetail from "./components/notifications/NotificationDetail";
import PermissionRequest from "./components/notifications/PermissionRequest";
import {
  fetchNotifications,
  markNotificationAsRead,
  connectNotificationSocket,
  disconnectNotificationSocket
} from "./services/notificationService";
import { getAllTechnicians } from "./services/technicianService";

function App() {
  const [activeTab, setActiveTab] = useState("dashboard");
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [isTechGroupOpen, setIsTechGroupOpen] = useState(true);

  // Notification States
  const [isNotificationDrawerOpen, setIsNotificationDrawerOpen] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);
  const [notifications, setNotifications] = useState([]);
  const [selectedNotification, setSelectedNotification] = useState(null);
  const [selectedJobDetail, setSelectedJobDetail] = useState(null);
  const [isBellAnimated, setIsBellAnimated] = useState(false);
  const [activeTechId, setActiveTechId] = useState("f953ad76-2e8c-4e8c-8be6-5743b185b1a2"); // fallback UUID
  const [techList, setTechList] = useState([]);

  // Fetch registered technicians to pick one as the active user
  useEffect(() => {
    const fetchTechs = async () => {
      try {
        const response = await getAllTechnicians();
        if (response.data && response.data.length > 0) {
          setTechList(response.data);
          // Pick the first technician's UUID
          const firstTech = response.data[0];
          const techId = firstTech.tech_id || firstTech.technician_id || firstTech.id;
          if (techId) {
            setActiveTechId(techId);
          }
        }
      } catch (err) {
        console.warn("Failed to fetch technicians list, using mock active technician ID.", err);
      }
    };
    fetchTechs();
  }, []);

  // Fetch notifications and initialize socket listeners for the active technician
  useEffect(() => {
    if (!activeTechId) return;

    // 1. Initial Load
    const loadInitialNotifications = async () => {
      const data = await fetchNotifications(activeTechId);
      setNotifications(data.notifications);
      setUnreadCount(data.unreadCount);
    };
    loadInitialNotifications();

    // 2. Connect Socket.io
    const socketHandlers = {
      onConnect: () => {
        console.log("Connected to notification server.");
      },
      onDisconnect: () => {
        console.log("Disconnected from notification server.");
      },
      onNewNotification: (notif) => {
        setNotifications((prev) => [notif, ...prev]);
        setUnreadCount((prev) => prev + 1);
        // Trigger bell bounce animation
        setIsBellAnimated(true);
        setTimeout(() => setIsBellAnimated(false), 1000);
      },
      onUnreadCount: (count) => {
        setUnreadCount(count);
      }
    };

    const socket = connectNotificationSocket(activeTechId, socketHandlers);

    return () => {
      disconnectNotificationSocket(socket);
    };
  }, [activeTechId]);

  // Handlers for NotificationDetail Actions
  const handleAcceptJob = async (jobId) => {
    console.log(`Accepting job ID: ${jobId}`);
    if (selectedNotification) {
      await handleMarkAsRead(selectedNotification.id);
    }
  };

  const handleRejectJob = async (jobId, reason) => {
    console.log(`Rejecting job ID: ${jobId} for reason: ${reason}`);
    if (selectedNotification) {
      await handleMarkAsRead(selectedNotification.id);
    }
  };

  const handleReassignJob = async (jobId) => {
    console.log(`Requesting reassignment for job ID: ${jobId}`);
    if (selectedNotification) {
      await handleMarkAsRead(selectedNotification.id);
    }
  };

  const handleNotificationClick = async (notif) => {
    setSelectedNotification(notif);
    setSelectedJobDetail(notif.job || null);
    setIsNotificationDrawerOpen(false); // Close drawer to display details

    // Mark as read immediately on click
    if (!notif.isRead) {
      await handleMarkAsRead(notif.id);
    }
  };

  const handleMarkAsRead = async (notifId) => {
    await markNotificationAsRead(notifId);
    setNotifications((prev) =>
      prev.map((n) => (n.id === notifId ? { ...n, isRead: true } : n))
    );
    setUnreadCount((prev) => Math.max(0, prev - 1));
  };

  const handleMarkAllAsRead = async () => {
    const unreadIds = notifications.filter((n) => !n.isRead).map((n) => n.id);
    await Promise.all(unreadIds.map((id) => markNotificationAsRead(id)));
    setNotifications((prev) => prev.map((n) => ({ ...n, isRead: true })));
    setUnreadCount(0);
  };

  // Helper function to trigger a mock notification (useful for testing & demo)
  const triggerMockNotification = () => {
    const randomId = `notif-${Date.now()}`;
    const newNotif = {
      id: randomId,
      type: Math.random() > 0.5 ? "JOB_ASSIGNED" : "SLA_WARNING",
      title: Math.random() > 0.5 ? "New Urgent Job" : "SLA Deadline Approaching",
      message: Math.random() > 0.5 ? "AC repair job assigned near Anna Nagar" : "AC Repair Service SLA deadline in 15 mins!",
      isRead: false,
      createdAt: new Date().toISOString(),
      jobId: 101,
      job: {
        id: 101,
        title: "AC Repair Service",
        description: "Customer reported cooling issue in split AC.",
        location: "Anna Nagar, Chennai",
        priority: "HIGH",
        customer_name: "Arun Kumar",
        customer_phone: "+91 9876543210",
        estimated_value: 2500,
        sla_deadline: new Date(Date.now() + 2 * 60 * 60 * 1000).toISOString(),
        distance_km: 6.8,
        required_skills: ["AC Repair", "Electrical", "Customer Support"]
      }
    };
    
    setNotifications((prev) => [newNotif, ...prev]);
    setUnreadCount((prev) => prev + 1);
    setIsBellAnimated(true);
    setTimeout(() => setIsBellAnimated(false), 1000);
  };

  return (
    <div className="app-shell">
      <aside className={`sidebar ${sidebarCollapsed ? "sidebar-collapsed" : ""}`}>
        <button
          className="sidebar-toggle"
          onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
        >
          {sidebarCollapsed ? <ChevronsRight size={18} /> : <ChevronsLeft size={18} />}
        </button>

        <div className="sidebar-content">
          <div className="sidebar-brand">
            <div className="brand-logo-wrap">
              <img src={logo} alt="FieldOps Logo" className="brand-logo-img" />
            </div>
          </div>

          <nav className="sidebar-nav">
            <span className="nav-group-label">MAIN MENU</span>

            <button
              className={`nav-item ${activeTab === "dashboard" ? "nav-active" : ""}`}
              onClick={() => setActiveTab("dashboard")}
            >
              <LayoutDashboard size={18} />
              <span className="nav-text">Dashboard</span>
            </button>

            <button
              className={`nav-item ${activeTab === "jobs" ? "nav-active" : ""}`}
              onClick={() => setActiveTab("jobs")}
            >
              <Briefcase size={18} />
              <span className="nav-text">Jobs</span>
            </button>

            <div className="nav-group">
              <button
                type="button"
                className="nav-group-header"
                onClick={() => setIsTechGroupOpen(!isTechGroupOpen)}
              >
                <span className="nav-group-icon-label-wrap">
                  <Users size={18} />
                  <span className="nav-text">Technicians</span>
                </span>
                <span className="chevron-icon nav-text">
                  {isTechGroupOpen ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                </span>
              </button>
              
              {isTechGroupOpen && (
                <div className="nav-group-items">
                  <button
                    className={`nav-item nav-sub-item ${activeTab === "techboard" ? "nav-active" : ""}`}
                    onClick={() => setActiveTab("techboard")}
                  >
                    <Wrench size={14} />
                    <span className="nav-text">Tech Dashboard</span>
                  </button>

                  <button
                    className={`nav-item nav-sub-item ${activeTab === "technicians" ? "nav-active" : ""}`}
                    onClick={() => setActiveTab("technicians")}
                  >
                    <ClipboardList size={14} />
                    <span className="nav-text">Technicians List</span>
                  </button>
                </div>
              )}
            </div>

            <button
              className={`nav-item ${activeTab === "planning" ? "nav-active" : ""}`}
              onClick={() => setActiveTab("planning")}
            >
              <Calendar size={18} />
              <span className="nav-text">Planning</span>
            </button>
          </nav>

          {/* Active tech switcher and demo controls */}
          <div className="sidebar-simulation-controls">
            {techList.length > 0 && (
              <div style={{ fontSize: "11px" }}>
                <label style={{ display: "block", marginBottom: "4px", color: "#6B7280", fontWeight: 600 }}>Simulated Tech:</label>
                <select
                  style={{ width: "100%", padding: "4px", borderRadius: "4px", border: "1px solid #E3ECE7", background: "#FFFFFF", fontSize: "11px" }}
                  value={activeTechId}
                  onChange={(e) => setActiveTechId(e.target.value)}
                >
                  {techList.map((t) => {
                    const val = t.tech_id || t.technician_id || t.id;
                    return (
                      <option key={val} value={val}>
                        {t.technician_name || t.name}
                      </option>
                    );
                  })}
                </select>
              </div>
            )}

            <div style={{ display: "flex", flexDirection: "column", gap: "6px", width: "100%" }}>
              <button
                type="button"
                className="permission-btn-secondary"
                style={{
                  width: "100%",
                  height: "28px",
                  fontSize: "11px",
                  padding: "0 10px",
                  background: "#FFFFFF",
                  border: "1px solid #E3ECE7",
                  borderRadius: "6px",
                  cursor: "pointer",
                  color: "#374151",
                  fontWeight: 600,
                  transition: "all 0.2s"
                }}
                onClick={triggerMockNotification}
                title="Test Notification UI"
              >
                Simulate Alert
              </button>
              <PermissionRequest compact={true} />
            </div>
          </div>

          <div className="sidebar-profile-mini">
            <div className="mini-avatar">R</div>

            <div className="mini-info">
              <span className="mini-name">Rajesh</span>
              <span className="mini-role">Admin</span>
            </div>

            <div style={{ marginLeft: "auto", display: "flex", alignItems: "center" }}>
              <NotificationBell
                unreadCount={unreadCount}
                onClick={() => setIsNotificationDrawerOpen(true)}
                isAnimated={isBellAnimated}
              />
            </div>
          </div>
        </div>
      </aside>

      <div className="main-area">

        <main className="page-wrap">
          {/* Permission Prompt integrated into header */}

          {/* Selected Notification Detail view */}
          {selectedNotification && (
            <NotificationDetail
              notification={selectedNotification}
              job={selectedJobDetail}
              onAccept={handleAcceptJob}
              onReject={handleRejectJob}
              onReassign={handleReassignJob}
              onClose={() => {
                setSelectedNotification(null);
                setSelectedJobDetail(null);
              }}
            />
          )}

          {/* Tab Pages */}
          {activeTab === "dashboard" && (
            <Dashboard
              onViewTab={(tab) => setActiveTab(tab)}
              unreadCount={unreadCount}
              isBellAnimated={isBellAnimated}
              onOpenBellDrawer={() => setIsNotificationDrawerOpen(true)}
            />
          )}
          {activeTab === "jobs" && <JobCreationForm />}
          {activeTab === "technicians" && <TechnicianList />}
          {activeTab === "techboard" && <TechnicianListPage />}
          {activeTab === "planning" && (
            <PlanningDashboard
              onViewAllJobs={() => setActiveTab("jobs")}
            />
          )}
        </main>
      </div>

      {/* Slide-out Drawer */}
      <NotificationDrawer
        isOpen={isNotificationDrawerOpen}
        onClose={() => setIsNotificationDrawerOpen(false)}
        notifications={notifications}
        onNotificationClick={handleNotificationClick}
        onMarkAllAsRead={handleMarkAllAsRead}
      />
    </div>
  );
}

export default App;
