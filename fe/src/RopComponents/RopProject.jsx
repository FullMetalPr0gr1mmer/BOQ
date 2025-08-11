import { useEffect, useState } from 'react';
import '../css/Project.css';

const PROJECTS_PER_PAGE = 5;

export default function ROPProject() {
  const [projects, setProjects] = useState([]);
  const [showForm, setShowForm] = useState(false);
  // New: store current editing project info
  const [editingProject, setEditingProject] = useState(null);

  // Form fields for create & update
  const [pid, setPid] = useState('');
  const [po, setPo] = useState('');
  const [projectName, setProjectName] = useState('');
  const [wps, setWps] = useState('');
  const [country, setCountry] = useState('');
  const [currency, setCurrency] = useState('Euros');

  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [currentPage, setCurrentPage] = useState(1);

  const VITE_API_URL = import.meta.env.VITE_API_URL;

  useEffect(() => {
    fetchProjects();
  }, []);

  const fetchProjects = async () => {
    try {
      const res = await fetch(`${VITE_API_URL}/rop-projects/`);
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

    // Compose project data
    const projectData = {
      pid,
      po,
      project_name: projectName,
      wps,
      country,
      currency,
    };

    try {
      let res;
      if (editingProject) {
        // Update existing
        res = await fetch(`${VITE_API_URL}/rop-projects/${editingProject.pid + editingProject.po}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(projectData),
        });
      } else {
        // Create new
        res = await fetch(`${VITE_API_URL}/rop-projects/`, {
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
    setPid('');
    setPo('');
    setProjectName('');
    setWps('');
    setCountry('');
    setCurrency('Euros');
    setEditingProject(null);
    setShowForm(false);
  };

  // Start editing a project - prefill form
  const handleEditClick = (proj) => {
    setEditingProject(proj);
    setPid(proj.pid);
    setPo(proj.po);
    setProjectName(proj.project_name);
    setWps(proj.wps || '');
    setCountry(proj.country || '');
    setCurrency(proj.currency || 'Euros');
    setShowForm(true);
  };

  // Delete project
  const handleDelete = async (proj) => {
    if (!window.confirm(`Delete project ${proj.pid} - ${proj.project_name}?`)) return;

    try {
      const res = await fetch(`${VITE_API_URL}/rop-projects/${proj.pid + proj.po}`, {
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
        <h2>ROP Projects</h2>
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
                placeholder="Project ID"
                value={pid}
                onChange={e => setPid(e.target.value)}
                required
                disabled={!!editingProject}
              />
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
                placeholder="WPS"
                value={wps}
                onChange={e => setWps(e.target.value)}
              />
              <input
                type="text"
                placeholder="Country"
                value={country}
                onChange={e => setCountry(e.target.value)}
              />
              <select value={currency} onChange={e => setCurrency(e.target.value)}>
                <option value="Euros">Euros</option>
                <option value="Dollar">Dollar</option>
              </select>
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
              <th>Purchase Order</th>
              <th>Project Name</th>
              <th>WPS</th>
              <th>Country</th>
              <th>Currency</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {paginatedProjects.map((proj, index) => (
              <tr key={index}>
                <td>{proj.pid}</td>
                <td>{proj.po}</td>
                <td>{proj.project_name}</td>
                <td>{proj.wps}</td>
                <td>{proj.country}</td>
                <td>{proj.currency}</td>
                <td style={{textAlign: 'center'}}>
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
