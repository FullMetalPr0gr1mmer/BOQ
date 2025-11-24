import React, { useState, useEffect, useRef } from "react";
import { apiCall, setTransient } from "../api.js";
import "../css/Inventory.css";
import '../css/shared/DownloadButton.css';
import StatsCarousel from '../Components/shared/StatsCarousel';
import FilterBar from '../Components/shared/FilterBar';
import DataTable from '../Components/shared/DataTable';
import HelpModal, { HelpList, HelpText, CodeBlock } from '../Components/shared/HelpModal';
import TitleWithInfo from '../Components/shared/InfoButton';
import { downloadDUODBOQItemsUploadTemplate } from '../utils/csvTemplateDownloader';
import Pagination from '../Components/shared/Pagination';
import DeleteConfirmationModal from '../Components/shared/DeleteConfirmationModal';

export default function ODBOQItems() {
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
  const [showDeleteAllModal, setShowDeleteAllModal] = useState(false);
  const [deleteAllLoading, setDeleteAllLoading] = useState(false);

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingRow, setEditingRow] = useState(null);
  const [editForm, setEditForm] = useState({});
  const [updating, setUpdating] = useState(false);

  const [projects, setProjects] = useState([]);
  const [selectedProject, setSelectedProject] = useState('');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [createForm, setCreateForm] = useState({
    cat: '',
    bu: '',
    category: '',
    description: '',
    uom: '',
    new_sran: '',
    sran_exp_1cc_l800: '',
    sran_exp_1cc_l1800: '',
    sran_exp_2cc_l800_l1800: '',
    sran_exp_2cc_l1800_l2100: '',
    sran_exp_2cc_l800_l2100: '',
    new_5g_n78: '',
    exp_5g_3cc: '',
    exp_5g_n41_reuse: '',
    exp_5g_3cc_ontop: '',
    exp_5g_band_swap: '',
    nr_fdd_model1_activation: '',
    nr_fdd_model1_tdra: '',
    nr_fdd_model1_2025: '',
    antenna_cutover_ipaa: '',
    total_qty: '',
    project_id: ''
  });
  const [creating, setCreating] = useState(false);
  const [stats, setStats] = useState({ total_items: 0, unique_categories: 0, unique_bus: 0 });

  const fetchAbort = useRef(null);

  const fetchProjects = async () => {
    try {
      const data = await apiCall('/du-projects');
      const projectsList = data?.records || data || [];
      setProjects(projectsList);
    } catch (err) {
      setTransient(setError, 'Failed to load projects.');
      console.error(err);
    }
  };

  const fetchStats = async (projectId = '') => {
    try {
      const params = new URLSearchParams();
      if (projectId) params.append('project_id', projectId);

      const data = await apiCall(`/boq-items/stats?${params.toString()}`);
      setStats(data || { total_items: 0, unique_categories: 0, unique_bus: 0 });
    } catch (err) {
      console.error('Failed to fetch stats:', err);
    }
  };

  const fetchBOQItems = async (page = 1, search = "", limit = rowsPerPage, projectId = selectedProject) => {
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

      const { records, total } = await apiCall(`/boq-items?${params.toString()}`, {
        signal: controller.signal,
      });

      setRows(records || []);
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
    fetchBOQItems(1, "", rowsPerPage, '');
    fetchStats('');
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleProjectChange = (e) => {
    const projectId = e.target.value;
    setSelectedProject(projectId);
    setSearchTerm('');
    setCurrentPage(1);
    fetchBOQItems(1, '', rowsPerPage, projectId);
    fetchStats(projectId);
  };

  const onSearchChange = (e) => {
    const v = e.target.value;
    setSearchTerm(v);
    fetchBOQItems(1, v, rowsPerPage, selectedProject);
  };

  const handleUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    if (!selectedProject) {
      setTransient(setError, 'Please select a project before uploading.');
      e.target.value = "";
      return;
    }

    setUploading(true);
    setError("");
    setSuccess("");
    const formData = new FormData();
    formData.append("file", file);
    formData.append("project_id", selectedProject);
    formData.append("skip_header_rows", "4");

    try {
      const result = await apiCall('/boq-items/upload-csv', {
        method: "POST",
        body: formData,
      });
      setTransient(setSuccess, `Upload successful! ${result.message}`);
      fetchBOQItems(1, searchTerm);
      fetchStats(selectedProject);
    } catch (err) {
      setTransient(setError, err.message);
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  };

  const handleDelete = async (row) => {
    if (!window.confirm("Are you sure you want to delete this item?")) return;
    try {
      await apiCall(`/boq-items/${row.id}`, { method: "DELETE" });
      setTransient(setSuccess, "Item deleted successfully");
      fetchBOQItems(currentPage, searchTerm);
      fetchStats(selectedProject);
    } catch (err) {
      setTransient(setError, err.message);
    }
  };

  const handleDeleteAllBOQItems = () => {
    if (!selectedProject) {
      setTransient(setError, 'Please select a project first.');
      return;
    }
    setShowDeleteAllModal(true);
  };

  const confirmDeleteAllBOQItems = async () => {
    if (!selectedProject) return;

    setDeleteAllLoading(true);
    setError('');
    setSuccess('');

    try {
      const result = await apiCall(`/boq-items/delete-all/${selectedProject}`, { method: 'DELETE' });
      const message = `Successfully deleted ${result.deleted_count} BOQ items.`;
      setTransient(setSuccess, message);
      setShowDeleteAllModal(false);
      setSelectedProject('');
      fetchBOQItems(1, '', rowsPerPage, '');
      fetchStats('');
    } catch (err) {
      setTransient(setError, err.message || 'Failed to delete BOQ items');
      setShowDeleteAllModal(false);
    } finally {
      setDeleteAllLoading(false);
    }
  };

  const cancelDeleteAllBOQItems = () => {
    if (!deleteAllLoading) {
      setShowDeleteAllModal(false);
    }
  };

  const getSelectedProjectName = () => {
    const project = projects.find(p => p.pid_po === selectedProject);
    return project ? `${project.project_name} (${project.pid_po})` : selectedProject;
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
      await apiCall(`/boq-items/${editingRow.id}`, {
        method: "PUT",
        body: JSON.stringify(editForm),
      });
      setTransient(setSuccess, "Item updated successfully!");
      closeModal();
      fetchBOQItems(currentPage, searchTerm);
      fetchStats(selectedProject);
    } catch (err) {
      setTransient(setError, err.message);
    } finally {
      setUpdating(false);
    }
  };

  const openCreateModal = () => {
    if (!selectedProject) {
      setTransient(setError, 'Please select a project to create a new item.');
      return;
    }
    setCreateForm({
      cat: '',
      bu: '',
      category: '',
      description: '',
      uom: '',
      new_sran: '',
      sran_exp_1cc_l800: '',
      sran_exp_1cc_l1800: '',
      sran_exp_2cc_l800_l1800: '',
      sran_exp_2cc_l1800_l2100: '',
      sran_exp_2cc_l800_l2100: '',
      new_5g_n78: '',
      exp_5g_3cc: '',
      exp_5g_n41_reuse: '',
      exp_5g_3cc_ontop: '',
      exp_5g_band_swap: '',
      nr_fdd_model1_activation: '',
      nr_fdd_model1_tdra: '',
      nr_fdd_model1_2025: '',
      antenna_cutover_ipaa: '',
      total_qty: '',
      project_id: selectedProject
    });
    setShowCreateModal(true);
    setError('');
    setSuccess('');
  };

  const closeCreateModal = () => {
    setShowCreateModal(false);
    setCreateForm({});
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
      await apiCall('/boq-items', {
        method: 'POST',
        body: JSON.stringify(createForm),
      });
      setTransient(setSuccess, 'Item created successfully!');
      fetchBOQItems(currentPage, searchTerm);
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
    fetchBOQItems(1, searchTerm, newLimit);
  };

  // Define stat cards
  const statCards = [
    { label: 'Total Items', value: stats.total_items || total },
    { label: 'Categories', value: stats.unique_categories || 0 },
    { label: 'BUs', value: stats.unique_bus || 0 },
    { label: 'Current Page', value: `${currentPage} / ${totalPages || 1}` },
    { label: 'Showing', value: `${rows.length} items` },
    {
      label: 'Rows Per Page',
      isEditable: true,
      component: (
        <select className="stat-select" value={rowsPerPage} onChange={handleRowsPerPageChange}>
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
    { key: 'cat', label: 'CAT' },
    { key: 'bu', label: 'BU' },
    { key: 'category', label: 'Category' },
    { key: 'description', label: 'Description' },
    { key: 'uom', label: 'UoM' },
    { key: 'new_sran', label: 'New SRAN' },
    { key: 'sran_exp_1cc_l800', label: 'SRAN Exp L800' },
    { key: 'sran_exp_1cc_l1800', label: 'SRAN Exp L1800' },
    { key: 'sran_exp_2cc_l800_l1800', label: 'SRAN Exp L800+L1800' },
    { key: 'sran_exp_2cc_l1800_l2100', label: 'SRAN Exp L1800+L2100' },
    { key: 'sran_exp_2cc_l800_l2100', label: 'SRAN Exp L800+L2100' },
    { key: 'new_5g_n78', label: 'New 5G n78' },
    { key: 'exp_5g_3cc', label: '5G Exp 3CC' },
    { key: 'exp_5g_n41_reuse', label: '5G n41 Reuse' },
    { key: 'exp_5g_3cc_ontop', label: '5G 3CC Ontop' },
    { key: 'exp_5g_band_swap', label: '5G Band Swap' },
    { key: 'nr_fdd_model1_activation', label: 'NR FDD Activation' },
    { key: 'nr_fdd_model1_tdra', label: 'NR FDD TDRA' },
    { key: 'nr_fdd_model1_2025', label: 'NR FDD 2025' },
    { key: 'antenna_cutover_ipaa', label: 'Antenna IPAA' },
    { key: 'total_qty', label: 'Total Qty' },
    { key: 'project_id', label: 'Project' }
  ];

  // Define table actions
  const tableActions = [
    { icon: '✏️', onClick: (row) => openEditModal(row), title: 'Edit', className: 'btn-edit' },
    { icon: '🗑️', onClick: (row) => handleDelete(row), title: 'Delete', className: 'btn-delete' }
  ];

  // Help modal sections
  const helpSections = [
    {
      icon: '📋',
      title: 'Overview',
      content: (
        <HelpText>
          The OD BOQ Items Management component allows you to manage Bill of Quantities items with multi-level headers.
          It supports New SRAN, SRAN Expansion, 5G, and NR FDD scope types.
        </HelpText>
      )
    },
    {
      icon: '✨',
      title: 'Features & Buttons',
      content: (
        <HelpList
          items={[
            { label: '+ New Item', text: 'Opens a form to create a new BOQ item. Select a project first.' },
            { label: '📤 Upload CSV', text: 'Bulk upload BOQ data from a CSV file with multi-level headers.' },
            { label: '🗑️ Delete All', text: 'Deletes ALL BOQ items for the selected project.' },
            { label: 'Search', text: 'Filter items by Description, CAT, BU, Category.' },
            { label: 'Project Dropdown', text: 'Filter all items by project.' },
            { label: '✏️ Edit', text: 'Modify an existing BOQ item.' },
            { label: '🗑️ Delete', text: 'Remove a BOQ item (requires confirmation).' },
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
            Your CSV file must have these exact headers (in order):
          </HelpText>
          <CodeBlock
            items={[
              'CAT',
              'BU',
              'Category',
              'Description',
              'UoM',
              'New SRAN',
              'SRAN Exp 1cc L800',
              'SRAN Exp 1cc L1800',
              'SRAN Exp 2cc L800+L1800',
              'SRAN Exp 2cc L1800+L2100',
              'SRAN Exp 2cc L800+L2100',
              'New 5G n78',
              '5G Exp 3CC',
              '5G n41 Reuse',
              '5G 3CC Ontop',
              '5G Band Swap',
              'NR FDD Activation',
              'NR FDD TDRA',
              'NR FDD 2025',
              'Antenna IPAA',
              'Total Qty'
            ]}
          />
          <button className="btn-download-template" onClick={downloadDUODBOQItemsUploadTemplate} type="button">
            Download CSV Template
          </button>
          <HelpText isNote>
            <strong>Note:</strong> Select a project before uploading. The file skips 4 header rows by default (multi-level headers).
          </HelpText>
        </>
      )
    },
    {
      icon: '💡',
      title: 'Scope Types',
      content: (
        <HelpList
          items={[
            'New SRAN: New 3G/LTE sites',
            'SRAN Expansion: 1cc to 3cc or 2cc to 3cc expansions',
            'New 5G-n78: New 5G colocation n78',
            '5G Expansion: 3CC, n41 reuse, band swap',
            '5G-NR FDD: FDD NR activation and readiness',
            'Antenna Cutover (IPAA+): IPAA services',
          ]}
        />
      )
    }
  ];

  // Form field renderer helper
  const renderFormField = (label, name, value, onChange, required = false, disabled = false) => (
    <div className="form-field">
      <label>{label}{required && ' *'}</label>
      <input
        type="text"
        name={name}
        value={value != null ? value : ''}
        onChange={onChange}
        required={required}
        disabled={disabled}
        className={disabled ? 'disabled-input' : ''}
      />
    </div>
  );

  // Numeric form field renderer - uses != null to properly show 0 values
  const renderNumericField = (label, name, value, onChange) => (
    <div className="form-field">
      <label>{label}</label>
      <input
        type="number"
        step="0.01"
        name={name}
        value={value != null ? value : ''}
        onChange={onChange}
      />
    </div>
  );

  return (
    <div className="inventory-container">
      {/* Header Section */}
      <div className="inventory-header">
        <TitleWithInfo
          title="OD BOQ Items Management"
          subtitle="Manage Bill of Quantities with multi-level headers"
          onInfoClick={() => setShowHelpModal(true)}
          infoTooltip="How to use this component"
        />
        <div className="header-actions">
          <button
            className={`btn-primary ${!selectedProject ? 'disabled' : ''}`}
            onClick={openCreateModal}
            disabled={!selectedProject}
            title={!selectedProject ? "Select a project first" : "Create a new item"}
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
          <button
            className={`btn-danger ${!selectedProject ? 'disabled' : ''}`}
            onClick={handleDeleteAllBOQItems}
            disabled={!selectedProject}
            title={!selectedProject ? "Select a project first" : "Delete all items for this project"}
          >
            <span className="btn-icon">🗑️</span>
            Delete All
          </button>
        </div>
      </div>

      {/* Filters Section */}
      <FilterBar
        searchTerm={searchTerm}
        onSearchChange={onSearchChange}
        searchPlaceholder="Search by Description, CAT, BU, Category..."
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
        onClearSearch={() => { setSearchTerm(''); fetchBOQItems(1, ''); }}
        clearButtonText="Clear Search"
      />

      {/* Messages */}
      {error && <div className="message error-message">{error}</div>}
      {success && <div className="message success-message">{success}</div>}
      {loading && <div className="loading-indicator">Loading BOQ Items...</div>}

      {/* Stats Bar */}
      <StatsCarousel cards={statCards} visibleCount={4} />

      {/* Table Section */}
      <DataTable
        columns={tableColumns}
        data={rows}
        actions={tableActions}
        loading={loading}
        noDataMessage="No BOQ items found"
        className="inventory-table-wrapper"
      />

      {/* Pagination */}
      <Pagination
        currentPage={currentPage}
        totalPages={totalPages}
        onPageChange={(page) => fetchBOQItems(page, searchTerm, rowsPerPage)}
        previousText="← Previous"
        nextText="Next →"
      />

      {/* Create Modal */}
      {showCreateModal && (
        <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && closeCreateModal()}>
          <div className="modal-container" style={{ maxWidth: '900px' }}>
            <div className="modal-header">
              <h2 className="modal-title">Create New BOQ Item</h2>
              <button className="modal-close" onClick={closeCreateModal} type="button">✕</button>
            </div>

            <form className="modal-form" onSubmit={handleCreate}>
              {error && <div className="message error-message">{error}</div>}
              {success && <div className="message success-message">{success}</div>}

              {/* Basic Information */}
              <div className="form-section">
                <h3 className="section-title">Basic Information</h3>
                <div className="form-grid">
                  {renderFormField('Project ID', 'project_id', createForm.project_id, (e) => onCreateChange('project_id', e.target.value), true, true)}
                  {renderFormField('CAT', 'cat', createForm.cat, (e) => onCreateChange('cat', e.target.value))}
                  {renderFormField('BU', 'bu', createForm.bu, (e) => onCreateChange('bu', e.target.value))}
                  {renderFormField('Category', 'category', createForm.category, (e) => onCreateChange('category', e.target.value))}
                </div>
              </div>

              {/* Description & UoM */}
              <div className="form-section">
                <h3 className="section-title">Description</h3>
                <div className="form-grid">
                  {renderFormField('Description', 'description', createForm.description, (e) => onCreateChange('description', e.target.value), true)}
                  {renderFormField('UoM', 'uom', createForm.uom, (e) => onCreateChange('uom', e.target.value))}
                </div>
              </div>

              {/* SRAN Quantities */}
              <div className="form-section">
                <h3 className="section-title">SRAN Quantities</h3>
                <div className="form-grid">
                  {renderNumericField('New SRAN', 'new_sran', createForm.new_sran, (e) => onCreateChange('new_sran', e.target.value))}
                  {renderNumericField('SRAN Exp 1cc L800', 'sran_exp_1cc_l800', createForm.sran_exp_1cc_l800, (e) => onCreateChange('sran_exp_1cc_l800', e.target.value))}
                  {renderNumericField('SRAN Exp 1cc L1800', 'sran_exp_1cc_l1800', createForm.sran_exp_1cc_l1800, (e) => onCreateChange('sran_exp_1cc_l1800', e.target.value))}
                  {renderNumericField('SRAN Exp 2cc L800+L1800', 'sran_exp_2cc_l800_l1800', createForm.sran_exp_2cc_l800_l1800, (e) => onCreateChange('sran_exp_2cc_l800_l1800', e.target.value))}
                  {renderNumericField('SRAN Exp 2cc L1800+L2100', 'sran_exp_2cc_l1800_l2100', createForm.sran_exp_2cc_l1800_l2100, (e) => onCreateChange('sran_exp_2cc_l1800_l2100', e.target.value))}
                  {renderNumericField('SRAN Exp 2cc L800+L2100', 'sran_exp_2cc_l800_l2100', createForm.sran_exp_2cc_l800_l2100, (e) => onCreateChange('sran_exp_2cc_l800_l2100', e.target.value))}
                </div>
              </div>

              {/* 5G Quantities */}
              <div className="form-section">
                <h3 className="section-title">5G Quantities</h3>
                <div className="form-grid">
                  {renderNumericField('New 5G n78', 'new_5g_n78', createForm.new_5g_n78, (e) => onCreateChange('new_5g_n78', e.target.value))}
                  {renderNumericField('5G Exp 3CC', 'exp_5g_3cc', createForm.exp_5g_3cc, (e) => onCreateChange('exp_5g_3cc', e.target.value))}
                  {renderNumericField('5G n41 Reuse', 'exp_5g_n41_reuse', createForm.exp_5g_n41_reuse, (e) => onCreateChange('exp_5g_n41_reuse', e.target.value))}
                  {renderNumericField('5G 3CC Ontop', 'exp_5g_3cc_ontop', createForm.exp_5g_3cc_ontop, (e) => onCreateChange('exp_5g_3cc_ontop', e.target.value))}
                  {renderNumericField('5G Band Swap', 'exp_5g_band_swap', createForm.exp_5g_band_swap, (e) => onCreateChange('exp_5g_band_swap', e.target.value))}
                </div>
              </div>

              {/* NR FDD & Other */}
              <div className="form-section">
                <h3 className="section-title">NR FDD & Other Quantities</h3>
                <div className="form-grid">
                  {renderNumericField('NR FDD Activation', 'nr_fdd_model1_activation', createForm.nr_fdd_model1_activation, (e) => onCreateChange('nr_fdd_model1_activation', e.target.value))}
                  {renderNumericField('NR FDD TDRA', 'nr_fdd_model1_tdra', createForm.nr_fdd_model1_tdra, (e) => onCreateChange('nr_fdd_model1_tdra', e.target.value))}
                  {renderNumericField('NR FDD 2025', 'nr_fdd_model1_2025', createForm.nr_fdd_model1_2025, (e) => onCreateChange('nr_fdd_model1_2025', e.target.value))}
                  {renderNumericField('Antenna IPAA', 'antenna_cutover_ipaa', createForm.antenna_cutover_ipaa, (e) => onCreateChange('antenna_cutover_ipaa', e.target.value))}
                  {renderNumericField('Total Qty', 'total_qty', createForm.total_qty, (e) => onCreateChange('total_qty', e.target.value))}
                </div>
              </div>

              {/* Form Actions */}
              <div className="form-actions">
                <button type="button" className="btn-cancel" onClick={closeCreateModal}>
                  Cancel
                </button>
                <button type="submit" className="btn-submit" disabled={creating}>
                  {creating ? 'Creating...' : 'Create Item'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Edit Modal */}
      {isModalOpen && (
        <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && closeModal()}>
          <div className="modal-container" style={{ maxWidth: '900px' }}>
            <div className="modal-header">
              <h2 className="modal-title">Edit BOQ Item</h2>
              <button className="modal-close" onClick={closeModal} type="button">✕</button>
            </div>

            <div className="modal-form">
              {error && <div className="message error-message">{error}</div>}
              {success && <div className="message success-message">{success}</div>}

              {/* Basic Information */}
              <div className="form-section">
                <h3 className="section-title">Basic Information</h3>
                <div className="form-grid">
                  {renderFormField('CAT', 'cat', editForm.cat, (e) => onEditChange('cat', e.target.value))}
                  {renderFormField('BU', 'bu', editForm.bu, (e) => onEditChange('bu', e.target.value))}
                  {renderFormField('Category', 'category', editForm.category, (e) => onEditChange('category', e.target.value))}
                  {renderFormField('UoM', 'uom', editForm.uom, (e) => onEditChange('uom', e.target.value))}
                </div>
              </div>

              {/* Description & Project */}
              <div className="form-section">
                <h3 className="section-title">Description & Project</h3>
                <div className="form-grid">
                  {renderFormField('Description', 'description', editForm.description, (e) => onEditChange('description', e.target.value))}
                  <div className="form-field">
                    <label>Project</label>
                    <select
                      value={editForm.project_id || ''}
                      onChange={(e) => onEditChange('project_id', e.target.value)}
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

              {/* SRAN Quantities */}
              <div className="form-section">
                <h3 className="section-title">SRAN Quantities</h3>
                <div className="form-grid">
                  {renderNumericField('New SRAN', 'new_sran', editForm.new_sran, (e) => onEditChange('new_sran', e.target.value))}
                  {renderNumericField('SRAN Exp 1cc L800', 'sran_exp_1cc_l800', editForm.sran_exp_1cc_l800, (e) => onEditChange('sran_exp_1cc_l800', e.target.value))}
                  {renderNumericField('SRAN Exp 1cc L1800', 'sran_exp_1cc_l1800', editForm.sran_exp_1cc_l1800, (e) => onEditChange('sran_exp_1cc_l1800', e.target.value))}
                  {renderNumericField('SRAN Exp 2cc L800+L1800', 'sran_exp_2cc_l800_l1800', editForm.sran_exp_2cc_l800_l1800, (e) => onEditChange('sran_exp_2cc_l800_l1800', e.target.value))}
                  {renderNumericField('SRAN Exp 2cc L1800+L2100', 'sran_exp_2cc_l1800_l2100', editForm.sran_exp_2cc_l1800_l2100, (e) => onEditChange('sran_exp_2cc_l1800_l2100', e.target.value))}
                  {renderNumericField('SRAN Exp 2cc L800+L2100', 'sran_exp_2cc_l800_l2100', editForm.sran_exp_2cc_l800_l2100, (e) => onEditChange('sran_exp_2cc_l800_l2100', e.target.value))}
                </div>
              </div>

              {/* 5G Quantities */}
              <div className="form-section">
                <h3 className="section-title">5G Quantities</h3>
                <div className="form-grid">
                  {renderNumericField('New 5G n78', 'new_5g_n78', editForm.new_5g_n78, (e) => onEditChange('new_5g_n78', e.target.value))}
                  {renderNumericField('5G Exp 3CC', 'exp_5g_3cc', editForm.exp_5g_3cc, (e) => onEditChange('exp_5g_3cc', e.target.value))}
                  {renderNumericField('5G n41 Reuse', 'exp_5g_n41_reuse', editForm.exp_5g_n41_reuse, (e) => onEditChange('exp_5g_n41_reuse', e.target.value))}
                  {renderNumericField('5G 3CC Ontop', 'exp_5g_3cc_ontop', editForm.exp_5g_3cc_ontop, (e) => onEditChange('exp_5g_3cc_ontop', e.target.value))}
                  {renderNumericField('5G Band Swap', 'exp_5g_band_swap', editForm.exp_5g_band_swap, (e) => onEditChange('exp_5g_band_swap', e.target.value))}
                </div>
              </div>

              {/* NR FDD & Other */}
              <div className="form-section">
                <h3 className="section-title">NR FDD & Other Quantities</h3>
                <div className="form-grid">
                  {renderNumericField('NR FDD Activation', 'nr_fdd_model1_activation', editForm.nr_fdd_model1_activation, (e) => onEditChange('nr_fdd_model1_activation', e.target.value))}
                  {renderNumericField('NR FDD TDRA', 'nr_fdd_model1_tdra', editForm.nr_fdd_model1_tdra, (e) => onEditChange('nr_fdd_model1_tdra', e.target.value))}
                  {renderNumericField('NR FDD 2025', 'nr_fdd_model1_2025', editForm.nr_fdd_model1_2025, (e) => onEditChange('nr_fdd_model1_2025', e.target.value))}
                  {renderNumericField('Antenna IPAA', 'antenna_cutover_ipaa', editForm.antenna_cutover_ipaa, (e) => onEditChange('antenna_cutover_ipaa', e.target.value))}
                  {renderNumericField('Total Qty', 'total_qty', editForm.total_qty, (e) => onEditChange('total_qty', e.target.value))}
                </div>
              </div>

              {/* Form Actions */}
              <div className="form-actions">
                <button type="button" className="btn-cancel" onClick={closeModal}>
                  Cancel
                </button>
                <button className="btn-submit" onClick={handleUpdate} disabled={updating}>
                  {updating ? 'Updating...' : 'Update Item'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Delete All Confirmation Modal */}
      <DeleteConfirmationModal
        show={showDeleteAllModal}
        onConfirm={confirmDeleteAllBOQItems}
        onCancel={cancelDeleteAllBOQItems}
        title="Delete All BOQ Items for Project"
        itemName={selectedProject ? getSelectedProjectName() : ''}
        warningText="Are you sure you want to delete ALL BOQ items for project"
        additionalInfo="This will permanently delete all related data from the following tables:"
        affectedItems={['OD BOQ Items - All items for this project']}
        confirmButtonText="Delete All Items"
        loading={deleteAllLoading}
      />

      {/* Help/Info Modal */}
      <HelpModal
        show={showHelpModal}
        onClose={() => setShowHelpModal(false)}
        title="OD BOQ Items Management - User Guide"
        sections={helpSections}
        closeButtonText="Got it!"
      />
    </div>
  );
}
