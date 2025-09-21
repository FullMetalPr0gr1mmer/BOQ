import React, { useState, useEffect } from 'react';
import '../css/Dismantling.css';
import { apiCall, getAuthHeaders } from '../api';

// API service with real endpoints
const apiService = {
  // Roles endpoints
  getAllRoles: async function() {
    return apiCall('/audit-logs/roles');
  },

  updateUserRole: async function(userId, newRoleName) {
    return apiCall('/audit-logs/update_user_role', {
      method: 'PUT',
      body: JSON.stringify({ user_id: userId, new_role_name: newRoleName }),
    });
  },

  async apiCall(endpoint, options = {}) {
    return apiCall(endpoint, options);
  },

  // Users endpoints
  getAllUsers: async function() {
    return this.apiCall('/audit-logs/users');
  },

  getUserProjects: async function(userId) {
    return this.apiCall(`/audit-logs/user/${userId}/projects`);
  },

  // Projects endpoints
  getAllProjects: async function() {

    return this.apiCall('/get_project');
  
  },

  // Access management endpoints
  grantAccess: async function(accessData) {
    return this.apiCall(`/audit-logs/grant_project_access`, {
      method: 'POST',
      body: JSON.stringify(accessData),
    });
  },

  updateAccess: async function(accessId, updateData) {
    return this.apiCall(`/audit-logs/update_project_access/${accessId}`, {
      method: 'PUT',
      body: JSON.stringify(updateData),
    });
  },

  revokeAccess: async function(accessId) {
    return this.apiCall(`/audit-logs/revoke_project_access/${accessId}`, {
      method: 'DELETE',
    });
  },

  // Audit logs endpoints
  getAuditLogs: async function(filters = {}) {
    const params = new URLSearchParams();
    Object.entries(filters).forEach(([key, value]) => {
      if (value) params.append(key, value);
    });
    const queryString = params.toString() ? `?${params.toString()}` : '';
    return this.apiCall(`/audit-logs${queryString}`);
  },

  getAvailableActions: async function() {
    return this.apiCall('/audit-logs/actions');
  },

  getAvailableResourceTypes: async function() {
    return this.apiCall('/audit-logs/resource_types');
  },
};

const SeniorAdminDashboard = () => {
  // State management
  const [activeTab, setActiveTab] = useState('users');
  const [users, setUsers] = useState([]);
  const [auditLogs, setAuditLogs] = useState([]);
  const [projects, setProjects] = useState([]);
  const [availableActions, setAvailableActions] = useState([]);
  const [availableResourceTypes, setAvailableResourceTypes] = useState([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState({ text: '', type: '' });
  const [authError, setAuthError] = useState(''); // State to handle authentication errors

  // Search and filter states
  const [userSearch, setUserSearch] = useState('');
  const [logSearch, setLogSearch] = useState('');
  const [actionFilter, setActionFilter] = useState('');
  const [resourceTypeFilter, setResourceTypeFilter] = useState('');

  // Modal states
  const [showGrantModal, setShowGrantModal] = useState(false);
  const [showUpdateModal, setShowUpdateModal] = useState(false);
  const [showControlAdminModal, setShowControlAdminModal] = useState(false);
  const [selectedAccess, setSelectedAccess] = useState(null);
  const [grantForm, setGrantForm] = useState({
    user_id: '',
    section: '', // 1 = MW BOQ, 2 = RAN BOQ
    project_id: '',
    permission_level: 'view'
  });
  const [sectionProjects, setSectionProjects] = useState([]);
  // Control Administration modal states
  const [controlAdminUserId, setControlAdminUserId] = useState('');
  const [controlAdminRole, setControlAdminRole] = useState('');
  const [allRoles, setAllRoles] = useState([]);

  // Pagination state
  const [currentPage, setCurrentPage] = useState(0);
  const [logsPerPage] = useState(20);

  // Load data on component mount
  useEffect(() => {
    loadInitialData();
  }, []);

  const loadInitialData = async () => {
    setLoading(true);
    setAuthError('');
    try {
      await Promise.all([
        loadUsers(),
        loadProjects(),
        loadAvailableFilters()
      ]);
    } catch (error) {
      // Check if the error is due to authentication
      if (error.message.includes('Unauthorized')) {
        setAuthError(error.message);
      } else {
        showMessage('Failed to load initial data', 'error');
      }
    } finally {
      setLoading(false);
    }
  };

  const loadUsers = async () => {
    try {
      const data = await apiService.getAllUsers();
      setUsers(Array.isArray(data) ? data : []);
    } catch (error) {
      if (error.message.includes('Unauthorized')) {
        setAuthError(error.message);
      } else {
        showMessage(`Failed to load users: ${error.message}`, 'error');
      }
    }
  };

  const loadAuditLogs = async (filters = {}) => {
    try {
      setLoading(true);
      const data = await apiService.getAuditLogs({
        ...filters,
        skip: currentPage * logsPerPage,
        limit: logsPerPage,
      });
      setAuditLogs(Array.isArray(data) ? data : []);
    } catch (error) {
      if (error.message.includes('Unauthorized')) {
        setAuthError(error.message);
      } else {
        showMessage(`Failed to load audit logs: ${error.message}`, 'error');
      }
    } finally {
      setLoading(false);
    }
  };

  const loadProjects = async () => {
    try {
      const data = await apiService.getAllProjects();
      setProjects(Array.isArray(data) ? data : []);
    } catch (error) {
      if (error.message.includes('Unauthorized')) {
        setAuthError(error.message);
      } else {
        showMessage(`Failed to load projects: ${error.message}`, 'error');
      }
    }
  };

  const loadAvailableFilters = async () => {
    try {
      const [actions, resourceTypes] = await Promise.all([
        apiService.getAvailableActions(),
        apiService.getAvailableResourceTypes()
      ]);
      setAvailableActions(actions.actions || []);
      setAvailableResourceTypes(resourceTypes.resource_types || []);
    } catch (error) {
      console.warn('Failed to load filter options:', error.message);
    }
  };

  // Load audit logs when switching to logs tab or filters change
  useEffect(() => {
    if (activeTab === 'logs') {
      loadAuditLogs({
        action: actionFilter,
        resource_type: resourceTypeFilter,
      });
    }
  }, [activeTab, actionFilter, resourceTypeFilter, currentPage]);

  const showMessage = (text, type) => {
    setMessage({ text, type });
    setTimeout(() => setMessage({ text: '', type: '' }), 5000);
  };

  const handleGrantAccess = async (e) => {
    e.preventDefault();
    setAuthError('');
    try {
      setLoading(true);
      await apiService.apiCall(`/audit-logs/grant_project_access`, {
        method: 'POST',
        body: JSON.stringify({
          section:parseInt(grantForm.section),
          user_id: parseInt(grantForm.user_id),
          project_id: grantForm.project_id,
          permission_level: grantForm.permission_level
        }),
      });
      showMessage('Access granted successfully', 'success');
      setShowGrantModal(false);
      setGrantForm({ user_id: '', project_id: '', permission_level: 'view' });
      await loadUsers();
    } catch (error) {
      if (error.message.includes('Unauthorized')) {
        setAuthError(error.message);
      } else {
        showMessage(`Failed to grant access: ${error.message}`, 'error');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleUpdateAccess = async (e) => {
    e.preventDefault();
    setAuthError('');
    try {
      setLoading(true);
      await apiService.updateAccess(selectedAccess.access_id, {
        permission_level: selectedAccess.permission_level
      });
      showMessage('Access updated successfully', 'success');
      setShowUpdateModal(false);
      setSelectedAccess(null);
      await loadUsers();
    } catch (error) {
      if (error.message.includes('Unauthorized')) {
        setAuthError(error.message);
      } else {
        showMessage(`Failed to update access: ${error.message}`, 'error');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleRevokeAccess = async (accessId) => {
    if (window.confirm('Are you sure you want to revoke this access?')) {
      setAuthError('');
      try {
        setLoading(true);
        await apiService.revokeAccess(accessId);
        showMessage('Access revoked successfully', 'success');
        await loadUsers();
      } catch (error) {
        if (error.message.includes('Unauthorized')) {
          setAuthError(error.message);
        } else {
          showMessage(`Failed to revoke access: ${error.message}`, 'error');
        }
      } finally {
        setLoading(false);
      }
    }
  };

  // Filter functions
  const filteredUsers = users.filter(user =>
    user.username.toLowerCase().includes(userSearch.toLowerCase()) ||
    user.email.toLowerCase().includes(userSearch.toLowerCase()) ||
    (user.role_name && user.role_name.toLowerCase().includes(userSearch.toLowerCase()))
  );

  const filteredLogs = auditLogs.filter(log => {
    if (!logSearch) return true;
    const searchTerm = logSearch.toLowerCase();
    return (
      (log.user && log.user.username.toLowerCase().includes(searchTerm)) ||
      (log.action && log.action.toLowerCase().includes(searchTerm)) ||
      (log.resource_name && log.resource_name.toLowerCase().includes(searchTerm))
    );
  });

  const formatTimestamp = (timestamp) => {
    return new Date(timestamp).toLocaleString();
  };

  const formatDetails = (details) => {
    if (!details) return 'N/A';
    try {
      const parsed = JSON.parse(details);
      return Object.entries(parsed).map(([key, value]) => 
        `${key}: ${value}`
      ).join(', ');
    } catch {
      return details;
    }
  };

  return (
    <div className="dismantling-container">
      {/* Header */}
      <div className="dismantling-header-row">
        <h2>Senior Admin Dashboard</h2>
        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
          <button 
            className="upload-btn"
            onClick={() => setShowGrantModal(true)}
            disabled={loading}
          >
            Grant Project Access
          </button>
          <button
            className="upload-btn"
            onClick={async () => {
              setShowControlAdminModal(true);
              try {
                const rolesData = await apiService.getAllRoles();
                setAllRoles(Array.isArray(rolesData.roles) ? rolesData.roles : []);
              } catch (error) {
                showMessage('Failed to load roles', 'error');
              }
            }}
            disabled={loading}
          >
            Control Administration
          </button>
        </div>
      </div>

      {/* Tab Navigation */}
      <div style={{ display: 'flex', gap: '1rem', marginBottom: '2rem', borderBottom: '2px solid var(--border-color)', paddingBottom: '1rem' }}>
        <button 
          className={`upload-btn ${activeTab === 'users' ? '' : 'clear-btn'}`}
          onClick={() => setActiveTab('users')}
          style={{ background: activeTab === 'users' ? undefined : 'linear-gradient(135deg, #f0f4f8 0%, #e2e8f0 100%)', color: activeTab === 'users' ? undefined : 'var(--primary-color)' }}
        >
          Users & Projects
        </button>
        <button 
          className={`upload-btn ${activeTab === 'logs' ? '' : 'clear-btn'}`}
          onClick={() => setActiveTab('logs')}
          style={{ background: activeTab === 'logs' ? undefined : 'linear-gradient(135deg, #f0f4f8 0%, #e2e8f0 100%)', color: activeTab === 'logs' ? undefined : 'var(--primary-color)' }}
        >
          Audit Logs
        </button>
      </div>

      {/* Message Display */}
      {message.text && (
        <div className={`dismantling-message ${message.type}`}>
          {message.text}
        </div>
      )}

      {/* Authentication Error Modal */}
      {authError && (
          <div className="modal-overlay">
              <div className="modal-content">
                  <span className="modal-close-btn" onClick={() => setAuthError('')}>&times;</span>
                  <div className="modal-body">
                      <p>{authError}</p>
                  </div>
              </div>
          </div>
      )}

      {/* Users Tab */}
      {activeTab === 'users' && (
        <div>
          <div className="dismantling-search-container">
            <input
              type="text"
              className="search-input"
              placeholder="Search users by username, email, or role..."
              value={userSearch}
              onChange={(e) => setUserSearch(e.target.value)}
            />
            <button 
              className="clear-btn"
              onClick={() => setUserSearch('')}
            >
              Clear
            </button>
          </div>

          <div className="dismantling-table-container">
            <table className="dismantling-table">
              <thead>
                <tr>
                  <th>User</th>
                  <th>Email</th>
                  <th>Role</th>
                  <th>Projects</th>
                </tr>
              </thead>
              <tbody>
                {filteredUsers.map(user => (
                  <tr key={user.id}>
                    <td><strong>{user.username}</strong></td>
                    <td>{user.email}</td>
                    <td>
                      <span style={{
                        padding: '0.25rem 0.75rem',
                        borderRadius: '12px',
                        fontSize: '0.8rem',
                        fontWeight: '500',
                        textTransform: 'uppercase',
                        background: user.role_name === 'senior_admin' ? 'linear-gradient(135deg, #e8f5e8 0%, #c8e6c9 100%)' :
                                        user.role_name === 'admin' ? 'linear-gradient(135deg, #f3e5f5 0%, #e1bee7 100%)' :
                                        'linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%)',
                        color: user.role_name === 'senior_admin' ? '#2e7d32' :
                               user.role_name === 'admin' ? '#7b1fa2' : '#1976d2'
                      }}>
                        {user.role_name}
                      </span>
                    </td>
                    <td>
                      {user.projects && user.projects.length > 0 ? (
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                          {user.projects.map(project => (
                            <div key={project.access_id} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                              <span style={{ minWidth: '150px' }}>{project.project_name}</span>
                              <span style={{
                                padding: '0.25rem 0.75rem',
                                borderRadius: '12px',
                                fontSize: '0.8rem',
                                fontWeight: '500',
                                textTransform: 'uppercase',
                                background: project.permission_level === 'all' ? 'linear-gradient(135deg, #e8f5e8 0%, #c8e6c9 100%)' :
                                                project.permission_level === 'edit' ? 'linear-gradient(135deg, #f3e5f5 0%, #e1bee7 100%)' :
                                                'linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%)',
                                color: project.permission_level === 'all' ? '#2e7d32' :
                                       project.permission_level === 'edit' ? '#7b1fa2' : '#1976d2'
                              }}>
                                {project.permission_level}
                              </span>
                              <div className="actions-cell">
                                <button 
                                  className="upload-btn"
                                  style={{ padding: '0.5rem 1rem', fontSize: '0.85rem' }}
                                  onClick={() => {
                                    setSelectedAccess(project);
                                    setShowUpdateModal(true);
                                  }}
                                  disabled={loading}
                                >
                                  Edit
                                </button>
                                <button 
                                  className="clear-btn"
                                  style={{ padding: '0.5rem 1rem', fontSize: '0.85rem', background: 'linear-gradient(135deg, #ffebee 0%, #ffcdd2 100%)', color: '#d32f2f' }}
                                  onClick={() => handleRevokeAccess(project.access_id)}
                                  disabled={loading}
                                >
                                  Revoke
                                </button>
                              </div>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <em style={{ color: '#888' }}>No project access</em>
                      )}
                    </td>
                  </tr>
                ))}
                {filteredUsers.length === 0 && (
                  <tr>
                    <td colSpan="4" className="no-results">
                      No users found
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Audit Logs Tab */}
      {activeTab === 'logs' && (
        <div>
          <div className="dismantling-search-container">
            <input
              type="text"
              className="search-input"
              placeholder="Search logs by user, action, or resource..."
              value={logSearch}
              onChange={(e) => setLogSearch(e.target.value)}
            />
            <button 
              className="clear-btn"
              onClick={() => {
                setLogSearch('');
                setActionFilter('');
                setResourceTypeFilter('');
              }}
            >
              Clear All
            </button>
          </div>

          <div style={{ display: 'flex', gap: '1rem', marginBottom: '1rem', flexWrap: 'wrap' }}>
            <select 
              className="search-input"
              value={actionFilter}
              onChange={(e) => setActionFilter(e.target.value)}
              style={{ width: 'auto', minWidth: '200px' }}
            >
              <option value="">All Actions</option>
              {availableActions.map(action => (
                <option key={action} value={action}>{action}</option>
              ))}
            </select>

            <select 
              className="search-input"
              value={resourceTypeFilter}
              onChange={(e) => setResourceTypeFilter(e.target.value)}
              style={{ width: 'auto', minWidth: '200px' }}
            >
              <option value="">All Resource Types</option>
              {availableResourceTypes.map(type => (
                <option key={type} value={type}>{type}</option>
              ))}
            </select>
          </div>

          <div className="dismantling-table-container">
            <table className="dismantling-table">
              <thead>
                <tr>
                  <th>Timestamp</th>
                  <th>User</th>
                  <th>Action</th>
                  <th>Resource</th>
                  <th>Details</th>
                  <th>IP Address</th>
                </tr>
              </thead>
              <tbody>
                {filteredLogs.map(log => (
                  <tr key={log.id}>
                    <td>{formatTimestamp(log.timestamp)}</td>
                    <td>
                      <div>
                        {log.user && <strong>{log.user.username}</strong>}
                        <br />
                        {log.user && <small style={{ color: '#666' }}>({log.user.role})</small>}
                      </div>
                    </td>
                    <td>
                      <span style={{
                        padding: '0.25rem 0.75rem',
                        borderRadius: '12px',
                        fontSize: '0.8rem',
                        fontWeight: '500',
                        textTransform: 'uppercase',
                        background: log.action === 'login' ? 'linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%)' :
                                        (log.action && log.action.includes('edit')) ? 'linear-gradient(135deg, #f3e5f5 0%, #e1bee7 100%)' :
                                        'linear-gradient(135deg, #e8f5e8 0%, #c8e6c9 100%)',
                        color: log.action === 'login' ? '#1976d2' :
                               (log.action && log.action.includes('edit')) ? '#7b1fa2' : '#2e7d32'
                      }}>
                        {log.action}
                      </span>
                    </td>
                    <td>
                      <div>
                        <strong>{log.resource_type}</strong>
                        {log.resource_name && (
                          <>
                            <br />
                            <small style={{ color: '#666' }}>{log.resource_name}</small>
                          </>
                        )}
                      </div>
                    </td>
                    <td>
                      <small>{formatDetails(log.details)}</small>
                    </td>
                    <td>{log.ip_address}</td>
                  </tr>
                ))}
                {filteredLogs.length === 0 && (
                  <tr>
                    <td colSpan="6" className="no-results">
                      No audit logs found
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination for logs */}
          <div className="dismantling-pagination">
            <button 
              className="pagination-btn"
              onClick={() => setCurrentPage(prev => Math.max(0, prev - 1))}
              disabled={currentPage === 0 || loading}
            >
              Previous
            </button>
            <span className="pagination-info">
              Page {currentPage + 1}
            </span>
            <button 
              className="pagination-btn"
              onClick={() => setCurrentPage(prev => prev + 1)}
              disabled={loading || filteredLogs.length < logsPerPage}
            >
              Next
            </button>
          </div>
        </div>
      )}

      {/* Grant Access Modal */}
      {showGrantModal && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0, 0, 0, 0.5)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000
        }}>
          <div style={{
            background: 'white',
            borderRadius: '16px',
            padding: '2rem',
            maxWidth: '500px',
            width: '90%',
            boxShadow: 'var(--shadow-main)',
            maxHeight: '80vh',
            overflowY: 'auto'
          }}>
            <div style={{ marginBottom: '1.5rem' }}>
              <h3 style={{ color: 'var(--primary-color)', margin: 0, fontSize: '1.5rem' }}>
                Grant Project Access
              </h3>
            </div>
            <form onSubmit={handleGrantAccess}>
              <div style={{ marginBottom: '1rem' }}>
                <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--primary-color)', fontWeight: '500' }}>
                  Select User:
                </label>
                <select
                  className="search-input"
                  value={grantForm.user_id}
                  onChange={async (e) => {
                    const user_id = e.target.value;
                    setGrantForm({ ...grantForm, user_id });
                  }}
                  required
                >
                  <option value="">Choose a user...</option>
                  {users.map(user => (
                    <option key={user.id} value={user.id}>
                      {user.username} ({user.email})
                    </option>
                  ))}
                </select>
              </div>
              <div style={{ marginBottom: '1rem' }}>
                <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--primary-color)', fontWeight: '500' }}>
                  Section:
                </label>
                <select
                  className="search-input"
                  value={grantForm.section}
                  onChange={async (e) => {
                    const section = e.target.value;
                    setGrantForm({ ...grantForm, section, project_id: '' });
                    // Fetch projects for selected section
                    if (section === '1') {
                      const mwProjects = await apiService.apiCall('/get_project');
                      setSectionProjects(Array.isArray(mwProjects) ? mwProjects : []);
                    } else if (section === '2') {
                      const ranProjects = await apiService.apiCall('/ran-projects');
                      setSectionProjects(Array.isArray(ranProjects) ? ranProjects : []);
                    } else if (section === '3') {
                      const leProjects = await apiService.apiCall('/rop-projects/');
                      setSectionProjects(Array.isArray(leProjects) ? leProjects : []);
                    } else {
                      setSectionProjects([]);
                    }
                  }}
                  required
                  disabled={!grantForm.user_id}
                >
                  <option value="">Choose a section...</option>
                  <option value="1">MW BOQ</option>
                  <option value="2">RAN BOQ</option>
                  <option value="3">LE-Automation</option>
                </select>
              </div>
              <div style={{ marginBottom: '1rem' }}>
                <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--primary-color)', fontWeight: '500' }}>
                  Select Project:
                </label>
                <select
                  className="search-input"
                  value={grantForm.project_id}
                  onChange={(e) => setGrantForm({ ...grantForm, project_id: e.target.value })}
                  required
                  disabled={!grantForm.user_id || !grantForm.section}
                >
                  <option value="">Choose a project...</option>
                  {sectionProjects.map(project => (
                    <option key={project.pid_po} value={project.pid_po}>
                      {project.project_name} ({project.pid_po})
                    </option>
                  ))}
                </select>
              </div>
              <div style={{ marginBottom: '1rem' }}>
                <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--primary-color)', fontWeight: '500' }}>
                  Permission Level:
                </label>
                <select
                  className="search-input"
                  value={grantForm.permission_level}
                  onChange={(e) => setGrantForm({ ...grantForm, permission_level: e.target.value })}
                  required
                  disabled={!grantForm.user_id || !grantForm.section}
                >
                  <option value="view">View Only</option>
                  <option value="edit">Edit Access</option>
                  <option value="all">Full Access</option>
                </select>
              </div>
              <div style={{ display: 'flex', gap: '1rem', justifyContent: 'flex-end', marginTop: '2rem' }}>
                <button 
                  type="button"
                  className="clear-btn"
                  onClick={() => {
                    setShowGrantModal(false);
                    setGrantForm({ user_id: '', section: '', project_id: '', permission_level: 'view' });
                    setSectionProjects([]);
                  }}
                  disabled={loading}
                >
                  Cancel
                </button>
                <button type="submit" className="upload-btn" disabled={loading}>
                  {loading ? 'Granting...' : 'Grant Access'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Control Administration Modal */}
      {showControlAdminModal && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0, 0, 0, 0.5)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000
        }}>
          <div style={{
            background: 'white',
            borderRadius: '16px',
            padding: '2rem',
            maxWidth: '500px',
            width: '90%',
            boxShadow: 'var(--shadow-main)',
            maxHeight: '80vh',
            overflowY: 'auto'
          }}>
            <div style={{ marginBottom: '1.5rem' }}>
              <h3 style={{ color: 'var(--primary-color)', margin: 0, fontSize: '1.5rem' }}>
                Control Administration
              </h3>
            </div>
            <form onSubmit={async (e) => {
              e.preventDefault();
              setAuthError('');
              try {
                setLoading(true);
                await apiService.updateUserRole(controlAdminUserId, controlAdminRole);
                showMessage('User role updated successfully', 'success');
                setShowControlAdminModal(false);
                setControlAdminUserId('');
                setControlAdminRole('');
                await loadUsers();
              } catch (error) {
                if (error.message.includes('Unauthorized')) {
                  setAuthError(error.message);
                } else {
                  showMessage(`Failed to update user role: ${error.message}`, 'error');
                }
              } finally {
                setLoading(false);
              }
            }}>
              <div style={{ marginBottom: '1rem' }}>
                <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--primary-color)', fontWeight: '500' }}>
                  Select User:
                </label>
                <select
                  className="search-input"
                  value={controlAdminUserId}
                  onChange={(e) => {
                    setControlAdminUserId(e.target.value);
                    setControlAdminRole('');
                  }}
                  required
                >
                  <option value="">Choose a user...</option>
                  {users.map(user => (
                    <option key={user.id} value={user.id}>
                      {user.username} ({user.role_name})
                    </option>
                  ))}
                </select>
              </div>
              <div style={{ marginBottom: '1rem' }}>
                <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--primary-color)', fontWeight: '500' }}>
                  Select Role:
                </label>
                <select
                  className="search-input"
                  value={controlAdminRole}
                  onChange={(e) => setControlAdminRole(e.target.value)}
                  required
                  disabled={!controlAdminUserId}
                >
                  <option value="">Choose a role...</option>
                  {allRoles.map(role => (
                    <option key={role.id} value={role.name}>{role.name}</option>
                  ))}
                </select>
              </div>
              <div style={{ display: 'flex', gap: '1rem', justifyContent: 'flex-end', marginTop: '2rem' }}>
                <button 
                  type="button"
                  className="clear-btn"
                  onClick={() => {
                    setShowControlAdminModal(false);
                    setControlAdminUserId('');
                    setControlAdminRole('');
                  }}
                  disabled={loading}
                >
                  Cancel
                </button>
                <button type="submit" className="upload-btn" disabled={loading || !controlAdminUserId || !controlAdminRole}>
                  {loading ? 'Updating...' : 'Update Role'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Update Access Modal */}
      {showUpdateModal && selectedAccess && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0, 0, 0, 0.5)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000
        }}>
          <div style={{
            background: 'white',
            borderRadius: '16px',
            padding: '2rem',
            maxWidth: '500px',
            width: '90%',
            boxShadow: 'var(--shadow-main)'
          }}>
            <div style={{ marginBottom: '1.5rem' }}>
              <h3 style={{ color: 'var(--primary-color)', margin: 0, fontSize: '1.5rem' }}>
                Update Project Access
              </h3>
            </div>
            <form onSubmit={handleUpdateAccess}>
              <div style={{ marginBottom: '1rem' }}>
                <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--primary-color)', fontWeight: '500' }}>
                  Project:
                </label>
                <input
                  type="text"
                  className="search-input"
                  value={selectedAccess.project_name}
                  readOnly
                  style={{ backgroundColor: '#f5f5f5' }}
                />
              </div>
              <div style={{ marginBottom: '1rem' }}>
                <label style={{ display: 'block', marginBottom: '0.5rem', color: 'var(--primary-color)', fontWeight: '500' }}>
                  Permission Level:
                </label>
                <select
                  className="search-input"
                  value={selectedAccess.permission_level}
                  onChange={(e) => setSelectedAccess({
                    ...selectedAccess,
                    permission_level: e.target.value
                  })}
                  required
                >
                  <option value="view">View Only</option>
                  <option value="edit">Edit Access</option>
                  <option value="all">Full Access</option>
                </select>
              </div>
              <div style={{ display: 'flex', gap: '1rem', justifyContent: 'flex-end', marginTop: '2rem' }}>
                <button 
                  type="button"
                  className="clear-btn"
                  onClick={() => {
                    setShowUpdateModal(false);
                    setSelectedAccess(null);
                  }}
                  disabled={loading}
                >
                  Cancel
                </button>
                <button type="submit" className="upload-btn" disabled={loading}>
                  {loading ? 'Updating...' : 'Update Access'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {loading && (
        <div className="loading-message">
          Loading...
        </div>
      )}
    </div>
  );
};

export default SeniorAdminDashboard;