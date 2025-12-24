import React, { useEffect, useState, useRef } from 'react';
import { apiCall, setTransient } from '../api.js';
import '../css/RanProject.css';
import StatsCarousel from '../Components/shared/StatsCarousel';
import FilterBar from '../Components/shared/FilterBar';
import DataTable from '../Components/shared/DataTable';
import ModalForm from '../Components/shared/ModalForm';
import TitleWithInfo from '../Components/shared/InfoButton';
import DeleteConfirmationModal from '../Components/shared/DeleteConfirmationModal';
import HelpModal, { HelpList, HelpText } from '../Components/shared/HelpModal';
import Pagination from '../Components/shared/Pagination';

const ROWS_PER_PAGE_OPTIONS = [10, 25, 50, 100];

export default function NDPDData() {
  // --- State Management ---
  const [rows, setRows] = useState([]);
  const [currentPage, setCurrentPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(25);
  const [showForm, setShowForm] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const [uploading, setUploading] = useState(false);
  const [showDeleteAllModal, setShowDeleteAllModal] = useState(false);
  const [deleteAllLoading, setDeleteAllLoading] = useState(false);
  const [showHelpModal, setShowHelpModal] = useState(false);
  const fetchAbort = useRef(null);
  const fileInputRef = useRef(null);

  const initialForm = {
    period: '',
    ct: '',
    actual_sites: 0,
    forecast_sites: 0
  };
  const [formData, setFormData] = useState(initialForm);

  // --- API Functions ---
  const fetchRecords = async (page = 1, search = '', limit = rowsPerPage) => {
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

      const data = await apiCall(`/ndpd?${params.toString()}`, {
        signal: controller.signal,
      });
      setRows(data.records || []);
      setTotal(data.total || 0);
      setCurrentPage(page);
    } catch (err) {
      if (err.name !== 'AbortError') setTransient(setError, 'Failed to fetch NDPD records');
    } finally {
      setLoading(false);
    }
  };

  // --- Initial Data Load ---
  useEffect(() => {
    fetchRecords(1, '', rowsPerPage);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // --- Event Handlers ---
  const onSearchChange = (e) => {
    const v = e.target.value;
    setSearchTerm(v);
    fetchRecords(1, v, rowsPerPage);
  };

  const openCreateForm = () => {
    setFormData(initialForm);
    setIsEditing(false);
    setEditingId(null);
    setShowForm(true);
  };

  const openEditForm = (item) => {
    setFormData({
      period: item.period,
      ct: item.ct,
      actual_sites: item.actual_sites,
      forecast_sites: item.forecast_sites
    });
    setIsEditing(true);
    setEditingId(item.id);
    setShowForm(true);
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: name === 'actual_sites' || name === 'forecast_sites' ? parseInt(value) || 0 : value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      if (isEditing && editingId) {
        await apiCall(`/ndpd/${editingId}`, {
          method: 'PUT',
          body: JSON.stringify(formData)
        });
      } else {
        await apiCall('/ndpd', {
          method: 'POST',
          body: JSON.stringify(formData)
        });
      }

      setTransient(setSuccess, isEditing ? 'Record updated successfully!' : 'Record created successfully!');
      setShowForm(false);
      fetchRecords(currentPage, searchTerm, rowsPerPage);
    } catch (err) {
      setTransient(setError, err.message || 'Operation failed');
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Are you sure you want to delete this record?')) return;
    try {
      await apiCall(`/ndpd/${id}`, { method: 'DELETE' });
      setTransient(setSuccess, 'Record deleted successfully!');
      const newPage = rows.length === 1 && currentPage > 1 ? currentPage - 1 : currentPage;
      fetchRecords(newPage, searchTerm, rowsPerPage);
    } catch (err) {
      setTransient(setError, err.message || 'Delete failed');
    }
  };

  const handleRowsPerPageChange = (e) => {
    const newLimit = parseInt(e.target.value);
    setRowsPerPage(newLimit);
    setCurrentPage(1);
    fetchRecords(1, searchTerm, newLimit);
  };

  const handlePageChange = (newPage) => {
    if (newPage < 1 || newPage > Math.ceil(total / rowsPerPage)) return;
    fetchRecords(newPage, searchTerm, rowsPerPage);
  };

  const handleUploadCSV = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setUploading(true);
    setError('');
    setSuccess('');

    const formData = new FormData();
    formData.append('file', file);

    try {
      const result = await apiCall('/ndpd/upload-csv', {
        method: 'POST',
        body: formData,
      });

      let message = `Upload successful! ${result.inserted_count} records inserted`;
      if (result.updated_count > 0) {
        message += `, ${result.updated_count} records updated`;
      }
      if (result.errors && result.errors.length > 0) {
        message += `. ${result.errors.length} errors occurred.`;
      }

      setTransient(setSuccess, message);
      fetchRecords(1, searchTerm, rowsPerPage);
    } catch (err) {
      setTransient(setError, err.message || 'CSV upload failed');
    } finally {
      setUploading(false);
      e.target.value = '';
    }
  };

  const handleDeleteAll = () => {
    if (total === 0) {
      setTransient(setError, 'No records to delete');
      return;
    }
    console.log('Opening delete all modal');
    setShowDeleteAllModal(true);
  };

  const confirmDeleteAll = async () => {
    console.log('Confirming delete all');
    setDeleteAllLoading(true);
    setError('');
    setSuccess('');

    try {
      const result = await apiCall('/ndpd/delete-all', {
        method: 'DELETE'
      });

      console.log('Delete all result:', result);
      setTransient(setSuccess, result.message || 'All records deleted successfully');
      setShowDeleteAllModal(false);
      fetchRecords(1, '', rowsPerPage);
      setSearchTerm('');
    } catch (err) {
      console.error('Delete all error:', err);
      console.error('Error payload:', err.payload);
      // Extract more detailed error message
      let errorMessage = 'Delete all failed';
      if (err.payload) {
        // Handle validation errors
        errorMessage = JSON.stringify(err.payload);
      } else if (err.detail) {
        errorMessage = err.detail;
      } else if (err.message) {
        errorMessage = err.message;
      }
      setTransient(setError, errorMessage);
      setShowDeleteAllModal(false);
    } finally {
      setDeleteAllLoading(false);
    }
  };

  const totalPages = Math.ceil(total / rowsPerPage);

  // --- UI Component Definitions ---
  const statCards = [
    { label: 'Total Records', value: total },
    { label: 'Current Page', value: `${currentPage} / ${totalPages || 1}` },
    { label: 'Showing', value: `${rows.length} records` },
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
    { key: 'id', label: 'ID' },
    { key: 'period', label: 'Period' },
    { key: 'ct', label: 'CT' },
    { key: 'actual_sites', label: 'Actual Sites' },
    { key: 'forecast_sites', label: 'Forecast Sites' },
  ];

  const tableActions = [
    { icon: '✏️', onClick: (row) => openEditForm(row), title: 'Edit', className: 'btn-edit' },
    { icon: '🗑️', onClick: (row) => handleDelete(row.id), title: 'Delete', className: 'btn-delete' }
  ];

  const helpSections = [
    {
      icon: '📋',
      title: 'Overview',
      content: <HelpText>This page allows you to manage NDPD (Network Deployment Planning Data) records. You can create, view, edit, delete, and bulk upload records for tracking deployment planning across different periods and contract teams.</HelpText>
    },
    {
      icon: '✨',
      title: 'Features',
      content: (
        <HelpList items={[
          { label: '+ New Record', text: 'Opens a form to create a new NDPD record manually.' },
          { label: 'Upload CSV', text: 'Bulk upload records from a CSV file. The file should have columns: Period, CT, Actual Sites, Forecast Sites. Existing records (matching Period + CT) will be updated automatically.' },
          { label: 'Delete All', text: 'Removes all NDPD records from the database. Only available to senior admins.' },
          { label: 'Search', text: 'Filter records in real-time by Period or CT name.' },
          { label: 'Edit (✏️)', text: 'Update an existing record. Note: Period cannot be changed after creation.' },
          { label: 'Delete (🗑️)', text: 'Permanently removes a single record.' },
        ]} />
      )
    },
    {
      icon: '📊',
      title: 'CSV Upload Format',
      content: (
        <HelpText isNote>
          Your CSV file should have the following columns:<br/><br/>
          <strong>Period, CT, Actual Sites, Forecast Sites</strong><br/><br/>
          Example:<br/>
          2025P01, MEA CEWA AIR CT Airtel Kenya, 101, 95<br/>
          2025P01, MEA NWAO NA CT Ooredoo Algeria, 34, 60<br/><br/>
          The system will automatically update existing records if the Period and CT match, or create new ones if they don't exist.
        </HelpText>
      )
    },
    {
      icon: '💡',
      title: 'Important Notes',
      content: (
        <HelpText isNote>
          • Period cannot be edited once a record is created<br/>
          • CSV upload supports multiple encodings (UTF-8, Windows-1252, etc.)<br/>
          • Duplicate records (same Period + CT) will be updated, not duplicated<br/>
          • Delete All is only available to senior admin users<br/>
          • Use the search bar to quickly find records by Period or CT name
        </HelpText>
      )
    }
  ];

  // --- Render ---
  return (
    <div className="ran-projects-container">
      <div className="ran-projects-header">
        <TitleWithInfo
          title="NDPD Data"
          subtitle="Network Deployment Planning Data Management"
          onInfoClick={() => setShowHelpModal(true)}
        />
        <div className="header-actions">
          <button className="btn-primary" onClick={openCreateForm}>
            <span className="btn-icon">+</span> New Record
          </button>
          <button
            className="btn-primary"
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading}
          >
            <span className="btn-icon">📤</span>
            {uploading ? 'Uploading...' : 'Upload CSV'}
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv"
            style={{ display: 'none' }}
            onChange={handleUploadCSV}
          />
          <button
            className="btn-primary"
            onClick={handleDeleteAll}
            disabled={total === 0}
            style={{ background: '#dc2626' }}
          >
            <span className="btn-icon">🗑️</span> Delete All
          </button>
        </div>
      </div>

      <FilterBar
        searchTerm={searchTerm}
        onSearchChange={onSearchChange}
        searchPlaceholder="Search by Period or CT..."
        showClearButton={!!searchTerm}
        onClearSearch={() => { setSearchTerm(''); fetchRecords(1, '', rowsPerPage); }}
      />

      {error && <div className="message error-message">{error}</div>}
      {success && <div className="message success-message">{success}</div>}
      {loading && <div className="loading-indicator">Loading NDPD records...</div>}

      <StatsCarousel cards={statCards} visibleCount={4} />

      <DataTable
        columns={tableColumns}
        data={rows}
        actions={tableActions}
        emptyMessage="No NDPD records found. Create your first record!"
      />

      <Pagination
        currentPage={currentPage}
        totalPages={totalPages}
        onPageChange={handlePageChange}
        previousText="← Previous"
        nextText="Next →"
      />

      <ModalForm
        show={showForm}
        onClose={() => setShowForm(false)}
        onSubmit={handleSubmit}
        title={isEditing ? 'Edit NDPD Record' : 'Create New NDPD Record'}
        submitText={isEditing ? 'Update' : 'Create'}
      >
        <div className="form-field">
          <label>Period *</label>
          <input
            type="text"
            name="period"
            value={formData.period}
            onChange={handleChange}
            placeholder="e.g., 2025P01"
            required
            disabled={isEditing}
          />
        </div>
        <div className="form-field">
          <label>CT *</label>
          <input
            type="text"
            name="ct"
            value={formData.ct}
            onChange={handleChange}
            placeholder="Contract/Customer name"
            required
          />
        </div>
        <div className="form-field">
          <label>Actual Sites *</label>
          <input
            type="number"
            name="actual_sites"
            value={formData.actual_sites}
            onChange={handleChange}
            required
          />
        </div>
        <div className="form-field">
          <label>Forecast Sites *</label>
          <input
            type="number"
            name="forecast_sites"
            value={formData.forecast_sites}
            onChange={handleChange}
            required
          />
        </div>
      </ModalForm>

      {showDeleteAllModal && (
        <DeleteConfirmationModal
          show={showDeleteAllModal}
          onCancel={() => setShowDeleteAllModal(false)}
          onConfirm={confirmDeleteAll}
          title="Delete All NDPD Records"
          warningText="Are you sure you want to delete"
          itemName={`all ${total} NDPD records`}
          confirmButtonText="Delete All"
          loading={deleteAllLoading}
        />
      )}

      <HelpModal
        show={showHelpModal}
        onClose={() => setShowHelpModal(false)}
        title="NDPD Data - User Guide"
        sections={helpSections}
      />
    </div>
  );
}
