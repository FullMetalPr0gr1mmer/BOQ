import React, { useState, useEffect, useRef } from "react";
import "../css/Dismantling.css";

const ROWS_PER_PAGE = 50;
const VITE_API_URL = import.meta.env.VITE_API_URL;

export default function Dismantling() {
  const [rows, setRows] = useState([]);
  const [currentPage, setCurrentPage] = useState(1);
  const [total, setTotal] = useState(0); // This will now hold the total count from the backend
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [uploading, setUploading] = useState(false);
  const [loading, setLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");

  const fetchAbort = useRef(null);

  const fetchDismantling = async (page = 1, search = "") => {
    try {
      if (fetchAbort.current) fetchAbort.current.abort();
      const controller = new AbortController();
      fetchAbort.current = controller;

      setLoading(true);
      setError("");
      const skip = (page - 1) * ROWS_PER_PAGE;
      const params = new URLSearchParams();
      params.set("skip", String(skip));
      params.set("limit", String(ROWS_PER_PAGE));
      if (search.trim()) params.set("search", search.trim());

      const res = await fetch(`${VITE_API_URL}/dismantling?${params.toString()}`, {
        signal: controller.signal,
      });

      if (!res.ok) throw new Error("Failed to fetch dismantling records");
      
      const { records, total } = await res.json(); // Destructure the new response object

      setRows(
        (records || []).map((r) => ({
          id: r.id,
          nokia_link_id: r.nokia_link_id,
          nec_dismantling_link_id: r.nec_dismantling_link_id,
          no_of_dismantling: r.no_of_dismantling,
          comments: r.comments,
        }))
      );
      
      setTotal(total || 0); // Correctly set the total count
      setCurrentPage(page);
    } catch (err) {
      if (err.name !== "AbortError") setError(err.message || "Failed to fetch dismantling records");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDismantling(1, "");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const onSearchChange = (e) => {
    const v = e.target.value;
    setSearchTerm(v);
    fetchDismantling(1, v);
  };

  const handleUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setUploading(true);
    setError("");
    setSuccess("");
    const formData = new FormData();
    formData.append("file", file);
    try {
      const res = await fetch(`${VITE_API_URL}/dismantling/upload-csv`, {
        method: "POST",
        body: formData,
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Failed to upload dismantling CSV");
      }
      const result = await res.json();
      setSuccess(`Upload successful! ${result.inserted} rows inserted.`);
      fetchDismantling(1, searchTerm);
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  };

  const totalPages = Math.ceil(total / ROWS_PER_PAGE);

  return (
    <div className="dismantling-container">
      {/* Header & Upload */}
      <div className="dismantling-header-row">
        <h2>Dismantling Records</h2>
        <label className={`upload-btn ${uploading ? 'disabled' : ''}`}>
          📤 Upload Dismantling CSV
          <input
            type="file"
            accept=".csv"
            style={{ display: "none" }}
            disabled={uploading}
            onChange={handleUpload}
          />
        </label>
      </div>

      {/* Search */}
      <div className="dismantling-search-container">
        <input
          type="text"
          placeholder="Filter by Nokia/NEC Link ID or comments..."
          value={searchTerm}
          onChange={onSearchChange}
          className="search-input"
        />
        {searchTerm && (
          <button
            onClick={() => {
              setSearchTerm("");
              fetchDismantling(1, "");
            }}
            className="clear-btn"
          >
            Clear
          </button>
        )}
      </div>

      {/* Messages */}
      {error && <div className="dismantling-message error">{error}</div>}
      {success && <div className="dismantling-message success">{success}</div>}
      {loading && <div className="loading-message">Loading dismantling records...</div>}

      {/* Table */}
      <div className="dismantling-table-container">
        <table className="dismantling-table">
          <thead>
            <tr>
              <th style={{ textAlign: 'center' }}>Nokia Link ID</th>
              <th style={{ textAlign: 'center' }}>NEC Dismantling Link ID</th>
              <th style={{ textAlign: 'center' }}>No. of Dismantling</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 && !loading ? (
              <tr>
                <td colSpan={3} className="no-results" style={{ textAlign: 'center' }}>
                  No results
                </td>
              </tr>
            ) : (
              rows.map((row) => (
                <tr key={row.id}>
                  <td style={{ textAlign: 'center' }}>{row.nokia_link_id}</td>
                  <td style={{ textAlign: 'center' }}>{row.nec_dismantling_link_id}</td>
                  <td style={{ textAlign: 'center' }}>{row.no_of_dismantling}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="dismantling-pagination">
          <button
            className="pagination-btn"
            disabled={currentPage === 1}
            onClick={() => fetchDismantling(currentPage - 1, searchTerm)}
          >
            Prev
          </button>
          <span className="pagination-info">
            Page {currentPage} of {totalPages}
          </span>
          <button
            className="pagination-btn"
            disabled={currentPage === totalPages}
            onClick={() => fetchDismantling(currentPage + 1, searchTerm)}
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}