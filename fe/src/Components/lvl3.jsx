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
    service_type: [],
};

const initialItemState = {
    item_name: '',
    item_details: '',
    vendor_part_number: '',
    service_type: [],
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

    const handleMultiSelectChange = (e) => {
        const selectedValues = Array.from(e.target.selectedOptions, option => option.value);
        setFormData(prev => ({ ...prev, service_type: selectedValues }));
    };

    const handleItemChange = (e) => {
        const { name, value } = e.target;
        setItemFormData(prev => ({ ...prev, [name]: value }));
    };

    const handleItemMultiSelectChange = (e) => {
        const selectedValues = Array.from(e.target.selectedOptions, option => option.value);
        setItemFormData(prev => ({ ...prev, service_type: selectedValues }));
    };

    const handleAddItem = (lvl3Id) => {
        setItemFormData(initialItemState);
        setEditingItemData({ lvl3Id, itemId: null });
        setShowItemForm(true);
    };

    const handleEditItem = (lvl3Id, item) => {
        setItemFormData({
            ...item,
            service_type: (item.service_type || []).map(name => SERVICE_VALUES[name])
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
            price: parseInt(itemFormData.price, 10),
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
            total_price: parseInt(formData.total_price, 10),
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
            service_type: (entry.service_type || []).map(name => SERVICE_VALUES[name]),
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
        <div className="project-container">
            <div className="header-row">
                <h2>Lvl3 Entries</h2>
                <button className="new-project-btn" onClick={() => { clearForm(); setShowForm(!showForm); }}>
                    {showForm ? 'Cancel' : '+ New Entry'}
                </button>
            </div>

            {showForm && (
                <div className="modal-overlay">
                    <div className="modal-content">
                        <form className="project-form" onSubmit={handleSubmit}>
                            <button className="close-btn stylish-btn danger" onClick={clearForm} type="button">X</button>
                            <h3>{editingEntry ? 'Edit Lvl3 Entry' : 'New Lvl3 Entry'}</h3>
                            <input type="text" name="project_id" placeholder="Project ID" value={formData.project_id} onChange={handleChange} required disabled={!!editingEntry} />
                            <input type="text" name="project_name" placeholder="Project Name" value={formData.project_name} onChange={handleChange} required />
                            <input type="text" name="item_name" placeholder="Item Name" value={formData.item_name} onChange={handleChange} required />
                            <input type="text" name="uom" placeholder="UOM" value={formData.uom} onChange={handleChange} required />
                            <input type="number" name="total_quantity" placeholder="Total Quantity" value={formData.total_quantity} onChange={handleChange} required />
                            <input type="number" name="total_price" placeholder="Total Price" value={formData.total_price} onChange={handleChange} required />
                            <select multiple name="service_type" value={formData.service_type} onChange={handleMultiSelectChange}>
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

            {showItemForm && (
                <div className="modal-overlay">
                    <div className="modal-content">
                        <form className="project-form" onSubmit={handleSaveItem}>
                            <button className="close-btn stylish-btn danger" onClick={() => setShowItemForm(false)} type="button">X</button>
                            <h3>{editingItemData?.itemId ? 'Edit Item' : 'Add New Item'}</h3>
                            <input type="text" name="item_name" placeholder="Item Name" value={itemFormData.item_name} onChange={handleItemChange} required />
                            <input type="text" name="item_details" placeholder="Item Details" value={itemFormData.item_details} onChange={handleItemChange} />
                            <input type="text" name="vendor_part_number" placeholder="Vendor Part Number" value={itemFormData.vendor_part_number} onChange={handleItemChange} />
                            <input type="text" name="category" placeholder="Category" value={itemFormData.category} onChange={handleItemChange} />
                            <input type="text" name="uom" placeholder="UOM" value={itemFormData.uom} onChange={handleItemChange} />
                            <input type="number" name="quantity" placeholder="Quantity" value={itemFormData.quantity} onChange={handleItemChange} required />
                            <input type="number" name="price" placeholder="Price" value={itemFormData.price} onChange={handleItemChange} required />
                            <select multiple name="service_type" value={itemFormData.service_type} onChange={handleItemMultiSelectChange}>
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

            {error && <div className="error">{error}</div>}
            {success && <div className="success">{success}</div>}

            <div className="project-table-container">
                <table className="project-table">
                    <thead>
                        <tr>
                            <th></th>
                            <th>Project ID</th>
                            <th>Project Name</th>
                            <th>Item Name</th>
                            <th>UOM</th>
                            <th>Total Quantity</th>
                            <th>Total Price</th>
                            <th>Service Type</th>
                            <th style={{ width: '160px' }}>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {paginatedEntries.map((entry) => (
                            <>
                                <tr key={entry.id}>
                                    <td>
                                        <button onClick={() => setShowItemsForId(showItemsForId === entry.id ? null : entry.id)} className="expand-btn">
                                            {showItemsForId === entry.id ? <MdExpandLess /> : <MdExpandMore />}
                                        </button>
                                    </td>
                                    <td>{entry.project_id}</td>
                                    <td>{entry.project_name}</td>
                                    <td>{entry.item_name}</td>
                                    <td>{entry.uom}</td>
                                    <td>{entry.total_quantity?.toLocaleString()}</td>
                                    <td>{entry.total_price?.toLocaleString()}</td>
                                    <td>{(entry.service_type || []).map(val => SERVICE_LABELS[val] || val).join(', ')}</td>
                                    <td style={{ textAlign: 'center' }}>
                                        <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'center' }}>
                                            <button className="stylish-btn" onClick={() => handleEditClick(entry)}>Details</button>
                                            <button className="stylish-btn danger" onClick={() => handleDelete(entry)}>Delete</button>
                                        </div>
                                    </td>
                                </tr>
                                {showItemsForId === entry.id && (
                                    <tr className="items-row-container">
                                        <td colSpan="9">
                                            <div className="sub-table-wrapper">
                                                <h4>Items for {entry.item_name}</h4>
                                                <button className="stylish-btn" onClick={() => handleAddItem(entry.id)}>+ Add New Item</button>
                                                <table className="project-sub-table">
                                                    <thead>
                                                        <tr>
                                                            <th>Item Name</th>
                                                            <th>Details</th>
                                                            <th>Part #</th>
                                                            <th>Category</th>
                                                            <th>UOM</th>
                                                            <th>Quantity</th>
                                                            <th>Price</th>
                                                            <th>Service Type</th>
                                                            <th>Actions</th>
                                                        </tr>
                                                    </thead>
                                                    <tbody>
                                                        {(entry.items || []).map((item) => (
                                                            <tr key={item.id}>
                                                                <td>{item.item_name}</td>
                                                                <td>{item.item_details}</td>
                                                                <td>{item.vendor_part_number}</td>
                                                                <td>{item.category}</td>
                                                                <td>{item.uom}</td>
                                                                <td>{item.quantity}</td>
                                                                <td>{item.price}</td>
                                                                <td>{(item.service_type || []).map(val => SERVICE_LABELS[val] || val).join(', ')}</td>
                                                                <td>
                                                                    <button className="stylish-btn" onClick={() => handleEditItem(entry.id, item)}>Edit</button>
                                                                    <button className="stylish-btn danger" onClick={() => handleDeleteItem(entry.id, item.id)}>Delete</button>
                                                                </td>
                                                            </tr>
                                                        ))}
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
            </div>

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