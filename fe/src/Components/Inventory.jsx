import { useEffect, useState } from 'react';
import '../css/Project.css';

const INVENTORY_PER_PAGE = 10;

export default function Inventory() {
    const [inventory, setInventory] = useState([]);
    const [showForm, setShowForm] = useState(false);
    const [formData, setFormData] = useState({
        site_id: '',
        site_name: '',
        slot_id: '',
        port_id: '',
        status: '',
        company_id: '',
        mnemonic: '',
        clei_code: '',
        part_no: '',
        software_no: '',
        factory_id: '',
        serial_no: '',
        date_id: '',
        manufactured_date: '',
        customer_field: '',
        license_points_consumed: '',
        alarm_status: '',
        Aggregated_alarm_status: ''
    });
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');
    const [currentPage, setCurrentPage] = useState(1);

    const VITE_API_URL = import.meta.env.VITE_API_URL;

    useEffect(() => {
        fetchInventory();
    }, []);

    const fetchInventory = async () => {
        try {
            const res = await fetch(`${VITE_API_URL}/inventory`);
            const data = await res.json();
            setInventory(data);
        } catch {
            setError('Failed to fetch inventory');
        }
    };

    const handleChange = (e) => {
        setFormData({ ...formData, [e.target.name]: e.target.value });
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setSuccess('');
        try {
            const res = await fetch(`${VITE_API_URL}/create-inventory`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(formData)
            });

            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.detail || 'Failed to create inventory item');
            }

            setSuccess('Inventory item created successfully!');
            setFormData({
                site_id: '', site_name: '', slot_id: '', port_id: '', status: '',
                company_id: '', mnemonic: '', clei_code: '', part_no: '', software_no: '',
                factory_id: '', serial_no: '', date_id: '', manufactured_date: '',
                customer_field: '', license_points_consumed: '', alarm_status: '',
                Aggregated_alarm_status: ''
            });
            setShowForm(false);
            fetchInventory();
        } catch (err) {
            setError(err.message);
        }
    };

    const paginatedInventory = inventory.slice(
        (currentPage - 1) * INVENTORY_PER_PAGE,
        currentPage * INVENTORY_PER_PAGE
    );

    const totalPages = Math.ceil(inventory.length / INVENTORY_PER_PAGE);

    return (
        <div className="project-container">
            <div className="header-row">
                <h2>Inventory</h2>
                <button className="new-project-btn" onClick={() => setShowForm(!showForm)}>
                    + New Inventory
                </button>
            </div>

            {showForm && (
                <form className="project-form" onSubmit={handleSubmit}>
                    {Object.keys(formData).map((key) => (
                        <input
                            key={key}
                            type="text"
                            name={key}
                            placeholder={key.replace(/_/g, ' ')}
                            value={formData[key]}
                            onChange={handleChange}
                            required
                        />
                    ))}
                    <button type="submit">Save</button>
                </form>
            )}

            {error && <div className="error">{error}</div>}
            {success && <div className="success">{success}</div>}

            <div className="project-table-container">
                <table className="project-table">
                    <thead>
                        <tr>
                            {Object.keys(formData).map((key) => (
                                <th key={key}>{key.replace(/_/g, ' ')}</th>
                            ))}
                        </tr>
                    </thead>
                    <tbody>
                        {paginatedInventory.map((item, index) => (
                            <tr key={index}>
                                {Object.keys(formData).map((key) => (
                                    <td key={key}>{item[key]}</td>
                                ))}
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
