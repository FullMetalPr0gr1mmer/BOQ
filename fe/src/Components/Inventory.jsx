import React, { useEffect, useState, useRef } from 'react';
import '../css/LLDManagment.css'; // Using the same styling
import '../css/Dismantling.css'; // Using the same styling
import { apiCall, setTransient } from '../api.js';

const ROWS_PER_PAGE = 50;
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

  // Project-related state
  const [projects, setProjects] = useState([]);
  const [selectedProject, setSelectedProject] = useState('');

  const fetchAbort = useRef(null);

  const initialForm = {
    site_id: '', site_name: '', slot_id: '', port_id: '', status: '',
    company_id: '', mnemonic: '', clei_code: '', part_no: '', software_no: '',
    factory_id: '', serial_no: '', date_id: '', manufactured_date: '',
    customer_field: '', license_points_consumed: '', alarm_status: '',
    Aggregated_alarm_status: '', pid_po: ''
  };
  const [formData, setFormData] = useState(initialForm);

  const fetchProjects = async () => {
    try {
      const data = await apiCall('/get_project');
      setProjects(data || []);
      // Auto-select the first project if available
      if (data && data.length > 0) {
        setSelectedProject(data[0].pid_po);
      }
    } catch (err) {
      setTransient(setError, 'Failed to load projects. Please ensure you have project access.');
      console.error(err);
    }
  };

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

      const data = await apiCall(`/inventory?${params.toString()}`, {
        signal: controller.signal,
        method: 'GET'
      });
      setRows(data.records || []);
      setTotal(data.total || 0);
      setCurrentPage(page);
    } catch (err) {
      if (err.name !== 'AbortError') setTransient(setError, err.message || 'Failed to fetch inventory');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProjects();
    fetchInventory(1, '');
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const onSearchChange = (e) => {
    const v = e.target.value;
    setSearchTerm(v);
    fetchInventory(1, v);
  };

  const openCreateForm = () => {
    // Validate project selection
    if (!selectedProject) {
      setTransient(setError, 'Please select a project to create a new inventory.');
      return;
    }

    setFormData({
      ...initialForm,
      pid_po: selectedProject
    });
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
      const payload = {
        ...formData,
        slot_id: parseInt(formData.slot_id || 0),
        port_id: parseInt(formData.port_id || 0),
      };

      if (isEditing && editingId !== null) {
        await apiCall(`/update-inventory/${editingId}`, {
          method: 'PUT',
          body: JSON.stringify(payload)
        });
      } else {
        await apiCall('/create-inventory', {
          method: 'POST',
          body: JSON.stringify(payload)
        });
      }

      setTransient(setSuccess, isEditing ? 'Inventory updated' : 'Inventory created');
      setShowForm(false);
      fetchInventory(currentPage, searchTerm);
    } catch (err) {
      setTransient(setError, err.message || 'Operation failed');
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this inventory item?')) return;
    try {
      await apiCall(`/delete-inventory/${id}`, {
        method: 'DELETE'
      });
      setTransient(setSuccess, 'Inventory deleted');
      fetchInventory(currentPage, searchTerm);
    } catch (err) {
      setTransient(setError, err.message || 'Delete failed');
    }
  };

  const handleUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    // Validate project selection
    if (!selectedProject) {
      setTransient(setError, 'Please select a project before uploading CSV.');
      e.target.value = "";
      return;
    }

    setUploading(true);
    setError('');
    setSuccess('');
    const formData = new FormData();
    formData.append("file", file);
    formData.append("pid_po", selectedProject);
    try {
      const result = await apiCall('/upload-inventory-csv', {
        method: "POST",
        body: formData
      });
      setTransient(setSuccess, `Upload successful! ${result.inserted_count} rows inserted.`);
      fetchInventory(1, searchTerm);
    } catch (err) {
      setTransient(setError, err.message);
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
          <button
            className={`stylish-btn ${!selectedProject ? 'disabled' : ''}`}
            onClick={openCreateForm}
            disabled={!selectedProject}
            title={!selectedProject ? "Select a project first" : "Create a new inventory"}
          >
            + New Inventory
          </button>
          <label
            className={`upload-btn ${uploading || !selectedProject ? 'disabled' : ''}`}
            title={!selectedProject ? "Select a project first" : "Upload inventory CSV"}
          >
            📤 Upload CSV
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

      <div className="dismantling-search-container">
      <input
          type="text"
          placeholder="Search by Site ID..."
          value={searchTerm}
          onChange={onSearchChange}
          className="search-input"
        />
        <select
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
                name="pid_po"
                placeholder="Project ID (pid_po)"
                value={formData.pid_po}
                onChange={handleChange}
                required
                disabled={true}
                style={{ backgroundColor: '#f5f5f5', cursor: 'not-allowed' }}
              />
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