import React, { useState, useEffect, useRef } from "react";
import "../css/Dismantling.css";
import { apiCall, setTransient } from '../api.js';

const ROWS_PER_PAGE = 50;

export default function Dismantling() {
  // --- State Variables ---
  const [rows, setRows] = useState([]);
  const [currentPage, setCurrentPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [uploading, setUploading] = useState(false);
  const [loading, setLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [editingRow, setEditingRow] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  // --- NEW: State for project selection and form data ---
  const [projects, setProjects] = useState([]);
  const [selectedProject, setSelectedProject] = useState('');
  const [formData, setFormData] = useState({
    nokia_link_id: '',
    nec_dismantling_link_id: '',
    no_of_dismantling: '',
    comments: '',
    pid_po: '', // To hold the project ID
  });

  const fetchAbort = useRef(null);

  // --- Function to fetch user's projects ---
  const fetchProjects = async () => {
    try {
      const data = await apiCall('/get_project');
      setProjects(data || []);
      // Optionally, auto-select the first project
      if (data && data.length > 0) {
        setSelectedProject(data[0].pid_po);
      }
    } catch (err) {
      setTransient(setError, 'Failed to load projects. Please ensure you have project access.');
      console.error(err);
    }
  };

  // --- Data Fetching ---
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

      const { records, total } = await apiCall(`/dismantling?${params.toString()}`, {
        signal: controller.signal
      });

      setRows(
        (records || []).map((r) => ({
          id: r.id,
          nokia_link_id: r.nokia_link_id,
          nec_dismantling_link_id: r.nec_dismantling_link_id,
          no_of_dismantling: r.no_of_dismantling,
          comments: r.comments,
          pid_po: r.pid_po, // Store project ID for context
        }))
      );
      setTotal(total || 0);
      setCurrentPage(page);
    } catch (err) {
      if (err.name !== "AbortError") setTransient(setError, err.message || "Failed to fetch dismantling records");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProjects(); // Fetch projects on component mount
    fetchDismantling(1, "");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const onSearchChange = (e) => {
    const v = e.target.value;
    setSearchTerm(v);
    fetchDismantling(1, v);
  };

  // --- MODIFIED: Handle Upload to include project_id in URL ---
  const handleUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    if (!selectedProject) {
      setTransient(setError, "Please select a project before uploading.");
      e.target.value = '';
      return;
    }
    setUploading(true);
    setError("");
    setSuccess("");

    const formDataLocal = new FormData();
    formDataLocal.append("file", file);
    formDataLocal.append("pid_po", selectedProject);

    try {
      const result = await apiCall('/dismantling/upload-csv', {
        method: "POST",
        body: formDataLocal
      });
      setTransient(setSuccess, `Upload successful! ${result.inserted} rows inserted.`);
      fetchDismantling(1, searchTerm);
    } catch (err) {
      setTransient(setError, err.message);
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  };

  // --- MODIFIED: Create / Edit / Delete to handle project_id ---
  const openCreateModal = () => {
    if (!selectedProject) {
      setTransient(setError, 'Please select a project to create a new record.');
      return;
    }
    setFormData({
      nokia_link_id: '',
      nec_dismantling_link_id: '',
      no_of_dismantling: '',
      comments: '',
      pid_po: selectedProject, // Set the project ID for the new record
    });
    setEditingRow(null);
    setShowForm(true);
    setError('');
    setSuccess('');
  };

  const openEditModal = async (row) => {
    if (!row || !row.id) {
      setTransient(setError, 'Cannot edit: missing id');
      return;
    }
    setEditingRow(row);
    try {
      setLoading(true);
      const data = await apiCall(`/dismantling/${row.id}`);
      setFormData({
        nokia_link_id: data.nokia_link_id || '',
        nec_dismantling_link_id: data.nec_dismantling_link_id || '',
        no_of_dismantling: data.no_of_dismantling || '',
        comments: data.comments || '',
        pid_po: data.pid_po || '',
      });
      setShowForm(true);
      setError('');
      setSuccess('');
    } catch (err) {
      setTransient(setError, err.message || 'Failed to load record for editing');
    } finally {
      setLoading(false);
    }
  };

  const closeFormModal = () => {
    setShowForm(false);
    setEditingRow(null);
    setFormData({
      nokia_link_id: '',
      nec_dismantling_link_id: '',
      no_of_dismantling: '',
      comments: '',
      pid_po: selectedProject,
    });
    setError('');
    setSuccess('');
  };

  const handleFormInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleFormSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setError('');
    setSuccess('');
    try {
      if (editingRow) {
        await apiCall(`/dismantling/${editingRow.id}`, {
          method: 'PUT',
          body: JSON.stringify(formData)
        });
        setTransient(setSuccess, 'Record updated successfully!');
      } else {
        await apiCall('/dismantling', {
          method: 'POST',
          body: JSON.stringify(formData)
        });
        setTransient(setSuccess, 'Record created successfully!');
      }
      fetchDismantling(currentPage, searchTerm);
      setTimeout(() => closeFormModal(), 1200);
    } catch (err) {
      setTransient(setError, err.message);
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (row) => {
    if (!row || !row.id) return;
    if (!window.confirm(`Are you sure you want to delete this record?`)) return;
    try {
      await apiCall(`/dismantling/${row.id}`, {
        method: 'DELETE'
      });
      setTransient(setSuccess, 'Record deleted successfully!');
      fetchDismantling(currentPage, searchTerm);
    } catch (err) {
      setTransient(setError, err.message);
    }
  };

  const totalPages = Math.ceil(total / ROWS_PER_PAGE);

  // --- JSX Rendering ---
  return (
    <div className="dismantling-container">
      {/* Header & Upload */}
      <div className="dismantling-header-row">
        <h2>Dismantling Records</h2>
        
        <div style={{ display: 'flex', gap: 16 }}>
          <button
            className="upload-btn"
            onClick={openCreateModal}
            disabled={!selectedProject}
            title={!selectedProject ? "Select a project first" : "Create a new record"}
          >
            + New Record
          </button>
          <label className={`upload-btn ${uploading || !selectedProject ? 'disabled' : ''}`}
            title={!selectedProject ? "Select a project first" : "Upload a dismantling CSV"}
          >
            📤 Upload Dismantling CSV
            <input
              type="file"
              accept=".csv"
              style={{ display: "none" }}
              disabled={uploading || !selectedProject}
              onChange={handleUpload}
            />
          </label>
        </div>
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
        <div className="project-selector-container">
          <select
            id="project-select"
            className="search-input"
            value={selectedProject}
            onChange={(e) => {
              setSelectedProject(e.target.value);
              fetchDismantling(1, ""); // Refetch data for the new project
            }}
          >
            <option value="">-- Select a Project --</option>
            {projects.map((p) => (
              <option key={p.pid_po} value={p.pid_po}>
                {p.project_name} ({p.pid_po})
              </option>
            ))}
          </select>
        </div>
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
             
              <th style={{ textAlign: 'center', width: '110px' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 && !loading ? (
              <tr>
                <td colSpan={5} className="no-results" style={{ textAlign: 'center' }}>
                  No results
                </td>
              </tr>
            ) : (
              rows.map((row) => (
                <tr key={row.id}>
                  <td style={{ textAlign: 'center' }}>{row.nokia_link_id}</td>
                  <td style={{ textAlign: 'center' }}>{row.nec_dismantling_link_id}</td>
                  <td style={{ textAlign: 'center' }}>{row.no_of_dismantling}</td>
     
                  <td style={{ textAlign: 'center', width: '110px' }}>
                    <div className="actions-cell">
                      <button className="pagination-btn" onClick={() => openEditModal(row)}>Details</button>
                      <button className="clear-btn" onClick={() => handleDelete(row)}>Delete</button>
                    </div>
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

      {/* Create/Edit Modal */}
      {showForm && (
        <div className="modal-overlay">
          <div className="modal-content">
            <form className="project-form" onSubmit={handleFormSubmit}>
              <div className="modal-header-row" style={{ justifyContent: 'space-between' }}>
                <h3 className="modal-title">
                  {editingRow ? `Editing Record: #${editingRow.id}` : 'New Dismantling Record'}
                </h3>
                <button className="modal-close-btn" onClick={closeFormModal} type="button">&times;</button>
              </div>

              {error && <div className="dismantling-message error">{error}</div>}
              {success && <div className="dismantling-message success">{success}</div>}

              <input
                className="search-input"
                type="text"
                name="nokia_link_id"
                placeholder="Nokia Link ID"
                value={formData.nokia_link_id}
                onChange={handleFormInputChange}
                required
              />
              <input
                className="search-input"
                type="text"
                name="nec_dismantling_link_id"
                placeholder="NEC Dismantling Link ID"
                value={formData.nec_dismantling_link_id}
                onChange={handleFormInputChange}
                required
              />
              <input
                className="search-input"
                type="number"
                name="no_of_dismantling"
                placeholder="No. of Dismantling"
                value={formData.no_of_dismantling}
                onChange={handleFormInputChange}
                required
              />
              <textarea
                className="search-input"
                name="comments"
                placeholder="Comments"
                value={formData.comments}
                onChange={handleFormInputChange}
              />
              <button className="upload-btn" type="submit" disabled={submitting}>
                {submitting ? 'Saving...' : (editingRow ? 'Update' : 'Save')}
              </button>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}