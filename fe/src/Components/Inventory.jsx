import React, { useEffect, useState } from 'react';
import '../css/Project.css';

const INVENTORY_PER_PAGE = 5;

export default function Inventory() {
  const [inventory, setInventory] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [editingId, setEditingId] = useState(null);

  const initialForm = {
    site_id: '', site_name: '', slot_id: '', port_id: '', status: '',
    company_id: '', mnemonic: '', clei_code: '', part_no: '', software_no: '',
    factory_id: '', serial_no: '', date_id: '', manufactured_date: '',
    customer_field: '', license_points_consumed: '', alarm_status: '',
    Aggregated_alarm_status: ''
  };

  const [formData, setFormData] = useState(initialForm);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [currentPage, setCurrentPage] = useState(1);

  const VITE_API_URL = import.meta.env.VITE_API_URL;

  useEffect(() => {
    fetchInventory();
  }, []);

  const fetchInventory = async () => {
    try {
      const res = await fetch(`${VITE_API_URL}/inventory`);
      if (!res.ok) throw new Error('Failed to fetch inventory');
      const data = await res.json();
      setInventory(data);
    } catch (err) {
      setError(err.message || 'Failed to fetch inventory');
    }
  };

  const openCreateForm = () => {
    setFormData(initialForm);
    setIsEditing(false);
    setEditingId(null);
    setShowForm(true);
  };

  const openEditForm = (item) => {
    // ensure we convert numbers to strings for inputs
    setFormData({
      site_id: item.site_id ?? '',
      site_name: item.site_name ?? '',
      slot_id: item.slot_id ?? '',
      port_id: item.port_id ?? '',
      status: item.status ?? '',
      company_id: item.company_id ?? '',
      mnemonic: item.mnemonic ?? '',
      clei_code: item.clei_code ?? '',
      part_no: item.part_no ?? '',
      software_no: item.software_no ?? '',
      factory_id: item.factory_id ?? '',
      serial_no: item.serial_no ?? '',
      date_id: item.date_id ?? '',
      manufactured_date: item.manufactured_date ?? '',
      customer_field: item.customer_field ?? '',
      license_points_consumed: item.license_points_consumed ?? '',
      alarm_status: item.alarm_status ?? '',
      Aggregated_alarm_status: item.Aggregated_alarm_status ?? ''
    });
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
      if (isEditing && editingId !== null) {
        res = await fetch(`${VITE_API_URL}/update-inventory/${editingId}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            ...formData,
            slot_id: parseInt(formData.slot_id || 0),
            port_id: parseInt(formData.port_id || 0)
          })
        });
      } else {
        res = await fetch(`${VITE_API_URL}/create-inventory`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            ...formData,
            slot_id: parseInt(formData.slot_id || 0),
            port_id: parseInt(formData.port_id || 0)
          })
        });
      }

      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || 'Failed to save inventory');
      }

      setSuccess(isEditing ? 'Inventory updated' : 'Inventory created');
      setShowForm(false);
      fetchInventory();
    } catch (err) {
      setError(err.message || 'Operation failed');
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this inventory item?')) return;
    try {
      const res = await fetch(`${VITE_API_URL}/delete-inventory/${id}`, {
        method: 'DELETE'
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || 'Failed to delete inventory');
      }
      setSuccess('Inventory deleted');
      fetchInventory();
    } catch (err) {
      setError(err.message || 'Delete failed');
    }
  };

  const paginatedInventory = inventory.slice(
    (currentPage - 1) * INVENTORY_PER_PAGE,
    currentPage * INVENTORY_PER_PAGE
  );
  const totalPages = Math.ceil(inventory.length / INVENTORY_PER_PAGE);

  return (
    <div className="project-container">
      <div className="header-row">
        <h2>Inventory</h2>
        <button className="new-project-btn" onClick={openCreateForm}>+ New Inventory</button>
      </div>

      {showForm && (
        <div style={{
          position: 'fixed', top: 0, left: 0, width: '100vw', height: '100vh',
          background: 'rgba(0,0,0,0.3)', display: 'flex', alignItems: 'center',
          justifyContent: 'center', zIndex: 1000
        }}>
          <div style={{
            background: '#fff', borderRadius: '12px', padding: '1rem', minWidth: '640px',
            boxShadow: '0 6px 30px rgba(0,0,0,0.2)', maxHeight: '85vh', overflowY: 'auto'
          }}>
            <form className="project-form" onSubmit={handleSubmit}>
              <div>
                <button className="stylish-btn danger" style={{ width: 'fit-content', padding: '0.4rem', float: 'right' }} onClick={() => setShowForm(false)} type="button">X</button>
              </div>

              {Object.keys(initialForm).map((key) => (
                <input
                  key={key}
                  type={['slot_id', 'port_id'].includes(key) ? 'number' : 'text'}
                  name={key}
                  placeholder={key.replace(/_/g, ' ')}
                  value={formData[key] ?? ''}
                  onChange={handleChange}
                  required
                  disabled={isEditing && key === 'site_id'} // site_id not editable when editing
                />
              ))}

              <button type="submit" style={{ width: '100%' }} className="stylish-btn">
                {isEditing ? 'Update Inventory' : 'Create Inventory'}
              </button>
            </form>
          </div>
        </div>
      )}

      {error && <div className="error">{error}</div>}
      {success && <div className="success">{success}</div>}

      <div className="project-table-container">
        <table className="project-table">
          <thead>
            <tr>
              <th>ID</th>
              {Object.keys(initialForm).map((key) => <th key={key}>{key.replace(/_/g, ' ')}</th>)}
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {paginatedInventory.map(item => (
              <tr key={item.id}>
                <td>{item.id}</td>
                {Object.keys(initialForm).map(key => <td key={key}>{item[key]}</td>)}
                <td style={{ textAlign: 'center' }}>
                  <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'center' }}>
                    <button
                      className="stylish-btn"
                      style={{ width: '46%' }}
                      onClick={() => openEditForm(item)}
                    >
                      Details
                    </button>
                    <button
                      className="stylish-btn danger"
                      style={{ width: '46%' }}
                      onClick={() => handleDelete(item.id)}
                    >
                      Delete
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div className="pagination">
          {Array.from({ length: totalPages }, (_, i) => (
            <button key={i} className={i + 1 === currentPage ? 'active-page' : ''} onClick={() => setCurrentPage(i + 1)}>
              {i + 1}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
