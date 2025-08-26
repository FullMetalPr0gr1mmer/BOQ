import { useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import '../css/RopLvl1.css';

const ENTRIES_PER_PAGE = 15;
const VITE_API_URL = import.meta.env.VITE_API_URL;

export default function RopLvl1() {
  const location = useLocation();
  const navigate = useNavigate();
  const projectState = location.state; // { pid_po, project_name }

  const [entries, setEntries] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [editId, setEditId] = useState(null);
  const [formData, setFormData] = useState({
    project_id: projectState?.pid_po || '',
    project_name: projectState?.project_name || '',
    item_name: '',
    region: '',
    total_quantity: '',
    price: '',
    start_date: '',
    end_date: '',
  });

  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [expandedRows, setExpandedRows] = useState({});
  const [lvl2Items, setLvl2Items] = useState({});

  useEffect(() => {
    fetchEntries();
  }, []);

  const fetchEntries = async () => {
    try {
      const url = projectState?.pid_po
        ? `${VITE_API_URL}/rop-lvl1/by-project/${projectState.pid_po}`
        : `${VITE_API_URL}/rop-lvl1/`;
      const res = await fetch(url);
      const data = await res.json();
      setEntries(data);
    } catch {
      setError('Failed to fetch ROP Lvl1 entries');
    }
  };

  const fetchLvl2Items = async (lvl1_id) => {
    try {
      const res = await fetch(`${VITE_API_URL}/rop-lvl2/by-lvl1/${lvl1_id}`);
      if (!res.ok) throw new Error('Failed to fetch Level 2 items');
      const data = await res.json();
      setLvl2Items(prev => ({ ...prev, [lvl1_id]: data }));
    } catch (err) {
      setLvl2Items(prev => ({ ...prev, [lvl1_id]: [] }));
    }
  };

  const resetForm = () => {
    setFormData({
      project_id: projectState?.pid_po || '',
      project_name: projectState?.project_name || '',
      item_name: '',
      region: '',
      total_quantity: '',
      price: '',
      start_date: '',
      end_date: '',
    });
    setEditId(null);
    setIsEditing(false);
    setShowForm(false);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    const payload = {
      project_id: formData.project_id,
      project_name: formData.project_name,
      item_name: formData.item_name,
      region: formData.region || null,
      total_quantity: formData.total_quantity ? parseInt(formData.total_quantity) : null,
      price: formData.price ? parseFloat(formData.price) : null,
      start_date: formData.start_date || null,
      end_date: formData.end_date || null,
    };

    try {
      let res;
      if (isEditing && editId !== null) {
        res = await fetch(`${VITE_API_URL}/rop-lvl1/update/${editId}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
      } else {
        res = await fetch(`${VITE_API_URL}/rop-lvl1/create`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
      }

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Failed to save entry');
      }

      setSuccess(isEditing ? 'ROP Lvl1 updated successfully!' : 'ROP Lvl1 created successfully!');
      resetForm();
      fetchEntries();
    } catch (err) {
      setError(err.message);
    }
  };

  const handleEdit = (entry) => {
    setIsEditing(true);
    setEditId(entry.id);
    setFormData({
      project_id: entry.project_id,
      project_name: entry.project_name,
      item_name: entry.item_name,
      region: entry.region || '',
      total_quantity: entry.total_quantity || '',
      price: entry.price || '',
      start_date: entry.start_date || '',
      end_date: entry.end_date || '',
    });
    setShowForm(true);
    setSuccess('');
    setError('');
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Are you sure you want to delete this entry?')) return;

    try {
      const res = await fetch(`${VITE_API_URL}/rop-lvl1/${id}`, { method: 'DELETE' });
      if (!res.ok) throw new Error('Failed to delete entry');
      setEntries(entries.filter((e) => e.id !== id));
      setSuccess('Entry deleted successfully!');
    } catch (err) {
      setError(err.message);
    }
  };

  const paginatedEntries = entries.slice(
    (currentPage - 1) * ENTRIES_PER_PAGE,
    currentPage * ENTRIES_PER_PAGE
  );
  const totalPages = Math.ceil(entries.length / ENTRIES_PER_PAGE);

  // Statistics calculations
  const totalItems = entries.length;
  const totalQuantity = entries.reduce((sum, e) => sum + (e.total_quantity || 0), 0);
  const totalLE = entries.reduce((sum, e) => sum + ((e.total_quantity || 0) * (e.price || 0)), 0);
  const avgQuantityPerItem = totalItems > 0 ? Math.round(totalQuantity / totalItems) : 0;
  const avgLEPerItem = totalItems > 0 ? Math.round(totalLE / totalItems) : 0;
  const avgPrice = totalItems > 0 ? (entries.reduce((sum, e) => sum + (e.price || 0), 0) / totalItems).toFixed(2) : 0;
  const highestLEItem = entries.reduce((highest, e) => {
    const le = (e.total_quantity || 0) * (e.price || 0);
    return le > (highest.le || 0) ? { ...e, le } : highest;
  }, {});
  const earliestStart = entries
    .filter(e => e.start_date)
    .reduce((earliest, e) => (!earliest || new Date(e.start_date) < earliest ? new Date(e.start_date) : earliest), null);
  const latestEnd = entries
    .filter(e => e.end_date)
    .reduce((latest, e) => (!latest || new Date(e.end_date) > latest ? new Date(e.end_date) : latest), null);

  // Regional distribution
  const regionCounts = entries.reduce((acc, e) => {
    const region = e.region || 'Unknown';
    acc[region] = (acc[region] || 0) + 1;
    return acc;
  }, {});
  const topRegion = Object.entries(regionCounts).reduce((max, [region, count]) => 
    count > max.count ? { region, count } : max, { region: 'None', count: 0 });

  return (
    <div className="dashboard-container">
      {/* Header Section */}
      <div className="dashboard-header">
        <div>
          <h1 className="dashboard-title">ROP Level 1 Analytics</h1>
          <p className="dashboard-subtitle">
            {formData.project_name ? `${formData.project_name} • Project ID: ${formData.project_id}` : 'Project Management Dashboard'}
          </p>
        </div>
        <button className="new-entry-btn" onClick={() => { resetForm(); setShowForm(!showForm); }}>
          {showForm ? '✕ Cancel' : '+ New Package'}
        </button>
      </div>

      {/* Alerts */}
      {error && <div className="dashboard-alert dashboard-alert-error">⚠️ {error}</div>}
      {success && <div className="dashboard-alert dashboard-alert-success">✅ {success}</div>}

      {/* Artistic Stats Grid */}
      <div className="dashboard-stats-container">
        <div className="stats-row">
          <div className="mini-stat-card card-blue">
            <div className="stat-icon">📊</div>
            <div className="mini-stat-value">{totalItems}</div>
            <div className="mini-stat-label">Total Items</div>
          </div>
          
          <div className="mini-stat-card card-cyan">
            <div className="stat-icon">📦</div>
            <div className="mini-stat-value">{totalQuantity.toLocaleString()}</div>
            <div className="mini-stat-label">Total Quantity</div>
          </div>
          
          <div className="mini-stat-card card-success">
            <div className="stat-icon">💰</div>
            <div className="mini-stat-value">{totalLE.toLocaleString()}</div>
            <div className="mini-stat-label">Total Price</div>
          </div>
          
          <div className="mini-stat-card card-warning">
            <div className="stat-icon">📈</div>
            <div className="mini-stat-value">{avgLEPerItem.toLocaleString()}</div>
            <div className="mini-stat-label">Avg LE/Item</div>
          </div>
        </div>

        <div className="stats-row">
          <div className="mini-stat-card card-purple">
            <div className="stat-icon">🎯</div>
            <div className="mini-stat-value">{avgQuantityPerItem.toLocaleString()}</div>
            <div className="mini-stat-label">Avg Qty/Item</div>
          </div>
          
          <div className="mini-stat-card card-teal">
            <div className="stat-icon">💲</div>
            <div className="mini-stat-value">{avgPrice}</div>
            <div className="mini-stat-label">Avg Price</div>
          </div>
          
          <div className="mini-stat-card card-blue">
            <div className="stat-icon">🏆</div>
            <div className="mini-stat-value">{highestLEItem.item_name?.substring(0, 12) || '-'}</div>
            <div className="mini-stat-extra">
              {highestLEItem.le ? `${highestLEItem.le.toLocaleString()} LE` : ''}
            </div>
            <div className="mini-stat-label">Top Item</div>
          </div>
          
          <div className="mini-stat-card card-warning">
            <div className="stat-icon">🌍</div>
            <div className="mini-stat-value">{topRegion.region}</div>
            <div className="mini-stat-extra">{topRegion.count} items</div>
            <div className="mini-stat-label">Top Region</div>
          </div>
        </div>
      </div>

      {/* Chart Dashboard Section */}
      <div className="dashboard-chart-section">
        <div className="chart-card">
          <h3 className="chart-title">📊 Project Overview</h3>
          
          <div className="metric-row">
            <span className="metric-label">Project Progress</span>
            <span className="metric-value">{totalItems} Items</span>
          </div>
          <div className="progress-bar">
            <div className="progress-fill" style={{width: `${Math.min((totalItems / 10) * 100, 100)}%`}}></div>
          </div>
          
          <div className="metric-row">
            <span className="metric-label">Budget Utilization</span>
            <span className="metric-value">{totalLE.toLocaleString()} LE</span>
          </div>
          <div className="progress-bar">
            <div className="progress-fill" style={{width: `${Math.min((totalLE / 100000) * 100, 100)}%`}}></div>
          </div>
          
          <div className="metric-row">
            <span className="metric-label">Quantity Target</span>
            <span className="metric-value">{totalQuantity.toLocaleString()} Units</span>
          </div>
          <div className="progress-bar">
            <div className="progress-fill" style={{width: `${Math.min((totalQuantity / 1000) * 100, 100)}%`}}></div>
          </div>
        </div>

        <div className="chart-card">
          <h3 className="chart-title">📅 Timeline Analysis</h3>
          
          <div className="metric-row">
            <span className="metric-label">Project Start</span>
            <span className="metric-value">
              {earliestStart ? earliestStart.toLocaleDateString() : 'Not Set'}
            </span>
          </div>
          
          <div className="metric-row">
            <span className="metric-label">Project End</span>
            <span className="metric-value">
              {latestEnd ? latestEnd.toLocaleDateString() : 'Not Set'}
            </span>
          </div>
          
          <div className="metric-row">
            <span className="metric-label">Duration</span>
            <span className="metric-value">
              {earliestStart && latestEnd 
                ? `${Math.ceil((latestEnd - earliestStart) / (1000 * 60 * 60 * 24))} days`
                : 'TBD'}
            </span>
          </div>
          
          <div className="metric-row">
            <span className="metric-label">Active Regions</span>
            <span className="metric-value">{Object.keys(regionCounts).length}</span>
          </div>
          
          <div className="metric-row">
            <span className="metric-label">Efficiency Rate</span>
            <span className="metric-value">
              {totalItems > 0 ? `${((totalLE / totalItems) / 1000).toFixed(1)}K LE/Item` : '0'}
            </span>
          </div>
        </div>
      </div>

      {/* Modal Form */}
      {showForm && (
        <div className="dashboard-modal">
          <div className="dashboard-modal-content">
            <div className="dashboard-modal-header">
              <h2 className="dashboard-modal-title">
                {isEditing ? '✏️ Edit Entry' : '✨ Create New Entry'}
              </h2>
              <button
                className="dashboard-modal-close"
                onClick={() => setShowForm(false)}
                type="button"
              >
                ✕
              </button>
            </div>

            <form className="dashboard-form" onSubmit={handleSubmit}>
              <input type="text" placeholder="Project ID" value={formData.project_id} disabled />
              <input type="text" placeholder="Project Name" value={formData.project_name} disabled />
              <input 
                type="text" 
                placeholder="Item Name" 
                value={formData.item_name}
                onChange={e => setFormData({ ...formData, item_name: e.target.value })} 
                required 
              />
              <input 
                type="text" 
                placeholder="Region" 
                value={formData.region}
                onChange={e => setFormData({ ...formData, region: e.target.value })} 
              />
              <input 
                type="number" 
                placeholder="Total Quantity" 
                value={formData.total_quantity}
                onChange={e => setFormData({ ...formData, total_quantity: e.target.value })} 
              />
              <input 
                type="number" 
                step="0.01" 
                placeholder="Price" 
                value={formData.price}
                onChange={e => setFormData({ ...formData, price: e.target.value })} 
              />
              <input 
                type="date" 
                placeholder="Start Date" 
                value={formData.start_date}
                onChange={e => setFormData({ ...formData, start_date: e.target.value })} 
              />
              <input 
                type="date" 
                placeholder="End Date" 
                value={formData.end_date}
                onChange={e => setFormData({ ...formData, end_date: e.target.value })} 
              />

              <button type="submit">
                {isEditing ? '🔄 Update Entry' : '🚀 Create Entry'}
              </button>
            </form>
          </div>
        </div>
      )}

      {/* Data Table Section */}
      <div className="dashboard-content-section">
        <div className="dashboard-section-header">
          📋 Detailed Entry Management
        </div>
        
        <div className="dashboard-table-container">
          {entries.length > 0 ? (
            <table className="dashboard-table">
              <thead>
                <tr>
                  <th></th>
                  <th></th>
                  <th style={{textAlign:'center'}}>ID</th>
                  <th style={{textAlign:'center'}}>Item Name</th>
                  <th style={{textAlign:'center'}}>Product Number</th>
                  <th>Quantity</th>
                  <th>Unit Price</th>
                  <th>Total Price</th>
                                   <th></th>

                </tr>
              </thead>
              <tbody>
                {paginatedEntries.map(entry => (
                  <>
                    <tr key={entry.id}>
                      <td>
                        <button
                          style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: '1.2rem' }}
                          onClick={async () => {
                            setExpandedRows(prev => ({ ...prev, [entry.id]: !prev[entry.id] }));
                            if (!lvl2Items[entry.id]) await fetchLvl2Items(entry.id);
                          }}
                          aria-label={expandedRows[entry.id] ? 'Collapse' : 'Expand'}
                        >
                          {expandedRows[entry.id] ? '▼' : '▶'}
                        </button>
                      </td>
                      <td><strong>#{entry.id}</strong></td>
                      <td><strong>{entry.item_name}</strong></td>
                      <td>{entry.product_number || '-'}</td>
                      <td>{entry.total_quantity?.toLocaleString() || '-'}</td>
                      <td>{entry.price ? `${entry.price.toFixed(2)} LE` : '-'}</td>
                      <td>
                        <strong style={{color: 'var(--nokia-success)'}}>
                          {((entry.total_quantity || 0) * (entry.price || 0)).toLocaleString()} LE
                        </strong>
                      </td>
                    </tr>
                    {expandedRows[entry.id] && (
                      <tr>
                        <td colSpan={7} style={{ background: '#f6f8fc', padding: 0 }}>
                          <div style={{ width: '100%' }}>
                            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                              <thead>
                                <tr>
                                  <th style={{textAlign:'center'}}>ID</th>
                                  <th style={{textAlign:'center'}}>Item Name</th>
                                  <th style={{textAlign:'center'}}>Product Number</th>
                                  <th style={{textAlign:'center'}}>Quantity</th>
                                  <th style={{textAlign:'center'}}>Price</th>
                                  <th style={{textAlign:'center'}}>Total Price</th>
                                </tr>
                              </thead>
                              <tbody>
                                {(lvl2Items[entry.id] || []).map(lvl2 => (
                                  <tr key={lvl2.id}>
                                    <td>{lvl2.id}</td>
                                    <td>{lvl2.item_name}</td>
                                    <td>{lvl2.product_number || '-'}</td>
                                    <td>{lvl2.total_quantity?.toLocaleString() || '-'}</td>
                                    <td>{lvl2.price ? `${lvl2.price.toFixed(2)} LE` : '-'}</td>
                                    <td>{((lvl2.total_quantity || 0) * (lvl2.price || 0)).toLocaleString()} LE</td>
                                  </tr>
                                ))}
                                {(lvl2Items[entry.id] && lvl2Items[entry.id].length === 0) && (
                                  <tr><td colSpan={6} style={{ textAlign: 'center', color: '#888' }}>No Level 2 items found.</td></tr>
                                )}
                              </tbody>
                            </table>
                          </div>
                        </td>
                      </tr>
                    )}
                  </>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="dashboard-empty-state">
              <div className="dashboard-empty-icon">📋</div>
              <div className="dashboard-empty-text">
                No entries found. Create your first entry to get started!
              </div>
            </div>
          )}
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="dashboard-pagination">
            {Array.from({ length: totalPages }, (_, i) => (
              <button
                key={i}
                className={i + 1 === currentPage ? 'active' : ''}
                onClick={() => setCurrentPage(i + 1)}
              >
                {i + 1}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}