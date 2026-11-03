
import { useEffect, useMemo, useState } from "react";
import AssetManagement from "./AssetManagement";
import CalibrationPlanManagement from "./CalibrationPlanManagement";
import CertificateManagement from "./CertificateManagement";
import ProductionUseManagement from "./ProductionUseManagement";
import ImpactAssessmentManagement from "./ImpactAssessmentManagement";
const API_URL = "/api/compliance/checks?as_of_date=2026-11-02";

function MetricCard({ label, value, note, tone = "neutral" }) {
  return (
    <article className={`metric-card ${tone}`}>
      <div className="metric-label">{label}</div>
      <div className="metric-value">
        {Number(value ?? 0).toLocaleString()}
      </div>
      <div className="metric-note">{note}</div>
    </article>
  );
}

function formatDate(value) {
  if (!value) return "—";
  return String(value).slice(0, 10);
}

export default function App() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");
  const [activePage, setActivePage] = useState("dashboard");

  async function loadChecks() {
    setLoading(true);
    setError("");

    try {
      const response = await fetch(API_URL);

      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw new Error(body.error || `Request failed (${response.status})`);
      }

      setData(await response.json());
    } catch (err) {
      setError(err.message || "Could not connect to the backend.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadChecks();
  }, []);

  const summary = data?.summary ?? {};
  const overdue = data?.findings?.overdue_assets ?? [];

  const impactAssessments =
    data?.findings?.failed_calibrations_without_impact_assessment ?? [];

  const filteredOverdue = useMemo(() => {
    const term = query.trim().toLowerCase();

    if (!term) return overdue;

    return overdue.filter((item) =>
      [
        item.asset_id,
        item.asset_name,
        item.issue_type,
        item.result,
      ]
        .filter(Boolean)
        .some((value) => String(value).toLowerCase().includes(term))
    );
  }, [overdue, query]);

  return (
    <main className="app-shell">

      {/* Header - visible on both pages */}
      <header className="topbar">
        <div className="brand">
          <div className="brand-mark">CM</div>

          <div>
            <div className="brand-title">
              Calibration Management
            </div>
            <div className="brand-subtitle">
              Production compliance overview
            </div>
          </div>
        </div>

        <div className="topbar-right">
          {activePage === "dashboard" && (
            <>
              <span className="date-chip">
                As of {data?.as_of_date ?? "—"}
              </span>

              <button
                className="refresh-button"
                onClick={loadChecks}
                disabled={loading}
              >
                {loading ? "Refreshing…" : "Refresh data"}
              </button>
            </>
          )}
        </div>
      </header>

      {/* Navigation */}
      <nav className="main-navigation">
        <button
          className={activePage === "dashboard" ? "nav-active" : ""}
          onClick={() => setActivePage("dashboard")}
        >
          Compliance Dashboard
        </button>

        <button
          className={activePage === "assets" ? "nav-active" : ""}
          onClick={() => setActivePage("assets")}
        >
          Asset Management
        </button>
        <button
  className={activePage === "calibration-plans" ? "nav-active" : ""}
  onClick={() => setActivePage("calibration-plans")}
>
  Calibration Plans
</button>
<button
  className={activePage === "certificates" ? "nav-active" : ""}
  onClick={() => setActivePage("certificates")}
>
  Certificates
</button>
<button
  className={activePage === "production-uses" ? "active" : ""}
  onClick={() => setActivePage("production-uses")}
>
  Production Use
</button>
<button
  className={activePage === "impact-assessments" ? "active" : ""}
  onClick={() => setActivePage("impact-assessments")}
>
  Impact Assessments
</button>
      </nav>

      {/* Page content */}
      {activePage === "dashboard" ? (
        <>
          {/* Dashboard heading */}
          <section className="page-heading">
            <div>
              <p className="eyebrow">OPERATIONS / OVERVIEW</p>
              <h1>Compliance dashboard</h1>

              <p className="page-description">
                Monitor calibration status, certificates, corrective
                actions and production-use compliance.
              </p>
            </div>

            <div
              className={`connection-pill ${
                error ? "offline" : data ? "online" : ""
              }`}
            >
              <span className="status-dot" />

              {error
                ? "Backend unavailable"
                : data
                ? "Backend connected"
                : "Connecting"}
            </div>
          </section>

          {/* Error message */}
          {error && (
            <section className="error-panel">
              <strong>Unable to load compliance data.</strong>
              <span>{error}</span>
              <span>
                Confirm that Flask is running at http://127.0.0.1:5000.
              </span>
              <button onClick={loadChecks}>Try again</button>
            </section>
          )}

          {/* Compliance metrics */}
          <section className="metrics-grid">
            <MetricCard
              label="Overdue assets"
              value={summary.overdue_assets}
              note="Require calibration attention"
              tone="warning"
            />

            <MetricCard
              label="Production-use violations"
              value={summary.production_use_violations}
              note="Use outside a valid calibration window"
              tone={
                summary.production_use_violations > 0
                  ? "danger"
                  : "success"
              }
            />

            <MetricCard
              label="Certificate gaps"
              value={summary.certificate_gaps}
              note="PASS calibrations without certificates"
              tone={
                summary.certificate_gaps > 0 ? "danger" : "success"
              }
            />

            <MetricCard
              label="Missing corrective actions"
              value={summary.failed_calibrations_without_corrective_action}
              note="Failed calibrations without work orders"
              tone={
                summary.failed_calibrations_without_corrective_action > 0
                  ? "danger"
                  : "success"
              }
            />

            <MetricCard
              label="Missing impact assessments"
              value={summary.failed_calibrations_without_impact_assessment}
              note="Failed calibrations without completed assessments"
              tone={
                summary.failed_calibrations_without_impact_assessment > 0
                  ? "danger"
                  : "success"
              }
            />
          </section>

          {/* Overdue assets */}
          <section className="content-panel">
            <div className="panel-header">
              <div>
                <p className="eyebrow">CALIBRATION FOLLOW-UP</p>
                <h2>Overdue assets</h2>
                <p className="panel-description">
                  Showing the records returned by the compliance API.
                </p>
              </div>

              <div className="table-tools">
                <input
                  aria-label="Search overdue assets"
                  placeholder="Search asset or issue…"
                  value={query}
                  onChange={(event) => setQuery(event.target.value)}
                />

                <span className="record-count">
                  {filteredOverdue.length.toLocaleString()} shown
                  {data?.sample_limit
                    ? ` · API sample limit ${data.sample_limit}`
                    : ""}
                </span>
              </div>
            </div>

            {loading && !data ? (
              <div className="empty-state">
                Loading compliance records…
              </div>
            ) : (
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Asset ID</th>
                      <th>Asset name</th>
                      <th>Last calibration</th>
                      <th>Due date</th>
                      <th>Result</th>
                      <th>Finding</th>
                    </tr>
                  </thead>

                  <tbody>
                    {filteredOverdue.map((item) => (
                      <tr
                        key={`${item.asset_id}-${item.calibration_id}`}
                      >
                        <td className="mono">{item.asset_id}</td>
                        <td>{item.asset_name || "—"}</td>
                        <td>{formatDate(item.calibration_date)}</td>
                        <td>{formatDate(item.due_date)}</td>
                        <td>
                          <span
                            className={`result-tag ${
                              item.result === "FAIL" ? "fail" : "pass"
                            }`}
                          >
                            {item.result || "—"}
                          </span>
                        </td>
                        <td>
                          <span className="finding-tag">
                            {String(item.issue_type || "").replaceAll(
                              "_",
                              " "
                            )}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>

                {filteredOverdue.length === 0 && (
                  <div className="empty-state">
                    {query
                      ? "No overdue assets match your search."
                      : "No overdue assets found."}
                  </div>
                )}
              </div>
            )}
          </section>

          {/* Missing impact assessments */}
          <section className="content-panel">
            <div className="panel-header">
              <div>
                <p className="eyebrow">QUALITY / CORRECTIVE ACTION</p>
                <h2>Missing impact assessments</h2>
                <p className="panel-description">
                  Failed calibrations that do not yet have a completed
                  impact assessment.
                </p>
              </div>

              <span className="record-count">
                {Number(
                  summary.failed_calibrations_without_impact_assessment ?? 0
                ).toLocaleString()} total findings
              </span>
            </div>

            {loading && !data ? (
              <div className="empty-state">
                Loading impact assessment records…
              </div>
            ) : (
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Calibration ID</th>
                      <th>Asset ID</th>
                      <th>Calibration date</th>
                      <th>Result</th>
                      <th>Finding</th>
                    </tr>
                  </thead>

                  <tbody>
                    {impactAssessments.map((item) => (
                      <tr key={item.calibration_id}>
                        <td className="mono">
                          {item.calibration_id}
                        </td>
                        <td className="mono">{item.asset_id}</td>
                        <td>{formatDate(item.calibration_date)}</td>
                        <td>
                          <span className="result-tag fail">
                            {item.result || "FAIL"}
                          </span>
                        </td>
                        <td>
                          <span className="finding-tag">
                            {String(item.issue_type || "").replaceAll(
                              "_",
                              " "
                            )}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>

                {impactAssessments.length === 0 && (
                  <div className="empty-state">
                    No missing impact assessments found.
                  </div>
                )}
              </div>
            )}
          </section>
               </>
      ) : activePage === "assets" ? (
        <AssetManagement />
      ) : activePage === "calibration-plans" ? (
        <CalibrationPlanManagement />
      ) : activePage === "production-uses" ? (
        <ProductionUseManagement />
      ): activePage === "impact-assessments" ? (
  <ImpactAssessmentManagement />
) : (
        <CertificateManagement />
      )}
      
      {/* Footer - visible on both pages */}
      <footer className="footer">
        <span>
          Calibration Management and Production Compliance System
        </span>
        <span>
          Live data from Flask API
        </span>
      </footer>

    </main>
  );
}
