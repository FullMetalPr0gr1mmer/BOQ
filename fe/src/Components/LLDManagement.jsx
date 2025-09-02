import React, { useState, useEffect, useRef } from 'react';
import '../css/LLDManagment.css'; // Updated to use the new LLD.css file

const ROWS_PER_PAGE = 50;
const VITE_API_URL = import.meta.env.VITE_API_URL;

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

  const fetchAbort = useRef(null);

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

      const res = await fetch(`${VITE_API_URL}/lld?${params.toString()}`, { signal: controller.signal });
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
    setUploading(true);
    setError('');
    setSuccess('');
    const formData = new FormData();
    formData.append('file', file);
    try {
      const res = await fetch(`${VITE_API_URL}/lld/upload-csv`, { method: 'POST', body: formData });
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
      const res = await fetch(`${VITE_API_URL}/lld/${link_id}`, { method: 'DELETE' });
      if (!res.ok) throw new Error('Failed to delete LLD row');
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

  // Handle field change in edit
  const onEditChange = (key, value) => {
    setEditRow(prev => ({ ...prev, [key]: value }));
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
        headers: { 'Content-Type': 'application/json' },
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

  // Download CSV
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

  return (
    <div className="lld-container"> {/* Updated container class */}
      {/* Header & Upload */}
      <div className="lld-header-row"> {/* Updated header class */}
        <h2>LLD Management</h2>
        <div style={{ display: 'flex', gap: 16, alignItems: 'center' }}>
          <label className={`upload-btn ${uploading ? 'disabled' : ''}`}>
            📤 Upload CSV
            <input type="file" accept=".csv" style={{ display: 'none' }} disabled={uploading} onChange={handleUpload} />
          </label>
          <button onClick={downloadCSV} className="upload-btn">⬇ Download CSV</button>
        </div>
      </div>

      {/* Search */}
      <div className="lld-search-container"> {/* Updated search container class */}
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
      </div>

      {/* Messages */}
      {error && <div className="lld-message error">{error}</div>} {/* Updated message class */}
      {success && <div className="lld-message success">{success}</div>} {/* Updated message class */}
      {loading && <div className="loading-message">Loading LLD records...</div>}

      {/* Table */}
      <div className="lld-table-container"> {/* Updated table container class */}
        <table className="lld-table"> {/* Updated table class */}
          <thead>
            <tr>
              <th>Link ID</th>
              <th>Action</th>
              <th>FON</th>
              <th>Item Name</th>
              <th>Distance</th>
              <th>Scope</th>
              <th>FE</th>
              <th>NE</th>
              <th>Link Category</th>
              <th>Link Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 && !loading ? (
              <tr><td colSpan={11} className="no-results">No results</td></tr>
            ) : rows.map((row) => (
              <tr key={row.link_id}>
                <td>{row.link_id}</td>
                <td>{row.action}</td>
                <td>{row.fon}</td>
                <td>{row.item_name}</td>
                <td>{row.distance}</td>
                <td>{row.scope}</td>
                <td>{row.fe}</td>
                <td>{row.ne}</td>
                <td>{row.link_category}</td>
                <td>{row.link_status}</td>
                <td>
                  <button onClick={() => handleEdit(row)} className="lld-table-btn edit-btn">Edit</button>
                  <button onClick={() => handleDelete(row.link_id)} className="lld-table-btn delete-btn">Delete</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="lld-pagination"> {/* Updated pagination class */}
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

      {/* Edit Modal (using existing styles) */}
      {showModal && (
        <div className="modal-overlay">
          <div className="modal-content">
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12 }}>
              <h3>Edit LLD: {editRow?.link_id}</h3>
              <button onClick={() => { setShowModal(false); setEditRow(null); }} className="close-btn">✖</button>
            </div>
            {editRow && (
              <>
                <table className="lld-table" style={{ width: '100%' }}>
                  <tbody>
                    {Object.entries(editRow).map(([key, value]) => (
                      <tr key={key}>
                        <td style={{ fontWeight: 'bold' }}>{key}</td>
                        <td>
                          <input
                            type="text"
                            value={value || ''}
                            onChange={e => onEditChange(key, e.target.value)}
                            style={{ width: '100%', padding: 4 }}
                          />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                <button
                  onClick={handleUpdate}
                  disabled={updating}
                  className="pagination-btn"
                  style={{ marginTop: 12 }}
                >
                  {updating ? 'Updating...' : 'Update'}
                </button>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}