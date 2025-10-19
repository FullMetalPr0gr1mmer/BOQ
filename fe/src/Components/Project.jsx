import { useEffect, useState } from 'react';
import '../css/Project.css';
import { apiCall, setTransient } from '../api.js';
import StatsCarousel from './shared/StatsCarousel';
import DataTable from './shared/DataTable';
import HelpModal, { HelpList, HelpText } from './shared/HelpModal';
import TitleWithInfo from './shared/InfoButton';
import Pagination from './shared/Pagination';

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
    const [showHelpModal, setShowHelpModal] = useState(false);

    useEffect(() => {
        fetchProjects();
    }, []);

    const fetchProjects = async () => {
        try {
            const data = await apiCall('/get_project', {
                method: 'GET'
            });
            setProjects(data);
        } catch (err) {
            setTransient(setError, 'Failed to fetch projects');
        }
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setError('');
        setSuccess('');
        setAuthError('');

        const projectData = { po, project_name: projectName, pid };

        try {
            if (editingProject) {
                await apiCall(`/update_project/${editingProject.pid + editingProject.po}`, {
                    method: 'PUT',
                    body: JSON.stringify({ project_name: projectName })
                });
            } else {
                await apiCall('/create_project', {
                    method: 'POST',
                    body: JSON.stringify(projectData)
                });
            }

            setTransient(setSuccess, editingProject ? 'Project updated successfully!' : 'Project created successfully!');
            clearForm();
            fetchProjects();
        } catch (err) {
            setTransient(setError, err.message);
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
            await apiCall(`/delete_project/${proj.pid + proj.po}`, {
                method: 'DELETE'
            });

            setTransient(setSuccess, 'Project deleted successfully!');
            fetchProjects();
        } catch (err) {
            setTransient(setError, err.message);
        }
    };
    
    const paginatedProjects = projects.slice(
        (currentPage - 1) * PROJECTS_PER_PAGE,
        currentPage * PROJECTS_PER_PAGE
    );
    const totalPages = Math.ceil(projects.length / PROJECTS_PER_PAGE);

    // Define stat cards for the carousel
    const statCards = [
        { label: 'Total Projects', value: projects.length },
        { label: 'Current Page', value: `${currentPage} / ${totalPages || 1}` },
        { label: 'Showing', value: `${paginatedProjects.length} projects` },
        { label: 'Projects Per Page', value: PROJECTS_PER_PAGE }
    ];

    // Define table columns
    const tableColumns = [
        { key: 'pid', label: 'Project ID' },
        { key: 'project_name', label: 'Project Name' },
        { key: 'po', label: 'Purchase Order' }
    ];

    // Define table actions
    const tableActions = [
        {
            icon: '✏️',
            onClick: (row) => handleEditClick(row),
            title: 'Details',
            className: 'btn-edit'
        },
        {
            icon: '🗑️',
            onClick: (row) => handleDelete(row),
            title: 'Delete',
            className: 'btn-delete'
        }
    ];

    // Define help modal sections
    const helpSections = [
        {
            icon: '📋',
            title: 'Overview',
            content: (
                <HelpText>
                    The Project Management component allows you to create, view, edit, and delete projects.
                    Projects are the foundation of your system - sites and inventory items are associated with projects.
                </HelpText>
            )
        },
        {
            icon: '✨',
            title: 'Features & Buttons',
            content: (
                <HelpList
                    items={[
                        { label: '+ New Project', text: 'Opens a form to create a new project with PO, Project Name, and Project ID.' },
                        { label: '✏️ Details', text: 'Click to edit project details. Note: PO and Project ID cannot be changed after creation.' },
                        { label: '🗑️ Delete', text: 'Click to remove a project (requires confirmation).' }
                    ]}
                />
            )
        },
        {
            icon: '📊',
            title: 'Statistics Cards',
            content: (
                <HelpList
                    items={[
                        { label: 'Total Projects', text: 'Total count of all projects in the system.' },
                        { label: 'Current Page', text: 'Shows which page you\'re viewing out of total pages.' },
                        { label: 'Showing', text: 'Number of projects currently displayed on this page.' },
                        { label: 'Projects Per Page', text: 'Fixed at 5 projects per page for easier navigation.' }
                    ]}
                />
            )
        },
        {
            icon: '💡',
            title: 'Tips',
            content: (
                <HelpList
                    items={[
                        'Project ID (PID) and Purchase Order (PO) cannot be changed after project creation.',
                        'Only the Project Name can be edited after creation.',
                        'Deleting a project may affect associated sites and inventory items.',
                        'All fields are required when creating a new project.'
                    ]}
                />
            )
        }
    ];

    return (
        <div className="project-container">
            {/* Header Section */}
            <div className="project-header">
                <TitleWithInfo
                    title="Project Management"
                    subtitle="Manage your projects and their details"
                    onInfoClick={() => setShowHelpModal(true)}
                    infoTooltip="How to use this component"
                />
                <div className="header-actions">
                    <button
                        className="btn-primary"
                        onClick={() => { clearForm(); setShowForm(!showForm); }}>
                        <span className="btn-icon">+</span>
                        {showForm ? 'Cancel' : 'New Project'}
                    </button>
                </div>
            </div>

            {/* Messages */}
            {error && <div className="message error-message">{error}</div>}
            {success && <div className="message success-message">{success}</div>}
            {authError && <div className="message error-message">{authError}</div>}

            {/* Stats Bar - Carousel Style */}
            <StatsCarousel cards={statCards} visibleCount={4} />
            
            {showForm && (
                <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && setShowForm(false)}>
                    <div className="modal-container">
                        <div className="modal-header">
                            <h2 className="modal-title">
                                {editingProject ? `Edit Project: ${editingProject.project_name}` : 'Create New Project'}
                            </h2>
                            <button className="modal-close" onClick={() => setShowForm(false)} type="button">
                                ✕
                            </button>
                        </div>

                        <form className="modal-form" onSubmit={handleSubmit}>
                            {/* Project Information Section */}
                            <div className="form-section">
                                <h3 className="section-title">Project Information</h3>
                                <div className="form-grid">
                                    <div className="form-field">
                                        <label>Project ID *</label>
                                        <input
                                            type="text"
                                            name="pid"
                                            value={pid}
                                            onChange={e => setPid(e.target.value)}
                                            required
                                            disabled={!!editingProject}
                                            className={editingProject ? 'disabled-input' : ''}
                                        />
                                    </div>
                                    <div className="form-field">
                                        <label>Purchase Order *</label>
                                        <input
                                            type="text"
                                            name="po"
                                            value={po}
                                            onChange={e => setPo(e.target.value)}
                                            required
                                            disabled={!!editingProject}
                                            className={editingProject ? 'disabled-input' : ''}
                                        />
                                    </div>
                                    <div className="form-field full-width">
                                        <label>Project Name *</label>
                                        <input
                                            type="text"
                                            name="project_name"
                                            value={projectName}
                                            onChange={e => setProjectName(e.target.value)}
                                            required
                                        />
                                    </div>
                                </div>
                            </div>

                            {/* Form Actions */}
                            <div className="form-actions">
                                <button type="button" className="btn-cancel" onClick={() => setShowForm(false)}>
                                    Cancel
                                </button>
                                <button type="submit" className="btn-submit">
                                    {editingProject ? 'Update Project' : 'Create Project'}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
            
            {/* Table Section */}
            <DataTable
                columns={tableColumns}
                data={paginatedProjects}
                actions={tableActions}
                loading={false}
                noDataMessage="No projects found"
                className="project-table-wrapper"
            />

            {/* Pagination */}
            <Pagination
                currentPage={currentPage}
                totalPages={totalPages}
                onPageChange={(page) => setCurrentPage(page)}
                previousText="← Previous"
                nextText="Next →"
            />

            {/* Help/Info Modal */}
            <HelpModal
                show={showHelpModal}
                onClose={() => setShowHelpModal(false)}
                title="Project Management - User Guide"
                sections={helpSections}
                closeButtonText="Got it!"
            />
        </div>
    );
}