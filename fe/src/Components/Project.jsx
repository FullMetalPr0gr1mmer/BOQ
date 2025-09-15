import { useEffect, useState } from 'react';
import '../css/Dismantling.css';

const PROJECTS_PER_PAGE = 5;

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
    const [authError, setAuthError] = useState('');

    const VITE_API_URL = import.meta.env.VITE_API_URL;

    const getAuthHeaders = () => {
        const token = localStorage.getItem('token');
        if (token) {
            return {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            };
        }
        return { 'Content-Type': 'application/json' };
    };

    useEffect(() => {
        fetchProjects();
    }, []);

    const fetchProjects = async () => {
        try {
            const res = await fetch(`${VITE_API_URL}/get_project`, {
                method: 'GET',
                headers: getAuthHeaders()
            });

            if (res.status === 401 || res.status === 403) {
                const err = await res.json();
                setAuthError(err.detail || "You are not authorized to view projects.");
                setProjects([]);
                return;
            }

            const data = await res.json();
            setProjects(data);
        } catch (err) {
            setError('Failed to fetch projects');
        }
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setSuccess('');
        setAuthError('');
        
        const projectData = { po, project_name: projectName, pid };

        try {
            let res;
            if (editingProject) {
                res = await fetch(`${VITE_API_URL}/update_project/${editingProject.pid + editingProject.po}`, {
                    method: 'PUT',
                    headers: getAuthHeaders(),
                    body: JSON.stringify({ project_name: projectName }),
                });
            } else {
                res = await fetch(`${VITE_API_URL}/create_project`, {
                    method: 'POST',
                    headers: getAuthHeaders(),
                    body: JSON.stringify(projectData),
                });
            }

            if (res.status === 401 || res.status === 403) {
                const err = await res.json();
                setAuthError(err.detail || 'You are not authorized to perform this action.');
                return;
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
    
    const clearForm = () => {
        setPo('');
        setPid('');
        setProjectName('');
        setEditingProject(null);
        setShowForm(false);
    };

    const handleEditClick = (proj) => {
        setEditingProject(proj);
        setPo(proj.po);
        setPid(proj.pid);
        setProjectName(proj.project_name);
        setShowForm(true);
    };

    const handleDelete = async (proj) => {
        if (!window.confirm(`Delete project ${proj.pid} - ${proj.project_name}?`)) return;

        try {
            const res = await fetch(`${VITE_API_URL}/delete_project/${proj.pid + proj.po}`, {
                method: 'DELETE',
                headers: getAuthHeaders(),
            });

            if (res.status === 401 || res.status === 403) {
                const err = await res.json();
                setAuthError(err.detail || 'You are not authorized to delete this project.');
                return;
            }

            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.detail || 'Failed to delete project');
            }

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
        <div className="dismantling-container">
            <div className="dismantling-header-row">
                <h2>Projects</h2>
                <button 
                    className="upload-btn" 
                    onClick={() => { clearForm(); setShowForm(!showForm); }}>
                    {showForm ? 'Cancel' : '+ New Project'}
                </button>
            </div>
            
            {error && <div className="dismantling-message error">{error}</div>}
            {success && <div className="dismantling-message success">{success}</div>}
            
            {authError && (
                <div className="">
                    <div className="">
                        <span className="" onClick={() => setAuthError('')}>&times;</span>
                        <div className="">
                            <p>{authError}</p>
                        </div>
                    </div>
                </div>
            )}
            
            {showForm && (
                <div className="modal-overlay">
                    <div className="modal-content">
                        <form className="project-form" onSubmit={handleSubmit}>
                            <div className="modal-header-row" style={{ justifyContent: 'space-between' }}>
                                <h3 className="modal-title">
                                    {editingProject ? `Editing Project: '${editingProject.project_name}'` : 'New Project'}
                                </h3>
                                <button className="modal-close-btn" onClick={() => setShowForm(false)} type="button">
                                    &times;
                                </button>
                            </div>
                            <input
                                className="search-input"
                                type="text"
                                placeholder="Purchase Order"
                                value={po}
                                onChange={e => setPo(e.target.value)}
                                required
                                disabled={!!editingProject}
                            />
                            <input
                                className="search-input"
                                type="text"
                                placeholder="Project Name"
                                value={projectName}
                                onChange={e => setProjectName(e.target.value)}
                                required
                            />
                            <input
                                className="search-input"
                                type="text"
                                placeholder="Project ID"
                                value={pid}
                                onChange={e => setPid(e.target.value)}
                                required
                                disabled={!!editingProject}
                            />
                            <button className="upload-btn" type="submit">
                                {editingProject ? 'Update' : 'Save'}
                            </button>
                        </form>
                    </div>
                </div>
            )}
            
            <div className="dismantling-table-container">
                <table className="dismantling-table">
                    <thead>
                        <tr>
                            <th style={{ textAlign: 'center' }}>Project ID</th>
                            <th style={{ textAlign: 'center' }}>Project Name</th>
                            <th style={{ textAlign: 'center' }}>Purchase Order</th>
                            <th style={{ textAlign: 'center' }}>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {paginatedProjects.map((proj, index) => (
                            <tr key={index}>
                                <td style={{ textAlign: 'center' }}>{proj.pid}</td>
                                <td style={{ textAlign: 'center' }}>{proj.project_name}</td>
                                <td style={{ textAlign: 'center' }}>{proj.po}</td>
                                <td style={{ textAlign: 'center' }}>
                                    <div className="actions-cell">
                                        <button
                                            className="pagination-btn"
                                            onClick={() => handleEditClick(proj)}
                                        >
                                            Details
                                        </button>
                                        <button
                                            className="clear-btn"
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
                <div className="dismantling-pagination">
                    {Array.from({ length: totalPages }, (_, i) => (
                        <button
                            key={i}
                            className={`pagination-btn ${i + 1 === currentPage ? 'active-page' : ''}`}
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