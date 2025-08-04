import { useEffect, useState } from 'react';
import '../css/Project.css'; // Shared styling

const ENTRIES_PER_PAGE = 10;

const SERVICE_LABELS = {
    "1": "Software",
    "2": "Hardware",
    "3": "Service"
};

export default function Lvl1() {
    const [entries, setEntries] = useState([]);
    const [showForm, setShowForm] = useState(false);
    const [formData, setFormData] = useState({
        project_id: '',
        project_name: '',
        item_name: '',
        region: '',
        quantity: '',
        price: '',
        service_type: []
    });
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');
    const [currentPage, setCurrentPage] = useState(1);

    const VITE_API_URL = import.meta.env.VITE_API_URL;

    useEffect(() => {
        fetchLvl1();
    }, []);

    const fetchLvl1 = async () => {
        try {
            const res = await fetch(`${VITE_API_URL}/get-lvl1`);
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
            quantity: parseInt(formData.quantity),
            price: parseInt(formData.price),
        };

        try {
            const res = await fetch(`${VITE_API_URL}/create-lvl1`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.detail || 'Failed to create entry');
            }

            setSuccess('Lvl1 entry created successfully!');
            setFormData({
                project_id: '',
                project_name: '',
                item_name: '',
                region: '',
                quantity: '',
                price: '',
                service_type: []
            });
            setShowForm(false);
            fetchLvl1();
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
                <h2>Lvl1 Entries</h2>
                <button className="new-project-btn" onClick={() => setShowForm(!showForm)}>
                    + New Entry
                </button>
            </div>

            {showForm && (
                <form className="project-form" onSubmit={handleSubmit}>
                    <input type="text" name="project_id" placeholder="Project ID" value={formData.project_id} onChange={handleChange} required />
                    <input type="text" name="project_name" placeholder="Project Name" value={formData.project_name} onChange={handleChange} required />
                    <input type="text" name="item_name" placeholder="Item Name" value={formData.item_name} onChange={handleChange} required />
                    <input type="text" name="region" placeholder="Region" value={formData.region} onChange={handleChange} />
                    <input type="number" name="quantity" placeholder="Quantity" value={formData.quantity} onChange={handleChange} required />
                    <input type="number" name="price" placeholder="Price" value={formData.price} onChange={handleChange} required />
                    
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
                            <th>Region</th>
                            <th>Quantity</th>
                            <th>Price</th>
                            <th>Service Type</th>
                        </tr>
                    </thead>
                    <tbody>
                        {paginatedEntries.map((entry, index) => (
                            <tr key={index}>
                                <td>{entry.project_id}</td>
                                <td>{entry.project_name}</td>
                                <td>{entry.item_name}</td>
                                <td>{entry.region}</td>
                                <td>{entry.quantity}</td>
                                <td>{entry.price}</td>
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
