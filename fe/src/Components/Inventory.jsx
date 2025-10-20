import React, { useEffect, useState, useRef } from 'react';
import { apiCall, setTransient } from '../api.js';
import '../css/Inventory.css';
import StatsCarousel from './shared/StatsCarousel';
import FilterBar from './shared/FilterBar';
import DataTable from './shared/DataTable';
import ModalForm, { FormSection, FormField } from './shared/ModalForm';
import HelpModal, { HelpList, HelpText, CodeBlock } from './shared/HelpModal';
import TitleWithInfo from './shared/InfoButton';
import Pagination from './shared/Pagination';

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
  const [showHelpModal, setShowHelpModal] = useState(false);
  const fetchAbort = useRef(null);

  const initialForm = {
    site_id: '', site_name: '', slot_id: '', port_id: '', status: '',
    company_id: '', mnemonic: '', clei_code: '', part_no: '', software_no: '',
    factory_id: '', serial_no: '', date_id: '', manufactured_date: '',
    customer_field: '', license_points_consumed: '', alarm_status: '',
    Aggregated_alarm_status: '', pid_po: ''
  };
  const [formData, setFormData] = useState(initialForm);

  const fetchProjects = async () => {
    try {
      const data = await apiCall('/get_project');
      setProjects(data || []);
      // Don't set a default project - let user select one
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

  // Define all stat cards for the carousel
  const statCards = [
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
    { key: 'site_id', label: 'Site ID' },
    { key: 'site_name', label: 'Site Name' },
    { key: 'slot_id', label: 'Slot ID' },
    { key: 'port_id', label: 'Port ID' },
    { key: 'status', label: 'Status', render: (row) => <span className="status-badge">{row.status}</span> },
    { key: 'company_id', label: 'Company ID' },
    { key: 'mnemonic', label: 'Mnemonic' },
    { key: 'clei_code', label: 'CLEI Code' },
    { key: 'part_no', label: 'Part No' },
    { key: 'software_no', label: 'Software No' },
    { key: 'factory_id', label: 'Factory ID' },
    { key: 'serial_no', label: 'Serial No' },
    { key: 'date_id', label: 'Date ID' },
    { key: 'manufactured_date', label: 'Mfg. Date' },
    { key: 'customer_field', label: 'Customer' },
    { key: 'license_points_consumed', label: 'License Pts' },
    { key: 'alarm_status', label: 'Alarm' },
    { key: 'Aggregated_alarm_status', label: 'Agg. Alarm' }
  ];

  // Define table actions
  const tableActions = [
    {
      icon: '✏️',
      onClick: (row) => openEditForm(row),
      title: 'Edit',
      className: 'btn-edit'
    },
    {
      icon: '🗑️',
      onClick: (row) => handleDelete(row.id),
      title: 'Delete',
      className: 'btn-delete'
    }
  ];

  // Define help modal sections
  const helpSections = [
    {
      icon: '📋',
      title: 'Overview',
      content: (
        <HelpText>
          The Inventory Management component allows you to create, view, edit, and delete inventory items
          for your projects. You can also bulk upload inventory data using CSV files and filter items by project.
        </HelpText>
      )
    },
    {
      icon: '✨',
      title: 'Features & Buttons',
      content: (
        <HelpList
          items={[
            { label: '+ New Item', text: 'Opens a form to create a new inventory item. You must select a project first.' },
            { label: '📤 Upload CSV', text: 'Allows you to bulk upload inventory items from a CSV file. Select a project before uploading.' },
            { label: 'Search', text: 'Filter inventory items by Site ID in real-time.' },
            { label: 'Project Dropdown', text: 'Filter all inventory items and statistics by the selected project.' },
            { label: 'Clear Search', text: 'Resets the search filter and shows all items for the selected project.' },
            { label: '✏️ Edit', text: 'Click on any row\'s edit button to modify that inventory item.' },
            { label: '🗑️ Delete', text: 'Click on any row\'s delete button to remove that inventory item (requires confirmation).' },
            { label: '‹ › Navigation Arrows', text: 'Cycle through statistics cards to view different metrics.' },
            { label: 'Rows Per Page Dropdown', text: 'Change how many items are displayed per page (50-500).' }
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
            { label: 'Total Items', text: 'Total count of inventory items for the selected project (or all projects if none selected).' },
            { label: 'Unique Sites', text: 'Number of distinct site IDs in the inventory.' },
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
            To upload inventory items via CSV, your file must contain the following headers (in any order):
          </HelpText>
          <CodeBlock
            items={[
              'site_id', 'site_name', 'slot_id', 'port_id', 'status', 'company_id', 'mnemonic', 'clei_code',
              'part_no', 'software_no', 'factory_id', 'serial_no', 'date_id', 'manufactured_date', 'customer_field',
              'license_points_consumed', 'alarm_status', 'Aggregated_alarm_status'
            ]}
          />
          <HelpText isNote>
            <strong>Note:</strong> Make sure to select a project before uploading. The CSV data will be associated
            with the selected project automatically.
          </HelpText>
        </>
      )
    },
    {
      icon: '💡',
      title: 'Tips',
      content: (
        <HelpList
          items={[
            'Always select a project before creating items or uploading CSV files.',
            'Use the search feature to quickly find items by Site ID.',
            'The table scrolls horizontally - use the scrollbar at the bottom to see all columns.',
            'Statistics update automatically when you filter by project or search.',
            'All required fields are marked with an asterisk (*) in the form.'
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
          title="Inventory Management"
          subtitle="Manage and track your inventory items"
          onInfoClick={() => setShowHelpModal(true)}
          infoTooltip="How to use this component"
        />
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
      <FilterBar
        searchTerm={searchTerm}
        onSearchChange={onSearchChange}
        searchPlaceholder="Search by Site ID..."
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
      {loading && <div className="loading-indicator">Loading inventory...</div>}

      {/* Stats Bar - Carousel Style (3 cards visible) */}
      <StatsCarousel cards={statCards} visibleCount={4} />

      {/* Table Section */}
      <DataTable
        columns={tableColumns}
        data={rows}
        actions={tableActions}
        loading={loading}
        noDataMessage="No inventory items found"
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
      <HelpModal
        show={showHelpModal}
        onClose={() => setShowHelpModal(false)}
        title="Inventory Management - User Guide"
        sections={helpSections}
        closeButtonText="Got it!"
      />
    </div>
  );
}
