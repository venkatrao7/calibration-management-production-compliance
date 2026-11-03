
import { useEffect, useState } from "react";

export default function ProductionUseManagement() {
  const [records, setRecords] = useState([]);
  const [total, setTotal] = useState(0);
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(0);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [violationCount, setViolationCount] = useState(0);

  const [form, setForm] = useState({
    asset_id: "",
    use_start: "",
    use_end: "",
    production_line: "",
    exception_reference: "",
    changed_by: "Production Operator"
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

      const response = await fetch(`/api/production-uses?${params}`);
      const data = await response.json();

      if (!response.ok) throw new Error(data.error || "Failed to load records");

      setRecords(data.records || []);
      setTotal(data.total || 0);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function loadViolations() {
    try {
      const response = await fetch("/api/production-uses/violations");
      const data = await response.json();

      if (!response.ok) throw new Error(data.error || "Failed to load violations");

      setViolationCount(data.total || 0);
    } catch (err) {
      setError(err.message);
    }
  }

  useEffect(() => {
    loadRecords();
  }, [search, page]);

  useEffect(() => {
    loadViolations();
  }, []);

  function updateField(event) {
    setForm({ ...form, [event.target.name]: event.target.value });
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setMessage("");
    setError("");

    try {
      const payload = {
        ...form,
        use_start: form.use_start.replace("T", " "),
        use_end: form.use_end ? form.use_end.replace("T", " ") : null,
        exception_reference: form.exception_reference || null
      };

      const response = await fetch("/api/production-uses", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      const data = await response.json();

      if (!response.ok) throw new Error(data.error || "Failed to record production use");

      setMessage(`Production use recorded successfully: ${data.use_id}`);

      setForm({
        asset_id: "",
        use_start: "",
        use_end: "",
        production_line: "",
        exception_reference: "",
        changed_by: "Production Operator"
      });

      setPage(0);
      await loadRecords();
      await loadViolations();
    } catch (err) {
      setError(err.message);
    }
  }

  const totalPages = Math.ceil(total / limit);

  return (
    <div className="production-use-page">
      <div className="page-header">
        <h2>Production Use Management</h2>
        <p>Record and monitor instrument usage during production.</p>
      </div>

      <div className="production-use-summary">
        <div className="summary-card">
          <span>Total Production Use Records</span>
          <strong>{total.toLocaleString()}</strong>
        </div>

        <div className="summary-card">
          <span>Compliance Violations</span>
          <strong>{violationCount}</strong>
        </div>
      </div>

      <section className="production-use-form-section">
        <h3>Record Production Use</h3>

        <form onSubmit={handleSubmit} className="production-use-form">
          <div>
            <label>Asset ID *</label>
            <input
              name="asset_id"
              value={form.asset_id}
              onChange={updateField}
              placeholder="AST-000001"
              required
            />
          </div>

          <div>
            <label>Production Line</label>
            <input
              name="production_line"
              value={form.production_line}
              onChange={updateField}
              placeholder="Line-1"
            />
          </div>

          <div>
            <label>Use Start *</label>
            <input
              type="datetime-local"
              name="use_start"
              value={form.use_start}
              onChange={updateField}
              required
            />
          </div>

          <div>
            <label>Use End</label>
            <input
              type="datetime-local"
              name="use_end"
              value={form.use_end}
              onChange={updateField}
            />
          </div>

          <div>
            <label>Emergency Extension Reference</label>
            <input
              name="exception_reference"
              value={form.exception_reference}
              onChange={updateField}
              placeholder="Optional"
            />
          </div>

          <button type="submit">Record Production Use</button>
        </form>
      </section>

      {message && <div className="success-message">{message}</div>}
      {error && <div className="error-message">{error}</div>}

      <section className="production-use-list">
        <div className="production-use-list-header">
          <h3>Production Use Records</h3>

          <input
            value={search}
            onChange={(event) => {
              setSearch(event.target.value);
              setPage(0);
            }}
            placeholder="Search asset, name or use ID..."
          />
        </div>

        {loading ? (
          <p>Loading records...</p>
        ) : (
          <div className="table-responsive">
            <table>
              <thead>
                <tr>
                  <th>Use ID</th>
                  <th>Asset ID</th>
                  <th>Asset Name</th>
                  <th>Production Line</th>
                  <th>Start</th>
                  <th>End</th>
                  <th>Extension</th>
                </tr>
              </thead>

              <tbody>
                {records.map((record) => (
                  <tr key={record.use_id}>
                    <td>{record.use_id}</td>
                    <td>{record.asset_id}</td>
                    <td>{record.asset_name}</td>
                    <td>{record.production_line || "-"}</td>
                    <td>{String(record.use_start).replace("T", " ")}</td>
                    <td>{record.use_end ? String(record.use_end).replace("T", " ") : "-"}</td>
                    <td>{record.extension_status || "-"}</td>
                  </tr>
                ))}

                {records.length === 0 && (
                  <tr>
                    <td colSpan="7">No production-use records found.</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}

        <div className="production-use-pagination">
          <span>
            Showing {records.length} of {total.toLocaleString()} records
          </span>

          <button disabled={page === 0} onClick={() => setPage(page - 1)}>
            Previous
          </button>

          <span>Page {page + 1} of {Math.max(totalPages, 1)}</span>

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
