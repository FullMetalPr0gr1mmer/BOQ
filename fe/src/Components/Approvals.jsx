import React, { useState, useEffect, useRef } from 'react';
import { useLocation } from 'react-router-dom';
import { apiCall, setTransient } from '../api.js';
import '../css/Inventory.css';
import FilterBar from './shared/FilterBar';
import DataTable from './shared/DataTable';
import Pagination from './shared/Pagination';
import TitleWithInfo from './shared/InfoButton';
import StatsCarousel from './shared/StatsCarousel';

const ROWS_PER_PAGE = 50;

export default function Approvals() {
  const location = useLocation();
  const activeTab = location.pathname === '/triggering' ? 'triggering' : 'approval';
  const [rows, setRows] = useState([]);
  const [currentPage, setCurrentPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [uploading, setUploading] = useState(false);
  const [loading, setLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [filterProjectType, setFilterProjectType] = useState('');
  const [projects, setProjects] = useState([]);
  const [selectedProject, setSelectedProject] = useState('');
  const [pendingCount, setPendingCount] = useState(0);
  const [rejectedCount, setRejectedCount] = useState(0);

  // Rejection modal state
  const [showRejectModal, setShowRejectModal] = useState(false);
  const [rejectingItem, setRejectingItem] = useState(null);
  const [rejectNotes, setRejectNotes] = useState('');
  const [submitting, setSubmitting] = useState(false);

  // Info modal state (for individual items)
  const [showInfoModal, setShowInfoModal] = useState(false);
  const [infoItem, setInfoItem] = useState(null);

  // Workflow help modal state
  const [showWorkflowHelp, setShowWorkflowHelp] = useState(false);

  // File upload state
  const [csvFile, setCsvFile] = useState(null);
  const [templateFile, setTemplateFile] = useState(null);
  const csvInputRef = useRef(null);
  const templateInputRef = useRef(null);

  const fetchAbort = useRef(null);

  const projectTypes = [
    { value: 'Zain MW BOQ', label: 'Zain MW BOQ' },
    { value: 'Zain Ran BOQ', label: 'Zain Ran BOQ' }
  ];

  const fetchApprovals = async (page = 1, stage = activeTab, search = searchTerm, filter = filterProjectType, projectId = selectedProject) => {
    try {
      if (fetchAbort.current) fetchAbort.current.abort();
      const controller = new AbortController();
      fetchAbort.current = controller;
      setLoading(true);
      setError('');

      const params = new URLSearchParams({
        page: page.toString(),
        page_size: ROWS_PER_PAGE.toString(),
        stage: stage
      });

      if (search.trim()) {
        params.set('search', search.trim());
      }

      if (filter) {
        params.set('project_type', filter);
      }

      if (projectId) {
        params.set('project_id', projectId);
      }

      const data = await apiCall(`/approvals/?${params.toString()}`, {
        signal: controller.signal,
        method: 'GET',
      });

      setRows(data.items || []);
      setTotal(data.total || 0);
      setCurrentPage(page);

      // Calculate status counts
      const items = data.items || [];
      const pending = items.filter(item =>
        item.status === 'pending_approval' || item.status === 'pending_triggering'
      ).length;
      const rejected = items.filter(item => item.status === 'rejected').length;
      setPendingCount(pending);
      setRejectedCount(rejected);
    } catch (err) {
      if (err.name !== 'AbortError') {
        setTransient(setError, err.message || 'Failed to fetch approvals');
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    setSearchTerm('');
    setFilterProjectType('');
    setProjects([]);
    setSelectedProject('');
    fetchApprovals(1, activeTab, '', '');
  }, [activeTab]);

  const handleSearchChange = (e) => {
    const value = e.target.value;
    setSearchTerm(value);
    fetchApprovals(1, activeTab, value, filterProjectType, selectedProject);
  };

  const fetchProjects = async (projectType) => {
    if (!projectType) {
      setProjects([]);
      setSelectedProject('');
      return;
    }

    try {
      const data = await apiCall(`/approvals/projects/${encodeURIComponent(projectType)}`, {
        method: 'GET',
      });
      setProjects(data || []);
    } catch (err) {
      setTransient(setError, err.message || 'Failed to fetch projects');
      setProjects([]);
    }
  };

  const handleFilterChange = async (e) => {
    const value = e.target.value;
    setFilterProjectType(value);
    setSelectedProject('');
    await fetchProjects(value);
    fetchApprovals(1, activeTab, searchTerm, value, '');
  };

  const handleProjectChange = (e) => {
    const value = e.target.value;
    setSelectedProject(value);
    fetchApprovals(1, activeTab, searchTerm, filterProjectType, value);
  };

  const handleClearSearch = () => {
    setSearchTerm('');
    setFilterProjectType('');
    setProjects([]);
    setSelectedProject('');
    fetchApprovals(1, activeTab, '', '');
  };

  const handleCsvChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      if (!file.name.endsWith('.csv')) {
        setTransient(setError, "PAC data file must be a CSV file (.csv)");
        e.target.value = '';
        return;
      }
      setCsvFile(file);
    }
  };

  const handleTemplateChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      const ext = file.name.toLowerCase();
      if (!ext.endsWith('.doc') && !ext.endsWith('.docx')) {
        setTransient(setError, "PAC template must be a Word file (.doc or .docx)");
        e.target.value = '';
        return;
      }
      setTemplateFile(file);
    }
  };

  const handleUpload = async () => {
    if (!filterProjectType) {
      setTransient(setError, "Please select a project type from the filter before uploading.");
      return;
    }

    if (!selectedProject) {
      setTransient(setError, "Please select a project before uploading.");
      return;
    }

    if (!csvFile) {
      setTransient(setError, "Please select a CSV file.");
      return;
    }

    if (!templateFile) {
      setTransient(setError, "Please select a Word template file. Both CSV and template are required.");
      return;
    }

    setUploading(true);
    setError('');
    setSuccess('');

    const formData = new FormData();
    formData.append('csv_file', csvFile);
    formData.append('template_file', templateFile);
    formData.append('project_id', selectedProject);
    formData.append('project_type', filterProjectType);

    try {
      await apiCall('/approvals/upload', {
        method: 'POST',
        body: formData,
      });

      setTransient(setSuccess, `Files uploaded successfully!`);
      fetchApprovals(1, activeTab, searchTerm, filterProjectType, selectedProject);

      // Clear file inputs
      setCsvFile(null);
      setTemplateFile(null);
      if (csvInputRef.current) csvInputRef.current.value = '';
      if (templateInputRef.current) templateInputRef.current.value = '';
    } catch (err) {
      setTransient(setError, err.message);
    } finally {
      setUploading(false);
    }
  };

  const handleApprove = async (row) => {
    if (!window.confirm(`Are you sure you want to approve "${row.filename}"?`)) return;

    try {
      const result = await apiCall(`/approvals/${row.id}/approve`, {
        method: 'POST',
      });
      setTransient(setSuccess, result.message || 'Approved successfully!');
      fetchApprovals(currentPage, activeTab, searchTerm, filterProjectType, selectedProject);
    } catch (err) {
      setTransient(setError, err.message);
    }
  };

  const openInfoModal = (row) => {
    setInfoItem(row);
    setShowInfoModal(true);
  };

  const closeInfoModal = () => {
    setShowInfoModal(false);
    setInfoItem(null);
  };

  const openRejectModal = (row) => {
    setRejectingItem(row);
    setRejectNotes('');
    setShowRejectModal(true);
  };

  const closeRejectModal = () => {
    setShowRejectModal(false);
    setRejectingItem(null);
    setRejectNotes('');
  };

  const handleRejectSubmit = async (e) => {
    e.preventDefault();
    if (!rejectNotes.trim()) {
      setTransient(setError, 'Please provide rejection notes');
      return;
    }

    setSubmitting(true);
    try {
      const result = await apiCall(`/approvals/${rejectingItem.id}/reject`, {
        method: 'POST',
        body: JSON.stringify({ notes: rejectNotes }),
      });
      setTransient(setSuccess, result.message || 'Rejected successfully!');
      closeRejectModal();
      fetchApprovals(currentPage, activeTab, searchTerm, filterProjectType, selectedProject);
    } catch (err) {
      setTransient(setError, err.message);
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (row) => {
    if (!window.confirm(`Are you sure you want to delete "${row.filename}"?`)) return;

    try {
      await apiCall(`/approvals/${row.id}`, {
        method: 'DELETE',
      });
      setTransient(setSuccess, 'Deleted successfully!');
      fetchApprovals(currentPage, activeTab, searchTerm, filterProjectType, selectedProject);
    } catch (err) {
      setTransient(setError, err.message);
    }
  };

  const handleDownload = async (row) => {
    try {
      const response = await fetch(`${import.meta.env.VITE_API_URL}/approvals/download/${row.id}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
      });

      if (!response.ok) throw new Error('Download failed');

      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', row.filename);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    } catch (err) {
      setTransient(setError, err.message || 'Failed to download CSV file');
    }
  };

  const handleDownloadTemplate = async (row) => {
    try {
      const response = await fetch(`${import.meta.env.VITE_API_URL}/approvals/download-template/${row.id}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
      });

      if (!response.ok) throw new Error('Download failed');

      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', row.template_filename);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    } catch (err) {
      setTransient(setError, err.message || 'Failed to download template file');
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-GB', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getStatusBadge = (status) => {
    const statusMap = {
      'pending_approval': { label: 'Pending', class: 'status-pending' },
      'pending_triggering': { label: 'Pending', class: 'status-pending' },
      'rejected': { label: 'Rejected', class: 'status-rejected' },
      'approved': { label: 'Approved', class: 'status-approved' }
    };
    const statusInfo = statusMap[status] || { label: status, class: '' };
    return <span className={`status-badge ${statusInfo.class}`}>{statusInfo.label}</span>;
  };

  const totalPages = Math.ceil(total / ROWS_PER_PAGE);

  // Define table columns
  const tableColumns = [
    { key: 'filename', label: 'File Name' },
    { key: 'project_type', label: 'Project Type' },
    {
      key: 'created_at',
      label: 'Upload Date',
      render: (row) => formatDate(row.created_at)
    },
    {
      key: 'status',
      label: 'Status',
      render: (row) => getStatusBadge(row.status)
    },
    {
      key: 'notes',
      label: 'Notes',
      render: (row) => row.notes ? (
        <span className="notes-cell" title={row.notes}>
          {row.notes.length > 50 ? row.notes.substring(0, 50) + '...' : row.notes}
        </span>
      ) : '-'
    },
    { key: 'uploader_name', label: 'Uploaded By' }
  ];

  // Define actions based on active tab
  const getTableActions = () => {
    const actions = [
      {
        icon: 'ℹ️',
        onClick: openInfoModal,
        title: 'View Details',
        className: 'btn-info'
      },
      {
        icon: '📄',
        onClick: handleDownload,
        title: 'Download CSV',
        className: 'btn-secondary'
      },
      {
        icon: '📝',
        onClick: handleDownloadTemplate,
        title: 'Download Template',
        className: 'btn-secondary'
      },
      {
        icon: '✅',
        onClick: handleApprove,
        title: 'Approve',
        className: 'btn-primary'
      }
    ];

    if (activeTab === 'triggering') {
      actions.push({
        icon: '❌',
        onClick: openRejectModal,
        title: 'Reject',
        className: 'btn-danger'
      });
    }

    if (activeTab === 'approval') {
      actions.push({
        icon: '🗑️',
        onClick: handleDelete,
        title: 'Delete',
        className: 'btn-danger'
      });
    }

    return actions;
  };

  // Define stat cards for carousel
  const statCards = [
    { label: 'Total Items', value: total },
    { label: 'Current Page', value: `${currentPage} / ${totalPages || 1}` },
    { label: 'Stage', value: activeTab === 'approval' ? 'Approval' : 'Triggering' },
    { label: 'Pending', value: <span style={{ color: '#d97706' }}>{pendingCount}</span> },
    { label: 'Rejected', value: <span style={{ color: '#dc2626' }}>{rejectedCount}</span> }
  ];

  return (
    <div className="inventory-container">
      {/* Header Section */}
      <div className="inventory-header">
        <TitleWithInfo
          title="Approvals Workflow"
          subtitle="Manage PAC file approvals and triggering"
          onInfoClick={() => setShowWorkflowHelp(true)}
          infoTooltip="Learn about the workflow"
        />
        <div className="header-actions">
          {activeTab === 'approval' && (
            <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
              <label className={`btn-secondary ${uploading ? 'disabled' : ''}`}>
                <span className="btn-icon">📄</span>
                {csvFile ? csvFile.name : 'Select CSV'}
                <input
                  ref={csvInputRef}
                  type="file"
                  accept=".csv"
                  style={{ display: "none" }}
                  disabled={uploading}
                  onChange={handleCsvChange}
                />
              </label>
              <label className={`btn-secondary ${uploading ? 'disabled' : ''}`}>
                <span className="btn-icon">📝</span>
                {templateFile ? templateFile.name : 'Select Template'}
                <input
                  ref={templateInputRef}
                  type="file"
                  accept=".doc,.docx"
                  style={{ display: "none" }}
                  disabled={uploading}
                  onChange={handleTemplateChange}
                />
              </label>
              <button
                className={`btn-primary ${uploading || !csvFile || !templateFile ? 'disabled' : ''}`}
                onClick={handleUpload}
                disabled={uploading || !csvFile || !templateFile}
                title={!csvFile || !templateFile ? "Select both files first" : "Upload files"}
              >
                <span className="btn-icon">📤</span>
                {uploading ? 'Uploading...' : 'Upload'}
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Filters Section */}
      <FilterBar
        searchTerm={searchTerm}
        onSearchChange={handleSearchChange}
        searchPlaceholder="Search by filename..."
        dropdowns={[
          {
            label: 'Project Type',
            value: filterProjectType,
            onChange: handleFilterChange,
            placeholder: '-- All Project Types --',
            options: projectTypes.map(pt => ({
              value: pt.value,
              label: pt.label
            }))
          },
          {
            label: 'Project',
            value: selectedProject,
            onChange: handleProjectChange,
            placeholder: filterProjectType ? '-- Select Project --' : '-- Select Type First --',
            disabled: !filterProjectType || projects.length === 0,
            options: projects.map(p => ({
              value: p.id,
              label: p.name
            }))
          }
        ]}
        showClearButton={!!searchTerm || !!filterProjectType || !!selectedProject}
        onClearSearch={handleClearSearch}
        clearButtonText="Clear Filters"
      />

      {/* Messages */}
      {error && <div className="message error-message">{error}</div>}
      {success && <div className="message success-message">{success}</div>}
      {loading && <div className="loading-indicator">Loading...</div>}

      {/* Stats */}
      <StatsCarousel cards={statCards} visibleCount={4} />

      {/* Table Section */}
      <DataTable
        columns={tableColumns}
        data={rows}
        actions={getTableActions()}
        loading={loading}
        noDataMessage={`No items in ${activeTab === 'approval' ? 'approval' : 'triggering'} stage`}
        className="inventory-table-wrapper"
      />

      {/* Pagination */}
      <Pagination
        currentPage={currentPage}
        totalPages={totalPages}
        onPageChange={(page) => fetchApprovals(page, activeTab, searchTerm, filterProjectType, selectedProject)}
        previousText="← Previous"
        nextText="Next →"
      />

      {/* Workflow Help Modal */}
      {showWorkflowHelp && (
        <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && setShowWorkflowHelp(false)}>
          <div className="modal-container" style={{ maxWidth: '800px' }}>
            <div className="modal-header">
              <h2 className="modal-title">📋 Approvals Workflow Guide</h2>
              <button className="modal-close" onClick={() => setShowWorkflowHelp(false)} type="button">✕</button>
            </div>

            <div className="modal-form">
              <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
                {/* Overview */}
                <div>
                  <h3 style={{
                    fontSize: '1.125rem',
                    fontWeight: '600',
                    color: '#1e293b',
                    marginBottom: '8px'
                  }}>
                    Overview
                  </h3>
                  <p style={{
                    fontSize: '0.875rem',
                    color: '#475569',
                    lineHeight: '1.6'
                  }}>
                    The Approvals Workflow is a two-stage process for managing PAC (Project Authorization Certificate) files.
                    Files move through approval and triggering stages to ensure proper validation before deployment.
                  </p>
                </div>

                {/* Workflow Stages */}
                <div>
                  <h3 style={{
                    fontSize: '1.125rem',
                    fontWeight: '600',
                    color: '#1e293b',
                    marginBottom: '12px'
                  }}>
                    Workflow Stages
                  </h3>

                  {/* Stage 1 */}
                  <div style={{
                    marginBottom: '16px',
                    padding: '16px',
                    background: '#f8fafc',
                    borderRadius: '8px',
                    borderLeft: '4px solid #3b82f6'
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                      <span style={{ fontSize: '1.5rem' }}>1️⃣</span>
                      <strong style={{ fontSize: '1rem', color: '#1e293b' }}>Approval Stage</strong>
                    </div>
                    <ul style={{ margin: '8px 0 0 0', paddingLeft: '24px', fontSize: '0.875rem', color: '#475569' }}>
                      <li>Upload PAC CSV files linked to specific MW or RAN projects</li>
                      <li>Files start with "Pending Approval" status</li>
                      <li>Actions: Approve (moves to Triggering) or Delete</li>
                    </ul>
                  </div>

                  {/* Stage 2 */}
                  <div style={{
                    padding: '16px',
                    background: '#f8fafc',
                    borderRadius: '8px',
                    borderLeft: '4px solid #10b981'
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                      <span style={{ fontSize: '1.5rem' }}>2️⃣</span>
                      <strong style={{ fontSize: '1rem', color: '#1e293b' }}>Triggering Stage</strong>
                    </div>
                    <ul style={{ margin: '8px 0 0 0', paddingLeft: '24px', fontSize: '0.875rem', color: '#475569' }}>
                      <li>Final validation and deployment preparation</li>
                      <li>Files have "Pending Triggering" status</li>
                      <li>Actions: Approve (completes workflow) or Reject (sends back with notes)</li>
                      <li>Rejection sends file back to Approval stage for corrections</li>
                    </ul>
                  </div>
                </div>

                {/* Actions Available */}
                <div>
                  <h3 style={{
                    fontSize: '1.125rem',
                    fontWeight: '600',
                    color: '#1e293b',
                    marginBottom: '12px'
                  }}>
                    Available Actions
                  </h3>
                  <div style={{ display: 'grid', gap: '8px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.875rem' }}>
                      <span style={{ fontSize: '1.25rem' }}>ℹ️</span>
                      <span><strong>View Details:</strong> See full information about the file</span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.875rem' }}>
                      <span style={{ fontSize: '1.25rem' }}>⬇️</span>
                      <span><strong>Download:</strong> Download the PAC CSV file</span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.875rem' }}>
                      <span style={{ fontSize: '1.25rem' }}>✅</span>
                      <span><strong>Approve:</strong> Move to next stage or complete workflow</span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.875rem' }}>
                      <span style={{ fontSize: '1.25rem' }}>❌</span>
                      <span><strong>Reject:</strong> Send back to approval with notes (Triggering only)</span>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.875rem' }}>
                      <span style={{ fontSize: '1.25rem' }}>🗑️</span>
                      <span><strong>Delete:</strong> Remove file permanently (Approval only)</span>
                    </div>
                  </div>
                </div>

                {/* Status Badges */}
                <div>
                  <h3 style={{
                    fontSize: '1.125rem',
                    fontWeight: '600',
                    color: '#1e293b',
                    marginBottom: '12px'
                  }}>
                    Status Indicators
                  </h3>
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                    <span className="status-badge status-pending">Pending</span>
                    <span className="status-badge status-rejected">Rejected</span>
                    <span className="status-badge status-approved">Approved</span>
                  </div>
                </div>
              </div>

              <div className="form-actions">
                <button type="button" className="btn-primary" onClick={() => setShowWorkflowHelp(false)}>
                  Got it!
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Info Modal */}
      {showInfoModal && infoItem && (
        <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && closeInfoModal()}>
          <div className="modal-container" style={{ maxWidth: '700px' }}>
            <div className="modal-header">
              <h2 className="modal-title">Approval Details</h2>
              <button className="modal-close" onClick={closeInfoModal} type="button">✕</button>
            </div>

            <div className="modal-form">
              <div style={{
                display: 'grid',
                gap: '16px'
              }}>
                <div className="info-row">
                  <label className="info-label">File Name:</label>
                  <span className="info-value">{infoItem.filename}</span>
                </div>

                <div className="info-row">
                  <label className="info-label">Project Type:</label>
                  <span className="info-value">{infoItem.project_type}</span>
                </div>

                <div className="info-row">
                  <label className="info-label">Project ID:</label>
                  <span className="info-value">{infoItem.project_id}</span>
                </div>

                <div className="info-row">
                  <label className="info-label">Stage:</label>
                  <span className="info-value" style={{ textTransform: 'capitalize' }}>
                    {infoItem.stage}
                  </span>
                </div>

                <div className="info-row">
                  <label className="info-label">Status:</label>
                  <span className="info-value">{getStatusBadge(infoItem.status)}</span>
                </div>

                <div className="info-row">
                  <label className="info-label">Upload Date:</label>
                  <span className="info-value">{formatDate(infoItem.created_at)}</span>
                </div>

                <div className="info-row">
                  <label className="info-label">Last Updated:</label>
                  <span className="info-value">{formatDate(infoItem.updated_at)}</span>
                </div>

                <div className="info-row">
                  <label className="info-label">Uploaded By:</label>
                  <span className="info-value">{infoItem.uploader_name || '-'}</span>
                </div>

                {infoItem.notes && (
                  <div className="info-row" style={{ flexDirection: 'column', alignItems: 'flex-start' }}>
                    <label className="info-label">Notes:</label>
                    <div style={{
                      marginTop: '8px',
                      padding: '12px',
                      background: '#f8fafc',
                      borderRadius: '8px',
                      width: '100%',
                      fontSize: '0.875rem',
                      color: '#475569',
                      whiteSpace: 'pre-wrap'
                    }}>
                      {infoItem.notes}
                    </div>
                  </div>
                )}
              </div>

              <div className="form-actions">
                <button type="button" className="btn-secondary" onClick={closeInfoModal}>
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Rejection Modal */}
      {showRejectModal && (
        <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && closeRejectModal()}>
          <div className="modal-container">
            <div className="modal-header">
              <h2 className="modal-title">Reject Item</h2>
              <button className="modal-close" onClick={closeRejectModal} type="button">✕</button>
            </div>

            <form className="modal-form" onSubmit={handleRejectSubmit}>
              <div style={{
                background: '#f8fafc',
                padding: '16px',
                borderRadius: '8px',
                marginBottom: '20px'
              }}>
                <p style={{ margin: '0 0 8px', fontSize: '0.875rem', color: '#475569' }}>
                  <strong>File:</strong> {rejectingItem?.filename}
                </p>
                <p style={{ margin: '0', fontSize: '0.875rem', color: '#475569' }}>
                  <strong>Project Type:</strong> {rejectingItem?.project_type}
                </p>
              </div>

              <div className="form-field">
                <label>Rejection Notes *</label>
                <textarea
                  value={rejectNotes}
                  onChange={(e) => setRejectNotes(e.target.value)}
                  placeholder="Please provide a reason for rejection..."
                  rows={4}
                  required
                  style={{
                    width: '100%',
                    padding: '12px',
                    border: '1px solid #cbd5e1',
                    borderRadius: '8px',
                    fontSize: '0.875rem',
                    resize: 'vertical',
                    fontFamily: 'inherit'
                  }}
                />
              </div>

              <div className="form-actions">
                <button type="button" className="btn-cancel" onClick={closeRejectModal}>
                  Cancel
                </button>
                <button type="submit" className="btn-danger" disabled={submitting}>
                  {submitting ? 'Submitting...' : 'Reject & Send Back'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Additional Styles for Status Badges and Info Modal */}
      <style>{`
        .status-badge {
          display: inline-block;
          padding: 4px 12px;
          border-radius: 20px;
          font-size: 0.75rem;
          font-weight: 500;
        }
        .status-pending {
          background: #fef3c7;
          color: #d97706;
        }
        .status-rejected {
          background: #fef2f2;
          color: #dc2626;
        }
        .status-approved {
          background: #d1fae5;
          color: #059669;
        }
        .notes-cell {
          font-size: 0.8125rem;
          color: #64748b;
          cursor: help;
        }
        .info-row {
          display: flex;
          align-items: center;
          padding: 12px 0;
          border-bottom: 1px solid #e2e8f0;
        }
        .info-row:last-child {
          border-bottom: none;
        }
        .info-label {
          font-weight: 600;
          color: #475569;
          font-size: 0.875rem;
          min-width: 140px;
          margin-right: 16px;
        }
        .info-value {
          color: #1e293b;
          font-size: 0.875rem;
          flex: 1;
        }
      `}</style>
    </div>
  );
}
