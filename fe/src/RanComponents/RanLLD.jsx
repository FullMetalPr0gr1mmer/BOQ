import React, { useState, useEffect, useRef } from "react";
import "../css/Dismantling.css";

const ROWS_PER_PAGE = 50;
const VITE_API_URL = import.meta.env.VITE_API_URL;

export default function RANLLD() {
  const [rows, setRows] = useState([]);
  const [currentPage, setCurrentPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [uploading, setUploading] = useState(false);
  const [loading, setLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingRow, setEditingRow] = useState(null);
  const [editForm, setEditForm] = useState({});
  const [updating, setUpdating] = useState(false);

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

      const res = await fetch(`${VITE_API_URL}/ran-sites?${params.toString()}`, {
        signal: controller.signal,
      });

      if (!res.ok) throw new Error("Failed to fetch RAN Sites");

      const { records, total } = await res.json();

      setRows(
        (records || []).map((r) => ({
          id: r.id,
          site_id: r.site_id,
          new_antennas: r.new_antennas,
          total_antennas: r.total_antennas,
          technical_boq: r.technical_boq,
        }))
      );
      setTotal(total || 0);
      setCurrentPage(page);
    } catch (err) {
      if (err.name !== "AbortError") setError(err.message || "Failed to fetch sites");
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
      const res = await fetch(`${VITE_API_URL}/ran-sites/upload-csv`, {
        method: "POST",
        body: formData,
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Failed to upload RAN Sites CSV");
      }
      const result = await res.json();
      setSuccess(`Upload successful! ${result.inserted || "?"} rows inserted.`);
      fetchSites(1, searchTerm);
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm("Are you sure you want to delete this site?")) return;
    try {
      const res = await fetch(`${VITE_API_URL}/ran-sites/${id}`, {
        method: "DELETE",
      });
      if (!res.ok) throw new Error("Failed to delete site");
      setSuccess("Site deleted successfully");
      fetchSites(currentPage, searchTerm);
    } catch (err) {
      setError(err.message);
    }
  };

  const openEditModal = (row) => {
    setEditingRow(row);
    const { id, ...formFields } = row;
    setEditForm(formFields);
    setIsModalOpen(true);
  };

  const closeModal = () => {
    setIsModalOpen(false);
    setEditingRow(null);
    setEditForm({});
    setError("");
    setSuccess("");
  };
  
  const onEditChange = (key, value) => {
    let convertedValue = value;
    // Only convert total_antennas to a number
    if (key === 'total_antennas') {
      convertedValue = parseInt(value, 10);
      if (isNaN(convertedValue)) {
        convertedValue = ''; 
      }
    }
    // new_antennas and other fields will remain strings
    setEditForm((prev) => ({ ...prev, [key]: convertedValue }));
  };

  const handleUpdate = async () => {
    if (!editingRow) return;
    setUpdating(true);
    setError("");
    setSuccess("");
    try {
      const res = await fetch(`${VITE_API_URL}/ran-sites/${editingRow.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(editForm),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Failed to update site");
      }
      setSuccess("Site updated successfully!");
      closeModal();
      fetchSites(currentPage, searchTerm);
    } catch (err) {
      setError(err.message);
    } finally {
      setUpdating(false);
    }
  };

  const totalPages = Math.ceil(total / ROWS_PER_PAGE);

  return (
    <div className="dismantling-container">
      {/* Header & Upload */}
      <div className="dismantling-header-row">
        <h2>RAN Sites</h2>
        <label className={`upload-btn ${uploading ? "disabled" : ""}`}>
          📤 Upload RAN Sites CSV
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
          placeholder="Filter by Site ID or BoQ..."
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
      {error && <div className="dismantling-message error">{error}</div>}
      {success && <div className="dismantling-message success">{success}</div>}
      {loading && <div className="loading-message">Loading RAN Sites...</div>}

      {/* Table */}
      <div className="dismantling-table-container">
        <table className="dismantling-table">
          <thead>
            <tr>
              <th>Site ID</th>
              <th>New Antennas</th>
              <th>Total Antennas</th>
              <th>Technical BoQ</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 && !loading ? (
              <tr>
                <td colSpan={5} className="no-results">
                  No results
                </td>
              </tr>
            ) : (
              rows.map((row) => (
                <tr key={row.id}>
                  <td>{row.site_id}</td>
                  <td>{row.new_antennas}</td>
                  <td>{row.total_antennas}</td>
                  <td>{row.technical_boq}</td>
                  <td className="actions-cell">
                    <button className="clear-btn" onClick={() => openEditModal(row)}>
                      Edit
                    </button>
                    <button className="clear-btn" onClick={() => handleDelete(row.id)}>
                      Delete
                    </button>
                  </td>
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

      {/* Edit Modal */}
      {isModalOpen && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12 }}>
              <h3>Edit Site: {editingRow?.site_id}</h3>
              <button onClick={closeModal} className="close-btn">✖</button>
            </div>
            <table className="dismantling-table" style={{ width: '100%', borderSpacing: 0, borderCollapse: 'collapse' }}>
              <tbody>
                {Object.keys(editForm).map((key) => (
                  <tr key={key}>
                    <td style={{ fontWeight: 'bold' }}>
                        {key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
                    </td>
                    <td>
                      <input
                        type={key === 'total_antennas' ? 'number' : 'text'}
                        value={editForm[key] !== null && editForm[key] !== undefined ? editForm[key] : ''}
                        onChange={e => onEditChange(key, e.target.value)}
                        style={{ width: '100%', padding: '8px', boxSizing: 'border-box' }}
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <button
              onClick={handleUpdate}
              disabled={updating}
              className="pagination-btn"
              style={{ marginTop: 12, width: '100%' }}
            >
              {updating ? 'Updating...' : 'Update'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}