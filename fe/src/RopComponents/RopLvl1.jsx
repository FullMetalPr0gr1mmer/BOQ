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
        package_name: '',
        start_date: '',
        end_date: '',
        quantity: '',
    });

    // State to hold selected Lvl1 items with their quantities
    const [selectedLvl1Items, setSelectedLvl1Items] = useState([]);
    const [lvl2Details, setLvl2Details] = useState({});
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');
    const [currentPage, setCurrentPage] = useState(1);
    const [expandedRows, setExpandedRows] = useState({});
    const [lvl2Items, setLvl2Items] = useState({});
    const [showLvl1Dropdown, setShowLvl1Dropdown] = useState(false);

    useEffect(() => {
        fetchEntries();
    }, []);

    useEffect(() => {
        const fetchDetailsForSelectedLvl1 = async () => {
            const newLvl2Details = {};
            for (const item of selectedLvl1Items) {
                try {
                    const res = await fetch(`${VITE_API_URL}/rop-lvl2/by-lvl1/${item.id}`);
                    if (!res.ok) throw new Error('Failed to fetch Level 2 items');
                    const data = await res.json();
                    newLvl2Details[item.id] = data;
                } catch (err) {
                    newLvl2Details[item.id] = [];
                }
            }
            setLvl2Details(newLvl2Details);
        };
        fetchDetailsForSelectedLvl1();
    }, [selectedLvl1Items]);

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
            package_name: '',
            start_date: '',
            end_date: '',
            quantity: '',
        });
        setSelectedLvl1Items([]);
        setLvl2Details({});
        setEditId(null);
        setIsEditing(false);
        setShowForm(false);
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setSuccess('');

        if (!formData.package_name || selectedLvl1Items.length === 0) {
            setError('Package Name and at least one Lvl1 item are required.');
            return;
        }

        const payload = {
            project_id: formData.project_id,
            package_name: formData.package_name,
            start_date: formData.start_date || null,
            end_date: formData.end_date || null,
            quantity: formData.quantity ? parseInt(formData.quantity) : null,
            lvl1_ids: selectedLvl1Items,
        };

        try {
            const res = await fetch(`${VITE_API_URL}/rop-package/create`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });

            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.detail || 'Failed to create package');
            }

            setSuccess('ROP Package created successfully!');
            resetForm();
            fetchEntries(); // This might not be needed if the table only shows Lvl1 items
        } catch (err) {
            setError(err.message);
        }
    };

    const handleSelectLvl1Item = (item) => {
        setSelectedLvl1Items(prev => {
            const itemExists = prev.find(i => i.id === item.id);
            if (itemExists) {
                // Remove item if it's already selected
                return prev.filter(i => i.id !== item.id);
            } else {
                // Add new item with a default quantity
                return [...prev, { id: item.id, quantity: '' }];
            }
        });
    };

    const handleQuantityChange = (id, quantity) => {
        setSelectedLvl1Items(prev =>
            prev.map(item =>
                item.id === id ? { ...item, quantity: quantity } : item
            )
        );
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
                        <div className="progress-fill" style={{ width: `${Math.min((totalItems / 10) * 100, 100)}%` }}></div>
                    </div>

                    <div className="metric-row">
                        <span className="metric-label">Budget Utilization</span>
                        <span className="metric-value">{totalLE.toLocaleString()} LE</span>
                    </div>
                    <div className="progress-bar">
                        <div className="progress-fill" style={{ width: `${Math.min((totalLE / 100000) * 100, 100)}%` }}></div>
                    </div>

                    <div className="metric-row">
                        <span className="metric-label">Quantity Target</span>
                        <span className="metric-value">{totalQuantity.toLocaleString()} Units</span>
                    </div>
                    <div className="progress-bar">
                        <div className="progress-fill" style={{ width: `${Math.min((totalQuantity / 1000) * 100, 100)}%` }}></div>
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
                                ✨ Create New Package
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
                                placeholder="Package Name"
                                value={formData.package_name}
                                onChange={e => setFormData({ ...formData, package_name: e.target.value })}
                                required
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
                            <input
                                type="number"
                                placeholder="Quantity"
                                value={formData.quantity}
                                onChange={e => setFormData({ ...formData, quantity: e.target.value })}
                            />

                            <div className="form-group" style={{ position: 'relative' }}>
                                <label htmlFor="lvl1-select">Select ROP Lvl1 Items:</label>
                                <div
                                    className="custom-dropdown-select"
                                    onClick={() => setShowLvl1Dropdown(!showLvl1Dropdown)}
                                    style={{
                                        padding: '10px',
                                        border: '1px solid #ccc',
                                        borderRadius: '4px',
                                        cursor: 'pointer',
                                        backgroundColor: '#fff',
                                        display: 'flex',
                                        justifyContent: 'space-between',
                                        alignItems: 'center',
                                    }}
                                >
                                    {selectedLvl1Items.length > 0
                                        ? `${selectedLvl1Items.length} item(s) selected`
                                        : 'Click to select items'}
                                    <span>{showLvl1Dropdown ? '▲' : '▼'}</span>
                                </div>
                                {showLvl1Dropdown && (
                                    <div
                                        style={{
                                            position: 'absolute',
                                            top: '100%',
                                            left: 0,
                                            zIndex: 100,
                                            width: '100%',
                                            border: '1px solid #ccc',
                                            borderRadius: '4px',
                                            backgroundColor: '#fff',
                                            maxHeight: '200px',
                                            overflowY: 'auto',
                                        }}
                                    >
                                        {entries.map(entry => {
                                            const isSelected = selectedLvl1Items.some(item => item.id === entry.id);
                                            const selectedItem = selectedLvl1Items.find(item => item.id === entry.id);
                                            return (
                                                <div
                                                    key={entry.id}
                                                    style={{
                                                        padding: '8px 10px',
                                                        cursor: 'pointer',
                                                        backgroundColor: isSelected ? '#e6f7ff' : 'transparent',
                                                        borderBottom: '1px solid #f0f0f0',
                                                        display: 'flex',
                                                        alignItems: 'center',
                                                    }}
                                            >
                                                <input
                                                    type="checkbox"
                                                    checked={isSelected}
                                                    onChange={() => handleSelectLvl1Item(entry)}
                                                    style={{ marginRight: '10px' }}
                                                />
                                                <span style={{ flexGrow: 1 }}>
                                                    {entry.item_name} (ID: {entry.id})
                                                </span>
                                                {isSelected && (
                                                    <input
                                                        type="number"
                                                        placeholder="Quantity"
                                                        value={selectedItem.quantity}
                                                        onChange={e => handleQuantityChange(entry.id, e.target.value)}
                                                        style={{ width: '80px' }}
                                                        onClick={e => e.stopPropagation()} // Prevent closing dropdown
                                                    />
                                                )}
                                            </div>
                                        );
                                    })}
                                    </div>
                                )}
                            </div>


                            <div className="form-group">
                                <label>Associated ROP Lvl2 Items:</label>
                                <div style={{ border: '1px solid #ccc', padding: '10px', maxHeight: '150px', overflowY: 'auto' }}>
                                    {selectedLvl1Items.length === 0 ? (
                                        <p style={{ color: '#888' }}>Select Lvl1 items to see their Lvl2 details.</p>
                                    ) : (
                                        selectedLvl1Items.map(item => (
                                            <div key={item.id} style={{ marginBottom: '10px' }}>
                                                <strong>Lvl1 Item ID: {item.id} (Quantity: {item.quantity || 'Not specified'})</strong>
                                                <ul>
                                                    {(lvl2Details[item.id] || []).length > 0 ? (
                                                        lvl2Details[item.id].map(lvl2 => (
                                                            <li key={lvl2.id}>
                                                                {lvl2.item_name} (ID: {lvl2.id})
                                                            </li>
                                                        ))
                                                    ) : (
                                                        <li>No Lvl2 items found for this entry.</li>
                                                    )}
                                                </ul>
                                            </div>
                                        ))
                                    )}
                                </div>
                            </div>

                            <button type="submit">
                                🚀 Create Package
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

                <div className="dashboard-table-container" style={{ overflowX: 'hidden' }}>
                    {entries.length > 0 ? (
                        <table className="dashboard-table">
                            <thead>
                                <tr>
                                    <th></th>
                                    <th></th>

                                    {/* Removed ID column */}
                                    <th style={{ textAlign: 'center' }}>Product Number</th>
                                    <th style={{ textAlign: 'center' }}>Item Name</th>
                                    <th style={{ textAlign: 'center' }}>Quantity</th>
                                    <th style={{ textAlign: 'center' }}>Unit Price</th>
                                    <th style={{ textAlign: 'center' }}>Total Price</th>
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
                                            {/* Removed ID cell */}
                                            <td>{entry.product_number || '-'}</td>
                                            <td><strong>{entry.item_name}</strong></td>
                                            <td>{entry.total_quantity?.toLocaleString() || '-'}</td>
                                            <td>{entry.price ? `${entry.price.toFixed(2)} LE` : '-'}</td>
                                            <td>
                                                <strong style={{ color: 'var(--nokia-success)' }}>
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

                                                                    {/* Removed ID column in expanded table */}
                                                                    <th style={{ textAlign: 'center' }}>Product Number</th>
                                                                    <th style={{ textAlign: 'center' }}>Item Name</th>
                                                                    <th style={{ textAlign: 'center' }}>Quantity</th>
                                                                    <th style={{ textAlign: 'center' }}>Price</th>
                                                                    <th style={{ textAlign: 'center' }}>Total Price</th>
                                                                </tr>
                                                            </thead>
                                                            <tbody>
                                                                {(lvl2Items[entry.id] || []).map(lvl2 => (
                                                                    <tr key={lvl2.id}>
                                                                        {/* Removed ID cell in expanded table */}
                                                                        <td>{lvl2.product_number || '-'}</td>
                                                                        <td>{lvl2.item_name}</td>
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