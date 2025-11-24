import React, { useState, useEffect, useRef } from "react";
import { apiCall, setTransient } from "../api.js";
import "../css/Inventory.css";
import '../css/shared/DownloadButton.css';
import StatsCarousel from '../Components/shared/StatsCarousel';
import FilterBar from '../Components/shared/FilterBar';
import DataTable from '../Components/shared/DataTable';
import HelpModal, { HelpList, HelpText, CodeBlock } from '../Components/shared/HelpModal';
import TitleWithInfo from '../Components/shared/InfoButton';
import { downloadDUCustomerPOUploadTemplate } from '../utils/csvTemplateDownloader';
import Pagination from '../Components/shared/Pagination';
import DeleteConfirmationModal from '../Components/shared/DeleteConfirmationModal';

export default function CustomerPO() {
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
    line: '',
    cat: '',
    item_job: '',
    pci: '',
    si: '',
    supplier_item: '',
    description: '',
    quantity: '',
    uom: '',
    price: '',
    amount: '',
    status: '',
    project_id: ''
  });
  const [creating, setCreating] = useState(false);
  const [stats, setStats] = useState({ total_items: 0, unique_categories: 0, total_quantity: 0, total_amount: 0 });

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

      const data = await apiCall(`/customer-po/stats?${params.toString()}`);
      setStats(data || { total_items: 0, unique_categories: 0, total_quantity: 0, total_amount: 0 });
    } catch (err) {
      console.error('Failed to fetch stats:', err);
    }
  };

  const fetchCustomerPOItems = async (page = 1, search = "", limit = rowsPerPage, projectId = selectedProject) => {
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

      const { records, total } = await apiCall(`/customer-po?${params.toString()}`, {
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
    fetchCustomerPOItems(1, "", rowsPerPage, '');
    fetchStats('');
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleProjectChange = (e) => {
    const projectId = e.target.value;
    setSelectedProject(projectId);
    setSearchTerm('');
    setCurrentPage(1);
    fetchCustomerPOItems(1, '', rowsPerPage, projectId);
    fetchStats(projectId);
  };

  const onSearchChange = (e) => {
    const v = e.target.value;
    setSearchTerm(v);
    fetchCustomerPOItems(1, v, rowsPerPage, selectedProject);
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
      const result = await apiCall('/customer-po/upload-csv', {
        method: "POST",
        body: formData,
      });
      setTransient(setSuccess, `Upload successful! ${result.message}`);
      fetchCustomerPOItems(1, searchTerm);
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
      await apiCall(`/customer-po/${row.id}`, { method: "DELETE" });
      setTransient(setSuccess, "Item deleted successfully");
      fetchCustomerPOItems(currentPage, searchTerm);
      fetchStats(selectedProject);
    } catch (err) {
      setTransient(setError, err.message);
    }
  };

  const handleDeleteAllCustomerPO = () => {
    if (!selectedProject) {
      setTransient(setError, 'Please select a project first.');
      return;
    }
    setShowDeleteAllModal(true);
  };

  const confirmDeleteAllCustomerPO = async () => {
    if (!selectedProject) return;

    setDeleteAllLoading(true);
    setError('');
    setSuccess('');

    try {
      const result = await apiCall(`/customer-po/delete-all/${selectedProject}`, { method: 'DELETE' });
      const message = `Successfully deleted ${result.deleted_count} Customer PO items.`;
      setTransient(setSuccess, message);
      setShowDeleteAllModal(false);
      setSelectedProject('');
      fetchCustomerPOItems(1, '', rowsPerPage, '');
      fetchStats('');
    } catch (err) {
      setTransient(setError, err.message || 'Failed to delete Customer PO items');
      setShowDeleteAllModal(false);
    } finally {
      setDeleteAllLoading(false);
    }
  };

  const cancelDeleteAllCustomerPO = () => {
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
      await apiCall(`/customer-po/${editingRow.id}`, {
        method: "PUT",
        body: JSON.stringify(editForm),
      });
      setTransient(setSuccess, "Item updated successfully!");
      closeModal();
      fetchCustomerPOItems(currentPage, searchTerm);
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
      line: '',
      cat: '',
      item_job: '',
      pci: '',
      si: '',
      supplier_item: '',
      description: '',
      quantity: '',
      uom: '',
      price: '',
      amount: '',
      status: '',
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
      await apiCall('/customer-po', {
        method: 'POST',
        body: JSON.stringify(createForm),
      });
      setTransient(setSuccess, 'Item created successfully!');
      fetchCustomerPOItems(currentPage, searchTerm);
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
    fetchCustomerPOItems(1, searchTerm, newLimit);
  };

  // Format currency values
  const formatCurrency = (value) => {
    if (value == null || value === '') return '-';
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(value);
  };

  // Define stat cards
  const statCards = [
    { label: 'Total Items', value: stats.total_items || total },
    { label: 'Categories', value: stats.unique_categories || 0 },
    { label: 'Total Qty', value: stats.total_quantity?.toLocaleString() || 0 },
    { label: 'Total Amount', value: formatCurrency(stats.total_amount) },
    { label: 'Current Page', value: `${currentPage} / ${totalPages || 1}` },
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
    { key: 'line', label: 'Line' },
    { key: 'cat', label: 'CAT' },
    { key: 'item_job', label: 'Item/Job' },
    { key: 'pci', label: 'PCI' },
    { key: 'si', label: 'SI' },
    { key: 'supplier_item', label: 'Supplier Item' },
    { key: 'description', label: 'Description' },
    { key: 'quantity', label: 'Qty' },
    { key: 'uom', label: 'UOM' },
    { key: 'price', label: 'Price' },
    { key: 'amount', label: 'Amount' },
    { key: 'status', label: 'Status' },
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
          The Customer PO Management component allows you to manage Customer Purchase Order items.
          It supports tracking line items with quantities, prices, and amounts.
        </HelpText>
      )
    },
    {
      icon: '✨',
      title: 'Features & Buttons',
      content: (
        <HelpList
          items={[
            { label: '+ New Item', text: 'Opens a form to create a new Customer PO item. Select a project first.' },
            { label: '📤 Upload CSV', text: 'Bulk upload Customer PO data from a CSV file.' },
            { label: '🗑️ Delete All', text: 'Deletes ALL Customer PO items for the selected project.' },
            { label: 'Search', text: 'Filter items by Description, CAT, Item/Job, Supplier Item.' },
            { label: 'Project Dropdown', text: 'Filter all items by project.' },
            { label: '✏️ Edit', text: 'Modify an existing Customer PO item.' },
            { label: '🗑️ Delete', text: 'Remove a Customer PO item (requires confirmation).' },
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
              'Line',
              'CAT',
              'Item/Job',
              'PCI',
              'SI',
              'Supplier Item',
              'Description',
              'Quantity',
              'UOM',
              'Price',
              'Amount',
              'Status'
            ]}
          />
          <button className="btn-download-template" onClick={downloadDUCustomerPOUploadTemplate} type="button">
            Download CSV Template
          </button>
          <HelpText isNote>
            <strong>Note:</strong> Select a project before uploading. The file skips 4 header rows by default.
          </HelpText>
        </>
      )
    },
    {
      icon: '💡',
      title: 'Column Descriptions',
      content: (
        <HelpList
          items={[
            'Line: Line number in the PO',
            'CAT: Category (e.g., OD, IBS)',
            'Item/Job: Item or job code',
            'PCI/SI: Reference codes',
            'Description: Item description',
            'Quantity: Number of items',
            'UOM: Unit of Measure',
            'Price: Unit price',
            'Amount: Total amount (Qty x Price)',
            'Status: Current status',
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
  const renderNumericField = (label, name, value, onChange, step = "0.01") => (
    <div className="form-field">
      <label>{label}</label>
      <input
        type="number"
        step={step}
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
          title="Customer PO Management"
          subtitle="Manage Customer Purchase Order items"
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
            onClick={handleDeleteAllCustomerPO}
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
        searchPlaceholder="Search by Description, CAT, Item/Job, Supplier Item..."
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
        onClearSearch={() => { setSearchTerm(''); fetchCustomerPOItems(1, ''); }}
        clearButtonText="Clear Search"
      />

      {/* Messages */}
      {error && <div className="message error-message">{error}</div>}
      {success && <div className="message success-message">{success}</div>}
      {loading && <div className="loading-indicator">Loading Customer PO Items...</div>}

      {/* Stats Bar */}
      <StatsCarousel cards={statCards} visibleCount={4} />

      {/* Table Section */}
      <DataTable
        columns={tableColumns}
        data={rows}
        actions={tableActions}
        loading={loading}
        noDataMessage="No Customer PO items found"
        className="inventory-table-wrapper"
      />

      {/* Pagination */}
      <Pagination
        currentPage={currentPage}
        totalPages={totalPages}
        onPageChange={(page) => fetchCustomerPOItems(page, searchTerm, rowsPerPage)}
        previousText="← Previous"
        nextText="Next →"
      />

      {/* Create Modal */}
      {showCreateModal && (
        <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && closeCreateModal()}>
          <div className="modal-container" style={{ maxWidth: '900px' }}>
            <div className="modal-header">
              <h2 className="modal-title">Create New Customer PO Item</h2>
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
                  {renderNumericField('Line', 'line', createForm.line, (e) => onCreateChange('line', e.target.value), "1")}
                  {renderFormField('CAT', 'cat', createForm.cat, (e) => onCreateChange('cat', e.target.value))}
                  {renderFormField('Item/Job', 'item_job', createForm.item_job, (e) => onCreateChange('item_job', e.target.value))}
                </div>
              </div>

              {/* Reference Codes */}
              <div className="form-section">
                <h3 className="section-title">Reference Codes</h3>
                <div className="form-grid">
                  {renderFormField('PCI', 'pci', createForm.pci, (e) => onCreateChange('pci', e.target.value))}
                  {renderFormField('SI', 'si', createForm.si, (e) => onCreateChange('si', e.target.value))}
                  {renderFormField('Supplier Item', 'supplier_item', createForm.supplier_item, (e) => onCreateChange('supplier_item', e.target.value))}
                  {renderFormField('Status', 'status', createForm.status, (e) => onCreateChange('status', e.target.value))}
                </div>
              </div>

              {/* Description */}
              <div className="form-section">
                <h3 className="section-title">Description</h3>
                <div className="form-grid" style={{ gridTemplateColumns: '1fr' }}>
                  {renderFormField('Description', 'description', createForm.description, (e) => onCreateChange('description', e.target.value), true)}
                </div>
              </div>

              {/* Quantities & Pricing */}
              <div className="form-section">
                <h3 className="section-title">Quantities & Pricing</h3>
                <div className="form-grid">
                  {renderNumericField('Quantity', 'quantity', createForm.quantity, (e) => onCreateChange('quantity', e.target.value))}
                  {renderFormField('UOM', 'uom', createForm.uom, (e) => onCreateChange('uom', e.target.value))}
                  {renderNumericField('Price', 'price', createForm.price, (e) => onCreateChange('price', e.target.value))}
                  {renderNumericField('Amount', 'amount', createForm.amount, (e) => onCreateChange('amount', e.target.value))}
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
              <h2 className="modal-title">Edit Customer PO Item</h2>
              <button className="modal-close" onClick={closeModal} type="button">✕</button>
            </div>

            <div className="modal-form">
              {error && <div className="message error-message">{error}</div>}
              {success && <div className="message success-message">{success}</div>}

              {/* Basic Information */}
              <div className="form-section">
                <h3 className="section-title">Basic Information</h3>
                <div className="form-grid">
                  {renderNumericField('Line', 'line', editForm.line, (e) => onEditChange('line', e.target.value), "1")}
                  {renderFormField('CAT', 'cat', editForm.cat, (e) => onEditChange('cat', e.target.value))}
                  {renderFormField('Item/Job', 'item_job', editForm.item_job, (e) => onEditChange('item_job', e.target.value))}
                  {renderFormField('Status', 'status', editForm.status, (e) => onEditChange('status', e.target.value))}
                </div>
              </div>

              {/* Reference Codes */}
              <div className="form-section">
                <h3 className="section-title">Reference Codes</h3>
                <div className="form-grid">
                  {renderFormField('PCI', 'pci', editForm.pci, (e) => onEditChange('pci', e.target.value))}
                  {renderFormField('SI', 'si', editForm.si, (e) => onEditChange('si', e.target.value))}
                  {renderFormField('Supplier Item', 'supplier_item', editForm.supplier_item, (e) => onEditChange('supplier_item', e.target.value))}
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

              {/* Quantities & Pricing */}
              <div className="form-section">
                <h3 className="section-title">Quantities & Pricing</h3>
                <div className="form-grid">
                  {renderNumericField('Quantity', 'quantity', editForm.quantity, (e) => onEditChange('quantity', e.target.value))}
                  {renderFormField('UOM', 'uom', editForm.uom, (e) => onEditChange('uom', e.target.value))}
                  {renderNumericField('Price', 'price', editForm.price, (e) => onEditChange('price', e.target.value))}
                  {renderNumericField('Amount', 'amount', editForm.amount, (e) => onEditChange('amount', e.target.value))}
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
        onConfirm={confirmDeleteAllCustomerPO}
        onCancel={cancelDeleteAllCustomerPO}
        title="Delete All Customer PO Items for Project"
        itemName={selectedProject ? getSelectedProjectName() : ''}
        warningText="Are you sure you want to delete ALL Customer PO items for project"
        additionalInfo="This will permanently delete all related data from the following tables:"
        affectedItems={['Customer PO Items - All items for this project']}
        confirmButtonText="Delete All Items"
        loading={deleteAllLoading}
      />

      {/* Help/Info Modal */}
      <HelpModal
        show={showHelpModal}
        onClose={() => setShowHelpModal(false)}
        title="Customer PO Management - User Guide"
        sections={helpSections}
        closeButtonText="Got it!"
      />
    </div>
  );
}
