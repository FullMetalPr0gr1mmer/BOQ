
import { useEffect, useState } from 'react';
import '../css/Project.css';

const PROJECTS_PER_PAGE = 10;

export default function Project() {
    const [projects, setProjects] = useState([]);
    const [showForm, setShowForm] = useState(false);
    const [editingProject, setEditingProject] = useState(null);
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

    // Handle create or update submission
    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setSuccess('');
        const projectData = {
            po,
            project_name: projectName,
            pid
        };
        try {
            let res;
            if (editingProject) {
                res = await fetch(`${VITE_API_URL}/update_project/${editingProject.pid + editingProject.po}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ project_name: projectName }), // only send project_name
                });
            }
            else {
                // Create new
                res = await fetch(`${VITE_API_URL}/create_project`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(projectData),
                });
            }

            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.detail || 'Failed to save project');
            }

            setSuccess(editingProject ? 'Project updated successfully!' : 'Project created successfully!');
            clearForm();
            fetchProjects();
        } catch (err) {
            setError(err.message);
        }
    };

    // Clear form & editing state
    const clearForm = () => {
        setPo('');
        setPid('');
        setProjectName('');
        setEditingProject(null);
        setShowForm(false);
    };

    // Start editing a project - prefill form
    const handleEditClick = (proj) => {
        setEditingProject(proj);
        setPo(proj.po);
        setPid(proj.pid);
        setProjectName(proj.project_name);
        setShowForm(true);
    };

    // Delete project
    const handleDelete = async (proj) => {
        if (!window.confirm(`Delete project ${proj.pid} - ${proj.project_name}?`)) return;
        try {
            const res = await fetch(`${VITE_API_URL}/delete_project/${proj.pid  + proj.po}`, {
                method: 'DELETE',
            });
            if (!res.ok) throw new Error('Failed to delete project');
            setSuccess('Project deleted successfully!');
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
                <button className="new-project-btn" onClick={() => { clearForm(); setShowForm(!showForm); }}>
                    {showForm ? 'Cancel' : '+ New Project'}
                </button>
            </div>

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
                            <div>
                                <button style={{
                                    width: 'fit-content',
                                    padding: '0.4rem',
                                    float: 'right'
                                }}
                                    className="stylish-btn danger" onClick={() => setShowForm(false)} type="button">
                                    X
                                </button>
                            </div>
                            <input
                                type="text"
                                placeholder="Purchase Order"
                                value={po}
                                onChange={e => setPo(e.target.value)}
                                required
                                disabled={!!editingProject}
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
                                disabled={!!editingProject}
                            />
                            <button style={{ width: '100%' }} type="submit" className="stylish-btn">
                                {editingProject ? 'Update' : 'Save'}
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
                            <th>Project ID</th>
                            <th>Project Name</th>
                            <th>Purchase Order</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {paginatedProjects.map((proj, index) => (
                            <tr key={index}>
                                <td>{proj.pid}</td>
                                <td>{proj.project_name}</td>
                                <td>{proj.po}</td>
                                <td style={{ textAlign: 'center' }}>
                                    <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'center' }}>
                                        <button
                                            className="stylish-btn"
                                            style={{ width: '46%' }}
                                            onClick={() => handleEditClick(proj)}
                                        >
                                            Details
                                        </button>
                                        <button
                                            className="stylish-btn danger"
                                            style={{ width: '46%' }}
                                            onClick={() => handleDelete(proj)}
                                        >
                                            Delete
                                        </button>
                                    </div>
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
