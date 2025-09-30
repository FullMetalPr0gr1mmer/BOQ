import React, { useState, useEffect, useRef } from "react";
import "../css/Site.css"; // We'll create this CSS file
import { apiCall, setTransient } from '../api.js';

const ROWS_PER_PAGE = 50;
export default function Site() {
  const [rows, setRows] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [editingRow, setEditingRow] = useState(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [uploading, setUploading] = useState(false);
  const [loading, setLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const [submitting, setSubmitting] = useState(false);

  // Project-related state
  const [projects, setProjects] = useState([]);
  const [selectedProject, setSelectedProject] = useState('');

  // Form state
  const [formData, setFormData] = useState({
    site_id: '',
    site_name: '',
    pid_po: ''
  });

  const fetchAbort = useRef(null);

  const fetchProjects = async () => {
    try {
      const data = await apiCall('/get_project');
      setProjects(data || []);
      // Auto-select the first project if available
      if (data && data.length > 0) {
        setSelectedProject(data[0].pid_po);
      }
    } catch (err) {
      setTransient(setError, 'Failed to load projects. Please ensure you have project access.');
      console.error(err);
    }
  };

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

      const { records, total } = await apiCall(`/sites?${params.toString()}`, {
        signal: controller.signal,
        method: 'GET'
      });

      setRows(
        (records || []).map((r) => ({
          id: r.id,
          site_id: r.site_id,
          site_name: r.site_name,
          pid_po: r.pid_po,
        }))
      );

      setTotal(total || 0);
      setCurrentPage(page);
    } catch (err) {
      if (err.name !== "AbortError") setTransient(setError, err.message || "Failed to fetch site records");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProjects();
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

    // Validate project selection
    if (!selectedProject) {
      setTransient(setError, 'Please select a project before uploading CSV.');
      e.target.value = "";
      return;
    }

    setUploading(true);
    setError("");
    setSuccess("");
    const formData = new FormData();
    formData.append("file", file);
    formData.append("pid_po", selectedProject);
    try {
      const result = await apiCall('/sites/upload-csv', {
        method: "POST",
        body: formData
      });
      setTransient(setSuccess, `Upload successful! ${result.inserted} sites inserted.`);
      fetchSites(1, searchTerm);
    } catch (err) {
      setTransient(setError, err.message);
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  };

  const openCreateModal = () => {
    // Validate project selection
    if (!selectedProject) {
      setTransient(setError, 'Please select a project to create a new site.');
      return;
    }

    setFormData({
      site_id: '',
      site_name: '',
      pid_po: selectedProject
    });
    setEditingRow(null);
    setShowForm(true);
  };

  const openEditModal = (row) => {
    setFormData({
      site_id: row.site_id,
      site_name: row.site_name,
      pid_po: row.pid_po // Note: using project_id from the response
    });
    setEditingRow(row);
    setShowForm(true);
  };

  const closeModal = () => {
    setShowForm(false);
    setEditingRow(null);
    setFormData({
      site_id: '',
      site_name: '',
      pid_po: ''
    });
    setError("");
    setSuccess("");
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setError("");
    setSuccess("");

    try {
      const endpoint = editingRow
        ? `/update-site/${editingRow.id}`
        : '/add-site';

      const method = editingRow ? 'PUT' : 'POST';

      await apiCall(endpoint, {
        method,
        body: JSON.stringify(formData)
      });

      setTransient(setSuccess, `Site ${editingRow ? 'updated' : 'created'} successfully!`);
      fetchSites(currentPage, searchTerm);

      // Close modal after a short delay to show success message
      setTimeout(() => {
        closeModal();
      }, 1500);

    } catch (err) {
      setTransient(setError, err.message);
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (row) => {
    if (!confirm(`Are you sure you want to delete site "${row.site_name}"?`)) return;

    try {
      await apiCall(`/delete-site/${row.site_id}`, {
        method: 'DELETE'
      });

      setTransient(setSuccess, 'Site deleted successfully!');
      fetchSites(currentPage, searchTerm);
    } catch (err) {
      setTransient(setError, err.message);
    }
  };

  const totalPages = Math.ceil(total / ROWS_PER_PAGE);

  return (
    <div className="dismantling-container">
      <div className="dismantling-header-row">
        <h2>Sites</h2>
        <div style={{ display: 'flex', gap: 16 }}>
          <button
            className={`upload-btn ${!selectedProject ? 'disabled' : ''}`}
            onClick={openCreateModal}
            disabled={!selectedProject}
            title={!selectedProject ? "Select a project first" : "Create a new site"}
          >
            + New Site
          </button>
          <label
            className={`upload-btn ${uploading || !selectedProject ? 'disabled' : ''}`}
            title={!selectedProject ? "Select a project first" : "Upload sites CSV"}
          >
            📤 Upload Sites CSV
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

      <div className="dismantling-search-container">
      <input
          type="text"
          placeholder="Filter by Site ID, Site Name"
          value={searchTerm}
          onChange={onSearchChange}
          className="search-input"
        />
        <select
          className="search-input"
          value={selectedProject}
          onChange={(e) => setSelectedProject(e.target.value)}
        >
          <option value="">-- Select a Project --</option>
          {projects.map((p) => (
            <option key={p.pid_po} value={p.pid_po}>
              {p.project_name} ({p.pid_po})
            </option>
          ))}
        </select>
        
        {searchTerm && (
          <button onClick={() => { setSearchTerm(''); fetchSites(1, ''); }} className="clear-btn">Clear</button>
        )}
      </div>

      {error && <div className="dismantling-message error">{error}</div>}
      {success && <div className="dismantling-message success">{success}</div>}
      {loading && <div className="loading-message">Loading site records...</div>}

      <div className="dismantling-table-container">
        <table className="dismantling-table">
          <thead>
            <tr>
              <th style={{ textAlign: 'center' }}>Site ID</th>
              <th style={{ textAlign: 'center' }}>Site Name</th>
              <th style={{ textAlign: 'center' }}>Project ID</th>
              <th style={{ textAlign: 'center', width: '110px' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 && !loading ? (
              <tr>
                <td colSpan={4} className="no-results">No results</td>
              </tr>
            ) : (
              rows.map((row) => (
                <tr key={row.id}>
                  <td style={{ textAlign: 'center' }}>{row.site_id}</td>
                  <td style={{ textAlign: 'center' }}>{row.site_name}</td>
                  <td style={{ textAlign: 'center' }}>{row.pid_po}</td>
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

      {totalPages > 1 && (
        <div className="dismantling-pagination">
          <button className="pagination-btn" disabled={currentPage === 1} onClick={() => fetchSites(currentPage - 1, searchTerm)}>Prev</button>
          <span className="pagination-info">Page {currentPage} of {totalPages}</span>
          <button className="pagination-btn" disabled={currentPage === totalPages} onClick={() => fetchSites(currentPage + 1, searchTerm)}>Next</button>
        </div>
      )}

      {showForm && (
        <div className="modal-overlay">
          <div className="modal-content">
            <form className="project-form" onSubmit={handleSubmit}>
              <div className="modal-header-row" style={{ justifyContent: 'space-between' }}>
                <h3 className="modal-title">
                  {editingRow ? `Editing Site: '${editingRow.site_name}'` : 'New Site'}
                </h3>
                <button className="modal-close-btn" onClick={closeModal} type="button">&times;</button>
              </div>

              {error && <div className="dismantling-message error">{error}</div>}
              {success && <div className="dismantling-message success">{success}</div>}

              <input
                className="search-input"
                type="text"
                name="pid_po"
                placeholder="Project ID (pid_po)"
                value={formData.pid_po}
                onChange={handleInputChange}
                required
                disabled={true}
                style={{ backgroundColor: '#f5f5f5', cursor: 'not-allowed' }}
              />
              
              <input
                className="search-input"
                type="text"
                name="site_id"
                placeholder="Site ID"
                value={formData.site_id}
                onChange={handleInputChange}
                required
                disabled={!!editingRow}
              />
              
              <input
                className="search-input"
                type="text"
                name="site_name"
                placeholder="Site Name"
                value={formData.site_name}
                onChange={handleInputChange}
                required
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