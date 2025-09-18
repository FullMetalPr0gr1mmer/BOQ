import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import '../css/Project.css';

const PROJECTS_PER_PAGE = 5;
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
const getAuthHeadersForFormData = () => {
  const token = localStorage.getItem('token');
  const headers = {};
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
};
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

  const VITE_API_URL = import.meta.env.VITE_API_URL;
  const navigate = useNavigate();

  useEffect(() => {
    fetchProjects();
  }, []);

  const fetchProjects = async () => {
    try {
      const res = await fetch(`${VITE_API_URL}/rop-projects/`,{ headers: getAuthHeaders() });
      const data = await res.json();
      setProjects(data);
    } catch {
      setError('Failed to fetch projects');
    }
  };

  const handleCsvUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    const formData = new FormData();
    formData.append('file', file);
    setLastCsvFile(file);
    try {
      const res = await fetch(`${VITE_API_URL}/rop-projects/upload-csv`, {
        headers: getAuthHeadersForFormData(),
        method: 'POST',
        body: formData
      });
      if (!res.ok) {
        const err = await res.json();
        setError(err.detail || 'Failed to upload CSV');
        // If error is due to missing Level 0, open modal in CSV mode
        if (err.detail && err.detail.includes('CSV must contain at least one Level 0 entry')) {
          setCsvModalMode(true);
          setShowForm(true);
        }
        return;
      }
      setSuccess('CSV uploaded and processed successfully!');
      fetchProjects();
    } catch (err) {
      setError(err.message);
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
      await fetch(`${VITE_API_URL}/rop-projects/upload-csv-fix`, {
        headers: getAuthHeadersForFormData(),
        method: 'POST',
        body: formData
      });
      setCsvModalMode(false);
      setShowForm(false);
      setSuccess('Project data sent for CSV correction!');
           fetchProjects();
      return;
    }

    try {
      let res;
      if (editingProject) {
        res = await fetch(`${VITE_API_URL}/rop-projects/${editingProject.pid_po}`, {
          method: 'PUT',
          headers: getAuthHeaders(),
          body: JSON.stringify(projectData),
        });
      } else {
        res = await fetch(`${VITE_API_URL}/rop-projects/`, {
          method: 'POST',
          headers: getAuthHeaders(),
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

  const handleDelete = async (proj) => {
    if (!window.confirm(`Delete project ${proj.pid} - ${proj.project_name}?`)) return;

    try {
      const res = await fetch(`${VITE_API_URL}/rop-projects/${proj.pid_po}`, { method: 'DELETE',headers: getAuthHeaders() });
      if (!res.ok) throw new Error('Failed to delete project');
      setSuccess('Project deleted successfully!');
      fetchProjects();
    } catch (err) {
      setError(err.message);
    }
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
          <button className="new-entry-btn" onClick={() => { clearForm(); setShowForm(!showForm); }}>
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
    </div>
  );
}
