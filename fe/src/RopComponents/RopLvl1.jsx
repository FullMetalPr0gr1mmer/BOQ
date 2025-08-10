import { useEffect, useState } from 'react';
import React from 'react';
import '../css/Project.css';
import { FaSignOutAlt, FaTimes } from 'react-icons/fa';
export default function ROPLvl1() {
    const [entries, setEntries] = useState([]);
    const [showForm, setShowForm] = useState(false);
    const [isEditing, setIsEditing] = useState(false); // to track if editing or creating
    const [editId, setEditId] = useState(null); // id of entry being edited
    const [formData, setFormData] = useState({
        project_id: '',
        project_name: '',
        item_name: '',
        region: '',
        total_quantity: '',
        price: '',
        start_date: '',
        end_date: '',
    });
    const [distributions, setDistributions] = useState([]);
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');
    const [expandedRows, setExpandedRows] = useState([]);
    const [showGeneralRop, setShowGeneralRop] = useState(false);
    const [showLE, setShowLE] = useState(false);
    const [showDetails, setShowDetails] = useState(false);
    const [detailsEntry, setDetailsEntry] = useState(null);

    const VITE_API_URL = import.meta.env.VITE_API_URL;

    useEffect(() => {
        fetchEntries();
    }, []);

    const fetchEntries = async () => {
        try {
            const res = await fetch(`${VITE_API_URL}/rop-lvl1`);
            const data = await res.json();
            setEntries(data);
        } catch {
            setError('Failed to fetch ROP Lvl1 entries');
        }
    };

    const generateDistributions = (start, end) => {
        const result = [];
        let current = new Date(start);
        const endDate = new Date(end);

        while (current <= endDate) {
            result.push({
                year: current.getFullYear(),
                month: current.getMonth() + 1,
                allocated_quantity: '',
            });
            current.setMonth(current.getMonth() + 1);
        }

        setDistributions(result);
    };

    const handleDateChange = (e) => {
        const { name, value } = e.target;
        const updatedForm = { ...formData, [name]: value };
        setFormData(updatedForm);

        if (name === 'start_date' || name === 'end_date') {
            const { start_date, end_date } = { ...updatedForm, [name]: value };
            if (start_date && end_date) {
                generateDistributions(start_date, end_date);
            }
        }
    };

    const handleDistributionChange = (index, value) => {
        const updated = [...distributions];
        updated[index].allocated_quantity = parseInt(value) || 0;
        setDistributions(updated);
    };

    const resetForm = () => {
        setFormData({
            project_id: '',
            project_name: '',
            item_name: '',
            region: '',
            total_quantity: '',
            price: '',
            start_date: '',
            end_date: '',
        });
        setDistributions([]);
        setEditId(null);
        setIsEditing(false);
        setShowForm(false);
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setSuccess('');

        const payload = {
            ...formData,
            total_quantity: parseInt(formData.total_quantity),
            price: parseInt(formData.price),
            distributions: distributions.map(d => ({
                year: d.year,
                month: d.month,
                allocated_quantity: d.allocated_quantity
            }))
        };

        try {
            let res;
            if (isEditing && editId !== null) {
                // Update existing entry
                res = await fetch(`${VITE_API_URL}/rop-lvl1/update/${editId}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
            } else {
                // Create new entry
                res = await fetch(`${VITE_API_URL}/rop-lvl1/create`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
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

    const handleDelete = async (id) => {
        if (!window.confirm('Are you sure you want to delete this entry?')) return;

        try {
            const res = await fetch(`${VITE_API_URL}/rop-lvl1/${id}`, {
                method: 'DELETE'
            });

            if (!res.ok) throw new Error('Failed to delete entry');

            setEntries(entries.filter(e => e.id !== id));
        } catch (err) {
            setError(err.message);
        }
    };

    const toggleDistributions = (id) => {
        if (expandedRows.includes(id)) {
            setExpandedRows(expandedRows.filter(rowId => rowId !== id));
        } else {
            setExpandedRows([...expandedRows, id]);
        }
    };

    const handleEdit = (entry) => {
        setIsEditing(true);
        setEditId(entry.id);
        setFormData({
            project_id: entry.project_id,
            project_name: entry.project_name,
            item_name: entry.item_name,
            region: entry.region,
            total_quantity: entry.total_quantity,
            price: entry.price,
            start_date: entry.start_date,
            end_date: entry.end_date,
        });

        // Load distributions for editing
        // Make sure allocated_quantity is string or number for inputs
        const distData = entry.distributions.map(d => ({
            year: d.year,
            month: d.month,
            allocated_quantity: d.allocated_quantity === 0 ? 0 : (d.allocated_quantity || ''),
        }));

        setDistributions(distData);
        setShowForm(true);
        setSuccess('');
        setError('');
    };

    // Prepare timeline: get all years/months from entries' distributions, sorted chronologically within each year
    const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    const allMonthsSet = new Set();
    entries.forEach(entry => {
        entry.distributions.forEach(d => {
            allMonthsSet.add(`${d.year}-${d.month}`);
        });
    });
    // Group months by year, then sort months within each year
    const monthsByYear = {};
    Array.from(allMonthsSet).forEach(key => {
        const [year, month] = key.split('-').map(Number);
        if (!monthsByYear[year]) monthsByYear[year] = [];
        monthsByYear[year].push(month);
    });
    Object.keys(monthsByYear).forEach(year => {
        monthsByYear[year].sort((a, b) => a - b);
    });
    // Flatten to get allMonths in correct order
    const allMonths = [];
    Object.keys(monthsByYear).sort((a, b) => a - b).forEach(year => {
        monthsByYear[year].forEach(month => {
            allMonths.push(`${year}-${month}`);
        });
    });

    // Group items by region, each item with its distributions
    const groupedByRegion = {};
    entries.forEach(entry => {
        if (!groupedByRegion[entry.region]) groupedByRegion[entry.region] = [];
        groupedByRegion[entry.region].push(entry);
    });

    // Helper to get quantity for a given item/distribution month
    function getQty(entry, year, month) {
        const found = entry.distributions.find(d => d.year === year && d.month === month);
        return found ? found.allocated_quantity : '';
    }

    // Helper to get total for an item
    function getItemTotal(entry) {
        return entry.distributions.reduce((sum, d) => sum + (parseInt(d.allocated_quantity) || 0), 0);
    }

    // Helper to get region total
    function getRegionTotal(regionEntries) {
        return regionEntries.reduce((sum, entry) => sum + getItemTotal(entry), 0);
    }

    // Helper to get month total for region
    function getMonthTotal(regionEntries, year, month) {
        return regionEntries.reduce((sum, entry) => sum + (parseInt(getQty(entry, year, month)) || 0), 0);
    }

    // Helper to get grand total
    function getGrandTotal() {
        return Object.values(groupedByRegion).reduce((sum, regionEntries) => sum + getRegionTotal(regionEntries), 0);
    }

    return (
        <div className="project-container">
            <div className="header-row">
                <h2>ROP Level 1</h2>
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                    <button
                        className="stylish-btn"
                        onClick={() => {
                            resetForm();
                            setShowForm(true);
                        }}
                    >
                        + New Entry
                    </button>
                    <button
                        className="stylish-btn secondary"
                        onClick={() => setShowGeneralRop(true)}
                    >
                        Generate general ROP
                    </button>
                    <button
                        className="stylish-btn secondary"
                        onClick={() => setShowLE(true)}
                    >
                        Generate LE
                    </button>
                </div>
            </div>
            {/* Modal for LE Table (values multiplied by price) */}
            {showLE && (
                <div style={{
                    position: 'fixed',
                    top: 0,
                    left: 0,
                    width: '100vw',
                    height: '100vh',
                    background: 'rgba(0,0,0,0.3)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    zIndex: 1000
                }}>
                    <div style={{
                        background: '#fff',
                        borderRadius: '12px',
                        padding: '2rem',
                        minWidth: '900px',
                        boxShadow: '0 4px 32px #00bcd44a',
                        maxHeight: '80vh',
                        overflowY: 'auto'
                    }}>
                        <h3 style={{ marginBottom: '1rem' }}>LE Table (Values × Price)</h3>
                        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.95rem', marginBottom: '1rem' }}>
                            <thead>
                                <tr style={{ background: '#e0f7fa' }}>
                                    <th rowSpan="2" style={{ border: '1px solid #b2ebf2', padding: '0.5rem', minWidth: '120px' }}>Activities</th>
                                    {Object.keys(monthsByYear).sort((a, b) => a - b).map(year => {
                                        const monthsInYear = monthsByYear[year].length;
                                        return <th key={year} colSpan={monthsInYear} style={{ border: '1px solid #b2ebf2', textAlign: 'center' }}>{year}</th>;
                                    })}
                                    <th rowSpan="2" style={{ border: '1px solid #b2ebf2', padding: '0.5rem' }}>Total</th>
                                </tr>
                                <tr style={{ background: '#e0f7fa' }}>
                                    {Object.keys(monthsByYear).sort((a, b) => a - b).map(year => (
                                        monthsByYear[year].map(month => (
                                            <th key={`${year}-${month}`} style={{ border: '1px solid #b2ebf2', padding: '0.5rem', minWidth: '40px' }}>{monthNames[month-1]}</th>
                                        ))
                                    ))}
                                </tr>
                            </thead>
                            <tbody>
                                {Object.entries(groupedByRegion).map(([region, regionEntries], idx) => (
                                    <React.Fragment key={region}>
                                        <tr style={{ background: '#ffe082', fontWeight: 'bold' }}>
                                            <td colSpan={allMonths.length + 2} style={{ border: '1px solid #b2ebf2', padding: '0.5rem' }}>{region}</td>
                                        </tr>
                                        {regionEntries.map((entry, i) => (
                                            <tr key={entry.id} style={{ borderBottom: '1px dotted #aaa' }}>
                                                <td style={{ border: '1px solid #b2ebf2', padding: '0.5rem' }}>{entry.item_name}</td>
                                                {allMonths.map(m => {
                                                    const [year, month] = m.split('-');
                                                    const qty = getQty(entry, parseInt(year), parseInt(month));
                                                    const val = qty ? qty * entry.price : 0;
                                                    return <td key={m} style={{ border: '1px solid #b2ebf2', padding: '0.5rem', textAlign: 'center' }}>{val.toLocaleString()}</td>;
                                                })}
                                                <td style={{ border: '1px solid #b2ebf2', padding: '0.5rem', fontWeight: 'bold', background: '#e0f7fa' }}>{(getItemTotal(entry) * entry.price).toLocaleString()}</td>
                                            </tr>
                                        ))}
                                        {/* Region total row */}
                                        <tr style={{ background: '#fffde7', fontWeight: 'bold' }}>
                                            <td style={{ border: '1px solid #b2ebf2', padding: '0.5rem' }}>Total {region}</td>
                                            {allMonths.map(m => {
                                                const [year, month] = m.split('-');
                                                // Sum for region, multiplied by price for each entry
                                                const total = regionEntries.reduce((sum, entry) => sum + ((parseInt(getQty(entry, parseInt(year), parseInt(month))) || 0) * entry.price), 0);
                                                return <td key={m} style={{ border: '1px solid #b2ebf2', padding: '0.5rem', textAlign: 'center' }}>{total.toLocaleString()}</td>;
                                            })}
                                            <td style={{ border: '1px solid #b2ebf2', padding: '0.5rem', fontWeight: 'bold', background: '#e0f7fa' }}>{regionEntries.reduce((sum, entry) => sum + (getItemTotal(entry) * entry.price), 0).toLocaleString()}</td>
                                        </tr>
                                    </React.Fragment>
                                ))}
                                {/* Grand total row */}
                                <tr style={{ background: '#b2ebf2', fontWeight: 'bold' }}>
                                    <td style={{ border: '1px solid #2196f3', padding: '0.5rem' }}>Total Sites</td>
                                    {allMonths.map(m => {
                                        const [year, month] = m.split('-');
                                        // Sum for all regions, multiplied by price
                                        const total = Object.values(groupedByRegion).reduce((sum, regionEntries) => sum + regionEntries.reduce((s, entry) => s + ((parseInt(getQty(entry, parseInt(year), parseInt(month))) || 0) * entry.price), 0), 0);
                                        return <td key={m} style={{ border: '1px solid #2196f3', padding: '0.5rem', textAlign: 'center' }}>{total.toLocaleString()}</td>;
                                    })}
                                    <td style={{ border: '1px solid #2196f3', padding: '0.5rem', fontWeight: 'bold', background: '#e0f7fa' }}>{Object.values(groupedByRegion).reduce((sum, regionEntries) => sum + regionEntries.reduce((s, entry) => s + (getItemTotal(entry) * entry.price), 0), 0).toLocaleString()}</td>
                                </tr>
                            </tbody>
                        </table>
                        <div style={{ display: 'flex', gap: '0.5rem', marginTop: '1rem' }}>
                            <button
                                className="stylish-btn"
                                onClick={() => {
                                    // Generate CSV for LE Table
                                    let csv = '';
                                    csv += 'Activities,';
                                    allMonths.forEach(m => {
                                        const [year, month] = m.split('-');
                                        csv += `${monthNames[month-1]} ${year},`;
                                    });
                                    csv += 'Total\n';

                                    Object.entries(groupedByRegion).forEach(([region, regionEntries]) => {
                                        csv += `${region},`;
                                        csv += Array(allMonths.length).fill('').join(',') + ',\n';
                                        regionEntries.forEach(entry => {
                                            csv += `${entry.item_name},`;
                                            allMonths.forEach(m => {
                                                const [year, month] = m.split('-');
                                                const qty = getQty(entry, parseInt(year), parseInt(month));
                                                csv += `${qty ? qty * entry.price : 0},`;
                                            });
                                            csv += `${getItemTotal(entry) * entry.price}\n`;
                                        });
                                        csv += `Total ${region},`;
                                        allMonths.forEach(m => {
                                            const [year, month] = m.split('-');
                                            const total = regionEntries.reduce((sum, entry) => sum + ((parseInt(getQty(entry, parseInt(year), parseInt(month))) || 0) * entry.price), 0);
                                            csv += `${total},`;
                                        });
                                        csv += `${regionEntries.reduce((sum, entry) => sum + (getItemTotal(entry) * entry.price), 0)}\n`;
                                    });
                                    csv += 'Total Sites,';
                                    allMonths.forEach(m => {
                                        const [year, month] = m.split('-');
                                        const total = Object.values(groupedByRegion).reduce((sum, regionEntries) => sum + regionEntries.reduce((s, entry) => s + ((parseInt(getQty(entry, parseInt(year), parseInt(month))) || 0) * entry.price), 0), 0);
                                        csv += `${total},`;
                                    });
                                    csv += `${Object.values(groupedByRegion).reduce((sum, regionEntries) => sum + regionEntries.reduce((s, entry) => s + (getItemTotal(entry) * entry.price), 0), 0)}\n`;

                                    const blob = new Blob([csv], { type: 'text/csv' });
                                    const url = URL.createObjectURL(blob);
                                    const a = document.createElement('a');
                                    a.href = url;
                                    a.download = 'le_table.csv';
                                    document.body.appendChild(a);
                                    a.click();
                                    document.body.removeChild(a);
                                    URL.revokeObjectURL(url);
                                }}
                            >
                                Download CSV
                            </button>
                            <button className="stylish-btn danger" onClick={() => setShowLE(false)}>
                                Close
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* Modal for General ROP Table */}
            {showGeneralRop && (
                <div style={{
                    position: 'fixed',
                    top: 0,
                    left: 0,
                    width: '100vw',
                    height: '100vh',
                    background: 'rgba(0,0,0,0.3)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    zIndex: 1000
                }}>
                    <div style={{
                        background: '#fff',
                        borderRadius: '12px',
                        padding: '2rem',
                        minWidth: '900px',
                        boxShadow: '0 4px 32px #00bcd44a',
                        maxHeight: '80vh',
                        overflowY: 'auto'
                    }}>
                        <h3 style={{ marginBottom: '1rem' }}>General ROP Table</h3>
                        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.95rem', marginBottom: '1rem' }}>
                            <thead>
                                {/* Timeline header: years and months */}
                                <tr style={{ background: '#e0f7fa' }}>
                                    <th rowSpan="2" style={{ border: '1px solid #b2ebf2', padding: '0.5rem', minWidth: '120px' }}>Activities</th>
                                    {/* Years header */}
                                    {Object.keys(monthsByYear).sort((a, b) => a - b).map(year => {
                                        const monthsInYear = monthsByYear[year].length;
                                        return <th key={year} colSpan={monthsInYear} style={{ border: '1px solid #b2ebf2', textAlign: 'center' }}>{year}</th>;
                                    })}
                                    <th rowSpan="2" style={{ border: '1px solid #b2ebf2', padding: '0.5rem' }}>Total</th>
                                </tr>
                                <tr style={{ background: '#e0f7fa' }}>
                                    {/* Months header */}
                                    {Object.keys(monthsByYear).sort((a, b) => a - b).map(year => (
                                        monthsByYear[year].map(month => (
                                            <th key={`${year}-${month}`} style={{ border: '1px solid #b2ebf2', padding: '0.5rem', minWidth: '40px' }}>{monthNames[month-1]}</th>
                                        ))
                                    ))}
                                </tr>
                            </thead>
                            <tbody>
                                {/* Regions and items */}
                                {Object.entries(groupedByRegion).map(([region, regionEntries], idx) => (
                                    <React.Fragment key={region}>
                                        <tr style={{ background: '#ffe082', fontWeight: 'bold' }}>
                                            <td colSpan={allMonths.length + 2} style={{ border: '1px solid #b2ebf2', padding: '0.5rem' }}>{region}</td>
                                        </tr>
                                        {regionEntries.map((entry, i) => (
                                            <tr key={entry.id} style={{ borderBottom: '1px dotted #aaa' }}>
                                                <td style={{ border: '1px solid #b2ebf2', padding: '0.5rem' }}>{entry.item_name}</td>
                                                {allMonths.map(m => {
                                                    const [year, month] = m.split('-');
                                                    const val = getQty(entry, parseInt(year), parseInt(month));
                                                    return <td key={m} style={{ border: '1px solid #b2ebf2', padding: '0.5rem', textAlign: 'center' }}>{val !== '' ? Number(val).toLocaleString() : ''}</td>;
                                                })}
                                                <td style={{ border: '1px solid #b2ebf2', padding: '0.5rem', fontWeight: 'bold', background: '#e0f7fa' }}>{getItemTotal(entry).toLocaleString()}</td>
                                            </tr>
                                        ))}
                                        {/* Region total row */}
                                        <tr style={{ background: '#fffde7', fontWeight: 'bold' }}>
                                            <td style={{ border: '1px solid #b2ebf2', padding: '0.5rem' }}>Total {region}</td>
                                            {allMonths.map(m => {
                                                const [year, month] = m.split('-');
                                                const val = getMonthTotal(regionEntries, parseInt(year), parseInt(month));
                                                return <td key={m} style={{ border: '1px solid #b2ebf2', padding: '0.5rem', textAlign: 'center' }}>{val.toLocaleString()}</td>;
                                            })}
                                            <td style={{ border: '1px solid #b2ebf2', padding: '0.5rem', fontWeight: 'bold', background: '#e0f7fa' }}>{getRegionTotal(regionEntries).toLocaleString()}</td>
                                        </tr>
                                    </React.Fragment>
                                ))}
                                {/* Grand total row */}
                                <tr style={{ background: '#b2ebf2', fontWeight: 'bold' }}>
                                    <td style={{ border: '1px solid #2196f3', padding: '0.5rem' }}>Total Sites</td>
                                    {allMonths.map(m => {
                                        const [year, month] = m.split('-');
                                        const total = Object.values(groupedByRegion).reduce((sum, regionEntries) => sum + getMonthTotal(regionEntries, parseInt(year), parseInt(month)), 0);
                                        return <td key={m} style={{ border: '1px solid #2196f3', padding: '0.5rem', textAlign: 'center' }}>{total.toLocaleString()}</td>;
                                    })}
                                    <td style={{ border: '1px solid #2196f3', padding: '0.5rem', fontWeight: 'bold', background: '#e0f7fa' }}>{getGrandTotal().toLocaleString()}</td>
                                </tr>
                            </tbody>
                        </table>
                        <div style={{ display: 'flex', gap: '0.5rem', marginTop: '1rem' }}>
                            <button
                                className="stylish-btn"
                                onClick={() => {
                                    // Generate CSV
                                    let csv = '';
                                    // Header row: Activities, months, Total
                                    csv += 'Activities,';
                                    allMonths.forEach(m => {
                                        const [year, month] = m.split('-');
                                        csv += `${monthNames[month-1]} ${year},`;
                                    });
                                    csv += 'Total\n';

                                    // Regions and items
                                    Object.entries(groupedByRegion).forEach(([region, regionEntries]) => {
                                        // Region header row
                                        csv += `${region},`;
                                        csv += Array(allMonths.length).fill('').join(',') + ',\n';
                                        // Items
                                        regionEntries.forEach(entry => {
                                            csv += `${entry.item_name},`;
                                            allMonths.forEach(m => {
                                                const [year, month] = m.split('-');
                                                csv += `${getQty(entry, parseInt(year), parseInt(month))},`;
                                            });
                                            csv += `${getItemTotal(entry)}\n`;
                                        });
                                        // Region total row
                                        csv += `Total ${region},`;
                                        allMonths.forEach(m => {
                                            const [year, month] = m.split('-');
                                            csv += `${getMonthTotal(regionEntries, parseInt(year), parseInt(month))},`;
                                        });
                                        csv += `${getRegionTotal(regionEntries)}\n`;
                                    });
                                    // Grand total row
                                    csv += 'Total Sites,';
                                    allMonths.forEach(m => {
                                        const [year, month] = m.split('-');
                                        const total = Object.values(groupedByRegion).reduce((sum, regionEntries) => sum + getMonthTotal(regionEntries, parseInt(year), parseInt(month)), 0);
                                        csv += `${total},`;
                                    });
                                    csv += `${getGrandTotal()}\n`;

                                    // Download CSV
                                    const blob = new Blob([csv], { type: 'text/csv' });
                                    const url = URL.createObjectURL(blob);
                                    const a = document.createElement('a');
                                    a.href = url;
                                    a.download = 'general_rop_table.csv';
                                    document.body.appendChild(a);
                                    a.click();
                                    document.body.removeChild(a);
                                    URL.revokeObjectURL(url);
                                }}
                            >
                                Download CSV
                            </button>
                            <button className="stylish-btn danger" onClick={() => setShowGeneralRop(false)}>
                                Close
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {showForm && (
                <div style={{
                    position: 'fixed',
                    top: 0,
                    left: 0,
                    width: '100vw',
                    height: '100vh',
                    background: 'rgba(0,0,0,0.3)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    zIndex: 1000
                }}>
                    <div style={{
                        background: '#fff',
                        borderRadius: '12px',
                        padding: '2rem',
                        minWidth: '500px',
                        boxShadow: '0 4px 32px #00bcd44a',
                        maxHeight: '80vh',
                        overflowY: 'auto'
                    }}>
                        <form className="project-form" onSubmit={handleSubmit}>
                            <div >
                            <button style={{
                                  
                                  widows:'fit-content',
                                  padding:'0.4rem',
                                  float:'right'
                                  }}
                             className="stylish-btn danger" onClick={() => setShowForm(false)}>
                                <FaTimes/>
                            </button>
                        </div>
                            <input
                                type="text"
                                placeholder="Project ID"
                                name="project_id"
                                value={formData.project_id}
                                onChange={e => setFormData({ ...formData, project_id: e.target.value })}
                                required
                                disabled={isEditing} // Prevent editing project_id on update if needed
                            />
                            <input
                                type="text"
                                placeholder="Project Name"
                                name="project_name"
                                value={formData.project_name}
                                onChange={e => setFormData({ ...formData, project_name: e.target.value })}
                                required
                            />
                            <input
                                type="text"
                                placeholder="Item Name"
                                name="item_name"
                                value={formData.item_name}
                                onChange={e => setFormData({ ...formData, item_name: e.target.value })}
                                required
                            />
                            <input
                                type="text"
                                placeholder="Region"
                                name="region"
                                value={formData.region}
                                onChange={e => setFormData({ ...formData, region: e.target.value })}
                                required
                            />
                            <input
                                type="number"
                                placeholder="Total Quantity"
                                name="total_quantity"
                                value={formData.total_quantity}
                                onChange={e => setFormData({ ...formData, total_quantity: e.target.value })}
                                required
                            />
                            <input
                                type="number"
                                placeholder="Price"
                                name="price"
                                value={formData.price}
                                onChange={e => setFormData({ ...formData, price: e.target.value })}
                                required
                            />
                            <input
                                type="date"
                                name="start_date"
                                value={formData.start_date}
                                onChange={handleDateChange}
                                required
                            />
                            <input
                                type="date"
                                name="end_date"
                                value={formData.end_date}
                                onChange={handleDateChange}
                                required
                            />

                            {distributions.length > 0 && (
                                <div style={{ marginTop: '1rem' }}>
                                    <h4>Monthly Distributions</h4>
                                    {distributions.map((dist, index) => (
                                        <div
                                            key={index}
                                            style={{ display: 'flex', gap: '1rem', alignItems: 'center', marginBottom: '0.5rem' }}
                                        >
                                            <span>{`${dist.month}/${dist.year}`}</span>
                                            <input
                                                type="number"
                                                placeholder="Allocated Quantity"
                                                value={dist.allocated_quantity}
                                                onChange={e => handleDistributionChange(index, e.target.value)}
                                                required
                                            />
                                        </div>
                                    ))}
                                </div>
                            )}

                            <button style={{
                                  
                                  width:'100%',
                                  
                                  }}type="submit" className="stylish-btn">
                                {isEditing ? 'Update' : 'Save'}
                            </button>
                            {/* <button 
                                type="button"
                                className="stylish-btn secondary"
                                style={{ marginLeft: '0.5rem' , width:'fit-content' }}
                                onClick={() => {
                                    resetForm();
                                }}
                            >
                                Cancel
                            </button> */}
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
                            <th>Project Name</th>
                            <th>Item Name</th>
                            <th>Region</th>
                            <th>Total Quantity</th>
                            <th>Price</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {entries.map((entry) => (
                            <React.Fragment key={entry.id}>
                                <tr>
                                    <td>{entry.id}</td>
                                    <td>{entry.project_name}</td>
                                    <td>{entry.item_name}</td>
                                    <td>{entry.region}</td>
                                    <td>{entry.total_quantity}</td>
                                    <td>{entry.price}</td>
                                    <td>
                                        <button
                                            className="stylish-btn"
                                            style={{ width: '100%', margin: '0.5rem' }}
                                            onClick={() => {
                                                setDetailsEntry(entry);
                                                setShowDetails(true);
                                            }}
                                        >
                                            View Details
                                        </button>
                                        <button
                                            className="stylish-btn secondary"
                                            style={{ width: '46%', margin: '0.5rem' }}
                                            onClick={() => handleEdit(entry)}
                                        >
                                            Edit
                                        </button>
                                        <button
                                            className="stylish-btn danger"
                                            style={{ width: '46%', margin: '0.5rem -0.5rem 0rem 0rem', float: 'right' }}
                                            onClick={() => handleDelete(entry.id)}
                                        >
                                            Delete
                                        </button>
                                    </td>
                                </tr>
                                {showDetails && detailsEntry && (
                                    <div style={{
                                        position: 'fixed',
                                        top: 0,
                                        left: 0,
                                        width: '100vw',
                                        height: '100vh',
                                        background: 'rgba(0,0,0,0.3)',
                                        display: 'flex',
                                        alignItems: 'center',
                                        justifyContent: 'center',
                                        zIndex: 1000
                                    }}>
                                        <div style={{
                                            background: '#fff',
                                            borderRadius: '12px',
                                            padding: '2rem',
                                            minWidth: '500px',
                                            boxShadow: '0 4px 32px #00bcd44a',
                                            maxHeight: '80vh',
                                            overflowY: 'auto'
                                        }}>
                                            <h3 style={{ marginBottom: '1rem' }}>Details for {detailsEntry.item_name}</h3>
                                            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.95rem', marginBottom: '1rem' }}>
                                                <thead>
                                                    <tr>
                                                        <th>Month</th>
                                                        <th>Year</th>
                                                        <th>Allocated Quantity</th>
                                                        <th>Latest Estimate</th>
                                                    </tr>
                                                </thead>
                                                <tbody>
                                                    {detailsEntry.distributions.map((d, idx) => (
                                                        <tr key={idx}>
                                                            <td>{d.month}</td>
                                                            <td>{d.year}</td>
                                                            <td>{d.allocated_quantity}</td>
                                                            <td>{(d.allocated_quantity * detailsEntry.price).toLocaleString()}</td>
                                                        </tr>
                                                    ))}
                                                </tbody>
                                            </table>
                                            <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                                                <button className="stylish-btn danger" onClick={() => setShowDetails(false)}>
                                                    Close
                                                </button>
                                            </div>
                                        </div>
                                    </div>
                                )}
                            </React.Fragment>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
}
