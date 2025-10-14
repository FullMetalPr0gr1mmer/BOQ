import React, { useEffect, useState, useRef } from 'react';
import { apiCall, setTransient } from '../api.js';
import '../css/Site.css';

export default function Site() {
  const [rows, setRows] = useState([]);
  const [currentPage, setCurrentPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(50);
  const [showForm, setShowForm] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const [projects, setProjects] = useState([]);
  const [selectedProject, setSelectedProject] = useState('');
  const [stats, setStats] = useState({ total_sites: 0, total_projects: 0 });
  const [visibleCardStart, setVisibleCardStart] = useState(0);
  const [showHelpModal, setShowHelpModal] = useState(false);
  const fetchAbort = useRef(null);

  const initialForm = {
    site_id: '',
    site_name: '',
    pid_po: ''
  };
  const [formData, setFormData] = useState(initialForm);

  const fetchProjects = async () => {
    try {
      const data = await apiCall('/get_project');
      setProjects(data || []);
      if (data && data.length > 0) {
        setSelectedProject(data[0].pid_po);
      }
    } catch (err) {
      setTransient(setError, 'Failed to load projects. Please ensure you have project access.');
      console.error(err);
    }
  };

  const fetchStats = async () => {
    try {
      const data = await apiCall('/sites/stats', {
        method: 'GET'
      });
      setStats(data);
    } catch (err) {
      console.error('Failed to fetch stats:', err);
    }
  };

  const fetchSites = async (page = 1, search = '', limit = rowsPerPage, projectId = selectedProject) => {
    try {
      if (fetchAbort.current) fetchAbort.current.abort();
      const controller = new AbortController();
      fetchAbort.current = controller;

      setLoading(true);
      setError('');
      const skip = (page - 1) * limit;
      const params = new URLSearchParams({
        skip: String(skip),
        limit: String(limit),
        search: search.trim(),
      });

      if (projectId) params.append('project_id', projectId);

      const data = await apiCall(`/sites?${params.toString()}`, {
        signal: controller.signal,
        method: 'GET'
      });
      setRows(data.records || []);
      setTotal(data.total || 0);
      setCurrentPage(page);
    } catch (err) {
      if (err.name !== 'AbortError') setTransient(setError, err.message || 'Failed to fetch sites');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProjects();
    fetchSites(1, '', rowsPerPage, '');
    fetchStats();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleProjectChange = (e) => {
    const projectId = e.target.value;
    setSelectedProject(projectId);
    setSearchTerm('');
    setCurrentPage(1);
    fetchSites(1, '', rowsPerPage, projectId);
  };

  const onSearchChange = (e) => {
    const v = e.target.value;
    setSearchTerm(v);
    fetchSites(1, v);
  };

  const openCreateForm = () => {
    if (!selectedProject) {
      setTransient(setError, 'Please select a project to create a new site.');
      return;
    }
    setFormData({ ...initialForm, pid_po: selectedProject });
    setIsEditing(false);
    setEditingId(null);
    setShowForm(true);
    setError('');
    setSuccess('');
  };

  const openEditForm = (item) => {
    setFormData({
      site_id: item.site_id,
      site_name: item.site_name,
      pid_po: item.pid_po
    });
    setIsEditing(true);
    setEditingId(item.id);
    setShowForm(true);
    setError('');
    setSuccess('');
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    try {
      if (isEditing && editingId !== null) {
        await apiCall(`/update-site/${editingId}`, {
          method: 'PUT',
          body: JSON.stringify(formData)
        });
      } else {
        await apiCall('/add-site', {
          method: 'POST',
          body: JSON.stringify(formData)
        });
      }

      setTransient(setSuccess, isEditing ? 'Site updated' : 'Site created');
      setShowForm(false);
      fetchSites(currentPage, searchTerm, rowsPerPage);
      fetchStats();
    } catch (err) {
      setTransient(setError, err.message || 'Operation failed');
    }
  };

  const handleDelete = async (siteId) => {
    if (!window.confirm('Delete this site?')) return;
    try {
      await apiCall(`/delete-site/${siteId}`, {
        method: 'DELETE'
      });
      setTransient(setSuccess, 'Site deleted');
      fetchSites(currentPage, searchTerm, rowsPerPage);
      fetchStats();
    } catch (err) {
      setTransient(setError, err.message || 'Delete failed');
    }
  };

  const handleUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    if (!selectedProject) {
      setTransient(setError, 'Please select a project before uploading CSV.');
      e.target.value = "";
      return;
    }

    setUploading(true);
    setError('');
    setSuccess('');
    const formData = new FormData();
    formData.append("file", file);
    formData.append("pid_po", selectedProject);
    try {
      const result = await apiCall('/sites/upload-csv', {
        method: "POST",
        body: formData
      });
      setTransient(setSuccess, `Upload successful! ${result.inserted} sites inserted.`);
      fetchSites(1, searchTerm, rowsPerPage);
      fetchStats();
    } catch (err) {
      setTransient(setError, err.message);
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  };

  const totalPages = Math.ceil(total / rowsPerPage);

  const handleRowsPerPageChange = (e) => {
    const newLimit = parseInt(e.target.value);
    setRowsPerPage(newLimit);
    setCurrentPage(1);
    fetchSites(1, searchTerm, newLimit);
  };

  // Define all stat cards
  const allCards = [
    { label: 'Total Sites', value: stats.total_sites },
    { label: 'Total Projects', value: stats.total_projects },
    { label: 'Current Page', value: `${currentPage} / ${totalPages || 1}` },
    { label: 'Showing', value: `${rows.length} sites` },
    {
      label: 'Rows Per Page',
      isEditable: true,
      component: (
        <select
          className="stat-select"
          value={rowsPerPage}
          onChange={handleRowsPerPageChange}
        >
          <option value={50}>50</option>
          <option value={100}>100</option>
          <option value={150}>150</option>
          <option value={200}>200</option>
          <option value={250}>250</option>
          <option value={500}>500</option>
        </select>
      )
    }
  ];

  const handlePrevCard = () => {
    setVisibleCardStart((prev) => (prev > 0 ? prev - 1 : allCards.length - 1));
  };

  const handleNextCard = () => {
    setVisibleCardStart((prev) => (prev < allCards.length - 1 ? prev + 1 : 0));
  };

  const getVisibleCards = () => {
    const visible = [];
    for (let i = 0; i < 3; i++) {
      const index = (visibleCardStart + i) % allCards.length;
      visible.push(allCards[index]);
    }
    return visible;
  };

  return (
    <div className="site-container">
      {/* Header Section */}
      <div className="site-header">
        <div className="header-left">
          <div className="title-row">
            <button
              className="info-btn"
              onClick={() => setShowHelpModal(true)}
              title="How to use this component"
            >
              <span className="info-icon">i</span>
            </button>
            <h1 className="page-title">Site Management</h1>
          </div>
          <p className="page-subtitle">Manage and track your sites</p>
        </div>
        <div className="header-actions">
          <button
            className={`btn-primary ${!selectedProject ? 'disabled' : ''}`}
            onClick={openCreateForm}
            disabled={!selectedProject}
            title={!selectedProject ? "Select a project first" : "Create a new site"}
          >
            <span className="btn-icon">+</span>
            New Site
          </button>
          <label className={`btn-secondary ${uploading || !selectedProject ? 'disabled' : ''}`}>
            <span className="btn-icon">📤</span>
            Upload CSV
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

      {/* Filters Section */}
      <div className="site-filters">
        <div className="filter-group">
          <label className="filter-label">Search</label>
          <input
            type="text"
            placeholder="Search by Site ID or Name..."
            value={searchTerm}
            onChange={onSearchChange}
            className="filter-input"
          />
        </div>
        <div className="filter-group">
          <label className="filter-label">Project</label>
          <select
            className="filter-select"
            value={selectedProject}
            onChange={handleProjectChange}
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
          <button onClick={() => { setSearchTerm(''); fetchSites(1, ''); }} className="btn-clear">
            Clear Search
          </button>
        )}
      </div>

      {/* Messages */}
      {error && <div className="message error-message">{error}</div>}
      {success && <div className="message success-message">{success}</div>}
      {loading && <div className="loading-indicator">Loading sites...</div>}

      {/* Stats Bar - Carousel Style (3 cards visible) */}
      <div className="stats-bar-container">
        <button
          className="stats-nav-btn stats-nav-left"
          onClick={handlePrevCard}
          title="Previous card"
        >
          ‹
        </button>
        <div className="stats-bar">
          {getVisibleCards().map((card, idx) => (
            <div
              key={`${card.label}-${idx}`}
              className={`stat-item ${card.isEditable ? 'stat-item-editable' : ''}`}
            >
              <span className="stat-label">{card.label}</span>
              {card.isEditable ? (
                card.component
              ) : (
                <span className="stat-value">{card.value}</span>
              )}
            </div>
          ))}
        </div>
        <button
          className="stats-nav-btn stats-nav-right"
          onClick={handleNextCard}
          title="Next card"
        >
          ›
        </button>
      </div>

      {/* Table Section */}
      <div className="site-table-wrapper">
        <table className="site-table">
          <thead>
            <tr>
              <th>Site ID</th>
              <th>Site Name</th>
              <th>Project ID</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 && !loading ? (
              <tr><td colSpan={4} className="no-data">No sites found</td></tr>
            ) : (
              rows.map(item => (
                <tr key={item.id}>
                  <td>{item.site_id}</td>
                  <td>{item.site_name}</td>
                  <td>{item.pid_po}</td>
                  <td>
                    <div className="action-buttons">
                      <button className="btn-action btn-edit" onClick={() => openEditForm(item)} title="Edit">
                        ✏️
                      </button>
                      <button className="btn-action btn-delete" onClick={() => handleDelete(item.site_id)} title="Delete">
                        🗑️
                      </button>
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
        <div className="pagination">
          <button
            className="pagination-btn"
            disabled={currentPage === 1}
            onClick={() => fetchSites(currentPage - 1, searchTerm, rowsPerPage)}
          >
            ← Previous
          </button>
          <span className="pagination-info">
            Page <strong>{currentPage}</strong> of <strong>{totalPages}</strong>
          </span>
          <button
            className="pagination-btn"
            disabled={currentPage === totalPages}
            onClick={() => fetchSites(currentPage + 1, searchTerm, rowsPerPage)}
          >
            Next →
          </button>
        </div>
      )}

      {/* Modal Form */}
      {showForm && (
        <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && setShowForm(false)}>
          <div className="modal-container">
            <div className="modal-header">
              <h2 className="modal-title">
                {isEditing ? `Edit Site: ${formData.site_id}` : 'Create New Site'}
              </h2>
              <button className="modal-close" onClick={() => setShowForm(false)} type="button">
                ✕
              </button>
            </div>

            <form className="modal-form" onSubmit={handleSubmit}>
              {/* Project Info Section */}
              <div className="form-section">
                <h3 className="section-title">Project Information</h3>
                <div className="form-grid">
                  <div className="form-field full-width">
                    <label>Project ID</label>
                    <input
                      type="text"
                      name="pid_po"
                      value={formData.pid_po}
                      onChange={handleChange}
                      required
                      disabled
                      className="disabled-input"
                    />
                  </div>
                </div>
              </div>

              {/* Site Information Section */}
              <div className="form-section">
                <h3 className="section-title">Site Information</h3>
                <div className="form-grid">
                  <div className="form-field">
                    <label>Site ID *</label>
                    <input
                      type="text"
                      name="site_id"
                      value={formData.site_id}
                      onChange={handleChange}
                      disabled={isEditing}
                      required
                    />
                  </div>
                  <div className="form-field">
                    <label>Site Name *</label>
                    <input
                      type="text"
                      name="site_name"
                      value={formData.site_name}
                      onChange={handleChange}
                      required
                    />
                  </div>
                </div>
              </div>

              {/* Form Actions */}
              <div className="form-actions">
                <button type="button" className="btn-cancel" onClick={() => setShowForm(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn-submit">
                  {isEditing ? 'Update Site' : 'Create Site'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Help/Info Modal */}
      {showHelpModal && (
        <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && setShowHelpModal(false)}>
          <div className="modal-container help-modal">
            <div className="modal-header">
              <h2 className="modal-title">Site Management - User Guide</h2>
              <button className="modal-close" onClick={() => setShowHelpModal(false)} type="button">
                ✕
              </button>
            </div>

            <div className="help-content">
              {/* Overview Section */}
              <div className="help-section">
                <h3 className="help-section-title">📋 Overview</h3>
                <p className="help-text">
                  The Site Management component allows you to create, view, edit, and delete sites
                  for your projects. You can also bulk upload site data using CSV files.
                </p>
              </div>

              {/* Features Section */}
              <div className="help-section">
                <h3 className="help-section-title">✨ Features & Buttons</h3>
                <ul className="help-list">
                  <li>
                    <strong>+ New Site:</strong> Opens a form to create a new site. You must select a project first.
                  </li>
                  <li>
                    <strong>📤 Upload CSV:</strong> Allows you to bulk upload sites from a CSV file. Select a project before uploading.
                  </li>
                  <li>
                    <strong>Search:</strong> Filter sites by Site ID or Site Name in real-time.
                  </li>
                  <li>
                    <strong>Project Dropdown:</strong> Filter all sites by the selected project.
                  </li>
                  <li>
                    <strong>Clear Search:</strong> Resets the search filter and shows all sites.
                  </li>
                  <li>
                    <strong>✏️ Edit:</strong> Click on any row's edit button to modify that site.
                  </li>
                  <li>
                    <strong>🗑️ Delete:</strong> Click on any row's delete button to remove that site (requires confirmation).
                  </li>
                  <li>
                    <strong>‹ › Navigation Arrows:</strong> Cycle through statistics cards to view different metrics.
                  </li>
                  <li>
                    <strong>Rows Per Page Dropdown:</strong> Change how many sites are displayed per page (50-500).
                  </li>
                </ul>
              </div>

              {/* Statistics Section */}
              <div className="help-section">
                <h3 className="help-section-title">📊 Statistics Cards</h3>
                <ul className="help-list">
                  <li><strong>Total Sites:</strong> Total count of sites in the system.</li>
                  <li><strong>Total Projects:</strong> Number of projects that have sites.</li>
                  <li><strong>Current Page:</strong> Shows which page you're viewing out of total pages.</li>
                  <li><strong>Showing:</strong> Number of sites currently displayed on this page.</li>
                  <li><strong>Rows Per Page:</strong> Adjustable dropdown to control pagination size.</li>
                </ul>
              </div>

              {/* CSV Upload Section */}
              <div className="help-section">
                <h3 className="help-section-title">📁 CSV Upload Guidelines</h3>
                <p className="help-text">
                  To upload sites via CSV, your file must contain link data with the following format:
                </p>
                <div className="csv-headers">
                  <code>LinkID</code>, <code>InterfaceName</code>, <code>SiteIPA</code>, <code>SiteIPB</code>
                </div>
                <p className="help-text">
                  Example: <code>JIZ0243-JIZ0169, eth0, 10.0.0.1, 10.0.0.2</code>
                </p>
                <p className="help-text help-note">
                  <strong>Note:</strong> Make sure to select a project before uploading. The system will automatically
                  parse the LinkID to extract site names and create sites accordingly.
                </p>
              </div>

              {/* Tips Section */}
              <div className="help-section">
                <h3 className="help-section-title">💡 Tips</h3>
                <ul className="help-list">
                  <li>Always select a project before creating sites or uploading CSV files.</li>
                  <li>Use the search feature to quickly find sites by ID or name.</li>
                  <li>Statistics update automatically when you add, edit, or delete sites.</li>
                  <li>Site IDs cannot be changed after creation for data integrity.</li>
                  <li>All required fields are marked with an asterisk (*) in the form.</li>
                </ul>
              </div>
            </div>

            <div className="help-footer">
              <button className="btn-submit" onClick={() => setShowHelpModal(false)}>
                Got it!
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
