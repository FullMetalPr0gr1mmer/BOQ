import { useEffect, useState } from 'react';
import '../css/Project.css';

const SITES_PER_PAGE = 10;

export default function Site() {
    const [sites, setSites] = useState([]);
    const [showForm, setShowForm] = useState(false);
    const [projectId, setProjectId] = useState('');
    const [siteName, setSiteName] = useState('');
    const [siteId, setSiteId] = useState('');
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');
    const [currentPage, setCurrentPage] = useState(1);

    const VITE_API_URL = import.meta.env.VITE_API_URL;

    useEffect(() => {
        fetchSites();
    }, []);

    const fetchSites = async () => {
        try {
            const res = await fetch(`${VITE_API_URL}/get-site`);
            const data = await res.json();

            setSites(data);


        } catch {
            setError('Failed to fetch sites');
        }
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setSuccess('');
        const newSite = {
            site_id: siteId,
            site_name: siteName,
            pid_po: projectId,


        };
        try {
            console.log(newSite);
            const res = await fetch(`${VITE_API_URL}/add-site`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(newSite)
            });

            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.detail || 'Failed to create Site');
            }

            setSuccess('Site created successfully!');
            setProjectId('');
            setSiteId('');
            setSiteName('');
            setShowForm(false);
            fetchSites();
        } catch (err) {
            setError(err.message);
        }
    };

    const paginatedSites = sites.slice(
        (currentPage - 1) * SITES_PER_PAGE,
        currentPage * SITES_PER_PAGE
    );

    const totalPages = Math.ceil(sites.length / SITES_PER_PAGE);

    return (
        <div className="project-container">
            <div className="header-row">
                <h2>Sites</h2>
                <button className="new-project-btn" onClick={() => setShowForm(!showForm)}>
                    + New Site
                </button>
            </div>

            {showForm && (
                <form className="project-form" onSubmit={handleSubmit}>
                    <input
                        type="text"
                        placeholder="Project Id"
                        value={projectId}
                        onChange={e => setProjectId(e.target.value)}
                        required
                    />
                    <input
                        type="text"
                        placeholder="Site Name"
                        value={siteName}
                        onChange={e => setSiteName(e.target.value)}
                        required
                    />
                    <input
                        type="text"
                        placeholder="Site ID"
                        value={siteId}
                        onChange={e => setSiteId(e.target.value)}
                        required
                    />
                    <button type="submit">Save</button>
                </form>
            )}

            {error && <div className="error">{error}</div>}
            {success && <div className="success">{success}</div>}

            <div className="project-table-container">
                <table className="project-table">
                    <thead>
                        <tr>
                            <th>Site ID</th>
                            <th>Site Name</th>
                            <th>Project ID</th>
                        </tr>
                    </thead>
                    <tbody>
                        {paginatedSites.map((site, index) => (
                            <tr key={index}>
                                <td>{site.site_id}</td>
                                <td>{site.site_name}</td>
                                <td>{site.project_id}</td>
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
