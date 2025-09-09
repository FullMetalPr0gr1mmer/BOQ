import React, { useState, useEffect, useRef } from "react";
import "../css/Dismantling.css";
// The VITE_API_URL is an environment variable. In this self-contained
// environment, we'll set a placeholder URL for demonstration.
const VITE_API_URL = import.meta.env.VITE_API_URL;
const ROWS_PER_PAGE = 50;

export default function RANInventory() {
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

  const fetchInventory = async (page = 1, search = "") => {
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

      const res = await fetch(`${VITE_API_URL}/raninventory?${params.toString()}`, {
        signal: controller.signal,
      });

      if (!res.ok) throw new Error("Failed to fetch RAN Inventory records");

      const { records, total } = await res.json();

      setRows(
        (records || []).map((r) => ({
          id: r.id,
          mrbts: r.mrbts,
          site_id: r.site_id,
          identification_code: r.identification_code,
          user_label: r.user_label,
          serial_number: r.serial_number,
          duplicate: r.duplicate,
          duplicate_remarks: r.duplicate_remarks,
        }))
      );
      setTotal(total || 0);
      setCurrentPage(page);
    } catch (err) {
      if (err.name !== "AbortError") setError(err.message || "Failed to fetch records");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchInventory(1, "");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const onSearchChange = (e) => {
    const v = e.target.value;
    setSearchTerm(v);
    fetchInventory(1, v);
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
      const res = await fetch(`${VITE_API_URL}/raninventory/upload-csv`, {
        method: "POST",
        body: formData,
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Failed to upload RAN Inventory CSV");
      }
      const result = await res.json();
      setSuccess(`Upload successful! ${result.message}`);
      fetchInventory(1, searchTerm);
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm("Are you sure you want to delete this record?")) return;
    try {
      const res = await fetch(`${VITE_API_URL}/raninventory/${id}`, {
        method: "DELETE",
      });
      if (!res.ok) throw new Error("Failed to delete record");
      setSuccess("Record deleted successfully");
      fetchInventory(currentPage, searchTerm);
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
    setEditForm((prev) => ({ ...prev, [key]: value }));
  };

  const handleUpdate = async () => {
    if (!editingRow) return;
    setUpdating(true);
    setError("");
    setSuccess("");
    try {
      const res = await fetch(`${VITE_API_URL}/raninventory/${editingRow.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(editForm),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Failed to update record");
      }
      setSuccess("Record updated successfully!");
      closeModal();
      fetchInventory(currentPage, searchTerm);
    } catch (err) {
      setError(err.message);
    } finally {
      setUpdating(false);
    }
  };

  const totalPages = Math.ceil(total / ROWS_PER_PAGE);

  return (
    <>
      <div className="dismantling-container">
        {/* Header & Upload */}
        <div className="dismantling-header-row">
          <h2>RAN Inventory</h2>
          <label className={`upload-btn ${uploading ? "disabled" : ""}`}>
            📤 Upload RAN Inventory CSV
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
            placeholder="Filter by Site ID, MRBTS, or Serial Number..."
            value={searchTerm}
            onChange={onSearchChange}
            className="search-input"
          />
          {searchTerm && (
            <button
              onClick={() => {
                setSearchTerm("");
                fetchInventory(1, "");
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
        {loading && <div className="loading-message">Loading RAN Inventory...</div>}

        {/* Table */}
        <div className="dismantling-table-container">
          <table className="dismantling-table">
            <thead>
              <tr>
                <th>MRBTS</th>
                <th>Site ID</th>
                <th>Identification Code</th>
                <th>User Label</th>
                <th>Serial Number</th>
                <th>Duplicate</th>
                <th>Duplicate Remarks</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {rows.length === 0 && !loading ? (
                <tr>
                  <td colSpan={8} className="no-results">
                    No results
                  </td>
                </tr>
              ) : (
                rows.map((row) => (
                  <tr key={row.id}>
                    <td>{row.mrbts}</td>
                    <td>{row.site_id}</td>
                    <td>{row.identification_code}</td>
                    <td>{row.user_label}</td>
                    <td>{row.serial_number}</td>
                    <td>{row.duplicate ? "Yes" : "No"}</td>
                    <td>{row.duplicate_remarks}</td>
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
              onClick={() => fetchInventory(currentPage - 1, searchTerm)}
            >
              Prev
            </button>
            <span className="pagination-info">
              Page {currentPage} of {totalPages}
            </span>
            <button
              className="pagination-btn"
              disabled={currentPage === totalPages}
              onClick={() => fetchInventory(currentPage + 1, searchTerm)}
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
                <h3>Edit Record</h3>
                <button onClick={closeModal} className="close-btn">✖</button>
              </div>
              <table className="dismantling-table" style={{ width: '100%', borderSpacing: 0, borderCollapse: 'collapse' }}>
                <tbody>
                  <tr key="mrbts">
                    <td style={{ fontWeight: 'bold' }}>MRBTS</td>
                    <td>
                      <input type="text" value={editForm.mrbts !== null && editForm.mrbts !== undefined ? editForm.mrbts : ''} onChange={e => onEditChange('mrbts', e.target.value)} style={{ width: '100%', padding: '8px', boxSizing: 'border-box' }} />
                    </td>
                  </tr>
                  <tr key="site_id">
                    <td style={{ fontWeight: 'bold' }}>Site ID</td>
                    <td>
                      <input type="text" value={editForm.site_id !== null && editForm.site_id !== undefined ? editForm.site_id : ''} onChange={e => onEditChange('site_id', e.target.value)} style={{ width: '100%', padding: '8px', boxSizing: 'border-box' }} />
                    </td>
                  </tr>
                  <tr key="identification_code">
                    <td style={{ fontWeight: 'bold' }}>Identification Code</td>
                    <td>
                      <input type="text" value={editForm.identification_code !== null && editForm.identification_code !== undefined ? editForm.identification_code : ''} onChange={e => onEditChange('identification_code', e.target.value)} style={{ width: '100%', padding: '8px', boxSizing: 'border-box' }} />
                    </td>
                  </tr>
                  <tr key="user_label">
                    <td style={{ fontWeight: 'bold' }}>User Label</td>
                    <td>
                      <input type="text" value={editForm.user_label !== null && editForm.user_label !== undefined ? editForm.user_label : ''} onChange={e => onEditChange('user_label', e.target.value)} style={{ width: '100%', padding: '8px', boxSizing: 'border-box' }} />
                    </td>
                  </tr>
                  <tr key="serial_number">
                    <td style={{ fontWeight: 'bold' }}>Serial Number</td>
                    <td>
                      <input type="text" value={editForm.serial_number !== null && editForm.serial_number !== undefined ? editForm.serial_number : ''} onChange={e => onEditChange('serial_number', e.target.value)} style={{ width: '100%', padding: '8px', boxSizing: 'border-box' }} />
                    </td>
                  </tr>
                  <tr key="duplicate">
                    <td style={{ fontWeight: 'bold' }}>Duplicate</td>
                    <td>
                      <input type="checkbox" checked={editForm.duplicate || false} onChange={e => onEditChange('duplicate', e.target.checked)} />
                    </td>
                  </tr>
                  <tr key="duplicate_remarks">
                    <td style={{ fontWeight: 'bold' }}>Duplicate Remarks</td>
                    <td>
                      <input type="text" value={editForm.duplicate_remarks !== null && editForm.duplicate_remarks !== undefined ? editForm.duplicate_remarks : ''} onChange={e => onEditChange('duplicate_remarks', e.target.value)} style={{ width: '100%', padding: '8px', boxSizing: 'border-box' }} />
                    </td>
                  </tr>
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
    </>
  );
}
