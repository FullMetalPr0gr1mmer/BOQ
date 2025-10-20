import React, { useState, useEffect, useRef } from "react";
import { apiCall, setTransient } from "../api.js";
import "../css/Inventory.css";
import StatsCarousel from '../Components/shared/StatsCarousel';
import FilterBar from '../Components/shared/FilterBar';
import HelpModal, { HelpList, HelpText, CodeBlock } from '../Components/shared/HelpModal';
import TitleWithInfo from '../Components/shared/InfoButton';
import Pagination from '../Components/shared/Pagination';

// Define the Service Type mapping for the dropdown
const serviceTypes = {
  "1": "Software",
  "2": "Hardware",
  "3": "Service",
};

export default function RANLvl3() {
  const [rows, setRows] = useState([]);
  const [currentPage, setCurrentPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(50);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [loading, setLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const [showHelpModal, setShowHelpModal] = useState(false);

  const [projects, setProjects] = useState([]);
  const [selectedProject, setSelectedProject] = useState('');

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingRow, setEditingRow] = useState(null);
  const [editForm, setEditForm] = useState({});
  const [updating, setUpdating] = useState(false);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [createForm, setCreateForm] = useState({});
  const [creating, setCreating] = useState(false);

  const [expandedRows, setExpandedRows] = useState(new Set());
  const [childEditingRow, setChildEditingRow] = useState(null);
  const [isChildModalOpen, setIsChildModalOpen] = useState(false);
  const [childEditForm, setChildEditForm] = useState({});
  const [childUpdating, setChildUpdating] = useState(false);
  const [childUploading, setChildUploading] = useState(false);
  const [stats, setStats] = useState({ total_records: 0, total_items: 0 });

  const fetchAbort = useRef(null);

  const fetchProjects = async () => {
    try {
      const data = await apiCall('/ran-projects');
      const projectsList = data?.records || data || [];
      setProjects(projectsList);
      // Don't set a default project - let user select one
    } catch (err) {
      setTransient(setError, 'Failed to load projects. Please ensure you have project access.');
      console.error(err);
    }
  };

  // Calculate stats from current data
  const calculateStats = () => {
    const totalChildItems = rows.reduce((sum, row) => sum + (row.items?.length || 0), 0);
    setStats({ total_records: total, total_items: totalChildItems });
  };

  const fetchRANLvl3 = async (page = 1, search = "", limit = rowsPerPage, projectId = selectedProject) => {
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

      const { records, total } = await apiCall(`/ranlvl3?${params.toString()}`, {
        signal: controller.signal,
      });

      setRows(
        (records || []).map((r) => ({
          id: r.id,
          project_id: r.project_id,
          item_name: r.item_name,
          key: r.key,
          service_type: r.service_type || [],
          uom: r.uom,
          total_quantity: r.total_quantity,
          total_price: r.total_price,
          category: r.category,
          po_line: r.po_line,
          upl_line: r.upl_line,
          ran_category: r.ran_category,
          items: r.items || [],
        }))
      );
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
    fetchRANLvl3(1, "", rowsPerPage, '');
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    calculateStats();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rows, total]);

  const handleProjectChange = (e) => {
    const projectId = e.target.value;
    setSelectedProject(projectId);
    setSearchTerm('');
    setCurrentPage(1);
    fetchRANLvl3(1, '', rowsPerPage, projectId);
  };

  const onSearchChange = (e) => {
    const v = e.target.value;
    setSearchTerm(v);
    fetchRANLvl3(1, v, rowsPerPage, selectedProject);
  };

  const handleChildUpload = async (e, parentId) => {
    const file = e.target.files[0];
    if (!file) return;

    setChildUploading(true);
    setError("");
    setSuccess("");
    const formData = new FormData();
    formData.append("file", file);

    try {
      const result = await apiCall(`/ranlvl3/${parentId}/items/upload-csv`, {
        method: "POST",
        body: formData,
      });
      setTransient(setSuccess, `Upload successful! ${result.inserted || "?"} items inserted.`);
      fetchRANLvl3(currentPage, searchTerm);
    } catch (err) {
      setTransient(setError, err.message);
    } finally {
      setChildUploading(false);
      e.target.value = "";
    }
  };

  const handleDelete = async (row) => {
    if (!window.confirm("Are you sure you want to delete this record?")) return;
    try {
      await apiCall(`/ranlvl3/${row.id}`, {
        method: "DELETE",
      });
      setTransient(setSuccess, "Record deleted successfully");
      fetchRANLvl3(currentPage, searchTerm);
    } catch (err) {
      setTransient(setError, err.message);
    }
  };

  const handleChildDelete = async (parentId, childId) => {
    if (!window.confirm("Are you sure you want to delete this item?")) return;
    try {
      await apiCall(`/ranlvl3/${parentId}/items/${childId}`, {
        method: "DELETE",
      });
      setTransient(setSuccess, "Item deleted successfully");
      fetchRANLvl3(currentPage, searchTerm);
    } catch (err) {
      setTransient(setError, err.message);
    }
  };

  const toggleRowExpansion = (rowId) => {
    setExpandedRows(prev => {
      const newSet = new Set(prev);
      if (newSet.has(rowId)) {
        newSet.delete(rowId);
      } else {
        newSet.add(rowId);
      }
      return newSet;
    });
  };

  const openCreateModal = () => {
    if (!selectedProject) {
      setTransient(setError, 'Please select a project to create a new RAN Level 3 record.');
      return;
    }
    setCreateForm({
      project_id: selectedProject,
      item_name: '',
      key: '',
      service_type: '',
      uom: '',
      total_quantity: '',
      total_price: '',
      category: '',
      po_line: '',
      upl_line: '',
      ran_category: ''
    });
    setIsCreateModalOpen(true);
    setError('');
    setSuccess('');
  };

  const closeCreateModal = () => {
    setIsCreateModalOpen(false);
    setCreateForm({});
    setError("");
    setSuccess("");
  };

  const onCreateChange = (key, value) => {
    let convertedValue = value;
    if (key === 'total_quantity') {
      convertedValue = parseInt(value, 10);
      if (isNaN(convertedValue)) {
        convertedValue = '';
      }
    } else if (key === 'total_price') {
      convertedValue = parseFloat(value);
      if (isNaN(convertedValue)) {
        convertedValue = '';
      }
    }
    setCreateForm((prev) => ({ ...prev, [key]: convertedValue }));
  };

  const handleCreate = async (e) => {
    e.preventDefault();
    setCreating(true);
    setError("");
    setSuccess("");
    try {
      const createData = {
        ...createForm,
        service_type: createForm.service_type ? [createForm.service_type] : [],
        items: []
      };
      await apiCall('/ranlvl3/', {
        method: "POST",
        body: JSON.stringify(createData),
      });
      setTransient(setSuccess, "Record created successfully!");
      fetchRANLvl3(currentPage, searchTerm);
      setTimeout(() => closeCreateModal(), 1200);
    } catch (err) {
      setTransient(setError, err.message);
    } finally {
      setCreating(false);
    }
  };

  const openEditModal = (row) => {
    setEditingRow(row);
    const { id, items, ...formFields } = row;
    setEditForm({
      ...formFields,
      service_type: formFields.service_type?.[0] || ""
    });
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
    let convertedValue = value;
    if (key === 'total_quantity') {
      convertedValue = parseInt(value, 10);
      if (isNaN(convertedValue)) {
        convertedValue = '';
      }
    } else if (key === 'total_price') {
      convertedValue = parseFloat(value);
      if (isNaN(convertedValue)) {
        convertedValue = '';
      }
    }
    setEditForm((prev) => ({ ...prev, [key]: convertedValue }));
  };

  const handleUpdate = async () => {
    if (!editingRow) return;
    setUpdating(true);
    setError("");
    setSuccess("");
    try {
      const updateData = {
        ...editForm,
        service_type: editForm.service_type ? [editForm.service_type] : [],
        items: editingRow.items || []
      };
      await apiCall(`/ranlvl3/${editingRow.id}`, {
        method: "PUT",
        body: JSON.stringify(updateData),
      });
      setTransient(setSuccess, "Record updated successfully!");
      closeModal();
      fetchRANLvl3(currentPage, searchTerm);
    } catch (err) {
      setTransient(setError, err.message);
    } finally {
      setUpdating(false);
    }
  };

  const openChildEditModal = (parentId, item) => {
    setChildEditingRow({ ...item, parentId });
    const { id, ranlvl3_id, ...formFields } = item;
    setChildEditForm({
      ...formFields,
      service_type: formFields.service_type ? formFields.service_type.join(',') : ''
    });
    setIsChildModalOpen(true);
  };

  const closeChildModal = () => {
    setIsChildModalOpen(false);
    setChildEditingRow(null);
    setChildEditForm({});
  };

  const onChildEditChange = (key, value) => {
    let convertedValue = value;
    if (key === 'uom' || key === 'quantity') {
      convertedValue = parseInt(value, 10);
      if (isNaN(convertedValue)) {
        convertedValue = '';
      }
    } else if (key === 'price') {
      convertedValue = parseFloat(value);
      if (isNaN(convertedValue)) {
        convertedValue = '';
      }
    }
    setChildEditForm((prev) => ({ ...prev, [key]: convertedValue }));
  };

  const handleChildUpdate = async () => {
    if (!childEditingRow) return;
    setChildUpdating(true);
    setError("");
    setSuccess("");
    try {
      const updateData = {
        ...childEditForm,
        service_type: childEditForm.service_type ? childEditForm.service_type.split(',').map(s => s.trim()) : []
      };
      await apiCall(`/ranlvl3/${childEditingRow.parentId}/items/${childEditingRow.id}`, {
        method: "PUT",
        body: JSON.stringify(updateData),
      });
      setTransient(setSuccess, "Item updated successfully!");
      closeChildModal();
      fetchRANLvl3(currentPage, searchTerm);
    } catch (err) {
      setTransient(setError, err.message);
    } finally {
      setChildUpdating(false);
    }
  };

  const totalPages = Math.ceil(total / rowsPerPage);

  const handleRowsPerPageChange = (e) => {
    const newLimit = parseInt(e.target.value);
    setRowsPerPage(newLimit);
    setCurrentPage(1);
    fetchRANLvl3(1, searchTerm, newLimit);
  };

  // Count total child items
  const totalChildItems = rows.reduce((sum, row) => sum + (row.items?.length || 0), 0);

  // Define stat cards
  const statCards = [
    { label: 'Total Records', value: stats.total_records || total },
    { label: 'Total Items', value: stats.total_items || totalChildItems },
    { label: 'Current Page', value: `${currentPage} / ${totalPages || 1}` },
    { label: 'Showing', value: `${rows.length} records` },
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
        </select>
      )
    }
  ];

  // Help modal sections
  const helpSections = [
    {
      icon: '📋',
      title: 'Overview',
      content: (
        <HelpText>
          The RAN Level 3 Management component allows you to create, view, edit, and delete RAN Level 3 records
          and their associated items. Each Level 3 record can contain multiple child items that are managed
          separately. You can filter records by project and bulk upload items using CSV files.
        </HelpText>
      )
    },
    {
      icon: '✨',
      title: 'Features & Buttons',
      content: (
        <HelpList
          items={[
            { label: '+ Create RAN Level 3 Item', text: 'Opens a form to create a new Level 3 record. You must select a project first.' },
            { label: 'Search', text: 'Filter records by Project Name or Item Name in real-time.' },
            { label: 'Project Dropdown', text: 'Filter all Level 3 records and statistics by the selected project.' },
            { label: 'Clear Search', text: 'Resets the search filter and shows all records for the selected project.' },
            { label: '▶ Expand/Collapse', text: 'Click the arrow button to expand or collapse the child items table for that record.' },
            { label: '✏️ Edit (Parent)', text: 'Click to edit the Level 3 record details.' },
            { label: '🗑️ Delete (Parent)', text: 'Click to delete the Level 3 record and all its child items (requires confirmation).' },
            { label: '📤 Upload Items CSV', text: 'Within an expanded record, upload child items via CSV file.' },
            { label: '✏️ Edit (Child)', text: 'Within the items table, click to edit a specific child item.' },
            { label: '🗑️ Delete (Child)', text: 'Within the items table, click to delete a specific child item (requires confirmation).' },
            { label: 'Rows Per Page Dropdown', text: 'Change how many Level 3 records are displayed per page (25-200).' }
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
            { label: 'Total Records', text: 'Total count of RAN Level 3 records for the selected project (or all projects if none selected).' },
            { label: 'Total Items', text: 'Sum of all child items across all Level 3 records.' },
            { label: 'Current Page', text: 'Shows which page you\'re viewing out of total pages.' },
            { label: 'Showing', text: 'Number of Level 3 records currently displayed on this page.' },
            { label: 'Rows Per Page', text: 'Adjustable dropdown to control pagination size.' }
          ]}
        />
      )
    },
    {
      icon: '🔍',
      title: 'Expandable Records',
      content: (
        <HelpText>
          Each RAN Level 3 record can be expanded to reveal its child items. Click the ▶ arrow button on the left
          to toggle the expansion. When expanded, you'll see a nested table displaying all associated items with
          their details, including item name, vendor part number, service type, quantity, and price.
        </HelpText>
      )
    },
    {
      icon: '📁',
      title: 'CSV Upload Guidelines - Child Items',
      content: (
        <>
          <HelpText>
            To upload child items for a Level 3 record via CSV, expand the record first, then click "Upload Items CSV".
            Your file must contain the following headers (in any order):
          </HelpText>
          <CodeBlock
            items={[
              'item_name', 'item_details', 'vendor_part_number', 'service_type',
              'category', 'uom', 'upl_line', 'quantity', 'price'
            ]}
          />
          <HelpText isNote>
            <strong>Note:</strong> The "service_type" field can be comma-separated for multiple types.
            Numeric fields (quantity, price, uom) should contain valid numbers.
          </HelpText>
        </>
      )
    },
    {
      icon: '🏷️',
      title: 'Service Types',
      content: (
        <HelpList
          items={[
            { label: '1 - Software', text: 'Software-related items and services.' },
            { label: '2 - Hardware', text: 'Physical equipment and hardware components.' },
            { label: '3 - Service', text: 'Installation, maintenance, and professional services.' }
          ]}
        />
      )
    },
    {
      icon: '💡',
      title: 'Tips',
      content: (
        <HelpList
          items={[
            'Always select a project before creating Level 3 records.',
            'Use the search feature to quickly find records by Project Name or Item Name.',
            'Expand records to view and manage their child items.',
            'Statistics update automatically when you filter by project or search.',
            'The table scrolls horizontally - use the scrollbar at the bottom to see all columns.',
            'Child items are deleted automatically when you delete their parent record.',
            'Each Level 3 record can have unlimited child items.',
            'Use bulk CSV upload to quickly add multiple items to a record.'
          ]}
        />
      )
    }
  ];

  return (
    <div className="inventory-container">
      {/* Header Section */}
      <div className="inventory-header">
        <TitleWithInfo
          title="RAN Level 3 Management"
          subtitle="Manage RAN Level 3 records and their items"
          onInfoClick={() => setShowHelpModal(true)}
          infoTooltip="How to use this component"
        />
        <div className="header-actions">
          <button
            className={`btn-primary ${!selectedProject ? 'disabled' : ''}`}
            onClick={openCreateModal}
            disabled={!selectedProject}
            title={!selectedProject ? "Select a project first" : "Create a new Level 3 record"}
          >
            <span className="btn-icon">+</span>
            Create RAN Level 3 Item
          </button>
        </div>
      </div>

      {/* Filters Section */}
      <FilterBar
        searchTerm={searchTerm}
        onSearchChange={onSearchChange}
        searchPlaceholder="Search by Project Name or Item Name..."
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
        onClearSearch={() => { setSearchTerm(''); fetchRANLvl3(1, ''); }}
        clearButtonText="Clear Search"
      />

      {/* Messages */}
      {error && <div className="message error-message">{error}</div>}
      {success && <div className="message success-message">{success}</div>}
      {loading && <div className="loading-indicator">Loading RAN Level 3 Records...</div>}

      {/* Stats Bar - Carousel Style */}
      <StatsCarousel cards={statCards} visibleCount={4} />

      {/* Custom Expandable Table */}
      <div className="inventory-table-wrapper">
        <div style={{ overflowX: 'auto' }}>
          <table className="inventory-table">
            <thead>
              <tr>
                <th style={{ width: '40px', minWidth: '40px' }}></th>
                <th>Project ID</th>
                <th>Item Name</th>
                <th>Key</th>
                <th>Service Type</th>
                <th>UOM</th>
                <th>Total Qty</th>
                <th>Total Price</th>
                <th>Category</th>
                <th>RAN Category</th>
                <th>PO Line</th>
                <th>UPL Line</th>
                <th style={{ width: '120px' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {rows.length === 0 && !loading ? (
                <tr>
                  <td colSpan={13} style={{ textAlign: 'center', padding: '2rem', color: '#6b7280' }}>
                    No RAN Level 3 records found
                  </td>
                </tr>
              ) : (
                rows.map((row) => (
                  <React.Fragment key={row.id}>
                    <tr>
                      <td>
                        <button
                          onClick={() => toggleRowExpansion(row.id)}
                          className="btn-action btn-expand"
                          style={{
                            transform: expandedRows.has(row.id) ? 'rotate(90deg)' : 'rotate(0deg)',
                            transition: 'transform 0.2s',
                            fontSize: '14px',
                            padding: '4px 8px'
                          }}
                          title={expandedRows.has(row.id) ? "Collapse" : "Expand"}
                        >
                          ▶
                        </button>
                      </td>
                      <td>{row.project_id}</td>
                      <td><strong>{row.item_name}</strong></td>
                      <td>{row.key}</td>
                      <td>
                        {Array.isArray(row.service_type)
                          ? row.service_type.map(s => serviceTypes[s] || s).join(', ')
                          : serviceTypes[row.service_type] || row.service_type}
                      </td>
                      <td>{row.uom}</td>
                      <td>{row.total_quantity}</td>
                      <td>{row.total_price}</td>
                      <td>{row.category}</td>
                      <td>{row.ran_category}</td>
                      <td>{row.po_line}</td>
                      <td>{row.upl_line}</td>
                      <td className="actions-cell">
                        <button className="btn-action btn-edit" onClick={() => openEditModal(row)} title="Edit">
                          ✏️
                        </button>
                        <button className="btn-action btn-delete" onClick={() => handleDelete(row)} title="Delete">
                          🗑️
                        </button>
                      </td>
                    </tr>
                    {expandedRows.has(row.id) && (
                      <tr>
                        <td colSpan={13} style={{ padding: 0, background: '#f9fafb' }}>
                          <div style={{ padding: '1.5rem', borderLeft: '4px solid #124191' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                              <h4 style={{ margin: 0, color: '#124191', fontSize: '1rem', fontWeight: '600' }}>
                                Items for {row.item_name} ({row.items?.length || 0} items)
                              </h4>
                              <label className={`btn-secondary ${childUploading ? "disabled" : ""}`} style={{ fontSize: '0.85rem' }}>
                                <span className="btn-icon">📤</span>
                                Upload Items CSV
                                <input
                                  type="file"
                                  accept=".csv"
                                  style={{ display: "none" }}
                                  disabled={childUploading}
                                  onChange={(e) => handleChildUpload(e, row.id)}
                                />
                              </label>
                            </div>
                            <div style={{ overflowX: 'auto', background: 'white', borderRadius: '8px', border: '1px solid #e5e7eb' }}>
                              <table className="inventory-table" style={{ margin: 0 }}>
                                <thead>
                                  <tr style={{ background: '#f3f4f6' }}>
                                    <th>Item Name</th>
                                    <th>Details</th>
                                    <th>Vendor Part #</th>
                                    <th>Service Type</th>
                                    <th>Category</th>
                                    <th>UOM</th>
                                    <th>UPL Line</th>
                                    <th>Quantity</th>
                                    <th>Price</th>
                                    <th style={{ width: '100px' }}>Actions</th>
                                  </tr>
                                </thead>
                                <tbody>
                                  {row.items.length === 0 ? (
                                    <tr>
                                      <td colSpan={10} style={{ textAlign: 'center', padding: '1.5rem', color: '#9ca3af' }}>
                                        No items found. Upload a CSV to add items.
                                      </td>
                                    </tr>
                                  ) : (
                                    row.items.map((item) => (
                                      <tr key={item.id}>
                                        <td><strong>{item.item_name}</strong></td>
                                        <td>{item.item_details}</td>
                                        <td>{item.vendor_part_number}</td>
                                        <td>
                                          {Array.isArray(item.service_type)
                                            ? item.service_type.map(s => serviceTypes[s] || s).join(', ')
                                            : serviceTypes[item.service_type] || item.service_type}
                                        </td>
                                        <td>{item.category}</td>
                                        <td>{item.uom}</td>
                                        <td>{item.upl_line}</td>
                                        <td>{item.quantity}</td>
                                        <td>{item.price}</td>
                                        <td className="actions-cell">
                                          <button className="btn-action btn-edit" onClick={() => openChildEditModal(row.id, item)} title="Edit">
                                            ✏️
                                          </button>
                                          <button className="btn-action btn-delete" onClick={() => handleChildDelete(row.id, item.id)} title="Delete">
                                            🗑️
                                          </button>
                                        </td>
                                      </tr>
                                    ))
                                  )}
                                </tbody>
                              </table>
                            </div>
                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Pagination */}
      <Pagination
        currentPage={currentPage}
        totalPages={totalPages}
        onPageChange={(page) => fetchRANLvl3(page, searchTerm, rowsPerPage)}
        previousText="← Previous"
        nextText="Next →"
      />

      {/* Create Modal */}
      {isCreateModalOpen && (
        <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && setIsCreateModalOpen(false)}>
          <div className="modal-container">
            <div className="modal-header">
              <h2 className="modal-title">Create New RAN Level 3 Item</h2>
              <button className="modal-close" onClick={closeCreateModal} type="button">✕</button>
            </div>

            <form className="modal-form" onSubmit={handleCreate}>
              {error && <div className="message error-message">{error}</div>}
              {success && <div className="message success-message">{success}</div>}

              {/* Project Information */}
              <div className="form-section">
                <h3 className="section-title">Project Information</h3>
                <div className="form-grid">
                  <div className="form-field full-width">
                    <label>Project ID *</label>
                    <select
                      value={createForm.project_id}
                      onChange={e => onCreateChange('project_id', e.target.value)}
                      required
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

              {/* Item Information */}
              <div className="form-section">
                <h3 className="section-title">Item Information</h3>
                <div className="form-grid">
                  <div className="form-field">
                    <label>Item Name *</label>
                    <input
                      type="text"
                      value={createForm.item_name}
                      onChange={e => onCreateChange('item_name', e.target.value)}
                      required
                    />
                  </div>
                  <div className="form-field">
                    <label>Key</label>
                    <input
                      type="text"
                      value={createForm.key}
                      onChange={e => onCreateChange('key', e.target.value)}
                    />
                  </div>
                  <div className="form-field">
                    <label>Service Type</label>
                    <select
                      value={createForm.service_type}
                      onChange={e => onCreateChange('service_type', e.target.value)}
                    >
                      <option value="">Select a type</option>
                      {Object.entries(serviceTypes).map(([value, name]) => (
                        <option key={value} value={value}>
                          {name}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div className="form-field">
                    <label>UOM</label>
                    <input
                      type="text"
                      value={createForm.uom}
                      onChange={e => onCreateChange('uom', e.target.value)}
                    />
                  </div>
                  <div className="form-field">
                    <label>Total Quantity</label>
                    <input
                      type="number"
                      value={createForm.total_quantity}
                      onChange={e => onCreateChange('total_quantity', e.target.value)}
                    />
                  </div>
                  <div className="form-field">
                    <label>Total Price</label>
                    <input
                      type="number"
                      step="0.01"
                      value={createForm.total_price}
                      onChange={e => onCreateChange('total_price', e.target.value)}
                    />
                  </div>
                  <div className="form-field">
                    <label>Category</label>
                    <input
                      type="text"
                      value={createForm.category}
                      onChange={e => onCreateChange('category', e.target.value)}
                    />
                  </div>
                  <div className="form-field">
                    <label>RAN Category</label>
                    <input
                      type="text"
                      value={createForm.ran_category}
                      onChange={e => onCreateChange('ran_category', e.target.value)}
                    />
                  </div>
                  <div className="form-field">
                    <label>PO Line</label>
                    <input
                      type="text"
                      value={createForm.po_line}
                      onChange={e => onCreateChange('po_line', e.target.value)}
                    />
                  </div>
                  <div className="form-field">
                    <label>UPL Line</label>
                    <input
                      type="text"
                      value={createForm.upl_line}
                      onChange={e => onCreateChange('upl_line', e.target.value)}
                    />
                  </div>
                </div>
              </div>

              {/* Form Actions */}
              <div className="form-actions">
                <button type="button" className="btn-cancel" onClick={closeCreateModal}>
                  Cancel
                </button>
                <button type="submit" className="btn-submit" disabled={creating}>
                  {creating ? 'Creating...' : 'Create Level 3 Item'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Parent Edit Modal */}
      {isModalOpen && (
        <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && setIsModalOpen(false)}>
          <div className="modal-container">
            <div className="modal-header">
              <h2 className="modal-title">Edit Record: {editingRow?.item_name}</h2>
              <button className="modal-close" onClick={closeModal} type="button">✕</button>
            </div>

            <div className="modal-form">
              {error && <div className="message error-message">{error}</div>}
              {success && <div className="message success-message">{success}</div>}

              {/* Item Information */}
              <div className="form-section">
                <h3 className="section-title">Item Information</h3>
                <div className="form-grid">
                  <div className="form-field">
                    <label>Project ID</label>
                    <select
                      value={editForm.project_id}
                      onChange={e => onEditChange('project_id', e.target.value)}
                    >
                      <option value="">-- Select Project --</option>
                      {projects.map((p) => (
                        <option key={p.pid_po} value={p.pid_po}>
                          {p.project_name} ({p.pid_po})
                        </option>
                      ))}
                    </select>
                  </div>
                  <div className="form-field">
                    <label>Item Name</label>
                    <input
                      type="text"
                      value={editForm.item_name || ''}
                      onChange={e => onEditChange('item_name', e.target.value)}
                    />
                  </div>
                  <div className="form-field">
                    <label>Key</label>
                    <input
                      type="text"
                      value={editForm.key || ''}
                      onChange={e => onEditChange('key', e.target.value)}
                    />
                  </div>
                  <div className="form-field">
                    <label>Service Type</label>
                    <select
                      value={editForm.service_type || ''}
                      onChange={e => onEditChange('service_type', e.target.value)}
                    >
                      <option value="">Select a type</option>
                      {Object.entries(serviceTypes).map(([value, name]) => (
                        <option key={value} value={value}>
                          {name}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div className="form-field">
                    <label>UOM</label>
                    <input
                      type="text"
                      value={editForm.uom || ''}
                      onChange={e => onEditChange('uom', e.target.value)}
                    />
                  </div>
                  <div className="form-field">
                    <label>Total Quantity</label>
                    <input
                      type="number"
                      value={editForm.total_quantity !== null && editForm.total_quantity !== undefined ? editForm.total_quantity : ''}
                      onChange={e => onEditChange('total_quantity', e.target.value)}
                    />
                  </div>
                  <div className="form-field">
                    <label>Total Price</label>
                    <input
                      type="number"
                      step="0.01"
                      value={editForm.total_price !== null && editForm.total_price !== undefined ? editForm.total_price : ''}
                      onChange={e => onEditChange('total_price', e.target.value)}
                    />
                  </div>
                  <div className="form-field">
                    <label>Category</label>
                    <input
                      type="text"
                      value={editForm.category || ''}
                      onChange={e => onEditChange('category', e.target.value)}
                    />
                  </div>
                  <div className="form-field">
                    <label>RAN Category</label>
                    <input
                      type="text"
                      value={editForm.ran_category || ''}
                      onChange={e => onEditChange('ran_category', e.target.value)}
                    />
                  </div>
                  <div className="form-field">
                    <label>PO Line</label>
                    <input
                      type="text"
                      value={editForm.po_line || ''}
                      onChange={e => onEditChange('po_line', e.target.value)}
                    />
                  </div>
                  <div className="form-field">
                    <label>UPL Line</label>
                    <input
                      type="text"
                      value={editForm.upl_line || ''}
                      onChange={e => onEditChange('upl_line', e.target.value)}
                    />
                  </div>
                </div>
              </div>

              {/* Form Actions */}
              <div className="form-actions">
                <button type="button" className="btn-cancel" onClick={closeModal}>
                  Cancel
                </button>
                <button className="btn-submit" onClick={handleUpdate} disabled={updating}>
                  {updating ? 'Updating...' : 'Update Record'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Child Edit Modal */}
      {isChildModalOpen && (
        <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && setIsChildModalOpen(false)}>
          <div className="modal-container">
            <div className="modal-header">
              <h2 className="modal-title">Edit Item: {childEditingRow?.item_name}</h2>
              <button className="modal-close" onClick={closeChildModal} type="button">✕</button>
            </div>

            <div className="modal-form">
              {error && <div className="message error-message">{error}</div>}
              {success && <div className="message success-message">{success}</div>}

              {/* Item Details */}
              <div className="form-section">
                <h3 className="section-title">Item Details</h3>
                <div className="form-grid">
                  <div className="form-field full-width">
                    <label>Item Name</label>
                    <input
                      type="text"
                      value={childEditForm.item_name || ''}
                      onChange={e => onChildEditChange('item_name', e.target.value)}
                      disabled
                      className="disabled-input"
                    />
                  </div>
                  <div className="form-field full-width">
                    <label>Details</label>
                    <input
                      type="text"
                      value={childEditForm.item_details || ''}
                      onChange={e => onChildEditChange('item_details', e.target.value)}
                    />
                  </div>
                  <div className="form-field">
                    <label>Vendor Part Number</label>
                    <input
                      type="text"
                      value={childEditForm.vendor_part_number || ''}
                      onChange={e => onChildEditChange('vendor_part_number', e.target.value)}
                    />
                  </div>
                  <div className="form-field">
                    <label>Service Type (comma-separated)</label>
                    <input
                      type="text"
                      value={childEditForm.service_type || ''}
                      onChange={e => onChildEditChange('service_type', e.target.value)}
                      placeholder="e.g., 1,2"
                    />
                  </div>
                  <div className="form-field">
                    <label>Category</label>
                    <input
                      type="text"
                      value={childEditForm.category || ''}
                      onChange={e => onChildEditChange('category', e.target.value)}
                    />
                  </div>
                  <div className="form-field">
                    <label>UOM</label>
                    <input
                      type="number"
                      value={childEditForm.uom !== null && childEditForm.uom !== undefined ? childEditForm.uom : ''}
                      onChange={e => onChildEditChange('uom', e.target.value)}
                    />
                  </div>
                  <div className="form-field">
                    <label>UPL Line</label>
                    <input
                      type="text"
                      value={childEditForm.upl_line || ''}
                      onChange={e => onChildEditChange('upl_line', e.target.value)}
                    />
                  </div>
                  <div className="form-field">
                    <label>Quantity</label>
                    <input
                      type="number"
                      value={childEditForm.quantity !== null && childEditForm.quantity !== undefined ? childEditForm.quantity : ''}
                      onChange={e => onChildEditChange('quantity', e.target.value)}
                    />
                  </div>
                  <div className="form-field">
                    <label>Price</label>
                    <input
                      type="number"
                      step="0.01"
                      value={childEditForm.price !== null && childEditForm.price !== undefined ? childEditForm.price : ''}
                      onChange={e => onChildEditChange('price', e.target.value)}
                    />
                  </div>
                </div>
              </div>

              {/* Form Actions */}
              <div className="form-actions">
                <button type="button" className="btn-cancel" onClick={closeChildModal}>
                  Cancel
                </button>
                <button className="btn-submit" onClick={handleChildUpdate} disabled={childUpdating}>
                  {childUpdating ? 'Updating...' : 'Update Item'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Help/Info Modal */}
      <HelpModal
        show={showHelpModal}
        onClose={() => setShowHelpModal(false)}
        title="RAN Level 3 Management - User Guide"
        sections={helpSections}
        closeButtonText="Got it!"
      />
    </div>
  );
}
