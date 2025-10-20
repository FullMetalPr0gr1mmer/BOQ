import React, { useEffect, useState, useRef } from 'react';
import { apiCall, setTransient } from '../api.js';
import '../css/RanAntennaSerials.css'; // Using the new unified CSS
import StatsCarousel from '../Components/shared/StatsCarousel';
import FilterBar from '../Components/shared/FilterBar';
import DataTable from '../Components/shared/DataTable';
import ModalForm from '../Components/shared/ModalForm';
import HelpModal, { HelpList, HelpText } from '../Components/shared/HelpModal';
import TitleWithInfo from '../Components/shared/InfoButton';
import Pagination from '../Components/shared/Pagination';

const ROWS_PER_PAGE_OPTIONS = [25, 50, 100, 200];

export default function RANAntennaSerials() {
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
  const [stats, setStats] = useState({ total_antennas: 0, unique_mrbts: 0 });
  const [showHelpModal, setShowHelpModal] = useState(false);
  const fetchAbort = useRef(null);

  const initialForm = {
    mrbts: '',
    antenna_model: '',
    serial_number: '',
    project_id: ''
  };
  const [formData, setFormData] = useState(initialForm);

  // --- API Functions ---
  const fetchProjects = async () => {
    try {
      const data = await apiCall('/ran-projects');
      const projectsList = data?.records || data || [];
      setProjects(projectsList);
      // Don't set a default project - let user select one
    } catch (err) {
      setTransient(setError, 'Failed to load projects.');
    }
  };

  const fetchStats = async (projectId = '') => {
    try {
      const params = new URLSearchParams();
      if (projectId) params.append('project_id', projectId);
      // Assuming a stats endpoint exists
      const data = await apiCall(`/ran-antenna-serials/stats?${params.toString()}`);
      setStats(data);
    } catch (err) {
      console.error('Failed to fetch RAN stats:', err);
    }
  };

  const fetchAntennaSerials = async (page = 1, search = '', limit = rowsPerPage, projectId = selectedProject) => {
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

      const data = await apiCall(`/ran-antenna-serials?${params.toString()}`, {
        signal: controller.signal,
      });
      setRows(data.records || []);
      setTotal(data.total || 0);
      setCurrentPage(page);
    } catch (err) {
      if (err.name !== 'AbortError') setTransient(setError, 'Failed to fetch RAN records');
    } finally {
      setLoading(false);
    }
  };

  // --- Initial Data Load ---
  useEffect(() => {
    fetchProjects();
    fetchAntennaSerials(1, '', rowsPerPage, '');
    fetchStats('');
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (selectedProject) {
        fetchAntennaSerials(1, '', rowsPerPage, selectedProject);
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
    // Data fetching will be handled by the useEffect watching selectedProject
  };

  const onSearchChange = (e) => {
    const v = e.target.value;
    setSearchTerm(v);
    fetchAntennaSerials(1, v, rowsPerPage, selectedProject);
  };

  const openCreateForm = () => {
    if (!selectedProject) {
      setTransient(setError, 'Please select a project to create a new record.');
      return;
    }
    setFormData({ ...initialForm, project_id: selectedProject });
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
      if (isEditing && editingId) {
        await apiCall(`/ran-antenna-serials/${editingId}`, { method: 'PUT', body: JSON.stringify(formData) });
      } else {
        await apiCall('/ran-antenna-serials', { method: 'POST', body: JSON.stringify(formData) });
      }

      setTransient(setSuccess, isEditing ? 'Record updated successfully!' : 'Record created successfully!');
      setShowForm(false);
      fetchAntennaSerials(currentPage, searchTerm, rowsPerPage, selectedProject);
      fetchStats(selectedProject);
    } catch (err) {
      setTransient(setError, err.message || 'Operation failed');
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Are you sure you want to delete this record?')) return;
    try {
      await apiCall(`/ran-antenna-serials/${id}`, { method: 'DELETE' });
      setTransient(setSuccess, 'Record deleted successfully!');
      fetchAntennaSerials(currentPage, searchTerm, rowsPerPage, selectedProject);
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
    formData.append("project_id", selectedProject);
    try {
      const result = await apiCall('/ran-antenna-serials/upload-csv', { method: "POST", body: formData });
      setTransient(setSuccess, `Upload successful! ${result.message || (result.inserted + ' rows inserted.')}`);
      fetchAntennaSerials(1, '', rowsPerPage, selectedProject);
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
    fetchAntennaSerials(1, searchTerm, newLimit, selectedProject);
  };

  const totalPages = Math.ceil(total / rowsPerPage);

  // --- UI Component Definitions ---
  const statCards = [
    { label: 'Total Antennas', value: stats.total_antennas || 0 },
    { label: 'Unique MRBTS', value: stats.unique_mrbts || 0 },
    { label: 'Current Page', value: `${currentPage} / ${totalPages || 1}` },
    { label: 'Showing', value: `${rows.length} records` },
    {
      label: 'Records Per Page', isEditable: true,
      component: (
        <select className="stat-select" value={rowsPerPage} onChange={handleRowsPerPageChange}>
          {ROWS_PER_PAGE_OPTIONS.map(val => <option key={val} value={val}>{val}</option>)}
        </select>
      )
    }
  ];

  const tableColumns = [
    { key: 'mrbts', label: 'MRBTS' },
    { key: 'antenna_model', label: 'Antenna Model' },
    { key: 'serial_number', label: 'Serial Number' },
    { key: 'project_id', label: 'Project ID' },
  ];

  const tableActions = [
    { icon: '✏️', onClick: (row) => openEditForm(row), title: 'Edit', className: 'btn-edit' },
    { icon: '🗑️', onClick: (row) => handleDelete(row.id), title: 'Delete', className: 'btn-delete' }
  ];

  const helpSections = [
    { icon: '📋', title: 'Overview', content: <HelpText>Manage RAN Antenna Serial records for your projects. You can add, edit, delete, and bulk upload records via CSV.</HelpText> },
    { icon: '✨', title: 'Features', content: (
        <HelpList items={[
            { label: '+ New Record', text: 'Create a new antenna serial record for the selected project.' },
            { label: '📤 Upload CSV', text: 'Bulk upload records from a CSV file.' },
            { label: 'Project Dropdown', text: 'Filter records and stats by the selected project.' },
        ]} />
    )},
    { icon: '📁', title: 'CSV Upload Guidelines', content: (
        <HelpText isNote>Your CSV file needs the headers: <code>mrbts</code>, <code>antenna_model</code>, and <code>serial_number</code>. All records will be assigned to the currently selected project.</HelpText>
    )}
  ];

  // --- Render ---
  return (
    <div className="ran-container">
      <div className="ran-header">
        <TitleWithInfo
          title="RAN Antenna Serials"
          subtitle="Track and manage antenna serial numbers"
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
        searchPlaceholder="Search by MRBTS, model, or serial..."
        dropdowns={[{
            label: 'Project', value: selectedProject, onChange: handleProjectChange, placeholder: '-- Select a Project --',
            options: projects.map(p => ({ value: p.pid_po, label: `${p.project_name} (${p.pid_po})` }))
        }]}
        showClearButton={!!searchTerm}
        onClearSearch={() => { setSearchTerm(''); fetchAntennaSerials(1, '', rowsPerPage, selectedProject); }}
      />

      {error && <div className="message error-message">{error}</div>}
      {success && <div className="message success-message">{success}</div>}
      {loading && <div className="loading-indicator">Loading records...</div>}

      <StatsCarousel cards={statCards} visibleCount={4} />

      <DataTable
        columns={tableColumns}
        data={rows}
        actions={tableActions}
        loading={loading}
        noDataMessage="No RAN antenna serials found"
        className="ran-table-wrapper"
      />

      <Pagination
        currentPage={currentPage}
        totalPages={totalPages}
        onPageChange={(page) => fetchAntennaSerials(page, searchTerm, rowsPerPage, selectedProject)}
      />

      <ModalForm
        show={showForm}
        onClose={() => setShowForm(false)}
        onSubmit={handleSubmit}
        title={isEditing ? `Edit Record #${editingId}` : 'Create New Record'}
        submitText={isEditing ? 'Update Record' : 'Create Record'}
      >
        <div className="form-field">
            <label>Project ID *</label>
            <select name="project_id" value={formData.project_id} onChange={handleChange} required>
                <option value="">-- Select Project --</option>
                {projects.map(p => <option key={p.pid_po} value={p.pid_po}>{`${p.project_name} (${p.pid_po})`}</option>)}
            </select>
        </div>
        <div className="form-field">
          <label>MRBTS *</label>
          <input type="text" name="mrbts" value={formData.mrbts} onChange={handleChange} required />
        </div>
        <div className="form-field">
          <label>Antenna Model *</label>
          <input type="text" name="antenna_model" value={formData.antenna_model} onChange={handleChange} required />
        </div>
        <div className="form-field">
          <label>Serial Number *</label>
          <input type="text" name="serial_number" value={formData.serial_number} onChange={handleChange} required />
        </div>
      </ModalForm>

      <HelpModal
        show={showHelpModal}
        onClose={() => setShowHelpModal(false)}
        title="RAN Antenna Serials - User Guide"
        sections={helpSections}
      />
    </div>
  );
}