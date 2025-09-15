import React, { useState, useEffect, useRef } from 'react';
import '../css/LLDManagment.css';

const ROWS_PER_PAGE = 50;
const VITE_API_URL = import.meta.env.VITE_API_URL;

// --- Helper Functions from BOQGeneration.jsx ---
const getAuthHeaders = () => {
  const token = localStorage.getItem('token');
  const headers = { 'Content-Type': 'application/json' };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
};

const getAuthHeadersForFormData = () => {
  const token = localStorage.getItem('token');
  const headers = {};
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
};

export default function LLDManagement() {
  const [rows, setRows] = useState([]);
  const [currentPage, setCurrentPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [editRow, setEditRow] = useState(null);
  const [updating, setUpdating] = useState(false);
  // NEW: State for projects
  const [projects, setProjects] = useState([]);
  const [selectedProject, setSelectedProject] = useState('');

  const fetchAbort = useRef(null);

  // Initialize empty form data
  const getEmptyFormData = () => ({
    link_id: '',
    action: '',
    fon: '',
    item_name: '',
    distance: '',
    scope: '',
    fe: '',
    ne: '',
    link_category: '',
    link_status: '',
    comments: '',
    dismanting_link_id: '',
    band: '',
    t_band_cs: '',
    ne_ant_size: '',
    fe_ant_size: '',
    sd_ne: '',
    sd_fe: '',
    odu_type: '',
    updated_sb: '',
    region: '',
    losr_approval: '',
    initial_lb: '',
    flb: '',
    pid_po: '', // Add pid_po to form data
  });

  // NEW: Function to fetch user's projects
  const fetchProjects = async () => {
    try {
      const res = await fetch(`${VITE_API_URL}/get_project`, { headers: getAuthHeaders() });
      if (!res.ok) throw new Error('Could not fetch projects');
      const data = await res.json();
      setProjects(data || []);
      if (data && data.length > 0) {
        setSelectedProject(data[0].pid_po);
      }
    } catch (err) {
      setError('Failed to load projects. Please ensure you have project access.');
      console.error(err);
    }
  };

  // Fetch LLD rows (pagination + search)
  const fetchLLD = async (page = 1, search = '') => {
    try {
      if (fetchAbort.current) fetchAbort.current.abort();
      const controller = new AbortController();
      fetchAbort.current = controller;

      setLoading(true);
      setError('');
      const skip = (page - 1) * ROWS_PER_PAGE;

      const params = new URLSearchParams();
      params.set('skip', String(skip));
      params.set('limit', String(ROWS_PER_PAGE));
      if (search.trim()) params.set('link_id', search.trim());
      // NEW: Don't filter by project ID on the front end, let the backend handle it based on user access.

      const res = await fetch(`${VITE_API_URL}/lld?${params.toString()}`, {
        signal: controller.signal,
        headers: getAuthHeaders(), // Add auth headers
      });
      if (!res.ok) throw new Error('Failed to fetch LLD rows');
      const data = await res.json();

      setRows(data.items || []);
      setTotal(data.total || 0);
      setCurrentPage(page);
    } catch (err) {
      if (err.name !== 'AbortError') setError(err.message || 'Failed to fetch LLD rows');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProjects(); // Fetch projects on mount
    fetchLLD(1, '');
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const onSearchChange = (e) => {
    const v = e.target.value;
    setSearchTerm(v);
    fetchLLD(1, v);
  };

  // CSV Upload
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
    setError('');
    setSuccess('');

    const formData = new FormData();
    formData.append('file', file);

    try {
      const url = `${VITE_API_URL}/lld/upload-csv?project_id=${selectedProject}`;
      const res = await fetch(url, {
        method: 'POST',
        body: formData,
        headers: getAuthHeadersForFormData(), // Use appropriate headers for FormData
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Failed to upload CSV');
      }
      const result = await res.json();
      setSuccess(`Upload successful! ${result.rows_inserted} rows inserted.`);
      fetchLLD(1, searchTerm);
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
      e.target.value = '';
    }
  };

  // Delete row
  const handleDelete = async (link_id) => {
    if (!window.confirm(`Delete LLD row ${link_id}?`)) return;
    try {
      const res = await fetch(`${VITE_API_URL}/lld/${link_id}`, {
        method: 'DELETE',
        headers: getAuthHeaders(), // Add auth headers
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Failed to delete LLD row');
      }
      setSuccess(`Deleted ${link_id} successfully`);
      fetchLLD(currentPage, searchTerm);
    } catch (err) {
      setError(err.message);
    }
  };

  // Open edit modal
  const handleEdit = (row) => {
    setEditRow({ ...row }); // clone
    setShowModal(true);
  };

  // Open create modal
  const handleOpenCreate = () => {
    if (!selectedProject) {
      setError('Please select a project to create a new LLD record.');
      return;
    }
    const emptyFormData = getEmptyFormData();
    emptyFormData.pid_po = selectedProject; // Set the project for the new record
    setEditRow(emptyFormData);
    setShowModal(true);
  };

  // Handle field change in edit/create
  const onEditChange = (key, value) => {
    setEditRow(prev => ({ ...prev, [key]: value }));
  };

  // Create new LLD row
  const handleCreate = async () => {
    if (!editRow) return;
    setUpdating(true);
    setError('');
    setSuccess('');
    try {
      const res = await fetch(`${VITE_API_URL}/lld`, {
        method: 'POST',
        headers: getAuthHeaders(), // Add auth headers
        body: JSON.stringify(editRow),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Failed to create LLD row');
      }
      setSuccess('Row created successfully!');
      fetchLLD(currentPage, searchTerm);
      setShowModal(false);
      setEditRow(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setUpdating(false);
    }
  };

  // Submit update
  const handleUpdate = async () => {
    if (!editRow || !editRow.link_id) return;
    setUpdating(true);
    setError('');
    setSuccess('');
    try {
      const res = await fetch(`${VITE_API_URL}/lld/${editRow.link_id}`, {
        method: 'PUT',
        headers: getAuthHeaders(), // Add auth headers
        body: JSON.stringify(editRow),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Failed to update LLD row');
      }
      setSuccess('Row updated successfully!');
      fetchLLD(currentPage, searchTerm);
      setShowModal(false);
      setEditRow(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setUpdating(false);
    }
  };

  const downloadCSV = () => {
    if (!rows.length) return;
    const header = [
      'link_id', 'action', 'fon', 'item_name', 'distance', 'scope', 'fe', 'ne', 'link_category', 'link_status',
      'comments', 'dismanting_link_id', 'band', 't_band_cs', 'ne_ant_size', 'fe_ant_size', 'sd_ne', 'sd_fe',
      'odu_type', 'updated_sb', 'region', 'losr_approval', 'initial_lb', 'flb'
    ];
    const rowsCsv = rows.map(r => header.map(h => r[h] || ''));
    const csvContent = [header.join(','), ...rowsCsv.map(e => e.join(','))].join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `LLD_export.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const totalPages = Math.ceil(total / ROWS_PER_PAGE);
  const isCreateMode = editRow && !editRow.id;

  return (
    <div className="lld-container">
      {/* Header & Upload */}
      <div className="lld-header-row">
        <h2>LLD Management</h2>
        <div style={{ display: 'flex', gap: 16, alignItems: 'center' }}>
          <button
            className="upload-btn"
            onClick={handleOpenCreate}
            disabled={!selectedProject} // Disable if no project is selected
            title={!selectedProject ? "Select a project first" : "Create a new LLD record"}
          >
            + Add LLD
          </button>
          <label
            className={`upload-btn ${uploading || !selectedProject ? 'disabled' : ''}`}
            title={!selectedProject ? "Select a project first" : "Upload a reference CSV"}
          >
            📤 Upload CSV
            <input
              type="file"
              accept=".csv"
              style={{ display: 'none' }}
              disabled={uploading || !selectedProject}
              onChange={handleUpload}
            />
          </label>
        </div>
      </div>

      {/* Search and Project Selector */}
      <div className="lld-search-container">
        <input
          type="text"
          placeholder="Search by Link ID..."
          value={searchTerm}
          onChange={onSearchChange}
          className="search-input"
        />
        {searchTerm && (
          <button
            onClick={() => {
              setSearchTerm('');
              fetchLLD(1, '');
            }}
            className="clear-btn"
          >
            Clear
          </button>
        )}
        {/* NEW: Project Selector */}
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
      {error && <div className="lld-message error">{error}</div>}
      {success && <div className="lld-message success">{success}</div>}
      {loading && <div className="loading-message">Loading LLD records...</div>}

      {/* Table */}
      <div className="lld-table-container">
        <table className="lld-table">
          <thead>
            <tr>
              <th style={{ textAlign: 'center' }}>Link ID</th>
              <th style={{ textAlign: 'center' }}>Action</th>
              <th style={{ textAlign: 'center' }}>FON</th>
              <th style={{ textAlign: 'center' }}>Item Name</th>
              <th style={{ textAlign: 'center' }}>Distance</th>
              <th style={{ textAlign: 'center' }}>Scope</th>
              <th style={{ textAlign: 'center' }}>FE</th>
              <th style={{ textAlign: 'center' }}>NE</th>
              <th style={{ textAlign: 'center' }}>Link Category</th>
              <th style={{ textAlign: 'center' }}>Link Status</th>
              <th style={{ textAlign: 'center' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 && !loading ? (
              <tr><td colSpan={11} className="no-results" style={{ textAlign: 'center' }}>No results</td></tr>
            ) : rows.map((row) => (
              <tr key={row.link_id}>
                <td style={{ textAlign: 'center' }}>{row.link_id}</td>
                <td style={{ textAlign: 'center' }}>{row.action}</td>
                <td style={{ textAlign: 'center' }}>{row.fon}</td>
                <td style={{ textAlign: 'center' }}>{row.item_name}</td>
                <td style={{ textAlign: 'center' }}>{row.distance}</td>
                <td style={{ textAlign: 'center' }}>{row.scope}</td>
                <td style={{ textAlign: 'center' }}>{row.fe}</td>
                <td style={{ textAlign: 'center' }}>{row.ne}</td>
                <td style={{ textAlign: 'center' }}>{row.link_category}</td>
                <td style={{ textAlign: 'center' }}>{row.link_status}</td>
                <td style={{ textAlign: 'center' }}>
                  <div className="actions-cell">
                    <button className="pagination-btn" onClick={() => handleEdit(row)}>Details</button>
                    <button className="clear-btn" onClick={() => handleDelete(row.link_id)}>Delete</button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="lld-pagination">
          <button
            className="pagination-btn"
            disabled={currentPage === 1}
            onClick={() => fetchLLD(currentPage - 1, searchTerm)}
          >
            Prev
          </button>
          <span className="pagination-info">
            Page {currentPage} of {totalPages}
          </span>
          <button
            className="pagination-btn"
            disabled={currentPage === totalPages}
            onClick={() => fetchLLD(currentPage + 1, searchTerm)}
          >
            Next
          </button>
        </div>
      )}

      {showModal && (
        <div className="modal-overlay">
          <div className="modal-content">
            <form className="project-form" onSubmit={e => {
              e.preventDefault();
              if (isCreateMode) {
                handleCreate();
              } else {
                handleUpdate();
              }
            }}>
              <div className="modal-header-row" style={{ justifyContent: 'space-between' }}>
                <h3 className="modal-title">
                  {isCreateMode ? 'New LLD' : `Editing LLD: '${editRow.link_id}'`}
                </h3>
                <button className="modal-close-btn" onClick={() => { setShowModal(false); setEditRow(null); }} type="button">&times;</button>
              </div>

              {error && <div className="lld-message error">{error}</div>}
              {success && <div className="lld-message success">{success}</div>}

              {/* Form fields with pid_po */}
              {isCreateMode && (
                <input
                  className="search-input"
                  type="text"
                  name="pid_po"
                  placeholder="Project ID"
                  value={editRow.pid_po || ''}
                  onChange={e => onEditChange('pid_po', e.target.value)}
                  disabled
                />
              )}
              <input
                className="search-input"
                type="text"
                name="link_id"
                placeholder="Link ID"
                value={editRow ? editRow.link_id || '' : ''}
                required
                disabled={!isCreateMode}
                onChange={e => onEditChange('link_id', e.target.value)}
              />
              <input
                className="search-input"
                type="text"
                name="action"
                placeholder="Action"
                value={editRow ? editRow.action || '' : ''}
                required
                onChange={e => onEditChange('action', e.target.value)}
              />
              <input
                className="search-input"
                type="text"
                name="fon"
                placeholder="FON"
                value={editRow ? editRow.fon || '' : ''}
                required
                onChange={e => onEditChange('fon', e.target.value)}
              />
              <input
                className="search-input"
                type="text"
                name="item_name"
                placeholder="Item Name"
                value={editRow ? editRow.item_name || '' : ''}
                required
                onChange={e => onEditChange('item_name', e.target.value)}
              />
              <input
                className="search-input"
                type="text"
                name="distance"
                placeholder="Distance"
                value={editRow ? editRow.distance || '' : ''}
                required
                onChange={e => onEditChange('distance', e.target.value)}
              />
              <input
                className="search-input"
                type="text"
                name="scope"
                placeholder="Scope"
                value={editRow ? editRow.scope || '' : ''}
                required
                onChange={e => onEditChange('scope', e.target.value)}
              />
              <input
                className="search-input"
                type="text"
                name="fe"
                placeholder="FE"
                value={editRow ? editRow.fe || '' : ''}
                required
                onChange={e => onEditChange('fe', e.target.value)}
              />
              <input
                className="search-input"
                type="text"
                name="ne"
                placeholder="NE"
                value={editRow ? editRow.ne || '' : ''}
                required
                onChange={e => onEditChange('ne', e.target.value)}
              />
              <input
                className="search-input"
                type="text"
                name="link_category"
                placeholder="Link Category"
                value={editRow ? editRow.link_category || '' : ''}
                required
                onChange={e => onEditChange('link_category', e.target.value)}
              />
              <input
                className="search-input"
                type="text"
                name="link_status"
                placeholder="Link Status"
                value={editRow ? editRow.link_status || '' : ''}
                required
                onChange={e => onEditChange('link_status', e.target.value)}
              />
              <input
                className="search-input"
                type="text"
                name="comments"
                placeholder="Comments"
                value={editRow ? editRow.comments || '' : ''}
                onChange={e => onEditChange('comments', e.target.value)}
              />
              <input
                className="search-input"
                type="text"
                name="dismanting_link_id"
                placeholder="Dismanting Link ID"
                value={editRow ? editRow.dismanting_link_id || '' : ''}
                onChange={e => onEditChange('dismanting_link_id', e.target.value)}
              />
              <input
                className="search-input"
                type="text"
                name="band"
                placeholder="Band"
                value={editRow ? editRow.band || '' : ''}
                onChange={e => onEditChange('band', e.target.value)}
              />
              <input
                className="search-input"
                type="text"
                name="t_band_cs"
                placeholder="T-band CS"
                value={editRow ? editRow.t_band_cs || '' : ''}
                onChange={e => onEditChange('t_band_cs', e.target.value)}
              />
              <input
                className="search-input"
                type="text"
                name="ne_ant_size"
                placeholder="NE Ant Size"
                value={editRow ? editRow.ne_ant_size || '' : ''}
                onChange={e => onEditChange('ne_ant_size', e.target.value)}
              />
              <input
                className="search-input"
                type="text"
                name="fe_ant_size"
                placeholder="FE Ant Size"
                value={editRow ? editRow.fe_ant_size || '' : ''}
                onChange={e => onEditChange('fe_ant_size', e.target.value)}
              />
              <input
                className="search-input"
                type="text"
                name="sd_ne"
                placeholder="SD NE"
                value={editRow ? editRow.sd_ne || '' : ''}
                onChange={e => onEditChange('sd_ne', e.target.value)}
              />
              <input
                className="search-input"
                type="text"
                name="sd_fe"
                placeholder="SD FE"
                value={editRow ? editRow.sd_fe || '' : ''}
                onChange={e => onEditChange('sd_fe', e.target.value)}
              />
              <input
                className="search-input"
                type="text"
                name="odu_type"
                placeholder="ODU Type"
                value={editRow ? editRow.odu_type || '' : ''}
                onChange={e => onEditChange('odu_type', e.target.value)}
              />
              <input
                className="search-input"
                type="text"
                name="updated_sb"
                placeholder="Updated SB"
                value={editRow ? editRow.updated_sb || '' : ''}
                onChange={e => onEditChange('updated_sb', e.target.value)}
              />
              <input
                className="search-input"
                type="text"
                name="region"
                placeholder="Region"
                value={editRow ? editRow.region || '' : ''}
                onChange={e => onEditChange('region', e.target.value)}
              />
              <input
                className="search-input"
                type="text"
                name="losr_approval"
                placeholder="LOSR Approval"
                value={editRow ? editRow.losr_approval || '' : ''}
                onChange={e => onEditChange('losr_approval', e.target.value)}
              />
              <input
                className="search-input"
                type="text"
                name="initial_lb"
                placeholder="Initial LB"
                value={editRow ? editRow.initial_lb || '' : ''}
                onChange={e => onEditChange('initial_lb', e.target.value)}
              />
              <input
                className="search-input"
                type="text"
                name="flb"
                placeholder="FLB"
                value={editRow ? editRow.flb || '' : ''}
                onChange={e => onEditChange('flb', e.target.value)}
              />
              <button className="upload-btn" type="submit" disabled={updating}>
                {updating ? 'Saving...' : (isCreateMode ? 'Create' : 'Update')}
              </button>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}