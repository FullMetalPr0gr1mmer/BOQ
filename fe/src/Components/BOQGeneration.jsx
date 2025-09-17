import React, { useState, useEffect, useRef } from 'react';
import '../css/Dismantling.css';

const ROWS_PER_PAGE = 100;
const VITE_API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// --- Helper Functions (No changes here) ---
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

export default function BOQGeneration() {
  // --- State Variables ---
  const [rows, setRows] = useState([]);
  const [currentPage, setCurrentPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [uploading, setUploading] = useState(false);
  const [loading, setLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [linkedIp, setLinkedIp] = useState('');
  const [generating, setGenerating] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [editingRow, setEditingRow] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [editableCsvData, setEditableCsvData] = useState([]);

  // --- NEW: State for project selection ---
  const [projects, setProjects] = useState([]);
  const [selectedProject, setSelectedProject] = useState('');

  const [formData, setFormData] = useState({
    linkid: '',
    InterfaceName: '',
    SiteIPA: '',
    SiteIPB: '',
    pid_po: '', // NEW: To hold the project ID
  });

  const fetchAbort = useRef(null);

  // --- NEW: Function to fetch user's projects ---
  const fetchProjects = async () => {
    try {
      const res = await fetch(`${VITE_API_URL}/get_project`, { headers: getAuthHeaders() });
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

  // --- Data Fetching ---
  const fetchReferences = async (page = 1, search = '') => {
    try {
      if (fetchAbort.current) fetchAbort.current.abort();
      const controller = new AbortController();
      fetchAbort.current = controller;
      setLoading(true);
      setError('');

      const skip = (page - 1) * ROWS_PER_PAGE;
      const params = new URLSearchParams({ skip: skip.toString(), limit: ROWS_PER_PAGE.toString() });
      if (search.trim()) params.set('search', search.trim());

      const url = `${VITE_API_URL}/boq/references?${params.toString()}`;
      const res = await fetch(url, { 
        signal: controller.signal,
        method: 'GET',
        headers: getAuthHeaders()
      });

      if (!res.ok) {
        let errorMessage = 'Failed to fetch references';
        try {
          const errorData = await res.json();
          errorMessage = errorData.detail || errorData.message || errorMessage;
        } catch (e) {
          errorMessage = `HTTP ${res.status}: ${res.statusText}`;
        }
        throw new Error(errorMessage);
      }

      const data = await res.json();
      setRows((data.items || []).map(r => ({
        id: r.id,
        linkedIp: r.linkid,
        interfaceName: r.InterfaceName,
        siteA: r.SiteIPA,
        siteB: r.SiteIPB,
        pid_po: r.pid_po, // Store project ID for context
      })));
      setTotal(data.total || 0);
      setCurrentPage(page);
    } catch (err) {
      if (err.name !== 'AbortError') {
        setError(err.message || 'Failed to fetch');
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProjects(); // Fetch projects on component mount
    fetchReferences(1, '');
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const onSearchChange = (e) => {
    const v = e.target.value;
    setSearchTerm(v);
    fetchReferences(1, v);
  };

  // --- MODIFIED: Handle Upload to include project_id ---
  const handleUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    // Check if a project is selected
    if (!selectedProject) {
      setError("Please select a project before uploading.");
      e.target.value = ''; // Clear file input
      return;
    }

    setUploading(true);
    setError('');
    setSuccess('');

    const formDataLocal = new FormData();
    formDataLocal.append('file', file);

    try {
      // Append project_id as a query parameter
      const url = `${VITE_API_URL}/boq/upload-reference?project_id=${selectedProject}`;
      const res = await fetch(url, { 
        method: 'POST', 
        body: formDataLocal,
        headers: getAuthHeadersForFormData()
      });

      if (!res.ok) {
        let errorMessage = 'Upload failed';
        try {
          const errorData = await res.json();
          errorMessage = errorData.detail || errorData.message || errorMessage;
        } catch (err) {
          errorMessage = `HTTP ${res.status}: ${res.statusText}`;
        }
        throw new Error(errorMessage);
      }

      const result = await res.json();
      setSuccess(`Upload successful! ${result.rows_inserted} rows inserted.`);
      fetchReferences(1, searchTerm);
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
      e.target.value = '';
    }
  };

  // --- Unchanged Functions ---
  const handleGenerateRow = async (row) => { /* ... no changes needed ... */ 
        if (!row || !row.linkedIp) {
      setError('Selected row is invalid');
      return;
    }

    setGenerating(true);
    setError('');
    setLinkedIp(row.linkedIp);

    try {
      const url = `${VITE_API_URL}/boq/generate-boq`;
      const res = await fetch(url, {
        method: 'POST',
        headers: getAuthHeaders(),
        body: JSON.stringify({ siteA: row.siteA, siteB: row.siteB, linkedIp: row.linkedIp }),
      });

      if (!res.ok) {
        let errorMessage = 'Failed to generate BOQ';
        try {
          const errorData = await res.json();
          errorMessage = errorData.detail || errorData.message || errorMessage;
        } catch (e) {
          errorMessage = `HTTP ${res.status}: ${res.statusText}`;
        }
        throw new Error(errorMessage);
      }

      const data = await res.json();

      if (data.csv_content) {
        setEditableCsvData(parseCSV(data.csv_content));
        setShowModal(true);
      } else {
        throw new Error('No CSV content received from the server.');
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setGenerating(false);
    }
  };
  const handleCellChange = (rowIndex, cellIndex, value) => { /* ... no changes needed ... */ 
      const updatedData = editableCsvData.map((row, rIdx) => 
      rIdx === rowIndex ? row.map((cell, cIdx) => (cIdx === cellIndex ? value : cell)) : row
    );
    setEditableCsvData(updatedData);
  };
  const handleAddRow = () => { /* ... no changes needed ... */ 
      const numColumns = editableCsvData[0]?.length || 1;
    const newRow = Array(numColumns).fill('----------------');
    const updatedData = [editableCsvData[0], ...editableCsvData.slice(1), newRow];
    setEditableCsvData(updatedData);
  };
  const handleDeleteRow = (rowIndexToDelete) => { /* ... no changes needed ... */ 
      if (rowIndexToDelete === 0) return; 
    setEditableCsvData(editableCsvData.filter((_, index) => index !== rowIndexToDelete));
  };
  const downloadCSV = () => { /* ... no changes needed ... */ 
      if (!editableCsvData.length) return;
    const csvContent = stringifyCSV(editableCsvData);
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `BOQ_${linkedIp || 'export'}_edited.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // --- MODIFIED: Create / Edit / Delete to handle project_id ---
  const openCreateModal = () => {
    if (!selectedProject) {
      setError('Please select a project to create a new reference.');
      return;
    }
    setFormData({
      linkid: '',
      InterfaceName: '',
      SiteIPA: '',
      SiteIPB: '',
      pid_po: selectedProject, // Set the project ID for the new record
    });
    setEditingRow(null);
    setShowForm(true);
    setError('');
    setSuccess('');
  };

  const openEditModal = async (row) => {
    if (!row || !row.id) {
      setError('Cannot edit: missing id');
      return;
    }
    setEditingRow(row);
    try {
      setLoading(true);
      const res = await fetch(`${VITE_API_URL}/boq/reference/${row.id}`, {
        method: 'GET',
        headers: getAuthHeaders()
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Failed to fetch reference');
      }
      const data = await res.json();
      setFormData({
        linkid: data.linkid || '',
        InterfaceName: data.InterfaceName || '',
        SiteIPA: data.SiteIPA || '',
        SiteIPB: data.SiteIPB || '',
        pid_po: data.pid_po || '', // Make sure to get the project_id
      });
      setShowForm(true);
      setError('');
      setSuccess('');
    } catch (err) {
      setError(err.message || 'Failed to load reference for editing');
    } finally {
      setLoading(false);
    }
  };

  const closeFormModal = () => { /* ... no changes needed ... */ 
      setShowForm(false);
    setEditingRow(null);
    setFormData({
      linkid: '',
      InterfaceName: '',
      SiteIPA: '',
      SiteIPB: '',
      pid_po: '',
    });
    setError('');
    setSuccess('');
  };

  const handleFormInputChange = (e) => { /* ... no changes needed ... */ 
      const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };
  
  // No changes needed here, as formData now includes pid_po
  const handleFormSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setError('');
    setSuccess('');
    try {
      // Ensure pid_po is set before submitting
      const submitData = {
        ...formData,
        pid_po: formData.pid_po || selectedProject
      };
      if (editingRow) {
        const url = `${VITE_API_URL}/boq/reference/${editingRow.id}`;
        const res = await fetch(url, {
          method: 'PUT',
          headers: getAuthHeaders(),
          body: JSON.stringify(submitData),
        });
        if (!res.ok) {
          const err = await res.json().catch(() => ({}));
          throw new Error(err.detail || 'Failed to update reference');
        }
        setSuccess('Reference updated successfully!');
      } else {
        const url = `${VITE_API_URL}/boq/reference`;
        const res = await fetch(url, {
          method: 'POST',
          headers: getAuthHeaders(),
          body: JSON.stringify(submitData),
        });
        if (!res.ok) {
          const err = await res.json().catch(() => ({}));
          throw new Error(err.detail || 'Failed to create reference');
        }
        setSuccess('Reference created successfully!');
      }
      fetchReferences(currentPage, searchTerm);
      setTimeout(() => closeFormModal(), 1200);
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (row) => { /* ... no changes needed ... */ 
        if (!row || !row.id) return;
    if (!confirm(`Are you sure you want to delete reference "${row.linkedIp}"?`)) return;
    try {
      const res = await fetch(`${VITE_API_URL}/boq/reference/${row.id}`, {
        method: 'DELETE',
        headers: getAuthHeaders()
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Failed to delete reference');
      }
      setSuccess('Reference deleted successfully!');
      fetchReferences(currentPage, searchTerm);
    } catch (err) {
      setError(err.message);
    }
  };

  const totalPages = Math.ceil(total / ROWS_PER_PAGE);
  const csvHeaders = editableCsvData[0] || [];
  const csvBody = editableCsvData.slice(1);

  // --- JSX Rendering with new Project Selector ---
  return (
    <div className="dismantling-container">
      <div className="dismantling-header-row">
        <h2>BOQ Generation</h2>
        {/* NEW: Project Selector */}
        <div className="project-selector-container">
          
        </div>
        <div style={{ display: 'flex', gap: 16 }}>
          <button 
            className="upload-btn" 
            onClick={openCreateModal}
            disabled={!selectedProject} // Disable if no project is selected
            title={!selectedProject ? "Select a project first" : "Create a new reference"}
          >
            + New Reference
          </button>
          <label className={`upload-btn ${uploading || !selectedProject ? 'disabled' : ''}`}
            title={!selectedProject ? "Select a project first" : "Upload a reference CSV"}
          >
            📤 Upload Reference
            <input type="file" accept=".csv" style={{ display: 'none' }} disabled={uploading || !selectedProject} onChange={handleUpload} />
          </label>
        </div>
      </div>

      <div className="dismantling-search-container">
        <input
          type="text"
          placeholder="Type to filter (linkid / interface / site IP)..."
          value={searchTerm}
          onChange={onSearchChange}
          className="search-input"
        />
        {searchTerm && (
          <button onClick={() => { setSearchTerm(''); fetchReferences(1, ''); }} className="clear-btn">Clear</button>
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

      {error && <div className="dismantling-message error">{error}</div>}
      {success && <div className="dismantling-message success">{success}</div>}
      {loading && <div className="loading-message">Loading references...</div>}

      {/* --- Table and Modals (No structural changes, only logic behind them is updated) --- */}
      <div className="dismantling-table-container">
        {/* ... table jsx ... */}
         <table className="dismantling-table">
          <thead>
            <tr>
              <th style={{ textAlign: 'center' }}></th>
              <th style={{ textAlign: 'center' }}>Linked-IP</th>
              <th style={{ textAlign: 'center' }}>Interface Name</th>
              <th style={{ textAlign: 'center' }}>Site-A IP</th>
              <th style={{ textAlign: 'center' }}>Site-B IP</th>
              <th style={{ textAlign: 'center', width: '110px' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 && !loading ? (
              <tr><td colSpan={6} style={{ textAlign: 'center', padding: 16 }}>No results</td></tr>
            ) : (
              rows.map((row, idx) => (
                <tr key={idx}>
                  <td style={{ textAlign: 'center' }}>
                    <button
                      title={`Generate BOQ for ${row.linkedIp}`}
                      onClick={() => handleGenerateRow(row)}
                      disabled={generating}
                      style={{ padding: '4px 8px', borderRadius: 6, cursor: generating ? 'not-allowed' : 'pointer', border: '1px solid #ccc' }}
                    >
                      ▼
                    </button>
                  </td>
                  <td style={{ textAlign: 'center' }}>{row.linkedIp}</td>
                  <td style={{ textAlign: 'center' }}>{row.interfaceName}</td>
                  <td style={{ textAlign: 'center' }}>{row.siteA}</td>
                  <td style={{ textAlign: 'center' }}>{row.siteB}</td>
                  <td style={{ textAlign: 'center', width: '110px' }}>
                    <div className="actions-cell">
                      <button className="pagination-btn" onClick={() => openEditModal(row)}>Details</button>
                      <button className="clear-btn" onClick={() => handleDelete(row)}>Delete</button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div className="dismantling-pagination">
        {/* ... pagination jsx ... */}
         <button className="pagination-btn" disabled={currentPage === 1} onClick={() => fetchReferences(currentPage - 1, searchTerm)}>Prev</button>
          <span className="pagination-info">Page {currentPage} of {totalPages}</span>
          <button className="pagination-btn" disabled={currentPage === totalPages} onClick={() => fetchReferences(currentPage + 1, searchTerm)}>Next</button>
        </div>
      )}

      {showModal && (
        <div className="modal-overlay">
        {/* ... editable CSV modal jsx ... */}
                <div className="modal-content" style={{ maxWidth: '1200px', width: '100%', maxHeight: '90vh', overflow: 'auto', padding: '24px' }}>
            <div className="modal-header-row" style={{ justifyContent: 'space-between' }}>
              <h3 className="modal-title">Edit BOQ Data for {linkedIp}</h3>
              <button className="modal-close-btn" onClick={() => setShowModal(false)} type="button">&times;</button>
            </div>
            <div style={{ display: 'flex', gap: 12, marginBottom: 16 }}>
              <button className="upload-btn" onClick={handleAddRow}>➕ Add Row</button>
              <button className="upload-btn" onClick={downloadCSV}>⬇ Download CSV</button>
              <span style={{ color: '#666', alignSelf: 'center' }}>
                {csvBody.filter(row => row.join('').trim() !== '').length} rows
              </span>
            </div>
            <div className="dismantling-table-container" style={{ overflow: 'auto' }}>
              <table className="dismantling-table" style={{ minWidth: '400px', fontSize: '12px' }}>
                <thead>
                  <tr>
                    <th style={{ padding: '4px 2px', fontSize: '12px', textAlign: 'center' }}>Action</th>
                    {csvHeaders.map((header, index) => (
                      <th key={index} style={{ padding: '4px 2px', fontSize: '12px', textAlign: 'center' }}>{header}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {csvBody.length === 0 ? (
                    <tr><td colSpan={csvHeaders.length + 1} className="no-results" style={{ textAlign: 'center' }}>No data rows.</td></tr>
                  ) : (
                    csvBody.map((row, rowIndex) => (
                      row.join("").trim() && <tr key={rowIndex}>
                        <td style={{ textAlign: 'center', padding: '2px' }}>
                          <button className="clear-btn" style={{ background: 'transparent' }} onClick={() => handleDeleteRow(rowIndex + 1)} title="Remove row">🗑</button>
                        </td>
                        {row.map((cell, cellIndex) => (
                          <td key={cellIndex} style={{ padding: '2px', textAlign: 'center' }}>
                            <input
                              type="text"
                              value={cell}
                              onChange={(e) => handleCellChange(rowIndex + 1, cellIndex, e.target.value)}
                              className="search-input"
                              style={{ fontSize: '12px', padding: '2px', textAlign: 'center' }}
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

      {showForm && (
        <div className="modal-overlay">
        {/* ... create/edit modal jsx ... */}
                 <div className="modal-content">
           <form className="project-form" onSubmit={handleFormSubmit}>
             <div className="modal-header-row" style={{ justifyContent: 'space-between' }}>
               <h3 className="modal-title">
                 {editingRow ? `Editing Reference: '${editingRow.linkedIp}'` : 'New Reference'}
               </h3>
               <button className="modal-close-btn" onClick={closeFormModal} type="button">&times;</button>
             </div>

             {error && <div className="dismantling-message error">{error}</div>}
             {success && <div className="dismantling-message success">{success}</div>}

             {/* The project context is now handled by the global selector */}
             <input
              className="search-input"
              type="text"
              name="linkid"
              placeholder="Linked ID (linkid)"
              value={formData.linkid}
              onChange={handleFormInputChange}
              required
            />
             <input
              className="search-input"
              type="text"
              name="InterfaceName"
              placeholder="Interface Name"
              value={formData.InterfaceName}
              onChange={handleFormInputChange}
            />
             <input
              className="search-input"
              type="text"
              name="SiteIPA"
              placeholder="Site A IP (SiteIPA)"
              value={formData.SiteIPA}
              onChange={handleFormInputChange}
            />
             <input
              className="search-input"
              type="text"
              name="SiteIPB"
              placeholder="Site B IP (SiteIPB)"
              value={formData.SiteIPB}
              onChange={handleFormInputChange}
            />
             <button className="upload-btn" type="submit" disabled={submitting}>
              {submitting ? 'Saving...' : (editingRow ? 'Update' : 'Save')}
            </button>
           </form>
         </div>
        </div>
      )}
    </div>
  );
}