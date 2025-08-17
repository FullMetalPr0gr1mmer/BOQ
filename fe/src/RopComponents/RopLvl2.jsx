import React,{ useEffect, useState } from 'react';
import { useLocation } from 'react-router-dom';
import '../css/Project.css';

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

  const VITE_API_URL = import.meta.env.VITE_API_URL;

  useEffect(() => {
    fetchEntries();
  }, []);

  const fetchEntries = async () => {
    try {
      const url = formData.lvl1_id
        ? `${VITE_API_URL}/rop-lvl2/by-lvl1/${formData.lvl1_id}`
        : `${VITE_API_URL}/rop-lvl2/`;
      const res = await fetch(url);
      const data = await res.json();
      setEntries(data);
    } catch {
      setError('Failed to fetch ROP Lvl2 entries');
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
    setError('Start date and end date are required');
    return;
  }
  if (new Date(formData.start_date) > new Date(formData.end_date)) {
    setError('Start date cannot be after end date');
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
    const url = isEditing && editId
      ? `${VITE_API_URL}/rop-lvl2/update/${editId}`
      : `${VITE_API_URL}/rop-lvl2/create`;

    const res = await fetch(url, {
      method: isEditing ? 'PUT' : 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    console.log('Response status:', res.status);

    // Try JSON first, fallback to text
    let data;
    try {
      data = await res.json();
    } catch {
      data = await res.text();
    }
    console.log('Response data:', data);

    if (!res.ok) {
      const message = data?.detail || data || 'Failed to save entry';
      throw new Error(message);
    }

    setSuccess(isEditing ? 'ROP Lvl2 updated successfully!' : 'ROP Lvl2 created successfully!');
    resetForm();
    fetchEntries();
  } catch (err) {
    console.error('Error submitting:', err);
    setError(err.message);
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
      const res = await fetch(`${VITE_API_URL}/rop-lvl2/${id}`, { method: 'DELETE' });
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
      const res = await fetch(`${VITE_API_URL}/rop-lvl2/update/${entry.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...entry, distributions: newDistributions })
      });
      if (!res.ok) throw new Error('Failed to save distributions');
      setSuccess('Distributions updated!');
      setEditedDistributions(prev => ({ ...prev, [entry.id]: {} }));
      setShowSaveRow(prev => ({ ...prev, [entry.id]: false }));
      fetchEntries();
    } catch (err) {
      setError(err.message);
    }
  };

  const stats = [
    { label: 'Total Items', value: totalItems },
    { label: 'Total Quantity', value: totalQuantity },
    { label: 'Total LE', value: totalLE },
    { label: 'Avg Quantity per Item', value: avgQuantityPerItem },
    { label: 'Highest LE Item', value: highestLEItem.item_name || '-', extra: highestLEItem.le?.toLocaleString() },
    { label: 'Earliest Start', value: earliestStart ? earliestStart.toLocaleDateString() : '-' },
    { label: 'Latest End', value: latestEnd ? latestEnd.toLocaleDateString() : '-' },
  ];

  return (
    <div className="project-container">
      {/* Header */}
      <div className="header-row">
        <h2>ROP Level 2</h2>
        <div style={{ display: 'flex', gap: '1rem' }}>
          <button className="new-project-btn" onClick={() => { resetForm(); setShowForm(!showForm); }}>
            {showForm ? 'Cancel' : '+ New Entry'}
          </button>
          <button className="stylish-btn secondary" onClick={() => setShowGeneralRop(true)}>
            Generate ROP
          </button>
          <button className="stylish-btn secondary" onClick={() => setShowLE(true)}>
            Generate LE
          </button>
        </div>
      {/* Generate ROP Modal */}
      {showGeneralRop && (
        <div style={{ position: 'fixed', top: 0, left: 0, width: '100vw', height: '100vh', background: 'rgba(0,0,0,0.3)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 2000 }}>
          <div style={{ background: '#fff', borderRadius: '12px', padding: '2rem', minWidth: '90vw', maxWidth: '1200px', boxShadow: '0 4px 32px #00bcd44a', maxHeight: '90vh', overflowY: 'auto', display: 'flex', flexDirection: 'column' }}>
            <div style={{ marginBottom: '1rem', textAlign: 'center' }}>
              <h3>ROP Table</h3>
            </div>
            {/* Table Construction: same as Table View, but show quantities */}
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
              // Calculate totals per month
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
                  <table className="project-table" style={{ fontSize: '0.95rem' }}>
                    <thead>
                      <tr>
                        <th style={{ minWidth: 120 }}>Region</th>
                        <th style={{ minWidth: 180 }}>Level 2 Item</th>
                        {months.map(m => (
                          <th key={m.label} style={{ minWidth: 60 }}>{m.label}</th>
                        ))}
                        <th>Total</th>
                      </tr>
                    </thead>
                    <tbody>
                      {regions.map(region => (
                        <React.Fragment key={region}>
                          <tr style={{ background: '#fffbe6', fontWeight: 'bold' }}>
                            <td colSpan={2 + months.length + 1}>{region || 'No Region'}</td>
                          </tr>
                          {entries.filter(e => (e.region || '') === region).map(item => (
                            <tr key={item.id}>
                              <td></td>
                              <td>{item.item_name}</td>
                              {months.map(m => {
                                const dist = (item.distributions || []).find(d => d.month === m.month && d.year === m.year);
                                return (
                                  <td key={m.label} style={{ textAlign: 'center' }}>{dist ? dist.allocated_quantity : '-'}</td>
                                );
                              })}
                              <td style={{ fontWeight: 'bold', textAlign: 'center' }}>{item.total_quantity?.toLocaleString() || '-'}</td>
                            </tr>
                          ))}
                        </React.Fragment>
                      ))}
                      {/* Totals row */}
                      <tr style={{ background: '#e3f2fd', fontWeight: 'bold' }}>
                        <td colSpan={2}>Total</td>
                        {monthTotals.map((total, idx) => (
                          <td key={idx} style={{ textAlign: 'center' }}>{total}</td>
                        ))}
                        <td></td>
                      </tr>
                    </tbody>
                  </table>
                  <div style={{ display: 'flex', justifyContent: 'center', gap: '1rem', marginTop: '2rem' }}>
                    <button className="stylish-btn danger" onClick={() => setShowGeneralRop(false)}>Close</button>
                    <button className="stylish-btn" onClick={() => {
                      // CSV download logic
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
                      // Totals row
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
      )}

      {/* Generate LE Modal */}
      {showLE && (
        <div style={{ position: 'fixed', top: 0, left: 0, width: '100vw', height: '100vh', background: 'rgba(0,0,0,0.3)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 2000 }}>
          <div style={{ background: '#fff', borderRadius: '12px', padding: '2rem', minWidth: '90vw', maxWidth: '1200px', boxShadow: '0 4px 32px #00bcd44a', maxHeight: '90vh', overflowY: 'auto', display: 'flex', flexDirection: 'column' }}>
            <div style={{ marginBottom: '1rem', textAlign: 'center' }}>
              <h3>LE Table (Values × Price)</h3>
            </div>
            {/* Table Construction: show quantity × price */}
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
              // Calculate totals per month (LE)
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
                  <table className="project-table" style={{ fontSize: '0.95rem' }}>
                    <thead>
                      <tr>
                        <th style={{ minWidth: 120 }}>Region</th>
                        <th style={{ minWidth: 180 }}>Level 2 Item</th>
                        {months.map(m => (
                          <th key={m.label} style={{ minWidth: 60 }}>{m.label}</th>
                        ))}
                        <th>Total</th>
                      </tr>
                    </thead>
                    <tbody>
                      {regions.map(region => (
                        <React.Fragment key={region}>
                          <tr style={{ background: '#fffbe6', fontWeight: 'bold' }}>
                            <td colSpan={2 + months.length + 1}>{region || 'No Region'}</td>
                          </tr>
                          {entries.filter(e => (e.region || '') === region).map(item => (
                            <tr key={item.id}>
                              <td></td>
                              <td>{item.item_name}</td>
                              {months.map(m => {
                                const dist = (item.distributions || []).find(d => d.month === m.month && d.year === m.year);
                                return (
                                  <td key={m.label} style={{ textAlign: 'center' }}>{dist ? (dist.allocated_quantity * (item.price || 0)).toLocaleString() : '-'}</td>
                                );
                              })}
                              <td style={{ fontWeight: 'bold', textAlign: 'center' }}>{((item.total_quantity || 0) * (item.price || 0)).toLocaleString() || '-'}</td>
                            </tr>
                          ))}
                        </React.Fragment>
                      ))}
                      {/* Totals row */}
                      <tr style={{ background: '#e3f2fd', fontWeight: 'bold' }}>
                        <td colSpan={2}>Total</td>
                        {monthTotals.map((total, idx) => (
                          <td key={idx} style={{ textAlign: 'center' }}>{total.toLocaleString()}</td>
                        ))}
                        <td></td>
                      </tr>
                    </tbody>
                  </table>
                  <div style={{ display: 'flex', justifyContent: 'center', gap: '1rem', marginTop: '2rem' }}>
                    <button className="stylish-btn danger" onClick={() => setShowLE(false)}>Close</button>
                    <button className="stylish-btn" onClick={() => {
                      // CSV download logic
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
                      // Totals row
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
      )}
      </div>

      {/* Statistics Cards */}
      <div className="stats-grid" style={{ display: 'flex', flexWrap: 'wrap', columnGap: '0.2rem', rowGap: '0.1rem' }}>
        {(() => {
          const statCards = [
            <div className="stat-card" style={{ width: 140, borderRadius: 26, padding: '0.8rem 1.2rem', fontSize: '1.1rem', margin: '0.06rem', boxSizing: 'border-box' }} key="lvl1_id">
              <div className="stat-value" style={{ fontSize: '1rem' }}>{formData.lvl1_id}</div>
              <div className="stat-label" style={{ fontSize: '0.95rem' }}>Level 1 ID</div>
            </div>,
            <div className="stat-card" style={{ width: 140, borderRadius: 26, padding: '0.8rem 1.2rem', fontSize: '1.1rem', margin: '0.06rem', boxSizing: 'border-box' }} key="lvl1_name">
              <div className="stat-value" style={{ fontSize: '1.2rem' }}>{formData.lvl1_item_name}</div>
              <div className="stat-label" style={{ fontSize: '0.95rem' }}>Level 1 Name</div>
            </div>,
            <div className="stat-card" style={{ width: 140, borderRadius: 26, padding: '0.8rem 1.2rem', fontSize: '1.1rem', margin: '0.06rem', boxSizing: 'border-box' }} key="project_id">
              <div className="stat-value" style={{ fontSize: '1rem' }}>{formData.project_id}</div>
              <div className="stat-label" style={{ fontSize: '0.95rem' }}>Project ID</div>
            </div>,
            <div className="stat-card" style={{ width: 140, borderRadius: 26, padding: '0.8rem 1.2rem', fontSize: '1.1rem', margin: '0.06rem', boxSizing: 'border-box' }} key="project_name">
              <div className="stat-value" style={{ fontSize: '1.2rem' }}>{formData.project_name}</div>
              <div className="stat-label" style={{ fontSize: '0.95rem' }}>Project Name</div>
            </div>,
            ...stats.map((stat, idx) => (
              <div key={idx} className="stat-card" style={{ width: 140, borderRadius: 26, padding: '0.8rem 1.2rem', fontSize: '1.1rem', margin: '0.06rem', boxSizing: 'border-box' }}>
                <div className="stat-value" style={{ fontSize: '1.2rem' }}>{stat.value}</div>
                {stat.extra && <div className="stat-extra" style={{ fontSize: '0.95rem' }}>{stat.extra}</div>}
                <div className="stat-label" style={{ fontSize: '0.95rem' }}>{stat.label}</div>
              </div>
            ))
          ];
          return (
            <>
              <div style={{ display: 'flex', justifyContent: 'space-evenly', gap: '0.2rem', marginBottom: '0.2rem', width: '100%' }}>
                {statCards.slice(0, 5)}
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-evenly', gap: '0.2rem', width: '100%' }}>
                {statCards.slice(5, 10)}
              </div>
            </>
          );
        })()}
      </div>

      {/* Modal Form */}
      {showForm && (
        <div style={{
          position: 'fixed', top: 0, left: 0, width: '100vw', height: '100vh',
          background: 'rgba(0,0,0,0.3)', display: 'flex', alignItems: 'center',
          justifyContent: 'center', zIndex: 1000
        }}>
          <div style={{
            background: '#fff', borderRadius: '12px', padding: '2rem',
            minWidth: '500px', boxShadow: '0 4px 32px #00bcd44a',
            maxHeight: '80vh', overflowY: 'auto'
          }}>
            <form className="project-form" onSubmit={handleSubmit}>
              <div>
                <button
                  style={{ width: 'fit-content', padding: '0.4rem', float: 'right' }}
                  className="stylish-btn danger"
                  onClick={() => setShowForm(false)}
                  type="button"
                >X</button>
              </div>

              <input type="text" placeholder="Project ID" value={formData.project_id} disabled />
              <input type="text" placeholder="Level 1 ID" value={formData.lvl1_id} disabled />
              <input type="text" placeholder="Lvl1 Item Name" value={formData.lvl1_item_name} disabled />
              <input type="text" placeholder="Item Name" value={formData.item_name}
                onChange={e => setFormData({ ...formData, item_name: e.target.value })} required />
              <input type="text" placeholder="Region" value={formData.region}
                onChange={e => setFormData({ ...formData, region: e.target.value })} />
              <input type="number" placeholder="Total Quantity" value={formData.total_quantity}
                onChange={e => setFormData({ ...formData, total_quantity: Number(e.target.value) || 0 })} />
              <input type="number" step="0.01" placeholder="Price" value={formData.price}
                onChange={e => setFormData({ ...formData, price: Number(e.target.value) || 0 })} />
              <input type="date" placeholder="Start Date" value={formData.start_date}
                onChange={e => setFormData({ ...formData, start_date: e.target.value })} />
              <input type="date" placeholder="End Date" value={formData.end_date}
                onChange={e => setFormData({ ...formData, end_date: e.target.value })} />

              {/* Dynamic Distribution Table */}
              {distributions.length > 0 && (
                <div style={{ margin: '1rem 0', overflowX: 'auto' }}>
                  <table className="project-table">
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
                              style={{ width: '80px' }}
                            />
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              <button style={{ width: '100%' }} type="submit" className="stylish-btn">
                {isEditing ? 'Update' : 'Create'}
              </button>
            </form>
          </div>
        </div>
      )}

      {error && <div className="error">{error}</div>}
      {success && <div className="success">{success}</div>}

      {/* Entries Table */}
      <div className="project-table-container">
        <table className="project-table">
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
                <th key={col.label}>{col.label}</th>
              ))}
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {paginatedEntries.map(entry => (
              <>
              <tr key={entry.id}>
                <td>{entry.id}</td>
                <td>{entry.item_name}</td>
                <td>{entry.product_number || '-'}</td>
                <td>{entry.region || '-'}</td>
                <td>{entry.total_quantity?.toLocaleString() || '-'}</td>
                <td>{entry.price?.toFixed(2) || '-'}</td>
                <td>{((entry.total_quantity || 0) * (entry.price || 0)).toLocaleString()}</td>
                {/* Distribution cells */}
                {distributionColumns.map(col => {
                  const orig = (entry.distributions || []).find(d => d.month === col.month && d.year === col.year);
                  const key = `${col.year}-${col.month}`;
                  if (!orig) {
                    // Month does not exist for this item, show '-' and disable editing
                    return (
                      <td key={key} style={{ color: '#aaa', textAlign: 'center' }}>-</td>
                    );
                  }
                  const value = editedDistributions[entry.id]?.[key] ?? orig.allocated_quantity;
                  return (
                    <td key={key}>
                      <input
                        type="number"
                        value={value !== undefined ? value : ''}
                        style={{ width: '60px' }}
                        onChange={e => handleDistributionEdit(entry.id, col.month, col.year, e.target.value)}
                      />
                    </td>
                  );
                })}
                <td style={{ textAlign: 'center', display: 'flex', gap: '0.5rem', justifyContent: 'center', flexWrap: 'wrap' }}>
                  <button className="stylish-btn danger" style={{ width: '100%' }} onClick={() => handleDelete(entry.id)}>Delete</button>
                </td>
              </tr>
              {/* Save button row */}
              {showSaveRow[entry.id] && (
                <tr>
                  <td colSpan={10 + distributionColumns.length} style={{ textAlign: 'center', background: '#f9f9f9' }}>
                    <button style={{float:'left'}}className="stylish-btn" onClick={() => handleSaveDistributions(entry)}>
                      Save
                    </button>
                  </td>
                </tr>
              )}
              </>
            ))}
            {entries.length === 0 && (
              <tr>
                <td colSpan={10 + distributionColumns.length} style={{ textAlign: 'center', padding: '2rem', fontStyle: 'italic', color: '#6c757d' }}>
                  No entries found. Click "New Entry" to create your first entry.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="pagination">
          {Array.from({ length: totalPages }, (_, i) => (
            <button
              key={i}
              className={i + 1 === currentPage ? 'active-page' : ''}
              onClick={() => setCurrentPage(i + 1)}
            >{i + 1}</button>
          ))}
        </div>
      )}
    </div>
  );
}
