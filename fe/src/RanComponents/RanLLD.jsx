import React, { useState, useEffect, useRef } from "react";
import "../css/Dismantling.css";

const getAuthHeaders = () => {
  const token = localStorage.getItem('token');
  if (token) {
    return {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    };
  }
  return { 'Content-Type': 'application/json' };
};

const getAuthHeadersForFormData = () => {
  const token = localStorage.getItem('token');
  const headers = {};
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
};

const ROWS_PER_PAGE = 50;
const VITE_API_URL = import.meta.env.VITE_API_URL;

// Helper functions to parse and stringify CSV data
const parseCSV = (csvString) => {
  if (!csvString) return [];
  const lines = csvString.split('\n');
  return lines.map(line => {
    const regex = /(".*?"|[^",]+)(?=\s*,|\s*$)/g;
    const matches = line.match(regex) || [];
    return matches.map(field => field.replace(/"/g, ''));
  });
};

const stringifyCSV = (data) => {
  return data.map(row =>
    row.map(field => {
      const fieldStr = String(field || '');
      if (fieldStr.includes(',') || fieldStr.includes('"')) {
        return `"${fieldStr.replace(/"/g, '""')}"`;
      }
      return fieldStr;
    }).join(',')
  ).join('\n');
};

export default function RANLLD() {
  const [rows, setRows] = useState([]);
  const [currentPage, setCurrentPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [uploading, setUploading] = useState(false);
  const [loading, setLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");

  // NEW: Project management states
  const [projects, setProjects] = useState([]);
  const [selectedProject, setSelectedProject] = useState('');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [createForm, setCreateForm] = useState({
    site_id: '',
    new_antennas: '',
    total_antennas: '',
    technical_boq: '',
    key: '',
    pid_po: ''
  });
  const [creating, setCreating] = useState(false);

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingRow, setEditingRow] = useState(null);
  const [editForm, setEditForm] = useState({});
  const [updating, setUpdating] = useState(false);
 
  // New state to track which row's BoQ is being generated
  const [generatingBoqId, setGeneratingBoqId] = useState(null);
  // State for the new editable CSV modal
  const [showCsvModal, setShowCsvModal] = useState(false);
  const [editableCsvData, setEditableCsvData] = useState([]);
  const [currentSiteId, setCurrentSiteId] = useState('');

  const fetchAbort = useRef(null);

  // NEW: Function to fetch user's accessible projects
  const fetchProjects = async () => {
    try {
      const res = await fetch(`${VITE_API_URL}/ran-projects`, { 
        headers: getAuthHeaders() 
      });
      if (!res.ok) throw new Error('Could not fetch projects');
      const data = await res.json();
      setProjects(data || []);
      // Optionally, auto-select the first project
      if (data && data.length > 0) {
        setSelectedProject(data[0].pid_po);
      }
    } catch (err) {
      setError('Failed to load projects. Please ensure you have project access.');
      console.error(err);
    }
  };

  const fetchSites = async (page = 1, search = "") => {
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

      const res = await fetch(`${VITE_API_URL}/ran-sites?${params.toString()}`, {
        headers: getAuthHeaders(),
        signal: controller.signal,
      });

      if (!res.ok) {
        let errorMessage = 'Failed to fetch RAN Sites';
        try {
          const errorData = await res.json();
          errorMessage = errorData.detail || errorData.message || errorMessage;
        } catch (e) {
          errorMessage = `HTTP ${res.status}: ${res.statusText}`;
        }
        throw new Error(errorMessage);
      }

      const { records, total } = await res.json();

      setRows(
        (records || []).map((r) => ({
          id: r.id,
          site_id: r.site_id,
          new_antennas: r.new_antennas,
          total_antennas: r.total_antennas,
          technical_boq: r.technical_boq,
          key: r.key,
          pid_po: r.pid_po,
        }))
      );
      setTotal(total || 0);
      setCurrentPage(page);
    } catch (err) {
      if (err.name !== "AbortError") setError(err.message || "Failed to fetch sites");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProjects(); // Fetch projects on component mount
    fetchSites(1, "");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // UPDATED FUNCTION to handle BoQ generation and open modal instead of direct download
  const handleGenerateBoq = async (row) => {
    setGeneratingBoqId(row.id);
    setError("");
    setSuccess("");
    try {
      const res = await fetch(`${VITE_API_URL}/ran-sites/${row.id}/generate-boq`, {
        headers: getAuthHeaders(),
      });

      if (!res.ok) {
        let errorMessage = 'Failed to generate BoQ';
        try {
          const errorData = await res.json();
          errorMessage = errorData.detail || errorData.message || errorMessage;
        } catch (e) {
          errorMessage = `HTTP ${res.status}: ${res.statusText}`;
        }
        throw new Error(errorMessage);
      }
     
      // Get the CSV data as text instead of blob
      const csvContent = await res.text();
      
      // Parse the CSV and open the modal
      setEditableCsvData(parseCSV(csvContent));
      setCurrentSiteId(row.site_id);
      setShowCsvModal(true);

      setSuccess(`BoQ for site ${row.site_id} generated successfully.`);

    } catch (err) {
      setError(err.message);
    } finally {
      setGeneratingBoqId(null); // Reset loading state for the row
    }
  };

  // Handlers for editing the 2D array data
  const handleCellChange = (rowIndex, cellIndex, value) => {
    const updatedData = editableCsvData.map((row, rIdx) =>
      rIdx === rowIndex ? row.map((cell, cIdx) => (cIdx === cellIndex ? value : cell)) : row
    );
    setEditableCsvData(updatedData);
  };

  const handleAddRow = () => {
    const numColumns = editableCsvData[0]?.length || 1;
    const newRow = Array(numColumns).fill('----------------');
    // Add new row after the header
    const updatedData = [editableCsvData[0], ...editableCsvData.slice(1), newRow];
    setEditableCsvData(updatedData);
  };

  const handleDeleteRow = (rowIndexToDelete) => {
    // Prevent deleting the header row
    if (rowIndexToDelete === 0) return;
    setEditableCsvData(editableCsvData.filter((_, index) => index !== rowIndexToDelete));
  };

  const downloadCSV = () => {
    if (!editableCsvData.length) return;
    const csvContent = stringifyCSV(editableCsvData);
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `boq_${currentSiteId || 'export'}_edited.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const onSearchChange = (e) => {
    const v = e.target.value;
    setSearchTerm(v);
    fetchSites(1, v);
  };

  // MODIFIED: Handle Upload with project selection
  const handleUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    // Check if a project is selected
    if (!selectedProject) {
      setError("Please select a project before uploading.");
      e.target.value = '';
      return;
    }

    setUploading(true);
    setError("");
    setSuccess("");
    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch(`${VITE_API_URL}/ran-sites/upload-csv`, {
        method: "POST",
        headers: getAuthHeadersForFormData(),
        body: formData,
      });
      if (!res.ok) {
        let errorMessage = 'Failed to upload RAN Sites CSV';
        try {
          const errorData = await res.json();
          errorMessage = errorData.detail || errorData.message || errorMessage;
        } catch (err) {
          errorMessage = `HTTP ${res.status}: ${res.statusText}`;
        }
        throw new Error(errorMessage);
      }
      const result = await res.json();
      setSuccess(`Upload successful! ${result.inserted || "?"} rows inserted.`);
      fetchSites(1, searchTerm);
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm("Are you sure you want to delete this site?")) return;
    try {
      const res = await fetch(`${VITE_API_URL}/ran-sites/${id}`, {
        headers: getAuthHeaders(),
        method: "DELETE",
      });
      if (!res.ok) {
        let errorMessage = 'Failed to delete site';
        try {
          const errorData = await res.json();
          errorMessage = errorData.detail || errorData.message || errorMessage;
        } catch (err) {
          errorMessage = `HTTP ${res.status}: ${res.statusText}`;
        }
        throw new Error(errorMessage);
      }
      setSuccess("Site deleted successfully");
      fetchSites(currentPage, searchTerm);
    } catch (err) {
      setError(err.message);
    }
  };

  // NEW: Functions for creating records
  const openCreateModal = () => {
    if (!selectedProject) {
      setError('Please select a project to create a new RAN Site record.');
      return;
    }
    setCreateForm({
      site_id: '',
      new_antennas: '',
      total_antennas: '',
      technical_boq: '',
      key: '',
      pid_po: selectedProject
    });
    setShowCreateModal(true);
    setError('');
    setSuccess('');
  };

  const closeCreateModal = () => {
    setShowCreateModal(false);
    setCreateForm({
      site_id: '',
      new_antennas: '',
      total_antennas: '',
      technical_boq: '',
      key: '',
      pid_po: ''
    });
    setError('');
    setSuccess('');
  };

  const onCreateChange = (key, value) => {
    let convertedValue = value;
    if (key === 'total_antennas') {
      convertedValue = parseInt(value, 10);
      if (isNaN(convertedValue)) {
        convertedValue = '';
      }
    }
    setCreateForm((prev) => ({ ...prev, [key]: convertedValue }));
  };

  const handleCreate = async (e) => {
    e.preventDefault();
    setCreating(true);
    setError('');
    setSuccess('');
    try {
      const res = await fetch(`${VITE_API_URL}/ran-sites/`, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify(createForm),
      });
      if (!res.ok) {
        let errorMessage = 'Failed to create site';
        try {
          const errorData = await res.json();
          errorMessage = errorData.detail || errorData.message || errorMessage;
        } catch (err) {
          errorMessage = `HTTP ${res.status}: ${res.statusText}`;
        }
        throw new Error(errorMessage);
      }
      setSuccess('Site created successfully!');
      fetchSites(currentPage, searchTerm);
      setTimeout(() => closeCreateModal(), 1200);
    } catch (err) {
      setError(err.message);
    } finally {
      setCreating(false);
    }
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
    let convertedValue = value;
    if (key === 'total_antennas') {
      convertedValue = parseInt(value, 10);
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
      const res = await fetch(`${VITE_API_URL}/ran-sites/${editingRow.id}`, {
        method: "PUT",
        headers: getAuthHeaders(),
        body: JSON.stringify(editForm),
      });
      if (!res.ok) {
        let errorMessage = 'Failed to update site';
        try {
          const errorData = await res.json();
          errorMessage = errorData.detail || errorData.message || errorMessage;
        } catch (err) {
          errorMessage = `HTTP ${res.status}: ${res.statusText}`;
        }
        throw new Error(errorMessage);
      }
      setSuccess("Site updated successfully!");
      closeModal();
      fetchSites(currentPage, searchTerm);
    } catch (err) {
      setError(err.message);
    } finally {
      setUpdating(false);
    }
  };

  const totalPages = Math.ceil(total / ROWS_PER_PAGE);
  const csvHeaders = editableCsvData[0] || [];
  const csvBody = editableCsvData.slice(1);

  return (
    <div className="dismantling-container">
      {/* Header & Upload */}
      <div className="dismantling-header-row">
        <h2>RAN Sites</h2>
        <div style={{ display: 'flex', gap: 16 }}>
          <button 
            className="upload-btn" 
            onClick={openCreateModal}
            disabled={!selectedProject}
            title={!selectedProject ? "Select a project first" : "Create a new RAN Site record"}
          >
            + New Site
          </button>
          <label className={`upload-btn ${uploading || !selectedProject ? "disabled" : ""}`}
            title={!selectedProject ? "Select a project first" : "Upload RAN Sites CSV"}
          >
            📤 Upload RAN Sites CSV
            <input
              type="file"
              accept=".csv"
              style={{ display: "none" }}
              disabled={uploading || !selectedProject}
              onChange={handleUpload}
            />
          </label>
        </div>
      </div>

      {/* Search & Project Selection */}
      <div className="dismantling-search-container">
        <input
          type="text"
          placeholder="Filter by Site ID or BoQ..."
          value={searchTerm}
          onChange={onSearchChange}
          className="search-input"
        />
        {searchTerm && (
          <button
            onClick={() => {
              setSearchTerm("");
              fetchSites(1, "");
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
      {loading && <div className="loading-message">Loading RAN Sites...</div>}
     
      {/* Table */}
      <div className="dismantling-table-container">
        <table className="dismantling-table">
          <thead>
            <tr>
              <th>BoQ</th>
              <th>Site ID</th>
              <th>New Antennas</th>
              <th>Total Antennas</th>
              <th>Technical BoQ</th>
              <th>Technical BoQ Key</th>
              <th>Project</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 && !loading ? (
              <tr>
                <td colSpan={8} className="no-results">
                  No results
                </td>
              </tr>
            ) : (
              rows.map((row) => (
                <tr key={row.id}>
                  <td>
                    <button
                      onClick={() => handleGenerateBoq(row)}
                      className="clear-btn"
                      disabled={generatingBoqId === row.id || !row.key}
                      title={!row.key ? "No key available for BoQ" : "Generate and Edit BoQ"}
                      style={{ padding: '4px 8px', fontSize: '16px' }}
                    >
                      {generatingBoqId === row.id ? '⚙️' : '📥'}
                    </button>
                  </td>
                  <td>{row.site_id}</td>
                  <td>{row.new_antennas}</td>
                  <td>{row.total_antennas}</td>
                  <td>{row.technical_boq}</td>
                  <td>{row.key}</td>
                  <td>{row.pid_po}</td>
                  <td className="actions-cell">
                    <button className="clear-btn" onClick={() => openEditModal(row)}>
                      Edit
                    </button>
                    <button className="clear-btn" onClick={() => handleDelete(row.id)}>
                      Delete
                    </button>
                  </td>
                </tr>
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
            onClick={() => fetchSites(currentPage - 1, searchTerm)}
          >
            Prev
          </button>
          <span className="pagination-info">
            Page {currentPage} of {totalPages}
          </span>
          <button
            className="pagination-btn"
            disabled={currentPage === totalPages}
            onClick={() => fetchSites(currentPage + 1, searchTerm)}
          >
            Next
          </button>
        </div>
      )}

      {/* Create Modal */}
      {showCreateModal && (
        <div className="modal-overlay">
          <div className="modal-content">
            <form onSubmit={handleCreate}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12 }}>
                <h3>Create New Site</h3>
                <button type="button" onClick={closeCreateModal} className="close-btn">✖</button>
              </div>
              
              {error && <div className="dismantling-message error">{error}</div>}
              {success && <div className="dismantling-message success">{success}</div>}
              
              <table className="dismantling-table" style={{ width: '100%', borderSpacing: 0, borderCollapse: 'collapse' }}>
                <tbody>
                  <tr>
                    <td style={{ fontWeight: 'bold' }}>Site ID</td>
                    <td>
                      <input 
                        type="text" 
                        value={createForm.site_id} 
                        onChange={e => onCreateChange('site_id', e.target.value)} 
                        style={{ width: '100%', padding: '8px', boxSizing: 'border-box' }} 
                        required
                      />
                    </td>
                  </tr>
                  <tr>
                    <td style={{ fontWeight: 'bold' }}>New Antennas</td>
                    <td>
                      <input 
                        type="text" 
                        value={createForm.new_antennas} 
                        onChange={e => onCreateChange('new_antennas', e.target.value)} 
                        style={{ width: '100%', padding: '8px', boxSizing: 'border-box' }} 
                      />
                    </td>
                  </tr>
                  <tr>
                    <td style={{ fontWeight: 'bold' }}>Total Antennas</td>
                    <td>
                      <input 
                        type="number" 
                        value={createForm.total_antennas} 
                        onChange={e => onCreateChange('total_antennas', e.target.value)} 
                        style={{ width: '100%', padding: '8px', boxSizing: 'border-box' }} 
                      />
                    </td>
                  </tr>
                  <tr>
                    <td style={{ fontWeight: 'bold' }}>Technical BoQ</td>
                    <td>
                      <input 
                        type="text" 
                        value={createForm.technical_boq} 
                        onChange={e => onCreateChange('technical_boq', e.target.value)} 
                        style={{ width: '100%', padding: '8px', boxSizing: 'border-box' }} 
                      />
                    </td>
                  </tr>
                  <tr>
                    <td style={{ fontWeight: 'bold' }}>Technical BoQ Key</td>
                    <td>
                      <input 
                        type="text" 
                        value={createForm.key} 
                        onChange={e => onCreateChange('key', e.target.value)} 
                        style={{ width: '100%', padding: '8px', boxSizing: 'border-box' }} 
                      />
                    </td>
                  </tr>
                </tbody>
              </table>
              <button
                type="submit"
                disabled={creating}
                className="pagination-btn"
                style={{ marginTop: 12, width: '100%' }}
              >
                {creating ? 'Creating...' : 'Create Site'}
              </button>
            </form>
          </div>
        </div>
      )}

      {/* Edit Modal */}
      {isModalOpen && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12 }}>
              <h3>Edit Site: {editingRow?.site_id}</h3>
              <button onClick={closeModal} className="close-btn">✖</button>
            </div>
            <table className="dismantling-table" style={{ width: '100%', borderSpacing: 0, borderCollapse: 'collapse' }}>
              <tbody>
                {Object.keys(editForm).map((key) => (
                  <tr key={key}>
                    <td style={{ fontWeight: 'bold' }}>
                      {key === 'pid_po' ? 'Project' : key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
                    </td>
                    <td>
                      {key === 'pid_po' ? (
                        <select 
                          value={editForm[key] || ''} 
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
                      ) : (
                        <input
                          type={key === 'total_antennas' ? 'number' : 'text'}
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

      {/* Editable CSV Modal */}
      {showCsvModal && (
        <div className="modal-overlay" style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.5)', display: 'flex', justifyContent: 'center', alignItems: 'center', zIndex: 1000 }}>
          <div style={{ background: '#fff', padding: 24, borderRadius: 8, width: '95%', height: '90%', display: 'flex', flexDirection: 'column' }}>
           
            {/* Modal Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16, flexShrink: 0 }}>
              <h3 style={{ margin: 0 }}>Edit BoQ Data for {currentSiteId}</h3>
              <button onClick={() => setShowCsvModal(false)} style={{ fontSize: 18, cursor: 'pointer', background: 'none', border: 'none', padding: '4px 8px' }}>
                ✖
              </button>
            </div>

            {/* Action Buttons */}
            <div style={{ display: 'flex', gap: 12, marginBottom: 16, flexShrink: 0 }}>
              <button onClick={handleAddRow} style={{ padding: '8px 16px', borderRadius: 6, cursor: 'pointer', background: '#4CAF50', color: 'white', border: 'none' }}>
                ➕ Add Row
              </button>
              <button onClick={downloadCSV} style={{ padding: '8px 16px', borderRadius: 6, cursor: 'pointer', background: '#2196F3', color: 'white', border: 'none' }}>
                ⬇ Download CSV
              </button>
               <span style={{ color: '#666', alignSelf: 'center' }}>
                {csvBody.filter(row => row.join('').trim() !== '').length} rows
              </span>
            </div>

            {/* Editable Table Container */}
            <div style={{ flex: 1, overflow: 'auto', border: '1px solid #ddd', borderRadius: 6 }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: '1200px' }}>
                <thead style={{ background: '#f5f5f5', position: 'sticky', top: 0, zIndex: 1 }}>
                  <tr>
                    <th style={{ padding: '12px 8px', border: '1px solid #ddd', textAlign: 'left', minWidth: '80px' }}>Action</th>
                    {csvHeaders.map((header, index) => (
                      <th key={index} style={{ padding: '12px 8px', border: '1px solid #ddd', textAlign: 'left', minWidth: '200px', whiteSpace: 'nowrap' }}>
                        {header}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {csvBody.length === 0 ? (
                    <tr><td colSpan={csvHeaders.length + 1} style={{ textAlign: 'center', padding: 20 }}>No data rows.</td></tr>
                  ) : (
                    csvBody.map((row, rowIndex) => (
                      // Filter out empty rows that might come from the BE
                      row.join("").trim() && <tr key={rowIndex}>
                        <td style={{ padding: '8px', border: '1px solid #ddd', textAlign: 'center' }}>
                           <button onClick={() => handleDeleteRow(rowIndex + 1)} style={{ background: '#f44336', color: 'white', border: 'none', borderRadius: 4, padding: '4px 8px', cursor: 'pointer', fontSize: '12px'}} title="Remove row">
                            🗑
                          </button>
                        </td>
                        {row.map((cell, cellIndex) => (
                          <td key={cellIndex} style={{ padding: '4px', border: '1px solid #ddd' }}>
                            <input
                              type="text"
                              value={cell}
                              onChange={(e) => handleCellChange(rowIndex + 1, cellIndex, e.target.value)}
                              style={{ width: '100%', border: 'none', padding: '8px', background: 'transparent', fontSize: '14px' }}
                            />
                          </td>
                        ))}
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>

          </div>
        </div>
      )}

    </div>
  );
}