import { useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import '../css/Project.css';

const ENTRIES_PER_PAGE = 5;

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

  const VITE_API_URL = import.meta.env.VITE_API_URL;

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

  return (
    <div className="project-container">
      <div className="header-row">
        <h2>ROP Level 1</h2>
        <button className="new-project-btn" onClick={() => { resetForm(); setShowForm(!showForm); }}>
          {showForm ? 'Cancel' : '+ New Entry'}
        </button>
      </div>

      {/* Statistics Cards */}
  <div className="stats-grid" style={{ display: 'flex', flexWrap: 'wrap', columnGap: '0.2rem', rowGap: '0.1rem' }}>
        {(() => {
          const statCards = [
            <div className="stat-card" style={{ width: 140, borderRadius: 26, padding: '0.8rem 1.2rem', fontSize: '1.1rem', margin: '0.06rem', boxSizing: 'border-box' }} key="project_id">
              <div className="stat-value" style={{ fontSize: '1rem'  }}>{formData.project_id}</div>
              <div className="stat-label" style={{ fontSize: '0.95rem' }}>Project ID</div>
            </div>,
            <div className="stat-card" style={{ width: 140, borderRadius: 26, padding: '0.8rem 1.2rem', fontSize: '1.1rem', margin: '0.06rem', boxSizing: 'border-box' }} key="project_name">
              <div className="stat-value" style={{ fontSize: '1.2rem' }}>{formData.project_name}</div>
              <div className="stat-label" style={{ fontSize: '0.95rem' }}>Project Name</div>
            </div>,
            ...[
              { label: 'Total Quantity', value: totalQuantity.toLocaleString() },
              { label: 'Total LE', value: totalLE.toLocaleString() },
              { label: 'Number of Items', value: totalItems },
              { label: 'Highest LE Item', value: highestLEItem.item_name || '-', extra: highestLEItem.le ? `(${highestLEItem.le.toLocaleString()})` : '' },
              { label: 'Avg. Quantity/Item', value: avgQuantityPerItem.toLocaleString() },
              { label: 'Avg. LE/Item', value: avgLEPerItem.toLocaleString() },
              { label: 'Earliest Start Date', value: earliestStart ? earliestStart.toLocaleDateString() : '-' },
              { label: 'Latest End Date', value: latestEnd ? latestEnd.toLocaleDateString() : '-' }
            ].map((stat, idx) => (
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
                >
                  X
                </button>
              </div>

              <input type="text" placeholder="Project ID" value={formData.project_id} disabled />
              <input type="text" placeholder="Project Name" value={formData.project_name} disabled />
              <input type="text" placeholder="Item Name" value={formData.item_name}
                onChange={e => setFormData({ ...formData, item_name: e.target.value })} required />
              <input type="text" placeholder="Region" value={formData.region}
                onChange={e => setFormData({ ...formData, region: e.target.value })} />
              <input type="number" placeholder="Total Quantity" value={formData.total_quantity}
                onChange={e => setFormData({ ...formData, total_quantity: e.target.value })} />
              <input type="number" step="0.01" placeholder="Price" value={formData.price}
                onChange={e => setFormData({ ...formData, price: e.target.value })} />
              <input type="date" placeholder="Start Date" value={formData.start_date}
                onChange={e => setFormData({ ...formData, start_date: e.target.value })} />
              <input type="date" placeholder="End Date" value={formData.end_date}
                onChange={e => setFormData({ ...formData, end_date: e.target.value })} />

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
              <th>LE</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {paginatedEntries.map(entry => (
              <tr key={entry.id}>
                <td>{entry.id}</td>
                <td>{entry.item_name}</td>
                <td>{entry.product_number || '-'}</td>
                <td>{entry.region || '-'}</td>
                <td>{entry.total_quantity?.toLocaleString() || '-'}</td>
                <td>{entry.price?.toFixed(2) || '-'}</td>
                <td>{((entry.total_quantity || 0) * (entry.price || 0)).toLocaleString()}</td>
                <td style={{ textAlign: 'center' }}>
                  <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'center', marginBottom: '0.5rem' }}>
                    <button className="stylish-btn" style={{ width: '48%' }} onClick={() => handleEdit(entry)}>Edit</button>
                    <button className="stylish-btn danger" style={{ width: '48%' }} onClick={() => handleDelete(entry.id)}>Delete</button>
                  </div>
                  <div>
                    <button className="stylish-btn" style={{ width: '100%' }} onClick={() => navigate('/rop-lvl2', {
                      state: {
                        lvl1_id: entry.id,
                        lvl1_item_name: entry.item_name,
                        pid_po: entry.project_id,
                        project_name: entry.project_name
                      }
                    })}>Level 2</button>
                  </div>
                </td>
              </tr>
            ))}
            {entries.length === 0 && (
              <tr>
                <td colSpan="9" style={{ textAlign: 'center', padding: '2rem', fontStyle: 'italic', color: '#6c757d' }}>
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
            >
              {i + 1}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
