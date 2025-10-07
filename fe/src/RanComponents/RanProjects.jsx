import { useEffect, useState } from 'react';
import { apiCall, setTransient } from '../api.js';
import '../css/RAN.css';

const PROJECTS_PER_PAGE = 5;

export default function RanProjects() {
    const [projects, setProjects] = useState([]);
    const [showForm, setShowForm] = useState(false);
    const [editingProject, setEditingProject] = useState(null);
    const [po, setPo] = useState('');
    const [projectName, setProjectName] = useState('');
    const [pid, setPid] = useState('');
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');
    const [currentPage, setCurrentPage] = useState(1);

    useEffect(() => {
        fetchProjects();
    }, []);

    const fetchProjects = async () => {
        try {
            const data = await apiCall('/ran-projects');
            setProjects(data);
        } catch (err) {
            setTransient(setError, 'Failed to fetch projects');
        }
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setSuccess('');
        const projectData = { po, project_name: projectName, pid };
        try {
            if (editingProject) {
                await apiCall(`/ran-projects/${editingProject.pid_po}`, {
                    method: 'PUT',
                    body: JSON.stringify({ project_name: projectName }),
                });
            } else {
                await apiCall('/ran-projects', {
                    method: 'POST',
                    body: JSON.stringify(projectData),
                });
            }
            setTransient(setSuccess, editingProject ? 'Project updated successfully!' : 'Project created successfully!');
            setShowForm(false);
            setEditingProject(null);
            setPo('');
            setProjectName('');
            setPid('');
            fetchProjects();
        } catch (err) {
            setTransient(setError, err.message || 'Failed to save project');
        }
    };

    const handleEdit = (project) => {
        setEditingProject(project);
        setPo(project.po || '');
        setProjectName(project.project_name || '');
        setPid(project.pid || '');
        setShowForm(true);
    };

    const handleDelete = async (project) => {
        if (!window.confirm(`Delete project ${project.project_name}?`)) return;
        try {
            await apiCall(`/ran-projects/${project.pid_po}`, {
                method: 'DELETE'
            });
            setTransient(setSuccess, 'Project deleted successfully!');
            fetchProjects();
        } catch (err) {
            setTransient(setError, err.message || 'Failed to delete project');
        }
    };

    const paginatedProjects = projects.slice((currentPage - 1) * PROJECTS_PER_PAGE, currentPage * PROJECTS_PER_PAGE);
    const totalPages = Math.ceil(projects.length / PROJECTS_PER_PAGE);

    return (
        <div className="dismantling-container">
            <div className="dismantling-header-row">
                <h2>RAN Projects</h2>
                <button 
                    className="upload-btn" 
                    onClick={() => { setShowForm(!showForm); setEditingProject(null); setPo(''); setProjectName(''); setPid(''); }}>
                    {showForm ? 'Cancel' : '+ New Project'}
                </button>
            </div>
            {error && <div className="dismantling-message error">{error}</div>}
            {success && <div className="dismantling-message success">{success}</div>}
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
                        {paginatedProjects.length === 0 ? (
                            <tr><td colSpan={4} style={{ textAlign: 'center', padding: 16 }}>No projects found</td></tr>
                        ) : (
                            paginatedProjects.map((project, idx) => (
                                <tr key={project.pid_po || idx}>
                                    <td style={{ textAlign: 'center' }}>{project.pid}</td>
                                    <td style={{ textAlign: 'center' }}>{project.project_name}</td>
                                    <td style={{ textAlign: 'center' }}>{project.po}</td>
                                    <td style={{ textAlign: 'center' }}>
                                        <div className="actions-cell">
                                            <button
                                                className="pagination-btn"
                                                onClick={() => handleEdit(project)}
                                            >
                                                Details
                                            </button>
                                            <button
                                                className="clear-btn"
                                                onClick={() => handleDelete(project)}
                                            >
                                                Delete
                                            </button>
                                        </div>
                                    </td>
                                </tr>
                            ))
                        )}
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