import React, { useEffect, useState, useRef } from 'react';
import { apiCall, setTransient } from '../api.js';
import '../css/Dismantling2.css'; // Using the new unified CSS
import StatsCarousel from './shared/StatsCarousel';
import FilterBar from './shared/FilterBar';
import DataTable from './shared/DataTable';
import ModalForm from './shared/ModalForm';
import HelpModal, { HelpList, HelpText, CodeBlock } from './shared/HelpModal';
import TitleWithInfo from './shared/InfoButton';
import Pagination from './shared/Pagination';

const ROWS_PER_PAGE_OPTIONS = [25, 50, 100, 200];

export default function Dismantling() {
  // --- State Management ---
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
  const [stats, setStats] = useState({ total_records: 0 });
  const [showHelpModal, setShowHelpModal] = useState(false);
  const fetchAbort = useRef(null);

  const initialForm = {
    nokia_link_id: '',
    nec_dismantling_link_id: '',
    no_of_dismantling: '',
    comments: '',
    pid_po: '',
  };
  const [formData, setFormData] = useState(initialForm);

  // --- API Functions ---
  const fetchProjects = async () => {
    try {
      const data = await apiCall('/get_project');
      setProjects(data || []);
      // Don't set a default project - let user select one
    } catch (err) {
      setTransient(setError, 'Failed to load projects.');
    }
  };

  const fetchStats = async (projectId = '') => {
    try {
      const params = new URLSearchParams();
      if (projectId) params.append('project_id', projectId);
      const data = await apiCall(`/dismantling/stats?${params.toString()}`);
      setStats(data);
    } catch (err) {
      console.error('Failed to fetch dismantling stats:', err);
    }
  };

  const fetchDismantling = async (page = 1, search = '', limit = rowsPerPage, projectId = selectedProject) => {
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

      const data = await apiCall(`/dismantling?${params.toString()}`, {
        signal: controller.signal,
      });
      setRows(data.records || []);
      setTotal(data.total || 0);
      setCurrentPage(page);
    } catch (err) {
      if (err.name !== 'AbortError') setTransient(setError, 'Failed to fetch dismantling records');
    } finally {
      setLoading(false);
    }
  };

  // --- Initial Data Load ---
  useEffect(() => {
    const initialize = async () => {
      await fetchProjects();
      // Wait for projects to be fetched and selectedProject to be set
    };
    initialize();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (selectedProject) {
        fetchDismantling(1, '', rowsPerPage, selectedProject);
        fetchStats(selectedProject);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedProject]);


  // --- Event Handlers ---
  const handleProjectChange = (e) => {
    const projectId = e.target.value;
    setSelectedProject(projectId);
    setSearchTerm('');
    setCurrentPage(1);
    fetchDismantling(1, '', rowsPerPage, projectId);
    fetchStats(projectId);
  };

  const onSearchChange = (e) => {
    const v = e.target.value;
    setSearchTerm(v);
    fetchDismantling(1, v, rowsPerPage, selectedProject);
  };

  const openCreateForm = () => {
    if (!selectedProject) {
      setTransient(setError, 'Please select a project to create a new record.');
      return;
    }
    setFormData({ ...initialForm, pid_po: selectedProject });
    setIsEditing(false);
    setEditingId(null);
    setShowForm(true);
  };

  const openEditForm = (item) => {
    setFormData({ ...item });
    setIsEditing(true);
    setEditingId(item.id);
    setShowForm(true);
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const payload = {
        ...formData,
        no_of_dismantling: parseInt(formData.no_of_dismantling || 0),
      };

      if (isEditing && editingId) {
        await apiCall(`/dismantling/${editingId}`, { method: 'PUT', body: JSON.stringify(payload) });
      } else {
        await apiCall('/dismantling', { method: 'POST', body: JSON.stringify(payload) });
      }

      setTransient(setSuccess, isEditing ? 'Record updated successfully!' : 'Record created successfully!');
      setShowForm(false);
      fetchDismantling(currentPage, searchTerm, rowsPerPage, selectedProject);
      fetchStats(selectedProject);
    } catch (err) {
      setTransient(setError, err.message || 'Operation failed');
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Are you sure you want to delete this record?')) return;
    try {
      await apiCall(`/dismantling/${id}`, { method: 'DELETE' });
      setTransient(setSuccess, 'Record deleted successfully!');
      fetchDismantling(currentPage, searchTerm, rowsPerPage, selectedProject);
      fetchStats(selectedProject);
    } catch (err) {
      setTransient(setError, err.message || 'Delete failed');
    }
  };

  const handleUpload = async (e) => {
    const file = e.target.files[0];
    if (!file || !selectedProject) {
      setTransient(setError, 'Please select a project before uploading CSV.');
      e.target.value = "";
      return;
    }

    setUploading(true);
    const formData = new FormData();
    formData.append("file", file);
    formData.append("pid_po", selectedProject);
    try {
      const result = await apiCall('/dismantling/upload-csv', { method: "POST", body: formData });
      setTransient(setSuccess, `Upload successful! ${result.inserted} rows inserted.`);
      fetchDismantling(1, '', rowsPerPage, selectedProject);
      fetchStats(selectedProject);
    } catch (err) {
      setTransient(setError, err.message);
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  };

  const handleRowsPerPageChange = (e) => {
    const newLimit = parseInt(e.target.value);
    setRowsPerPage(newLimit);
    setCurrentPage(1);
    fetchDismantling(1, searchTerm, newLimit, selectedProject);
  };

  const totalPages = Math.ceil(total / rowsPerPage);

  // --- UI Component Definitions ---
  const statCards = [
    { label: 'Total Records', value: stats.total_records },
    { label: 'Current Page', value: `${currentPage} / ${totalPages || 1}` },
    { label: 'Showing', value: `${rows.length} records` },
    {
      label: 'Records Per Page',
      isEditable: true,
      component: (
        <select className="stat-select" value={rowsPerPage} onChange={handleRowsPerPageChange}>
          {ROWS_PER_PAGE_OPTIONS.map(val => <option key={val} value={val}>{val}</option>)}
        </select>
      )
    }
  ];

  const tableColumns = [
    { key: 'nokia_link_id', label: 'Nokia Link ID' },
    { key: 'nec_dismantling_link_id', label: 'NEC Dismantling Link ID' },
    { key: 'no_of_dismantling', label: 'No. of Dismantling' },
    { key: 'comments', label: 'Comments' },
  ];

  const tableActions = [
    { icon: '✏️', onClick: (row) => openEditForm(row), title: 'Edit', className: 'btn-edit' },
    { icon: '🗑️', onClick: (row) => handleDelete(row.id), title: 'Delete', className: 'btn-delete' }
  ];

  const helpSections = [
    { icon: '📋', title: 'Overview', content: <HelpText>Manage dismantling records associated with your projects. You can add, edit, delete, and bulk upload records via CSV.</HelpText> },
    {
      icon: '✨', title: 'Features', content: (
        <HelpList items={[
            { label: '+ New Record', text: 'Opens a form to create a new dismantling record for the selected project.' },
            { label: '📤 Upload CSV', text: 'Allows bulk uploading of records from a CSV file.' },
            { label: 'Project Dropdown', text: 'Filters all records and statistics by the selected project.' },
        ]} />
      )
    },
    {
      icon: '📁', title: 'CSV Upload Guidelines', content: (
        <>
          <HelpText>Your CSV file must contain the following headers in the first row (case-sensitive):</HelpText>
          <HelpList items={[
            { label: 'Required Headers', text: 'nokia_link_id, nec_dismantling_link_id, no_of_dismantling, comments' },
            'All four headers must be present in the CSV file',
            'The header row should be the first row in the file',
            'Data rows should follow the header row',
          ]} />
          <HelpText isNote style={{ marginTop: '1rem' }}><strong>Important:</strong> Ensure a project is selected before uploading, as all records in the file will be assigned to that project.</HelpText>
        </>
      )
    }
  ];

  // --- Render ---
  return (
    <div className="dismantling-container">
      <div className="dismantling-header">
        <TitleWithInfo
          title="Dismantling Records"
          subtitle="Track and manage all dismantling activities"
          onInfoClick={() => setShowHelpModal(true)}
        />
        <div className="header-actions">
          <button className={`btn-primary ${!selectedProject ? 'disabled' : ''}`} onClick={openCreateForm} disabled={!selectedProject}>
            <span className="btn-icon">+</span> New Record
          </button>
          <label className={`btn-secondary ${uploading || !selectedProject ? 'disabled' : ''}`}>
            <span className="btn-icon">📤</span> Upload CSV
            <input type="file" accept=".csv" style={{ display: "none" }} disabled={uploading || !selectedProject} onChange={handleUpload} />
          </label>
        </div>
      </div>

      <FilterBar
        searchTerm={searchTerm}
        onSearchChange={onSearchChange}
        searchPlaceholder="Search by Link ID or comments..."
        dropdowns={[
          {
            label: 'Project', value: selectedProject, onChange: handleProjectChange, placeholder: '-- Select a Project --',
            options: projects.map(p => ({ value: p.pid_po, label: `${p.project_name} (${p.pid_po})` }))
          }
        ]}
        showClearButton={!!searchTerm}
        onClearSearch={() => { setSearchTerm(''); fetchDismantling(1, '', rowsPerPage, selectedProject); }}
      />

      <StatsCarousel cards={statCards} visibleCount={4} />

      {error && <div className="message error-message">{error}</div>}
      {success && <div className="message success-message">{success}</div>}
      {loading && <div className="loading-indicator">Loading records...</div>}

      <DataTable
        columns={tableColumns}
        data={rows}
        actions={tableActions}
        loading={loading}
        noDataMessage="No dismantling records found"
        className="dismantling-table-wrapper"
      />

      <Pagination
        currentPage={currentPage}
        totalPages={totalPages}
        onPageChange={(page) => fetchDismantling(page, searchTerm, rowsPerPage, selectedProject)}
      />

      <ModalForm
        show={showForm}
        onClose={() => setShowForm(false)}
        onSubmit={handleSubmit}
        title={isEditing ? `Edit Record #${editingId}` : 'Create New Record'}
        submitText={isEditing ? 'Update Record' : 'Create Record'}
      >
        <div className="form-field full-width">
          <label>Project ID</label>
          <input type="text" name="pid_po" value={formData.pid_po} disabled className="disabled-input" />
        </div>
        <div className="form-field">
          <label>Nokia Link ID *</label>
          <input type="text" name="nokia_link_id" value={formData.nokia_link_id} onChange={handleChange} required />
        </div>
        <div className="form-field">
          <label>NEC Dismantling Link ID *</label>
          <input type="text" name="nec_dismantling_link_id" value={formData.nec_dismantling_link_id} onChange={handleChange} required />
        </div>
        <div className="form-field">
          <label>Number of Dismantling *</label>
          <input type="number" name="no_of_dismantling" value={formData.no_of_dismantling} onChange={handleChange} required />
        </div>
        <div className="form-field full-width">
          <label>Comments</label>
          <input type="text" name="comments" value={formData.comments} onChange={handleChange} />
        </div>
      </ModalForm>

      <HelpModal
        show={showHelpModal}
        onClose={() => setShowHelpModal(false)}
        title="Dismantling Records - User Guide"
        sections={helpSections}
      />
    </div>
  );
}