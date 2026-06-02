import React, { useState, useEffect, useCallback, useRef, useMemo } from "react";
import { getAllTechnicians, updateTechnicianAvailability, createTechnician, updateTechnician, deleteTechnician } from "../services/technicianService";
import usePageVisibility from "../hooks/usePageVisibility";
import useInterval from "../hooks/useInterval";
import StatusBadge from "./common/StatusBadge";
import LoadingSpinner from "./LoadingSpinner.jsx";
import { Eye, Pencil, Trash2 } from "lucide-react";
import "./TechnicianListPage.css";

const PAGE_SIZE = 8;
const REFRESH_MS = 30_000;
const STALE_MS   = 60_000;
const SKILLS = ["HVAC Repair","Electrical","Plumbing","Network Support","General Maintenance"];

const SORT_KEYS = { name: "name", status: "status", jobs: "jobs", ping: "ping" };

/* ── Helpers ─────────────────────────────────────────────────────────────── */
function normalizeStatus(s) {
  const l = (s||"").toLowerCase();
  if (l==="available") return "Available";
  if (l==="busy")      return "Busy";
  if (l==="assigned")  return "Assigned";
  if (l==="offline")   return "Offline";
  return s||"Unknown";
}
function statusCls(s){ const n=normalizeStatus(s).toLowerCase(); return n==="available"?"available":n==="busy"?"busy":n==="assigned"?"assigned":"offline"; }
function getInitials(n=""){ return n.trim().split(/\s+/).map(w=>w[0]?.toUpperCase()||"").slice(0,2).join(""); }
function formatAgo(ts){
  if(!ts) return "—";
  try{
    const diff=Math.round((Date.now()-new Date(ts))/60000);
    if(diff<1) return "just now";
    if(diff<60) return `${diff}m ago`;
    const h=Math.round(diff/60);
    if(h<24) return `${h}h ago`;
    return new Date(ts).toLocaleDateString();
  }catch{ return String(ts); }
}
function normTech(t){
  return {
    id:          t.technician_id??t.id??Math.random(),
    name:        t.technician_name??t.name??"Unknown",
    status:      t.technician_status??t.status??"Unknown",
    skill:       t.technician_skill??t.skills??t.skill??"—",
    location:    t.technician_location??t.zone??t.location??"—",
    currentJobs: t.current_jobs??t.active_jobs??0,
    maxJobs:     t.max_jobs??5,
    lastPing:    t.last_ping??t.updated_at??null,
  };
}
function wPct(cur,max){ return max>0?Math.min(Math.round((cur/max)*100),100):0; }
function wColor(p){ return p>=90?"high":p>=60?"mid":"low"; }

/* ── Sub-components ──────────────────────────────────────────────────────── */

function SkeletonRows({n=8}){
  return Array.from({length:n},(_,i)=>(
    <tr key={i} className="tld-skeleton-row">
      <td><div className="tld-name-cell"><div className="tld-skeleton-avatar"/><div className="tld-skeleton-name-wrap"><div className="tld-skeleton-bar" style={{width:120}}/><div className="tld-skeleton-bar" style={{width:80,marginTop:4,height:10}}/></div></div></td>
      <td><div className="tld-skeleton-bar" style={{width:70}}/></td>
      <td><div className="tld-skeleton-bar" style={{width:90}}/></td>
      <td><div className="tld-skeleton-bar" style={{width:60}}/></td>
      <td><div className="tld-skeleton-bar" style={{width:100}}/></td>
    </tr>
  ));
}

function SortIcon({col,sortKey,sortDir}){
  if(sortKey!==col) return <span className="sort-icon">⇅</span>;
  return <span className="sort-icon active">{sortDir==="asc"?"↑":"↓"}</span>;
}

function MetricsPanel({metrics,lastSuccessAt}){
  const rate = metrics.successCount+metrics.failureCount===0
    ? "—"
    : `${Math.round((metrics.successCount/(metrics.successCount+metrics.failureCount))*100)}%`;
  return(
    <div className="tld-metrics-panel">
      <p className="tld-metrics-title">Refresh Metrics</p>
      <div className="tld-metrics-row"><span className="tld-metrics-label">Success</span><span className={`tld-metrics-value good`}>{metrics.successCount}</span></div>
      <div className="tld-metrics-row"><span className="tld-metrics-label">Failures</span><span className={`tld-metrics-value ${metrics.failureCount>0?"error":"good"}`}>{metrics.failureCount}</span></div>
      <div className="tld-metrics-row"><span className="tld-metrics-label">Success rate</span><span className="tld-metrics-value">{rate}</span></div>
      <div className="tld-metrics-row"><span className="tld-metrics-label">Last latency</span><span className="tld-metrics-value">{metrics.lastLatencyMs!=null?`${metrics.lastLatencyMs}ms`:"—"}</span></div>
      <div className="tld-metrics-row"><span className="tld-metrics-label">Last success</span><span className="tld-metrics-value">{formatAgo(lastSuccessAt)}</span></div>
    </div>
  );
}

/* ── Main Component ──────────────────────────────────────────────────────── */
export default function TechnicianListPage(){
  /* ── State: data ── */
  const [technicians, setTechnicians] = useState([]);
  const [loading,     setLoading]     = useState(true);    // initial load only
  const [fetching,    setFetching]    = useState(false);   // background refresh
  const [initError,   setInitError]   = useState("");      // initial load failure
  const [bgError,     setBgError]     = useState("");      // background refresh failure

  /* ── State: UI (never reset on refresh) ── */
  const [search,        setSearch]        = useState("");
  const [debSearch,     setDebSearch]     = useState("");
  const [statusFilter,  setStatusFilter]  = useState("ALL");
  const [skillFilter,   setSkillFilter]   = useState("ALL");
  const [zoneFilter,    setZoneFilter]    = useState("ALL");
  const [sortKey,       setSortKey]       = useState("name");
  const [sortDir,       setSortDir]       = useState("asc");
  const [page,          setPage]          = useState(1);

  /* ── State: sidebar ── */
  const [selected,  setSelected]  = useState(null);
  const [newStatus, setNewStatus] = useState("");
  const [saving,    setSaving]    = useState(false);

  // Form states for Add/Edit
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [editingTechId, setEditingTechId] = useState(null);
  const [formLoading, setFormLoading] = useState(false);
  const [formErrors, setFormErrors] = useState({});
  const [techFormData, setTechFormData] = useState({
    technician_name: "",
    technician_skill: "",
    technician_location: "",
    technician_status: "Available",
  });

  const openAddForm = () => {
    setIsEditing(false);
    setEditingTechId(null);
    setTechFormData({
      technician_name: "",
      technician_skill: "",
      technician_location: "",
      technician_status: "Available",
    });
    setFormErrors({});
    setIsFormOpen(true);
  };

  const openEditForm = (tech) => {
    setIsEditing(true);
    setEditingTechId(tech.id);
    setTechFormData({
      technician_name: tech.name,
      technician_skill: tech.skill,
      technician_location: tech.location,
      technician_status: normalizeStatus(tech.status),
    });
    setFormErrors({});
    setIsFormOpen(true);
  };

  const closeForm = () => {
    setIsFormOpen(false);
  };

  const handleFormChange = (e) => {
    const { name, value } = e.target;
    setTechFormData(prev => ({ ...prev, [name]: value }));
    setFormErrors(prev => ({ ...prev, [name]: "" }));
  };

  const validateForm = () => {
    const errors = {};
    if (!techFormData.technician_name.trim()) errors.technician_name = "Name is required";
    if (!techFormData.technician_skill.trim()) errors.technician_skill = "Skill is required";
    if (!techFormData.technician_location.trim()) errors.technician_location = "Location is required";
    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleFormSubmit = async (e) => {
    e.preventDefault();
    if (!validateForm()) return;
    setFormLoading(true);
    try {
      if (isEditing) {
        await updateTechnician(editingTechId, techFormData);
        showToast("Technician updated successfully");
      } else {
        await createTechnician(techFormData);
        showToast("Technician added successfully");
      }
      setIsFormOpen(false);
      fetchData(technicians.length > 0);
    } catch (err) {
      const msg = err.response?.data?.error || err.response?.data?.detail || "Failed to save technician.";
      showToast(msg, "error");
    } finally {
      setFormLoading(false);
    }
  };

  /* ── State: toast ── */
  const [toast,     setToast]     = useState({msg:"",type:""});
  const toastTimer                = useRef(null);

  /* ── State: refresh meta ── */
  const [lastSuccessAt,  setLastSuccessAt]  = useState(null);
  const [countdown,      setCountdown]      = useState(100); // 0→100%
  const [showMetrics,    setShowMetrics]    = useState(false);
  const [metrics, setMetrics] = useState({successCount:0,failureCount:0,lastLatencyMs:null});

  const isTabActive = usePageVisibility();
  const metricsRef  = useRef(null);

  /* ── Stale detection ── */
  const isStale = lastSuccessAt && (Date.now()-lastSuccessAt)>STALE_MS;

  /* ── Debounce search ── */
  useEffect(()=>{ const t=setTimeout(()=>setDebSearch(search),300); return()=>clearTimeout(t); },[search]);
  useEffect(()=>setPage(1),[debSearch,statusFilter,skillFilter,zoneFilter]);

  /* ── Fetch function ── */
  const fetchData = useCallback(async(silent=false)=>{
    if(silent){ setFetching(true); setBgError(""); }
    else { setLoading(true); setInitError(""); }
    const t0=Date.now();
    try{
      const res=await getAllTechnicians();
      setTechnicians((res.data||[]).map(normTech));
      const latency=Date.now()-t0;
      setLastSuccessAt(Date.now());
      setMetrics(m=>({...m,successCount:m.successCount+1,lastLatencyMs:latency}));
      setBgError("");
    }catch(err){
      const msg=err.response?.data?.error||err.response?.data?.detail||"Unable to reach backend.";
      if(silent){ setBgError(msg); setMetrics(m=>({...m,failureCount:m.failureCount+1})); }
      else { setInitError(msg); }
    }finally{
      if(silent) setFetching(false);
      else setLoading(false);
    }
  },[]);

  /* Initial load */
  useEffect(()=>{ fetchData(false); },[fetchData]);

  /* ── Countdown tick (updates every second) ── */
  useInterval(()=>{
    if(!lastSuccessAt||!isTabActive) return;
    const elapsed=Date.now()-lastSuccessAt;
    const pct=Math.max(0,Math.min(100,Math.round((elapsed/REFRESH_MS)*100)));
    setCountdown(pct);
  }, 1000);

  /* ── Auto-refresh (pauses when tab hidden) ── */
  useInterval(()=>{ fetchData(true); setCountdown(0); }, isTabActive ? REFRESH_MS : null);

  /* ── Close metrics panel on outside click ── */
  useEffect(()=>{
    if(!showMetrics) return;
    const handler=(e)=>{ if(metricsRef.current&&!metricsRef.current.contains(e.target)) setShowMetrics(false); };
    document.addEventListener("mousedown",handler);
    return()=>document.removeEventListener("mousedown",handler);
  },[showMetrics]);

  /* ── Derived lists ── */
  const uniqueZones = useMemo(() => {
    const seen = new Set();
    const result = [];
    technicians.forEach(t => {
      if (t.location) {
        const val = t.location.trim();
        const norm = val.toUpperCase().replace(/_/g, " ").replace(/\s+/g, " ");
        if (!seen.has(norm)) {
          seen.add(norm);
          result.push(val);
        }
      }
    });
    return result.sort();
  }, [technicians]);

  const filtered = useMemo(()=>{
    let list=technicians;
    if(debSearch){ const s=debSearch.toLowerCase(); list=list.filter(t=>t.name.toLowerCase().includes(s)||t.skill.toLowerCase().includes(s)||t.location.toLowerCase().includes(s)); }
    if(statusFilter!=="ALL") list=list.filter(t=>normalizeStatus(t.status)===statusFilter);
    if(skillFilter!=="ALL")  list=list.filter(t=>t.skill===skillFilter);
    if(zoneFilter!=="ALL")   list=list.filter(t=>(t.location || "").trim().toUpperCase().replace(/_/g, " ").replace(/\s+/g, " ")===zoneFilter.trim().toUpperCase().replace(/_/g, " ").replace(/\s+/g, " "));
    return [...list].sort((a,b)=>{
      let av,bv;
      if(sortKey==="name"){av=a.name.toLowerCase();bv=b.name.toLowerCase();}
      else if(sortKey==="status"){av=normalizeStatus(a.status);bv=normalizeStatus(b.status);}
      else if(sortKey==="jobs"){av=a.currentJobs;bv=b.currentJobs;}
      else if(sortKey==="ping"){av=a.lastPing||0;bv=b.lastPing||0;}
      else{av=a.id;bv=b.id;}
      if(av<bv) return sortDir==="asc"?-1:1;
      if(av>bv) return sortDir==="asc"?1:-1;
      return 0;
    });
  },[technicians,debSearch,statusFilter,skillFilter,zoneFilter,sortKey,sortDir]);

  // Clamp page to totalPages if length changes and page is out of bounds
  useEffect(() => {
    const total = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
    if (page > total) {
      setPage(total);
    }
  }, [filtered.length, page]);

  const totalPages = Math.max(1,Math.ceil(filtered.length/PAGE_SIZE));
  const safePage   = Math.min(page,totalPages);
  const pageSlice  = filtered.slice((safePage-1)*PAGE_SIZE, safePage*PAGE_SIZE);



  /* ── Handlers ── */
  function handleSort(key){ if(sortKey===key) setSortDir(d=>d==="asc"?"desc":"asc"); else{setSortKey(key);setSortDir("asc");} setPage(1); }
  function showToast(msg,type="success"){ clearTimeout(toastTimer.current); setToast({msg,type}); toastTimer.current=setTimeout(()=>setToast({msg:"",type:""}),3500); }
  function openSidebar(tech){ 
    setSelected(tech); 
    setNewStatus(normalizeStatus(tech.status)); 
    // Simulate navigation to route as requested
    window.location.hash = `#/technicians/${tech.id}`;
  }
  function closeSidebar(){ 
    setSelected(null); 
    // Clear simulated route on close
    if(window.location.hash.startsWith('#/technicians/')) {
      window.location.hash = '';
    }
  }
  function clearFilters(){ setSearch(""); setStatusFilter("ALL"); setSkillFilter("ALL"); setZoneFilter("ALL"); setPage(1); }
  const hasFilters=search||statusFilter!=="ALL"||skillFilter!=="ALL"||zoneFilter!=="ALL";

  async function handleSaveStatus(){
    if(!selected) return;
    setSaving(true);
    try{
      await updateTechnicianAvailability(selected.id,newStatus);
      setTechnicians(prev=>prev.map(t=>t.id===selected.id?{...t,status:newStatus}:t));
      showToast(`${selected.name} set to ${newStatus}`);
      closeSidebar();
    }catch(err){
      showToast(err.response?.data?.error||err.response?.data?.detail||"Failed to update status","error");
    }finally{ setSaving(false); }
  }

  function handleManualRefresh(){ fetchData(technicians.length>0); setCountdown(0); }

  async function handleDeleteTech(tech) {
    if (!window.confirm(`Are you sure you want to delete "${tech.name}"?`)) return;
    try {
      await deleteTechnician(tech.id);
      showToast(`${tech.name} deleted successfully`);
      fetchData(technicians.length > 0);
    } catch (err) {
      const msg = err.response?.data?.error || err.response?.data?.detail || "Failed to delete technician.";
      showToast(msg, "error");
    }
  }

  function handleEditTech(tech) {
    openEditForm(tech);
  }

  function getPageNums(){
    const nums=[]; const delta=2;
    for(let i=Math.max(1,safePage-delta);i<=Math.min(totalPages,safePage+delta);i++) nums.push(i);
    return nums;
  }

  /* ── Render ── */
  return(
    <div className="tld-page">

      {/* Toast */}
      {toast.msg&&<div className={`tld-toast ${toast.type}`}>{toast.msg}</div>}


      {/* Countdown progress rail */}
      {!loading&&technicians.length>0&&(
        <div className="tld-countdown-rail">
          <div className={`tld-countdown-fill${fetching?" fetching":""}`} style={{width:`${countdown}%`}}/>
        </div>
      )}

      {/* Background error banner */}
      {bgError&&(
        <div className="tld-bg-error-banner">
          <strong>Refresh failed.</strong> Showing last available data. — {bgError}
          <button className="tld-bg-error-retry" onClick={handleManualRefresh}>Retry</button>
        </div>
      )}



      {/* Table Card */}
      <div className="tld-table-card">
        <div className="tld-card-header">
          <div>
            <span className="tld-section-badge">Dashboard</span>
            <p className="tld-card-subtitle">Monitor registered technicians, real-time workload, and latency metrics</p>
          </div>
          <div className="tld-header-right">
            {/* Refresh indicator */}
            <div className="tld-refresh-bar">
              {fetching
                ? <><div className="tld-refresh-spinner"/><span className="tld-refresh-fetching">Refreshing…</span></>
                : !isTabActive
                  ? <span className="tld-refresh-paused">Paused</span>
                  : <span className="tld-refresh-last">Updated {formatAgo(lastSuccessAt)}</span>
              }
              {isStale&&!fetching&&<span className="tld-stale-warning">Data may be outdated</span>}
              {/* Metrics popover */}
              <div className="tld-metrics-wrap" ref={metricsRef}>
                <button className="tld-metrics-trigger" onClick={()=>setShowMetrics(v=>!v)}>
                  Metrics
                </button>
                {showMetrics&&<MetricsPanel metrics={metrics} lastSuccessAt={lastSuccessAt}/>}
              </div>
            </div>

            <button
              className="tld-refresh-btn"
              onClick={handleManualRefresh}
              disabled={fetching||loading}
              title="Refresh now"
            >
              {fetching||loading
                ? <><div className="tld-refresh-btn-spinner"/>Refreshing…</>
                : <>Refresh</>
              }
            </button>
            <button className="tld-add-btn" onClick={openAddForm}>
              + Add Technician
            </button>
          </div>
        </div>

        {/* Filter Bar */}
        <div className="tld-filter-bar">
          <div className="tld-filter-group search-group">
            <label>Search</label>
            <div className="tld-search-wrap">
              <span className="tld-search-icon"></span>
              <input id="tech-search" type="text" className="tld-search-input"
                placeholder="Name, skill, location…" value={search} onChange={e=>setSearch(e.target.value)}/>
            </div>
          </div>
          <div className="tld-filter-group">
            <label>Status</label>
            <select id="tech-status-filter" className="tld-select" value={statusFilter} onChange={e=>setStatusFilter(e.target.value)}>
              <option value="ALL">All Statuses</option>
              <option value="Available">Available</option>
              <option value="Busy">Busy</option>
              <option value="Assigned">Assigned</option>
              <option value="Offline">Offline</option>
            </select>
          </div>
          <div className="tld-filter-group">
            <label>Zone</label>
            <select id="tech-zone-filter" className="tld-select" value={zoneFilter} onChange={e=>setZoneFilter(e.target.value)}>
              <option value="ALL">All Zones</option>
              {uniqueZones.map(z=><option key={z} value={z}>{z}</option>)}
            </select>
          </div>
          <div className="tld-filter-group">
            <label>Skill</label>
            <select id="tech-skill-filter" className="tld-select" value={skillFilter} onChange={e=>setSkillFilter(e.target.value)}>
              <option value="ALL">All Skills</option>
              {SKILLS.map(s=><option key={s} value={s}>{s}</option>)}
            </select>
          </div>
          {hasFilters&&<button className="tld-filter-clear" onClick={clearFilters}>Clear</button>}
        </div>

        <div className="tld-table-meta">
          <p className="tld-results-count">
            Showing <strong>{pageSlice.length}</strong> of <strong>{filtered.length}</strong> technician{filtered.length!==1?"s":""}
          </p>
        </div>
        <div className="tld-table-wrap">
          <table className="tld-table">
            <thead>
              <tr>
                <th className={`sortable${sortKey==="name"?" sort-active":""}`} onClick={()=>handleSort("name")}>
                  Technician Name <SortIcon col="name" sortKey={sortKey} sortDir={sortDir}/>
                </th>
                <th className={`sortable${sortKey==="status"?" sort-active":""}`} onClick={()=>handleSort("status")}>
                  Status <SortIcon col="status" sortKey={sortKey} sortDir={sortDir}/>
                </th>
                <th className={`sortable${sortKey==="jobs"?" sort-active":""}`} onClick={()=>handleSort("jobs")}>
                  Active Jobs <SortIcon col="jobs" sortKey={sortKey} sortDir={sortDir}/>
                </th>
                <th className={`sortable${sortKey==="ping"?" sort-active":""}`} onClick={()=>handleSort("ping")}>
                  Last Ping <SortIcon col="ping" sortKey={sortKey} sortDir={sortDir}/>
                </th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {/* Initial load loading spinner */}
              {loading && (
                <tr>
                  <td colSpan={5} className="tld-state-cell">
                    <LoadingSpinner message="Loading technician dashboard..." />
                  </td>
                </tr>
              )}

              {/* Initial load error */}
              {!loading&&initError&&(
                <tr><td colSpan={5} className="tld-state-cell">
                  <span className="tld-state-icon"></span>
                  <p className="tld-state-title">Failed to load technicians</p>
                  <p className="tld-state-sub">{initError}</p>
                  <button className="tld-retry-btn" onClick={()=>fetchData(false)}>Retry</button>
                </td></tr>
              )}

              {/* Empty */}
              {!loading&&!initError&&filtered.length===0&&(
                <tr><td colSpan={5} className="tld-state-cell">
                  <span className="tld-state-icon"></span>
                  <p className="tld-state-title">{hasFilters?"No technicians match your filters":"No technicians found"}</p>
                  <p className="tld-state-sub">{hasFilters?"Try adjusting filters.":"Add technicians to get started."}</p>
                  {hasFilters&&<button className="tld-retry-btn" onClick={clearFilters}>Clear Filters</button>}
                </td></tr>
              )}

              {/* Data rows — rendered while fetching too (no flicker) */}
              {!loading&&!initError&&pageSlice.map(tech=>{
                const pct=wPct(tech.currentJobs,tech.maxJobs);
                return(
                  <tr key={tech.id} onClick={()=>openSidebar(tech)} title={`View ${tech.name}`}>
                    <td data-label="Name">
                      <div className="tld-name-cell">
                        <div className="tld-avatar">{getInitials(tech.name)}</div>
                        <div className="tld-name-info">
                          <span className="tld-name-primary">{tech.name}</span>
                          <span className="tld-name-secondary">
                            {tech.skill!=="—"?`${tech.skill}`:""}{tech.location!=="—"?` · ${tech.location}`:""}
                          </span>
                        </div>
                      </div>
                    </td>
                    <td data-label="Status"><StatusBadge status={tech.status}/></td>
                    <td data-label="Active Jobs">
                      <div className="tld-workload-cell">
                        <div className="tld-workload-numbers">{tech.currentJobs} / {tech.maxJobs}</div>
                        <div className="tld-workload-track">
                          <div className={`tld-workload-fill ${wColor(pct)}`} style={{width:`${pct}%`}}/>
                        </div>
                      </div>
                    </td>
                    <td data-label="Last Ping"><span className="tld-ping">{formatAgo(tech.lastPing)}</span></td>
                    <td data-label="Actions">
                      <div className="tld-actions" onClick={e=>e.stopPropagation()}>
                        <button
                          className="icon-action-btn icon-view"
                          onClick={()=>openSidebar(tech)}
                          title="View technician"
                          aria-label="View technician"
                        >
                          <Eye size={15}/>
                        </button>
                        <button
                          className="icon-action-btn icon-edit"
                          onClick={()=>handleEditTech(tech)}
                          title="Edit technician"
                          aria-label="Edit technician"
                        >
                          <Pencil size={15}/>
                        </button>
                        <button
                          className="icon-action-btn icon-delete"
                          onClick={()=>handleDeleteTech(tech)}
                          title="Delete technician"
                          aria-label="Delete technician"
                        >
                          <Trash2 size={15}/>
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {!loading&&!initError&&(
          <div className="tld-pagination">
            <span className="tld-page-info">Page <strong>{safePage}</strong> of <strong>{totalPages}</strong> · {filtered.length} results</span>
            <div className="tld-page-controls">
              <button className="tld-page-btn" onClick={()=>setPage(1)} disabled={safePage===1}>«</button>
              <button className="tld-page-btn" onClick={()=>setPage(p=>Math.max(1,p-1))} disabled={safePage===1}>‹ Prev</button>
              <div className="tld-page-numbers">
                {getPageNums().map(n=><button key={n} className={`tld-page-num${n===safePage?" active":""}`} onClick={()=>setPage(n)}>{n}</button>)}
              </div>
              <button className="tld-page-btn" onClick={()=>setPage(p=>Math.min(totalPages,p+1))} disabled={safePage===totalPages}>Next ›</button>
              <button className="tld-page-btn" onClick={()=>setPage(totalPages)} disabled={safePage===totalPages}>»</button>
            </div>
          </div>
        )}
      </div>

      {/* Detail Sidebar */}
      {selected&&<div className="tld-sidebar-overlay" onClick={closeSidebar}/>}
      <div className={`tld-sidebar${selected?" open":""}`}>
        <div className="tld-sidebar-head">
          <h3>Technician Details</h3>
          <button className="tld-sidebar-close" onClick={closeSidebar}>X</button>
        </div>
        {selected&&(
          <div className="tld-sidebar-body">
            <div className="tld-detail-hero">
              <div className="tld-detail-avatar">{getInitials(selected.name)}</div>
              <div>
                <div className="tld-detail-name">{selected.name}</div>
                <div className="tld-detail-meta"><StatusBadge status={selected.status}/></div>
              </div>
            </div>
            <p className="tld-detail-section-title">Technician Info</p>
            {[
              ["ID",`#${selected.id}`],
              ["Skill",selected.skill],
              ["Zone / Location",selected.location],
              ["Current Jobs",`${selected.currentJobs} / ${selected.maxJobs}`],
              ["Last Active",formatAgo(selected.lastPing)],
            ].map(([label,val])=>(
              <div key={label} className="tld-detail-row">
                <span className="tld-detail-label">{label}</span>
                <span className="tld-detail-value">{val}</span>
              </div>
            ))}
            <div className="tld-status-select-wrap">
              <label>Update Availability Status</label>
              <select className="tld-status-select" value={newStatus} onChange={e=>setNewStatus(e.target.value)}>
                <option value="Available">Available</option>
                <option value="Busy">Busy</option>
                <option value="Assigned">Assigned</option>
                <option value="Offline">Offline</option>
              </select>
              <button className="tld-save-btn" onClick={handleSaveStatus}
                disabled={saving||newStatus===normalizeStatus(selected.status)}>
                {saving?"Saving…":"Save Status"}
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Form Sidebar for Add/Edit */}
      {isFormOpen && <div className="tld-sidebar-overlay" onClick={closeForm}/>}
      <div className={`tld-sidebar${isFormOpen ? " open" : ""}`}>
        <div className="tld-sidebar-head">
          <h3>{isEditing ? "Edit Technician" : "Add New Technician"}</h3>
          <button className="tld-sidebar-close" onClick={closeForm}>X</button>
        </div>
        <div className="tld-sidebar-body">
          <form className="tech-form" onSubmit={handleFormSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div className="form-group" style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <label style={{ fontSize: '11px', fontWeight: 'bold', color: '#475569', textTransform: 'uppercase' }}>Full Name <span style={{ color: '#ef4444' }}>*</span></label>
              <input
                type="text"
                name="technician_name"
                value={techFormData.technician_name}
                onChange={handleFormChange}
                placeholder="e.g. Rajesh Kumar"
                style={{ width: '100%', padding: '8px 12px', border: formErrors.technician_name ? '1px solid #f87171' : '1px solid #e2e8f0', borderRadius: '6px', fontSize: '13px' }}
              />
              {formErrors.technician_name && <span style={{ fontSize: '11px', color: '#ef4444', fontWeight: 'bold' }}>{formErrors.technician_name}</span>}
            </div>

            <div className="form-group" style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <label style={{ fontSize: '11px', fontWeight: 'bold', color: '#475569', textTransform: 'uppercase' }}>Skill <span style={{ color: '#ef4444' }}>*</span></label>
              <input
                type="text"
                name="technician_skill"
                value={techFormData.technician_skill}
                onChange={handleFormChange}
                placeholder="e.g. Electrical, HVAC"
                style={{ width: '100%', padding: '8px 12px', border: formErrors.technician_skill ? '1px solid #f87171' : '1px solid #e2e8f0', borderRadius: '6px', fontSize: '13px' }}
                list="tld-skill-suggestions"
              />
              <datalist id="tld-skill-suggestions">
                {SKILLS.map(s => <option key={s} value={s} />)}
              </datalist>
              {formErrors.technician_skill && <span style={{ fontSize: '11px', color: '#ef4444', fontWeight: 'bold' }}>{formErrors.technician_skill}</span>}
            </div>

            <div className="form-group" style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <label style={{ fontSize: '11px', fontWeight: 'bold', color: '#475569', textTransform: 'uppercase' }}>Location / Zone <span style={{ color: '#ef4444' }}>*</span></label>
              <input
                type="text"
                name="technician_location"
                value={techFormData.technician_location}
                onChange={handleFormChange}
                placeholder="e.g. 13.0827,80.2707"
                style={{ width: '100%', padding: '8px 12px', border: formErrors.technician_location ? '1px solid #f87171' : '1px solid #e2e8f0', borderRadius: '6px', fontSize: '13px' }}
              />
              {formErrors.technician_location && <span style={{ fontSize: '11px', color: '#ef4444', fontWeight: 'bold' }}>{formErrors.technician_location}</span>}
            </div>

            <div className="form-group" style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <label style={{ fontSize: '11px', fontWeight: 'bold', color: '#475569', textTransform: 'uppercase' }}>{isEditing ? "Status" : "Initial Status"}</label>
              <select
                name="technician_status"
                value={techFormData.technician_status}
                onChange={handleFormChange}
                style={{ width: '100%', padding: '8px 12px', border: '1px solid #e2e8f0', borderRadius: '6px', fontSize: '13px', background: '#fff' }}
              >
                <option value="Available">Available</option>
                <option value="Busy">Busy</option>
                <option value="Assigned">Assigned</option>
                <option value="Offline">Offline</option>
              </select>
            </div>

            <div style={{ display: 'flex', gap: '10px', marginTop: '10px' }}>
              <button 
                type="submit" 
                disabled={formLoading}
                style={{ flex: 1, padding: '10px', background: '#2F4F3E', color: '#fff', border: 'none', borderRadius: '6px', fontSize: '13px', fontWeight: 'bold', cursor: 'pointer' }}
              >
                {formLoading ? "Saving..." : isEditing ? "Update Technician" : "Add Technician"}
              </button>
              <button 
                type="button" 
                onClick={closeForm}
                style={{ padding: '10px 16px', background: '#fff', color: '#475569', border: '1px solid #cbd5e1', borderRadius: '6px', fontSize: '13px', fontWeight: 'bold', cursor: 'pointer' }}
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      </div>

    </div>
  );
}
