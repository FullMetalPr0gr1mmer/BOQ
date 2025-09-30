import React, { useEffect, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { apiCall, setTransient } from '../api.js';
import '../css/RopLvl2.css';
const ENTRIES_PER_PAGE = 5;

export default function RopLvl2() {
  const location = useLocation();
  const lvl1State = location.state; // { lvl1_id, lvl1_item_name, pid_po, project_name }

  const [entries, setEntries] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [editId, setEditId] = useState(null);
  const [distributions, setDistributions] = useState([]);
  const [formData, setFormData] = useState({
    project_id: lvl1State?.pid_po || '',
    project_name: lvl1State?.project_name || '',
    lvl1_id: lvl1State?.lvl1_id || 0,
    lvl1_item_name: lvl1State?.lvl1_item_name || '',
    item_name: '',
    region: '',
    total_quantity: 0,
    price: 0,
    start_date: '',
    end_date: '',
  });
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [showGeneralRop, setShowGeneralRop] = useState(false);
  const [showLE, setShowLE] = useState(false);
  const [showTableView, setShowTableView] = useState(false);

  useEffect(() => {
    fetchEntries();
  }, []);

  const fetchEntries = async () => {
    try {
      const endpoint = formData.lvl1_id
        ? `/rop-lvl2/by-lvl1/${formData.lvl1_id}`
        : `/rop-lvl2/`;
      const data = await apiCall(endpoint);
      setEntries(data);
    } catch (err) {
      setTransient(setError, err.message || 'Failed to fetch ROP Lvl2 entries');
    }
  };

  const resetForm = () => {
    setFormData({
      project_id: lvl1State?.pid_po || '',
      project_name: lvl1State?.project_name || '',
      lvl1_id: lvl1State?.lvl1_id || 0,
      lvl1_item_name: lvl1State?.lvl1_item_name || '',
      item_name: '',
      region: '',
      total_quantity: 0,
      price: 0,
      start_date: '',
      end_date: '',
    });
    setDistributions([]);
    setEditId(null);
    setIsEditing(false);
    setShowForm(false);
  };

  // Generate month-year pairs for distribution table
  const generateDistributionTable = (start, end) => {
    const table = [];
    let current = new Date(start.getFullYear(), start.getMonth(), 1);
    const endDate = new Date(end.getFullYear(), end.getMonth(), 1);

    while (current <= endDate) {
      table.push({ month: current.getMonth() + 1, year: current.getFullYear(), allocated_quantity: 0 });
      current.setMonth(current.getMonth() + 1);
    }
    return table;
  };

  useEffect(() => {
    if (formData.start_date && formData.end_date) {
      const start = new Date(formData.start_date);
      const end = new Date(formData.end_date);
      if (start <= end) {
        setDistributions(generateDistributionTable(start, end));
      } else {
        setDistributions([]);
      }
    } else {
      setDistributions([]);
    }
  }, [formData.start_date, formData.end_date]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    // Basic validation
    if (!formData.start_date || !formData.end_date) {
      setTransient(setError, 'Start date and end date are required');
      return;
    }
    if (new Date(formData.start_date) > new Date(formData.end_date)) {
      setTransient(setError, 'Start date cannot be after end date');
      return;
    }

    // Prepare payload with explicit type conversions
    const payload = {
      project_id: formData.project_id,
      lvl1_id: Number(formData.lvl1_id),
      lvl1_item_name: formData.lvl1_item_name,
      item_name: formData.item_name,
      region: formData.region || null,
      total_quantity: Number(formData.total_quantity) || 0,
      price: Number(formData.price) || 0,
      start_date: formData.start_date,
      end_date: formData.end_date,
      distributions: distributions.map(d => ({
        month: Number(d.month),
        year: Number(d.year),
        allocated_quantity: Number(d.allocated_quantity) || 0
      }))
    };

    console.log('Submitting payload:', payload);

    try {
      const endpoint = isEditing && editId
        ? `/rop-lvl2/update/${editId}`
        : `/rop-lvl2/create`;

      await apiCall(endpoint, {
        method: isEditing ? 'PUT' : 'POST',
        body: JSON.stringify(payload)
      });

      setTransient(setSuccess, isEditing ? 'ROP Lvl2 updated successfully!' : 'ROP Lvl2 created successfully!');
      resetForm();
      fetchEntries();
    } catch (err) {
      console.error('Error submitting:', err);
      setTransient(setError, err.message || 'Failed to save entry');
    }
  };

  const handleEdit = (entry) => {
    setIsEditing(true);
    setEditId(entry.id);
    setFormData({
      project_id: entry.project_id,
      lvl1_id: Number(entry.lvl1_id),
      lvl1_item_name: entry.lvl1_item_name,
      item_name: entry.item_name,
      region: entry.region || '',
      total_quantity: Number(entry.total_quantity) || 0,
      price: Number(entry.price) || 0,
      start_date: entry.start_date || '',
      end_date: entry.end_date || '',
    });
    setDistributions(entry.distributions?.map(d => ({
      month: Number(d.month),
      year: Number(d.year),
      allocated_quantity: Number(d.allocated_quantity) || 0
    })) || []);
    setShowForm(true);
    setSuccess('');
    setError('');
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Are you sure you want to delete this entry?')) return;
    try {
      await apiCall(`/rop-lvl2/${id}`, { method: 'DELETE' });
      setEntries(entries.filter((e) => e.id !== id));
      setTransient(setSuccess, 'Entry deleted successfully!');
    } catch (err) {
      setTransient(setError, err.message || 'Failed to delete entry');
    }
  };

  const paginatedEntries = entries.slice(
    (currentPage - 1) * ENTRIES_PER_PAGE,
    currentPage * ENTRIES_PER_PAGE
  );
  const totalPages = Math.ceil(entries.length / ENTRIES_PER_PAGE);

  // Statistics
  const totalItems = entries.length;
  const totalQuantity = entries.reduce((sum, e) => sum + (e.total_quantity || 0), 0);
  const totalLE = entries.reduce((sum, e) => sum + ((e.total_quantity || 0) * (e.price || 0)), 0);
  const avgQuantityPerItem = totalItems > 0 ? Math.round(totalQuantity / totalItems) : 0;
  const avgLEPerItem = totalItems > 0 ? Math.round(totalLE / totalItems) : 0;
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

  // Distribution columns: get all months from earliestStart to latestEnd
  let distributionColumns = [];
  if (earliestStart && latestEnd) {
    let current = new Date(earliestStart.getFullYear(), earliestStart.getMonth(), 1);
    const endDate = new Date(latestEnd.getFullYear(), latestEnd.getMonth(), 1);
    while (current <= endDate) {
      distributionColumns.push({
        month: current.getMonth() + 1,
        year: current.getFullYear(),
        label: `${current.toLocaleString('default', { month: 'short' })} ${current.getFullYear()}`
      });
      current.setMonth(current.getMonth() + 1);
    }
  }

  // Track distribution edits per row
  const [editedDistributions, setEditedDistributions] = useState({});
  const [showSaveRow, setShowSaveRow] = useState({});

  // Handle distribution cell edit
  const handleDistributionEdit = (entryId, month, year, value) => {
    setEditedDistributions(prev => {
      const prevEntry = prev[entryId] || {};
      return {
        ...prev,
        [entryId]: {
          ...prevEntry,
          [`${year}-${month}`]: value
        }
      };
    });
    setShowSaveRow(prev => ({ ...prev, [entryId]: true }));
  };

  // Save distribution changes for a row
  const handleSaveDistributions = async (entry) => {
    const changes = editedDistributions[entry.id] || {};
    // Only include months that actually exist for this item
    const newDistributions = (entry.distributions || []).map(orig => {
      const key = `${orig.year}-${orig.month}`;
      return {
        month: orig.month,
        year: orig.year,
        allocated_quantity: changes.hasOwnProperty(key)
          ? Number(changes[key]) || 0
          : orig.allocated_quantity
      };
    });
    try {
      await apiCall(`/rop-lvl2/update/${entry.id}`, {
        method: 'PUT',
        body: JSON.stringify({ ...entry, distributions: newDistributions })
      });
      setTransient(setSuccess, 'Distributions updated!');
      setEditedDistributions(prev => ({ ...prev, [entry.id]: {} }));
      setShowSaveRow(prev => ({ ...prev, [entry.id]: false }));
      fetchEntries();
    } catch (err) {
      setTransient(setError, err.message || 'Failed to save distributions');
    }
  };

  const stats = [
    { label: 'Total Items', value: totalItems },
    { label: 'Total Quantity', value: totalQuantity.toLocaleString() },
    { label: 'Total LE', value: `$${totalLE.toLocaleString()}` },
    { label: 'Avg Quantity per Item', value: avgQuantityPerItem.toLocaleString() },
    { label: 'Highest LE Item', value: highestLEItem.item_name || '-', extra: highestLEItem.le ? `$${highestLEItem.le.toLocaleString()}` : '' },
    { label: 'Earliest Start', value: earliestStart ? earliestStart.toLocaleDateString() : '-' },
    { label: 'Latest End', value: latestEnd ? latestEnd.toLocaleDateString() : '-' },
  ];

  return (
    <div className="nokia-dashboard">
      {/* Header */}
      <div className="dashboard-header">
        <div className="header-left">
          <h1>ROP Level 2 Dashboard</h1>
          <div className="breadcrumb">
            <span>Projects</span> / <span>Level 1</span> / <span className="active">Level 2</span>
          </div>
        </div>
        <div className="header-actions">
          <button className="nokia-btn primary" onClick={() => { resetForm(); setShowForm(!showForm); }}>
            {showForm ? 'Cancel' : '+ New Entry'}
          </button>
          <button className="nokia-btn secondary" onClick={() => setShowGeneralRop(true)}>
            Generate ROP
          </button>
          <button className="nokia-btn secondary" onClick={() => setShowLE(true)}>
            Generate LE
          </button>
        </div>
      </div>

      {/* Project Context Cards */}
      <div className="project-context">
        <div className="context-card primary">
          <div className="context-label">Project ID</div>
          <div className="context-value">{formData.project_id}</div>
        </div>
        <div className="context-card">
          <div className="context-label">Project Name</div>
          <div className="context-value">{formData.project_name}</div>
        </div>
        <div className="context-card">
          <div className="context-label">Level 1 ID</div>
          <div className="context-value">{formData.lvl1_id}</div>
        </div>
        <div className="context-card">
          <div className="context-label">Level 1 Item</div>
          <div className="context-value">{formData.lvl1_item_name}</div>
        </div>
      </div>

      {/* Statistics Grid */}
      <div className="stats-grid">
        {stats.map((stat, idx) => (
          <div key={idx} className="stat-card">
            <div className="stat-value">{stat.value}</div>
            {stat.extra && <div className="stat-extra">{stat.extra}</div>}
            <div className="stat-label">{stat.label}</div>
          </div>
        ))}
      </div>

      {/* Generate ROP Modal */}
      {showGeneralRop && (
        <div className="modal-overlay">
          <div className="modal-container">
            <div className="modal-header">
              <h3>ROP Table</h3>
              <button className="close-btn" onClick={() => setShowGeneralRop(false)}>×</button>
            </div>
            <div className="modal-content">
              {(() => {
                const regions = Array.from(new Set(entries.map(e => e.region || '')));
                let months = [];
                if (earliestStart && latestEnd) {
                  let current = new Date(earliestStart.getFullYear(), earliestStart.getMonth(), 1);
                  const endDate = new Date(latestEnd.getFullYear(), latestEnd.getMonth(), 1);
                  while (current <= endDate) {
                    months.push({
                      month: current.getMonth() + 1,
                      year: current.getFullYear(),
                      label: `${current.toLocaleString('default', { month: 'short' })} ${current.getFullYear()}`
                    });
                    current.setMonth(current.getMonth() + 1);
                  }
                }
                const monthTotals = months.map(m => {
                  let total = 0;
                  entries.forEach(item => {
                    const dist = (item.distributions || []).find(d => d.month === m.month && d.year === m.year);
                    total += dist ? dist.allocated_quantity : 0;
                  });
                  return total;
                });
                return (
                  <>
                    <div className="table-container">
                      <table className="nokia-table">
                        <thead>
                          <tr>
                            <th>Region</th>
                            <th>Level 2 Item</th>
                            {months.map(m => (
                              <th key={m.label}>{m.label}</th>
                            ))}
                            <th>Total</th>
                          </tr>
                        </thead>
                        <tbody>
                          {regions.map(region => (
                            <React.Fragment key={region}>
                              <tr className="region-header">
                                <td colSpan={2 + months.length + 1}>{region || 'No Region'}</td>
                              </tr>
                              {entries.filter(e => (e.region || '') === region).map(item => (
                                <tr key={item.id}>
                                  <td></td>
                                  <td>{item.item_name}</td>
                                  {months.map(m => {
                                    const dist = (item.distributions || []).find(d => d.month === m.month && d.year === m.year);
                                    return (
                                      <td key={m.label}>{dist ? dist.allocated_quantity : '-'}</td>
                                    );
                                  })}
                                  <td className="total-cell">{item.total_quantity?.toLocaleString() || '-'}</td>
                                </tr>
                              ))}
                            </React.Fragment>
                          ))}
                          <tr className="totals-row">
                            <td colSpan={2}>Total</td>
                            {monthTotals.map((total, idx) => (
                              <td key={idx}>{total}</td>
                            ))}
                            <td></td>
                          </tr>
                        </tbody>
                      </table>
                    </div>
                    <div className="modal-actions">
                      <button className="nokia-btn danger" onClick={() => setShowGeneralRop(false)}>Close</button>
                      <button className="nokia-btn primary" onClick={() => {
                        let csv = '';
                        csv += 'Region,Level 2 Item,' + months.map(m => m.label).join(',') + ',Total\n';
                        regions.forEach(region => {
                          entries.filter(e => (e.region || '') === region).forEach(item => {
                            let row = [region || 'No Region', item.item_name];
                            months.forEach(m => {
                              const dist = (item.distributions || []).find(d => d.month === m.month && d.year === m.year);
                              row.push(dist ? dist.allocated_quantity : '-');
                            });
                            row.push(item.total_quantity?.toLocaleString() || '-');
                            csv += row.join(',') + '\n';
                          });
                        });
                        let totalRow = ['Total', ''];
                        monthTotals.forEach(t => totalRow.push(t));
                        totalRow.push('');
                        csv += totalRow.join(',') + '\n';
                        const blob = new Blob([csv], { type: 'text/csv' });
                        const url = URL.createObjectURL(blob);
                        const a = document.createElement('a');
                        a.href = url;
                        a.download = 'rop_table.csv';
                        document.body.appendChild(a);
                        a.click();
                        document.body.removeChild(a);
                        URL.revokeObjectURL(url);
                      }}>Download CSV</button>
                    </div>
                  </>
                );
              })()}
            </div>
          </div>
        </div>
      )}

      {/* Generate LE Modal */}
      {showLE && (
        <div className="modal-overlay">
          <div className="modal-container">
            <div className="modal-header">
              <h3>LE Table (Values × Price)</h3>
              <button className="close-btn" onClick={() => setShowLE(false)}>×</button>
            </div>
            <div className="modal-content">
              {(() => {
                const regions = Array.from(new Set(entries.map(e => e.region || '')));
                let months = [];
                if (earliestStart && latestEnd) {
                  let current = new Date(earliestStart.getFullYear(), earliestStart.getMonth(), 1);
                  const endDate = new Date(latestEnd.getFullYear(), latestEnd.getMonth(), 1);
                  while (current <= endDate) {
                    months.push({
                      month: current.getMonth() + 1,
                      year: current.getFullYear(),
                      label: `${current.toLocaleString('default', { month: 'short' })} ${current.getFullYear()}`
                    });
                    current.setMonth(current.getMonth() + 1);
                  }
                }
                const monthTotals = months.map(m => {
                  let total = 0;
                  entries.forEach(item => {
                    const dist = (item.distributions || []).find(d => d.month === m.month && d.year === m.year);
                    total += dist ? (dist.allocated_quantity * (item.price || 0)) : 0;
                  });
                  return total;
                });
                return (
                  <>
                    <div className="table-container">
                      <table className="nokia-table">
                        <thead>
                          <tr>
                            <th>Region</th>
                            <th>Level 2 Item</th>
                            {months.map(m => (
                              <th key={m.label}>{m.label}</th>
                            ))}
                            <th>Total</th>
                          </tr>
                        </thead>
                        <tbody>
                          {regions.map(region => (
                            <React.Fragment key={region}>
                              <tr className="region-header">
                                <td colSpan={2 + months.length + 1}>{region || 'No Region'}</td>
                              </tr>
                              {entries.filter(e => (e.region || '') === region).map(item => (
                                <tr key={item.id}>
                                  <td></td>
                                  <td>{item.item_name}</td>
                                  {months.map(m => {
                                    const dist = (item.distributions || []).find(d => d.month === m.month && d.year === m.year);
                                    return (
                                      <td key={m.label}>{dist ? (dist.allocated_quantity * (item.price || 0)).toLocaleString() : '-'}</td>
                                    );
                                  })}
                                  <td className="total-cell">{((item.total_quantity || 0) * (item.price || 0)).toLocaleString() || '-'}</td>
                                </tr>
                              ))}
                            </React.Fragment>
                          ))}
                          <tr className="totals-row">
                            <td colSpan={2}>Total</td>
                            {monthTotals.map((total, idx) => (
                              <td key={idx}>{total.toLocaleString()}</td>
                            ))}
                            <td></td>
                          </tr>
                        </tbody>
                      </table>
                    </div>
                    <div className="modal-actions">
                      <button className="nokia-btn danger" onClick={() => setShowLE(false)}>Close</button>
                      <button className="nokia-btn primary" onClick={() => {
                        let csv = '';
                        csv += 'Region,Level 2 Item,' + months.map(m => m.label).join(',') + ',Total\n';
                        regions.forEach(region => {
                          entries.filter(e => (e.region || '') === region).forEach(item => {
                            let row = [region || 'No Region', item.item_name];
                            months.forEach(m => {
                              const dist = (item.distributions || []).find(d => d.month === m.month && d.year === m.year);
                              row.push(dist ? (dist.allocated_quantity * (item.price || 0)) : '-');
                            });
                            row.push(((item.total_quantity || 0) * (item.price || 0)).toLocaleString() || '-');
                            csv += row.join(',') + '\n';
                          });
                        });
                        let totalRow = ['Total', ''];
                        monthTotals.forEach(t => totalRow.push(t));
                        totalRow.push('');
                        csv += totalRow.join(',') + '\n';
                        const blob = new Blob([csv], { type: 'text/csv' });
                        const url = URL.createObjectURL(blob);
                        const a = document.createElement('a');
                        a.href = url;
                        a.download = 'le_table.csv';
                        document.body.appendChild(a);
                        a.click();
                        document.body.removeChild(a);
                        URL.revokeObjectURL(url);
                      }}>Download CSV</button>
                    </div>
                  </>
                );
              })()}
            </div>
          </div>
        </div>
      )}

      {/* Form Modal */}
      {showForm && (
        <div className="modal-overlay">
          <div className="form-modal">
            <div className="modal-header">
              <h3>{isEditing ? 'Edit Entry' : 'New Entry'}</h3>
              <button className="close-btn" onClick={() => setShowForm(false)}>×</button>
            </div>
            <form className="nokia-form" onSubmit={handleSubmit}>
              <div className="form-row">
                <div className="form-group">
                  <label>Project ID</label>
                  <input type="text" value={formData.project_id} disabled />
                </div>
                <div className="form-group">
                  <label>Level 1 ID</label>
                  <input type="text" value={formData.lvl1_id} disabled />
                </div>
              </div>
              <div className="form-group">
                <label>Level 1 Item Name</label>
                <input type="text" value={formData.lvl1_item_name} disabled />
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label>Item Name *</label>
                  <input type="text" value={formData.item_name}
                    onChange={e => setFormData({ ...formData, item_name: e.target.value })} required />
                </div>
                <div className="form-group">
                  <label>Region</label>
                  <input type="text" value={formData.region}
                    onChange={e => setFormData({ ...formData, region: e.target.value })} />
                </div>
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label>Total Quantity</label>
                  <input type="number" value={formData.total_quantity}
                    onChange={e => setFormData({ ...formData, total_quantity: Number(e.target.value) || 0 })} />
                </div>
                <div className="form-group">
                  <label>Price</label>
                  <input type="number" step="0.01" value={formData.price}
                    onChange={e => setFormData({ ...formData, price: Number(e.target.value) || 0 })} />
                </div>
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label>Start Date</label>
                  <input type="date" value={formData.start_date}
                    onChange={e => setFormData({ ...formData, start_date: e.target.value })} />
                </div>
                <div className="form-group">
                  <label>End Date</label>
                  <input type="date" value={formData.end_date}
                    onChange={e => setFormData({ ...formData, end_date: e.target.value })} />
                </div>
              </div>

              {/* Dynamic Distribution Table */}
              {distributions.length > 0 && (
                <div className="distribution-section">
                  <h4>Distribution Schedule</h4>
                  <div className="table-container">
                    <table className="nokia-table">
                      <thead>
                        <tr>
                          <th>Month</th>
                          <th>Year</th>
                          <th>Allocated Quantity</th>
                        </tr>
                      </thead>
                      <tbody>
                        {distributions.map((dist, idx) => (
                          <tr key={idx}>
                            <td>{dist.month}</td>
                            <td>{dist.year}</td>
                            <td>
                              <input
                                type="number"
                                value={dist.allocated_quantity}
                                onChange={e => {
                                  const newDists = [...distributions];
                                  newDists[idx].allocated_quantity = Number(e.target.value) || 0;
                                  setDistributions(newDists);
                                }}
                                className="table-input"
                              />
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              <button type="submit" className="nokia-btn primary full-width">
                {isEditing ? 'Update Entry' : 'Create Entry'}
              </button>
            </form>
          </div>
        </div>
      )}

      {/* Notifications */}
      {error && <div className="notification error">{error}</div>}
      {success && <div className="notification success">{success}</div>}

      {/* Main Data Table */}
      <div className="data-section">
        <div className="section-header">
          <h3>Entries</h3>
          <div className="table-info">
            Showing {paginatedEntries.length} of {entries.length} entries
          </div>
        </div>
        
        <div className="table-container">
          <table className="nokia-table main-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Item Name</th>
                <th>Product Number</th>
                <th>Region</th>
                <th>Quantity</th>
                <th>Price</th>
                <th>Total Price</th>
                {/* Distribution columns */}
                {distributionColumns.map(col => (
                  <th key={col.label} className="dist-col">{col.label}</th>
                ))}
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {paginatedEntries.map(entry => (
                <React.Fragment key={entry.id}>
                  <tr>
                    <td className="id-cell">{entry.id}</td>
                    <td className="item-name">{entry.item_name}</td>
                    <td>{entry.product_number || '-'}</td>
                    <td>{entry.region || '-'}</td>
                    <td className="number-cell">{entry.total_quantity?.toLocaleString() || '-'}</td>
                    <td className="number-cell">${entry.price?.toFixed(2) || '0.00'}</td>
                    <td className="number-cell total">${((entry.total_quantity || 0) * (entry.price || 0)).toLocaleString()}</td>
                    {/* Distribution cells */}
                    {distributionColumns.map(col => {
                      const orig = (entry.distributions || []).find(d => d.month === col.month && d.year === col.year);
                      const key = `${col.year}-${col.month}`;
                      if (!orig) {
                        return (
                          <td key={key} className="dist-cell empty">-</td>
                        );
                      }
                      const value = editedDistributions[entry.id]?.[key] ?? orig.allocated_quantity;
                      return (
                        <td key={key} className="dist-cell">
                          <input
                            type="number"
                            value={value !== undefined ? value : ''}
                            className="dist-input"
                            onChange={e => handleDistributionEdit(entry.id, col.month, col.year, e.target.value)}
                          />
                        </td>
                      );
                    })}
                    <td className="actions-cell">
                      <button className="nokia-btn small secondary" onClick={() => handleEdit(entry)}>
                        Edit
                      </button>
                      <button className="nokia-btn small danger" onClick={() => handleDelete(entry.id)}>
                        Delete
                      </button>
                    </td>
                  </tr>
                  {/* Save button row */}
                  {showSaveRow[entry.id] && (
                    <tr className="save-row">
                      <td colSpan={7 + distributionColumns.length}>
                        <button className="nokia-btn small primary" onClick={() => handleSaveDistributions(entry)}>
                          Save Distribution Changes
                        </button>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              ))}
              {entries.length === 0 && (
                <tr className="empty-row">
                  <td colSpan={7 + distributionColumns.length}>
                    <div className="empty-state">
                      <div className="empty-icon">📊</div>
                      <div className="empty-text">No entries found</div>
                      <div className="empty-subtext">Click "New Entry" to create your first entry</div>
                    </div>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="pagination">
            <button 
              className="page-btn"
              disabled={currentPage === 1}
              onClick={() => setCurrentPage(currentPage - 1)}
            >
              Previous
            </button>
            {Array.from({ length: totalPages }, (_, i) => (
              <button
                key={i}
                className={`page-btn ${i + 1 === currentPage ? 'active' : ''}`}
                onClick={() => setCurrentPage(i + 1)}
              >
                {i + 1}
              </button>
            ))}
            <button 
              className="page-btn"
              disabled={currentPage === totalPages}
              onClick={() => setCurrentPage(currentPage + 1)}
            >
              Next
            </button>
          </div>
        )}
      </div>
    </div>
  );
}