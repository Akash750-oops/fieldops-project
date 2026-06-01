import React, { useEffect, useState } from "react";
import { getDashboardStats, getJobs } from "../services/planningService.js";
import NotificationBell from "./notifications/NotificationBell";
import PermissionRequest from "./notifications/PermissionRequest";
import LoadingSpinner from "./LoadingSpinner.jsx";
import {
  Briefcase,
  User,
  Clock,
  CheckCircle,
  AlertCircle,
  Users,
  BarChart,
  Calendar,
  Coffee,
  MinusCircle,
  Snowflake,
  Zap,
  Droplet,
  Wrench,
  MoreHorizontal,
  TrendingUp,
  Check,
  ChevronDown
} from "lucide-react";
import "./Dashboard.css";

const getPriorityClass = (priority) => {
  const p = (priority || "").toUpperCase();
  if (p === "CRITICAL" || p === "P1") return "badge-critical";
  if (p === "HIGH" || p === "P2") return "badge-high";
  if (p === "MEDIUM" || p === "P3") return "badge-medium";
  if (p === "LOW" || p === "P4" || p === "P5") return "badge-low";
  return "badge-default";
};

const getStatusClass = (status) => {
  const s = (status || "").toLowerCase().trim().replace(" ", "-");
  if (s === "inprogress") return "status-badge status-in-progress";
  if (s === "canceled") return "status-badge status-cancelled";
  return `status-badge status-${s}`;
};

const formatStatus = (status) => {
  const s = (status || "active").toLowerCase().trim();
  if (s === "inprogress" || s === "in progress") return "In Progress";
  if (s === "canceled" || s === "cancelled") return "Cancelled";
  return s.charAt(0).toUpperCase() + s.slice(1);
};

const SegmentedProgressBar = ({ percentage, colorClass }) => {
  const activeCount = Math.round(percentage / 10);
  return (
    <div className="segmented-bar-track">
      {Array.from({ length: 10 }).map((_, idx) => {
        const isActive = idx < activeCount;
        return (
          <div
            key={idx}
            className={`segmented-bar-dot ${isActive ? "active" : "inactive"} ${colorClass}`}
          />
        );
      })}
    </div>
  );
};

const AnimatedGauge = ({ percentage, count, label, icon: Icon, color, textClass }) => {
  const [displayPct, setDisplayPct] = useState(0);

  useEffect(() => {
    let start = 0;
    const end = Math.round(percentage);
    if (start === end) {
      setDisplayPct(end);
      return;
    }

    const duration = 1000; // 1 second
    const startTime = performance.now();

    let animationFrameId;

    const animate = (currentTime) => {
      const elapsedTime = currentTime - startTime;
      const progress = Math.min(elapsedTime / duration, 1);
      
      // Easing function: easeOutQuad
      const easeProgress = progress * (2 - progress);
      
      const currentVal = Math.round(easeProgress * end);
      setDisplayPct(currentVal);

      if (progress < 1) {
        animationFrameId = requestAnimationFrame(animate);
      }
    };

    animationFrameId = requestAnimationFrame(animate);

    return () => {
      cancelAnimationFrame(animationFrameId);
    };
  }, [percentage]);

  return (
    <div className="gauge-item">
      <div className="gauge-circle-wrap">
        <svg width="100%" height="100%" viewBox="0 0 36 36">
          <path
            d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
            fill="none"
            stroke="#F3F4F6"
            strokeWidth="2.5"
          />
          <path
            className="gauge-circle-progress"
            strokeDasharray={`${displayPct}, 100`}
            d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
            fill="none"
            stroke={color}
            strokeWidth="2.5"
            strokeLinecap="round"
          />
          <text x="18" y="20.35" className="gauge-percent-text" textAnchor="middle" fontSize="6.5" fontWeight="700" fill={color}>
            {displayPct}%
          </text>
        </svg>
      </div>
      <span className={`gauge-sub-icon ${textClass}`}><Icon size={16} /></span>
      <span className="gauge-name">{label}</span>
      <strong className="gauge-count">{count}</strong>
    </div>
  );
};

function Dashboard({ onViewTab, unreadCount, isBellAnimated, onOpenBellDrawer }) {
  // Stats state from the backend — initially null so no stale data shows before load
  const [stats, setStats] = useState(null);
  const [recentJobs, setRecentJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [statsError, setStatsError] = useState(false);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        setStatsError(false);
        const [statsRes, jobsRes] = await Promise.all([
          getDashboardStats(),
          getJobs()
        ]);
        if (statsRes && statsRes.data) {
          setStats(statsRes.data);
        }
        if (jobsRes && jobsRes.data) {
          setRecentJobs(jobsRes.data.slice(0, 5));
        }
      } catch (err) {
        console.error("Dashboard error loading data:", err);
        setStatsError(true);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  // Wait until backend data is loaded
  if (loading || stats === null) {
    return <LoadingSpinner message="Assembling Operations Center Dashboard..." />;
  }

  if (statsError) {
    return (
      <div className="ops-dashboard">
        <div style={{ padding: "2rem", textAlign: "center", color: "#ef4444" }}>
          <strong>Failed to load dashboard data.</strong> Please ensure the backend server is running at <code>http://localhost:8000</code> and refresh the page.
        </div>
      </div>
    );
  }

  // Extract jobs counts — safe to access because stats is guaranteed non-null here
  const pendingCount = stats.jobs.pending;
  const activeCount = stats.jobs.active;
  const inProgressCount = stats.jobs.in_progress;
  const completedCount = stats.jobs.completed;
  const totalJobsCount = stats.jobs.total;

  // Percentage splits
  const activePct = totalJobsCount > 0 ? parseFloat(((activeCount / totalJobsCount) * 100).toFixed(1)) : 0;
  const inProgressPct = totalJobsCount > 0 ? parseFloat(((inProgressCount / totalJobsCount) * 100).toFixed(1)) : 0;
  const completedPct = totalJobsCount > 0 ? parseFloat(((completedCount / totalJobsCount) * 100).toFixed(1)) : 0;
  const pendingPct = totalJobsCount > 0 ? parseFloat(((pendingCount / totalJobsCount) * 100).toFixed(1)) : 0;

  // Technician availability counts
  const techAvailable = stats.technicians.available;
  const techBusy = stats.technicians.busy;
  const techBreak = stats.technicians.break;
  const techOffline = stats.technicians.offline;
  const totalTechs = techAvailable + techBusy + techBreak + techOffline;

  const availablePct = totalTechs > 0 ? parseFloat(((techAvailable / totalTechs) * 100).toFixed(1)) : 0;
  const busyPct = totalTechs > 0 ? parseFloat(((techBusy / totalTechs) * 100).toFixed(1)) : 0;
  const breakPct = totalTechs > 0 ? parseFloat(((techBreak / totalTechs) * 100).toFixed(1)) : 0;
  const offlinePct = totalTechs > 0 ? parseFloat(((techOffline / totalTechs) * 100).toFixed(1)) : 0;

  // Category counts
  const hvacCount = stats.categories.hvac;
  const electricalCount = stats.categories.electrical;
  const plumbingCount = stats.categories.plumbing;
  const mechanicalCount = stats.categories.mechanical;
  const otherCount = stats.categories.other;
  const totalCategories = hvacCount + electricalCount + plumbingCount + mechanicalCount + otherCount;

  const hvacPct = totalCategories > 0 ? parseFloat(((hvacCount / totalCategories) * 100).toFixed(1)) : 0;
  const electricalPct = totalCategories > 0 ? parseFloat(((electricalCount / totalCategories) * 100).toFixed(1)) : 0;
  const plumbingPct = totalCategories > 0 ? parseFloat(((plumbingCount / totalCategories) * 100).toFixed(1)) : 0;
  const mechanicalPct = totalCategories > 0 ? parseFloat(((mechanicalCount / totalCategories) * 100).toFixed(1)) : 0;
  const otherPct = totalCategories > 0 ? parseFloat(((otherCount / totalCategories) * 100).toFixed(1)) : 0;

  return (
    <div className="ops-dashboard">
      {/* ── Header ── */}
      <header className="dashboard-header-card">
        <div className="header-greeting-area">
          <h1 className="header-welcome-title">Welcome back! </h1>
          <p className="header-welcome-subtitle">Here's what's happening with your field operations today.</p>
        </div>

        <div className="header-controls-area">
          <div className="dropdown-calendar-wrap">
            <Calendar size={14} className="dropdown-calendar-icon" />
            <select className="dropdown-this-week" defaultValue="week">
              <option value="week">This Week</option>
              <option value="month">This Month</option>
            </select>
          </div>

          <div className="dashboard-search-bar">
            <span className="dashboard-search-icon">🔍</span>
            <input
              type="text"
              placeholder="Search jobs, technicians, locations..."
              className="dashboard-search-input"
            />
          </div>

          <NotificationBell
            unreadCount={unreadCount}
            onClick={onOpenBellDrawer}
            isAnimated={isBellAnimated}
          />

          <div className="dashboard-profile-pill">
            <div className="profile-avatar-c">R</div>
            <span className="profile-name-c">Rajesh</span>
            <ChevronDown size={14} className="profile-arrow-lucide" />
          </div>
        </div>
      </header>

      {/* ── Metrics Cards Row ── */}
      <div className="metrics-cards-grid">
        {/* Card 1: Total Jobs */}
        <div className="metric-slanted-card card-total" onClick={() => onViewTab("jobs")}>
          <svg className="metric-card-bg-svg" viewBox="0 0 100 100" preserveAspectRatio="none">
            <path
              d="M 1,1.5 L 93,1.5 L 98.5,50 L 93,98.5 L 1,98.5 Z"
              fill="#FFFFFF"
              stroke="#E3ECE7"
              strokeWidth="1.5"
              vectorEffect="non-scaling-stroke"
            />
            <path
              d="M 2.5,2 L 2.5,98"
              stroke="#10B981"
              strokeWidth="3.5"
              strokeLinecap="square"
              vectorEffect="non-scaling-stroke"
            />
          </svg>
          <div className="metric-card-content pad-card-first">
            <div className="metric-icon-wrap bg-total">
              <Briefcase size={20} color="#10B981" />
            </div>
            <div className="metric-details">
              <span className="metric-label">Total Jobs</span>
              <h2 className="metric-val">{totalJobsCount}</h2>
              <div className="metric-stat-row">
                <span className="stat-compare">{activeCount} active · {completedCount} done</span>
              </div>
            </div>
          </div>
        </div>

        {/* Card 2: Active Jobs */}
        <div className="metric-slanted-card card-active" onClick={() => onViewTab("planning")}>
          <svg className="metric-card-bg-svg" viewBox="0 0 100 100" preserveAspectRatio="none">
            <path
              d="M 7,1.5 L 93,1.5 L 98.5,50 L 93,98.5 L 7,98.5 L 13,50 Z"
              fill="#FFFFFF"
              stroke="#E3ECE7"
              strokeWidth="1.5"
              vectorEffect="non-scaling-stroke"
            />
            <path
              d="M 8,3 L 14,50 L 8,97"
              stroke="#3B82F6"
              strokeWidth="3.5"
              fill="none"
              strokeLinecap="round"
              strokeLinejoin="round"
              vectorEffect="non-scaling-stroke"
            />
          </svg>
          <div className="metric-card-content pad-card-middle">
            <div className="metric-icon-wrap bg-active">
              <User size={20} color="#3B82F6" />
            </div>
            <div className="metric-details">
              <span className="metric-label">Active Jobs</span>
              <h2 className="metric-val">{activeCount}</h2>
              <div className="metric-stat-row">
                <span className="stat-compare">{activePct}% of total</span>
              </div>
            </div>
          </div>
        </div>

        {/* Card 3: In Progress */}
        <div className="metric-slanted-card card-progress" onClick={() => onViewTab("planning")}>
          <svg className="metric-card-bg-svg" viewBox="0 0 100 100" preserveAspectRatio="none">
            <path
              d="M 7,1.5 L 93,1.5 L 98.5,50 L 93,98.5 L 7,98.5 L 13,50 Z"
              fill="#FFFFFF"
              stroke="#E3ECE7"
              strokeWidth="1.5"
              vectorEffect="non-scaling-stroke"
            />
            <path
              d="M 8,3 L 14,50 L 8,97"
              stroke="#F59E0B"
              strokeWidth="3.5"
              fill="none"
              strokeLinecap="round"
              strokeLinejoin="round"
              vectorEffect="non-scaling-stroke"
            />
          </svg>
          <div className="metric-card-content pad-card-middle">
            <div className="metric-icon-wrap bg-progress">
              <Clock size={20} color="#F59E0B" />
            </div>
            <div className="metric-details">
              <span className="metric-label">In Progress</span>
              <h2 className="metric-val">{inProgressCount}</h2>
              <div className="metric-stat-row">
                <span className="stat-compare">{inProgressPct}% of total</span>
              </div>
            </div>
          </div>
        </div>

        {/* Card 4: Completed */}
        <div className="metric-slanted-card card-completed" onClick={() => onViewTab("techboard")}>
          <svg className="metric-card-bg-svg" viewBox="0 0 100 100" preserveAspectRatio="none">
            <path
              d="M 7,1.5 L 93,1.5 L 98.5,50 L 93,98.5 L 7,98.5 L 13,50 Z"
              fill="#FFFFFF"
              stroke="#E3ECE7"
              strokeWidth="1.5"
              vectorEffect="non-scaling-stroke"
            />
            <path
              d="M 8,3 L 14,50 L 8,97"
              stroke="#8B5CF6"
              strokeWidth="3.5"
              fill="none"
              strokeLinecap="round"
              strokeLinejoin="round"
              vectorEffect="non-scaling-stroke"
            />
          </svg>
          <div className="metric-card-content pad-card-middle">
            <div className="metric-icon-wrap bg-completed">
              <CheckCircle size={20} color="#8B5CF6" />
            </div>
            <div className="metric-details">
              <span className="metric-label">Completed</span>
              <h2 className="metric-val">{completedCount}</h2>
              <div className="metric-stat-row">
                <span className="stat-compare">{completedPct}% of total</span>
              </div>
            </div>
          </div>
        </div>

        {/* Card 5: Pending */}
        <div className="metric-slanted-card card-pending" onClick={() => onViewTab("planning")}>
          <svg className="metric-card-bg-svg" viewBox="0 0 100 100" preserveAspectRatio="none">
            <path
              d="M 7,1.5 L 98.5,1.5 L 98.5,98.5 L 7,98.5 L 13,50 Z"
              fill="#FFFFFF"
              stroke="#E3ECE7"
              strokeWidth="1.5"
              vectorEffect="non-scaling-stroke"
            />
            <path
              d="M 8,3 L 14,50 L 8,97"
              stroke="#06B6D4"
              strokeWidth="3.5"
              fill="none"
              strokeLinecap="round"
              strokeLinejoin="round"
              vectorEffect="non-scaling-stroke"
            />
          </svg>
          <div className="metric-card-content pad-card-last">
            <div className="metric-icon-wrap bg-pending">
              <AlertCircle size={20} color="#06B6D4" />
            </div>
            <div className="metric-details">
              <span className="metric-label">Pending</span>
              <h2 className="metric-val">{pendingCount}</h2>
              <div className="metric-stat-row">
                <span className="stat-compare">{pendingPct}% of total</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* ── Main Content Cards ── */}
      <div className="content-cards-grid">
        {/* Card A: Jobs Overview */}
        <div className="ops-card card-jobs-overview">
          <div className="ops-card-header">
            <h3>JOBS OVERVIEW</h3>
            <div className="dropdown-calendar-wrap">
              <select className="dropdown-small" defaultValue="week">
                <option value="week">This Week</option>
              </select>
            </div>
          </div>
          <div className="ops-card-body body-jobs-overview">
            <div className="jobs-overview-labels">
              <div className="overview-row">
                <span className="indicator-badge badge-active"><User size={14} strokeWidth={2.5} /></span>
                <span className="overview-lbl">Active</span>
                <span className="overview-num">{activeCount}</span>
                <span className="overview-pct">({activePct}%)</span>
              </div>
              <div className="overview-row">
                <span className="indicator-badge badge-progress"><Wrench size={14} strokeWidth={2.5} /></span>
                <span className="overview-lbl">In Progress</span>
                <span className="overview-num">{inProgressCount}</span>
                <span className="overview-pct">({inProgressPct}%)</span>
              </div>
              <div className="overview-row">
                <span className="indicator-badge badge-completed"><Check size={14} strokeWidth={3} /></span>
                <span className="overview-lbl">Completed</span>
                <span className="overview-num">{completedCount}</span>
                <span className="overview-pct">({completedPct}%)</span>
              </div>
              <div className="overview-row">
                <span className="indicator-badge badge-pending"><Clock size={14} strokeWidth={2.5} /></span>
                <span className="overview-lbl">Pending</span>
                <span className="overview-num">{pendingCount}</span>
                <span className="overview-pct">({pendingPct}%)</span>
              </div>
            </div>

            {/* Hand-crafted 3D stacked layout layers diagram using Inline SVG */}
            <div className="jobs-overview-diagram">
              <svg viewBox="38 8 124 168" width="100%" height="100%">
                <defs>
                  {/* Green Layer (Top) Gradients */}
                  <linearGradient id="grad-green-top" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" stopColor="#4CD964" />
                    <stop offset="100%" stopColor="#28C745" />
                  </linearGradient>

                  {/* Orange Layer Gradients */}
                  <linearGradient id="grad-orange-top" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" stopColor="#FF9F0A" />
                    <stop offset="100%" stopColor="#FF8A00" />
                  </linearGradient>

                  {/* Blue Layer Gradients */}
                  <linearGradient id="grad-blue-top" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" stopColor="#0084FF" />
                    <stop offset="100%" stopColor="#0062FF" />
                  </linearGradient>

                  {/* Gray Layer (Bottom) Gradients */}
                  <linearGradient id="grad-gray-top" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" stopColor="#8E8E93" />
                    <stop offset="100%" stopColor="#7A7A7F" />
                  </linearGradient>
                </defs>

                {/* Layer 4: Pending (Gray/Bottom) */}
                <g transform="translate(0, 96)">
                  {/* Side extrusion */}
                  <path d="M 50 35 Q 40 40, 50 45 L 90 65 Q 100 70, 110 65 L 150 45 Q 160 40, 150 35 L 150 47 Q 160 52, 150 57 L 110 77 Q 100 82, 90 77 L 50 57 Q 40 52, 50 47 Z" fill="#5C5C60" />
                  {/* Top Face */}
                  <path d="M 90 15 Q 100 10, 110 15 L 150 35 Q 160 40, 150 45 L 110 65 Q 100 70, 90 65 L 50 45 Q 40 40, 50 35 Z" fill="url(#grad-gray-top)" />
                </g>

                {/* Layer 3: Completed (Blue) */}
                <g transform="translate(0, 64)">
                  {/* Side extrusion */}
                  <path d="M 50 35 Q 40 40, 50 45 L 90 65 Q 100 70, 110 65 L 150 45 Q 160 40, 150 35 L 150 47 Q 160 52, 150 57 L 110 77 Q 100 82, 90 77 L 50 57 Q 40 52, 50 47 Z" fill="#0051C7" />
                  {/* Top Face */}
                  <path d="M 90 15 Q 100 10, 110 15 L 150 35 Q 160 40, 150 45 L 110 65 Q 100 70, 90 65 L 50 45 Q 40 40, 50 35 Z" fill="url(#grad-blue-top)" />
                </g>

                {/* Layer 2: In Progress (Orange) */}
                <g transform="translate(0, 32)">
                  {/* Side extrusion */}
                  <path d="M 50 35 Q 40 40, 50 45 L 90 65 Q 100 70, 110 65 L 150 45 Q 160 40, 150 35 L 150 47 Q 160 52, 150 57 L 110 77 Q 100 82, 90 77 L 50 57 Q 40 52, 50 47 Z" fill="#D95300" />
                  {/* Top Face */}
                  <path d="M 90 15 Q 100 10, 110 15 L 150 35 Q 160 40, 150 45 L 110 65 Q 100 70, 90 65 L 50 45 Q 40 40, 50 35 Z" fill="url(#grad-orange-top)" />
                </g>

                {/* Layer 1: Active (Green/Top) */}
                <g transform="translate(0, 0)">
                  {/* Side extrusion */}
                  <path d="M 50 35 Q 40 40, 50 45 L 90 65 Q 100 70, 110 65 L 150 45 Q 160 40, 150 35 L 150 47 Q 160 52, 150 57 L 110 77 Q 100 82, 90 77 L 50 57 Q 40 52, 50 47 Z" fill="#21A139" />
                  {/* Top Face */}
                  <path d="M 90 15 Q 100 10, 110 15 L 150 35 Q 160 40, 150 45 L 110 65 Q 100 70, 90 65 L 50 45 Q 40 40, 50 35 Z" fill="url(#grad-green-top)" />
                </g>
              </svg>
            </div>
          </div>
          <div className="ops-card-footer footer-green">
            <span className="footer-stat">
              <TrendingUp size={16} className="footer-icon-green" /> 12% increase in active jobs vs last week
            </span>
            <button className="footer-link-btn" onClick={() => onViewTab("jobs")}>View Report →</button>
          </div>
        </div>

        {/* Card B: Technician Availability */}
        <div className="ops-card card-tech-availability">
          <div className="ops-card-header">
            <h3>TECHNICIAN AVAILABILITY</h3>
            <select className="dropdown-small" defaultValue="week">
              <option value="week">This Week</option>
            </select>
          </div>
          <div className="ops-card-body body-tech-availability">
            {/* Circle Gauges */}
            <div className="gauges-flex-row">
              <AnimatedGauge
                percentage={availablePct}
                count={techAvailable}
                label="Available"
                icon={User}
                color="#10B981"
                textClass="text-green"
              />
              <AnimatedGauge
                percentage={busyPct}
                count={techBusy}
                label="On Job / Busy"
                icon={Users}
                color="#F97316"
                textClass="text-orange"
              />
              <AnimatedGauge
                percentage={breakPct}
                count={techBreak}
                label="Break"
                icon={Coffee}
                color="#8B5CF6"
                textClass="text-purple"
              />
              <AnimatedGauge
                percentage={offlinePct}
                count={techOffline}
                label="Offline"
                icon={MinusCircle}
                color="#64748B"
                textClass="text-gray"
              />
            </div>
          </div>
          <div className="ops-card-footer footer-blue">
            <div className="footer-stat-container">
              <Users size={18} className="footer-icon-blue" />
              <div className="footer-stat-text-wrap">
                <span className="footer-stat-primary">{techAvailable} technicians available</span>
                <span className="footer-stat-secondary">ready to assign</span>
              </div>
            </div>
            <button className="footer-link-btn" onClick={() => onViewTab("technicians")}>
              View Report →
            </button>
          </div>
        </div>

        {/* Card C: Service Category Split */}
        <div className="ops-card card-service-split">
          <div className="ops-card-header">
            <h3>SERVICE CATEGORY SPLIT</h3>
            <select className="dropdown-small" defaultValue="week">
              <option value="week">This Week</option>
            </select>
          </div>
          <div className="ops-card-body body-service-split">
            <div className="category-bars-list">
              {/* Category 1: HVAC */}
              <div className="category-bar-row">
                <span className="category-tag-badge hvac-tag"><Snowflake size={11} /></span>
                <span className="category-label">HVAC</span>
                <SegmentedProgressBar percentage={hvacPct} colorClass="fill-hvac" />
                <strong className="category-value">{hvacCount} ({hvacPct}%)</strong>
              </div>

              {/* Category 2: Electrical */}
              <div className="category-bar-row">
                <span className="category-tag-badge elec-tag"><Zap size={11} /></span>
                <span className="category-label">Electrical</span>
                <SegmentedProgressBar percentage={electricalPct} colorClass="fill-elec" />
                <strong className="category-value">{electricalCount} ({electricalPct}%)</strong>
              </div>

              {/* Category 3: Plumbing */}
              <div className="category-bar-row">
                <span className="category-tag-badge plumb-tag"><Droplet size={11} /></span>
                <span className="category-label">Plumbing</span>
                <SegmentedProgressBar percentage={plumbingPct} colorClass="fill-plumb" />
                <strong className="category-value">{plumbingCount} ({plumbingPct}%)</strong>
              </div>

              {/* Category 4: Mechanical */}
              <div className="category-bar-row">
                <span className="category-tag-badge mech-tag"><Wrench size={11} /></span>
                <span className="category-label">Mechanical</span>
                <SegmentedProgressBar percentage={mechanicalPct} colorClass="fill-mech" />
                <strong className="category-value">{mechanicalCount} ({mechanicalPct}%)</strong>
              </div>

              {/* Category 5: Other */}
              <div className="category-bar-row">
                <span className="category-tag-badge other-tag"><MoreHorizontal size={11} /></span>
                <span className="category-label">Other</span>
                <SegmentedProgressBar percentage={otherPct} colorClass="fill-other" />
                <strong className="category-value">{otherCount} ({otherPct}%)</strong>
              </div>
            </div>
          </div>
          <div className="ops-card-footer footer-purple">
            <div className="footer-stat-container">
              <BarChart size={18} className="footer-icon-purple" />
              <div className="footer-stat-text-wrap">
                <span className="footer-stat-primary-purple">
                  {/* Dynamically show highest category */}
                  {(() => {
                    const cats = [
                      { name: "HVAC", count: hvacCount },
                      { name: "Electrical", count: electricalCount },
                      { name: "Plumbing", count: plumbingCount },
                      { name: "Mechanical", count: mechanicalCount },
                      { name: "Other", count: otherCount },
                    ];
                    const top = cats.reduce((a, b) => a.count >= b.count ? a : b);
                    return `${top.name} is highest`;
                  })()}
                </span>
                <span className="footer-stat-secondary">
                  {(() => {
                    const cats = [
                      { name: "HVAC", count: hvacCount, pct: hvacPct },
                      { name: "Electrical", count: electricalCount, pct: electricalPct },
                      { name: "Plumbing", count: plumbingCount, pct: plumbingPct },
                      { name: "Mechanical", count: mechanicalCount, pct: mechanicalPct },
                      { name: "Other", count: otherCount, pct: otherPct },
                    ];
                    const top = cats.reduce((a, b) => a.count >= b.count ? a : b);
                    return `${top.pct}% of total jobs`;
                  })()}
                </span>
              </div>
            </div>
            <button className="footer-link-btn" onClick={() => onViewTab("jobs")}>
              View Report →
            </button>
          </div>
        </div>
      </div>

      {/* ── Recent Jobs Card ── */}
      <div className="card-recent-jobs">
        <div className="ops-card-header">
          <h3>RECENT JOBS</h3>
          <button className="dropdown-small" onClick={() => onViewTab("jobs")} style={{ padding: "5px 12px", appearance: "none", backgroundImage: "none" }}>
            View All
          </button>
        </div>
        <div className="recent-jobs-table-container">
          <table className="recent-jobs-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Customer / Job Name</th>
                <th>Location</th>
                <th>Service Type</th>
                <th>Priority</th>
                <th>Status</th>
                <th>Preferred Date</th>
              </tr>
            </thead>
            <tbody>
              {recentJobs.length === 0 ? (
                <tr>
                  <td colSpan="7" style={{ textAlign: "center", color: "#6B7280", padding: "20px" }}>
                    No recent jobs found.
                  </td>
                </tr>
              ) : (
                recentJobs.map((job) => (
                  <tr key={job.id}>
                    <td className="job-id-pill">#{job.id}</td>
                    <td style={{ fontWeight: "700", color: "#2F4F3E" }}>
                      <div>{job.customer_name}</div>
                      {job.issue_description && (
                        <div style={{ fontSize: "11px", color: "#6B7280", fontWeight: "400", marginTop: "2px" }}>
                          {job.issue_description}
                        </div>
                      )}
                    </td>
                    <td>{job.location}</td>
                    <td>{(job.service_type || "").replace(/_/g, " ")}</td>
                    <td>
                      <span className={`priority-badge ${getPriorityClass(job.priority)}`}>
                        {(job.priority || "UNKNOWN").toUpperCase()}
                      </span>
                    </td>
                    <td>
                      <span className={getStatusClass(job.status)}>
                        {formatStatus(job.status)}
                      </span>
                    </td>
                    <td>{job.preferred_service_date || "—"}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
        <div className="ops-card-footer footer-green">
          <span className="footer-stat">
            <TrendingUp size={16} className="footer-icon-green" /> Total pending: {stats.jobs.pending} · active: {stats.jobs.active}
          </span>
          <button className="footer-link-btn" onClick={() => onViewTab("jobs")}>
            Manage Jobs →
          </button>
        </div>
      </div>
    </div>
  );
}

export default Dashboard;
