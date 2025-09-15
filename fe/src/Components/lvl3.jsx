import { useEffect, useState } from 'react';
import '../css/Project.css'; // Shared styling
import { MdExpandMore, MdExpandLess } from 'react-icons/md';

const ENTRIES_PER_PAGE = 10;

const SERVICE_LABELS = {
    "1": "Software",
    "2": "Hardware",
    "3": "Service"
};

const SERVICE_VALUES = {
    "Software": "1",
    "Hardware": "2",
    "Service": "3"
};

const initialLvl3State = {
    project_id: '',
    project_name: '',
    item_name: '',
    uom: '',
    total_quantity: '',
    total_price: '',
    service_type: '',
};

const initialItemState = {
    item_name: '',
    item_details: '',
    vendor_part_number: '',
    service_type: '',
    category: '',
    uom: '',
    quantity: '',
    price: ''
};

export default function Lvl3() {
    const [entries, setEntries] = useState([]);
    const [showForm, setShowForm] = useState(false);
    const [editingEntry, setEditingEntry] = useState(null);
    const [formData, setFormData] = useState(initialLvl3State);
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');
    const [currentPage, setCurrentPage] = useState(1);
    const [showItemsForId, setShowItemsForId] = useState(null);
    const [showItemForm, setShowItemForm] = useState(false);
    const [editingItemData, setEditingItemData] = useState(null);
    const [itemFormData, setItemFormData] = useState(initialItemState);

    const VITE_API_URL = import.meta.env.VITE_API_URL;

    useEffect(() => {
        fetchLvl3();
    }, []);

    const fetchLvl3 = async () => {
        try {
            const res = await fetch(`${VITE_API_URL}/lvl3/`);
            const data = await res.json();
            setEntries(data);
        } catch {
            setError('Failed to fetch entries');
        }
    };

    const handleChange = (e) => {
        const { name, value } = e.target;
        setFormData(prev => ({ ...prev, [name]: value }));
    };

    const handleItemChange = (e) => {
        const { name, value } = e.target;
        setItemFormData(prev => ({ ...prev, [name]: value }));
    };

    const handleAddItem = (lvl3Id) => {
        setItemFormData(initialItemState);
        setEditingItemData({ lvl3Id, itemId: null });
        setShowItemForm(true);
    };

    const handleEditItem = (lvl3Id, item) => {
        setItemFormData({
            ...item,
            service_type: (item.service_type && item.service_type.length > 0) 
                ? (SERVICE_VALUES[item.service_type[0]] || item.service_type[0]) 
                : ''
        });
        setEditingItemData({ lvl3Id, itemId: item.id });
        setShowItemForm(true);
    };

    const handleSaveItem = async (e) => {
        e.preventDefault();
        setError('');
        setSuccess('');

        const payload = {
            ...itemFormData,
            quantity: parseInt(itemFormData.quantity, 10),
            price: parseFloat(itemFormData.price),
            service_type: itemFormData.service_type ? [itemFormData.service_type] : []
        };

        const { lvl3Id, itemId } = editingItemData;

        try {
            let res;
            if (itemId) {
                // Update existing item
                res = await fetch(`${VITE_API_URL}/lvl3/${lvl3Id}/items/${itemId}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
            } else {
                // Create new item for an existing Lvl3
                res = await fetch(`${VITE_API_URL}/lvl3/${lvl3Id}/items`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
            }

            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.detail || 'Failed to save item');
            }

            setSuccess(itemId ? 'Item updated successfully!' : 'Item added successfully!');
            setShowItemForm(false);
            setEditingItemData(null);
            fetchLvl3();
        } catch (err) {
            setError(err.message);
        }
    };

    const handleDeleteItem = async (lvl3Id, itemId) => {
        if (!window.confirm("Are you sure you want to delete this item?")) return;
        try {
            const res = await fetch(`${VITE_API_URL}/lvl3/${lvl3Id}/items/${itemId}`, {
                method: 'DELETE'
            });
            if (!res.ok) throw new Error('Failed to delete item');
            setSuccess('Item deleted!');
            fetchLvl3();
        } catch (err) {
            setError(err.message);
        }
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setSuccess('');

        const payload = {
            ...formData,
            total_quantity: parseInt(formData.total_quantity, 10),
            total_price: parseFloat(formData.total_price),
            service_type: formData.service_type ? [formData.service_type] : [],
            items: [] // Ensure no items are sent on Lvl3 create/update
        };

        try {
            let res;
            if (editingEntry) {
                res = await fetch(`${VITE_API_URL}/lvl3/${editingEntry.id}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
            } else {
                res = await fetch(`${VITE_API_URL}/lvl3/create`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
            }

            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.detail || 'Failed to save entry');
            }

            setSuccess(editingEntry ? 'Lvl3 entry updated!' : 'Lvl3 entry created!');
            clearForm();
            fetchLvl3();
        } catch (err) {
            setError(err.message);
        }
    };

const handleUploadCSV = (lvl3Id, parentItemName) => async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setError('');
    setSuccess('');

    const reader = new FileReader();
    reader.onload = async (event) => {
        const text = event.target.result;
        const lines = text.split('\n').filter(line => line.trim() !== '');

        if (lines.length === 0) {
            setError('CSV file is empty.');
            return;
        }

        // Function to parse CSV line properly handling quotes and commas
        const parseCSVLine = (line) => {
            const result = [];
            let current = '';
            let inQuotes = false;
            
            for (let i = 0; i < line.length; i++) {
                const char = line[i];
                
                if (char === '"') {
                    inQuotes = !inQuotes;
                } else if (char === ',' && !inQuotes) {
                    result.push(current.trim());
                    current = '';
                } else {
                    current += char;
                }
            }
            
            // Don't forget the last field
            result.push(current.trim());
            return result;
        };

        const payloadItems = [];
        for (let i = 0; i < lines.length; i++) {
            const line = lines[i].trim();
            
            // Use our custom CSV parser
            const columns = parseCSVLine(line);
            
            if (columns.length < 4) {
                setError(`Error on row ${i + 1}: Expected at least 4 columns, got ${columns.length}.`);
                return;
            }

            // Extract columns directly
            let item_details = columns[0].replace(/^"|"$/g, ''); // Remove surrounding quotes
            let vendor_part_number = columns[1].replace(/^"|"$/g, ''); 
            let uom = columns[2].replace(/^"|"$/g, ''); 
            let priceColumn = columns[3].replace(/^"|"$/g, '');

            // Clean the price column - more robust approach
            let cleanedPriceString = priceColumn;
            
            // Remove "SAR" and any other text
            cleanedPriceString = cleanedPriceString.replace(/SAR/gi, '');
            
            // Remove any leading/trailing whitespace
            cleanedPriceString = cleanedPriceString.trim();
            
            // Remove any remaining non-numeric characters except dots and commas
            cleanedPriceString = cleanedPriceString.replace(/[^0-9.,]/g, '');
            
            // Remove thousands separators (commas) but keep decimal point
            cleanedPriceString = cleanedPriceString.replace(/,/g, '');
            
            const parsedPrice = parseFloat(cleanedPriceString);

            if (isNaN(parsedPrice)) {
                setError(`Error on row ${i + 1}: Could not parse price from "${priceColumn}".`);
                return;
            }

            console.log(`Row ${i + 1}:`, {
                item_details,
                vendor_part_number,
                uom,
                originalPrice: priceColumn,
                cleanedPrice: cleanedPriceString,
                price: parsedPrice,
                allColumns: columns
            });

            payloadItems.push({
                item_name: parentItemName,
                item_details: item_details,
                vendor_part_number: vendor_part_number,
                service_type: ["2"],
                category: "MW",
                uom: uom,
                quantity: 0,
                price: parsedPrice
            });
        }

        try {
            const res = await fetch(`${VITE_API_URL}/lvl3/${lvl3Id}/items/bulk`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payloadItems)
            });

            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.detail || 'Failed to upload items from CSV.');
            }

            setSuccess('Items uploaded successfully!');
            e.target.value = null;
            fetchLvl3();
        } catch (err) {
            setError(err.message);
            e.target.value = null;
        }
    };

    reader.readAsText(file);
};

    const clearForm = () => {
        setFormData(initialLvl3State);
        setEditingEntry(null);
        setShowForm(false);
    };

    const handleEditClick = (entry) => {
        setEditingEntry(entry);
        setFormData({
            project_id: entry.project_id,
            project_name: entry.project_name,
            item_name: entry.item_name,
            uom: entry.uom,
            total_quantity: entry.total_quantity,
            total_price: entry.total_price,
            service_type: (entry.service_type && entry.service_type.length > 0) 
                ? (SERVICE_VALUES[entry.service_type[0]] || entry.service_type[0])
                : '',
        });
        setShowForm(true);
    };

    const handleDelete = async (entry) => {
        if (!window.confirm(`Delete entry ${entry.project_id} - ${entry.item_name}?`)) return;
        try {
            const res = await fetch(`${VITE_API_URL}/lvl3/${entry.id}`, {
                method: 'DELETE'
            });
            if (!res.ok) throw new Error('Failed to delete entry');
            setSuccess('Entry deleted!');
            fetchLvl3();
        } catch (err) {
            setError(err.message);
        }
    };

    const paginatedEntries = entries.slice(
        (currentPage - 1) * ENTRIES_PER_PAGE,
        currentPage * ENTRIES_PER_PAGE
    );

    const totalPages = Math.ceil(entries.length / ENTRIES_PER_PAGE);

    return (
                <div className="dismantling-container">
                            {/* Create/Edit Modal */}
                                                    {showForm && (
                                                        <div className="modal-overlay">
                                                            <div className="modal-content">
                                                                <form className="project-form" onSubmit={handleSubmit}>
                                                                    <div className="modal-header-row" style={{ justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                                                                        <h3 className="modal-title">
                                                                            {editingEntry ? `Editing item : '${formData.item_name}'` : 'New Level 3 Item'}
                                                                        </h3>
                                                                        <button className="modal-close-btn" onClick={clearForm} type="button">&times;</button>
                                                                    </div>
                                                                    <input type="text" name="project_id" placeholder="Project ID" value={formData.project_id} onChange={handleChange} required disabled={!!editingEntry} />
                                                                    <input type="text" name="project_name" placeholder="Project Name" value={formData.project_name} onChange={handleChange} required />
                                                                    <input type="text" name="item_name" placeholder="Item Name" value={formData.item_name} onChange={handleChange} required />
                                                                    <input type="text" name="uom" placeholder="UOM" value={formData.uom} onChange={handleChange} required />
                                                                    <input type="number" name="total_quantity" placeholder="Total Quantity" value={formData.total_quantity} onChange={handleChange}  />
                                                                    <input type="number" name="total_price" placeholder="Total Price" value={formData.total_price} onChange={handleChange} required />
                                                                    <select name="service_type" value={formData.service_type || ''} onChange={handleChange} required>
                                                                        <option value="">Select Service Type</option>
                                                                        <option value="1">Software</option>
                                                                        <option value="2">Hardware</option>
                                                                        <option value="3">Service</option>
                                                                    </select>
                                                                    <button style={{ width: '100%', marginTop: '1rem' }} type="submit" className="stylish-btn">
                                                                        {editingEntry ? 'Update' : 'Save'}
                                                                    </button>
                                                                </form>
                                                            </div>
                                                        </div>
                                                    )}

                            {/* Item Create/Edit Modal */}
                                                    {showItemForm && (
                                                        <div className="modal-overlay">
                                                            <div className="modal-content">
                                                                <form className="project-form" onSubmit={handleSaveItem}>
                                                                    <div className="modal-header-row" style={{ justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                                                                        <h3 className="modal-title">
                                                                            {editingItemData?.itemId ? `Editing item : '${itemFormData.item_name}'` : 'New Level 3 Item'}
                                                                        </h3>
                                                                        <button className="modal-close-btn" onClick={() => setShowItemForm(false)} type="button">&times;</button>
                                                                    </div>
                                                                    <input type="text" name="item_name" placeholder="Item Name" value={itemFormData.item_name} onChange={handleItemChange} required />
                                                                    <input type="text" name="item_details" placeholder="Item Details" value={itemFormData.item_details} onChange={handleItemChange} />
                                                                    <input type="text" name="vendor_part_number" placeholder="Vendor Part Number" value={itemFormData.vendor_part_number} onChange={handleItemChange} />
                                                                    <input type="text" name="category" placeholder="Category" value={itemFormData.category} onChange={handleItemChange} />
                                                                    <input type="text" name="uom" placeholder="UOM" value={itemFormData.uom} onChange={handleItemChange} />
                                                                    <input type="number" name="quantity" placeholder="Quantity" value={itemFormData.quantity} onChange={handleItemChange} required />
                                                                    <input type="number" name="price" placeholder="Price" value={itemFormData.price} onChange={handleItemChange} required />
                                                                    <select name="service_type" value={itemFormData.service_type || ''} onChange={handleItemChange} required>
                                                                        <option value="">Select Service Type</option>
                                                                        <option value="1">Software</option>
                                                                        <option value="2">Hardware</option>
                                                                        <option value="3">Service</option>
                                                                    </select>
                                                                    <button style={{ width: '100%', marginTop: '1rem' }} type="submit" className="stylish-btn">
                                                                        Save Item
                                                                    </button>
                                                                </form>
                                                            </div>
                                                        </div>
                                                    )}
                    {/* Header & Create Button */}
                    <div className="dismantling-header-row">
                        <h2>Level 3 Records</h2>
                        <button className="upload-btn" onClick={() => { clearForm(); setShowForm(!showForm); }}>
                            {showForm ? 'Cancel' : '➕ Create Level 3 Item'}
                        </button>
                    </div>

                    {/* Search */}
                    <div className="dismantling-search-container">
                        <input
                            type="text"
                            placeholder="Filter by Project Name or Item Name..."
                            value={''}
                            onChange={() => {}}
                            className="search-input"
                        />
                    </div>

                    {/* Messages */}
                    {error && <div className="dismantling-message error">{error}</div>}
                    {success && <div className="dismantling-message success">{success}</div>}

                    {/* Table */}
                    <div className="dismantling-table-container">
                        <table className="dismantling-table">
                            <thead>
                                <tr>
                                    <th style={{ width: '30px' }}></th>
                                    <th>Project ID</th>
                                    <th>Project Name</th>
                                    <th>Item Name</th>
                                    <th>UOM</th>
                                    <th>Total Quantity</th>
                                    <th>Total Price</th>
                                    <th>Service Type</th>
                                    <th>Actions</th>
                                </tr>
                            </thead>
                            <tbody>
                                {paginatedEntries.length === 0 ? (
                                    <tr>
                                        <td colSpan={9} className="no-results">No results</td>
                                    </tr>
                                ) : (
                                    paginatedEntries.map((entry) => (
                                        <>
                                            <tr key={entry.id}>
                                                <td>
                                                    <button
                                                        onClick={() => setShowItemsForId(showItemsForId === entry.id ? null : entry.id)}
                                                        className="clear-btn"
                                                        style={{ padding: '4px 8px', fontSize: '12px', transform: showItemsForId === entry.id ? 'rotate(90deg)' : 'rotate(0deg)', transition: 'transform 0.2s' }}
                                                    >
                                                        ▶
                                                    </button>
                                                </td>
                                                <td>{entry.project_id}</td>
                                                <td>{entry.project_name}</td>
                                                <td>{entry.item_name}</td>
                                                <td>{entry.uom}</td>
                                                <td>{entry.total_quantity?.toLocaleString()}</td>
                                                <td>{entry.total_price?.toLocaleString()}</td>
                                                <td>{(entry.service_type || []).map(val => SERVICE_LABELS[val] || val).join(', ')}</td>
                                                <td className="actions-cell">
                                                    <button className="clear-btn" onClick={() => handleEditClick(entry)}>Edit</button>
                                                    <button className="clear-btn" onClick={() => handleDelete(entry)}>Delete</button>
                                                </td>
                                            </tr>
                                            {showItemsForId === entry.id && (
                                                <tr>
                                                    <td colSpan={9} style={{ padding: 0, background: '#f8fafb' }}>
                                                        <div style={{ padding: '1rem', borderLeft: '4px solid var(--primary-color)' }}>
                                                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                                                                <h4 style={{ margin: 0, color: 'var(--primary-color)' }}>Items for {entry.item_name}</h4>
                                                                <label className="upload-btn" style={{ fontSize: '0.8rem', padding: '0.5rem 1rem' }}>
                                                                    📤 Upload Items CSV
                                                                    <input type="file" accept=".csv" style={{ display: 'none' }} onChange={handleUploadCSV(entry.id, entry.item_name)} />
                                                                </label>
                                                            </div>
                                                            <div style={{ overflowX: 'auto' }}>
                                                                <table className="dismantling-table" style={{ margin: 0 }}>
                                                                    <thead>
                                                                        <tr>
                                                                            <th>Item Name</th>
                                                                            <th>Details</th>
                                                                            <th>Vendor Part #</th>
                                                                            <th>Category</th>
                                                                            <th>UOM</th>
                                                                            <th>Quantity</th>
                                                                            <th>Price</th>
                                                                            <th>Service Type</th>
                                                                            <th>Actions</th>
                                                                        </tr>
                                                                    </thead>
                                                                    <tbody>
                                                                        {(entry.items || []).length === 0 ? (
                                                                            <tr>
                                                                                <td colSpan={9} className="no-results">No items found</td>
                                                                            </tr>
                                                                        ) : (
                                                                            (entry.items || []).map((item) => (
                                                                                <tr key={item.id}>
                                                                                    <td>{item.item_name}</td>
                                                                                    <td>{item.item_details}</td>
                                                                                    <td>{item.vendor_part_number}</td>
                                                                                    <td>{item.category}</td>
                                                                                    <td>{item.uom}</td>
                                                                                    <td>{item.quantity}</td>
                                                                                    <td>{item.price}</td>
                                                                                    <td>{(item.service_type || []).map(val => SERVICE_LABELS[val] || val).join(', ')}</td>
                                                                                    <td className="actions-cell">
                                                                                        <button className="clear-btn" onClick={() => handleEditItem(entry.id, item)}>Edit</button>
                                                                                        <button className="clear-btn" onClick={() => handleDeleteItem(entry.id, item.id)}>Delete</button>
                                                                                    </td>
                                                                                </tr>
                                                                            ))
                                                                        )}
                                                                    </tbody>
                                                                </table>
                                                            </div>
                                                        </div>
                                                    </td>
                                                </tr>
                                            )}
                                        </>
                                    ))
                                )}
                            </tbody>
                        </table>
                    </div>

                    {totalPages > 1 && (
                        <div className="dismantling-pagination">
                            <button className="pagination-btn" disabled={currentPage === 1} onClick={() => setCurrentPage(currentPage - 1)}>Prev</button>
                            <span className="pagination-info">Page {currentPage} of {totalPages}</span>
                            <button className="pagination-btn" disabled={currentPage === totalPages} onClick={() => setCurrentPage(currentPage + 1)}>Next</button>
                        </div>
                    )}
                </div>
    );
}