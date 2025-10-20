import React, { useState, useEffect, useRef } from 'react';
import '../css/LLDManagement.css';
import { apiCall, setTransient } from '../api.js';
import TitleWithInfo from './shared/InfoButton.jsx';
import FilterBar from './shared/FilterBar.jsx';
import StatsCarousel from './shared/StatsCarousel.jsx';
import DataTable from './shared/DataTable.jsx';
import Pagination from './shared/Pagination.jsx';
import HelpModal, { HelpList, HelpText } from './shared/HelpModal.jsx';

const ROWS_PER_PAGE = 50;

export default function LLDManagement() {
  const [rows, setRows] = useState([]);
  const [currentPage, setCurrentPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [editRow, setEditRow] = useState(null);
  const [updating, setUpdating] = useState(false);
  // NEW: State for projects
  const [projects, setProjects] = useState([]);
  const [selectedProject, setSelectedProject] = useState('');
  const [showHelpModal, setShowHelpModal] = useState(false);

  const fetchAbort = useRef(null);

  // Stats Cards Configuration
  const statCards = [
    { label: 'Total LLD Records', value: total || 0, color: '#124191' },
    { label: 'Current Page Records', value: rows.length || 0, color: '#5bcefa' },
    { label: 'Total Pages', value: Math.ceil(total / ROWS_PER_PAGE) || 0, color: '#124191' },
    { label: 'Active Projects', value: projects.length || 0, color: '#5bcefa' },
  ];

  // Table Columns Configuration
  const tableColumns = [
    { key: 'link_id', label: 'Link ID', align: 'center' },
    { key: 'action', label: 'Action', align: 'center' },
    { key: 'fon', label: 'FON', align: 'center' },
    { key: 'item_name', label: 'Item Name', align: 'center' },
    { key: 'distance', label: 'Distance', align: 'center' },
    { key: 'scope', label: 'Scope', align: 'center' },
    { key: 'fe', label: 'FE', align: 'center' },
    { key: 'ne', label: 'NE', align: 'center' },
    { key: 'link_category', label: 'Link Category', align: 'center' },
    { key: 'link_status', label: 'Link Status', align: 'center' },
  ];

  // Table Actions Configuration
  const tableActions = [
    {
      icon: '✏️',
      title: 'Edit Details',
      onClick: (row) => handleEdit(row),
      className: 'btn-view',
    },
    {
      icon: '🗑️',
      title: 'Delete',
      onClick: (row) => handleDelete(row.link_id),
      className: 'btn-delete',
    },
  ];

  // Help Sections Configuration
  const helpSections = [
    {
      icon: '📋',
      title: 'Managing LLD Records',
      content: (
        <>
          <HelpText>This section helps you manage Low-Level Design records for your projects.</HelpText>
          <HelpList
            items={[
              'Use the search bar to find specific Link IDs',
              'Select a project from the dropdown to filter records',
              'Click "+ Add LLD" to create a new record',
              'Use the edit icon (✏️) to view and edit existing records',
              'Click the delete icon (🗑️) to remove records (requires confirmation)',
            ]}
          />
        </>
      ),
    },
    {
      icon: '📤',
      title: 'Uploading CSV Files',
      content: (
        <>
          <HelpText>Import multiple LLD records at once using CSV files.</HelpText>
          <HelpList
            items={[
              'Select a project before uploading CSV files',
              'Click "📤 Upload CSV" to import multiple records',
              'Ensure your CSV file matches the required format',
              'Upload progress will be shown with success/error messages',
            ]}
          />
          <HelpText style={{ marginTop: '1rem', fontWeight: 'bold' }}>Required CSV Headers:</HelpText>
          <HelpList
            items={[
              { label: 'Required headers', text: 'link ID, Action, FON, configuration, Distance, Scope, FE, NE, link catergory, Link status' },
              { label: 'Optional headers', text: 'COMMENTS, Dismanting link ID, Band, T-band CS, NE Ant size, FE Ant Size, SD NE, SD FE, ODU TYPE, Updated SB, Region, LOSR approval, initial LB, FLB' },
              'The CSV file must contain all required headers as the first row (case-sensitive)',
              'Optional fields can be left empty but headers should be included for best results',
              'Note: "configuration" maps to Item Name, "link catergory" (sic) is the expected spelling',
            ]}
          />
        </>
      ),
    },
    {
      icon: '📝',
      title: 'Record Fields',
      content: (
        <>
          <HelpText>Understanding the LLD record fields:</HelpText>
          <HelpList
            items={[
              { label: 'Link ID', text: 'Unique identifier for each LLD record (required)' },
              { label: 'Action', text: 'Action type for the link (required)' },
              { label: 'FON', text: 'Fiber Optic Network identifier (required)' },
              { label: 'Item Name', text: 'Name of the network item (required)' },
              { label: 'Distance, Scope, FE, NE', text: 'Network configuration fields (required)' },
              { label: 'Link Category & Status', text: 'Classification and current state (required)' },
              { label: 'Technical Details', text: 'Band, ODU Type, Antenna Sizes, etc. (optional)' },
              { label: 'Additional Info', text: 'Region, LOSR Approval, Initial LB, FLB, Comments (optional)' },
            ]}
          />
        </>
      ),
    },
    {
      icon: '🔍',
      title: 'Navigation Tips',
      content: (
        <>
          <HelpText>Make the most of the LLD Management interface:</HelpText>
          <HelpList
            items={[
              'Use pagination controls to navigate through multiple pages (50 records per page)',
              'Filter by project to view project-specific records',
              'Search results update automatically as you type',
              'Click "Clear Search" to reset filters and show all records',
              'Download current page data using the "📥 Download CSV" button',
            ]}
          />
        </>
      ),
    },
  ];

  // Initialize empty form data
  const getEmptyFormData = () => ({
    link_id: '',
    action: '',
    fon: '',
    item_name: '',
    distance: '',
    scope: '',
    fe: '',
    ne: '',
    link_category: '',
    link_status: '',
    comments: '',
    dismanting_link_id: '',
    band: '',
    t_band_cs: '',
    ne_ant_size: '',
    fe_ant_size: '',
    sd_ne: '',
    sd_fe: '',
    odu_type: '',
    updated_sb: '',
    region: '',
    losr_approval: '',
    initial_lb: '',
    flb: '',
    pid_po: '', // Add pid_po to form data
  });

  // NEW: Function to fetch user's projects
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

  // Fetch LLD rows (pagination + search + project filter)
  const fetchLLD = async (page = 1, search = '') => {
    try {
      if (fetchAbort.current) fetchAbort.current.abort();
      const controller = new AbortController();
      fetchAbort.current = controller;

      setLoading(true);
      setError('');
      const skip = (page - 1) * ROWS_PER_PAGE;

      const params = new URLSearchParams();
      params.set('skip', String(skip));
      params.set('limit', String(ROWS_PER_PAGE));
      if (search.trim()) params.set('link_id', search.trim());
      // Filter by selected project if one is selected
      if (selectedProject) params.set('project_id', selectedProject);

      const data = await apiCall(`/lld?${params.toString()}`, {
        signal: controller.signal,
      });

      setRows(data.items || []);
      setTotal(data.total || 0);
      setCurrentPage(page);
    } catch (err) {
      if (err.name !== 'AbortError') setTransient(setError, err.message || 'Failed to fetch LLD rows');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProjects(); // Fetch projects on mount
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Re-fetch LLD data when selected project changes
  useEffect(() => {
    if (selectedProject) {
      fetchLLD(1, searchTerm);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedProject]);

  const onSearchChange = (e) => {
    const v = e.target.value;
    setSearchTerm(v);
    fetchLLD(1, v);
  };

  // CSV Upload
  const handleUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    // Check if a project is selected
    if (!selectedProject) {
      setTransient(setError, "Please select a project before uploading.");
      e.target.value = '';
      return;
    }

    setUploading(true);
    setError('');
    setSuccess('');

    const formData = new FormData();
    formData.append('file', file);

    try {
      const result = await apiCall(`/lld/upload-csv?project_id=${selectedProject}`, {
        method: 'POST',
        body: formData,
      });
      setTransient(setSuccess, `Upload successful! ${result.rows_inserted} rows inserted.`);
      fetchLLD(1, searchTerm);
    } catch (err) {
      setTransient(setError, err.message);
    } finally {
      setUploading(false);
      e.target.value = '';
    }
  };

  // Delete row
  const handleDelete = async (link_id) => {
    if (!window.confirm(`Delete LLD row ${link_id}?`)) return;
    try {
      await apiCall(`/lld/${link_id}`, {
        method: 'DELETE',
      });
      setTransient(setSuccess, `Deleted ${link_id} successfully`);
      fetchLLD(currentPage, searchTerm);
    } catch (err) {
      setTransient(setError, err.message);
    }
  };

  // Open edit modal
  const handleEdit = (row) => {
    setEditRow({ ...row }); // clone
    setShowModal(true);
  };

  // Open create modal
  const handleOpenCreate = () => {
    if (!selectedProject) {
      setTransient(setError, 'Please select a project to create a new LLD record.');
      return;
    }
    const emptyFormData = getEmptyFormData();
    emptyFormData.pid_po = selectedProject; // Set the project for the new record
    setEditRow(emptyFormData);
    setShowModal(true);
  };

  // Handle field change in edit/create
  const onEditChange = (key, value) => {
    setEditRow(prev => ({ ...prev, [key]: value }));
  };

  // Create new LLD row
  const handleCreate = async () => {
    if (!editRow) return;
    setUpdating(true);
    setError('');
    setSuccess('');
    try {
      await apiCall('/lld', {
        method: 'POST',
        body: JSON.stringify(editRow),
      });
      setTransient(setSuccess, 'Row created successfully!');
      fetchLLD(currentPage, searchTerm);
      setShowModal(false);
      setEditRow(null);
    } catch (err) {
      setTransient(setError, err.message);
    } finally {
      setUpdating(false);
    }
  };

  // Submit update
  const handleUpdate = async () => {
    if (!editRow || !editRow.link_id) return;
    setUpdating(true);
    setError('');
    setSuccess('');
    try {
      await apiCall(`/lld/${editRow.link_id}`, {
        method: 'PUT',
        body: JSON.stringify(editRow),
      });
      setTransient(setSuccess, 'Row updated successfully!');
      fetchLLD(currentPage, searchTerm);
      setShowModal(false);
      setEditRow(null);
    } catch (err) {
      setTransient(setError, err.message);
    } finally {
      setUpdating(false);
    }
  };

  const downloadCSV = () => {
    if (!rows.length) return;
    const header = [
      'link_id', 'action', 'fon', 'item_name', 'distance', 'scope', 'fe', 'ne', 'link_category', 'link_status',
      'comments', 'dismanting_link_id', 'band', 't_band_cs', 'ne_ant_size', 'fe_ant_size', 'sd_ne', 'sd_fe',
      'odu_type', 'updated_sb', 'region', 'losr_approval', 'initial_lb', 'flb'
    ];
    const rowsCsv = rows.map(r => header.map(h => r[h] || ''));
    const csvContent = [header.join(','), ...rowsCsv.map(e => e.join(','))].join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `LLD_export.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const totalPages = Math.ceil(total / ROWS_PER_PAGE);
  const isCreateMode = editRow && !editRow.id;

  // Filter Bar Dropdowns Configuration
  const dropdowns = [
    {
      label: 'Project',
      value: selectedProject,
      onChange: (e) => {
        setSelectedProject(e.target.value);
        // Data will be re-fetched automatically via useEffect
      },
      options: projects.map((p) => ({
        value: p.pid_po,
        label: `${p.project_name} (${p.pid_po})`,
      })),
      placeholder: '-- Select a Project --',
    },
  ];

  return (
    <div className="lld-container">
      {/* Header with Info Button */}
      <div className="lld-header-row">
        <TitleWithInfo
          title="LLD Management"
          subtitle="Manage Low-Level Design records"
          onInfoClick={() => setShowHelpModal(true)}
          infoTooltip="How to use LLD Management"
        />

        {/* Action Buttons */}
        <div className="action-buttons">
          <button
            className="btn-primary"
            onClick={handleOpenCreate}
            disabled={!selectedProject}
            title={!selectedProject ? 'Select a project first' : 'Create a new LLD record'}
          >
            + Add LLD
          </button>
          <label
            className={`btn-secondary ${uploading || !selectedProject ? 'disabled' : ''}`}
            title={!selectedProject ? 'Select a project first' : 'Upload a reference CSV'}
          >
            📤 Upload CSV
            <input
              type="file"
              accept=".csv"
              style={{ display: 'none' }}
              disabled={uploading || !selectedProject}
              onChange={handleUpload}
            />
          </label>
          {/* <button className="btn-secondary" onClick={downloadCSV} disabled={!rows.length}>
            📥 Download CSV
          </button> */}
        </div>
      </div>

      {/* Filter Bar with Search and Project Selector */}
      <FilterBar
        searchTerm={searchTerm}
        onSearchChange={onSearchChange}
        searchPlaceholder="Search by Link ID..."
        dropdowns={dropdowns}
        showClearButton={!!searchTerm}
        onClearSearch={() => {
          setSearchTerm('');
          fetchLLD(1, '');
        }}
        clearButtonText="Clear Search"
      />

      {/* Stats Carousel */}
      <StatsCarousel cards={statCards} visibleCount={4} />

      {/* Messages */}
      {error && <div className="lld-message error">{error}</div>}
      {success && <div className="lld-message success">{success}</div>}

      {/* Data Table */}
      <DataTable
        columns={tableColumns}
        data={rows}
        actions={tableActions}
        loading={loading}
        noDataMessage="No LLD records found"
      />

      {/* Pagination */}
      <Pagination
        currentPage={currentPage}
        totalPages={totalPages}
        onPageChange={(page) => fetchLLD(page, searchTerm)}
        previousText="← Previous"
        nextText="Next →"
      />

      {showModal && (
        <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && (setShowModal(false), setEditRow(null))}>
          <div className="modal-container">
            <div className="modal-header">
              <h2 className="modal-title">
                {isCreateMode ? 'Create New LLD Record' : `Edit LLD: ${editRow.link_id}`}
              </h2>
              <button
                className="modal-close"
                onClick={() => {
                  setShowModal(false);
                  setEditRow(null);
                }}
                type="button"
              >
                ✕
              </button>
            </div>

            <form className="modal-form" onSubmit={(e) => {
              e.preventDefault();
              if (isCreateMode) {
                handleCreate();
              } else {
                handleUpdate();
              }
            }}>
              {/* Basic Information Section */}
              <div className="form-section">
                <h3 className="section-title">Basic Information</h3>
                <div className="form-grid">
                  {isCreateMode && (
                    <div className="form-field">
                      <label>Project ID *</label>
                      <input
                        type="text"
                        name="pid_po"
                        value={editRow.pid_po || ''}
                        onChange={(e) => onEditChange('pid_po', e.target.value)}
                        disabled
                        className="disabled-input"
                      />
                    </div>
                  )}
                  <div className="form-field">
                    <label>Link ID *</label>
                    <input
                      type="text"
                      name="link_id"
                      value={editRow ? editRow.link_id || '' : ''}
                      onChange={(e) => onEditChange('link_id', e.target.value)}
                      required
                      disabled={!isCreateMode}
                      className={!isCreateMode ? 'disabled-input' : ''}
                    />
                  </div>
                  <div className="form-field">
                    <label>Action *</label>
                    <input
                      type="text"
                      name="action"
                      value={editRow ? editRow.action || '' : ''}
                      onChange={(e) => onEditChange('action', e.target.value)}
                      required
                    />
                  </div>
                  <div className="form-field">
                    <label>FON *</label>
                    <input
                      type="text"
                      name="fon"
                      value={editRow ? editRow.fon || '' : ''}
                      onChange={(e) => onEditChange('fon', e.target.value)}
                      required
                    />
                  </div>
                  <div className="form-field full-width">
                    <label>Item Name *</label>
                    <input
                      type="text"
                      name="item_name"
                      value={editRow ? editRow.item_name || '' : ''}
                      onChange={(e) => onEditChange('item_name', e.target.value)}
                      required
                    />
                  </div>
                </div>
              </div>

              {/* Network Configuration Section */}
              <div className="form-section">
                <h3 className="section-title">Network Configuration</h3>
                <div className="form-grid">
                  <div className="form-field">
                    <label>Distance *</label>
                    <input
                      type="text"
                      name="distance"
                      value={editRow ? editRow.distance || '' : ''}
                      onChange={(e) => onEditChange('distance', e.target.value)}
                      required
                    />
                  </div>
                  <div className="form-field">
                    <label>Scope *</label>
                    <input
                      type="text"
                      name="scope"
                      value={editRow ? editRow.scope || '' : ''}
                      onChange={(e) => onEditChange('scope', e.target.value)}
                      required
                    />
                  </div>
                  <div className="form-field">
                    <label>FE *</label>
                    <input
                      type="text"
                      name="fe"
                      value={editRow ? editRow.fe || '' : ''}
                      onChange={(e) => onEditChange('fe', e.target.value)}
                      required
                    />
                  </div>
                  <div className="form-field">
                    <label>NE *</label>
                    <input
                      type="text"
                      name="ne"
                      value={editRow ? editRow.ne || '' : ''}
                      onChange={(e) => onEditChange('ne', e.target.value)}
                      required
                    />
                  </div>
                  <div className="form-field">
                    <label>Link Category *</label>
                    <input
                      type="text"
                      name="link_category"
                      value={editRow ? editRow.link_category || '' : ''}
                      onChange={(e) => onEditChange('link_category', e.target.value)}
                      required
                    />
                  </div>
                  <div className="form-field">
                    <label>Link Status *</label>
                    <input
                      type="text"
                      name="link_status"
                      value={editRow ? editRow.link_status || '' : ''}
                      onChange={(e) => onEditChange('link_status', e.target.value)}
                      required
                    />
                  </div>
                </div>
              </div>

              {/* Technical Details Section */}
              <div className="form-section">
                <h3 className="section-title">Technical Details</h3>
                <div className="form-grid">
                  <div className="form-field">
                    <label>Band</label>
                    <input
                      type="text"
                      name="band"
                      value={editRow ? editRow.band || '' : ''}
                      onChange={(e) => onEditChange('band', e.target.value)}
                    />
                  </div>
                  <div className="form-field">
                    <label>T-band CS</label>
                    <input
                      type="text"
                      name="t_band_cs"
                      value={editRow ? editRow.t_band_cs || '' : ''}
                      onChange={(e) => onEditChange('t_band_cs', e.target.value)}
                    />
                  </div>
                  <div className="form-field">
                    <label>NE Ant Size</label>
                    <input
                      type="text"
                      name="ne_ant_size"
                      value={editRow ? editRow.ne_ant_size || '' : ''}
                      onChange={(e) => onEditChange('ne_ant_size', e.target.value)}
                    />
                  </div>
                  <div className="form-field">
                    <label>FE Ant Size</label>
                    <input
                      type="text"
                      name="fe_ant_size"
                      value={editRow ? editRow.fe_ant_size || '' : ''}
                      onChange={(e) => onEditChange('fe_ant_size', e.target.value)}
                    />
                  </div>
                  <div className="form-field">
                    <label>SD NE</label>
                    <input
                      type="text"
                      name="sd_ne"
                      value={editRow ? editRow.sd_ne || '' : ''}
                      onChange={(e) => onEditChange('sd_ne', e.target.value)}
                    />
                  </div>
                  <div className="form-field">
                    <label>SD FE</label>
                    <input
                      type="text"
                      name="sd_fe"
                      value={editRow ? editRow.sd_fe || '' : ''}
                      onChange={(e) => onEditChange('sd_fe', e.target.value)}
                    />
                  </div>
                  <div className="form-field">
                    <label>ODU Type</label>
                    <input
                      type="text"
                      name="odu_type"
                      value={editRow ? editRow.odu_type || '' : ''}
                      onChange={(e) => onEditChange('odu_type', e.target.value)}
                    />
                  </div>
                  <div className="form-field">
                    <label>Dismanting Link ID</label>
                    <input
                      type="text"
                      name="dismanting_link_id"
                      value={editRow ? editRow.dismanting_link_id || '' : ''}
                      onChange={(e) => onEditChange('dismanting_link_id', e.target.value)}
                    />
                  </div>
                </div>
              </div>

              {/* Additional Information Section */}
              <div className="form-section">
                <h3 className="section-title">Additional Information</h3>
                <div className="form-grid">
                  <div className="form-field">
                    <label>Region</label>
                    <input
                      type="text"
                      name="region"
                      value={editRow ? editRow.region || '' : ''}
                      onChange={(e) => onEditChange('region', e.target.value)}
                    />
                  </div>
                  <div className="form-field">
                    <label>Updated SB</label>
                    <input
                      type="text"
                      name="updated_sb"
                      value={editRow ? editRow.updated_sb || '' : ''}
                      onChange={(e) => onEditChange('updated_sb', e.target.value)}
                    />
                  </div>
                  <div className="form-field">
                    <label>LOSR Approval</label>
                    <input
                      type="text"
                      name="losr_approval"
                      value={editRow ? editRow.losr_approval || '' : ''}
                      onChange={(e) => onEditChange('losr_approval', e.target.value)}
                    />
                  </div>
                  <div className="form-field">
                    <label>Initial LB</label>
                    <input
                      type="text"
                      name="initial_lb"
                      value={editRow ? editRow.initial_lb || '' : ''}
                      onChange={(e) => onEditChange('initial_lb', e.target.value)}
                    />
                  </div>
                  <div className="form-field">
                    <label>FLB</label>
                    <input
                      type="text"
                      name="flb"
                      value={editRow ? editRow.flb || '' : ''}
                      onChange={(e) => onEditChange('flb', e.target.value)}
                    />
                  </div>
                  <div className="form-field full-width">
                    <label>Comments</label>
                    <input
                      type="text"
                      name="comments"
                      value={editRow ? editRow.comments || '' : ''}
                      onChange={(e) => onEditChange('comments', e.target.value)}
                    />
                  </div>
                </div>
              </div>

              {/* Form Actions */}
              <div className="form-actions">
                <button
                  type="button"
                  className="btn-cancel"
                  onClick={() => {
                    setShowModal(false);
                    setEditRow(null);
                  }}
                >
                  Cancel
                </button>
                <button type="submit" className="btn-submit" disabled={updating}>
                  {updating ? 'Saving...' : isCreateMode ? 'Create LLD Record' : 'Update LLD Record'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Help Modal */}
      <HelpModal
        show={showHelpModal}
        onClose={() => setShowHelpModal(false)}
        title="LLD Management User Guide"
        sections={helpSections}
        closeButtonText="Got it!"
      />
    </div>
  );
}