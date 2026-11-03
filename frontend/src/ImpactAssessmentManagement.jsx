
import { useEffect, useState } from "react";

const categories = [
  "NO_IMPACT",
  "PRODUCT_HOLD",
  "REWORK_REQUIRED",
  "RECALL_REQUIRED",
  "INVESTIGATION_REQUIRED"
];

export default function ImpactAssessmentManagement() {
  const [records, setRecords] = useState([]);
  const [total, setTotal] = useState(0);
  const [draftTotal, setDraftTotal] = useState(0);
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(0);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [selected, setSelected] = useState(null);

  const [draft, setDraft] = useState({
    calibration_id: "",
    asset_id: "",
    work_order_id: "",
    notes: "",
    changed_by: "Quality Engineer"
  });

  const [completion, setCompletion] = useState({
    impact_category: "",
    affected_from: "",
    affected_to: "",
    disposition: "",
    notes: "",
    assessed_by: "",
    assessed_at: ""
  });

  const limit = 10;

  async function loadRecords() {
    setLoading(true);
    setError("");

    try {
      const params = new URLSearchParams({
        search,
        limit: String(limit),
        offset: String(page * limit)
      });

      if (status) params.set("status", status);

      const response = await fetch(`/api/impact-assessments?${params}`);
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Unable to load assessments");
      }

      setRecords(data.records || []);
      setTotal(data.total || 0);
      setDraftTotal(data.draft_total || 0);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadRecords();
  }, [search, status, page]);

  function updateDraft(event) {
    setDraft({
      ...draft,
      [event.target.name]: event.target.value
    });
  }

  function updateCompletion(event) {
    setCompletion({
      ...completion,
      [event.target.name]: event.target.value
    });
  }

  async function createDraft(event) {
    event.preventDefault();
    setMessage("");
    setError("");

    try {
      const response = await fetch("/api/impact-assessments", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(draft)
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Unable to create assessment");
      }

      setMessage(data.message);
      setDraft({
        calibration_id: "",
        asset_id: "",
        work_order_id: "",
        notes: "",
        changed_by: "Quality Engineer"
      });

      setPage(0);
      await loadRecords();
    } catch (err) {
      setError(err.message);
    }
  }

  function openCompletion(record) {
    setSelected(record);

    setCompletion({
      impact_category: "",
      affected_from: "",
      affected_to: "",
      disposition: "",
      notes: record.notes || "",
      assessed_by: "",
      assessed_at: new Date().toISOString().slice(0, 16)
    });

    setMessage("");
    setError("");
  }

  async function completeAssessment(event) {
    event.preventDefault();
    setMessage("");
    setError("");

    try {
      const payload = {
        ...completion,
        affected_from: completion.affected_from
          ? completion.affected_from.replace("T", " ")
          : null,
        affected_to: completion.affected_to
          ? completion.affected_to.replace("T", " ")
          : null,
        assessed_at: completion.assessed_at.replace("T", " ")
      };

      const response = await fetch(
        `/api/impact-assessments/${selected.assessment_id}/complete`,
        {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload)
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Unable to complete assessment");
      }

      setMessage(data.message);
      setSelected(null);
      await loadRecords();
    } catch (err) {
      setError(err.message);
    }
  }

  const totalPages = Math.ceil(total / limit);

  return (
    <div className="impact-assessment-page">
      <div className="page-header">
        <h2>Impact Assessment Management</h2>
        <p>Assess the production impact of failed calibrations.</p>
      </div>

      <div className="production-use-summary">
        <div className="summary-card">
          <span>Total Assessments</span>
          <strong>{total}</strong>
        </div>
        <div className="summary-card">
          <span>Draft Assessments</span>
          <strong>
            {draftTotal}
          </strong>
        </div>
      </div>

      {message && <div className="success-message">{message}</div>}
      {error && <div className="error-message">{error}</div>}

      <section className="production-use-form-section">
        <h3>Create Draft Assessment</h3>

        <form className="production-use-form" onSubmit={createDraft}>
          <div>
            <label>Calibration ID *</label>
            <input
              name="calibration_id"
              value={draft.calibration_id}
              onChange={updateDraft}
              placeholder="CAL-AST-000001-2026-000001"
              required
            />
          </div>

          <div>
            <label>Asset ID *</label>
            <input
              name="asset_id"
              value={draft.asset_id}
              onChange={updateDraft}
              placeholder="AST-000001"
              required
            />
          </div>

          <div>
            <label>Corrective Work Order ID *</label>
            <input
              name="work_order_id"
              value={draft.work_order_id}
              onChange={updateDraft}
              placeholder="WO-2026-000001"
              required
            />
          </div>

          <div>
            <label>Notes</label>
            <input
              name="notes"
              value={draft.notes}
              onChange={updateDraft}
              placeholder="Assessment notes"
            />
          </div>

          <button type="submit">Create Draft</button>
        </form>
      </section>

      {selected && (
        <section className="production-use-form-section">
          <h3>Complete Impact Assessment</h3>

          <p>
            Assessment: <strong>{selected.assessment_id}</strong>
          </p>

          <p>
            Calibration: {selected.calibration_id} |
            Asset: {selected.asset_id}
          </p>

          <form className="production-use-form" onSubmit={completeAssessment}>
            <div>
              <label>Impact Category *</label>
              <select
                name="impact_category"
                value={completion.impact_category}
                onChange={updateCompletion}
                required
              >
                <option value="">Select category</option>
                {categories.map(category => (
                  <option key={category} value={category}>
                    {category.replaceAll("_", " ")}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label>Assessed By *</label>
              <input
                name="assessed_by"
                value={completion.assessed_by}
                onChange={updateCompletion}
                required
              />
            </div>

            <div>
              <label>Affected From</label>
              <input
                type="datetime-local"
                name="affected_from"
                value={completion.affected_from}
                onChange={updateCompletion}
              />
            </div>

            <div>
              <label>Affected To</label>
              <input
                type="datetime-local"
                name="affected_to"
                value={completion.affected_to}
                onChange={updateCompletion}
              />
            </div>

            <div>
              <label>Assessment Date *</label>
              <input
                type="datetime-local"
                name="assessed_at"
                value={completion.assessed_at}
                onChange={updateCompletion}
                required
              />
            </div>

            <div>
              <label>Disposition *</label>
              <textarea
                name="disposition"
                value={completion.disposition}
                onChange={updateCompletion}
                placeholder="Enter the actual quality assessment and disposition"
                required
              />
            </div>

            <div>
              <label>Notes</label>
              <textarea
                name="notes"
                value={completion.notes}
                onChange={updateCompletion}
              />
            </div>

            <button type="submit">Complete Assessment</button>

            <button
              type="button"
              onClick={() => setSelected(null)}
            >
              Cancel
            </button>
          </form>
        </section>
      )}

      <section className="production-use-list">
        <div className="production-use-list-header">
          <h3>Impact Assessment Records</h3>

          <input
            placeholder="Search assessment, calibration or asset..."
            value={search}
            onChange={event => {
              setSearch(event.target.value);
              setPage(0);
            }}
          />

          <select
            value={status}
            onChange={event => {
              setStatus(event.target.value);
              setPage(0);
            }}
          >
            <option value="">All Statuses</option>
            <option value="DRAFT">DRAFT</option>
            <option value="COMPLETED">COMPLETED</option>
          </select>
        </div>

        {loading ? (
          <p>Loading assessments...</p>
        ) : (
          <div className="table-responsive">
            <table>
              <thead>
                <tr>
                  <th>Assessment ID</th>
                  <th>Asset</th>
                  <th>Calibration</th>
                  <th>Work Order</th>
                  <th>Category</th>
                  <th>Status</th>
                  <th>Action</th>
                </tr>
              </thead>

              <tbody>
                {records.map(record => (
                  <tr key={record.assessment_id}>
                    <td>{record.assessment_id}</td>
                    <td>{record.asset_id}</td>
                    <td>{record.calibration_id}</td>
                    <td>{record.work_order_id || "-"}</td>
                    <td>{record.impact_category || "-"}</td>
                    <td>{record.assessment_status}</td>
                    <td>
                      {record.assessment_status === "DRAFT" ? (
                        <button onClick={() => openCompletion(record)}>
                          Complete
                        </button>
                      ) : (
                        "Completed"
                      )}
                    </td>
                  </tr>
                ))}

                {records.length === 0 && (
                  <tr>
                    <td colSpan="7">No assessments found.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}

        <div className="production-use-pagination">
          <span>
            Showing {records.length} of {total} assessments
          </span>

          <button
            disabled={page === 0}
            onClick={() => setPage(page - 1)}
          >
            Previous
          </button>

          <span>
            Page {page + 1} of {Math.max(totalPages, 1)}
          </span>

          <button
            disabled={page + 1 >= totalPages}
            onClick={() => setPage(page + 1)}
          >
            Next
          </button>
        </div>
      </section>
    </div>
  );
}
