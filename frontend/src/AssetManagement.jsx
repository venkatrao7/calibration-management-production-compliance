
import { useEffect, useState } from "react";

const PAGE_SIZE = 10;

const emptyForm = {
  asset_name: "",
  instrument_type_id: "",
  location: "",
  status: "ACTIVE",
};

export default function AssetManagement() {
  const [assets, setAssets] = useState([]);
  const [types, setTypes] = useState([]);
  const [total, setTotal] = useState(0);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [page, setPage] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [form, setForm] = useState(emptyForm);
  const [saving, setSaving] = useState(false);

  async function loadTypes() {
    const response = await fetch("/api/instrument-types");
    if (!response.ok) throw new Error("Could not load instrument types.");
    const result = await response.json();
    setTypes(result.instrument_types || []);
  }

  async function loadAssets() {
    setLoading(true);
    setError("");

    try {
      const params = new URLSearchParams({
        search,
        limit: String(PAGE_SIZE),
        offset: String(page * PAGE_SIZE),
      });

      if (statusFilter) params.set("status", statusFilter);
      if (typeFilter) params.set("instrument_type_id", typeFilter);

      const response = await fetch(`/api/assets?${params.toString()}`);
      const result = await response.json();

      if (!response.ok) {
        throw new Error(result.error || "Could not load assets.");
      }

      setAssets(result.assets || []);
      setTotal(result.total || 0);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadTypes().catch((err) => setError(err.message));
  }, []);

  useEffect(() => {
    loadAssets();
  }, [search, statusFilter, typeFilter, page]);

  function updateField(event) {
    const { name, value } = event.target;
    setForm((current) => ({ ...current, [name]: value }));
  }

  function openCreateForm() {
    setEditingId(null);
    setForm(emptyForm);
    setMessage("");
    setError("");
    setShowForm(true);
  }

  function openEditForm(asset) {
    setEditingId(asset.asset_id);
    setForm({
      asset_name: asset.asset_name || "",
      instrument_type_id: String(asset.instrument_type_id),
      location: asset.location || "",
      status: asset.status,
    });
    setMessage("");
    setError("");
    setShowForm(true);
  }

  async function saveAsset(event) {
    event.preventDefault();
    setSaving(true);
    setError("");
    setMessage("");

    try {
      const payload = {
        asset_name: form.asset_name.trim(),
        instrument_type_id: Number(form.instrument_type_id),
        location: form.location.trim(),
        status: form.status,
      };

      const url = editingId
        ? `/api/assets/${editingId}`
        : "/api/assets";

      const response = await fetch(url, {
        method: editingId ? "PUT" : "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      const result = await response.json();

      if (!response.ok) {
        throw new Error(result.error || "Could not save asset.");
      }

      setShowForm(false);
      setMessage(
        editingId ? "Asset updated successfully." : "Asset created successfully."
      );
      setPage(0);
      await loadAssets();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  }

  async function toggleStatus(asset) {
    const nextStatus = asset.status === "ACTIVE" ? "INACTIVE" : "ACTIVE";

    const confirmed = window.confirm(
      `Are you sure you want to mark ${asset.asset_id} as ${nextStatus}?`
    );

    if (!confirmed) return;

    setError("");
    setMessage("");

    try {
      const response = await fetch(`/api/assets/${asset.asset_id}/status`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          status: nextStatus,
          changed_by: "ADMIN",
        }),
      });

      const result = await response.json();

      if (!response.ok) {
        throw new Error(result.error || "Could not update asset status.");
      }

      setMessage(`${asset.asset_id} is now ${nextStatus}.`);
      await loadAssets();
    } catch (err) {
      setError(err.message);
    }
  }

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <section>
      <div className="page-heading">
        <div>
          <p className="eyebrow">OPERATIONS / MASTER DATA</p>
          <h1>Asset Management</h1>
          <p className="page-description">
            Register, search and manage plant instruments and equipment.
          </p>
        </div>

        <button className="primary-button" onClick={openCreateForm}>
          + Add asset
        </button>
      </div>

      <section className="asset-summary">
        <article className="metric-card">
          <div className="metric-label">Matching assets</div>
          <div className="metric-value">{total.toLocaleString()}</div>
          <div className="metric-note">Based on current filters</div>
        </article>
        <article className="metric-card">
          <div className="metric-label">Current page</div>
          <div className="metric-value">{assets.length}</div>
          <div className="metric-note">Records displayed</div>
        </article>
      </section>

      {message && <div className="success-panel">{message}</div>}
      {error && <div className="asset-error">{error}</div>}

      {showForm && (
        <section className="content-panel asset-form-panel">
          <div className="panel-header">
            <div>
              <p className="eyebrow">ASSET DETAILS</p>
              <h2>{editingId ? `Edit ${editingId}` : "Register new asset"}</h2>
            </div>
            <button
              type="button"
              className="secondary-button"
              onClick={() => setShowForm(false)}
            >
              Cancel
            </button>
          </div>

          <form className="asset-form" onSubmit={saveAsset}>
            <label>
              Asset name *
              <input
                name="asset_name"
                value={form.asset_name}
                onChange={updateField}
                placeholder="Enter asset name"
                required
                maxLength={100}
              />
            </label>

            <label>
              Instrument type *
              <select
                name="instrument_type_id"
                value={form.instrument_type_id}
                onChange={updateField}
                required
              >
                <option value="">Select instrument type</option>
                {types.map((type) => (
                  <option
                    key={type.instrument_type_id}
                    value={type.instrument_type_id}
                  >
                    {type.type_name}
                  </option>
                ))}
              </select>
            </label>

            <label>
              Location
              <input
                name="location"
                value={form.location}
                onChange={updateField}
                placeholder="Example: Plant-1 / Line-2"
                maxLength={100}
              />
            </label>

            {!editingId && (
              <label>
                Initial status
                <select
                  name="status"
                  value={form.status}
                  onChange={updateField}
                >
                  <option value="ACTIVE">ACTIVE</option>
                  <option value="INACTIVE">INACTIVE</option>
                </select>
              </label>
            )}

            <div className="form-actions">
              <button
                className="primary-button"
                type="submit"
                disabled={saving}
              >
                {saving
                  ? "Saving..."
                  : editingId
                  ? "Save changes"
                  : "Create asset"}
              </button>
              <button
                className="secondary-button"
                type="button"
                onClick={() => setShowForm(false)}
              >
                Cancel
              </button>
            </div>
          </form>
        </section>
      )}

      <section className="content-panel">
        <div className="panel-header asset-panel-header">
          <div>
            <p className="eyebrow">MASTER DATA / REGISTER</p>
            <h2>Instrument register</h2>
            <p className="panel-description">
              Search and filter registered instruments.
            </p>
          </div>

          <button
            className="secondary-button"
            onClick={loadAssets}
            disabled={loading}
          >
            {loading ? "Loading..." : "Refresh"}
          </button>
        </div>

        <div className="asset-filters">
          <input
            value={search}
            onChange={(event) => {
              setSearch(event.target.value);
              setPage(0);
            }}
            placeholder="Search ID, name or location..."
          />

          <select
            value={statusFilter}
            onChange={(event) => {
              setStatusFilter(event.target.value);
              setPage(0);
            }}
          >
            <option value="">All statuses</option>
            <option value="ACTIVE">Active</option>
            <option value="INACTIVE">Inactive</option>
          </select>

          <select
            value={typeFilter}
            onChange={(event) => {
              setTypeFilter(event.target.value);
              setPage(0);
            }}
          >
            <option value="">All instrument types</option>
            {types.map((type) => (
              <option
                key={type.instrument_type_id}
                value={type.instrument_type_id}
              >
                {type.type_name}
              </option>
            ))}
          </select>
        </div>

        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Asset ID</th>
                <th>Asset name</th>
                <th>Instrument type</th>
                <th>Location</th>
                <th>Status</th>
                <th>Actions</th>
              </tr>
            </thead>

            <tbody>
              {assets.map((asset) => (
                <tr key={asset.asset_id}>
                  <td className="mono">{asset.asset_id}</td>
                  <td>{asset.asset_name}</td>
                  <td>{asset.type_name}</td>
                  <td>{asset.location || "—"}</td>
                  <td>
                    <span
                      className={`asset-status ${
                        asset.status === "ACTIVE" ? "active" : "inactive"
                      }`}
                    >
                      {asset.status}
                    </span>
                  </td>
                  <td>
                    <div className="action-buttons">
                      <button
                        className="text-button"
                        onClick={() => openEditForm(asset)}
                      >
                        Edit
                      </button>
                      <button
                        className="text-button"
                        onClick={() => toggleStatus(asset)}
                      >
                        {asset.status === "ACTIVE" ? "Deactivate" : "Activate"}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          {!loading && assets.length === 0 && (
            <div className="empty-state">No matching assets found.</div>
          )}

          {loading && (
            <div className="empty-state">Loading asset records...</div>
          )}
        </div>

        <div className="pagination">
          <span>
            Showing {total === 0 ? 0 : page * PAGE_SIZE + 1}–
            {Math.min((page + 1) * PAGE_SIZE, total)} of {total}
          </span>

          <div>
            <button
              className="secondary-button"
              disabled={page === 0 || loading}
              onClick={() => setPage((current) => current - 1)}
            >
              Previous
            </button>
            <span className="page-number">
              Page {page + 1} of {totalPages}
            </span>
            <button
              className="secondary-button"
              disabled={page + 1 >= totalPages || loading}
              onClick={() => setPage((current) => current + 1)}
            >
              Next
            </button>
          </div>
        </div>
      </section>
    </section>
  );
}
