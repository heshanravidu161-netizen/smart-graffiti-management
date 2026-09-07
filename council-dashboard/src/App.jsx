import { useEffect, useMemo, useState } from "react";
import {
  MapContainer,
  TileLayer,
  CircleMarker,
  Popup,
} from "react-leaflet";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import "leaflet/dist/leaflet.css";
import "./App.css";

const API_BASE = "http://localhost:8000";
const DEFAULT_CENTER = [-31.9523, 115.8613];

const STATUS_INFORMATION = {
  new: {
    label: "New",
    colour: "#f59e0b",
    className: "status-new",
  },
  scheduled: {
    label: "Scheduled",
    colour: "#3b82f6",
    className: "status-scheduled",
  },
  resolved: {
    label: "Resolved",
    colour: "#10b981",
    className: "status-resolved",
  },
};

function StatusBadge({ status }) {
  const information =
    STATUS_INFORMATION[status] || {
      label: status,
      className: "",
    };

  return (
    <span className={`status-badge ${information.className}`}>
      <span className="status-dot" />
      {information.label}
    </span>
  );
}

function App() {
  const [reports, setReports] = useState([]);
  const [selectedReport, setSelectedReport] = useState(null);

  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [filter, setFilter] = useState("all");
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState("newest");
  const [view, setView] = useState("list");

  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [updating, setUpdating] = useState(false);

  const [error, setError] = useState(null);
  const [message, setMessage] = useState("");
  const [lastUpdated, setLastUpdated] = useState(null);

  async function fetchReports(quiet = false) {
    if (quiet) {
      setRefreshing(true);
    } else {
      setLoading(true);
    }

    setError(null);

    try {
      const response = await fetch(`${API_BASE}/reports/`);

      if (!response.ok) {
        throw new Error(`Server returned ${response.status}`);
      }

      const data = await response.json();
      setReports(data);
      setLastUpdated(new Date());
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }

  useEffect(() => {
    fetchReports();
  }, []);

  useEffect(() => {
    function handleEscape(event) {
      if (event.key === "Escape") {
        setSidebarOpen(false);
        setSelectedReport(null);
      }
    }

    window.addEventListener("keydown", handleEscape);

    return () => {
      window.removeEventListener("keydown", handleEscape);
    };
  }, []);

  const reportCounts = useMemo(() => {
    return {
      all: reports.length,

      new: reports.filter(
        (report) => report.status === "new",
      ).length,

      scheduled: reports.filter(
        (report) => report.status === "scheduled",
      ).length,

      resolved: reports.filter(
        (report) => report.status === "resolved",
      ).length,
    };
  }, [reports]);

  const statusChartData = useMemo(() => {
    return [
      {
        name: "New",
        value: reportCounts.new,
        colour: STATUS_INFORMATION.new.colour,
      },
      {
        name: "Scheduled",
        value: reportCounts.scheduled,
        colour: STATUS_INFORMATION.scheduled.colour,
      },
      {
        name: "Resolved",
        value: reportCounts.resolved,
        colour: STATUS_INFORMATION.resolved.colour,
      },
    ];
  }, [reportCounts]);

  const sevenDayChartData = useMemo(() => {
    const days = [];
    const totalsByDate = new Map();

    for (let offset = 6; offset >= 0; offset -= 1) {
      const date = new Date();
      date.setHours(0, 0, 0, 0);
      date.setDate(date.getDate() - offset);

      const key = [
        date.getFullYear(),
        String(date.getMonth() + 1).padStart(2, "0"),
        String(date.getDate()).padStart(2, "0"),
      ].join("-");

      totalsByDate.set(key, 0);
      days.push({
        key,
        day: new Intl.DateTimeFormat("en-AU", {
          weekday: "short",
        }).format(date),
      });
    }

    reports.forEach((report) => {
      if (!report.submitted_at) {
        return;
      }

      const submittedDate = new Date(report.submitted_at);

      if (Number.isNaN(submittedDate.getTime())) {
        return;
      }

      const key = [
        submittedDate.getFullYear(),
        String(submittedDate.getMonth() + 1).padStart(2, "0"),
        String(submittedDate.getDate()).padStart(2, "0"),
      ].join("-");

      if (totalsByDate.has(key)) {
        totalsByDate.set(key, totalsByDate.get(key) + 1);
      }
    });

    return days.map((day) => ({
      day: day.day,
      reports: totalsByDate.get(day.key),
    }));
  }, [reports]);

  const visibleReports = useMemo(() => {
    const searchText = search.trim().toLowerCase();

    return reports
      .filter((report) => {
        return filter === "all" || report.status === filter;
      })
      .filter((report) => {
        if (!searchText) {
          return true;
        }

        const searchableText = `
          ${report.id}
          ${report.notes || ""}
          ${report.latitude}
          ${report.longitude}
          ${report.reporter_name || ""}
          ${report.reporter_email || ""}
          ${report.reporter_phone || ""}
        `.toLowerCase();

        return searchableText.includes(searchText);
      })
      .sort((firstReport, secondReport) => {
        const firstDate = new Date(firstReport.submitted_at);
        const secondDate = new Date(secondReport.submitted_at);

        if (sort === "oldest") {
          return firstDate - secondDate;
        }

        return secondDate - firstDate;
      });
  }, [reports, filter, search, sort]);

  async function updateStatus(reportId, newStatus) {
    setUpdating(true);
    setMessage("");

    try {
      const response = await fetch(
        `${API_BASE}/reports/${reportId}/status?status=${newStatus}`,
        {
          method: "PATCH",
        },
      );

      if (!response.ok) {
        throw new Error(`Server returned ${response.status}`);
      }

      const updatedReport = await response.json();

      setReports((currentReports) =>
        currentReports.map((report) =>
          report.id === reportId ? updatedReport : report,
        ),
      );

      setSelectedReport(updatedReport);

      setMessage(
        `Report #${reportId} was updated successfully.`,
      );

      window.setTimeout(() => {
        setMessage("");
      }, 3000);
    } catch (requestError) {
      setMessage(`Update failed: ${requestError.message}`);
    } finally {
      setUpdating(false);
    }
  }

  function formatDate(date) {
    if (!date) {
      return "Date unavailable";
    }

    return new Intl.DateTimeFormat("en-AU", {
      day: "numeric",
      month: "short",
      year: "numeric",
      hour: "numeric",
      minute: "2-digit",
    }).format(new Date(date));
  }

  const mapCentre =
    visibleReports.length > 0
      ? [
          visibleReports[0].latitude,
          visibleReports[0].longitude,
        ]
      : DEFAULT_CENTER;

  const completionRate = reportCounts.all
    ? Math.round((reportCounts.resolved / reportCounts.all) * 100)
    : 0;

  const identifiedReports = reports.filter(
    (report) => report.reporter_email || report.reporter_name,
  ).length;

  const reportsWithPhotos = reports.filter(
    (report) => Boolean(report.image_url),
  ).length;

  return (
    <div className="app-shell">
      {/* Button used to open the hidden sidebar */}
      <button
        className="menu-button"
        onClick={() => setSidebarOpen(true)}
        aria-label="Open navigation menu"
      >
        ☰
      </button>

      {/* Dark background behind the open sidebar */}
      {sidebarOpen && (
        <button
          className="sidebar-overlay"
          onClick={() => setSidebarOpen(false)}
          aria-label="Close navigation menu"
        />
      )}

      {/* Hidden expandable sidebar */}
      <aside
        className={`sidebar ${
          sidebarOpen ? "sidebar-open" : ""
        }`}
      >
        <div className="sidebar-header">
          <div className="brand">
            <span className="brand-mark">U</span>

            <div className="brand-text">
              <strong>UrbanEyes</strong>
              <small>Council Portal</small>
            </div>
          </div>

          <button
            className="sidebar-close"
            onClick={() => setSidebarOpen(false)}
            aria-label="Close navigation menu"
          >
            ✕
          </button>
        </div>

        <nav className="sidebar-navigation">
          <button
            className="nav-item active"
            onClick={() => setSidebarOpen(false)}
          >
            <span className="nav-icon">▦</span>
            Overview
          </button>

          <button
            className="nav-item"
            onClick={() => setSidebarOpen(false)}
          >
            <span className="nav-icon">▤</span>
            Reports

            <span className="nav-count">
              {reportCounts.new}
            </span>
          </button>

          <button
            className="nav-item"
            onClick={() => setSidebarOpen(false)}
          >
            <span className="nav-icon">♙</span>
            User Management

            <span className="soon-label">Soon</span>
          </button>
        </nav>

        <div className="sidebar-bottom">
          <button className="nav-item">
            <span className="nav-icon">⚙</span>
            Settings
          </button>

          <div className="council-user">
            <div className="council-avatar">CS</div>

            <div>
              <strong>Council Staff</strong>
              <small>Administrator</small>
            </div>
          </div>
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <div>
            <p className="eyebrow">OPERATIONS OVERVIEW</p>

            <h1>Graffiti reports</h1>

            <p className="subtitle">
              Review, schedule and resolve community reports.
            </p>
          </div>

          <button
            className="refresh-button"
            onClick={() => fetchReports(true)}
            disabled={refreshing}
          >
            <span className={refreshing ? "rotating" : ""}>
              ↻
            </span>

            {refreshing ? "Refreshing..." : "Refresh data"}
          </button>
        </header>

        {/* Report totals */}
        <section className="stat-grid">
          <button
            className={`stat-card ${
              filter === "all" ? "selected" : ""
            }`}
            onClick={() => setFilter("all")}
          >
            <div className="stat-heading">
              <span className="stat-dot total" />
              Total reports
            </div>

            <strong>{reportCounts.all}</strong>
            <small>All community submissions</small>
          </button>

          <button
            className={`stat-card ${
              filter === "new" ? "selected" : ""
            }`}
            onClick={() => setFilter("new")}
          >
            <div className="stat-heading">
              <span className="stat-dot new" />
              New reports
            </div>

            <strong>{reportCounts.new}</strong>
            <small>Waiting for review</small>
          </button>

          <button
            className={`stat-card ${
              filter === "scheduled" ? "selected" : ""
            }`}
            onClick={() => setFilter("scheduled")}
          >
            <div className="stat-heading">
              <span className="stat-dot scheduled" />
              Scheduled
            </div>

            <strong>{reportCounts.scheduled}</strong>
            <small>Action has been planned</small>
          </button>

          <button
            className={`stat-card ${
              filter === "resolved" ? "selected" : ""
            }`}
            onClick={() => setFilter("resolved")}
          >
            <div className="stat-heading">
              <span className="stat-dot resolved" />
              Resolved
            </div>

            <strong>{reportCounts.resolved}</strong>
            <small>Work has been completed</small>
          </button>
        </section>

        <section className="operations-panel">
          <div className="operations-heading">
            <div>
              <p className="eyebrow">LIVE SERVICE SNAPSHOT</p>
              <h2>Operational summary</h2>
            </div>

            <span className="live-status">
              <i />
              Live data
            </span>
          </div>

          <div className="operations-grid">
            <article className="progress-card">
              <div className="progress-copy">
                <span>Resolution progress</span>
                <strong>{completionRate}%</strong>
              </div>

              <div className="progress-track">
                <span style={{ width: `${completionRate}%` }} />
              </div>

              <small>
                {reportCounts.resolved} of {reportCounts.all} reports resolved
              </small>
            </article>

            <article className="insight-card attention">
              <span className="insight-icon">!</span>
              <div>
                <strong>{reportCounts.new}</strong>
                <span>Awaiting council review</span>
              </div>
            </article>

            <article className="insight-card">
              <span className="insight-icon">✓</span>
              <div>
                <strong>{identifiedReports}</strong>
                <span>Reports with identified users</span>
              </div>
            </article>

            <article className="insight-card">
              <span className="insight-icon">▧</span>
              <div>
                <strong>{reportsWithPhotos}</strong>
                <span>Reports with photo evidence</span>
              </div>
            </article>
          </div>

          <p className="updated-time">
            Last refreshed: {lastUpdated ? formatDate(lastUpdated) : "Not yet refreshed"}
          </p>
        </section>

        {/* Live charts generated from report data */}
        <section className="analytics-section">
          <div className="analytics-heading">
            <div>
              <p className="eyebrow">REPORT ANALYTICS</p>
              <h2>Service trends</h2>
            </div>

            <span>{reportCounts.all} total reports</span>
          </div>

          <div className="chart-grid">
            <article className="chart-card">
              <div className="chart-card-heading">
                <div>
                  <h3>Status distribution</h3>
                  <p>Current workflow breakdown</p>
                </div>

                <span className="chart-icon">◔</span>
              </div>

              <div className="chart-area">
                {reportCounts.all === 0 ? (
                  <div className="chart-empty">
                    No report data available
                  </div>
                ) : (
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={statusChartData}
                        dataKey="value"
                        nameKey="name"
                        cx="50%"
                        cy="45%"
                        innerRadius={58}
                        outerRadius={88}
                        paddingAngle={4}
                        stroke="none"
                      >
                        {statusChartData.map((entry) => (
                          <Cell
                            key={entry.name}
                            fill={entry.colour}
                          />
                        ))}
                      </Pie>

                      <Tooltip
                        contentStyle={{
                          background: "#091321",
                          border: "1px solid #22344d",
                          borderRadius: "10px",
                          color: "#f5f8ff",
                        }}
                      />

                      <Legend
                        iconType="circle"
                        verticalAlign="bottom"
                      />
                    </PieChart>
                  </ResponsiveContainer>
                )}
              </div>
            </article>

            <article className="chart-card chart-card-wide">
              <div className="chart-card-heading">
                <div>
                  <h3>Reports received</h3>
                  <p>Submissions during the last seven days</p>
                </div>

                <span className="chart-icon">▥</span>
              </div>

              <div className="chart-area">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={sevenDayChartData}
                    margin={{ top: 12, right: 8, left: -22, bottom: 0 }}
                  >
                    <CartesianGrid
                      stroke="#17263a"
                      strokeDasharray="4 4"
                      vertical={false}
                    />

                    <XAxis
                      dataKey="day"
                      tick={{ fill: "#74839a", fontSize: 11 }}
                      axisLine={false}
                      tickLine={false}
                    />

                    <YAxis
                      allowDecimals={false}
                      tick={{ fill: "#74839a", fontSize: 11 }}
                      axisLine={false}
                      tickLine={false}
                    />

                    <Tooltip
                      cursor={{ fill: "rgba(23, 139, 255, 0.08)" }}
                      contentStyle={{
                        background: "#091321",
                        border: "1px solid #22344d",
                        borderRadius: "10px",
                        color: "#f5f8ff",
                      }}
                    />

                    <Bar
                      dataKey="reports"
                      name="Reports"
                      fill="#178bff"
                      radius={[7, 7, 0, 0]}
                      maxBarSize={42}
                    />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </article>
          </div>
        </section>

        <section className="workspace">
          {/* Search and filters */}
          <div className="workspace-toolbar">
            <div className="search-box">
              <span>⌕</span>

              <input
                type="search"
                value={search}
                onChange={(event) =>
                  setSearch(event.target.value)
                }
                placeholder="Search reports or people"
                aria-label="Search reports"
              />
            </div>

            <div className="toolbar-actions">
              <select
                value={filter}
                onChange={(event) =>
                  setFilter(event.target.value)
                }
              >
                <option value="all">All statuses</option>
                <option value="new">New</option>
                <option value="scheduled">Scheduled</option>
                <option value="resolved">Resolved</option>
              </select>

              <select
                value={sort}
                onChange={(event) =>
                  setSort(event.target.value)
                }
              >
                <option value="newest">Newest first</option>
                <option value="oldest">Oldest first</option>
              </select>

              <div className="view-switch">
                <button
                  className={view === "list" ? "active" : ""}
                  onClick={() => setView("list")}
                >
                  List
                </button>

                <button
                  className={view === "map" ? "active" : ""}
                  onClick={() => setView("map")}
                >
                  Map
                </button>
              </div>
            </div>
          </div>

          <div className="results-heading">
            <div>
              <h2>
                {filter === "all"
                  ? "All reports"
                  : `${STATUS_INFORMATION[filter].label} reports`}
              </h2>

              <p>
                {visibleReports.length}{" "}
                {visibleReports.length === 1
                  ? "result"
                  : "results"}
              </p>
            </div>
          </div>

          {loading && (
            <div className="state-panel">
              <div className="spinner" />

              <strong>Loading reports</strong>

              <span>
                Connecting to the UrbanEyes service...
              </span>
            </div>
          )}

          {error && (
            <div className="state-panel error">
              <strong>Reports could not be loaded</strong>

              <span>
                {error}. Check that the backend is running.
              </span>

              <button onClick={() => fetchReports()}>
                Try again
              </button>
            </div>
          )}

          {!loading &&
            !error &&
            visibleReports.length === 0 && (
              <div className="state-panel">
                <strong>No matching reports</strong>

                <span>
                  Try changing the search or status filter.
                </span>
              </div>
            )}

          {/* Report list */}
          {!loading &&
            !error &&
            view === "list" &&
            visibleReports.length > 0 && (
              <div className="report-list">
                <div className="list-header">
                  <span>Report</span>
                  <span>Reporter</span>
                  <span>Location</span>
                  <span>Status</span>
                  <span />
                </div>

                {visibleReports.map((report) => (
                  <button
                    className="report-row"
                    key={report.id}
                    onClick={() => setSelectedReport(report)}
                  >
                    <span className="report-primary">
                      <span className="thumbnail">
                        {report.image_url ? (
                          <img
                            src={report.image_url}
                            alt=""
                          />
                        ) : (
                          <span>▧</span>
                        )}
                      </span>

                      <span className="report-description">
                        <strong>Report #{report.id}</strong>

                        <small>
                          {report.notes ||
                            "No description provided"}
                        </small>
                      </span>
                    </span>

                    <span className="reporter-summary">
                      <strong>
                        {report.reporter_name ||
                          "Name not provided"}
                      </strong>

                      <small>
                        {report.reporter_email ||
                          "Email not provided"}
                      </small>
                    </span>

                    <span className="report-location">
                      📍{" "}
                      {Number(report.latitude).toFixed(4)},{" "}
                      {Number(report.longitude).toFixed(4)}
                    </span>

                    <StatusBadge status={report.status} />

                    <span className="row-arrow">›</span>
                  </button>
                ))}
              </div>
            )}

          {/* Report map */}
          {!loading &&
            !error &&
            view === "map" &&
            visibleReports.length > 0 && (
              <div className="map-wrapper">
                <MapContainer
                  key={`${mapCentre[0]}-${mapCentre[1]}-${visibleReports.length}`}
                  center={mapCentre}
                  zoom={12}
                  scrollWheelZoom
                  style={{
                    width: "100%",
                    height: "570px",
                  }}
                >
                  <TileLayer
                    url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
                    attribution="Tiles &copy; Esri"
                  />

                  {visibleReports.map((report) => (
                    <CircleMarker
                      key={report.id}
                      center={[
                        report.latitude,
                        report.longitude,
                      ]}
                      radius={10}
                      pathOptions={{
                        color: "#ffffff",
                        weight: 3,
                        fillColor:
                          STATUS_INFORMATION[report.status]
                            ?.colour || "#64748b",
                        fillOpacity: 1,
                      }}
                      eventHandlers={{
                        click: () =>
                          setSelectedReport(report),
                      }}
                    >
                      <Popup>
                        <strong>Report #{report.id}</strong>

                        <br />

                        {report.reporter_name ||
                          report.reporter_email ||
                          "Unknown reporter"}

                        <br />

                        <button
                          className="popup-button"
                          onClick={() =>
                            setSelectedReport(report)
                          }
                        >
                          View details
                        </button>
                      </Popup>
                    </CircleMarker>
                  ))}
                </MapContainer>

                <div className="map-legend">
                  {Object.entries(STATUS_INFORMATION).map(
                    ([status, information]) => (
                      <span key={status}>
                        <i
                          style={{
                            background: information.colour,
                          }}
                        />

                        {information.label}
                      </span>
                    ),
                  )}
                </div>
              </div>
            )}
        </section>
      </main>

      {/* Report details panel */}
      {selectedReport && (
        <div
          className="drawer-overlay"
          onMouseDown={(event) => {
            if (event.target === event.currentTarget) {
              setSelectedReport(null);
            }
          }}
        >
          <aside
            className="detail-drawer"
            role="dialog"
            aria-modal="true"
          >
            <div className="drawer-header">
              <div>
                <p>REPORT DETAILS</p>

                <h2>Report #{selectedReport.id}</h2>
              </div>

              <button
                className="drawer-close"
                onClick={() => setSelectedReport(null)}
                aria-label="Close report details"
              >
                ✕
              </button>
            </div>

            <div className="report-image">
              {selectedReport.image_url ? (
                <img
                  src={selectedReport.image_url}
                  alt={`Graffiti report ${selectedReport.id}`}
                />
              ) : (
                <div className="no-image">
                  <span>▧</span>
                  No image available
                </div>
              )}
            </div>

            <div className="detail-section">
              <div className="detail-title">
                <span>Current status</span>

                <StatusBadge status={selectedReport.status} />
              </div>

              <label htmlFor="status-update">
                Update workflow status
              </label>

              <select
                id="status-update"
                value={selectedReport.status}
                disabled={updating}
                onChange={(event) =>
                  updateStatus(
                    selectedReport.id,
                    event.target.value,
                  )
                }
              >
                <option value="new">
                  New — needs review
                </option>

                <option value="scheduled">
                  Scheduled — action planned
                </option>

                <option value="resolved">
                  Resolved — work completed
                </option>
              </select>
            </div>

            <div className="detail-grid">
              <div>
                <span>Location</span>

                <strong>
                  📍{" "}
                  {Number(selectedReport.latitude).toFixed(5)}
                  ,{" "}
                  {Number(selectedReport.longitude).toFixed(
                    5,
                  )}
                </strong>
              </div>

              <div>
                <span>Submitted</span>

                <strong>
                  ◷ {formatDate(selectedReport.submitted_at)}
                </strong>
              </div>
            </div>

            <div className="detail-section">
              <span className="section-label">
                Submitted by
              </span>

              <div className="reporter-details">
                <div className="reporter-avatar">
                  {(
                    selectedReport.reporter_name ||
                    selectedReport.reporter_email ||
                    "U"
                  )
                    .charAt(0)
                    .toUpperCase()}
                </div>

                <div className="reporter-information">
                  <strong>
                    {selectedReport.reporter_name ||
                      "Name not provided"}
                  </strong>

                  <span>
                    {selectedReport.reporter_email ||
                      "Email not provided"}
                  </span>

                  <span>
                    {selectedReport.reporter_phone ||
                      "Phone number not provided"}
                  </span>
                </div>
              </div>

              <div className="user-id">
                <span>Supabase User ID</span>

                <code>
                  {selectedReport.submitted_by_uuid ||
                    "Not available"}
                </code>
              </div>
            </div>

            <div className="detail-section">
              <span className="section-label">
                Reporter notes
              </span>

              <p
                className={
                  selectedReport.notes ? "" : "muted"
                }
              >
                {selectedReport.notes ||
                  "No notes were included with this report."}
              </p>
            </div>

            <a
              className="map-link"
              href={`https://www.openstreetmap.org/?mlat=${selectedReport.latitude}&mlon=${selectedReport.longitude}#map=17/${selectedReport.latitude}/${selectedReport.longitude}`}
              target="_blank"
              rel="noreferrer"
            >
              Open location in map
            </a>
          </aside>
        </div>
      )}

      {message && (
        <div
          className={`toast ${
            message.startsWith("Update failed")
              ? "error"
              : ""
          }`}
        >
          {message}
        </div>
      )}
    </div>
  );
}

export default App;
