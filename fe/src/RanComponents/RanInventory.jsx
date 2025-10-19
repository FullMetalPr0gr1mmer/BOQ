import React, { useState, useEffect, useRef } from "react";
import { apiCall, setTransient } from "../api.js";
import "../css/Inventory.css";
import StatsCarousel from '../Components/shared/StatsCarousel';
import FilterBar from '../Components/shared/FilterBar';
import DataTable from '../Components/shared/DataTable';
import HelpModal, { HelpList, HelpText, CodeBlock } from '../Components/shared/HelpModal';
import TitleWithInfo from '../Components/shared/InfoButton';
import Pagination from '../Components/shared/Pagination';

export default function RANInventory() {
  const [rows, setRows] = useState([]);
  const [currentPage, setCurrentPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(50);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [uploading, setUploading] = useState(false);
  const [loading, setLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const [showHelpModal, setShowHelpModal] = useState(false);

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingRow, setEditingRow] = useState(null);
  const [editForm, setEditForm] = useState({});
  const [updating, setUpdating] = useState(false);

  const [projects, setProjects] = useState([]);
  const [selectedProject, setSelectedProject] = useState('');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [createForm, setCreateForm] = useState({
    mrbts: '',
    site_id: '',
    identification_code: '',
    user_label: '',
    serial_number: '',
    duplicate: false,
    duplicate_remarks: '',
    pid_po: ''
  });
  const [creating, setCreating] = useState(false);
  const [stats, setStats] = useState({ total_items: 0, unique_sites: 0 });

  const fetchAbort = useRef(null);

  const fetchProjects = async () => {
    try {
      const data = await apiCall('/ran-projects');
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

      const data = await apiCall(`/raninventory/stats?${params.toString()}`, {
        method: 'GET'
      });
      setStats(data || { total_items: 0, unique_sites: 0 });
    } catch (err) {
      console.error('Failed to fetch stats:', err);
    }
  };

  const fetchInventory = async (page = 1, search = "", limit = rowsPerPage, projectId = selectedProject) => {
    try {
      if (fetchAbort.current) fetchAbort.current.abort();
      const controller = new AbortController();
      fetchAbort.current = controller;

      setLoading(true);
      setError("");
      const skip = (page - 1) * limit;
      const params = new URLSearchParams({
        skip: String(skip),
        limit: String(limit)
      });

      if (search.trim()) params.append('search', search.trim());
      if (projectId) params.append('project_id', projectId);

      const { records, total } = await apiCall(`/raninventory?${params.toString()}`, {
        signal: controller.signal,
      });

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
          pid_po: r.pid_po,
        }))
      );
      setTotal(total || 0);
      setCurrentPage(page);
    } catch (err) {
      if (err.name !== "AbortError") setTransient(setError, err.message || "Failed to fetch records");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProjects();
    fetchInventory(1, "", rowsPerPage, '');
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
    const formData = new FormData();
    formData.append("file", file);
    formData.append("pid_po", selectedProject);

    try {
      const result = await apiCall('/raninventory/upload-csv', {
        method: "POST",
        body: formData,
      });
      setTransient(setSuccess, `Upload successful! ${result.message}`);
      fetchInventory(1, searchTerm);
      fetchStats(selectedProject);
    } catch (err) {
      setTransient(setError, err.message);
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  };

  const handleDelete = async (row) => {
    if (!window.confirm("Are you sure you want to delete this record?")) return;
    try {
      await apiCall(`/raninventory/${row.id}`, {
        method: "DELETE",
      });
      setTransient(setSuccess, "Record deleted successfully");
      fetchInventory(currentPage, searchTerm);
      fetchStats(selectedProject);
    } catch (err) {
      setTransient(setError, err.message);
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
      await apiCall(`/raninventory/${editingRow.id}`, {
        method: "PUT",
        body: JSON.stringify(editForm),
      });
      setTransient(setSuccess, "Record updated successfully!");
      closeModal();
      fetchInventory(currentPage, searchTerm);
      fetchStats(selectedProject);
    } catch (err) {
      setTransient(setError, err.message);
    } finally {
      setUpdating(false);
    }
  };

  const openCreateModal = () => {
    if (!selectedProject) {
      setTransient(setError, 'Please select a project to create a new record.');
      return;
    }
    setCreateForm({
      mrbts: '',
      site_id: '',
      identification_code: '',
      user_label: '',
      serial_number: '',
      duplicate: false,
      duplicate_remarks: '',
      pid_po: selectedProject
    });
    setShowCreateModal(true);
    setError('');
    setSuccess('');
  };

  const closeCreateModal = () => {
    setShowCreateModal(false);
    setCreateForm({
      mrbts: '',
      site_id: '',
      identification_code: '',
      user_label: '',
      serial_number: '',
      duplicate: false,
      duplicate_remarks: '',
      pid_po: ''
    });
    setError('');
    setSuccess('');
  };

  const onCreateChange = (key, value) => {
    setCreateForm((prev) => ({ ...prev, [key]: value }));
  };

  const handleCreate = async (e) => {
    e.preventDefault();
    setCreating(true);
    setError('');
    setSuccess('');
    try {
      await apiCall('/raninventory/', {
        method: 'POST',
        body: JSON.stringify(createForm),
      });
      setTransient(setSuccess, 'Record created successfully!');
      fetchInventory(currentPage, searchTerm);
      fetchStats(selectedProject);
      setTimeout(() => closeCreateModal(), 1200);
    } catch (err) {
      setTransient(setError, err.message);
    } finally {
      setCreating(false);
    }
  };

  const totalPages = Math.ceil(total / rowsPerPage);

  const handleRowsPerPageChange = (e) => {
    const newLimit = parseInt(e.target.value);
    setRowsPerPage(newLimit);
    setCurrentPage(1);
    fetchInventory(1, searchTerm, newLimit);
  };

  // Define stat cards
  const statCards = [
    { label: 'Total Items', value: stats.total_items || total },
    { label: 'Unique Sites', value: stats.unique_sites || 0 },
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
          <option value={25}>25</option>
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

  // Define table columns
  const tableColumns = [
    { key: 'mrbts', label: 'MRBTS' },
    { key: 'site_id', label: 'Site ID' },
    { key: 'identification_code', label: 'Identification Code' },
    { key: 'user_label', label: 'User Label' },
    { key: 'serial_number', label: 'Serial Number' },
    {
      key: 'duplicate',
      label: 'Duplicate',
      render: (row) => (
        <span className={`status-badge ${row.duplicate ? 'duplicate-yes' : 'duplicate-no'}`}>
          {row.duplicate ? 'Yes' : 'No'}
        </span>
      )
    },
    { key: 'duplicate_remarks', label: 'Duplicate Remarks' },
    { key: 'pid_po', label: 'Project' }
  ];

  // Define table actions
  const tableActions = [
    {
      icon: '✏️',
      onClick: (row) => openEditModal(row),
      title: 'Edit',
      className: 'btn-edit'
    },
    {
      icon: '🗑️',
      onClick: (row) => handleDelete(row),
      title: 'Delete',
      className: 'btn-delete'
    }
  ];

  // Help modal sections
  const helpSections = [
    {
      icon: '📋',
      title: 'Overview',
      content: (
        <HelpText>
          The RAN Inventory Management component allows you to create, view, edit, and delete RAN inventory items
          for your projects. You can also bulk upload inventory data using CSV files and filter items by project.
          This system helps you track MRBTS, site information, serial numbers, and identify duplicates.
        </HelpText>
      )
    },
    {
      icon: '✨',
      title: 'Features & Buttons',
      content: (
        <HelpList
          items={[
            { label: '+ New Record', text: 'Opens a form to create a new RAN inventory item. You must select a project first.' },
            { label: '📤 Upload CSV', text: 'Allows you to bulk upload RAN inventory items from a CSV file. Select a project before uploading.' },
            { label: 'Search', text: 'Filter inventory items by Site ID, MRBTS, or Serial Number in real-time.' },
            { label: 'Project Dropdown', text: 'Filter all inventory items and statistics by the selected project.' },
            { label: 'Clear Search', text: 'Resets the search filter and shows all items for the selected project.' },
            { label: '✏️ Edit', text: 'Click on any row\'s edit button to modify that inventory item.' },
            { label: '🗑️ Delete', text: 'Click on any row\'s delete button to remove that inventory item (requires confirmation).' },
            { label: 'Rows Per Page Dropdown', text: 'Change how many items are displayed per page (25-500).' }
          ]}
        />
      )
    },
    {
      icon: '📊',
      title: 'Statistics Cards',
      content: (
        <HelpList
          items={[
            { label: 'Total Items', text: 'Total count of RAN inventory items for the selected project (or all projects if none selected).' },
            { label: 'Unique Sites', text: 'Number of distinct site IDs in the RAN inventory.' },
            { label: 'Current Page', text: 'Shows which page you\'re viewing out of total pages.' },
            { label: 'Showing', text: 'Number of items currently displayed on this page.' },
            { label: 'Rows Per Page', text: 'Adjustable dropdown to control pagination size.' }
          ]}
        />
      )
    },
    {
      icon: '📁',
      title: 'CSV Upload Guidelines',
      content: (
        <>
          <HelpText>
            To upload RAN inventory items via CSV, your file must contain the following headers (in any order):
          </HelpText>
          <CodeBlock
            items={[
              'mrbts', 'site_id', 'identification_code', 'user_label', 'serial_number',
              'duplicate', 'duplicate_remarks'
            ]}
          />
          <HelpText isNote>
            <strong>Note:</strong> Make sure to select a project before uploading. The CSV data will be associated
            with the selected project automatically. The "duplicate" field should be "true" or "false".
          </HelpText>
        </>
      )
    },
    {
      icon: '🔍',
      title: 'Duplicate Detection',
      content: (
        <HelpText>
          The RAN Inventory system can flag duplicate entries. When creating or editing records, you can mark
          an item as a duplicate and add remarks explaining the duplication. Use the search feature to quickly
          find duplicate entries and manage them accordingly.
        </HelpText>
      )
    },
    {
      icon: '💡',
      title: 'Tips',
      content: (
        <HelpList
          items={[
            'Always select a project before creating items or uploading CSV files.',
            'Use the search feature to quickly find items by Site ID, MRBTS, or Serial Number.',
            'The table scrolls horizontally - use the scrollbar at the bottom to see all columns.',
            'Statistics update automatically when you filter by project or search.',
            'Mark duplicates and add remarks to help identify and manage duplicate entries.',
            'Serial numbers should be unique per site for easy tracking.'
          ]}
        />
      )
    }
  ];

  return (
    <div className="inventory-container">
      {/* Header Section */}
      <div className="inventory-header">
        <TitleWithInfo
          title="RAN Inventory Management"
          subtitle="Manage and track your RAN inventory items"
          onInfoClick={() => setShowHelpModal(true)}
          infoTooltip="How to use this component"
        />
        <div className="header-actions">
          <button
            className={`btn-primary ${!selectedProject ? 'disabled' : ''}`}
            onClick={openCreateModal}
            disabled={!selectedProject}
            title={!selectedProject ? "Select a project first" : "Create a new inventory"}
          >
            <span className="btn-icon">+</span>
            New Record
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
      <FilterBar
        searchTerm={searchTerm}
        onSearchChange={onSearchChange}
        searchPlaceholder="Search by Site ID, MRBTS, or Serial Number..."
        dropdowns={[
          {
            label: 'Project',
            value: selectedProject,
            onChange: handleProjectChange,
            placeholder: '-- Select a Project --',
            options: projects.map(p => ({
              value: p.pid_po,
              label: `${p.project_name} (${p.pid_po})`
            }))
          }
        ]}
        showClearButton={!!searchTerm}
        onClearSearch={() => { setSearchTerm(''); fetchInventory(1, ''); }}
        clearButtonText="Clear Search"
      />

      {/* Messages */}
      {error && <div className="message error-message">{error}</div>}
      {success && <div className="message success-message">{success}</div>}
      {loading && <div className="loading-indicator">Loading RAN Inventory...</div>}

      {/* Stats Bar - Carousel Style */}
      <StatsCarousel cards={statCards} visibleCount={4} />

      {/* Table Section */}
      <DataTable
        columns={tableColumns}
        data={rows}
        actions={tableActions}
        loading={loading}
        noDataMessage="No RAN inventory items found"
        className="inventory-table-wrapper"
      />

      {/* Pagination */}
      <Pagination
        currentPage={currentPage}
        totalPages={totalPages}
        onPageChange={(page) => fetchInventory(page, searchTerm, rowsPerPage)}
        previousText="← Previous"
        nextText="Next →"
      />

      {/* Create Modal */}
      {showCreateModal && (
        <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && setShowCreateModal(false)}>
          <div className="modal-container">
            <div className="modal-header">
              <h2 className="modal-title">Create New RAN Inventory Record</h2>
              <button className="modal-close" onClick={closeCreateModal} type="button">✕</button>
            </div>

            <form className="modal-form" onSubmit={handleCreate}>
              {error && <div className="message error-message">{error}</div>}
              {success && <div className="message success-message">{success}</div>}

              {/* Project Information */}
              <div className="form-section">
                <h3 className="section-title">Project Information</h3>
                <div className="form-grid">
                  <div className="form-field full-width">
                    <label>Project ID</label>
                    <input
                      type="text"
                      name="pid_po"
                      value={createForm.pid_po}
                      onChange={(e) => onCreateChange('pid_po', e.target.value)}
                      required
                      disabled
                      className="disabled-input"
                    />
                  </div>
                </div>
              </div>

              {/* Site & Equipment Information */}
              <div className="form-section">
                <h3 className="section-title">Site & Equipment Information</h3>
                <div className="form-grid">
                  <div className="form-field">
                    <label>MRBTS *</label>
                    <input
                      type="text"
                      name="mrbts"
                      value={createForm.mrbts}
                      onChange={(e) => onCreateChange('mrbts', e.target.value)}
                      required
                    />
                  </div>
                  <div className="form-field">
                    <label>Site ID *</label>
                    <input
                      type="text"
                      name="site_id"
                      value={createForm.site_id}
                      onChange={(e) => onCreateChange('site_id', e.target.value)}
                      required
                    />
                  </div>
                  <div className="form-field">
                    <label>Identification Code</label>
                    <input
                      type="text"
                      name="identification_code"
                      value={createForm.identification_code}
                      onChange={(e) => onCreateChange('identification_code', e.target.value)}
                    />
                  </div>
                  <div className="form-field">
                    <label>User Label</label>
                    <input
                      type="text"
                      name="user_label"
                      value={createForm.user_label}
                      onChange={(e) => onCreateChange('user_label', e.target.value)}
                    />
                  </div>
                  <div className="form-field">
                    <label>Serial Number *</label>
                    <input
                      type="text"
                      name="serial_number"
                      value={createForm.serial_number}
                      onChange={(e) => onCreateChange('serial_number', e.target.value)}
                      required
                    />
                  </div>
                </div>
              </div>

              {/* Duplicate Information */}
              <div className="form-section">
                <h3 className="section-title">Duplicate Information</h3>
                <div className="form-grid">
                  <div className="form-field">
                    <label className="checkbox-label">
                      <input
                        type="checkbox"
                        checked={createForm.duplicate}
                        onChange={(e) => onCreateChange('duplicate', e.target.checked)}
                      />
                      <span>Mark as Duplicate</span>
                    </label>
                  </div>
                  <div className="form-field full-width">
                    <label>Duplicate Remarks</label>
                    <input
                      type="text"
                      name="duplicate_remarks"
                      value={createForm.duplicate_remarks}
                      onChange={(e) => onCreateChange('duplicate_remarks', e.target.value)}
                      placeholder="Add remarks if this is a duplicate"
                    />
                  </div>
                </div>
              </div>

              {/* Form Actions */}
              <div className="form-actions">
                <button type="button" className="btn-cancel" onClick={closeCreateModal}>
                  Cancel
                </button>
                <button type="submit" className="btn-submit" disabled={creating}>
                  {creating ? 'Creating...' : 'Create Record'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Edit Modal */}
      {isModalOpen && (
        <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && setIsModalOpen(false)}>
          <div className="modal-container">
            <div className="modal-header">
              <h2 className="modal-title">Edit RAN Inventory Record</h2>
              <button className="modal-close" onClick={closeModal} type="button">✕</button>
            </div>

            <div className="modal-form">
              {error && <div className="message error-message">{error}</div>}
              {success && <div className="message success-message">{success}</div>}

              {/* Site & Equipment Information */}
              <div className="form-section">
                <h3 className="section-title">Site & Equipment Information</h3>
                <div className="form-grid">
                  <div className="form-field">
                    <label>MRBTS</label>
                    <input
                      type="text"
                      value={editForm.mrbts !== null && editForm.mrbts !== undefined ? editForm.mrbts : ''}
                      onChange={(e) => onEditChange('mrbts', e.target.value)}
                    />
                  </div>
                  <div className="form-field">
                    <label>Site ID</label>
                    <input
                      type="text"
                      value={editForm.site_id !== null && editForm.site_id !== undefined ? editForm.site_id : ''}
                      onChange={(e) => onEditChange('site_id', e.target.value)}
                    />
                  </div>
                  <div className="form-field">
                    <label>Identification Code</label>
                    <input
                      type="text"
                      value={editForm.identification_code !== null && editForm.identification_code !== undefined ? editForm.identification_code : ''}
                      onChange={(e) => onEditChange('identification_code', e.target.value)}
                    />
                  </div>
                  <div className="form-field">
                    <label>User Label</label>
                    <input
                      type="text"
                      value={editForm.user_label !== null && editForm.user_label !== undefined ? editForm.user_label : ''}
                      onChange={(e) => onEditChange('user_label', e.target.value)}
                    />
                  </div>
                  <div className="form-field">
                    <label>Serial Number</label>
                    <input
                      type="text"
                      value={editForm.serial_number !== null && editForm.serial_number !== undefined ? editForm.serial_number : ''}
                      onChange={(e) => onEditChange('serial_number', e.target.value)}
                    />
                  </div>
                  <div className="form-field">
                    <label>Project</label>
                    <select
                      value={editForm.pid_po || ''}
                      onChange={(e) => onEditChange('pid_po', e.target.value)}
                    >
                      <option value="">-- Select Project --</option>
                      {projects.map((p) => (
                        <option key={p.pid_po} value={p.pid_po}>
                          {p.project_name} ({p.pid_po})
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
              </div>

              {/* Duplicate Information */}
              <div className="form-section">
                <h3 className="section-title">Duplicate Information</h3>
                <div className="form-grid">
                  <div className="form-field">
                    <label className="checkbox-label">
                      <input
                        type="checkbox"
                        checked={editForm.duplicate || false}
                        onChange={(e) => onEditChange('duplicate', e.target.checked)}
                      />
                      <span>Mark as Duplicate</span>
                    </label>
                  </div>
                  <div className="form-field full-width">
                    <label>Duplicate Remarks</label>
                    <input
                      type="text"
                      value={editForm.duplicate_remarks !== null && editForm.duplicate_remarks !== undefined ? editForm.duplicate_remarks : ''}
                      onChange={(e) => onEditChange('duplicate_remarks', e.target.value)}
                    />
                  </div>
                </div>
              </div>

              {/* Form Actions */}
              <div className="form-actions">
                <button type="button" className="btn-cancel" onClick={closeModal}>
                  Cancel
                </button>
                <button className="btn-submit" onClick={handleUpdate} disabled={updating}>
                  {updating ? 'Updating...' : 'Update Record'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Help/Info Modal */}
      <HelpModal
        show={showHelpModal}
        onClose={() => setShowHelpModal(false)}
        title="RAN Inventory Management - User Guide"
        sections={helpSections}
        closeButtonText="Got it!"
      />
    </div>
  );
}
