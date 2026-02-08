import React, { useState, useEffect } from 'react';
import '../css/Inventory.css';
import { apiCall } from '../api';
import StatsCarousel from './shared/StatsCarousel';
import FilterBar from './shared/FilterBar';
import DataTable from './shared/DataTable';
import HelpModal, { HelpList, HelpText } from './shared/HelpModal';
import TitleWithInfo from './shared/InfoButton';
import Pagination from './shared/Pagination';

// API service with real endpoints
const apiService = {
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

  getAllUsers: async function() {
    return this.apiCall('/audit-logs/users');
  },

  getUserProjects: async function(userId) {
    return this.apiCall(`/audit-logs/user/${userId}/projects`);
  },

  getAllProjects: async function() {
    return this.apiCall('/get_project');
  },

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

  getAuditLogs: async function(filters = {}) {
    const params = new URLSearchParams();
    Object.entries(filters).forEach(([key, value]) => {
      if (value !== undefined && value !== '') params.append(key, value);
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
  const [authError, setAuthError] = useState('');
  const [showHelpModal, setShowHelpModal] = useState(false);

  // Search and filter states
  const [userSearch, setUserSearch] = useState('');
  const [logSearch, setLogSearch] = useState('');
  const [actionFilter, setActionFilter] = useState('');
  const [resourceTypeFilter, setResourceTypeFilter] = useState('');

  // Modal states
  const [showGrantModal, setShowGrantModal] = useState(false);
  const [showUpdateModal, setShowUpdateModal] = useState(false);
  const [showControlAdminModal, setShowControlAdminModal] = useState(false);
  const [showApprovalAccessModal, setShowApprovalAccessModal] = useState(false);
  const [selectedAccess, setSelectedAccess] = useState(null);
  const [selectedUserForApproval, setSelectedUserForApproval] = useState(null);
  const [approvalAccessForm, setApprovalAccessForm] = useState({
    can_access_approval: false,
    can_access_triggering: false,
    can_access_logistics: false
  });
  const [grantForm, setGrantForm] = useState({
    user_id: '',
    section: '',
    project_id: '',
    permission_level: 'view'
  });
  const [sectionProjects, setSectionProjects] = useState([]);
  const [controlAdminUserId, setControlAdminUserId] = useState('');
  const [controlAdminRole, setControlAdminRole] = useState('');
  const [allRoles, setAllRoles] = useState([]);

  // Pagination state
  const [currentPage, setCurrentPage] = useState(1);
  const [logsPerPage, setLogsPerPage] = useState(20);
  const [totalLogs, setTotalLogs] = useState(0);

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
      // OPTIMIZED: Server-side pagination with total count
      const data = await apiService.getAuditLogs({
        ...filters,
        skip: (currentPage - 1) * logsPerPage,
        limit: logsPerPage,
        search: logSearch || undefined,  // OPTIMIZED: Server-side search
      });

      // OPTIMIZED: Handle paginated response format
      console.log('Audit logs API response:', data);
      if (data && typeof data === 'object' && 'records' in data) {
        console.log('Using paginated format - Total:', data.total, 'Records:', data.records?.length);
        setAuditLogs(Array.isArray(data.records) ? data.records : []);
        setTotalLogs(data.total || 0);
      } else {
        console.log('Using legacy format - Data length:', data?.length);
        // Fallback for old response format
        setAuditLogs(Array.isArray(data) ? data : []);
        setTotalLogs(Array.isArray(data) ? data.length : 0);
      }
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

  // OPTIMIZED: Debounced log loading for search
  useEffect(() => {
    if (activeTab === 'logs') {
      // Debounce search by 300ms
      const debounceTimer = setTimeout(() => {
        loadAuditLogs({
          action: actionFilter,
          resource_type: resourceTypeFilter,
        });
      }, logSearch ? 300 : 0); // Only debounce when searching

      return () => clearTimeout(debounceTimer);
    }
  }, [activeTab, actionFilter, resourceTypeFilter, currentPage, logSearch, logsPerPage]);

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
          section: parseInt(grantForm.section),
          user_id: parseInt(grantForm.user_id),
          project_id: grantForm.project_id,
          permission_level: grantForm.permission_level
        }),
      });
      showMessage('Access granted successfully', 'success');
      setShowGrantModal(false);
      setGrantForm({ user_id: '', section: '', project_id: '', permission_level: 'view' });
      setSectionProjects([]);
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

  const handleOpenApprovalAccessModal = (user) => {
    setSelectedUserForApproval(user);
    setApprovalAccessForm({
      can_access_approval: user.can_access_approval || false,
      can_access_triggering: user.can_access_triggering || false,
      can_access_logistics: user.can_access_logistics || false
    });
    setShowApprovalAccessModal(true);
  };

  const handleUpdateApprovalAccess = async (e) => {
    e.preventDefault();
    setAuthError('');
    try {
      setLoading(true);
      await apiService.apiCall('/audit-logs/update_approval_stage_access', {
        method: 'PUT',
        body: JSON.stringify({
          user_id: selectedUserForApproval.id,
          ...approvalAccessForm
        }),
      });
      showMessage('Approval stage access updated successfully', 'success');
      setShowApprovalAccessModal(false);
      setSelectedUserForApproval(null);
      await loadUsers();
    } catch (error) {
      if (error.message.includes('Unauthorized')) {
        setAuthError(error.message);
      } else {
        showMessage(`Failed to update approval stage access: ${error.message}`, 'error');
      }
    } finally {
      setLoading(false);
    }
  };

  const filteredUsers = users.filter(user =>
    user.username.toLowerCase().includes(userSearch.toLowerCase()) ||
    user.email.toLowerCase().includes(userSearch.toLowerCase()) ||
    (user.role_name && user.role_name.toLowerCase().includes(userSearch.toLowerCase()))
  );

  // OPTIMIZED: Server-side search - no client-side filtering needed
  // All filtering is done on the backend for better performance
  const filteredLogs = auditLogs;

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

  // Handler for logs per page change
  const handleLogsPerPageChange = (e) => {
    const newLimit = parseInt(e.target.value);
    setLogsPerPage(newLimit);
    setCurrentPage(1); // Reset to first page
  };

  // OPTIMIZED: Calculate total pages from API's total count, not filtered array length
  const totalPages = Math.ceil(totalLogs / logsPerPage);
  console.log('Pagination calculation:', { totalLogs, logsPerPage, totalPages });

  // Stats for carousel
  const statCards = activeTab === 'users'
    ? [
        { label: 'Total Users', value: users.length },
        { label: 'Filtered Users', value: filteredUsers.length },
        { label: 'Total Projects', value: projects.length },
      ]
    : [
        { label: 'Total Logs', value: totalLogs },  // OPTIMIZED: Show total from API
        { label: 'Current Page', value: `${currentPage} / ${totalPages || 1}` },
        {
          label: 'Logs Per Page',
          isEditable: true,
          component: (
            <select
              className="stat-select"
              value={logsPerPage}
              onChange={handleLogsPerPageChange}
            >
              <option value={10}>10</option>
              <option value={20}>20</option>
              <option value={50}>50</option>
              <option value={100}>100</option>
              <option value={200}>200</option>
            </select>
          )
        }
      ];

  // Users table columns
  const userColumns = [
    {
      key: 'username',
      label: 'User',
      render: (user) => <strong>{user.username}</strong>
    },
    { key: 'email', label: 'Email' },
    {
      key: 'role_name',
      label: 'Role',
      render: (user) => (
        <span className={`role-badge role-${user.role_name}`}>
          {user.role_name}
        </span>
      )
    },
    {
      key: 'projects',
      label: 'Projects',
      render: (user) => (
        user.projects && user.projects.length > 0 ? (
          <div className="projects-list">
            {user.projects.map(project => (
              <div key={project.access_id} className="project-item">
                <span className="project-name">{project.project_name}</span>
                <span className={`permission-badge permission-${project.permission_level}`}>
                  {project.permission_level}
                </span>
                <div className="project-actions">
                  <button
                    className="btn-action btn-edit"
                    onClick={() => {
                      setSelectedAccess(project);
                      setShowUpdateModal(true);
                    }}
                    disabled={loading}
                    title="Edit"
                  >
                    ✏️
                  </button>
                  <button
                    className="btn-action btn-delete"
                    onClick={() => handleRevokeAccess(project.access_id)}
                    disabled={loading}
                    title="Revoke"
                  >
                    🗑️
                  </button>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <em style={{ color: '#888' }}>No project access</em>
        )
      )
    },
    {
      key: 'approval_access',
      label: 'Approval Access',
      render: (user) => (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px' }}>
            {user.can_access_approval && (
              <span className="permission-badge permission-view">Approval</span>
            )}
            {user.can_access_triggering && (
              <span className="permission-badge permission-edit">Triggering</span>
            )}
            {user.can_access_logistics && (
              <span className="permission-badge permission-all">Logistics</span>
            )}
            {!user.can_access_approval && !user.can_access_triggering && !user.can_access_logistics && (
              <em style={{ color: '#888', fontSize: '0.875rem' }}>No access</em>
            )}
          </div>
          <button
            className="btn-action btn-edit"
            onClick={() => handleOpenApprovalAccessModal(user)}
            disabled={loading}
            title="Manage Approval Stage Access"
            style={{ fontSize: '0.75rem', padding: '4px 8px' }}
          >
            ⚙️ Manage
          </button>
        </div>
      )
    }
  ];

  // Audit logs table columns
  const logColumns = [
    {
      key: 'timestamp',
      label: 'Timestamp',
      render: (log) => formatTimestamp(log.timestamp)
    },
    {
      key: 'user',
      label: 'User',
      render: (log) => (
        <div>
          {log.user && <strong>{log.user.username}</strong>}
          <br />
          {log.user && <small style={{ color: '#666' }}>({log.user.role})</small>}
        </div>
      )
    },
    {
      key: 'action',
      label: 'Action',
      render: (log) => (
        <span className={`action-badge action-${log.action}`}>
          {log.action}
        </span>
      )
    },
    {
      key: 'resource',
      label: 'Resource',
      render: (log) => (
        <div>
          <strong>{log.resource_type}</strong>
          {log.resource_name && (
            <>
              <br />
              <small style={{ color: '#666' }}>{log.resource_name}</small>
            </>
          )}
        </div>
      )
    },
    {
      key: 'details',
      label: 'Details',
      render: (log) => <small>{formatDetails(log.details)}</small>
    },
    { key: 'ip_address', label: 'IP Address' },
  ];

  // Help modal sections
  const helpSections = [
    {
      icon: '📋',
      title: 'Overview',
      content: (
        <HelpText>
          The Senior Admin Dashboard provides comprehensive user and project access management, along with
          detailed audit logging capabilities. You can grant, update, and revoke user access to projects,
          control user roles, and monitor all system activities through audit logs.
        </HelpText>
      )
    },
    {
      icon: '👥',
      title: 'Users & Projects Tab',
      content: (
        <HelpList
          items={[
            { label: 'Grant Project Access', text: 'Opens a form to grant a user access to a specific project with defined permission levels.' },
            { label: 'Control Administration', text: 'Allows you to change user roles (e.g., user, admin, senior_admin).' },
            { label: 'Search Users', text: 'Filter users by username, email, or role in real-time.' },
            { label: 'Edit Access', text: 'Modify permission levels for existing project access (view, edit, all).' },
            { label: 'Revoke Access', text: 'Remove a user\'s access to a specific project.' },
          ]}
        />
      )
    },
    {
      icon: '📊',
      title: 'Audit Logs Tab',
      content: (
        <HelpList
          items={[
            { label: 'Search Logs', text: 'Filter logs by user, action, or resource name in real-time.' },
            { label: 'Action Filter', text: 'Filter logs by specific actions (e.g., login, create, edit, delete).' },
            { label: 'Resource Type Filter', text: 'Filter logs by resource types (e.g., project, user, inventory).' },
            { label: 'Clear All', text: 'Resets all search and filter criteria.' },
            { label: 'Pagination', text: 'Navigate through audit logs with previous/next buttons.' },
          ]}
        />
      )
    },
    {
      icon: '🔐',
      title: 'Permission Levels',
      content: (
        <HelpList
          items={[
            { label: 'View Only', text: 'User can only view data in the project.' },
            { label: 'Edit Access', text: 'User can view and edit data in the project.' },
            { label: 'Full Access', text: 'User has complete access including create, edit, and delete operations.' },
          ]}
        />
      )
    },
    {
      icon: '🎭',
      title: 'User Roles',
      content: (
        <HelpList
          items={[
            { label: 'User', text: 'Basic user with limited access to assigned projects.' },
            { label: 'Admin', text: 'Administrator with elevated privileges for project management.' },
            { label: 'Senior Admin', text: 'Highest level with full system access, user management, and audit capabilities.' },
          ]}
        />
      )
    },
    {
      icon: '📁',
      title: 'Granting Project Access',
      content: (
        <HelpText>
          To grant project access: Select the user, choose the section (MW BOQ, RAN BOQ, or LE-Automation),
          select the project from the filtered list, set the permission level, and submit. The user will
          immediately gain access according to the specified permission level.
        </HelpText>
      )
    },
    {
      icon: '💡',
      title: 'Tips',
      content: (
        <HelpList
          items={[
            'Use the search feature to quickly find specific users or logs.',
            'Monitor audit logs regularly to track system usage and detect anomalies.',
            'Always verify permission levels before granting access to sensitive projects.',
            'The action and resource type filters help narrow down audit log searches.',
            'Use "Control Administration" carefully - role changes affect user permissions globally.',
          ]}
        />
      )
    }
  ];

  return (
    <div className="inventory-container">
      {/* Header Section */}
      <div className="inventory-header">
        <TitleWithInfo
          title="Senior Admin Dashboard"
          subtitle="Manage users, projects, and monitor system activities"
          onInfoClick={() => setShowHelpModal(true)}
          infoTooltip="How to use this dashboard"
        />
        <div className="header-actions">
          <button
            className="btn-primary"
            onClick={() => setShowGrantModal(true)}
            disabled={loading}
          >
            <span className="btn-icon">🔑</span>
            Grant Project Access
          </button>
          <button
            className="btn-secondary"
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
            <span className="btn-icon">⚙️</span>
            Control Administration
          </button>
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="tab-navigation">
        <button
          className={`tab-button ${activeTab === 'users' ? 'active' : ''}`}
          onClick={() => setActiveTab('users')}
        >
          <span className="tab-icon">👥</span>
          Users & Projects
        </button>
        <button
          className={`tab-button ${activeTab === 'logs' ? 'active' : ''}`}
          onClick={() => setActiveTab('logs')}
        >
          <span className="tab-icon">📊</span>
          Audit Logs
        </button>
      </div>

      {/* Messages */}
      {message.text && (
        <div className={`message ${message.type === 'error' ? 'error-message' : 'success-message'}`}>
          {message.text}
        </div>
      )}

      {/* Authentication Error Modal */}
      {authError && (
        <div className="modal-overlay" onClick={() => setAuthError('')}>
          <div className="modal-container">
            <div className="modal-header">
              <h2 className="modal-title">Authentication Error</h2>
              <button className="modal-close" onClick={() => setAuthError('')}>✕</button>
            </div>
            <div className="modal-form">
              <p>{authError}</p>
            </div>
          </div>
        </div>
      )}

      {/* Stats Bar - Carousel Style */}
      <StatsCarousel cards={statCards} visibleCount={activeTab === 'users' ? 3 : 3} />

      {/* Users Tab */}
      {activeTab === 'users' && (
        <div>
          <FilterBar
            searchTerm={userSearch}
            onSearchChange={(e) => setUserSearch(e.target.value)}
            searchPlaceholder="Search users by username, email, or role..."
            showClearButton={!!userSearch}
            onClearSearch={() => setUserSearch('')}
            clearButtonText="Clear"
          />

          <DataTable
            columns={userColumns}
            data={filteredUsers}
            loading={loading}
            noDataMessage="No users found"
            className="inventory-table-wrapper"
          />
        </div>
      )}

      {/* Audit Logs Tab */}
      {activeTab === 'logs' && (
        <div>
          <FilterBar
            searchTerm={logSearch}
            onSearchChange={(e) => setLogSearch(e.target.value)}
            searchPlaceholder="Search logs by user, action, or resource..."
            dropdowns={[
              {
                label: 'Action',
                value: actionFilter,
                onChange: (e) => setActionFilter(e.target.value),
                placeholder: 'All Actions',
                options: availableActions.map(action => ({
                  value: action,
                  label: action
                }))
              },
              {
                label: 'Resource Type',
                value: resourceTypeFilter,
                onChange: (e) => setResourceTypeFilter(e.target.value),
                placeholder: 'All Resource Types',
                options: availableResourceTypes.map(type => ({
                  value: type,
                  label: type
                }))
              }
            ]}
            showClearButton={!!(logSearch || actionFilter || resourceTypeFilter)}
            onClearSearch={() => {
              setLogSearch('');
              setActionFilter('');
              setResourceTypeFilter('');
            }}
            clearButtonText="Clear All"
          />

          <DataTable
            columns={logColumns}
            data={filteredLogs}
            loading={loading}
            noDataMessage="No audit logs found"
            className="inventory-table-wrapper"
          />

          <Pagination
            currentPage={currentPage}
            totalPages={totalPages || 1}
            onPageChange={(page) => setCurrentPage(page)}
            previousText="← Previous"
            nextText="Next →"
          />
        </div>
      )}

      {/* Grant Access Modal */}
      {showGrantModal && (
        <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && setShowGrantModal(false)}>
          <div className="modal-container">
            <div className="modal-header">
              <h2 className="modal-title">Grant Project Access</h2>
              <button className="modal-close" onClick={() => {
                setShowGrantModal(false);
                setGrantForm({ user_id: '', section: '', project_id: '', permission_level: 'view' });
                setSectionProjects([]);
              }}>✕</button>
            </div>

            <form className="modal-form" onSubmit={handleGrantAccess}>
              <div className="form-section">
                <h3 className="section-title">Access Details</h3>
                <div className="form-grid">
                  <div className="form-field">
                    <label>Select User *</label>
                    <select
                      className="filter-input"
                      value={grantForm.user_id}
                      onChange={(e) => setGrantForm({ ...grantForm, user_id: e.target.value })}
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

                  <div className="form-field">
                    <label>Section *</label>
                    <select
                      className="filter-input"
                      value={grantForm.section}
                      onChange={async (e) => {
                        const section = e.target.value;
                        setGrantForm({ ...grantForm, section, project_id: '' });
                        try {
                          if (section === '1') {
                            const mwProjects = await apiService.apiCall('/get_project?limit=1000');
                            setSectionProjects(Array.isArray(mwProjects?.records) ? mwProjects.records : (Array.isArray(mwProjects) ? mwProjects : []));
                          } else if (section === '2') {
                            const ranProjects = await apiService.apiCall('/ran-projects?limit=1000');
                            setSectionProjects(Array.isArray(ranProjects?.records) ? ranProjects.records : (Array.isArray(ranProjects) ? ranProjects : []));
                          } else if (section === '3') {
                            const leProjects = await apiService.apiCall('/rop-projects?limit=1000');
                            setSectionProjects(Array.isArray(leProjects?.records) ? leProjects.records : (Array.isArray(leProjects) ? leProjects : []));
                          } else if (section === '4') {
                            const duProjects = await apiService.apiCall('/du-projects?limit=1000');
                            console.log('DU Projects Response:', duProjects);
                            setSectionProjects(Array.isArray(duProjects?.records) ? duProjects.records : []);
                          } else {
                            setSectionProjects([]);
                          }
                        } catch (error) {
                          console.error('Error loading projects for section:', section, error);
                          showMessage(`Failed to load projects: ${error.message}`, 'error');
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
                      <option value="4">DU BOQ</option>
                    </select>
                  </div>

                  <div className="form-field">
                    <label>Select Project *</label>
                    <select
                      className="filter-input"
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

                  <div className="form-field">
                    <label>Permission Level *</label>
                    <select
                      className="filter-input"
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
                </div>
              </div>

              <div className="form-actions">
                <button
                  type="button"
                  className="btn-cancel"
                  onClick={() => {
                    setShowGrantModal(false);
                    setGrantForm({ user_id: '', section: '', project_id: '', permission_level: 'view' });
                    setSectionProjects([]);
                  }}
                  disabled={loading}
                >
                  Cancel
                </button>
                <button type="submit" className="btn-submit" disabled={loading}>
                  {loading ? 'Granting...' : 'Grant Access'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Control Administration Modal */}
      {showControlAdminModal && (
        <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && setShowControlAdminModal(false)}>
          <div className="modal-container">
            <div className="modal-header">
              <h2 className="modal-title">Control Administration</h2>
              <button className="modal-close" onClick={() => {
                setShowControlAdminModal(false);
                setControlAdminUserId('');
                setControlAdminRole('');
              }}>✕</button>
            </div>

            <form className="modal-form" onSubmit={async (e) => {
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
              <div className="form-section">
                <h3 className="section-title">Role Management</h3>
                <div className="form-grid">
                  <div className="form-field">
                    <label>Select User *</label>
                    <select
                      className="filter-input"
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

                  <div className="form-field">
                    <label>Select Role *</label>
                    <select
                      className="filter-input"
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
                </div>
              </div>

              <div className="form-actions">
                <button
                  type="button"
                  className="btn-cancel"
                  onClick={() => {
                    setShowControlAdminModal(false);
                    setControlAdminUserId('');
                    setControlAdminRole('');
                  }}
                  disabled={loading}
                >
                  Cancel
                </button>
                <button type="submit" className="btn-submit" disabled={loading || !controlAdminUserId || !controlAdminRole}>
                  {loading ? 'Updating...' : 'Update Role'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Update Access Modal */}
      {showUpdateModal && selectedAccess && (
        <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && setShowUpdateModal(false)}>
          <div className="modal-container">
            <div className="modal-header">
              <h2 className="modal-title">Update Project Access</h2>
              <button className="modal-close" onClick={() => {
                setShowUpdateModal(false);
                setSelectedAccess(null);
              }}>✕</button>
            </div>

            <form className="modal-form" onSubmit={handleUpdateAccess}>
              <div className="form-section">
                <h3 className="section-title">Access Details</h3>
                <div className="form-grid">
                  <div className="form-field">
                    <label>Project</label>
                    <input
                      type="text"
                      className="filter-input disabled-input"
                      value={selectedAccess.project_name}
                      readOnly
                      disabled
                    />
                  </div>

                  <div className="form-field">
                    <label>Permission Level *</label>
                    <select
                      className="filter-input"
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
                </div>
              </div>

              <div className="form-actions">
                <button
                  type="button"
                  className="btn-cancel"
                  onClick={() => {
                    setShowUpdateModal(false);
                    setSelectedAccess(null);
                  }}
                  disabled={loading}
                >
                  Cancel
                </button>
                <button type="submit" className="btn-submit" disabled={loading}>
                  {loading ? 'Updating...' : 'Update Access'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Approval Stage Access Modal */}
      {showApprovalAccessModal && selectedUserForApproval && (
        <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && setShowApprovalAccessModal(false)}>
          <div className="modal-container">
            <div className="modal-header">
              <h2 className="modal-title">Manage Approval Stage Access</h2>
              <button className="modal-close" onClick={() => {
                setShowApprovalAccessModal(false);
                setSelectedUserForApproval(null);
              }}>✕</button>
            </div>

            <form className="modal-form" onSubmit={handleUpdateApprovalAccess}>
              <div className="form-section">
                <h3 className="section-title">User: {selectedUserForApproval.username}</h3>
                <p style={{ color: '#666', marginBottom: '20px', fontSize: '0.875rem' }}>
                  Grant access to different stages of the approval workflow. Users will only see items in stages they have access to.
                </p>
                <div className="form-grid">
                  <div className="form-field" style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <input
                      type="checkbox"
                      id="can_access_approval"
                      checked={approvalAccessForm.can_access_approval}
                      onChange={(e) => setApprovalAccessForm({
                        ...approvalAccessForm,
                        can_access_approval: e.target.checked
                      })}
                      style={{ width: 'auto', cursor: 'pointer' }}
                    />
                    <label htmlFor="can_access_approval" style={{ cursor: 'pointer', marginBottom: 0 }}>
                      <strong>Approval Stage</strong>
                      <span style={{ display: 'block', color: '#666', fontSize: '0.8rem' }}>
                        Can view and manage items in the approval stage
                      </span>
                    </label>
                  </div>

                  <div className="form-field" style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <input
                      type="checkbox"
                      id="can_access_triggering"
                      checked={approvalAccessForm.can_access_triggering}
                      onChange={(e) => setApprovalAccessForm({
                        ...approvalAccessForm,
                        can_access_triggering: e.target.checked
                      })}
                      style={{ width: 'auto', cursor: 'pointer' }}
                    />
                    <label htmlFor="can_access_triggering" style={{ cursor: 'pointer', marginBottom: 0 }}>
                      <strong>Triggering Stage</strong>
                      <span style={{ display: 'block', color: '#666', fontSize: '0.8rem' }}>
                        Can view and manage items in the triggering stage
                      </span>
                    </label>
                  </div>

                  <div className="form-field" style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <input
                      type="checkbox"
                      id="can_access_logistics"
                      checked={approvalAccessForm.can_access_logistics}
                      onChange={(e) => setApprovalAccessForm({
                        ...approvalAccessForm,
                        can_access_logistics: e.target.checked
                      })}
                      style={{ width: 'auto', cursor: 'pointer' }}
                    />
                    <label htmlFor="can_access_logistics" style={{ cursor: 'pointer', marginBottom: 0 }}>
                      <strong>Logistics Stage</strong>
                      <span style={{ display: 'block', color: '#666', fontSize: '0.8rem' }}>
                        Can view and manage items in the logistics stage
                      </span>
                    </label>
                  </div>
                </div>
              </div>

              <div className="form-actions">
                <button
                  type="button"
                  className="btn-cancel"
                  onClick={() => {
                    setShowApprovalAccessModal(false);
                    setSelectedUserForApproval(null);
                  }}
                  disabled={loading}
                >
                  Cancel
                </button>
                <button type="submit" className="btn-submit" disabled={loading}>
                  {loading ? 'Updating...' : 'Update Approval Access'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Help/Info Modal */}
      <HelpModal
        show={showHelpModal}
        onClose={() => setShowHelpModal(false)}
        title="Senior Admin Dashboard - User Guide"
        sections={helpSections}
        closeButtonText="Got it!"
      />

      {loading && <div className="loading-indicator">Loading...</div>}
    </div>
  );
};

export default SeniorAdminDashboard;
