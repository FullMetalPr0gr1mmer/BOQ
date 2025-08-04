import { useEffect, useState } from 'react';
import '../css/Project.css'; // Shared styling

const ENTRIES_PER_PAGE = 10;

const SERVICE_LABELS = {
    "1": "Software",
    "2": "Hardware",
    "3": "Service"
};

export default function Lvl3() {
    const [entries, setEntries] = useState([]);
    const [showForm, setShowForm] = useState(false);
    const [formData, setFormData] = useState({
        project_id: '',
        project_name: '',
        item_name: '',
        uom: '',
        total_quantity: '',
        total_price: '',
        service_type: []
    });
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');
    const [currentPage, setCurrentPage] = useState(1);

    const VITE_API_URL = import.meta.env.VITE_API_URL;

    useEffect(() => {
        fetchLvl3();
    }, []);

    const fetchLvl3 = async () => {
        try {
            const res = await fetch(`${VITE_API_URL}/get-lvl3`);
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

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setSuccess('');

        const payload = {
            ...formData,
            total_quantity: parseInt(formData.total_quantity),
            total_price: parseInt(formData.total_price),
        };

        try {
            const res = await fetch(`${VITE_API_URL}/create-lvl3`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.detail || 'Failed to create entry');
            }

            setSuccess('Lvl3 entry created successfully!');
            setFormData({
                project_id: '',
                project_name: '',
                item_name: '',
                uom: '',
                total_quantity: '',
                total_price: '',
                service_type: []
            });
            setShowForm(false);
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
                <button className="new-project-btn" onClick={() => setShowForm(!showForm)}>
                    + New Entry
                </button>
            </div>

            {showForm && (
                <form className="project-form" onSubmit={handleSubmit}>
                    <input type="text" name="project_id" placeholder="Project ID" value={formData.project_id} onChange={handleChange} required />
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

                    <button type="submit">Save</button>
                </form>
            )}

            {error && <div className="error">{error}</div>}
            {success && <div className="success">{success}</div>}

            <div className="project-table-container">
                <table className="project-table">
                    <thead>
                        <tr>
                            <th>Project ID</th>
                            <th>Project Name</th>
                            <th>Item Name</th>
                            <th>UOM</th>
                            <th>Total Quantity</th>
                            <th>Total Price</th>
                            <th>Service Type</th>
                        </tr>
                    </thead>
                    <tbody>
                        {paginatedEntries.map((entry, index) => (
                            <tr key={index}>
                                <td>{entry.project_id}</td>
                                <td>{entry.project_name}</td>
                                <td>{entry.item_name}</td>
                                <td>{entry.uom}</td>
                                <td>{entry.total_quantity}</td>
                                <td>{entry.total_price}</td>
                                <td>
                                    {entry.service_type.map((val, idx) => SERVICE_LABELS[val] || val).join(', ')}
                                </td>
                            </tr>
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
