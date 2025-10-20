import React, { useEffect, useState, useRef } from 'react';
import { apiCall, setTransient } from '../api.js';
import '../css/Site.css';
import StatsCarousel from './shared/StatsCarousel';
import FilterBar from './shared/FilterBar';
import DataTable from './shared/DataTable';
import HelpModal, { HelpList, HelpText, CodeBlock } from './shared/HelpModal';
import TitleWithInfo from './shared/InfoButton';
import Pagination from './shared/Pagination';

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
      // Don't set a default project - let user select one
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

  // Define stat cards for the carousel
  const statCards = [
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
    { key: 'pid_po', label: 'Project ID' }
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
      onClick: (row) => handleDelete(row.site_id),
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
          The Site Management component allows you to create, view, edit, and delete sites
          for your projects. You can also bulk upload site data using CSV files.
        </HelpText>
      )
    },
    {
      icon: '✨',
      title: 'Features & Buttons',
      content: (
        <HelpList
          items={[
            { label: '+ New Site', text: 'Opens a form to create a new site. You must select a project first.' },
            { label: '📤 Upload CSV', text: 'Allows you to bulk upload sites from a CSV file. Select a project before uploading.' },
            { label: 'Search', text: 'Filter sites by Site ID or Site Name in real-time.' },
            { label: 'Project Dropdown', text: 'Filter all sites by the selected project.' },
            { label: 'Clear Search', text: 'Resets the search filter and shows all sites.' },
            { label: '✏️ Edit', text: 'Click on any row\'s edit button to modify that site.' },
            { label: '🗑️ Delete', text: 'Click on any row\'s delete button to remove that site (requires confirmation).' },
            { label: '‹ › Navigation Arrows', text: 'Cycle through statistics cards to view different metrics.' },
            { label: 'Rows Per Page Dropdown', text: 'Change how many sites are displayed per page (50-500).' }
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
            { label: 'Total Sites', text: 'Total count of sites in the system.' },
            { label: 'Total Projects', text: 'Number of projects that have sites.' },
            { label: 'Current Page', text: 'Shows which page you\'re viewing out of total pages.' },
            { label: 'Showing', text: 'Number of sites currently displayed on this page.' },
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
            To upload sites via CSV, your file must contain link data with the following format:
          </HelpText>
          <CodeBlock items={['LinkID', 'InterfaceName', 'SiteIPA', 'SiteIPB']} />
          <HelpText>
            Example: <code>JIZ0243-JIZ0169, eth0, 10.0.0.1, 10.0.0.2</code>
          </HelpText>
          <HelpText isNote>
            <strong>Note:</strong> Make sure to select a project before uploading. The system will automatically
            parse the LinkID to extract site names and create sites accordingly.
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
            'Always select a project before creating sites or uploading CSV files.',
            'Use the search feature to quickly find sites by ID or name.',
            'Statistics update automatically when you add, edit, or delete sites.',
            'Site IDs cannot be changed after creation for data integrity.',
            'All required fields are marked with an asterisk (*) in the form.'
          ]}
        />
      )
    }
  ];

  return (
    <div className="site-container">
      {/* Header Section */}
      <div className="site-header">
        <TitleWithInfo
          title="Site Management"
          subtitle="Manage and track your sites"
          onInfoClick={() => setShowHelpModal(true)}
          infoTooltip="How to use this component"
        />
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
      <FilterBar
        searchTerm={searchTerm}
        onSearchChange={onSearchChange}
        searchPlaceholder="Search by Site ID or Name..."
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
        onClearSearch={() => { setSearchTerm(''); fetchSites(1, ''); }}
        clearButtonText="Clear Search"
      />

      {/* Messages */}
      {error && <div className="message error-message">{error}</div>}
      {success && <div className="message success-message">{success}</div>}
      {loading && <div className="loading-indicator">Loading sites...</div>}

      {/* Stats Bar - Carousel Style (3 cards visible) */}
      <StatsCarousel cards={statCards} visibleCount={4} />

      {/* Table Section */}
      <DataTable
        columns={tableColumns}
        data={rows}
        actions={tableActions}
        loading={loading}
        noDataMessage="No sites found"
        className="site-table-wrapper"
      />

      {/* Pagination */}
      <Pagination
        currentPage={currentPage}
        totalPages={totalPages}
        onPageChange={(page) => fetchSites(page, searchTerm, rowsPerPage)}
        previousText="← Previous"
        nextText="Next →"
      />

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
      <HelpModal
        show={showHelpModal}
        onClose={() => setShowHelpModal(false)}
        title="Site Management - User Guide"
        sections={helpSections}
        closeButtonText="Got it!"
      />
    </div>
  );
}
