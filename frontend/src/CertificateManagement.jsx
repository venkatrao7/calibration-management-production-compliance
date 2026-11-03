
import { useEffect, useState } from "react";

const API_URL = "/api/certificates";
const PAGE_SIZE = 10;

function formatDate(value) {
  return value ? String(value).slice(0, 10) : "—";
}

export default function CertificateManagement() {
  const [certificates, setCertificates] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(0);

  const [selectedCertificate, setSelectedCertificate] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);

  async function loadCertificates() {
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
        throw new Error(data.error || "Could not load certificates.");
      }

      setCertificates(data.certificates || []);
      setTotal(Number(data.total || 0));
    } catch (err) {
      setError(err.message || "Backend connection failed.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadCertificates();
  }, [page, search, status]);

  function handleSearch(event) {
    event.preventDefault();
    setPage(0);
    setSearch(searchInput.trim());
  }

  async function viewCertificate(certificateId) {
    setDetailLoading(true);
    setSelectedCertificate(null);
    setError("");

    try {
      const response = await fetch(
        `${API_URL}/${encodeURIComponent(certificateId)}`
      );

      const data = await response.json().catch(() => ({}));

      if (!response.ok) {
        throw new Error(data.error || "Could not load certificate details.");
      }

      setSelectedCertificate(data);
    } catch (err) {
      setError(err.message || "Could not load certificate details.");
    } finally {
      setDetailLoading(false);
    }
  }

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div className="certificate-page">
      <section className="page-heading">
        <div>
          <p className="eyebrow">QUALITY / DOCUMENT CONTROL</p>
          <h1>Certificate Management</h1>
          <p className="page-description">
            Track calibration certificates, validity periods and linked assets.
          </p>
        </div>

        <div className="certificate-total-card">
          <span>Total certificates</span>
          <strong>{total.toLocaleString()}</strong>
        </div>
      </section>

      {error && (
        <div className="calibration-error-message">
          <strong>Request failed:</strong> {error}
        </div>
      )}

      <section className="content-panel">
        <div className="panel-header">
          <div>
            <p className="eyebrow">CERTIFICATE REGISTER</p>
            <h2>Calibration certificates</h2>
            <p className="panel-description">
              Certificates generated from successful calibration events.
            </p>
          </div>

          <span className="record-count">
            {total.toLocaleString()} total records
          </span>
        </div>

        <form className="calibration-filters" onSubmit={handleSearch}>
          <input
            value={searchInput}
            onChange={(event) => setSearchInput(event.target.value)}
            placeholder="Search certificate, asset or calibration..."
            aria-label="Search certificates"
          />

          <select
            value={status}
            onChange={(event) => {
              setStatus(event.target.value);
              setPage(0);
            }}
            aria-label="Filter certificate status"
          >
            <option value="">All statuses</option>
            <option value="VALID">VALID</option>
            <option value="EXPIRED">EXPIRED</option>
            <option value="REVOKED">REVOKED</option>
          </select>

          <button type="submit" className="calibration-secondary-button">
            Search
          </button>
        </form>

        {loading ? (
          <div className="empty-state">Loading certificates...</div>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Certificate ID</th>
                  <th>Certificate number</th>
                  <th>Asset ID</th>
                  <th>Calibration ID</th>
                  <th>Issue date</th>
                  <th>Expiry date</th>
                  <th>Status</th>
                  <th>Action</th>
                </tr>
              </thead>

              <tbody>
                {certificates.map((certificate) => (
                  <tr key={certificate.certificate_id}>
                    <td className="mono">
                      {certificate.certificate_id}
                    </td>
                    <td className="mono">
                      {certificate.certificate_number}
                    </td>
                    <td className="mono">{certificate.asset_id}</td>
                    <td className="mono">
                      {certificate.calibration_id}
                    </td>
                    <td>{formatDate(certificate.issue_date)}</td>
                    <td>{formatDate(certificate.expiry_date)}</td>
                    <td>
                      <span
                        className={`result-tag ${
                          certificate.status === "VALID"
                            ? "pass"
                            : "fail"
                        }`}
                      >
                        {certificate.status}
                      </span>
                    </td>
                    <td>
                      <button
                        className="certificate-view-button"
                        onClick={() =>
                          viewCertificate(certificate.certificate_id)
                        }
                      >
                        View
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {certificates.length === 0 && (
              <div className="empty-state">
                No certificates found.
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

      {detailLoading && (
        <section className="content-panel">
          <div className="empty-state">Loading certificate details...</div>
        </section>
      )}

      {selectedCertificate && (
        <section className="content-panel certificate-detail-panel">
          <div className="panel-header">
            <div>
              <p className="eyebrow">CERTIFICATE INFORMATION</p>
              <h2>Certificate details</h2>
            </div>

            <button
              className="calibration-secondary-button"
              onClick={() => setSelectedCertificate(null)}
            >
              Close
            </button>
          </div>

          <div className="certificate-detail-grid">
            <div>
              <span>Certificate ID</span>
              <strong>{selectedCertificate.certificate_id}</strong>
            </div>

            <div>
              <span>Certificate number</span>
              <strong>{selectedCertificate.certificate_number}</strong>
            </div>

            <div>
              <span>Asset ID</span>
              <strong>{selectedCertificate.asset_id}</strong>
            </div>

            <div>
              <span>Asset name</span>
              <strong>{selectedCertificate.asset_name}</strong>
            </div>

            <div>
              <span>Calibration ID</span>
              <strong>{selectedCertificate.calibration_id}</strong>
            </div>

            <div>
              <span>Issue date</span>
              <strong>{formatDate(selectedCertificate.issue_date)}</strong>
            </div>

            <div>
              <span>Expiry date</span>
              <strong>{formatDate(selectedCertificate.expiry_date)}</strong>
            </div>

            <div>
              <span>Status</span>
              <strong>{selectedCertificate.status}</strong>
            </div>

            <div>
              <span>File reference</span>
              <strong>
                {selectedCertificate.file_reference || "Not available"}
              </strong>
            </div>
          </div>
        </section>
      )}
    </div>
  );
}
