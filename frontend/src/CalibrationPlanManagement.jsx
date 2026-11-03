
import { useEffect, useState } from "react";

const API_URL = "/api/calibration-plans";
const PAGE_SIZE = 10;

export default function CalibrationPlanManagement() {
  const [plans, setPlans] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(0);

  const [showForm, setShowForm] = useState(false);
  const [saving, setSaving] = useState(false);

  const [form, setForm] = useState({
    asset_id: "",
    interval_days: "30",
    effective_from: "",
    effective_to: "",
    status: "ACTIVE",
    changed_by: "ADMIN",
  });

  async function loadPlans() {
    setLoading(true);
    setError("");

    try {
      const params = new URLSearchParams({
        limit: String(PAGE_SIZE),
        offset: String(page * PAGE_SIZE),
      });

      if (search) params.set("search", search);
      if (status) params.set("status", status);

      const response = await fetch(`${API_URL}?${params}`);

      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        throw new Error(data.error || "Could not load calibration plans.");
      }

      setPlans(data.plans || []);
      setTotal(Number(data.total || 0));
    } catch (err) {
      setError(err.message || "Backend connection failed.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadPlans();
  }, [page, search, status]);

  function updateForm(event) {
    const { name, value } = event.target;
    setForm((previous) => ({ ...previous, [name]: value }));
  }

  function handleSearch(event) {
    event.preventDefault();
    setPage(0);
    setSearch(searchInput.trim());
  }

  async function createPlan(event) {
    event.preventDefault();
    setSaving(true);
    setError("");
    setMessage("");

    try {
      const payload = {
        ...form,
        interval_days: Number(form.interval_days),
        effective_to: form.effective_to || null,
      };

      const response = await fetch(API_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        throw new Error(data.error || "Could not create calibration plan.");
      }

      setMessage(data.message || "Calibration plan created successfully.");
      setForm({
        asset_id: "",
        interval_days: "30",
        effective_from: "",
        effective_to: "",
        status: "ACTIVE",
        changed_by: "ADMIN",
      });
      setShowForm(false);
      setPage(0);
      setSearch("");
      setSearchInput("");
      setStatus("");
      await loadPlansAfterCreate();
    } catch (err) {
      setError(err.message || "Could not create calibration plan.");
    } finally {
      setSaving(false);
    }
  }

  async function loadPlansAfterCreate() {
    const params = new URLSearchParams({
      limit: String(PAGE_SIZE),
      offset: "0",
    });

    const response = await fetch(`${API_URL}?${params}`);
    const data = await response.json().catch(() => ({}));

    if (response.ok) {
      setPlans(data.plans || []);
      setTotal(Number(data.total || 0));
    }
  }

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div className="calibration-page">
      <section className="page-heading">
        <div>
          <p className="eyebrow">OPERATIONS / CALIBRATION</p>
          <h1>Calibration Plan Management</h1>
          <p className="page-description">
            Manage calibration intervals and effective dates for instruments.
          </p>
        </div>

        <button
          className="calibration-primary-button"
          onClick={() => {
            setShowForm((current) => !current);
            setError("");
            setMessage("");
          }}
        >
          {showForm ? "Close form" : "+ Create plan"}
        </button>
      </section>

      {message && (
        <div className="calibration-success-message">{message}</div>
      )}

      {error && (
        <div className="calibration-error-message">
          <strong>Unable to complete request:</strong> {error}
        </div>
      )}

      {showForm && (
        <section className="content-panel calibration-form-panel">
          <div className="panel-header">
            <div>
              <p className="eyebrow">NEW RECORD</p>
              <h2>Create calibration plan</h2>
              <p className="panel-description">
                Enter the asset and its calibration schedule.
              </p>
            </div>
          </div>

          <form onSubmit={createPlan}>
            <div className="calibration-form-grid">
              <label>
                Asset ID *
                <input
                  name="asset_id"
                  value={form.asset_id}
                  onChange={updateForm}
                  placeholder="AST-002001"
                  required
                />
              </label>

              <label>
                Calibration interval (days) *
                <input
                  type="number"
                  name="interval_days"
                  min="1"
                  value={form.interval_days}
                  onChange={updateForm}
                  required
                />
              </label>

              <label>
                Effective from *
                <input
                  type="date"
                  name="effective_from"
                  value={form.effective_from}
                  onChange={updateForm}
                  required
                />
              </label>

              <label>
                Effective to
                <input
                  type="date"
                  name="effective_to"
                  value={form.effective_to}
                  onChange={updateForm}
                  min={form.effective_from || undefined}
                />
              </label>

              <label>
                Plan status
                <select
                  name="status"
                  value={form.status}
                  onChange={updateForm}
                >
                  <option value="ACTIVE">ACTIVE</option>
                  <option value="INACTIVE">INACTIVE</option>
                </select>
              </label>
            </div>

            <div className="calibration-form-actions">
              <button
                type="submit"
                className="calibration-primary-button"
                disabled={saving}
              >
                {saving ? "Saving..." : "Save calibration plan"}
              </button>

              <button
                type="button"
                className="calibration-secondary-button"
                onClick={() => setShowForm(false)}
              >
                Cancel
              </button>
            </div>
          </form>
        </section>
      )}

      <section className="content-panel">
        <div className="panel-header calibration-list-header">
          <div>
            <p className="eyebrow">MASTER DATA</p>
            <h2>Calibration plans</h2>
            <p className="panel-description">
              Plans linked to registered instruments.
            </p>
          </div>

          <span className="record-count">
            {total.toLocaleString()} total plans
          </span>
        </div>

        <form className="calibration-filters" onSubmit={handleSearch}>
          <input
            value={searchInput}
            onChange={(event) => setSearchInput(event.target.value)}
            placeholder="Search asset ID or asset name..."
            aria-label="Search calibration plans"
          />

          <select
            value={status}
            onChange={(event) => {
              setStatus(event.target.value);
              setPage(0);
            }}
            aria-label="Filter by plan status"
          >
            <option value="">All statuses</option>
            <option value="ACTIVE">ACTIVE</option>
            <option value="INACTIVE">INACTIVE</option>
          </select>

          <button type="submit" className="calibration-secondary-button">
            Search
          </button>
        </form>

        {loading ? (
          <div className="empty-state">Loading calibration plans...</div>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Plan ID</th>
                  <th>Asset ID</th>
                  <th>Asset name</th>
                  <th>Interval</th>
                  <th>Effective from</th>
                  <th>Effective to</th>
                  <th>Status</th>
                </tr>
              </thead>

              <tbody>
                {plans.map((plan) => (
                  <tr key={plan.plan_id}>
                    <td className="mono">{plan.plan_id}</td>
                    <td className="mono">{plan.asset_id}</td>
                    <td>{plan.asset_name || "—"}</td>
                    <td>{plan.interval_days} days</td>
                    <td>{String(plan.effective_from || "").slice(0, 10)}</td>
                    <td>
                      {plan.effective_to
                        ? String(plan.effective_to).slice(0, 10)
                        : "No end date"}
                    </td>
                    <td>
                      <span
                        className={`result-tag ${
                          plan.status === "ACTIVE" ? "pass" : "fail"
                        }`}
                      >
                        {plan.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {plans.length === 0 && (
              <div className="empty-state">
                No calibration plans found.
              </div>
            )}
          </div>
        )}

        <div className="calibration-pagination">
          <span>
            Page {page + 1} of {totalPages}
          </span>

          <div>
            <button
              className="calibration-secondary-button"
              disabled={page === 0 || loading}
              onClick={() => setPage((current) => current - 1)}
            >
              Previous
            </button>

            <button
              className="calibration-secondary-button"
              disabled={page + 1 >= totalPages || loading}
              onClick={() => setPage((current) => current + 1)}
            >
              Next
            </button>
          </div>
        </div>
      </section>
    </div>
  );
}
