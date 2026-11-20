import { useEffect, useState } from "react";
import { api, downloadReport } from "./api";
import Login from "./components/Login";
import Upload from "./components/Upload";
import Viewer from "./components/Viewer";
import Progress from "./components/Progress";

const iconPaths = {
  overview: <><rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/></>,
  timeline: <><path d="M4 19V5M4 19h17"/><path d="m7 15 4-4 3 2 5-6"/><circle cx="19" cy="7" r="1"/></>,
  photo: <><rect x="3" y="5" width="18" height="15" rx="2"/><circle cx="8.5" cy="10" r="1.5"/><path d="m21 15-5-5L5 20"/></>,
  search: <><circle cx="10.8" cy="10.8" r="6.8"/><path d="m16 16 4 4"/></>,
  logout: <><path d="M10 17l5-5-5-5M15 12H3"/><path d="M12 3h6a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-6"/></>,
  collapse: <><rect x="3" y="4" width="18" height="16" rx="2"/><path d="M9 4v16m6-11-3 3 3 3"/></>,
  expand: <><rect x="3" y="4" width="18" height="16" rx="2"/><path d="M9 4v16m6-8-3-3m3 3-3 3"/></>,
  plus: <><path d="M12 5v14M5 12h14"/></>,
  download: <><path d="M12 3v12m-5-5 5 5 5-5"/><path d="M5 17v3h14v-3"/></>,
  ruler: <><path d="M3 16 16 3l5 5L8 21z"/><path d="m13 6 2 2m-5 1 2 2m-5 1 2 2"/></>,
  close: <><path d="m6 6 12 12M18 6 6 18"/></>,
};
function Icon({ name, size = 17 }) {
  return <svg aria-hidden="true" width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">{iconPaths[name]}</svg>;
}

export default function App() {
  const [authed, setAuthed] = useState(!!localStorage.getItem("token"));
  const [wounds, setWounds] = useState([]);
  const [wid, setWid] = useState(null);
  const [history, setHistory] = useState([]);
  const [woundQuery, setWoundQuery] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [sidebarCollapsed, setSidebarCollapsed] = useState(localStorage.getItem("smartheal-sidebar-collapsed") === "true");
  const [activeNav, setActiveNav] = useState("overview");
  const activeWound = wounds.find((w) => w.id === wid);
  const visibleWounds = wounds.filter((w) => `${w.label} ${w.body_location || ""}`.toLowerCase().includes(woundQuery.trim().toLowerCase()));
  const filteredHistory = history.filter((item) => (!dateFrom || item.captured_on >= dateFrom) && (!dateTo || item.captured_on <= dateTo));

  const loadWounds = () => api("/api/wounds").then((items) => {
    setWounds(items);
    if (!wid && items.length) setWid(items[0].id);
  }).catch(() => { localStorage.removeItem("token"); setAuthed(false); });
  const loadHistory = () => (wid ? api(`/api/wounds/${wid}/history`).then(setHistory) : setHistory([]));
  useEffect(() => { if (authed) loadWounds(); }, [authed]);
  useEffect(() => { loadHistory(); }, [wid]);

  const addWound = async () => {
    const label = prompt("Wound name (e.g. Forearm cut)");
    if (!label?.trim()) return;
    const body_location = prompt("Body location (optional, e.g. left forearm)") || "";
    const w = await api("/api/wounds", { method: "POST", body: { label: label.trim(), body_location: body_location.trim() } });
    await loadWounds();
    setWid(w.id);
  };
  const logout = () => { localStorage.removeItem("token"); setAuthed(false); setWid(null); };
  const jumpTo = (id, nav = id) => {
    setActiveNav(nav);
    document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
  };
  const toggleSidebar = () => setSidebarCollapsed((collapsed) => {
    const next = !collapsed;
    localStorage.setItem("smartheal-sidebar-collapsed", String(next));
    return next;
  });
  const exportCsv = () => {
    const safeCell = (value) => {
      let text = String(value ?? "");
      if (/^[=+@\-\t\r]/.test(text)) text = `'${text}`;
      return `"${text.replaceAll('"', '""')}"`;
    };
    const rows = [["Wound", "Body location", "Photo date", "Area", "Area unit", "Perimeter", "Perimeter unit", "Low confidence", "Boundary corrected"]];
    for (const item of filteredHistory) {
      const calibrated = item.calibrated;
      rows.push([activeWound?.label, activeWound?.body_location, item.captured_on,
        calibrated ? item.area_cm2 : item.area_px, calibrated ? "cm2" : "px2",
        calibrated ? item.perimeter_cm : item.perimeter_px, calibrated ? "cm" : "px",
        item.low_confidence ? "Yes" : "No", item.manually_corrected ? "Yes" : "No"]);
    }
    const blob = new Blob(["\uFEFF" + rows.map((row) => row.map(safeCell).join(",")).join("\r\n")], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = Object.assign(document.createElement("a"), { href: url, download: `smartheal_wound_${wid}_measurements.csv` });
    link.click();
    URL.revokeObjectURL(url);
  };
  if (!authed) return <Login onAuth={() => setAuthed(true)} />;

  const latest = history[history.length - 1];
  const first = history[0];
  const change = first && latest && history.length > 1
    ? ((first.area_px - latest.area_px) / first.area_px) * 100 : null;

  return (
    <div className="app-shell">
      <aside className={`sidebar ${sidebarCollapsed ? "sidebar-collapsed" : ""}`}>
        <div className="brand-row">
          <div className="brand"><span className="brand-mark">+</span><span className="brand-name">smart<span>heal</span><small>WOUND CARE JOURNAL</small></span></div>
          <button className="sidebar-toggle" onClick={toggleSidebar} aria-label={sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"} title={sidebarCollapsed ? "Expand sidebar" : "Collapse sidebar"}><Icon name={sidebarCollapsed ? "expand" : "collapse"} size={16} /></button>
        </div>
        <div className="side-label">WORKSPACE</div>
        <button className={`side-link ${activeNav === "overview" ? "active" : ""}`} onClick={() => jumpTo("overview", "overview")} title="Overview"><span className="side-icon"><Icon name="overview" /></span><span className="side-link-label">Overview</span></button>
        <button className={`side-link ${activeNav === "photo" ? "active" : ""}`} onClick={() => jumpTo("upload-photo", "photo")} title="Add a progress photo"><span className="side-icon"><Icon name="photo" /></span><span className="side-link-label">Add a photo</span><span className="nav-shortcut">+</span></button>
        <button className={`side-link ${activeNav === "timeline" ? "active" : ""}`} onClick={() => jumpTo("timeline", "timeline")} title="Photo timeline"><span className="side-icon"><Icon name="timeline" /></span><span className="side-link-label">Photo timeline</span></button>
        <div className="side-section-head"><span className="side-label">MY WOUNDS</span><span className="record-count">{wounds.length}</span><button className="add-small" onClick={addWound} aria-label="Add wound" title="Add a wound"><Icon name="plus" size={15} /></button></div>
        {wounds.length > 0 && <div className="wound-search-wrap"><Icon name="search" size={15} /><input className="wound-search" aria-label="Search wound records" placeholder="Search wounds" value={woundQuery} onChange={(e) => setWoundQuery(e.target.value)} />{woundQuery && <button className="search-clear" aria-label="Clear search" onClick={() => setWoundQuery("")}><Icon name="close" size={13} /></button>}</div>}
        {wounds.length ? <div className="wound-list">{visibleWounds.length ? visibleWounds.map((w) => <button key={w.id} title={`${w.label}${w.body_location ? ` | ${w.body_location}` : ""}`} className={`wound-link ${wid === w.id ? "selected" : ""}`} onClick={() => setWid(w.id)}><span className="wound-dot" /> <span className="wound-copy"><b>{w.label}</b><small>{w.body_location || "Location not set"}</small></span></button>) : <p className="sidebar-empty">No matching wounds.</p>}</div> : <p className="sidebar-empty">Your wound records will appear here.</p>}
        <div className="sidebar-spacer" />
        <div className="side-recent"><div className="side-recent-head"><span className="recent-icon"><Icon name="timeline" size={14} /></span><span>LATEST UPDATE</span></div><b>{latest ? latest.captured_on : "No photos yet"}</b><small>{latest ? `${history.length} photo ${history.length === 1 ? "entry" : "entries"} for this wound` : "Add a photo to start tracking"}</small></div>
        <div className="side-tip"><span>PHOTO TIP</span><p>Use similar lighting and distance for more useful comparisons.</p></div>
        <button className="side-link logout-link" onClick={logout} title="Log out"><span className="side-icon"><Icon name="logout" /></span><span className="side-link-label">Log out</span></button>
      </aside>

      <main className="main-area" id="overview">
        <header className="page-header">
          <div className="breadcrumb">MY WORKSPACE <span>/</span> WOUND TRACKER</div>
          <div className="header-actions"><span className="secure-badge"><i /> Private health journal</span><button className="avatar" title="Log out" onClick={logout}>SH</button></div>
        </header>
        <section className="welcome-row">
          <div><p className="eyebrow">YOUR HEALING JOURNEY</p><h1>{activeWound ? activeWound.label : "Your wound tracker"}</h1><p className="welcome-sub">{activeWound?.body_location || "Keep a clear, dated record of visible changes."}</p></div>
          <div className="welcome-actions"><button className="button-secondary" onClick={addWound}><Icon name="plus" size={14} /> New wound</button>{wid && history.length > 0 && <><button className="button-secondary" onClick={exportCsv}><Icon name="download" size={14} /> Export CSV</button><button className="button-primary" onClick={() => downloadReport(wid)}><Icon name="download" size={14} /> Export PDF</button></>}</div>
        </section>
        <div className="notice"><span className="notice-icon">i</span><span><b>Tracking tool, not a diagnosis.</b> SmartHeal measures visible wound area in photos. Contact a healthcare professional with medical concerns.</span></div>

        {!wounds.length ? <section className="empty-state"><div className="empty-icon"><Icon name="photo" size={21} /></div><h2>Start your wound journal</h2><p>Create a record, then add a dated photo to track visible changes over time.</p><button className="button-primary" onClick={addWound}>Create your first wound</button></section> : !wid ? <section className="empty-state"><h2>Select a wound</h2><p>Choose a record from the sidebar to view its history.</p></section> : <>
          <section className="stat-grid">
            <article className="stat-card"><div className="stat-top"><span>PHOTO ENTRIES</span><span className="stat-icon lavender"><Icon name="photo" size={14} /></span></div><strong>{history.length}</strong><small>{history.length === 1 ? "dated record" : "dated records"}</small></article>
            <article className="stat-card"><div className="stat-top"><span>LATEST MEASUREMENT</span><span className="stat-icon mint"><Icon name="ruler" size={14} /></span></div><strong>{latest ? (latest.calibrated ? latest.area_cm2 : latest.area_px).toFixed(1) : "Not available"}</strong><small>{latest ? `${latest.calibrated ? "cm2" : "px2 (uncalibrated)"} | ${latest.captured_on}` : "Add a photo to begin"}</small></article>
            <article className="stat-card"><div className="stat-top"><span>CHANGE SINCE FIRST PHOTO</span><span className="stat-icon peach"><Icon name="timeline" size={14} /></span></div><strong className={change == null ? "" : change >= 0 ? "positive" : "negative"}>{change == null ? "Not enough data" : `${change >= 0 ? "Reduced " : "Increased "}${Math.abs(change).toFixed(1)}%`}</strong><small>{history.length > 1 ? "based on visible area" : "Add another photo to compare"}</small></article>
          </section>

          <section className="section-heading" id="upload-photo"><div><p className="eyebrow">KEEP YOUR RECORD UP TO DATE</p><h2>Add a progress photo</h2></div><span className="step-pill"><Icon name="photo" size={13} /> PHOTO LOG</span></section>
          <Upload woundId={wid} onDone={loadHistory} />
          {history.length > 0 && <div id="timeline" className="tracking-section"><section className="section-heading chart-heading"><div><p className="eyebrow">AT A GLANCE</p><h2>Area over time</h2></div><span className="unit-note">{filteredHistory.length} of {history.length} records / {filteredHistory.length && filteredHistory.every((h) => h.calibrated) ? "cm2" : "pixels"}</span></section>
            <div className="history-filters"><label>From <input type="date" value={dateFrom} max={dateTo || undefined} onChange={(e) => setDateFrom(e.target.value)} /></label><label>To <input type="date" value={dateTo} min={dateFrom || undefined} onChange={(e) => setDateTo(e.target.value)} /></label>{(dateFrom || dateTo) && <button className="clear-filter" onClick={() => { setDateFrom(""); setDateTo(""); }}>Clear dates</button>}</div>
            {filteredHistory.length ? <Progress history={filteredHistory} /> : <div className="filter-empty">No photo records match this date range. Adjust the dates or clear the filter.</div>}
            <section className="section-heading history-heading"><div><p className="eyebrow">YOUR RECORD</p><h2>Photo timeline</h2></div><span className="unit-note">{filteredHistory.length} {filteredHistory.length === 1 ? "entry" : "entries"}</span></section>
            {filteredHistory.length ? [...filteredHistory].reverse().map((item, i) => <div className="timeline-entry" key={item.id}><div className="timeline-rail"><span className="timeline-node">{String(filteredHistory.length - i).padStart(2, "0")}</span></div><Viewer item={item} onChanged={loadHistory} /></div>) : <div className="filter-empty">No entries to show.</div>}
          </div>}
        </>}
        <footer className="page-footer">SMARTHEAL <span className="footer-mark"><Icon name="photo" size={11} /></span> Your photos help you keep track. A clinician can help interpret them.</footer>
      </main>
    </div>
  );
}
