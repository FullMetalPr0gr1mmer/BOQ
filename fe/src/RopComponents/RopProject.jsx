import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import '../css/Project.css';
import { apiCall, setTransient } from '../api';

const PROJECTS_PER_PAGE = 5;
// getAuthHeaders and apiCall imported from ../api
export default function ROPProject() {
  const [projects, setProjects] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [editingProject, setEditingProject] = useState(null);

  const [pid, setPid] = useState('');
  const [po, setPo] = useState('');
  const [projectName, setProjectName] = useState('');
  const [wbs, setWbs] = useState('');
  const [country, setCountry] = useState('');
  const [currency, setCurrency] = useState('Euros');

  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [csvModalMode, setCsvModalMode] = useState(false); // true if modal opened due to CSV error
  const [lastCsvFile, setLastCsvFile] = useState(null); // to store the last uploaded CSV file
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [projectToDelete, setProjectToDelete] = useState(null);

  const navigate = useNavigate();

  useEffect(() => {
    fetchProjects();
  }, []);

  const fetchProjects = async () => {
    try {
      const data = await apiCall(`/rop-projects/`);
      setProjects(data);
    } catch (e) {
      setTransient(setError, e.message || 'Failed to fetch projects');
    }
  };

  const handleCsvUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const formData = new FormData();
    formData.append('file', file);
    setLastCsvFile(file);
    try {
      await apiCall(`/rop-projects/upload-csv`, {
        method: 'POST',
        body: formData
      });
      setTransient(setSuccess, 'CSV uploaded and processed successfully!');
      fetchProjects();
    } catch (err) {
      const msg = err?.message || 'Failed to upload CSV';
      setTransient(setError, msg);
      if (msg.includes('CSV must contain at least one Level 0 entry')) {
        setCsvModalMode(true);
        setShowForm(true);
      }
    }
    document.getElementById('csv-upload-input').value = '';
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    const projectData = { pid, po, project_name: projectName, wbs, country, currency };

    if (csvModalMode) {
      const formData = new FormData();
      formData.append('pid', pid);
      formData.append('po', po);
      formData.append('project_name', projectName);
      formData.append('wbs', wbs);
      formData.append('country', country);
      formData.append('currency', currency);
      // Attach the CSV file again (assume you store it in state as lastCsvFile)
      if (lastCsvFile) {
        formData.append('file', lastCsvFile);
      }
      await apiCall(`/rop-projects/upload-csv-fix`, {
        method: 'POST',
        body: formData
      });
      setCsvModalMode(false);
      setShowForm(false);
      setTransient(setSuccess, 'Project data sent for CSV correction!');
           fetchProjects();
      return;
    }

    try {
      if (editingProject) {
        await apiCall(`/rop-projects/${editingProject.pid_po}`, {
          method: 'PUT',
          body: JSON.stringify(projectData)
        });
      } else {
        await apiCall(`/rop-projects/`, {
          method: 'POST',
          body: JSON.stringify(projectData)
        });
      }

      setTransient(setSuccess, editingProject ? 'Project updated successfully!' : 'Project created successfully!');
      clearForm();
      fetchProjects();
    } catch (err) {
      setTransient(setError, err.message || 'Failed to save project');
    }
  };

  const clearForm = () => {
    setPid('');
    setPo('');
    setProjectName('');
    setWbs('');
    setCountry('');
    setCurrency('Euros');
    setEditingProject(null);
    setShowForm(false);
  };

  const handleEditClick = (proj) => {
    setEditingProject(proj);
    setPid(proj.pid);
    setPo(proj.po);
    setProjectName(proj.project_name);
    setWbs(proj.wbs || '');
    setCountry(proj.country || '');
    setCurrency(proj.currency || 'Euros');
    setShowForm(true);
  };

  const handleDelete = (proj) => {
    setProjectToDelete(proj);
    setShowDeleteModal(true);
  };

  const confirmDelete = async () => {
    if (!projectToDelete) return;
    try {
      await apiCall(`/rop-projects/${projectToDelete.pid_po}`, { method: 'DELETE' });
      setTransient(setSuccess, 'Project and related items deleted successfully.');
      setShowDeleteModal(false);
      setProjectToDelete(null);
      fetchProjects();
    } catch (err) {
      setTransient(setError, err.message || 'Failed to delete project');
      setShowDeleteModal(false);
      setProjectToDelete(null);
    }
  };

  const cancelDelete = () => {
    setShowDeleteModal(false);
    setProjectToDelete(null);
  };

  const handleLevel1 = (proj) => {
    // const pid_po = proj.pid + proj.po;
    navigate('/rop-lvl1', { state: { pid_po:proj.pid_po, project_name: proj.project_name,currency:proj.currency } });
  };

  const paginatedProjects = projects.slice(
    (currentPage - 1) * PROJECTS_PER_PAGE,
    currentPage * PROJECTS_PER_PAGE
  );
  const totalPages = Math.ceil(projects.length / PROJECTS_PER_PAGE);

  return (
    <div className="dashboard-container">
      <div className="dashboard-header">
        <div>
          <h1 className="dashboard-title">ROP Projects</h1>
          <p className="dashboard-subtitle">Project Management Dashboard</p>
        </div>
        <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
          <button className="new-entry-btn" style={{visibility:'hidden'}} onClick={() => { clearForm(); setShowForm(!showForm); }}>
            {showForm ? '✕ Cancel' : '+ New Project'}
          </button>
          <form id="csv-upload-form" style={{ display: 'inline' }}>
            <input
              type="file"
              accept=".csv"
              style={{ display: 'none' }}
              id="csv-upload-input"
              onChange={handleCsvUpload}
            />
            <button
              type="button"
              className="new-entry-btn"
              onClick={() => document.getElementById('csv-upload-input').click()}
            >Upload QC CSV</button>
          </form>
        </div>
      </div>

      {showForm && (
        <div style={{
          position: 'fixed', top: 0, left: 0, width: '100vw', height: '100vh',
          background: 'rgba(0,0,0,0.3)', display: 'flex', alignItems: 'center',
          justifyContent: 'center', zIndex: 1000
        }}>
          <div style={{
            background: '#fff', borderRadius: '12px', padding: '2rem',
            minWidth: '500px', boxShadow: '0 4px 32px #00bcd44a',
            maxHeight: '80vh', overflowY: 'auto'
          }}>
            <form className="project-form" onSubmit={handleSubmit}>
              <div>
                <button style={{ width: 'fit-content', padding: '0.4rem', float: 'right' }}
                  className="stylish-btn danger" onClick={() => setShowForm(false)} type="button">
                  X
                </button>
              </div>
              <input type="text" placeholder="Project ID" value={pid} onChange={e => setPid(e.target.value)} required disabled={!!editingProject} />
              <input type="text" placeholder="Purchase Order" value={po} onChange={e => setPo(e.target.value)} required disabled={!!editingProject} />
              <input type="text" placeholder="Project Name" value={projectName} onChange={e => setProjectName(e.target.value)} required />
              <input type="text" placeholder="WBS" value={wbs} onChange={e => setWbs(e.target.value)} />
              <input type="text" placeholder="Country" value={country} onChange={e => setCountry(e.target.value)} />
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

  {error && <div className="dashboard-alert dashboard-alert-error">⚠️ {error}</div>}
  {success && <div className="dashboard-alert dashboard-alert-success">✅ {success}</div>}

  <div className="dashboard-table-container" style={{ overflowX: 'hidden' }}>
        <table className="dashboard-table">
          <thead>
            <tr>
              <th></th>
              {/* Removed Project ID column */}
              <th style={{textAlign:'center'}}>Customer Material Number</th>
              <th style={{textAlign:'center'}}>Project Name</th>
              {/* Removed Product Number column */}
              <th style={{textAlign:'center'}}>WBS</th>
                {/* Removed Country column */}
              <th style={{textAlign:'center'}}>Currency</th>
              <th style={{textAlign:'center'}}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {paginatedProjects.map((proj, index) => (
              <tr key={index}>
                {/* Removed Project ID cell */}
                <td>{proj.po}</td>
                <td>{proj.project_name}</td>
                {/* Removed Product Number cell */}
                <td>{proj.wbs}</td>
                  {/* Removed Country cell */}
                <td>{proj.currency}</td>
                <td style={{ textAlign: 'center', display: 'flex', gap: '0.5rem', flexWrap: 'wrap', justifyContent: 'center' }}>
                  <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'center', marginBottom: '0.5rem', width: '100%' }}>
                    <button className="stylish-btn" style={{ width: '48%' }} onClick={() => handleEditClick(proj)}>Edit</button>
                    <button className="stylish-btn danger" style={{ width: '48%' }} onClick={() => handleDelete(proj)}>Delete</button>
                  </div>
                  <div style={{ width: '100%' }}>
                    <button className="stylish-btn" style={{ width: '100%' }} onClick={() => handleLevel1(proj)}>Level 1</button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {totalPages > 1 && (
        <div className="dashboard-pagination">
          {Array.from({ length: totalPages }, (_, i) => (
            <button
              key={i}
              className={i + 1 === currentPage ? 'active' : ''}
              onClick={() => setCurrentPage(i + 1)}
            >
              {i + 1}
            </button>
          ))}
        </div>
      )}

      {showDeleteModal && (
        <div style={{
          position: 'fixed', top: 0, left: 0, width: '100vw', height: '100vh',
          background: 'rgba(0,0,0,0.35)', display: 'flex', alignItems: 'center',
          justifyContent: 'center', zIndex: 1001
        }}>
          <div style={{
            background: '#fff', borderRadius: '14px', padding: '1.5rem',
            minWidth: '360px', maxWidth: '90vw', boxShadow: '0 12px 40px rgba(0,0,0,0.18)'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '12px' }}>
              <div style={{
                width: 40, height: 40, borderRadius: '50%', background: '#fff3cd',
                display: 'flex', alignItems: 'center', justifyContent: 'center', border: '2px solid #ffecb5'
              }}>⚠️</div>
              <h3 style={{ margin: 0 }}>Confirm Project Deletion</h3>
            </div>
            <p style={{ marginTop: 0, color: '#444' }}>
              Deleting project <strong>{projectToDelete?.project_name}</strong> will also permanently delete all related PCIs, SIs, and Packages. This action cannot be undone. Are you sure you want to proceed?
            </p>
            <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end', marginTop: '16px' }}>
              <button className="stylish-btn" onClick={cancelDelete} style={{ background: '#e0e0e0', color: '#333' }}>Cancel</button>
              <button className="stylish-btn danger" onClick={confirmDelete}>Delete</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
