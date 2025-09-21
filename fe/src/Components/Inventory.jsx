import React, { useEffect, useState, useRef } from 'react';
import '../css/LLDManagment.css'; // Using the same styling
import '../css/Dismantling.css'; // Using the same styling

const ROWS_PER_PAGE = 50;
const VITE_API_URL = import.meta.env.VITE_API_URL;
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

      const res = await fetch(`${VITE_API_URL}/inventory?${params.toString()}`, {
        signal: controller.signal, method: 'GET',
        headers: getAuthHeaders()
      });
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
          body: JSON.stringify(payload),
          headers: getAuthHeaders()
        });
      } else {
        res = await fetch(`${VITE_API_URL}/create-inventory`, {
          method: 'POST',
          body: JSON.stringify(payload),
          headers: getAuthHeaders()
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
      const res = await fetch(`${VITE_API_URL}/delete-inventory/${id}`, {
        method: 'DELETE',
        headers: getAuthHeaders()
      });
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
        headers: getAuthHeaders()
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
              <th style={{ textAlign: 'center' }}>Site Id</th>
              <th style={{ textAlign: 'center' }}>Site Name</th>
              <th style={{ textAlign: 'center' }}>Slot Id</th>
              <th style={{ textAlign: 'center' }}>Port Id</th>
              <th style={{ textAlign: 'center' }}>Status</th>
              <th style={{ textAlign: 'center' }}>Company ID</th>
              <th style={{ textAlign: 'center' }}>Mnemonic</th>
              <th style={{ textAlign: 'center' }}>CLEI Code</th>
              <th style={{ textAlign: 'center' }}>Part No</th>
              <th style={{ textAlign: 'center' }}>Software Part No</th>
              <th style={{ textAlign: 'center' }}>Factory ID</th>
              <th style={{ textAlign: 'center' }}>Serial No</th>
              <th style={{ textAlign: 'center' }}>Date ID</th>
              <th style={{ textAlign: 'center' }}>Manufactured Date</th>
              <th style={{ textAlign: 'center' }}>Customer Field</th>
              <th style={{ textAlign: 'center' }}>License Points Consumed</th>
              <th style={{ textAlign: 'center' }}>Alarm Status</th>
              <th style={{ textAlign: 'center' }}>Aggregated Alarm Status</th>
              <th style={{ textAlign: 'center' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 && !loading ? (
              <tr><td colSpan={19} className="no-results">No results</td></tr>
            ) : (
              rows.map(item => (
                <tr key={item.id}>
                  <td style={{ textAlign: 'center' }}>{item.site_id}</td>
                  <td style={{ textAlign: 'center' }}>{item.site_name}</td>
                  <td style={{ textAlign: 'center' }}>{item.slot_id}</td>
                  <td style={{ textAlign: 'center' }}>{item.port_id}</td>
                  <td style={{ textAlign: 'center' }}>{item.status}</td>
                  <td style={{ textAlign: 'center' }}>{item.company_id}</td>
                  <td style={{ textAlign: 'center' }}>{item.mnemonic}</td>
                  <td style={{ textAlign: 'center' }}>{item.clei_code}</td>
                  <td style={{ textAlign: 'center' }}>{item.part_no}</td>
                  <td style={{ textAlign: 'center' }}>{item.software_no}</td>
                  <td style={{ textAlign: 'center' }}>{item.factory_id}</td>
                  <td style={{ textAlign: 'center' }}>{item.serial_no}</td>
                  <td style={{ textAlign: 'center' }}>{item.date_id}</td>
                  <td style={{ textAlign: 'center' }}>{item.manufactured_date}</td>
                  <td style={{ textAlign: 'center' }}>{item.customer_field}</td>
                  <td style={{ textAlign: 'center' }}>{item.license_points_consumed}</td>
                  <td style={{ textAlign: 'center' }}>{item.alarm_status}</td>
                  <td style={{ textAlign: 'center' }}>{item.Aggregated_alarm_status}</td>
                  <td style={{ textAlign: 'center' }}>
                    <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'center' }}>
                      <button className="pagination-btn" onClick={() => openEditForm(item)}>Details</button>
                      <button className="clear-btn" onClick={() => handleDelete(item.id)}>Delete</button>
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
          <div className="modal-content">
            <form className="project-form" onSubmit={handleSubmit}>
              <div className="modal-header-row" style={{ justifyContent: 'space-between' }}>
                <h3 className="modal-title">
                  {isEditing ? `Edit Inventory: ${editingId}` : 'New Inventory'}
                </h3>
                <button className="modal-close-btn" onClick={() => setShowForm(false)} type="button">&times;</button>
              </div>
              <input
                className="search-input"
                type="text"
                name="site_id"
                placeholder="Site ID"
                value={formData.site_id}
                required
                disabled={isEditing}
                onChange={handleChange}
              />
              <input
                className="search-input"
                type="text"
                name="site_name"
                placeholder="Site Name"
                value={formData.site_name}
                required
                onChange={handleChange}
              />
              <input
                className="search-input"
                type="number"
                name="slot_id"
                placeholder="Slot ID"
                value={formData.slot_id}
                required
                onChange={handleChange}
              />
              <input
                className="search-input"
                type="number"
                name="port_id"
                placeholder="Port ID"
                value={formData.port_id}
                required
                onChange={handleChange}
              />
              <input
                className="search-input"
                type="text"
                name="status"
                placeholder="Status"
                value={formData.status}
                required
                onChange={handleChange}
              />
              <input
                className="search-input"
                type="text"
                name="company_id"
                placeholder="Company ID"
                value={formData.company_id}
                required
                onChange={handleChange}
              />
              <input
                className="search-input"
                type="text"
                name="mnemonic"
                placeholder="Mnemonic"
                value={formData.mnemonic}
                required
                onChange={handleChange}
              />
              <input
                className="search-input"
                type="text"
                name="clei_code"
                placeholder="CLEI Code"
                value={formData.clei_code}
                required
                onChange={handleChange}
              />
              <input
                className="search-input"
                type="text"
                name="part_no"
                placeholder="Part No"
                value={formData.part_no}
                required
                onChange={handleChange}
              />
              <input
                className="search-input"
                type="text"
                name="software_no"
                placeholder="Software Part No"
                value={formData.software_no}
                required
                onChange={handleChange}
              />
              <input
                className="search-input"
                type="text"
                name="factory_id"
                placeholder="Factory ID"
                value={formData.factory_id}
                required
                onChange={handleChange}
              />
              <input
                className="search-input"
                type="text"
                name="serial_no"
                placeholder="Serial No"
                value={formData.serial_no}
                required
                onChange={handleChange}
              />
              <input
                className="search-input"
                type="text"
                name="date_id"
                placeholder="Date ID"
                value={formData.date_id}
                required
                onChange={handleChange}
              />
              <input
                className="search-input"
                type="text"
                name="manufactured_date"
                placeholder="Manufactured Date"
                value={formData.manufactured_date}
                required
                onChange={handleChange}
              />
              <input
                className="search-input"
                type="text"
                name="customer_field"
                placeholder="Customer Field"
                value={formData.customer_field}
                required
                onChange={handleChange}
              />
              <input
                className="search-input"
                type="text"
                name="license_points_consumed"
                placeholder="License Points Consumed"
                value={formData.license_points_consumed}
                required
                onChange={handleChange}
              />
              <input
                className="search-input"
                type="text"
                name="alarm_status"
                placeholder="Alarm Status"
                value={formData.alarm_status}
                required
                onChange={handleChange}
              />
              <input
                className="search-input"
                type="text"
                name="Aggregated_alarm_status"
                placeholder="Aggregated Alarm Status"
                value={formData.Aggregated_alarm_status}
                required
                onChange={handleChange}
              />
              <button className="upload-btn" type="submit">
                {isEditing ? 'Update' : 'Save'}
              </button>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}