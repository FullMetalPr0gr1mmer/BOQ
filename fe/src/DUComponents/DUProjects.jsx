import React, { useEffect, useState, useRef } from 'react';
import { apiCall, setTransient } from '../api.js';
import '../css/RanProject.css';
import StatsCarousel from '../Components/shared/StatsCarousel';
import FilterBar from '../Components/shared/FilterBar';
import DataTable from '../Components/shared/DataTable';
import ModalForm from '../Components/shared/ModalForm';
import HelpModal, { HelpList, HelpText } from '../Components/shared/HelpModal';
import TitleWithInfo from '../Components/shared/InfoButton';
import Pagination from '../Components/shared/Pagination';

const ROWS_PER_PAGE_OPTIONS = [5, 10, 25, 50];

export default function DUProjects() {
  // --- State Management ---
  const [rows, setRows] = useState([]);
  const [currentPage, setCurrentPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  const [showForm, setShowForm] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const [stats, setStats] = useState({ total_projects: 0 });
  const [showHelpModal, setShowHelpModal] = useState(false);
  const fetchAbort = useRef(null);

  const initialForm = {
    pid: '',
    project_name: '',
    po: ''
  };
  const [formData, setFormData] = useState(initialForm);

  // --- API Functions ---
  const fetchProjects = async (page = 1, search = '', limit = rowsPerPage) => {
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

      const data = await apiCall(`/du-projects?${params.toString()}`, {
        signal: controller.signal,
      });
      setRows(data.records || []);
      setTotal(data.total || 0);
      setCurrentPage(page);
    } catch (err) {
      if (err.name !== 'AbortError') setTransient(setError, 'Failed to fetch DU projects');
    } finally {
      setLoading(false);
    }
  };

  const fetchStats = async () => {
    try {
      const data = await apiCall('/du-projects/stats/summary');
      setStats(data || { total_projects: 0 });
    } catch (err) {
      console.error('Failed to fetch stats:', err);
    }
  };

  // --- Initial Data Load ---
  useEffect(() => {
    fetchProjects(1, '', rowsPerPage);
    fetchStats();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // --- Event Handlers ---
  const onSearchChange = (e) => {
    const v = e.target.value;
    setSearchTerm(v);
    fetchProjects(1, v, rowsPerPage);
  };

  const openCreateForm = () => {
    setFormData(initialForm);
    setIsEditing(false);
    setEditingId(null);
    setShowForm(true);
  };

  const openEditForm = (item) => {
    setFormData({
      pid: item.pid,
      project_name: item.project_name,
      po: item.po
    });
    setIsEditing(true);
    setEditingId(item.pid_po);
    setShowForm(true);
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      if (isEditing && editingId) {
        // Only project_name is editable for an existing project
        await apiCall(`/du-projects/${editingId}`, { method: 'PUT', body: JSON.stringify({ project_name: formData.project_name }) });
      } else {
        await apiCall('/du-projects', { method: 'POST', body: JSON.stringify(formData) });
      }

      setTransient(setSuccess, isEditing ? 'Project updated successfully!' : 'Project created successfully!');
      setShowForm(false);
      fetchProjects(currentPage, searchTerm, rowsPerPage);
      fetchStats();
    } catch (err) {
      setTransient(setError, err.message || 'Operation failed');
    }
  };

  const handleDelete = async (pid_po) => {
    if (!window.confirm('Are you sure you want to delete this project? This will also delete all related BOQ entries.')) return;
    try {
      await apiCall(`/du-projects/${pid_po}`, { method: 'DELETE' });
      setTransient(setSuccess, 'Project deleted successfully!');
      const newPage = rows.length === 1 && currentPage > 1 ? currentPage - 1 : currentPage;
      fetchProjects(newPage, searchTerm, rowsPerPage);
      fetchStats();
    } catch (err) {
      setTransient(setError, err.message || 'Delete failed');
    }
  };

  const handleRowsPerPageChange = (e) => {
    const newLimit = parseInt(e.target.value);
    setRowsPerPage(newLimit);
    setCurrentPage(1);
    fetchProjects(1, searchTerm, newLimit);
  };

  const totalPages = Math.ceil(total / rowsPerPage);

  // --- UI Component Definitions ---
  const statCards = [
    { label: 'Total Projects', value: stats.total_projects },
    { label: 'Current Page', value: `${currentPage} / ${totalPages || 1}` },
    { label: 'Showing', value: `${rows.length} projects` },
    {
      label: 'Rows Per Page', isEditable: true,
      component: (
        <select className="stat-select" value={rowsPerPage} onChange={handleRowsPerPageChange}>
          {ROWS_PER_PAGE_OPTIONS.map(val => <option key={val} value={val}>{val}</option>)}
        </select>
      )
    }
  ];

  const tableColumns = [
    { key: 'pid', label: 'Project ID' },
    { key: 'project_name', label: 'Project Name' },
    { key: 'po', label: 'Purchase Order (PO)' },
  ];

  const tableActions = [
    { icon: '✏️', onClick: (row) => openEditForm(row), title: 'Edit', className: 'btn-edit' },
    { icon: '🗑️', onClick: (row) => handleDelete(row.pid_po), title: 'Delete', className: 'btn-delete' }
  ];

  const helpSections = [
    { icon: '📋', title: 'Overview', content: <HelpText>This page allows you to manage DU (Digital Transformation) projects for BOQ management. You can create, view, edit, and delete projects.</HelpText> },
    { icon: '✨', title: 'Features', content: (
      <HelpList items={[
        { label: '+ New Project', text: 'Opens a form to create a new DU project.' },
        { label: 'Search', text: 'Filter projects in real-time by their name, ID, or PO number.' },
        { label: 'Edit (✏️)', text: 'Allows you to update the name of an existing project.' },
        { label: 'Delete (🗑️)', text: 'Permanently removes a project and all related BOQ entries.' },
      ]} />
    )},
    { icon: '💡', title: 'Important Notes', content: (
      <HelpText isNote>When editing a project, the Project ID and Purchase Order cannot be changed. Only the Project Name can be updated. Deleting a project will also delete all associated BOQ entries.</HelpText>
    )}
  ];

  // --- Render ---
  return (
    <div className="ran-projects-container">
      <div className="ran-projects-header">
        <TitleWithInfo
          title="DU Projects"
          subtitle="Manage Digital Transformation projects for BOQ management"
          onInfoClick={() => setShowHelpModal(true)}
        />
        <div className="header-actions">
          <button className="btn-primary" onClick={openCreateForm}>
            <span className="btn-icon">+</span> New Project
          </button>
        </div>
      </div>

      <FilterBar
        searchTerm={searchTerm}
        onSearchChange={onSearchChange}
        searchPlaceholder="Search by Project Name, ID, or PO..."
        showClearButton={!!searchTerm}
        onClearSearch={() => { setSearchTerm(''); fetchProjects(1, '', rowsPerPage); }}
      />

      {error && <div className="message error-message">{error}</div>}
      {success && <div className="message success-message">{success}</div>}
      {loading && <div className="loading-indicator">Loading projects...</div>}

      <StatsCarousel cards={statCards} visibleCount={4} />

      <DataTable
        columns={tableColumns}
        data={rows}
        actions={tableActions}
        loading={loading}
        noDataMessage="No DU projects found"
        className="ran-projects-table-wrapper"
      />

      <Pagination
        currentPage={currentPage}
        totalPages={totalPages}
        onPageChange={(page) => fetchProjects(page, searchTerm, rowsPerPage)}
      />

      <ModalForm
        show={showForm}
        onClose={() => setShowForm(false)}
        onSubmit={handleSubmit}
        title={isEditing ? `Edit Project: ${formData.project_name}` : 'Create New DU Project'}
        submitText={isEditing ? 'Update Project' : 'Create Project'}
      >
        <div className="form-field">
          <label>Project Name *</label>
          <input type="text" name="project_name" value={formData.project_name} onChange={handleChange} required />
        </div>
        <div className="form-field">
          <label>Project ID (PID) *</label>
          <input type="text" name="pid" value={formData.pid} onChange={handleChange} required disabled={isEditing} />
        </div>
        <div className="form-field">
          <label>Purchase Order (PO) *</label>
          <input type="text" name="po" value={formData.po} onChange={handleChange} required disabled={isEditing} />
        </div>
      </ModalForm>

      <HelpModal
        show={showHelpModal}
        onClose={() => setShowHelpModal(false)}
        title="DU Projects - User Guide"
        sections={helpSections}
      />
    </div>
  );
}
