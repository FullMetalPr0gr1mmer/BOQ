import React, { useEffect, useState, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiCall, setTransient } from '../api';
import '../css/RanProject.css';
import StatsCarousel from '../Components/shared/StatsCarousel';
import FilterBar from '../Components/shared/FilterBar';
import DataTable from '../Components/shared/DataTable';
import ModalForm from '../Components/shared/ModalForm';
import HelpModal, { HelpList, HelpText, CodeBlock } from '../Components/shared/HelpModal';
import TitleWithInfo from '../Components/shared/InfoButton';
import Pagination from '../Components/shared/Pagination';

const ROWS_PER_PAGE_OPTIONS = [5, 10, 25, 50];

export default function ROPProject() {
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
  const [csvModalMode, setCsvModalMode] = useState(false);
  const [lastCsvFile, setLastCsvFile] = useState(null);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [projectToDelete, setProjectToDelete] = useState(null);
  const fetchAbort = useRef(null);
  const navigate = useNavigate();

  const initialForm = {
    pid: '',
    po: '',
    project_name: '',
    wbs: '',
    country: '',
    currency: 'Euros'
  };
  const [formData, setFormData] = useState(initialForm);

  // --- API Functions ---
  const fetchProjects = async () => {
    try {
      if (fetchAbort.current) fetchAbort.current.abort();
      const controller = new AbortController();
      fetchAbort.current = controller;

      setLoading(true);
      setError('');

      const data = await apiCall('/rop-projects/', {
        signal: controller.signal,
      });
      setRows(data || []);
      setTotal(data?.length || 0);
    } catch (err) {
      if (err.name !== 'AbortError') setTransient(setError, 'Failed to fetch projects');
    } finally {
      setLoading(false);
    }
  };

  // Calculate stats from current data
  const calculateStats = () => {
    setStats({ total_projects: total });
  };

  // --- Initial Data Load ---
  useEffect(() => {
    fetchProjects();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Calculate stats when data changes
  useEffect(() => {
    calculateStats();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rows, total]);

  // --- Event Handlers ---
  const onSearchChange = (e) => {
    const v = e.target.value.toLowerCase();
    setSearchTerm(v);
    setCurrentPage(1);
  };

  // Filter data based on search
  const filteredRows = rows.filter((proj) => {
    if (!searchTerm) return true;
    return (
      proj.po?.toLowerCase().includes(searchTerm) ||
      proj.project_name?.toLowerCase().includes(searchTerm) ||
      proj.wbs?.toLowerCase().includes(searchTerm) ||
      proj.country?.toLowerCase().includes(searchTerm)
    );
  });

  // Paginate filtered data
  const paginatedRows = filteredRows.slice(
    (currentPage - 1) * rowsPerPage,
    currentPage * rowsPerPage
  );

  const totalPages = Math.ceil(filteredRows.length / rowsPerPage);

  const openCreateForm = () => {
    setFormData(initialForm);
    setIsEditing(false);
    setEditingId(null);
    setCsvModalMode(false);
    setShowForm(true);
  };

  const openEditForm = (item) => {
    setFormData({
      pid: item.pid,
      po: item.po,
      project_name: item.project_name,
      wbs: item.wbs || '',
      country: item.country || '',
      currency: item.currency || 'Euros'
    });
    setIsEditing(true);
    setEditingId(item.pid_po);
    setCsvModalMode(false);
    setShowForm(true);
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      if (csvModalMode) {
        // CSV Fix mode
        const formDataToSend = new FormData();
        formDataToSend.append('pid', formData.pid);
        formDataToSend.append('po', formData.po);
        formDataToSend.append('project_name', formData.project_name);
        formDataToSend.append('wbs', formData.wbs);
        formDataToSend.append('country', formData.country);
        formDataToSend.append('currency', formData.currency);
        if (lastCsvFile) {
          formDataToSend.append('file', lastCsvFile);
        }
        await apiCall('/rop-projects/upload-csv-fix', {
          method: 'POST',
          body: formDataToSend
        });
        setCsvModalMode(false);
        setTransient(setSuccess, 'CSV uploaded with project data successfully!');
      } else if (isEditing && editingId) {
        // Edit mode
        await apiCall(`/rop-projects/${editingId}`, {
          method: 'PUT',
          body: JSON.stringify(formData)
        });
        setTransient(setSuccess, 'Project updated successfully!');
      } else {
        // Create mode
        await apiCall('/rop-projects/', {
          method: 'POST',
          body: JSON.stringify(formData)
        });
        setTransient(setSuccess, 'Project created successfully!');
      }

      setShowForm(false);
      fetchProjects();
    } catch (err) {
      setTransient(setError, err.message || 'Operation failed');
    }
  };

  const handleDelete = (row) => {
    setProjectToDelete(row);
    setShowDeleteModal(true);
  };

  const confirmDelete = async () => {
    if (!projectToDelete) return;
    try {
      await apiCall(`/rop-projects/${projectToDelete.pid_po}`, { method: 'DELETE' });
      setTransient(setSuccess, 'Project and related items deleted successfully!');
      setShowDeleteModal(false);
      setProjectToDelete(null);
      fetchProjects();
    } catch (err) {
      setTransient(setError, err.message || 'Delete failed');
      setShowDeleteModal(false);
      setProjectToDelete(null);
    }
  };

  const cancelDelete = () => {
    setShowDeleteModal(false);
    setProjectToDelete(null);
  };

  const handleLevel1 = (row) => {
    navigate('/rop-lvl1', {
      state: {
        pid_po: row.pid_po,
        project_name: row.project_name,
        currency: row.currency
      }
    });
  };

  const handleCsvUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    const formData = new FormData();
    formData.append('file', file);
    setLastCsvFile(file);

    try {
      await apiCall('/rop-projects/upload-csv', {
        method: 'POST',
        body: formData
      });
      setTransient(setSuccess, 'CSV uploaded and processed successfully!');
      fetchProjects();
    } catch (err) {
      const msg = err?.message || 'Failed to upload CSV';
      setTransient(setError, msg);
      if (msg.includes('CSV must contain at least one Level 0 entry')) {
        setCsvModalMode(true);
        setShowForm(true);
      }
    }
    document.getElementById('csv-upload-input').value = '';
  };

  const handleRowsPerPageChange = (e) => {
    const newLimit = parseInt(e.target.value);
    setRowsPerPage(newLimit);
    setCurrentPage(1);
  };

  // --- UI Component Definitions ---
  const statCards = [
    { label: 'Total Projects', value: stats.total_projects },
    { label: 'Current Page', value: `${currentPage} / ${totalPages || 1}` },
    { label: 'Showing', value: `${paginatedRows.length} projects` },
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
    { key: 'po', label: 'Customer Material Number' },
    { key: 'project_name', label: 'Project Name' },
    { key: 'wbs', label: 'WBS' },
    { key: 'currency', label: 'Currency' },
  ];

  const tableActions = [
    { icon: '✏️', onClick: (row) => openEditForm(row), title: 'Edit', className: 'btn-edit' },
    { icon: '🗑️', onClick: (row) => handleDelete(row), title: 'Delete', className: 'btn-delete' },
    { icon: 'View PCIs', onClick: (row) => handleLevel1(row), title: 'View Product Component Items', className: 'btn-level1' }
  ];

  const helpSections = [
    {
      icon: '📋',
      title: 'Overview',
      content: <HelpText>This page allows you to manage ROP (Return on Products) projects. You can create, view, edit, delete projects, and upload project data via CSV files.</HelpText>
    },
    {
      icon: '✨',
      title: 'Features',
      content: (
        <HelpList items={[
          { label: '+ New Project', text: 'Opens a form to manually create a new project with all required fields.' },
          { label: 'Upload QC CSV', text: 'Allows you to upload a CSV file containing project and component data. The system will automatically parse and import the data.' },
          { label: 'Search', text: 'Filter projects in real-time by Customer Material Number (PO), Project Name, WBS, or Country.' },
          { label: 'Edit (✏️)', text: 'Update project details including name, WBS, country, and currency.' },
          { label: 'Delete (🗑️)', text: 'Permanently removes a project and all related PCIs (Product Component Items), SIs (Sub Items), and Packages.' },
          { label: 'Level 1 (📊)', text: 'Navigate to the Level 1 page to view and manage Product Component Items (PCIs) for the project.' },
        ]} />
      )
    },
    {
      icon: '📤',
      title: 'How to Upload CSV',
      content: (
        <>
          <HelpText>The CSV file should follow a specific structure with hierarchical levels:</HelpText>
          <HelpList items={[
            'Level 0: Project information (first row with project details)',
            'Level 1: Product Component Items (PCIs)',
            'Level 2: Sub Items (SIs) - components of PCIs',
          ]} />
          <HelpText>Required CSV columns:</HelpText>
          <CodeBlock items={[
            'Level',
            'Product Number',
            'Product Item Name',
            'Product Component Name',
            'Sub Component Name',
            'Quantity',
            'Unit Price',
            'Total Price'
          ]} />
          <HelpText isNote>
            If the CSV does not contain a Level 0 entry (project information), you will be prompted to manually enter the project details (PID, PO, Project Name, WBS, Country, Currency) to complete the upload.
          </HelpText>
        </>
      )
    },
    {
      icon: '💡',
      title: 'Important Notes',
      content: (
        <>
          <HelpText isNote>When editing a project, the Project ID (PID) and Purchase Order (PO) cannot be changed as they form the unique identifier.</HelpText>
          <HelpText isNote>Deleting a project will cascade delete all related data including PCIs, SIs, Packages, and Monthly Distributions. This action cannot be undone.</HelpText>
        </>
      )
    }
  ];

  // --- Render ---
  return (
    <div className="ran-projects-container">
      <div className="ran-projects-header">
        <TitleWithInfo
          title="ROP Projects"
          subtitle="Manage all Return on Products projects"
          onInfoClick={() => setShowHelpModal(true)}
        />
        <div className="header-actions">
          <button className="btn-primary" style={{ visibility: 'hidden' }} onClick={openCreateForm}>
            <span className="btn-icon">+</span> New Project
          </button>
          <form id="csv-upload-form" style={{ display: 'inline' }}>
            <input
              type="file"
              accept=".csv"
              style={{ display: 'none' }}
              id="csv-upload-input"
              onChange={handleCsvUpload}
            />
            <button
              type="button"
              className="btn-primary"
              onClick={() => document.getElementById('csv-upload-input').click()}
            >
              <span className="btn-icon">📤</span> Upload QC CSV
            </button>
          </form>
        </div>
      </div>

      <FilterBar
        searchTerm={searchTerm}
        onSearchChange={onSearchChange}
        searchPlaceholder="Search by PO, Project Name, WBS, or Country..."
        showClearButton={!!searchTerm}
        onClearSearch={() => { setSearchTerm(''); setCurrentPage(1); }}
      />

      {error && <div className="message error-message">{error}</div>}
      {success && <div className="message success-message">{success}</div>}
      {loading && <div className="loading-indicator">Loading projects...</div>}

      <StatsCarousel cards={statCards} visibleCount={4} />

      <DataTable
        columns={tableColumns}
        data={paginatedRows}
        actions={tableActions}
        loading={loading}
        noDataMessage="No projects found"
        className="ran-projects-table-wrapper"
      />

      <Pagination
        currentPage={currentPage}
        totalPages={totalPages}
        onPageChange={(page) => setCurrentPage(page)}
      />

      <ModalForm
        show={showForm}
        onClose={() => { setShowForm(false); setCsvModalMode(false); }}
        onSubmit={handleSubmit}
        title={csvModalMode ? 'Complete CSV Upload - Enter Project Details' : (isEditing ? `Edit Project: ${formData.project_name}` : 'Create New Project')}
        submitText={csvModalMode ? 'Upload CSV with Project Data' : (isEditing ? 'Update Project' : 'Create Project')}
      >
        <div className="form-field">
          <label>Project ID (PID) *</label>
          <input type="text" name="pid" value={formData.pid} onChange={handleChange} required disabled={isEditing} />
        </div>
        <div className="form-field">
          <label>Purchase Order (PO) *</label>
          <input type="text" name="po" value={formData.po} onChange={handleChange} required disabled={isEditing} />
        </div>
        <div className="form-field">
          <label>Project Name *</label>
          <input type="text" name="project_name" value={formData.project_name} onChange={handleChange} required />
        </div>
        <div className="form-field">
          <label>WBS</label>
          <input type="text" name="wbs" value={formData.wbs} onChange={handleChange} />
        </div>
        <div className="form-field">
          <label>Country</label>
          <input type="text" name="country" value={formData.country} onChange={handleChange} />
        </div>
        <div className="form-field">
          <label>Currency *</label>
          <input type="text" name="currency" value={formData.currency} onChange={handleChange} required placeholder="e.g., Euros, USD, GBP" />
        </div>
      </ModalForm>

      <HelpModal
        show={showHelpModal}
        onClose={() => setShowHelpModal(false)}
        title="ROP Projects - User Guide"
        sections={helpSections}
      />

      {/* Delete Confirmation Modal */}
      {showDeleteModal && (
        <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && cancelDelete()}>
          <div className="modal-container delete-modal">
            <div className="modal-header-delete">
              <div className="warning-icon">⚠️</div>
              <h2 className="modal-title">Confirm Project Deletion</h2>
            </div>
            <div className="modal-body-delete">
              <p className="delete-warning-text">
                Are you sure you want to delete project <strong>"{projectToDelete?.project_name}"</strong>?
              </p>
              <p className="delete-info-text">
                This will also permanently delete all related:
              </p>
              <ul className="delete-items-list">
                <li>PCIs (Product Component Items)</li>
                <li>SIs (Sub Items)</li>
                <li>Packages</li>
                <li>Monthly Distributions</li>
              </ul>
              <p className="delete-warning-note">
                ⚠️ This action cannot be undone.
              </p>
            </div>
            <div className="modal-footer-delete">
              <button type="button" className="btn-cancel" onClick={cancelDelete}>
                Cancel
              </button>
              <button type="button" className="btn-delete-confirm" onClick={confirmDelete}>
                Delete Project
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
