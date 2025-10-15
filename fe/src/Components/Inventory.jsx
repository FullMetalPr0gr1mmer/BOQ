import React, { useEffect, useState, useRef } from 'react';
import { apiCall, setTransient } from '../api.js';
import '../css/Inventory.css';

export default function Inventory() {
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
  const [stats, setStats] = useState({ total_items: 0, unique_sites: 0 });
  const [visibleCardStart, setVisibleCardStart] = useState(0);
  const [showHelpModal, setShowHelpModal] = useState(false);
  const fetchAbort = useRef(null);

  const initialForm = {
    site_id: '', site_name: '', slot_id: '', port_id: '', status: '',
    company_id: '', mnemonic: '', clei_code: '', part_no: '', software_no: '',
    factory_id: '', serial_no: '', date_id: '', manufactured_date: '',
    customer_field: '', license_points_consumed: '', alarm_status: '',
    Aggregated_alarm_status: '', upl_line: '', pid_po: ''
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

  const fetchStats = async (projectId = '') => {
    try {
      const params = new URLSearchParams();
      if (projectId) params.append('project_id', projectId);

      const data = await apiCall(`/inventory/stats?${params.toString()}`, {
        method: 'GET'
      });
      setStats(data);
    } catch (err) {
      console.error('Failed to fetch stats:', err);
    }
  };

  const fetchInventory = async (page = 1, search = '', limit = rowsPerPage, projectId = selectedProject) => {
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

      const data = await apiCall(`/inventory?${params.toString()}`, {
        signal: controller.signal,
        method: 'GET'
      });
      setRows(data.records || []);
      setTotal(data.total || 0);
      setCurrentPage(page);
    } catch (err) {
      if (err.name !== 'AbortError') setTransient(setError, err.message || 'Failed to fetch inventory');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProjects();
    fetchInventory(1, '', rowsPerPage, '');
    fetchStats('');
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleProjectChange = (e) => {
    const projectId = e.target.value;
    setSelectedProject(projectId);
    setSearchTerm('');
    setCurrentPage(1);
    fetchInventory(1, '', rowsPerPage, projectId);
    fetchStats(projectId);
  };

  const onSearchChange = (e) => {
    const v = e.target.value;
    setSearchTerm(v);
    fetchInventory(1, v);
  };

  const openCreateForm = () => {
    if (!selectedProject) {
      setTransient(setError, 'Please select a project to create a new inventory.');
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
    setFormData({ ...item });
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
      const payload = {
        ...formData,
        slot_id: parseInt(formData.slot_id || 0),
        port_id: parseInt(formData.port_id || 0),
      };

      if (isEditing && editingId !== null) {
        await apiCall(`/update-inventory/${editingId}`, {
          method: 'PUT',
          body: JSON.stringify(payload)
        });
      } else {
        await apiCall('/create-inventory', {
          method: 'POST',
          body: JSON.stringify(payload)
        });
      }

      setTransient(setSuccess, isEditing ? 'Inventory updated' : 'Inventory created');
      setShowForm(false);
      fetchInventory(currentPage, searchTerm, rowsPerPage);
    } catch (err) {
      setTransient(setError, err.message || 'Operation failed');
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this inventory item?')) return;
    try {
      await apiCall(`/delete-inventory/${id}`, {
        method: 'DELETE'
      });
      setTransient(setSuccess, 'Inventory deleted');
      fetchInventory(currentPage, searchTerm, rowsPerPage);
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
      const result = await apiCall('/upload-inventory-csv', {
        method: "POST",
        body: formData
      });
      setTransient(setSuccess, `Upload successful! ${result.inserted_count} rows inserted.`);
      fetchInventory(1, searchTerm, rowsPerPage);
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
    setCurrentPage(1); // Reset to first page
    fetchInventory(1, searchTerm, newLimit);
  };

  // Define all stat cards
  const allCards = [
    { label: 'Total Items', value: stats.total_items },
    { label: 'Unique Sites', value: stats.unique_sites },
    { label: 'Current Page', value: `${currentPage} / ${totalPages || 1}` },
    { label: 'Showing', value: `${rows.length} items` },
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
    <div className="inventory-container">
      {/* Header Section */}
      <div className="inventory-header">
        <div className="header-left">
          <div className="title-row">
            <button
              className="info-btn"
              onClick={() => setShowHelpModal(true)}
              title="How to use this component"
            >
              <span className="info-icon">i</span>
            </button>
            <h1 className="page-title">Inventory Management</h1>
          </div>
          <p className="page-subtitle">Manage and track your inventory items</p>
        </div>
        <div className="header-actions">
          <button
            className={`btn-primary ${!selectedProject ? 'disabled' : ''}`}
            onClick={openCreateForm}
            disabled={!selectedProject}
            title={!selectedProject ? "Select a project first" : "Create a new inventory"}
          >
            <span className="btn-icon">+</span>
            New Item
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
      <div className="inventory-filters">
        <div className="filter-group">
          <label className="filter-label">Search</label>
          <input
            type="text"
            placeholder="Search by Site ID..."
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
          <button onClick={() => { setSearchTerm(''); fetchInventory(1, ''); }} className="btn-clear">
            Clear Search
          </button>
        )}
      </div>

      {/* Messages */}
      {error && <div className="message error-message">{error}</div>}
      {success && <div className="message success-message">{success}</div>}
      {loading && <div className="loading-indicator">Loading inventory...</div>}

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
      <div className="inventory-table-wrapper">
        <table className="inventory-table">
          <thead>
            <tr>
              <th>Site ID</th>
              <th>Site Name</th>
              <th>Slot ID</th>
              <th>Port ID</th>
              <th>Status</th>
              <th>Company ID</th>
              <th>Mnemonic</th>
              <th>CLEI Code</th>
              <th>Part No</th>
              <th>Software No</th>
              <th>Factory ID</th>
              <th>Serial No</th>
              <th>Date ID</th>
              <th>Mfg. Date</th>
              <th>Customer</th>
              <th>License Pts</th>
              <th>Alarm</th>
              <th>Agg. Alarm</th>
              <th>UPL Line</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 && !loading ? (
              <tr><td colSpan={20} className="no-data">No inventory items found</td></tr>
            ) : (
              rows.map(item => (
                <tr key={item.id}>
                  <td>{item.site_id}</td>
                  <td>{item.site_name}</td>
                  <td>{item.slot_id}</td>
                  <td>{item.port_id}</td>
                  <td><span className="status-badge">{item.status}</span></td>
                  <td>{item.company_id}</td>
                  <td>{item.mnemonic}</td>
                  <td>{item.clei_code}</td>
                  <td>{item.part_no}</td>
                  <td>{item.software_no}</td>
                  <td>{item.factory_id}</td>
                  <td>{item.serial_no}</td>
                  <td>{item.date_id}</td>
                  <td>{item.manufactured_date}</td>
                  <td>{item.customer_field}</td>
                  <td>{item.license_points_consumed}</td>
                  <td>{item.alarm_status}</td>
                  <td>{item.Aggregated_alarm_status}</td>
                  <td>{item.upl_line || 'N/A'}</td>
                  <td>
                    <div className="action-buttons">
                      <button className="btn-action btn-edit" onClick={() => openEditForm(item)} title="Edit">
                        ✏️
                      </button>
                      <button className="btn-action btn-delete" onClick={() => handleDelete(item.id)} title="Delete">
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
            onClick={() => fetchInventory(currentPage - 1, searchTerm, rowsPerPage)}
          >
            ← Previous
          </button>
          <span className="pagination-info">
            Page <strong>{currentPage}</strong> of <strong>{totalPages}</strong>
          </span>
          <button
            className="pagination-btn"
            disabled={currentPage === totalPages}
            onClick={() => fetchInventory(currentPage + 1, searchTerm, rowsPerPage)}
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
                {isEditing ? `Edit Inventory Item #${editingId}` : 'Create New Inventory Item'}
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
                  <div className="form-field">
                    <label>Slot ID *</label>
                    <input
                      type="number"
                      name="slot_id"
                      value={formData.slot_id}
                      onChange={handleChange}
                      required
                    />
                  </div>
                  <div className="form-field">
                    <label>Port ID *</label>
                    <input
                      type="number"
                      name="port_id"
                      value={formData.port_id}
                      onChange={handleChange}
                      required
                    />
                  </div>
                  <div className="form-field">
                    <label>Status *</label>
                    <input
                      type="text"
                      name="status"
                      value={formData.status}
                      onChange={handleChange}
                      required
                    />
                  </div>
                  <div className="form-field">
                    <label>Company ID *</label>
                    <input
                      type="text"
                      name="company_id"
                      value={formData.company_id}
                      onChange={handleChange}
                      required
                    />
                  </div>
                </div>
              </div>

              {/* Hardware Details Section */}
              <div className="form-section">
                <h3 className="section-title">Hardware Details</h3>
                <div className="form-grid">
                  <div className="form-field">
                    <label>Mnemonic *</label>
                    <input
                      type="text"
                      name="mnemonic"
                      value={formData.mnemonic}
                      onChange={handleChange}
                      required
                    />
                  </div>
                  <div className="form-field">
                    <label>CLEI Code *</label>
                    <input
                      type="text"
                      name="clei_code"
                      value={formData.clei_code}
                      onChange={handleChange}
                      required
                    />
                  </div>
                  <div className="form-field">
                    <label>Part Number *</label>
                    <input
                      type="text"
                      name="part_no"
                      value={formData.part_no}
                      onChange={handleChange}
                      required
                    />
                  </div>
                  <div className="form-field">
                    <label>Software Part No *</label>
                    <input
                      type="text"
                      name="software_no"
                      value={formData.software_no}
                      onChange={handleChange}
                      required
                    />
                  </div>
                  <div className="form-field">
                    <label>Factory ID *</label>
                    <input
                      type="text"
                      name="factory_id"
                      value={formData.factory_id}
                      onChange={handleChange}
                      required
                    />
                  </div>
                  <div className="form-field">
                    <label>Serial Number *</label>
                    <input
                      type="text"
                      name="serial_no"
                      value={formData.serial_no}
                      onChange={handleChange}
                      required
                    />
                  </div>
                </div>
              </div>

              {/* Manufacturing & Dates Section */}
              <div className="form-section">
                <h3 className="section-title">Manufacturing Information</h3>
                <div className="form-grid">
                  <div className="form-field">
                    <label>Date ID *</label>
                    <input
                      type="text"
                      name="date_id"
                      value={formData.date_id}
                      onChange={handleChange}
                      required
                    />
                  </div>
                  <div className="form-field">
                    <label>Manufactured Date *</label>
                    <input
                      type="text"
                      name="manufactured_date"
                      value={formData.manufactured_date}
                      onChange={handleChange}
                      required
                    />
                  </div>
                  <div className="form-field">
                    <label>Customer Field *</label>
                    <input
                      type="text"
                      name="customer_field"
                      value={formData.customer_field}
                      onChange={handleChange}
                      required
                    />
                  </div>
                  <div className="form-field">
                    <label>License Points *</label>
                    <input
                      type="text"
                      name="license_points_consumed"
                      value={formData.license_points_consumed}
                      onChange={handleChange}
                      required
                    />
                  </div>
                </div>
              </div>

              {/* Status & Alarms Section */}
              <div className="form-section">
                <h3 className="section-title">Status & Alarms</h3>
                <div className="form-grid">
                  <div className="form-field">
                    <label>Alarm Status *</label>
                    <input
                      type="text"
                      name="alarm_status"
                      value={formData.alarm_status}
                      onChange={handleChange}
                      required
                    />
                  </div>
                  <div className="form-field">
                    <label>Aggregated Alarm Status *</label>
                    <input
                      type="text"
                      name="Aggregated_alarm_status"
                      value={formData.Aggregated_alarm_status}
                      onChange={handleChange}
                      required
                    />
                  </div>
                  <div className="form-field">
                    <label>UPL Line</label>
                    <input
                      type="text"
                      name="upl_line"
                      value={formData.upl_line}
                      onChange={handleChange}
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
                  {isEditing ? 'Update Inventory' : 'Create Inventory'}
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
              <h2 className="modal-title">Inventory Management - User Guide</h2>
              <button className="modal-close" onClick={() => setShowHelpModal(false)} type="button">
                ✕
              </button>
            </div>

            <div className="help-content">
              {/* Overview Section */}
              <div className="help-section">
                <h3 className="help-section-title">📋 Overview</h3>
                <p className="help-text">
                  The Inventory Management component allows you to create, view, edit, and delete inventory items
                  for your projects. You can also bulk upload inventory data using CSV files and filter items by project.
                </p>
              </div>

              {/* Features Section */}
              <div className="help-section">
                <h3 className="help-section-title">✨ Features & Buttons</h3>
                <ul className="help-list">
                  <li>
                    <strong>+ New Item:</strong> Opens a form to create a new inventory item. You must select a project first.
                  </li>
                  <li>
                    <strong>📤 Upload CSV:</strong> Allows you to bulk upload inventory items from a CSV file. Select a project before uploading.
                  </li>
                  <li>
                    <strong>Search:</strong> Filter inventory items by Site ID in real-time.
                  </li>
                  <li>
                    <strong>Project Dropdown:</strong> Filter all inventory items and statistics by the selected project.
                  </li>
                  <li>
                    <strong>Clear Search:</strong> Resets the search filter and shows all items for the selected project.
                  </li>
                  <li>
                    <strong>✏️ Edit:</strong> Click on any row's edit button to modify that inventory item.
                  </li>
                  <li>
                    <strong>🗑️ Delete:</strong> Click on any row's delete button to remove that inventory item (requires confirmation).
                  </li>
                  <li>
                    <strong>‹ › Navigation Arrows:</strong> Cycle through statistics cards to view different metrics.
                  </li>
                  <li>
                    <strong>Rows Per Page Dropdown:</strong> Change how many items are displayed per page (50-500).
                  </li>
                </ul>
              </div>

              {/* Statistics Section */}
              <div className="help-section">
                <h3 className="help-section-title">📊 Statistics Cards</h3>
                <ul className="help-list">
                  <li><strong>Total Items:</strong> Total count of inventory items for the selected project (or all projects if none selected).</li>
                  <li><strong>Unique Sites:</strong> Number of distinct site IDs in the inventory.</li>
                  <li><strong>Current Page:</strong> Shows which page you're viewing out of total pages.</li>
                  <li><strong>Showing:</strong> Number of items currently displayed on this page.</li>
                  <li><strong>Rows Per Page:</strong> Adjustable dropdown to control pagination size.</li>
                </ul>
              </div>

              {/* CSV Upload Section */}
              <div className="help-section">
                <h3 className="help-section-title">📁 CSV Upload Guidelines</h3>
                <p className="help-text">
                  To upload inventory items via CSV, your file must contain the following headers (in any order):
                </p>
                <div className="csv-headers">
                  <code>site_id</code>, <code>site_name</code>, <code>slot_id</code>, <code>port_id</code>,
                  <code>status</code>, <code>company_id</code>, <code>mnemonic</code>, <code>clei_code</code>,
                  <code>part_no</code>, <code>software_no</code>, <code>factory_id</code>, <code>serial_no</code>,
                  <code>date_id</code>, <code>manufactured_date</code>, <code>customer_field</code>,
                  <code>license_points_consumed</code>, <code>alarm_status</code>, <code>Aggregated_alarm_status</code>
                </div>
                <p className="help-text help-note">
                  <strong>Note:</strong> Make sure to select a project before uploading. The CSV data will be associated
                  with the selected project automatically.
                </p>
              </div>

              {/* Tips Section */}
              <div className="help-section">
                <h3 className="help-section-title">💡 Tips</h3>
                <ul className="help-list">
                  <li>Always select a project before creating items or uploading CSV files.</li>
                  <li>Use the search feature to quickly find items by Site ID.</li>
                  <li>The table scrolls horizontally - use the scrollbar at the bottom to see all columns.</li>
                  <li>Statistics update automatically when you filter by project or search.</li>
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
