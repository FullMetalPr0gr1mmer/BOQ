import { useEffect, useState } from 'react';
import '../css/Project.css';

const PROJECTS_PER_PAGE = 10;

export default function Project() {
    const [projects, setProjects] = useState([]);
    const [showForm, setShowForm] = useState(false);
    const [po, setPo] = useState('');
    const [projectName, setProjectName] = useState('');
    const [pid, setPid] = useState('');
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');
    const [currentPage, setCurrentPage] = useState(1);

    const VITE_API_URL = import.meta.env.VITE_API_URL;

    useEffect(() => {
        fetchProjects();
    }, []);

    const fetchProjects = async () => {
        try {
            const res = await fetch(`${VITE_API_URL}/get_project`);
            const data = await res.json();
            setProjects(data);
        } catch {
            setError('Failed to fetch projects');
        }
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setSuccess('');
        const newProject = {
            po,
            project_name: projectName,
            pid
        };
        try {
            const res = await fetch(`${VITE_API_URL}/create_project`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(newProject)
            });

            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.detail || 'Failed to create project');
            }

            setSuccess('Project created successfully!');
            setPo('');
            setPid('');
            setProjectName('');
            setShowForm(false);
            fetchProjects();
        } catch (err) {
            setError(err.message);
        }
    };

    const paginatedProjects = projects.slice(
        (currentPage - 1) * PROJECTS_PER_PAGE,
        currentPage * PROJECTS_PER_PAGE
    );

    const totalPages = Math.ceil(projects.length / PROJECTS_PER_PAGE);

    return (
        <div className="project-container">
            <div className="header-row">
                <h2>Projects</h2>
                <button className="new-project-btn" onClick={() => setShowForm(!showForm)}>
                    + New Project
                </button>
            </div>

            {showForm && (
                <form className="project-form" onSubmit={handleSubmit}>
                    <input
                        type="text"
                        placeholder="Purchase Order"
                        value={po}
                        onChange={e => setPo(e.target.value)}
                        required
                    />
                    <input
                        type="text"
                        placeholder="Project Name"
                        value={projectName}
                        onChange={e => setProjectName(e.target.value)}
                        required
                    />
                    <input
                        type="text"
                        placeholder="Project ID"
                        value={pid}
                        onChange={e => setPid(e.target.value)}
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
                            <th>Project ID</th>
                            <th>Project Name</th>
                            <th>Purchase Order</th>
                        </tr>
                    </thead>
                    <tbody>
                        {paginatedProjects.map((proj, index) => (
                            <tr key={index}>
                                <td>{proj.pid}</td>
                                <td>{proj.project_name}</td>
                                <td>{proj.po}</td>
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
