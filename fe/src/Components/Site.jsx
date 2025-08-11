import React, { useEffect, useState } from 'react';
import '../css/Project.css';

const SITES_PER_PAGE = 5;

export default function Site() {
  const [sites, setSites] = useState([]);
  const [showForm, setShowForm] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [editingSiteId, setEditingSiteId] = useState(null);

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
      if (!res.ok) throw new Error('Failed to fetch sites');
      const data = await res.json();
      setSites(data);
    } catch (err) {
      setError(err.message || 'Failed to fetch sites');
    }
  };

  const openCreateForm = () => {
    clearForm();
    setShowForm(true);
    setIsEditing(false);
  };

  const openEditForm = (site) => {
    setEditingSiteId(site.site_id);
    setSiteId(site.site_id);
    setSiteName(site.site_name);
    setProjectId(site.project_id);
    setIsEditing(true);
    setShowForm(true);
    setSuccess('');
    setError('');
  };

  const clearForm = () => {
    setProjectId('');
    setSiteName('');
    setSiteId('');
    setEditingSiteId(null);
    setIsEditing(false);
    setShowForm(false);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    try {
      if (isEditing) {
        // Update (only site_name and project_id allowed by backend)
        const res = await fetch(`${VITE_API_URL}/update-site/${editingSiteId}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            site_id: siteId,       // backend expects full AddSite shape
            site_name: siteName,
            pid_po: projectId
          })
        });
        if (!res.ok) {
          const body = await res.json().catch(() => ({}));
          throw new Error(body.detail || 'Failed to update site');
        }
        setSuccess('Site updated successfully');
      } else {
        // Create
        const res = await fetch(`${VITE_API_URL}/add-site`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            site_id: siteId,
            site_name: siteName,
            pid_po: projectId
          })
        });
        if (!res.ok) {
          const body = await res.json().catch(() => ({}));
          throw new Error(body.detail || 'Failed to create site');
        }
        setSuccess('Site created successfully');
      }

      clearForm();
      fetchSites();
    } catch (err) {
      setError(err.message || 'Operation failed');
    }
  };

  const handleDelete = async (site) => {
    if (!window.confirm(`Delete site ${site.site_id} — ${site.site_name}?`)) return;
    try {
      const res = await fetch(`${VITE_API_URL}/delete-site/${site.site_id}`, {
        method: 'DELETE'
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || 'Failed to delete site');
      }
      setSuccess('Site deleted');
      fetchSites();
    } catch (err) {
      setError(err.message || 'Delete failed');
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
        <button className="new-project-btn" onClick={openCreateForm}>
          + New Site
        </button>
      </div>

      {showForm && (
        <div style={{
          position: 'fixed',
          top: 0, left: 0, width: '100vw', height: '100vh',
          background: 'rgba(0,0,0,0.3)', display: 'flex',
          alignItems: 'center', justifyContent: 'center', zIndex: 1000
        }}>
          <div style={{
            background: '#fff', borderRadius: '12px', padding: '1.2rem',
            minWidth: '420px', boxShadow: '0 6px 30px rgba(0,0,0,0.2)'
          }}>
            <form className="project-form" onSubmit={handleSubmit}>
              <div>
                <button
                  style={{ width: 'fit-content', padding: '0.4rem', float: 'right' }}
                  className="stylish-btn danger"
                  onClick={() => setShowForm(false)}
                  type="button"
                >X</button>
              </div>

              <input
                type="text"
                placeholder="Project pid_po"
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
                disabled={isEditing} // cannot change site_id while editing
              />

              <button style={{ width: '100%' }} type="submit" className="stylish-btn">
                {isEditing ? 'Update Site' : 'Save Site'}
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
              <th>Site ID</th>
              <th>Site Name</th>
              <th>Project ID</th>
              <th style={{ width: '120px' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {paginatedSites.map((site, i) => (
              <tr key={site.site_id}>
                <td>{site.site_id}</td>
                <td>{site.site_name}</td>
                <td>{site.project_id}</td>
                <td style={{ textAlign: 'center', width: '120px' }}>
                  <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'center' }}>
                    <button
                      className="stylish-btn"
                      style={{ width: '46%' }}
                      onClick={() => openEditForm(site)}
                    >
                      Details
                    </button>
                    <button
                      className="stylish-btn danger"
                      style={{ width: '46%' }}
                      onClick={() => handleDelete(site)}
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
