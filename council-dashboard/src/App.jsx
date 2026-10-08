import { useEffect, useMemo, useRef, useState } from "react";
import { createClient } from "@supabase/supabase-js";
import {
  MapContainer,
  TileLayer,
  CircleMarker,
  Popup,
} from "react-leaflet";
import {
  Area,
  AreaChart,
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
import "./CouncilLogin.css";

const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL;
const SUPABASE_ANON_KEY = import.meta.env.VITE_SUPABASE_ANON_KEY;

const supabase =
  SUPABASE_URL && SUPABASE_ANON_KEY
    ? createClient(SUPABASE_URL, SUPABASE_ANON_KEY)
    : null;

const API_BASE =
  import.meta.env.VITE_API_URL ||
  "http://127.0.0.1:8000";
const DEFAULT_CENTER = [-31.9523, 115.8613];
const AUSTRALIA_CENTER = [-25.2744, 133.7751];

const PRIORITY_COLOURS = {
  high: "#fb3d67",
  medium: "#f59e0b",
  low: "#22c55e",
  pending: "#8b5cf6",
  not_applicable: "#64748b",
};

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

const PRIORITY_INFORMATION = {
  high: {
    label: "High priority",
    action: "Immediate removal required",
  },
  medium: {
    label: "Medium priority",
    action: "Schedule for removal",
  },
  low: {
    label: "Low priority",
    action: "Routine review",
  },
  pending: {
    label: "AI pending",
    action: "Awaiting classification",
  },
  not_applicable: {
    label: "Not applicable",
    action: "No graffiti detected",
  },
};

const REVIEW_OPTIONS = {
  surface_type: [
    "private_fence",
    "temporary_hoarding",
    "commercial_shopfront",
    "public_signage",
    "heritage_building",
    "public_monument",
    "community_facility",
    "fence",
    "shopfront",
    "wall_or_hoarding",
    "pavement_or_footpath",
    "other",
    "unknown",
  ],
  tag_category: [
    "tag",
    "stencil",
    "mural",
    "offensive_content",
    "other",
    "unknown",
  ],
  location_type: [
    "laneway",
    "rear_wall",
    "side_street",
    "main_street",
    "school_zone",
    "transport_hub",
    "unknown",
  ],
  size_category: ["small", "medium", "large"],
};

function formatCategory(value) {
  if (!value) {
    return "Not available";
  }

  return String(value)
    .replaceAll("_", " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function getPriority(classification) {
  if (!classification) {
    return "pending";
  }

  if (classification.graffiti_detected === false) {
    return "not_applicable";
  }

  const score = Number(classification?.harm_score);

  if (!Number.isFinite(score)) {
    return "pending";
  }

  if (score >= 11) {
    return "high";
  }

  if (score >= 6) {
    return "medium";
  }

  return "low";
}

function PriorityBadge({ classification }) {
  const priority = getPriority(classification);
  const information = PRIORITY_INFORMATION[priority];

  return (
    <span className={`priority-badge priority-${priority}`}>
      <span className="priority-dot" />
      {information.label}
      {classification?.harm_score != null && (
        <strong>{classification.harm_score}/15</strong>
      )}
    </span>
  );
}

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

function CouncilDashboard({ session, onSignOut }) {
  const [reports, setReports] = useState([]);
  const [selectedReport, setSelectedReport] = useState(null);
  const [classification, setClassification] = useState(null);
  const [classificationLoading, setClassificationLoading] =
    useState(false);
  const [classificationError, setClassificationError] =
    useState("");
  const [classificationsByReport, setClassificationsByReport] =
    useState({});

  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [filter, setFilter] = useState("all");
  const [search, setSearch] = useState("");
  const [sort, setSort] = useState("newest");
  const [priorityFilter, setPriorityFilter] = useState("all");
  const [view, setView] = useState("list");
  const [analyticsRange, setAnalyticsRange] = useState(30);

  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [updating, setUpdating] = useState(false);

  const [error, setError] = useState(null);
  const [connectionWarning, setConnectionWarning] = useState("");
  const [message, setMessage] = useState("");
  const [lastUpdated, setLastUpdated] = useState(null);
  const reportsRequestInProgress = useRef(false);
  const retryTimeout = useRef(null);
  const classificationsRef = useRef({});
  const [reviewForm, setReviewForm] = useState({
    surface_type: "unknown",
    tag_category: "unknown",
    location_type: "unknown",
    size_category: "medium",
    reviewed_by: session?.user?.email || "Council staff",
    review_notes: "",
  });
  const [reviewSaving, setReviewSaving] = useState(false);
  const [reviewError, setReviewError] = useState("");
  const [reviewMessage, setReviewMessage] = useState("");

  async function fetchReports(quiet = false) {
    if (reportsRequestInProgress.current) {
      return;
    }

    reportsRequestInProgress.current = true;

    if (quiet) {
      setRefreshing(true);
    } else {
      setLoading(true);
    }

    try {
      const response = await fetch(`${API_BASE}/reports/`, {
        headers: {
          Authorization: `Bearer ${session.access_token}`,
        },
      });

      if (!response.ok) {
        throw new Error(`Server returned ${response.status}`);
      }

      const data = await response.json();
      setReports(data);
      setLoading(false);
      await fetchReportClassifications(data);
      setLastUpdated(new Date());
      setError(null);
      setConnectionWarning("");

      if (retryTimeout.current) {
        window.clearTimeout(retryTimeout.current);
        retryTimeout.current = null;
      }
    } catch (requestError) {
      if (quiet || reports.length > 0) {
        setConnectionWarning(
          "The backend is busy processing AI results. Retrying automatically.",
        );
      } else {
        setError(requestError.message);
      }

      if (!retryTimeout.current) {
        retryTimeout.current = window.setTimeout(() => {
          retryTimeout.current = null;
          fetchReports(true);
        }, 15000);
      }
    } finally {
      reportsRequestInProgress.current = false;
      setLoading(false);
      setRefreshing(false);
    }
  }

  async function fetchReportClassifications(reportList) {
    const existingClassifications = classificationsRef.current;
    const pendingReports = reportList.filter(
      (report) => !existingClassifications[report.id],
    );
    const newEntries = {};

    for (const report of pendingReports) {
      try {
        const response = await fetch(
          `${API_BASE}/classifications/${report.id}/latest`,
          {
            headers: {
              Authorization: `Bearer ${session.access_token}`,
            },
          },
        );

        if (response.status === 404) {
          newEntries[report.id] = null;
          continue;
        }

        if (!response.ok) {
          throw new Error(`Server returned ${response.status}`);
        }

        newEntries[report.id] = await response.json();
      } catch (requestError) {
        console.error(
          `Could not load classification for report ${report.id}:`,
          requestError,
        );
      }
    }

    setClassificationsByReport((current) => ({
      ...current,
      ...newEntries,
    }));
  }

  async function fetchClassification(reportId) {
    setClassificationLoading(true);
    setClassificationError("");
    setClassification(null);

    try {
      const response = await fetch(
        `${API_BASE}/classifications/${reportId}/latest`,
        {
          headers: {
            Authorization: `Bearer ${session.access_token}`,
          },
        },
      );

      if (response.status === 404) {
        setClassificationError(
          "AI analysis is currently pending. Results will appear automatically.",
        );
        return;
      }

      if (!response.ok) {
        throw new Error(`Server returned ${response.status}`);
      }

      const data = await response.json();
      setClassification(data);
      setClassificationsByReport((current) => ({
        ...current,
        [reportId]: data,
      }));
    } catch (requestError) {
      setClassificationError(requestError.message);
    } finally {
      setClassificationLoading(false);
    }
  }

  async function classifySelectedReport() {
    if (!selectedReport) {
      return;
    }

    setClassificationLoading(true);
    setClassificationError("");

    try {
      const response = await fetch(
        `${API_BASE}/classifications/${selectedReport.id}/classify`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${session.access_token}`,
          },
        },
      );

      if (!response.ok) {
        const errorData = await response.json().catch(() => null);

        throw new Error(
          errorData?.detail ||
            `Server returned ${response.status}`,
        );
      }

      const data = await response.json();
      setClassification(data);
      setClassificationsByReport((current) => ({
        ...current,
        [selectedReport.id]: data,
      }));
      setMessage(
        `Report #${selectedReport.id} was classified successfully.`,
      );
    } catch (requestError) {
      setClassificationError(requestError.message);
    } finally {
      setClassificationLoading(false);
    }
  }

  async function submitManualReview(event) {
    event.preventDefault();

    if (!selectedReport || !classification) {
      return;
    }

    setReviewSaving(true);
    setReviewError("");
    setReviewMessage("");

    try {
      const response = await fetch(
        `${API_BASE}/classifications/${selectedReport.id}/review`,
        {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${session.access_token}`,
          },
          body: JSON.stringify(reviewForm),
        },
      );

      if (!response.ok) {
        const errorData = await response.json().catch(() => null);
        throw new Error(
          errorData?.detail || `Server returned ${response.status}`,
        );
      }

      const updatedClassification = await response.json();
      setClassification(updatedClassification);
      setClassificationsByReport((current) => ({
        ...current,
        [selectedReport.id]: updatedClassification,
      }));
      setReviewMessage(
        "Review saved. The harm score and council priority have been recalculated.",
      );
      setMessage(`Review saved for report #${selectedReport.id}.`);
    } catch (requestError) {
      setReviewError(requestError.message);
    } finally {
      setReviewSaving(false);
    }
  }

  useEffect(() => {
    classificationsRef.current = classificationsByReport;
  }, [classificationsByReport]);

  useEffect(() => {
    fetchReports();

    // Refresh the dashboard automatically so new reports and completed
    // AI classifications appear without a manual page refresh.
    const refreshInterval = window.setInterval(() => {
      fetchReports(true);
    }, 60000);

    return () => {
      window.clearInterval(refreshInterval);

      if (retryTimeout.current) {
        window.clearTimeout(retryTimeout.current);
      }
    };
  }, []);

  useEffect(() => {
    if (!selectedReport) {
      setClassification(null);
      setClassificationError("");
      return;
    }

    fetchClassification(selectedReport.id);
  }, [selectedReport?.id]);

  useEffect(() => {
    if (!classification) {
      return;
    }

    setReviewForm({
      surface_type: classification.surface_type || "unknown",
      tag_category: classification.tag_category || "unknown",
      location_type: classification.location_type || "unknown",
      size_category: classification.size_category || "medium",
      reviewed_by:
        classification.reviewed_by ||
        session?.user?.email ||
        "Council staff",
      review_notes: classification.review_notes || "",
    });
    setReviewError("");
    setReviewMessage("");
  }, [classification?.id, selectedReport?.id]);

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
        if (priorityFilter === "all") {
          return true;
        }

        return (
          getPriority(classificationsByReport[report.id]) ===
          priorityFilter
        );
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
        const firstScore = Number(
          classificationsByReport[firstReport.id]?.harm_score ?? -1,
        );
        const secondScore = Number(
          classificationsByReport[secondReport.id]?.harm_score ?? -1,
        );

        if (sort === "priority") {
          return secondScore - firstScore;
        }

        const firstDate = new Date(firstReport.submitted_at);
        const secondDate = new Date(secondReport.submitted_at);

        if (sort === "oldest") {
          return firstDate - secondDate;
        }

        return secondDate - firstDate;
      });
  }, [
    reports,
    classificationsByReport,
    filter,
    priorityFilter,
    search,
    sort,
  ]);

  const priorityCounts = useMemo(() => {
    const counts = {
      high: 0,
      medium: 0,
      low: 0,
      pending: 0,
      not_applicable: 0,
    };

    reports.forEach((report) => {
      const priority = getPriority(
        classificationsByReport[report.id],
      );
      counts[priority] += 1;
    });

    return counts;
  }, [reports, classificationsByReport]);

  const activityChartData = useMemo(() => {
    const days = [];
    const totalsByDate = new Map();

    for (let offset = analyticsRange - 1; offset >= 0; offset -= 1) {
      const date = new Date();
      date.setHours(0, 0, 0, 0);
      date.setDate(date.getDate() - offset);

      const key = [
        date.getFullYear(),
        String(date.getMonth() + 1).padStart(2, "0"),
        String(date.getDate()).padStart(2, "0"),
      ].join("-");

      totalsByDate.set(key, 0);
      days.push({ key, date });
    }

    reports.forEach((report) => {
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

    return days.map(({ key, date }, index) => ({
      label:
        analyticsRange === 7
          ? new Intl.DateTimeFormat("en-AU", {
              weekday: "short",
            }).format(date)
          : index % (analyticsRange === 90 ? 10 : 4) === 0
            ? new Intl.DateTimeFormat("en-AU", {
                day: "numeric",
                month: "short",
              }).format(date)
            : "",
      reports: totalsByDate.get(key),
    }));
  }, [reports, analyticsRange]);

  const priorityChartData = useMemo(
    () => [
      { name: "High", reports: priorityCounts.high, colour: "#fb7185" },
      { name: "Medium", reports: priorityCounts.medium, colour: "#fbbf24" },
      { name: "Low", reports: priorityCounts.low, colour: "#34d399" },
      { name: "Pending", reports: priorityCounts.pending, colour: "#94a3b8" },
    ],
    [priorityCounts],
  );

  const harmBandData = useMemo(() => {
    const bands = [
      { name: "Low 1–5", reports: 0, colour: "#34d399" },
      { name: "Medium 6–10", reports: 0, colour: "#fbbf24" },
      { name: "High 11–15", reports: 0, colour: "#fb7185" },
    ];

    reports.forEach((report) => {
      const score = Number(
        classificationsByReport[report.id]?.harm_score,
      );

      if (!Number.isFinite(score) || score <= 0) {
        return;
      }

      if (score >= 11) {
        bands[2].reports += 1;
      } else if (score >= 6) {
        bands[1].reports += 1;
      } else {
        bands[0].reports += 1;
      }
    });

    return bands;
  }, [reports, classificationsByReport]);

  const aiInsights = useMemo(() => {
    const classifications = reports
      .map((report) => classificationsByReport[report.id])
      .filter(Boolean);

    const scored = classifications.filter((item) =>
      Number.isFinite(Number(item.harm_score)),
    );

    const totalScore = scored.reduce(
      (sum, item) => sum + Number(item.harm_score),
      0,
    );

    const offensive = classifications.filter((item) =>
      item.detections?.some(
        (detection) => detection.offensive_content_detected === true,
      ),
    ).length;

    return {
      classified: classifications.length,
      coverage: reports.length
        ? Math.round((classifications.length / reports.length) * 100)
        : 0,
      averageHarm: scored.length
        ? (totalScore / scored.length).toFixed(1)
        : "0.0",
      review: classifications.filter(
        (item) => item.manual_review_required,
      ).length,
      offensive,
    };
  }, [reports, classificationsByReport]);

  const immediateRemovalReports = useMemo(() => {
    return reports
      .filter((report) => report.status !== "resolved")
      .filter(
        (report) =>
          getPriority(classificationsByReport[report.id]) ===
          "high",
      )
      .sort(
        (firstReport, secondReport) =>
          Number(
            classificationsByReport[secondReport.id]?.harm_score ?? 0,
          ) -
          Number(
            classificationsByReport[firstReport.id]?.harm_score ?? 0,
          ),
      );
  }, [reports, classificationsByReport]);

  async function updateStatus(reportId, newStatus) {
    setUpdating(true);
    setMessage("");

    try {
      const response = await fetch(
        `${API_BASE}/reports/${reportId}/status?status=${newStatus}`,
        {
          method: "PATCH",
          headers: {
            Authorization: `Bearer ${session.access_token}`,
          },
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

  const bestStyleDetection =
    classification?.detections?.length > 0
      ? classification.detections.reduce(
          (bestDetection, currentDetection) =>
            Number(currentDetection.confidence || 0) >
            Number(bestDetection.confidence || 0)
              ? currentDetection
              : bestDetection,
        )
      : null;

  const styleCategory =
    bestStyleDetection?.style_category ||
    classification?.tag_category ||
    "unknown";

  const styleConfidence =
    bestStyleDetection?.style_confidence;

  const offensiveCategory =
    bestStyleDetection?.offensive_category ||
    (classification?.tag_category === "offensive_content"
      ? "offensive"
      : "unknown");

  const offensiveConfidence =
    bestStyleDetection?.offensive_confidence;

  const surfaceCategory =
    classification?.surface_type ||
    bestStyleDetection?.surface_category ||
    "unknown";

  const surfaceConfidence =
    bestStyleDetection?.surface_confidence;

  const locationCategory =
    classification?.location_type ||
    bestStyleDetection?.location_type ||
    "unknown";

  const locationConfidence =
    bestStyleDetection?.location_confidence;

  const locationAccepted =
    bestStyleDetection?.location_prediction_accepted === true;

  const offensiveDetected =
    bestStyleDetection?.offensive_content_detected === true ||
    offensiveCategory === "offensive";

  const harmScore = Number(classification?.harm_score || 0);
  const harmPercentage = Math.max(
    0,
    Math.min(100, (harmScore / 15) * 100),
  );

  const harmTone =
    harmScore >= 11
      ? "high"
      : harmScore >= 6
        ? "medium"
        : "low";

  const recurrenceDetails =
    classification?.harm_breakdown?.recurrence ||
    bestStyleDetection?.recurrence ||
    null;

  const occurrenceCount = Number(
    recurrenceDetails?.occurrence_count || 1,
  );

  const similarReportCount = Number(
    recurrenceDetails?.similar_report_count || 0,
  );

  const recurrenceRadius = Number(
    recurrenceDetails?.radius_metres || 50,
  );

  const matchedReports = Array.isArray(
    recurrenceDetails?.matched_reports,
  )
    ? recurrenceDetails.matched_reports
    : [];

  const repeatedGraffitiDetected =
    recurrenceDetails?.repeated_graffiti_detected === true &&
    similarReportCount > 0;

  const recurrenceWarningTone =
    occurrenceCount >= 3 ? "high" : "medium";

  const harmBreakdown =
    classification?.harm_breakdown || {};

  const scoreAllocation = [
    {
      key: "content",
      label: "Content type",
      maximum: 15,
      className: "allocation-content",
    },
    {
      key: "surface_type",
      label: "Surface type",
      maximum: 10,
      className: "allocation-surface",
    },
    {
      key: "location_visibility",
      label: "Location visibility",
      maximum: 10,
      className: "allocation-location",
    },
    {
      key: "size_coverage",
      label: "Size and coverage",
      maximum: 5,
      className: "allocation-size",
    },
    {
      key: "recurrence",
      label: "Recurrence",
      maximum: 10,
      className: "allocation-recurrence",
    },
  ].map((item) => {
    const breakdownItem = harmBreakdown[item.key] || {};
    const awarded = Number(breakdownItem.weighted || 0);

    return {
      ...item,
      awarded,
      category: breakdownItem.category,
      percentage: Math.max(
        0,
        Math.min(100, (awarded / item.maximum) * 100),
      ),
    };
  });

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
            <span className="brand-mark">
              <span className="brand-mark">AU</span>
            </span>

            <div className="brand-text">
              <strong>UrbanEyes</strong>
              <small>Council Administration Portal</small>
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

        <div className="sidebar-account">
          <p className="sidebar-section-label">
            SIGNED IN AS
          </p>

          <div className="logged-in-user">
            <div className="logged-in-avatar">
              {session?.user?.email
                ?.charAt(0)
                .toUpperCase() || "C"}
            </div>

            <div className="logged-in-details">
              <strong>
                {session?.user?.user_metadata?.full_name ||
                  session?.user?.user_metadata?.name ||
                  "Council Staff"}
              </strong>

              <span>{session?.user?.email}</span>

              <small>Authorised council user</small>
            </div>
          </div>
        </div>

        <div className="sidebar-bottom">
          <button
            className="sidebar-signout"
            onClick={onSignOut}
          >
            <span>↪</span>
            Sign out
          </button>
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <div>
            <p className="eyebrow">OPERATIONS OVERVIEW</p>

            <h1>Welcome to the Operations Dashboard</h1>

            <p className="subtitle">
              Keep Australia Beautiful
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

        {/* National command-centre overview. This uses the same report data
            and selection handler as the report list below. */}
        <section className="national-command-centre">
          <div className="command-centre-heading">
            <div>
              <span className="command-kicker">
                <i /> NATIONAL OPERATIONS MAP
              </span>
              <h2>UrbenEyes 🇦🇺 🦘</h2>
              <p>
                Live council reports, AI risk signals and removal priorities
                in one operational view.
              </p>
            </div>

            <div className="command-centre-actions">
              <span className="command-live-pill">
                <i /> Live
              </span>
              <button
                type="button"
                onClick={() => {
                  setView("map");
                  document
                    .querySelector(".workspace")
                    ?.scrollIntoView({ behavior: "smooth" });
                }}
              >
                Open report map
              </button>
            </div>
          </div>

          <div className="command-layout">
            <aside className="command-column command-column-left">
              <article className="command-metric command-metric-cyan">
                <span>Total reports</span>
                <strong>{reportCounts.all}</strong>
                <small>{reportCounts.new} awaiting review</small>
              </article>

              <article className="command-metric command-metric-purple">
                <span>AI coverage</span>
                <strong>{aiInsights.coverage}%</strong>
                <small>{aiInsights.classified} reports classified</small>
              </article>

              <article className="command-mini-chart">
                <div>
                  <span>Workflow status</span>
                  <small>Live distribution</small>
                </div>
                <div className="command-chart-area">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={statusChartData}
                        dataKey="value"
                        nameKey="name"
                        cx="50%"
                        cy="50%"
                        innerRadius={33}
                        outerRadius={49}
                        paddingAngle={5}
                        stroke="none"
                      >
                        {statusChartData.map((entry) => (
                          <Cell key={entry.name} fill={entry.colour} />
                        ))}
                      </Pie>
                      <Tooltip
                        contentStyle={{
                          background: "#0a111d",
                          border: "1px solid #26364c",
                          borderRadius: "10px",
                          color: "#ffffff",
                        }}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
                <div className="command-chart-legend">
                  {statusChartData.map((item) => (
                    <span key={item.name}>
                      <i style={{ background: item.colour }} />
                      {item.name} <strong>{item.value}</strong>
                    </span>
                  ))}
                </div>
              </article>
            </aside>

            <div className="australia-map-panel">
              <div className="map-panel-label">
                <span>AUSTRALIA</span>
                <strong>{reports.length} active data points</strong>
              </div>

              <MapContainer
                className="australia-map"
                center={AUSTRALIA_CENTER}
                zoom={4}
                minZoom={3}
                scrollWheelZoom
                style={{ width: "100%", height: "100%" }}
              >
                <TileLayer
                  url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
                  attribution="Tiles &copy; Esri"
                />

                {reports.map((report) => {
                  const reportClassification =
                    classificationsByReport[report.id];
                  const priority = getPriority(reportClassification);

                  return (
                    <CircleMarker
                      key={`national-${report.id}`}
                      center={[report.latitude, report.longitude]}
                      radius={priority === "high" ? 10 : 7}
                      pathOptions={{
                        color: "#ffffff",
                        weight: 2,
                        fillColor: PRIORITY_COLOURS[priority],
                        fillOpacity: 0.95,
                      }}
                      eventHandlers={{
                        click: () => setSelectedReport(report),
                      }}
                    >
                      <Popup>
                        <strong>Report #{report.id}</strong>
                        <br />
                        {PRIORITY_INFORMATION[priority].label}
                        <br />
                        <button
                          className="popup-button"
                          onClick={() => setSelectedReport(report)}
                        >
                          View report
                        </button>
                      </Popup>
                    </CircleMarker>
                  );
                })}
              </MapContainer>

              <div className="national-map-legend">
                {[
                  ["high", "High"],
                  ["medium", "Medium"],
                  ["low", "Low"],
                  ["pending", "AI pending"],
                ].map(([priority, label]) => (
                  <span key={priority}>
                    <i style={{ background: PRIORITY_COLOURS[priority] }} />
                    {label}
                  </span>
                ))}
              </div>
            </div>

            <aside className="command-column command-column-right">
              <article className="threat-monitor">
                <div className="threat-monitor-heading">
                  <div>
                    <span>AI risk monitor</span>
                    <small>Priority intelligence</small>
                  </div>
                  <b>{priorityCounts.high}</b>
                </div>

                <div className="risk-bars">
                  {[
                    ["High", priorityCounts.high, "high"],
                    ["Medium", priorityCounts.medium, "medium"],
                    ["Low", priorityCounts.low, "low"],
                  ].map(([label, value, priority]) => {
                    const percentage = reportCounts.all
                      ? Math.max(5, (value / reportCounts.all) * 100)
                      : 0;

                    return (
                      <div className="risk-bar" key={priority}>
                        <span>{label}</span>
                        <div>
                          <i
                            style={{
                              width: `${percentage}%`,
                              background: PRIORITY_COLOURS[priority],
                            }}
                          />
                        </div>
                        <strong>{value}</strong>
                      </div>
                    );
                  })}
                </div>
              </article>

              <article className="command-metric command-metric-red">
                <span>Content alerts</span>
                <strong>{aiInsights.offensive}</strong>
                <small>Potential offensive content</small>
              </article>

              <article className="command-alert-list">
                <div className="command-alert-heading">
                  <span>Priority queue</span>
                  <button
                    onClick={() => {
                      setPriorityFilter("high");
                      setSort("priority");
                      setView("list");
                    }}
                  >
                    View all
                  </button>
                </div>

                {immediateRemovalReports.length === 0 ? (
                  <p className="command-alert-empty">
                    No immediate removals currently required.
                  </p>
                ) : (
                  immediateRemovalReports.slice(0, 3).map((report) => (
                    <button
                      className="command-alert-row"
                      key={`command-alert-${report.id}`}
                      onClick={() => setSelectedReport(report)}
                    >
                      <span>#{report.id}</span>
                      <div>
                        <strong>
                          {report.notes || "Graffiti report"}
                        </strong>
                        <small>{formatDate(report.submitted_at)}</small>
                      </div>
                      <b>
                        {classificationsByReport[report.id]?.harm_score || 0}
                      </b>
                    </button>
                  ))
                )}
              </article>
            </aside>
          </div>
        </section>

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
                <strong>{priorityCounts.high}</strong>
                <span>High-priority reports</span>
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

        <section className="priority-overview">
          <div className="priority-overview-heading">
            <div>
              <p className="eyebrow">AI PRIORITY QUEUE</p>
              <h2>Removal priorities</h2>
              <span>
                Priority is calculated from the saved 1–15 harm score.
              </span>
            </div>

            <button
              className="priority-view-all"
              onClick={() => {
                setPriorityFilter("all");
                setSort("priority");
                setView("list");
              }}
            >
              View all by priority
            </button>
          </div>

          <div className="priority-summary-grid">
            {Object.entries(PRIORITY_INFORMATION).map(
              ([priority, information]) => (
                <button
                  key={priority}
                  className={`priority-summary-card priority-summary-${priority} ${
                    priorityFilter === priority ? "selected" : ""
                  }`}
                  onClick={() => {
                    setPriorityFilter(priority);
                    setSort("priority");
                    setView("list");
                  }}
                >
                  <span>{information.label}</span>
                  <strong>{priorityCounts[priority]}</strong>
                  <small>{information.action}</small>
                </button>
              ),
            )}
          </div>

          <div className="urgent-queue">
            <div className="urgent-queue-heading">
              <div>
                <span className="urgent-icon">!</span>
                <div>
                  <h3>Immediate removal required</h3>
                  <p>Unresolved reports with a harm score of 11–15</p>
                </div>
              </div>

              <strong>{immediateRemovalReports.length}</strong>
            </div>

            {immediateRemovalReports.length === 0 ? (
              <div className="urgent-empty">
                No unresolved high-priority reports at this time.
              </div>
            ) : (
              <div className="urgent-report-list">
                {immediateRemovalReports.slice(0, 5).map((report) => {
                  const reportClassification =
                    classificationsByReport[report.id];

                  return (
                    <button
                      key={report.id}
                      className="urgent-report"
                      onClick={() => setSelectedReport(report)}
                    >
                      <span className="urgent-thumbnail">
                        {report.image_url ? (
                          <img src={report.image_url} alt="" />
                        ) : (
                          "▧"
                        )}
                      </span>

                      <span className="urgent-report-copy">
                        <strong>Report #{report.id}</strong>
                        <small>
                          {report.notes || "No description provided"}
                        </small>
                      </span>

                      <PriorityBadge
                        classification={reportClassification}
                      />

                      <span className="urgent-arrow">›</span>
                    </button>
                  );
                })}
              </div>
            )}
          </div>
        </section>

        {/* Live charts generated from report data */}
        <section className="analytics-section">
          <div className="analytics-heading">
            <div>
              <p className="eyebrow">REPORT ANALYTICS</p>
              <h2>Service trends</h2>
            </div>

            <div className="analytics-range" aria-label="Analytics time range">
              {[7, 30, 90].map((range) => (
                <button
                  key={range}
                  className={analyticsRange === range ? "active" : ""}
                  onClick={() => setAnalyticsRange(range)}
                >
                  {range}D
                </button>
              ))}
            </div>
          </div>

          <div className="analytics-kpi-grid">
            <article className="analytics-kpi kpi-blue">
              <span>AI coverage</span>
              <strong>{aiInsights.coverage}%</strong>
              <small>{aiInsights.classified} reports classified</small>
            </article>

            <article className="analytics-kpi kpi-purple">
              <span>Average harm</span>
              <strong>{aiInsights.averageHarm}<em>/15</em></strong>
              <small>Across scored reports</small>
            </article>

            <article className="analytics-kpi kpi-amber">
              <span>Manual reviews</span>
              <strong>{aiInsights.review}</strong>
              <small>Need council confirmation</small>
            </article>

            <article className="analytics-kpi kpi-red">
              <span>Content alerts</span>
              <strong>{aiInsights.offensive}</strong>
              <small>Potentially offensive</small>
            </article>
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
                  <p>Submissions during the last {analyticsRange} days</p>
                </div>

                <span className="chart-icon">▥</span>
              </div>

              <div className="chart-area">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart
                    data={activityChartData}
                    margin={{ top: 12, right: 8, left: -22, bottom: 0 }}
                  >
                    <defs>
                      <linearGradient id="reportsGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#38bdf8" stopOpacity={0.5} />
                        <stop offset="100%" stopColor="#2563eb" stopOpacity={0.02} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid
                      stroke="#17263a"
                      strokeDasharray="4 4"
                      vertical={false}
                    />

                    <XAxis
                      dataKey="label"
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

                    <Area
                      dataKey="reports"
                      name="Reports"
                      type="monotone"
                      stroke="#38bdf8"
                      strokeWidth={3}
                      fill="url(#reportsGradient)"
                      activeDot={{ r: 6, fill: "#ffffff", stroke: "#38bdf8" }}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </article>

            <article className="chart-card">
              <div className="chart-card-heading">
                <div>
                  <h3>Priority distribution</h3>
                  <p>AI-ranked council workload</p>
                </div>
                <span className="chart-icon">◆</span>
              </div>

              <div className="chart-area compact-chart">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={priorityChartData}
                    layout="vertical"
                    margin={{ top: 4, right: 18, left: 8, bottom: 0 }}
                  >
                    <CartesianGrid stroke="#17263a" strokeDasharray="4 4" horizontal={false} />
                    <XAxis type="number" allowDecimals={false} hide />
                    <YAxis
                      type="category"
                      dataKey="name"
                      width={62}
                      tick={{ fill: "#8fa1b8", fontSize: 11 }}
                      axisLine={false}
                      tickLine={false}
                    />
                    <Tooltip
                      cursor={{ fill: "rgba(255,255,255,0.03)" }}
                      contentStyle={{
                        background: "#091321",
                        border: "1px solid #22344d",
                        borderRadius: "10px",
                        color: "#f5f8ff",
                      }}
                    />
                    <Bar dataKey="reports" radius={[0, 8, 8, 0]} maxBarSize={24}>
                      {priorityChartData.map((entry) => (
                        <Cell key={entry.name} fill={entry.colour} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </article>

            <article className="chart-card chart-card-wide">
              <div className="chart-card-heading">
                <div>
                  <h3>Harm-score bands</h3>
                  <p>Classified reports grouped by severity</p>
                </div>
                <span className="chart-icon">▥</span>
              </div>

              <div className="chart-area compact-chart">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart
                    data={harmBandData}
                    margin={{ top: 10, right: 10, left: -20, bottom: 0 }}
                  >
                    <CartesianGrid stroke="#17263a" strokeDasharray="4 4" vertical={false} />
                    <XAxis
                      dataKey="name"
                      tick={{ fill: "#8fa1b8", fontSize: 11 }}
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
                      cursor={{ fill: "rgba(255,255,255,0.03)" }}
                      contentStyle={{
                        background: "#091321",
                        border: "1px solid #22344d",
                        borderRadius: "10px",
                        color: "#f5f8ff",
                      }}
                    />
                    <Bar dataKey="reports" radius={[8, 8, 0, 0]} maxBarSize={70}>
                      {harmBandData.map((entry) => (
                        <Cell key={entry.name} fill={entry.colour} />
                      ))}
                    </Bar>
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
                value={priorityFilter}
                onChange={(event) =>
                  setPriorityFilter(event.target.value)
                }
                aria-label="Filter reports by priority"
              >
                <option value="all">All priorities</option>
                <option value="high">High priority</option>
                <option value="medium">Medium priority</option>
                <option value="low">Low priority</option>
                <option value="pending">AI pending</option>
                <option value="not_applicable">
                  Not applicable
                </option>
              </select>

              <select
                value={sort}
                onChange={(event) =>
                  setSort(event.target.value)
                }
              >
                <option value="newest">Newest first</option>
                <option value="oldest">Oldest first</option>
                <option value="priority">Highest priority</option>
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
                  <span>Priority</span>
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

                    <PriorityBadge
                      classification={
                        classificationsByReport[report.id]
                      }
                    />

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
                <div className="detection-image-stage">
                  <img
                    src={selectedReport.image_url}
                    alt={`Graffiti report ${selectedReport.id}`}
                  />

                  {classification?.detections?.map(
                    (detection, index) => {
                      const box = detection.bbox;
                      const imageWidth =
                        detection.image_width;
                      const imageHeight =
                        detection.image_height;

                      if (
                        !box ||
                        !imageWidth ||
                        !imageHeight
                      ) {
                        return null;
                      }

                      const left =
                        (box.x1 / imageWidth) * 100;
                      const top =
                        (box.y1 / imageHeight) * 100;
                      const width =
                        ((box.x2 - box.x1) /
                          imageWidth) *
                        100;
                      const height =
                        ((box.y2 - box.y1) /
                          imageHeight) *
                        100;

                      return (
                        <div
                          className={`graffiti-box ${
                            detection.offensive_content_detected
                              ? "graffiti-box-offensive"
                              : ""
                          }`}
                          key={`${detection.confidence}-${index}`}
                          style={{
                            left: `${left}%`,
                            top: `${top}%`,
                            width: `${width}%`,
                            height: `${height}%`,
                          }}
                        >
                          <span>
                            {detection.offensive_content_detected
                              ? "Potentially offensive · "
                              : ""}
                            {detection.style_category
                              ? `${detection.style_category} · `
                              : "Graffiti · "}
                            {Math.round(detection.confidence * 100)}%
                          </span>
                        </div>
                      );
                    },
                  )}
                </div>
              ) : (
                <div className="no-image">
                  <span>▧</span>
                  No image available
                </div>
              )}
            </div>

            <div className="detail-section ai-section">
              <div className="detail-title">
                <span>AI graffiti analysis</span>

                {classification && (
                  <span
                    className={`severity-badge severity-${classification.severity_band?.toLowerCase()}`}
                  >
                    {classification.severity_band}
                  </span>
                )}
              </div>

              {classification && (
                <div className="detail-priority-row">
                  <span>Council priority</span>
                  <PriorityBadge classification={classification} />
                </div>
              )}

              {classificationLoading && (
                <div className="ai-loading">
                  Analysing report image...
                </div>
              )}

              {!classificationLoading &&
                classificationError && (
                  <div className="ai-empty">
                    <p>{classificationError}</p>

                    <button
                      type="button"
                      className="classify-button"
                      onClick={classifySelectedReport}
                    >
                      Run AI detection
                    </button>
                  </div>
                )}

              {!classificationLoading && classification && (
                <>
                  <div className={`harm-score-hero harm-tone-${harmTone}`}>
                    <div
                      className="harm-score-ring"
                      style={{
                        "--harm-progress": `${harmPercentage * 3.6}deg`,
                      }}
                    >
                      <div>
                        <strong>{harmScore}</strong>
                        <span>/15</span>
                      </div>
                    </div>

                    <div className="harm-score-copy">
                      <span>PRELIMINARY HARM SCORE</span>
                      <strong>
                        {classification.severity_band || "Pending"} priority
                      </strong>
                      <p>
                        AI recommendation based on detected content,
                        image coverage and the current scoring rules.
                      </p>
                    </div>
                  </div>

                  {repeatedGraffitiDetected && (
                    <div
                      className={`recurrence-warning recurrence-${recurrenceWarningTone}`}
                    >
                      <div className="recurrence-warning-icon">!</div>

                      <div className="recurrence-warning-content">
                        <div className="recurrence-warning-heading">
                          <div>
                            <span>RECURRENCE WARNING</span>
                            <strong>
                              Repeated graffiti detected nearby
                            </strong>
                          </div>

                          <div className="recurrence-count-badge">
                            Occurrence {occurrenceCount}
                          </div>
                        </div>

                        <p>
                          {similarReportCount} visually similar{" "}
                          {similarReportCount === 1
                            ? "report was"
                            : "reports were"}{" "}
                          detected within a{" "}
                          {recurrenceRadius}-metre radius.
                        </p>

                        {matchedReports.length > 0 && (
                          <div className="recurrence-matches">
                            {matchedReports.map((matchedReport) => (
                              <div
                                className="recurrence-match"
                                key={matchedReport.report_id}
                              >
                                <span>
                                  Report #{matchedReport.report_id}
                                </span>
                                <strong>
                                  {Number(
                                    matchedReport.distance_metres || 0,
                                  ).toFixed(1)}
                                  m away
                                </strong>
                              </div>
                            ))}
                          </div>
                        )}

                        <small>
                          This warning is based on image similarity
                          and location. Council staff should confirm
                          that the reports show the same graffiti.
                        </small>
                      </div>
                    </div>
                  )}

                  {classification.graffiti_detected && (
                    <div className="score-allocation-card">
                      <div className="score-allocation-header">
                        <div>
                          <span>HARM SCORE BREAKDOWN</span>
                          <strong>How the score was allocated</strong>
                        </div>

                        <div className="allocation-total">
                          <strong>{harmScore}</strong>
                          <span>/15 final score</span>
                        </div>
                      </div>

                      <div className="score-allocation-chart">
                        {scoreAllocation.map((item) => (
                          <div
                            className="allocation-row"
                            key={item.key}
                          >
                            <div className="allocation-row-heading">
                              <div>
                                <strong>{item.label}</strong>
                                <span>
                                  {item.category != null
                                    ? String(item.category).replaceAll(
                                        "_",
                                        " ",
                                      )
                                    : "Not available"}
                                </span>
                              </div>

                              <b>
                                {item.awarded}/{item.maximum}
                              </b>
                            </div>

                            <div className="allocation-track">
                              <span
                                className={item.className}
                                style={{
                                  width: `${item.percentage}%`,
                                }}
                              />
                            </div>
                          </div>
                        ))}
                      </div>

                      <p className="allocation-note">
                        Weighted category points are combined and
                        converted to the final harm score out of 15.
                      </p>
                    </div>
                  )}

                  <div className="ai-metrics">
                    <div className="ai-metric-card metric-detection">
                      <div className="metric-icon">◎</div>
                      <span>Graffiti</span>
                      <strong>
                        {classification.graffiti_detected
                          ? "Detected"
                          : "Not detected"}
                      </strong>
                    </div>

                    <div className="ai-metric-card metric-confidence">
                      <div className="metric-icon">%</div>
                      <span>Detection confidence</span>
                      <strong>
                        {Math.round(
                          Number(
                            classification.detection_confidence || 0,
                          ) * 100,
                        )}
                        %
                      </strong>
                      <div className="confidence-track">
                        <span
                          style={{
                            width: `${Math.round(
                              Number(
                                classification.detection_confidence || 0,
                              ) * 100,
                            )}%`,
                          }}
                        />
                      </div>
                    </div>

                    <div className="ai-metric-card metric-style">
                      <div className="metric-icon">✦</div>
                      <span>Graffiti style</span>
                      <strong>
                        {classification.graffiti_detected
                          ? styleCategory.replaceAll("_", " ")
                          : "Not applicable"}
                      </strong>
                    </div>

                    <div className="ai-metric-card metric-style-confidence">
                      <div className="metric-icon">%</div>
                      <span>Style confidence</span>
                      <strong>
                        {classification.graffiti_detected &&
                        styleConfidence != null
                          ? `${Math.round(
                              Number(styleConfidence) * 100,
                            )}%`
                          : "Not available"}
                      </strong>
                      {styleConfidence != null && (
                        <div className="confidence-track">
                          <span
                            style={{
                              width: `${Math.round(
                                Number(styleConfidence) * 100,
                              )}%`,
                            }}
                          />
                        </div>
                      )}
                    </div>

                    <div
                      className={`ai-metric-card metric-offensive ${
                        offensiveDetected ? "is-offensive" : "is-clear"
                      }`}
                    >
                      <div className="metric-icon">
                        {offensiveDetected ? "!" : "✓"}
                      </div>
                      <span>Content safety</span>
                      <strong>
                        {classification.graffiti_detected
                          ? offensiveCategory.replaceAll("_", " ")
                          : "Not applicable"}
                      </strong>
                    </div>

                    <div
                      className={`ai-metric-card metric-offensive-confidence ${
                        offensiveDetected ? "is-offensive" : "is-clear"
                      }`}
                    >
                      <div className="metric-icon">%</div>
                      <span>Content confidence</span>
                      <strong>
                        {classification.graffiti_detected &&
                        offensiveConfidence != null
                          ? `${Math.round(
                              Number(offensiveConfidence) * 100,
                            )}%`
                          : "Not available"}
                      </strong>
                      {offensiveConfidence != null && (
                        <div className="confidence-track">
                          <span
                            style={{
                              width: `${Math.round(
                                Number(offensiveConfidence) * 100,
                              )}%`,
                            }}
                          />
                        </div>
                      )}
                    </div>

                    <div className="ai-metric-card metric-surface">
                      <div className="metric-icon">▧</div>
                      <span>Surface type</span>
                      <strong>
                        {classification.graffiti_detected
                          ? surfaceCategory.replaceAll("_", " ")
                          : "Not applicable"}
                      </strong>
                    </div>

                    <div className="ai-metric-card metric-surface-confidence">
                      <div className="metric-icon">%</div>
                      <span>Surface confidence</span>
                      <strong>
                        {classification.graffiti_detected &&
                        surfaceConfidence != null
                          ? `${Math.round(
                              Number(surfaceConfidence) * 100,
                            )}%`
                          : "Not available"}
                      </strong>
                      {surfaceConfidence != null && (
                        <div className="confidence-track">
                          <span
                            style={{
                              width: `${Math.round(
                                Number(surfaceConfidence) * 100,
                              )}%`,
                            }}
                          />
                        </div>
                      )}
                    </div>

                    <div
                      className={`ai-metric-card metric-location ${
                        locationAccepted ? "is-accepted" : "needs-review"
                      }`}
                    >
                      <div className="metric-icon">⌖</div>
                      <span>Area type · Map data</span>
                      <strong>
                        {classification.graffiti_detected
                          ? locationCategory.replaceAll("_", " ")
                          : "Not applicable"}
                      </strong>

                      {classification.graffiti_detected && (
                        <small className="metric-supporting-text">
                          {locationConfidence != null
                            ? `${Math.round(
                                Number(locationConfidence) * 100,
                              )}% confidence · ${
                                locationAccepted
                                  ? "Map verified"
                                  : "Review location"
                              }`
                            : "Map confidence unavailable"}
                        </small>
                      )}
                    </div>

                    <div className="ai-metric-card metric-size">
                      <div className="metric-icon">↗</div>
                      <span>Estimated size</span>
                      <strong>
                        {classification.size_category
                          ?.replaceAll("_", " ") ||
                          "Unknown"}
                      </strong>
                    </div>

                    <div className="ai-metric-card metric-review">
                      <div className="metric-icon">
                        {classification.manual_review_required ? "!" : "✓"}
                      </div>
                      <span>Review status</span>
                      <strong>
                        {classification.manual_review_required
                          ? "Council review"
                          : "AI checks passed"}
                      </strong>
                    </div>
                  </div>

                  {offensiveDetected && (
                    <div className="offensive-alert">
                      <span>!</span>
                      <div>
                        <strong>Potentially offensive content</strong>
                        <p>
                          The experimental model flagged this image.
                          Treat this as a recommendation and confirm it
                          manually before prioritising removal.
                        </p>
                      </div>
                    </div>
                  )}

                  {classification.manual_review_required && (
                    <div className="manual-review-warning">
                      <span>!</span>

                      <div>
                        <strong>Manual review required</strong>

                        <p>
                          One or more AI results have low
                          confidence. Council staff should confirm
                          the detection, style and content-safety
                          recommendation before making a decision.
                        </p>
                      </div>
                    </div>
                  )}

                  <div className="council-review-card">
                    <div className="council-review-header">
                      <div>
                        <span>COUNCIL VERIFICATION</span>
                        <strong>Review and correct the AI result</strong>
                        <p>
                          The original AI result is retained for auditing.
                          Saving corrections recalculates the harm score and
                          dashboard priority.
                        </p>
                      </div>

                      <span
                        className={`review-state-badge ${
                          classification.manually_reviewed
                            ? "is-reviewed"
                            : "needs-review"
                        }`}
                      >
                        {classification.manually_reviewed
                          ? "✓ Reviewed"
                          : "Awaiting review"}
                      </span>
                    </div>

                    <div className="ai-review-comparison">
                      <div className="comparison-heading">
                        <span>Category</span>
                        <span>Original AI result</span>
                        <span>Current result</span>
                      </div>

                      {[
                        ["Surface", "ai_surface_type", "surface_type"],
                        ["Graffiti type", "ai_tag_category", "tag_category"],
                        ["Area type", "ai_location_type", "location_type"],
                        ["Estimated size", "ai_size_category", "size_category"],
                      ].map(([label, aiKey, currentKey]) => (
                        <div className="comparison-row" key={currentKey}>
                          <strong>{label}</strong>
                          <span>
                            {formatCategory(
                              classification[aiKey] ||
                                classification[currentKey],
                            )}
                          </span>
                          <span
                            className={
                              classification.manually_reviewed &&
                              classification[aiKey] &&
                              classification[aiKey] !==
                                classification[currentKey]
                                ? "corrected-value"
                                : ""
                            }
                          >
                            {formatCategory(classification[currentKey])}
                          </span>
                        </div>
                      ))}
                    </div>

                    <form
                      className="council-review-form"
                      onSubmit={submitManualReview}
                    >
                      <div className="review-form-grid">
                        {[
                          ["Surface type", "surface_type"],
                          ["Graffiti type", "tag_category"],
                          ["Area type", "location_type"],
                          ["Estimated size", "size_category"],
                        ].map(([label, field]) => (
                          <label className="review-field" key={field}>
                            <span>{label}</span>
                            <select
                              value={reviewForm[field]}
                              onChange={(event) =>
                                setReviewForm((current) => ({
                                  ...current,
                                  [field]: event.target.value,
                                }))
                              }
                            >
                              {REVIEW_OPTIONS[field].map((option) => (
                                <option value={option} key={option}>
                                  {formatCategory(option)}
                                </option>
                              ))}
                            </select>
                          </label>
                        ))}
                      </div>

                      <label className="review-field">
                        <span>Reviewed by</span>
                        <input
                          type="text"
                          value={reviewForm.reviewed_by}
                          required
                          onChange={(event) =>
                            setReviewForm((current) => ({
                              ...current,
                              reviewed_by: event.target.value,
                            }))
                          }
                        />
                      </label>

                      <label className="review-field">
                        <span>Review notes</span>
                        <textarea
                          rows="3"
                          value={reviewForm.review_notes}
                          placeholder="Explain any correction or verification decision."
                          onChange={(event) =>
                            setReviewForm((current) => ({
                              ...current,
                              review_notes: event.target.value,
                            }))
                          }
                        />
                      </label>

                      {reviewError && (
                        <div className="review-feedback review-error">
                          {reviewError}
                        </div>
                      )}

                      {reviewMessage && (
                        <div className="review-feedback review-success">
                          {reviewMessage}
                        </div>
                      )}

                      {classification.manually_reviewed && (
                        <div className="review-audit-line">
                          Last reviewed by {classification.reviewed_by || "Council staff"}
                          {classification.reviewed_at
                            ? ` on ${formatDate(classification.reviewed_at)}`
                            : ""}
                        </div>
                      )}

                      <button
                        type="submit"
                        className="save-review-button"
                        disabled={reviewSaving}
                      >
                        {reviewSaving
                          ? "Saving review..."
                          : classification.manually_reviewed
                            ? "Update council review"
                            : "Confirm council review"}
                      </button>
                    </form>
                  </div>

                  <p className="model-information">
                    {classification.detections?.length || 0}{" "}
                    bounding box(es) ·{" "}
                    {classification.model_version}
                  </p>

                  <button
                    type="button"
                    className="classify-button secondary"
                    onClick={classifySelectedReport}
                  >
                    Run detection again
                  </button>
                </>
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

      {(connectionWarning || message) && (
        <div
          className={`toast ${
            connectionWarning || message.startsWith("Update failed")
              ? "error"
              : ""
          }`}
        >
          {connectionWarning || message}
        </div>
      )}
    </div>
  );
}

function CouncilLogin() {
  const [session, setSession] = useState(null);
  const [checkingSession, setCheckingSession] = useState(true);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [loginError, setLoginError] = useState("");

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => {
      setSession(data.session);
      setCheckingSession(false);
    });

    const { data: listener } = supabase.auth.onAuthStateChange(
      (_event, nextSession) => {
        setSession(nextSession);
        setCheckingSession(false);
      },
    );

    return () => listener.subscription.unsubscribe();
  }, []);

  const isCouncilUser =
    session?.user?.app_metadata?.role === "council";

  useEffect(() => {
    if (session && !isCouncilUser) {
      setLoginError(
        "This account does not have permission to use the council portal.",
      );
      supabase.auth.signOut();
    }
  }, [session, isCouncilUser]);

  async function handleLogin(event) {
    event.preventDefault();
    setSubmitting(true);
    setLoginError("");

    const { data, error } = await supabase.auth.signInWithPassword({
      email: email.trim(),
      password,
    });

    if (error) {
      setLoginError("The email address or password is incorrect.");
      setSubmitting(false);
      return;
    }

    if (data.user?.app_metadata?.role !== "council") {
      await supabase.auth.signOut();
      setLoginError(
        "This account does not have permission to use the council portal.",
      );
      setSubmitting(false);
      return;
    }

    setSubmitting(false);
  }

  async function handleSignOut() {
    await supabase.auth.signOut();
    setEmail("");
    setPassword("");
  }

  if (checkingSession) {
    return (
      <main className="login-page">
        <div className="login-loader" aria-label="Checking session" />
      </main>
    );
  }

  if (session && isCouncilUser) {
    return (
      <CouncilDashboard
        session={session}
        onSignOut={handleSignOut}
      />
    );
  }

  return (
    <main className="login-page">
      <section className="login-card">
        <div className="login-brand">
          <span
          className="login-brand-mark"
          role="img"
          aria-label="Australian flag"
        >
          🇦🇺
        </span>

          <div>
            <strong>UrbanEyes</strong>
            <small>🇦🇺 Be the reason Australia’s streets look better tomorrow</small>
          </div>
        </div>

        <div className="login-heading">
          <p>COUNCIL DASHBOARD</p>
          <h1>Welcome back </h1>
          <span>✅ Sign in to your account to continue.</span>
        </div>

        <form className="login-form" onSubmit={handleLogin}>
          <label htmlFor="council-email">Email address</label>
          <input
            id="council-email"
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            placeholder="Enter your email"
            autoComplete="email"
            required
          />

          <label htmlFor="council-password">Password</label>
          <div className="password-field">
            <input
              id="council-password"
              type={showPassword ? "text" : "password"}
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="Enter your password"
              autoComplete="current-password"
              required
            />

            <button
              type="button"
              onClick={() => setShowPassword((current) => !current)}
            >
              {showPassword ? "Hide" : "Show"}
            </button>
          </div>

          {loginError && (
            <div className="login-error" role="alert">
              {loginError}
            </div>
          )}

          <button
            className="login-submit"
            type="submit"
            disabled={submitting}
          >
            {submitting ? "Signing in..." : "Sign in to Dashboard"}
          </button>
        </form>

        <p className="login-help">
          Access is restricted to authorised council staff.
        </p>
      </section>
    </main>
  );
}

function App() {
  if (!SUPABASE_URL || !SUPABASE_ANON_KEY) {
    return (
      <main className="login-page">
        <section className="login-card">
          <h1>Configuration required</h1>
          <p className="login-error">
            Add VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY to
            the dashboard environment variables.
          </p>
        </section>
      </main>
    );
  }

  return <CouncilLogin />;
}

export default App;
