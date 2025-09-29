import React, { useState, useEffect, useRef } from "react";
import { apiCall, setTransient } from "../api.js";
import "../css/Dismantling.css";

const ROWS_PER_PAGE = 50;

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
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [loading, setLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");

  // NEW: Project management states
  const [projects, setProjects] = useState([]);
  const [selectedProject, setSelectedProject] = useState('');

  // Parent modal states
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingRow, setEditingRow] = useState(null);
  const [editForm, setEditForm] = useState({});
  const [updating, setUpdating] = useState(false);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [createForm, setCreateForm] = useState({});
  const [creating, setCreating] = useState(false);

  // Child-related states
  const [expandedRows, setExpandedRows] = useState(new Set());
  const [childEditingRow, setChildEditingRow] = useState(null);
  const [isChildModalOpen, setIsChildModalOpen] = useState(false);
  const [childEditForm, setChildEditForm] = useState({});
  const [childUpdating, setChildUpdating] = useState(false);
  const [childUploading, setChildUploading] = useState(false);

  const fetchAbort = useRef(null);

  // NEW: Function to fetch user's accessible projects
  const fetchProjects = async () => {
    try {
      const data = await apiCall('/ran-projects');
      setProjects(data || []);
      // Optionally, auto-select the first project
      if (data && data.length > 0) {
        setSelectedProject(data[0].pid_po);
      }
    } catch (err) {
      setTransient(setError, 'Failed to load projects. Please ensure you have project access.');
      console.error(err);
    }
  };

  const fetchRANLvl3 = async (page = 1, search = "") => {
    try {
      if (fetchAbort.current) fetchAbort.current.abort();
      const controller = new AbortController();
      fetchAbort.current = controller;

      setLoading(true);
      setError("");
      const skip = (page - 1) * ROWS_PER_PAGE;
      const params = new URLSearchParams();
      params.set("skip", String(skip));
      params.set("limit", String(ROWS_PER_PAGE));
      if (search.trim()) params.set("search", search.trim());

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
          upl_line:r.upl_line,
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
    fetchProjects(); // Fetch projects on component mount
    fetchRANLvl3(1, "");
  }, []);

  const onSearchChange = (e) => {
    const v = e.target.value;
    setSearchTerm(v);
    fetchRANLvl3(1, v);
  };

  // MODIFIED: Handle child upload with project validation
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

  const handleDelete = async (id) => {
    if (!window.confirm("Are you sure you want to delete this record?")) return;
    try {
      await apiCall(`/ranlvl3/${id}`, {
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

  // MODIFIED: Create modal functions with project validation
  const openCreateModal = () => {
    if (!selectedProject) {
      setError('Please select a project to create a new RAN Level 3 record.');
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
      upl_line:''
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
    if (key === 'total_quantity' ) {
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

  const handleCreate = async () => {
    setCreating(true);
    setError("");
    setSuccess("");
    try {
      // The service_type must be an array of strings for the API
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
      closeCreateModal();
      fetchRANLvl3(1, searchTerm);
    } catch (err) {
      setTransient(setError, err.message);
    } finally {
      setCreating(false);
    }
  };

  // Parent modal functions
  const openEditModal = (row) => {
    setEditingRow(row);
    const { id, items, ...formFields } = row;
    setEditForm({
      ...formFields,
      // We only expect one service type, so get the first item
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
    if (key === 'total_quantity' ) {
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
        // The service_type must be an array of strings for the API
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

  // Child modal functions
  const openChildEditModal = (parentId, item) => {
    setChildEditingRow({ ...item, parentId });
    const { id, ranlvl3_id, ...formFields } = item;
    setChildEditForm({
      ...formFields,
      // We only expect one service type, so get the first item
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

  const totalPages = Math.ceil(total / ROWS_PER_PAGE);

  return (
    <div className="dismantling-container">
      {/* Header & Create Button */}
      <div className="dismantling-header-row">
        <h2>RAN Level 3 Records</h2>
        <button
          className="upload-btn"
          onClick={openCreateModal}
          disabled={!selectedProject}
          title={!selectedProject ? "Select a project first" : "Create a new RAN Level 3 record"}
        >
          + Create RAN Level 3 Item
        </button>
      </div>

      {/* Search & Project Selection */}
      <div className="dismantling-search-container">
        <input
          type="text"
          placeholder="Filter by Project Name or Item Name..."
          value={searchTerm}
          onChange={onSearchChange}
          className="search-input"
        />
        {searchTerm && (
          <button
            onClick={() => {
              setSearchTerm("");
              fetchRANLvl3(1, "");
            }}
            className="clear-btn"
          >
            Clear
          </button>
        )}
        
        <select
          id="project-select"
          className="search-input"
          value={selectedProject}
          onChange={(e) => setSelectedProject(e.target.value)}
        >
          <option value="">-- Select a Project --</option>
          {projects.map((p) => (
            <option key={p.pid_po} value={p.pid_po}>
              {p.project_name} ({p.pid_po})
            </option>
          ))}
        </select>
      </div>

      {/* Messages */}
      {error && <div className="dismantling-message error">{error}</div>}
      {success && <div className="dismantling-message success">{success}</div>}
      {loading && <div className="loading-message">Loading RAN Level 3 Records...</div>}

      {/* Table */}
      <div className="dismantling-table-container">
        <table className="dismantling-table">
          <thead>
            <tr>
              <th style={{ width: '30px' }}></th>
              <th>Project ID</th>
              <th>Item Name</th>
              <th>Key</th>
              <th>Service Type</th>
              <th>UOM</th>
              <th>Total Quantity</th>
              <th>Total Price</th>
              <th>Category</th>
              <th>PO Line</th>
              <th>UPL Line</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 && !loading ? (
              <tr>
                <td colSpan={11} className="no-results">
                  No results
                </td>
              </tr>
            ) : (
              rows.map((row) => (
                <React.Fragment key={row.id}>
                  <tr>
                    <td>
                      <button
                        onClick={() => toggleRowExpansion(row.id)}
                        className="clear-btn"
                        style={{
                          padding: '4px 8px',
                          fontSize: '12px',
                          transform: expandedRows.has(row.id) ? 'rotate(90deg)' : 'rotate(0deg)',
                          transition: 'transform 0.2s'
                        }}
                      >
                        ▶
                      </button>
                    </td>
                    <td>{row.project_id}</td>
                    <td>{row.item_name}</td>
                    <td>{row.key}</td>
                    {/* Display the service type name from the mapping */}
                    <td>{Array.isArray(row.service_type) ? row.service_type.map(s => serviceTypes[s] || s).join(', ') : serviceTypes[row.service_type] || row.service_type}</td>
                    <td>{row.uom}</td>
                    <td>{row.total_quantity}</td>
                    <td>{row.total_price}</td>
                    <td>{row.category}</td>
                    <td>{row.po_line}</td>
                    <td>{row.upl_line}</td>
                    <td className="actions-cell">
                      <button className="clear-btn" onClick={() => openEditModal(row)}>
                        Edit
                      </button>
                      <button className="clear-btn" onClick={() => handleDelete(row.id)}>
                        Delete
                      </button>
                    </td>
                  </tr>
                  {expandedRows.has(row.id) && (
                    <tr>
                      <td colSpan={11} style={{ padding: 0, background: '#f8fafb' }}>
                        <div style={{ padding: '1rem', borderLeft: '4px solid var(--primary-color)' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                            <h4 style={{ margin: 0, color: 'var(--primary-color)' }}>Items for {row.item_name}</h4>
                            <label className={`upload-btn ${childUploading ? "disabled" : ""}`} style={{ fontSize: '0.8rem', padding: '0.5rem 1rem' }}>
                              📤 Upload Items CSV
                              <input
                                type="file"
                                accept=".csv"
                                style={{ display: "none" }}
                                disabled={childUploading}
                                onChange={(e) => handleChildUpload(e, row.id)}
                              />
                            </label>
                          </div>
                          <div style={{ overflowX: 'auto' }}>
                            <table className="dismantling-table" style={{ margin: 0 }}>
                              <thead>
                                <tr>
                                  <th>Item Name</th>
                                  <th>Details</th>
                                  <th>Vendor Part #</th>
                                  <th>Service Type</th>
                                  <th>Category</th>
                                  <th>UOM</th>
                                  <th>UPL Line</th>
                                  <th>Quantity</th>
                                  <th>Price</th>
                                  <th>Actions</th>
                                </tr>
                              </thead>
                              <tbody>
                                {row.items.length === 0 ? (
                                  <tr>
                                    <td colSpan={9} className="no-results">
                                      No items found
                                    </td>
                                  </tr>
                                ) : (
                                  row.items.map((item) => (
                                    <tr key={item.id}>
                                      <td>{item.item_name}</td>
                                      <td>{item.item_details}</td>
                                      <td>{item.vendor_part_number}</td>
                                      <td>{Array.isArray(item.service_type) ? item.service_type.map(s => serviceTypes[s] || s).join(', ') : serviceTypes[item.service_type] || item.service_type}</td>
                                      <td>{item.category}</td>
                                      <td>{item.uom}</td>
                                      <td>{item.upl_line}</td>
                                      <td>{item.quantity}</td>
                                      <td>{item.price}</td>
                                      <td className="actions-cell">
                                        <button className="clear-btn" onClick={() => openChildEditModal(row.id, item)}>
                                          Edit
                                        </button>
                                        <button className="clear-btn" onClick={() => handleChildDelete(row.id, item.id)}>
                                          Delete
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

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="dismantling-pagination">
          <button
            className="pagination-btn"
            disabled={currentPage === 1}
            onClick={() => fetchRANLvl3(currentPage - 1, searchTerm)}
          >
            Prev
          </button>
          <span className="pagination-info">
            Page {currentPage} of {totalPages}
          </span>
          <button
            className="pagination-btn"
            disabled={currentPage === totalPages}
            onClick={() => fetchRANLvl3(currentPage + 1, searchTerm)}
          >
            Next
          </button>
        </div>
      )}

      {/* Create Modal */}
      {isCreateModalOpen && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12 }}>
              <h3>Create New RAN Level 3 Item</h3>
              <button onClick={closeCreateModal} className="close-btn">✖</button>
            </div>
            
            {error && <div className="dismantling-message error">{error}</div>}
            {success && <div className="dismantling-message success">{success}</div>}
            
            <table className="dismantling-table" style={{ width: '100%', borderSpacing: 0, borderCollapse: 'collapse' }}>
              <tbody>
                {Object.keys(createForm).map((key) => (
                  <tr key={key}>
                    <td style={{ fontWeight: 'bold' }}>
                      {key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
                    </td>
                    <td>
                      {key === 'project_id' ? (
                        <select
                          value={createForm[key]}
                          onChange={e => onCreateChange(key, e.target.value)}
                          style={{ width: '100%', padding: '8px', boxSizing: 'border-box' }}
                        >
                          <option value="">-- Select Project --</option>
                          {projects.map((p) => (
                            <option key={p.pid_po} value={p.pid_po}>
                              {p.project_name} ({p.pid_po})
                            </option>
                          ))}
                        </select>
                      ) : key === 'service_type' ? (
                        <select
                          value={createForm[key]}
                          onChange={e => onCreateChange(key, e.target.value)}
                          style={{ width: '100%', padding: '8px', boxSizing: 'border-box' }}
                        >
                          <option value="">Select a type</option>
                          {Object.entries(serviceTypes).map(([value, name]) => (
                            <option key={value} value={value}>
                              {name}
                            </option>
                          ))}
                        </select>
                      ) : (
                        <input
                          type={['total_quantity'].includes(key) ? 'number' : ['total_price'].includes(key) ? 'number' : 'text'}
                          step={key === 'total_price' ? '0.01' : undefined}
                          value={createForm[key] !== null && createForm[key] !== undefined ? createForm[key] : ''}
                          onChange={e => onCreateChange(key, e.target.value)}
                          style={{ width: '100%', padding: '8px', boxSizing: 'border-box' }}
                          disabled={key === 'project_id'}
                        />
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <button
              onClick={handleCreate}
              disabled={creating}
              className="pagination-btn"
              style={{ marginTop: 12, width: '100%' }}
            >
              {creating ? 'Creating...' : 'Create'}
            </button>
          </div>
        </div>
      )}

      {/* Parent Edit Modal */}
      {isModalOpen && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12 }}>
              <h3>Edit Record: {editingRow?.project_id}</h3>
              <button onClick={closeModal} className="close-btn">✖</button>
            </div>
            <table className="dismantling-table" style={{ width: '100%', borderSpacing: 0, borderCollapse: 'collapse' }}>
              <tbody>
                {Object.keys(editForm).map((key) => (
                  <tr key={key}>
                    <td style={{ fontWeight: 'bold' }}>
                      {key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
                    </td>
                    <td>
                      {key === 'project_id' ? (
                        <select
                          value={editForm[key]}
                          onChange={e => onEditChange(key, e.target.value)}
                          style={{ width: '100%', padding: '8px', boxSizing: 'border-box' }}
                        >
                          <option value="">-- Select Project --</option>
                          {projects.map((p) => (
                            <option key={p.pid_po} value={p.pid_po}>
                              {p.project_name} ({p.pid_po})
                            </option>
                          ))}
                        </select>
                      ) : key === 'service_type' ? (
                        <select
                          value={editForm[key]}
                          onChange={e => onEditChange(key, e.target.value)}
                          style={{ width: '100%', padding: '8px', boxSizing: 'border-box' }}
                        >
                          <option value="">Select a type</option>
                          {Object.entries(serviceTypes).map(([value, name]) => (
                            <option key={value} value={value}>
                              {name}
                            </option>
                          ))}
                        </select>
                      ) : (
                        <input
                          type={['total_quantity'].includes(key) ? 'number' : ['total_price'].includes(key) ? 'number' : 'text'}
                          step={key === 'total_price' ? '0.01' : undefined}
                          value={editForm[key] !== null && editForm[key] !== undefined ? editForm[key] : ''}
                          onChange={e => onEditChange(key, e.target.value)}
                          style={{ width: '100%', padding: '8px', boxSizing: 'border-box' }}
                        />
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <button
              onClick={handleUpdate}
              disabled={updating}
              className="pagination-btn"
              style={{ marginTop: 12, width: '100%' }}
            >
              {updating ? 'Updating...' : 'Update'}
            </button>
          </div>
        </div>
      )}

      {/* Child Edit Modal */}
      {isChildModalOpen && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12 }}>
              <h3>Edit Item: {childEditingRow?.item_name}</h3>
              <button onClick={closeChildModal} className="close-btn">✖</button>
            </div>
            <table className="dismantling-table" style={{ width: '100%', borderSpacing: 0, borderCollapse: 'collapse' }}>
              <tbody>
                {Object.keys(childEditForm).map((key) => (
                  <tr key={key}>
                    <td style={{ fontWeight: 'bold' }}>
                      {key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
                    </td>
                    <td>
                      <input
                        type={['uom', 'quantity'].includes(key) ? 'number' : ['price'].includes(key) ? 'number' : 'text'}
                        step={key === 'price' ? '0.01' : undefined}
                        value={childEditForm[key] !== null && childEditForm[key] !== undefined ? childEditForm[key] : ''}
                        onChange={e => onChildEditChange(key, e.target.value)}
                        style={{ width: '100%', padding: '8px', boxSizing: 'border-box' }}
                        disabled={key==='item_name'}
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <button
              onClick={handleChildUpdate}
              disabled={childUpdating}
              className="pagination-btn"
              style={{ marginTop: 12, width: '100%' }}
            >
              {childUpdating ? 'Updating...' : 'Update'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}