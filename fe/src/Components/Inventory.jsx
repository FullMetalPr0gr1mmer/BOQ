import React, { useEffect, useState, useRef } from 'react';
import '../css/LLDManagment.css'; // Using the same styling
import '../css/Dismantling.css'; // Using the same styling

const ROWS_PER_PAGE = 50;
const VITE_API_URL = import.meta.env.VITE_API_URL;

export default function Inventory() {
  const [rows, setRows] = useState([]);
  const [currentPage, setCurrentPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [showForm, setShowForm] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [searchTerm, setSearchTerm] = useState('');

  const fetchAbort = useRef(null);

  const initialForm = {
    site_id: '', site_name: '', slot_id: '', port_id: '', status: '',
    company_id: '', mnemonic: '', clei_code: '', part_no: '', software_no: '',
    factory_id: '', serial_no: '', date_id: '', manufactured_date: '',
    customer_field: '', license_points_consumed: '', alarm_status: '',
    Aggregated_alarm_status: ''
  };
  const [formData, setFormData] = useState(initialForm);

  const fetchInventory = async (page = 1, search = '') => {
    try {
      if (fetchAbort.current) fetchAbort.current.abort();
      const controller = new AbortController();
      fetchAbort.current = controller;

      setLoading(true);
      setError('');
      const skip = (page - 1) * ROWS_PER_PAGE;
      const params = new URLSearchParams({
        skip: String(skip),
        limit: String(ROWS_PER_PAGE),
        search: search.trim(),
      });
      
      const res = await fetch(`${VITE_API_URL}/inventory?${params.toString()}`, { signal: controller.signal });
      if (!res.ok) throw new Error('Failed to fetch inventory');
      
      const data = await res.json();
      setRows(data.records || []);
      setTotal(data.total || 0);
      setCurrentPage(page);
    } catch (err) {
      if (err.name !== 'AbortError') setError(err.message || 'Failed to fetch inventory');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchInventory(1, '');
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const onSearchChange = (e) => {
    const v = e.target.value;
    setSearchTerm(v);
    fetchInventory(1, v);
  };

  const openCreateForm = () => {
    setFormData(initialForm);
    setIsEditing(false);
    setEditingId(null);
    setShowForm(true);
    setError('');
    setSuccess('');
  };

  const openEditForm = (item) => {
    setFormData({ ...item });
    setIsEditing(true);
    setEditingId(item.id);
    setShowForm(true);
    setError('');
    setSuccess('');
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    try {
      let res;
      const payload = {
        ...formData,
        slot_id: parseInt(formData.slot_id || 0),
        port_id: parseInt(formData.port_id || 0),
      };
      
      if (isEditing && editingId !== null) {
        res = await fetch(`${VITE_API_URL}/update-inventory/${editingId}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
      } else {
        res = await fetch(`${VITE_API_URL}/create-inventory`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
      }

      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || 'Failed to save inventory');
      }

      setSuccess(isEditing ? 'Inventory updated' : 'Inventory created');
      setShowForm(false);
      fetchInventory(currentPage, searchTerm);
    } catch (err) {
      setError(err.message || 'Operation failed');
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this inventory item?')) return;
    try {
      const res = await fetch(`${VITE_API_URL}/delete-inventory/${id}`, { method: 'DELETE' });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || 'Failed to delete inventory');
      }
      setSuccess('Inventory deleted');
      fetchInventory(currentPage, searchTerm);
    } catch (err) {
      setError(err.message || 'Delete failed');
    }
  };

  const handleUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setUploading(true);
    setError('');
    setSuccess('');
    const formData = new FormData();
    formData.append("file", file);
    try {
      const res = await fetch(`${VITE_API_URL}/upload-inventory-csv`, {
        method: "POST",
        body: formData,
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || "Failed to upload CSV");
      }
      const result = await res.json();
      setSuccess(`Upload successful! ${result.inserted_count} rows inserted.`);
      fetchInventory(1, searchTerm);
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  };

  const totalPages = Math.ceil(total / ROWS_PER_PAGE);

  return (
    <div className="dismantling-container">
      <div className="dismantling-header-row">
        <h2>Inventory</h2>
        <div style={{ display: 'flex', gap: 16 }}>
          <button className="stylish-btn" onClick={openCreateForm}>+ New Inventory</button>
          <label className={`upload-btn ${uploading ? 'disabled' : ''}`}>
            📤 Upload CSV
            <input type="file" accept=".csv" style={{ display: "none" }} disabled={uploading} onChange={handleUpload} />
          </label>
        </div>
      </div>

      <div className="dismantling-search-container">
        <input
          type="text"
          placeholder="Search by Site ID..."
          value={searchTerm}
          onChange={onSearchChange}
          className="search-input"
        />
        {searchTerm && (
          <button onClick={() => { setSearchTerm(''); fetchInventory(1, ''); }} className="clear-btn">Clear</button>
        )}
      </div>

      {error && <div className="dismantling-message error">{error}</div>}
      {success && <div className="dismantling-message success">{success}</div>}
      {loading && <div className="loading-message">Loading inventory...</div>}

      <div className="dismantling-table-container">
        <table className="dismantling-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Site Id</th>
              <th>Site Name</th>
              <th>Slot Id</th>
              <th>Port Id</th>
              <th>Status</th>
              <th>Company ID</th>
              <th>Mnemonic</th>
              <th>CLEI Code</th>
              <th>Part No</th>
              <th>Software Part No</th>
              <th>Factory ID</th>
              <th>Serial No</th>
              <th>Date ID</th>
              <th>Manufactured Date</th>
              <th>Customer Field</th>
              <th>License Points Consumed</th>
              <th>Alarm Status</th>
              <th>Aggregated Alarm Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 && !loading ? (
              <tr><td colSpan={20} className="no-results">No results</td></tr>
            ) : (
              rows.map(item => (
                <tr key={item.id}>
                  <td>{item.id}</td>
                  <td>{item.site_id}</td>
                  <td>{item.site_name}</td>
                  <td>{item.slot_id}</td>
                  <td>{item.port_id}</td>
                  <td>{item.status}</td>
                  <td>{item.company_id}</td>
                  <td>{item.mnemonic}</td>
                  <td>{item.clei_code}</td>
                  <td>{item.part_no}</td>
                  <td>{item.software_no}</td>
                  <td>{item.factory_id}</td>
                  <td>{item.serial_no}</td>
                  <td>{item.date_id}</td>
                  <td>{item.manufactured_date}</td>
                  <td>{item.customer_field}</td>
                  <td>{item.license_points_consumed}</td>
                  <td>{item.alarm_status}</td>
                  <td>{item.Aggregated_alarm_status}</td>
                  <td style={{ textAlign: 'center' }}>
                    <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'center' }}>
                      <button className="stylish-btn" onClick={() => openEditForm(item)}>Details</button>
                      <button className="stylish-btn danger" onClick={() => handleDelete(item.id)}>Delete</button>
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
          <button className="pagination-btn" disabled={currentPage === 1} onClick={() => fetchInventory(currentPage - 1, searchTerm)}>Prev</button>
          <span className="pagination-info">Page {currentPage} of {totalPages}</span>
          <button className="pagination-btn" disabled={currentPage === totalPages} onClick={() => fetchInventory(currentPage + 1, searchTerm)}>Next</button>
        </div>
      )}

      {showForm && (
        <div className="modal-overlay">
          <div className="modal-content" style={{ minWidth: '800px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12 }}>
              <h3>{isEditing ? `Edit Inventory: ${editingId}` : 'New Inventory'}</h3>
              <button onClick={() => setShowForm(false)} className="close-btn">✖</button>
            </div>
            <form onSubmit={handleSubmit} className="project-form">
              {Object.keys(initialForm).map((key) => (
                <div key={key}>
                  <label>{key.replace(/_/g, ' ')}</label>
                  <input
                    type={['slot_id', 'port_id'].includes(key) ? 'number' : 'text'}
                    name={key}
                    value={formData[key] || ''}
                    onChange={handleChange}
                    required
                    disabled={isEditing && key === 'site_id'}
                  />
                </div>
              ))}
              <button type="submit" className="stylish-btn" style={{ width: '100%', marginTop: '1rem' }}>
                {isEditing ? 'Update Inventory' : 'Create Inventory'}
              </button>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}