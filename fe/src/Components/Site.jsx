import React, { useState, useEffect, useRef } from "react";
import "../css/Site.css"; // We'll create this CSS file

const ROWS_PER_PAGE = 50;
const VITE_API_URL = import.meta.env.VITE_API_URL;

export default function Site() {
  const [rows, setRows] = useState([]);
  const [currentPage, setCurrentPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [uploading, setUploading] = useState(false);
  const [loading, setLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");

  const fetchAbort = useRef(null);

  const fetchSites = async (page = 1, search = "") => {
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

      const res = await fetch(`${VITE_API_URL}/sites?${params.toString()}`, {
        signal: controller.signal,
      });

      if (!res.ok) throw new Error("Failed to fetch site records");
      
      const { records, total } = await res.json();

      setRows(
        (records || []).map((r) => ({
          id: r.id,
          site_id: r.site_id,
          site_name: r.site_name,
          
        }))
      );
      
      setTotal(total || 0);
      setCurrentPage(page);
    } catch (err) {
      if (err.name !== "AbortError") setError(err.message || "Failed to fetch site records");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSites(1, "");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const onSearchChange = (e) => {
    const v = e.target.value;
    setSearchTerm(v);
    fetchSites(1, v);
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
      const res = await fetch(`${VITE_API_URL}/sites/upload-csv`, {
        method: "POST",
        body: formData,
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Failed to upload sites CSV");
      }
      const result = await res.json();
      setSuccess(`Upload successful! ${result.inserted} sites inserted.`);
      fetchSites(1, searchTerm);
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  };

  const totalPages = Math.ceil(total / ROWS_PER_PAGE);

  return (
    <div className="site-container">
      {/* Header & Upload */}
      <div className="site-header-row">
        <h2>Site Records</h2>
        <label className={`upload-btn ${uploading ? 'disabled' : ''}`}>
          📤 Upload Sites CSV
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
      <div className="site-search-container">
        <input
          type="text"
          placeholder="Filter by Site ID, Site Name"
          value={searchTerm}
          onChange={onSearchChange}
          className="search-input"
        />
        {searchTerm && (
          <button
            onClick={() => {
              setSearchTerm("");
              fetchSites(1, "");
            }}
            className="clear-btn"
          >
            Clear
          </button>
        )}
      </div>

      {/* Messages */}
      {error && <div className="site-message error">{error}</div>}
      {success && <div className="site-message success">{success}</div>}
      {loading && <div className="loading-message">Loading site records...</div>}

      {/* Table */}
      <div className="site-table-container">
        <table className="site-table">
          <thead>
            <tr>
              <th>Site ID</th>
              <th>Site Name</th>
              
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 && !loading ? (
              <tr>
                <td colSpan={3} className="no-results">
                  No results
                </td>
              </tr>
            ) : (
              rows.map((row) => (
                <tr key={row.id}>
                  <td>{row.site_id}</td>
                  <td>{row.site_name}</td>
                 
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="site-pagination">
          <button
            className="pagination-btn"
            disabled={currentPage === 1}
            onClick={() => fetchSites(currentPage - 1, searchTerm)}
          >
            Prev
          </button>
          <span className="pagination-info">
            Page {currentPage} of {totalPages}
          </span>
          <button
            className="pagination-btn"
            disabled={currentPage === totalPages}
            onClick={() => fetchSites(currentPage + 1, searchTerm)}
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}