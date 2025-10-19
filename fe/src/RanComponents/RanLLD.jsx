import React, { useState, useEffect, useRef } from "react";
import { apiCall, setTransient } from "../api.js";
import "../css/Inventory.css";
import StatsCarousel from '../Components/shared/StatsCarousel';
import FilterBar from '../Components/shared/FilterBar';
import DataTable from '../Components/shared/DataTable';
import HelpModal, { HelpList, HelpText, CodeBlock } from '../Components/shared/HelpModal';
import TitleWithInfo from '../Components/shared/InfoButton';
import Pagination from '../Components/shared/Pagination';

// Helper functions to parse and stringify CSV data
const parseCSV = (csvString) => {
  if (!csvString) return [];
  const lines = csvString.split('\n');
  return lines.map(line => {
    const regex = /(".*?"|[^",]+)(?=\s*,|\s*$)/g;
    const matches = line.match(regex) || [];
    return matches.map(field => field.replace(/"/g, ''));
  });
};

const stringifyCSV = (data) => {
  return data.map(row =>
    row.map(field => {
      const fieldStr = String(field || '');
      if (fieldStr.includes(',') || fieldStr.includes('"')) {
        return `"${fieldStr.replace(/"/g, '""')}"`;
      }
      return fieldStr;
    }).join(',')
  ).join('\n');
};

export default function RANLLD() {
  const [rows, setRows] = useState([]);
  const [currentPage, setCurrentPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(50);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [uploading, setUploading] = useState(false);
  const [loading, setLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const [showHelpModal, setShowHelpModal] = useState(false);

  const [projects, setProjects] = useState([]);
  const [selectedProject, setSelectedProject] = useState('');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [createForm, setCreateForm] = useState({
    site_id: '',
    new_antennas: '',
    total_antennas: '',
    technical_boq: '',
    key: '',
    pid_po: ''
  });
  const [creating, setCreating] = useState(false);

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingRow, setEditingRow] = useState(null);
  const [editForm, setEditForm] = useState({});
  const [updating, setUpdating] = useState(false);

  const [generatingBoqId, setGeneratingBoqId] = useState(null);
  const [showCsvModal, setShowCsvModal] = useState(false);
  const [editableCsvData, setEditableCsvData] = useState([]);
  const [currentSiteId, setCurrentSiteId] = useState('');
  const [stats, setStats] = useState({ total_sites: 0, total_antennas: 0 });

  const fetchAbort = useRef(null);

  const fetchProjects = async () => {
    try {
      const data = await apiCall('/ran-projects');
      setProjects(data || []);
      if (data && data.length > 0) {
        setSelectedProject(data[0].pid_po);
      }
    } catch (err) {
      setTransient(setError, 'Failed to load projects. Please ensure you have project access.');
      console.error(err);
    }
  };

  // Calculate stats from current data
  const calculateStats = () => {
    const totalAntennas = rows.reduce((sum, row) => sum + (parseInt(row.total_antennas) || 0), 0);
    setStats({ total_sites: total, total_antennas: totalAntennas });
  };

  const fetchSites = async (page = 1, search = "", limit = rowsPerPage, projectId = selectedProject) => {
    try {
      if (fetchAbort.current) fetchAbort.current.abort();
      const controller = new AbortController();
      fetchAbort.current = controller;

      setLoading(true);
      setError("");
      const skip = (page - 1) * limit;
      const params = new URLSearchParams({
        skip: String(skip),
        limit: String(limit)
      });

      if (search.trim()) params.append('search', search.trim());
      if (projectId) params.append('project_id', projectId);

      const { records, total } = await apiCall(`/ran-sites?${params.toString()}`, {
        signal: controller.signal,
      });

      setRows(
        (records || []).map((r) => ({
          id: r.id,
          site_id: r.site_id,
          new_antennas: r.new_antennas,
          total_antennas: r.total_antennas,
          technical_boq: r.technical_boq,
          key: r.key,
          pid_po: r.pid_po,
        }))
      );
      setTotal(total || 0);
      setCurrentPage(page);
    } catch (err) {
      if (err.name !== "AbortError") setTransient(setError, err.message || "Failed to fetch sites");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProjects();
    fetchSites(1, "", rowsPerPage, '');
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    calculateStats();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rows, total]);

  const handleProjectChange = (e) => {
    const projectId = e.target.value;
    setSelectedProject(projectId);
    setSearchTerm('');
    setCurrentPage(1);
    fetchSites(1, '', rowsPerPage, projectId);
  };

  const handleGenerateBoq = async (row) => {
    setGeneratingBoqId(row.id);
    setError("");
    setSuccess("");
    try {
      const csvContent = await apiCall(`/ran-sites/${row.id}/generate-boq`);
      setEditableCsvData(parseCSV(csvContent));
      setCurrentSiteId(row.site_id);
      setShowCsvModal(true);
      setTransient(setSuccess, `BoQ for site ${row.site_id} generated successfully.`);
    } catch (err) {
      setTransient(setError, err.message);
    } finally {
      setGeneratingBoqId(null);
    }
  };

  const handleCellChange = (rowIndex, cellIndex, value) => {
    const updatedData = editableCsvData.map((row, rIdx) =>
      rIdx === rowIndex ? row.map((cell, cIdx) => (cIdx === cellIndex ? value : cell)) : row
    );
    setEditableCsvData(updatedData);
  };

  const handleAddRow = () => {
    const numColumns = editableCsvData[0]?.length || 1;
    const newRow = Array(numColumns).fill('----------------');
    const updatedData = [editableCsvData[0], ...editableCsvData.slice(1), newRow];
    setEditableCsvData(updatedData);
  };

  const handleDeleteRow = (rowIndexToDelete) => {
    if (rowIndexToDelete === 0) return;
    setEditableCsvData(editableCsvData.filter((_, index) => index !== rowIndexToDelete));
  };

  const downloadCSV = () => {
    if (!editableCsvData.length) return;
    const csvContent = stringifyCSV(editableCsvData);
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `boq_${currentSiteId || 'export'}_edited.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const onSearchChange = (e) => {
    const v = e.target.value;
    setSearchTerm(v);
    fetchSites(1, v);
  };

  const handleUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    if (!selectedProject) {
      setTransient(setError, "Please select a project before uploading.");
      e.target.value = '';
      return;
    }

    setUploading(true);
    setError("");
    setSuccess("");
    const formData = new FormData();
    formData.append("file", file);
    formData.append("pid_po", selectedProject);

    try {
      const result = await apiCall('/ran-sites/upload-csv', {
        method: "POST",
        body: formData,
      });
      setTransient(setSuccess, `Upload successful! ${result.inserted || "?"} rows inserted.`);
      fetchSites(1, searchTerm);
    } catch (err) {
      setTransient(setError, err.message);
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  };

  const handleDelete = async (row) => {
    if (!window.confirm("Are you sure you want to delete this site?")) return;
    try {
      await apiCall(`/ran-sites/${row.id}`, {
        method: "DELETE",
      });
      setTransient(setSuccess, "Site deleted successfully");
      fetchSites(currentPage, searchTerm);
    } catch (err) {
      setTransient(setError, err.message);
    }
  };

  const openCreateModal = () => {
    if (!selectedProject) {
      setTransient(setError, 'Please select a project to create a new RAN Site record.');
      return;
    }
    setCreateForm({
      site_id: '',
      new_antennas: '',
      total_antennas: '',
      technical_boq: '',
      key: '',
      pid_po: selectedProject
    });
    setShowCreateModal(true);
    setError('');
    setSuccess('');
  };

  const closeCreateModal = () => {
    setShowCreateModal(false);
    setCreateForm({
      site_id: '',
      new_antennas: '',
      total_antennas: '',
      technical_boq: '',
      key: '',
      pid_po: ''
    });
    setError('');
    setSuccess('');
  };

  const onCreateChange = (key, value) => {
    let convertedValue = value;
    if (key === 'total_antennas') {
      convertedValue = parseInt(value, 10);
      if (isNaN(convertedValue)) {
        convertedValue = '';
      }
    }
    setCreateForm((prev) => ({ ...prev, [key]: convertedValue }));
  };

  const handleCreate = async (e) => {
    e.preventDefault();
    setCreating(true);
    setError('');
    setSuccess('');
    try {
      await apiCall('/ran-sites/', {
        method: 'POST',
        body: JSON.stringify(createForm),
      });
      setTransient(setSuccess, 'Site created successfully!');
      fetchSites(currentPage, searchTerm);
      setTimeout(() => closeCreateModal(), 1200);
    } catch (err) {
      setTransient(setError, err.message);
    } finally {
      setCreating(false);
    }
  };

  const openEditModal = (row) => {
    setEditingRow(row);
    const { id, ...formFields } = row;
    setEditForm(formFields);
    setIsModalOpen(true);
  };

  const closeModal = () => {
    setIsModalOpen(false);
    setEditingRow(null);
    setEditForm({});
    setError("");
    setSuccess("");
  };

  const onEditChange = (key, value) => {
    let convertedValue = value;
    if (key === 'total_antennas') {
      convertedValue = parseInt(value, 10);
      if (isNaN(convertedValue)) {
        convertedValue = '';
      }
    }
    setEditForm((prev) => ({ ...prev, [key]: convertedValue }));
  };

  const handleUpdate = async () => {
    if (!editingRow) return;
    setUpdating(true);
    setError("");
    setSuccess("");
    try {
      await apiCall(`/ran-sites/${editingRow.id}`, {
        method: "PUT",
        body: JSON.stringify(editForm),
      });
      setTransient(setSuccess, "Site updated successfully!");
      closeModal();
      fetchSites(currentPage, searchTerm);
    } catch (err) {
      setTransient(setError, err.message);
    } finally {
      setUpdating(false);
    }
  };

  const totalPages = Math.ceil(total / rowsPerPage);
  const csvHeaders = editableCsvData[0] || [];
  const csvBody = editableCsvData.slice(1);

  const handleRowsPerPageChange = (e) => {
    const newLimit = parseInt(e.target.value);
    setRowsPerPage(newLimit);
    setCurrentPage(1);
    fetchSites(1, searchTerm, newLimit);
  };

  // Define stat cards
  const statCards = [
    { label: 'Total Sites', value: stats.total_sites || total },
    { label: 'Total Antennas', value: stats.total_antennas || 0 },
    { label: 'Current Page', value: `${currentPage} / ${totalPages || 1}` },
    { label: 'Showing', value: `${rows.length} items` },
    {
      label: 'Rows Per Page',
      isEditable: true,
      component: (
        <select
          className="stat-select"
          value={rowsPerPage}
          onChange={handleRowsPerPageChange}
        >
          <option value={25}>25</option>
          <option value={50}>50</option>
          <option value={100}>100</option>
          <option value={150}>150</option>
          <option value={200}>200</option>
          <option value={250}>250</option>
          <option value={500}>500</option>
        </select>
      )
    }
  ];

  // Define table columns
  const tableColumns = [
    {
      key: 'boq',
      label: 'BoQ',
      render: (row) => (
        <button
          onClick={() => handleGenerateBoq(row)}
          className="btn-generate"
          disabled={generatingBoqId === row.id || !row.key}
          title={!row.key ? "No key available for BoQ" : "Generate and Edit BoQ"}
        >
          {generatingBoqId === row.id ? '⚙️' : '📥'}
        </button>
      )
    },
    { key: 'site_id', label: 'Site ID' },
    { key: 'new_antennas', label: 'New Antennas' },
    { key: 'total_antennas', label: 'Total Antennas' },
    { key: 'technical_boq', label: 'Technical BoQ' },
    { key: 'key', label: 'Technical BoQ Key' },
    { key: 'pid_po', label: 'Project' }
  ];

  // Define table actions
  const tableActions = [
    {
      icon: '✏️',
      onClick: (row) => openEditModal(row),
      title: 'Edit',
      className: 'btn-edit'
    },
    {
      icon: '🗑️',
      onClick: (row) => handleDelete(row),
      title: 'Delete',
      className: 'btn-delete'
    }
  ];

  // Help modal sections
  const helpSections = [
    {
      icon: '📋',
      title: 'Overview',
      content: (
        <HelpText>
          The RAN LLD (Low-Level Design) Management component allows you to create, view, edit, and delete RAN site
          records for your projects. You can also generate Bill of Quantities (BoQ) for each site, bulk upload site
          data using CSV files, and filter sites by project. This system helps you manage antenna configurations
          and technical BoQ details.
        </HelpText>
      )
    },
    {
      icon: '✨',
      title: 'Features & Buttons',
      content: (
        <HelpList
          items={[
            { label: '+ New Site', text: 'Opens a form to create a new RAN site record. You must select a project first.' },
            { label: '📤 Upload CSV', text: 'Allows you to bulk upload RAN site records from a CSV file. Select a project before uploading.' },
            { label: 'Search', text: 'Filter sites by Site ID or BoQ in real-time.' },
            { label: 'Project Dropdown', text: 'Filter all site records and statistics by the selected project.' },
            { label: 'Clear Search', text: 'Resets the search filter and shows all sites for the selected project.' },
            { label: '📥 Generate BoQ', text: 'Click to generate a Bill of Quantities for that site. The BoQ will open in an editable modal where you can modify and download it.' },
            { label: '✏️ Edit', text: 'Click on any row\'s edit button to modify that site record.' },
            { label: '🗑️ Delete', text: 'Click on any row\'s delete button to remove that site (requires confirmation).' },
            { label: 'Rows Per Page Dropdown', text: 'Change how many sites are displayed per page (25-500).' }
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
            { label: 'Total Sites', text: 'Total count of RAN site records for the selected project (or all projects if none selected).' },
            { label: 'Total Antennas', text: 'Sum of all antennas across all sites in the current view.' },
            { label: 'Current Page', text: 'Shows which page you\'re viewing out of total pages.' },
            { label: 'Showing', text: 'Number of sites currently displayed on this page.' },
            { label: 'Rows Per Page', text: 'Adjustable dropdown to control pagination size.' }
          ]}
        />
      )
    },
    {
      icon: '📁',
      title: 'CSV Upload Guidelines',
      content: (
        <>
          <HelpText>
            To upload RAN sites via CSV, your file must contain the following headers (in any order):
          </HelpText>
          <CodeBlock
            items={[
              'site_id', 'new_antennas', 'total_antennas', 'technical_boq', 'key'
            ]}
          />
          <HelpText isNote>
            <strong>Note:</strong> Make sure to select a project before uploading. The CSV data will be associated
            with the selected project automatically. The "total_antennas" field should be a number.
          </HelpText>
        </>
      )
    },
    {
      icon: '🔧',
      title: 'BoQ Generation & Editing',
      content: (
        <HelpList
          items={[
            'Click the 📥 button in the BoQ column to generate a Bill of Quantities for that site.',
            'The BoQ will only generate if the site has a valid "key" value.',
            'After generation, an editable modal will open with the BoQ data in a table format.',
            'You can edit any cell directly by clicking and typing.',
            'Use the ➕ Add Row button to add new rows to the BoQ.',
            'Use the 🗑 button on each row to delete that row.',
            'Click ⬇ Download CSV to export the BoQ as a CSV file.',
            'The modal displays the total number of data rows (excluding the header).',
          ]}
        />
      )
    },
    {
      icon: '📡',
      title: 'Antenna Configuration',
      content: (
        <HelpText>
          Each RAN site can have "New Antennas" (antennas being added) and "Total Antennas" (total count after
          installation). The "Technical BoQ" field describes the type of BoQ configuration, and the "Technical BoQ Key"
          is used to generate the actual BoQ document. Make sure to set the correct key for each site to enable
          BoQ generation.
        </HelpText>
      )
    },
    {
      icon: '💡',
      title: 'Tips',
      content: (
        <HelpList
          items={[
            'Always select a project before creating sites or uploading CSV files.',
            'Use the search feature to quickly find sites by Site ID or BoQ.',
            'The table scrolls horizontally - use the scrollbar at the bottom to see all columns.',
            'Statistics update automatically when you filter by project or search.',
            'Ensure each site has a valid "key" to enable BoQ generation.',
            'Downloaded BoQ files can be imported into other systems or modified externally.',
            'Total Antennas should reflect the final count after installation is complete.'
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
          title="RAN LLD Management"
          subtitle="Manage RAN sites and generate Bill of Quantities"
          onInfoClick={() => setShowHelpModal(true)}
          infoTooltip="How to use this component"
        />
        <div className="header-actions">
          <button
            className={`btn-primary ${!selectedProject ? 'disabled' : ''}`}
            onClick={openCreateModal}
            disabled={!selectedProject}
            title={!selectedProject ? "Select a project first" : "Create a new site"}
          >
            <span className="btn-icon">+</span>
            New Site
          </button>
          <label className={`btn-secondary ${uploading || !selectedProject ? 'disabled' : ''}`}>
            <span className="btn-icon">📤</span>
            Upload CSV
            <input
              type="file"
              accept=".csv"
              style={{ display: "none" }}
              disabled={uploading || !selectedProject}
              onChange={handleUpload}
            />
          </label>
        </div>
      </div>

      {/* Filters Section */}
      <FilterBar
        searchTerm={searchTerm}
        onSearchChange={onSearchChange}
        searchPlaceholder="Search by Site ID or BoQ..."
        dropdowns={[
          {
            label: 'Project',
            value: selectedProject,
            onChange: handleProjectChange,
            placeholder: '-- Select a Project --',
            options: projects.map(p => ({
              value: p.pid_po,
              label: `${p.project_name} (${p.pid_po})`
            }))
          }
        ]}
        showClearButton={!!searchTerm}
        onClearSearch={() => { setSearchTerm(''); fetchSites(1, ''); }}
        clearButtonText="Clear Search"
      />

      {/* Messages */}
      {error && <div className="message error-message">{error}</div>}
      {success && <div className="message success-message">{success}</div>}
      {loading && <div className="loading-indicator">Loading RAN Sites...</div>}

      {/* Stats Bar - Carousel Style */}
      <StatsCarousel cards={statCards} visibleCount={4} />

      {/* Table Section */}
      <DataTable
        columns={tableColumns}
        data={rows}
        actions={tableActions}
        loading={loading}
        noDataMessage="No RAN sites found"
        className="inventory-table-wrapper"
      />

      {/* Pagination */}
      <Pagination
        currentPage={currentPage}
        totalPages={totalPages}
        onPageChange={(page) => fetchSites(page, searchTerm, rowsPerPage)}
        previousText="← Previous"
        nextText="Next →"
      />

      {/* Create Modal */}
      {showCreateModal && (
        <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && setShowCreateModal(false)}>
          <div className="modal-container">
            <div className="modal-header">
              <h2 className="modal-title">Create New RAN Site</h2>
              <button className="modal-close" onClick={closeCreateModal} type="button">✕</button>
            </div>

            <form className="modal-form" onSubmit={handleCreate}>
              {error && <div className="message error-message">{error}</div>}
              {success && <div className="message success-message">{success}</div>}

              {/* Project Information */}
              <div className="form-section">
                <h3 className="section-title">Project Information</h3>
                <div className="form-grid">
                  <div className="form-field full-width">
                    <label>Project ID</label>
                    <input
                      type="text"
                      name="pid_po"
                      value={createForm.pid_po}
                      onChange={(e) => onCreateChange('pid_po', e.target.value)}
                      required
                      disabled
                      className="disabled-input"
                    />
                  </div>
                </div>
              </div>

              {/* Site Information */}
              <div className="form-section">
                <h3 className="section-title">Site Information</h3>
                <div className="form-grid">
                  <div className="form-field">
                    <label>Site ID *</label>
                    <input
                      type="text"
                      name="site_id"
                      value={createForm.site_id}
                      onChange={(e) => onCreateChange('site_id', e.target.value)}
                      required
                    />
                  </div>
                  <div className="form-field">
                    <label>New Antennas</label>
                    <input
                      type="text"
                      name="new_antennas"
                      value={createForm.new_antennas}
                      onChange={(e) => onCreateChange('new_antennas', e.target.value)}
                    />
                  </div>
                  <div className="form-field">
                    <label>Total Antennas</label>
                    <input
                      type="number"
                      name="total_antennas"
                      value={createForm.total_antennas}
                      onChange={(e) => onCreateChange('total_antennas', e.target.value)}
                    />
                  </div>
                </div>
              </div>

              {/* Technical BoQ Information */}
              <div className="form-section">
                <h3 className="section-title">Technical BoQ Information</h3>
                <div className="form-grid">
                  <div className="form-field">
                    <label>Technical BoQ</label>
                    <input
                      type="text"
                      name="technical_boq"
                      value={createForm.technical_boq}
                      onChange={(e) => onCreateChange('technical_boq', e.target.value)}
                    />
                  </div>
                  <div className="form-field">
                    <label>Technical BoQ Key</label>
                    <input
                      type="text"
                      name="key"
                      value={createForm.key}
                      onChange={(e) => onCreateChange('key', e.target.value)}
                      placeholder="Required for BoQ generation"
                    />
                  </div>
                </div>
              </div>

              {/* Form Actions */}
              <div className="form-actions">
                <button type="button" className="btn-cancel" onClick={closeCreateModal}>
                  Cancel
                </button>
                <button type="submit" className="btn-submit" disabled={creating}>
                  {creating ? 'Creating...' : 'Create Site'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Edit Modal */}
      {isModalOpen && (
        <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && setIsModalOpen(false)}>
          <div className="modal-container">
            <div className="modal-header">
              <h2 className="modal-title">Edit Site: {editingRow?.site_id}</h2>
              <button className="modal-close" onClick={closeModal} type="button">✕</button>
            </div>

            <div className="modal-form">
              {error && <div className="message error-message">{error}</div>}
              {success && <div className="message success-message">{success}</div>}

              {/* Site Information */}
              <div className="form-section">
                <h3 className="section-title">Site Information</h3>
                <div className="form-grid">
                  <div className="form-field">
                    <label>Site ID</label>
                    <input
                      type="text"
                      value={editForm.site_id !== null && editForm.site_id !== undefined ? editForm.site_id : ''}
                      onChange={(e) => onEditChange('site_id', e.target.value)}
                    />
                  </div>
                  <div className="form-field">
                    <label>New Antennas</label>
                    <input
                      type="text"
                      value={editForm.new_antennas !== null && editForm.new_antennas !== undefined ? editForm.new_antennas : ''}
                      onChange={(e) => onEditChange('new_antennas', e.target.value)}
                    />
                  </div>
                  <div className="form-field">
                    <label>Total Antennas</label>
                    <input
                      type="number"
                      value={editForm.total_antennas !== null && editForm.total_antennas !== undefined ? editForm.total_antennas : ''}
                      onChange={(e) => onEditChange('total_antennas', e.target.value)}
                    />
                  </div>
                  <div className="form-field">
                    <label>Project</label>
                    <select
                      value={editForm.pid_po || ''}
                      onChange={(e) => onEditChange('pid_po', e.target.value)}
                    >
                      <option value="">-- Select Project --</option>
                      {projects.map((p) => (
                        <option key={p.pid_po} value={p.pid_po}>
                          {p.project_name} ({p.pid_po})
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
              </div>

              {/* Technical BoQ Information */}
              <div className="form-section">
                <h3 className="section-title">Technical BoQ Information</h3>
                <div className="form-grid">
                  <div className="form-field">
                    <label>Technical BoQ</label>
                    <input
                      type="text"
                      value={editForm.technical_boq !== null && editForm.technical_boq !== undefined ? editForm.technical_boq : ''}
                      onChange={(e) => onEditChange('technical_boq', e.target.value)}
                    />
                  </div>
                  <div className="form-field">
                    <label>Technical BoQ Key</label>
                    <input
                      type="text"
                      value={editForm.key !== null && editForm.key !== undefined ? editForm.key : ''}
                      onChange={(e) => onEditChange('key', e.target.value)}
                    />
                  </div>
                </div>
              </div>

              {/* Form Actions */}
              <div className="form-actions">
                <button type="button" className="btn-cancel" onClick={closeModal}>
                  Cancel
                </button>
                <button className="btn-submit" onClick={handleUpdate} disabled={updating}>
                  {updating ? 'Updating...' : 'Update Site'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Editable CSV Modal (kept as-is) */}
      {showCsvModal && (
        <div className="modal-overlay" style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.5)', display: 'flex', justifyContent: 'center', alignItems: 'center', zIndex: 1000 }}>
          <div style={{ background: '#fff', padding: 24, borderRadius: 8, width: '95%', height: '90%', display: 'flex', flexDirection: 'column' }}>

            {/* Modal Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16, flexShrink: 0 }}>
              <h3 style={{ margin: 0 }}>Edit BoQ Data for {currentSiteId}</h3>
              <button onClick={() => setShowCsvModal(false)} style={{ fontSize: 18, cursor: 'pointer', background: 'none', border: 'none', padding: '4px 8px' }}>
                ✖
              </button>
            </div>

            {/* Action Buttons */}
            <div style={{ display: 'flex', gap: 12, marginBottom: 16, flexShrink: 0 }}>
              <button onClick={handleAddRow} style={{ padding: '8px 16px', borderRadius: 6, cursor: 'pointer', background: '#4CAF50', color: 'white', border: 'none' }}>
                ➕ Add Row
              </button>
              <button onClick={downloadCSV} style={{ padding: '8px 16px', borderRadius: 6, cursor: 'pointer', background: '#2196F3', color: 'white', border: 'none' }}>
                ⬇ Download CSV
              </button>
               <span style={{ color: '#666', alignSelf: 'center' }}>
                {csvBody.filter(row => row.join('').trim() !== '').length} rows
              </span>
            </div>

            {/* Editable Table Container */}
            <div style={{ flex: 1, overflow: 'auto', border: '1px solid #ddd', borderRadius: 6 }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: '1200px' }}>
                <thead style={{ background: '#f5f5f5', position: 'sticky', top: 0, zIndex: 1 }}>
                  <tr>
                    <th style={{ padding: '12px 8px', border: '1px solid #ddd', textAlign: 'left', minWidth: '80px' }}>Action</th>
                    {csvHeaders.map((header, index) => (
                      <th key={index} style={{ padding: '12px 8px', border: '1px solid #ddd', textAlign: 'left', minWidth: '200px', whiteSpace: 'nowrap' }}>
                        {header}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {csvBody.length === 0 ? (
                    <tr><td colSpan={csvHeaders.length + 1} style={{ textAlign: 'center', padding: 20 }}>No data rows.</td></tr>
                  ) : (
                    csvBody.map((row, rowIndex) => (
                      row.join("").trim() && <tr key={rowIndex}>
                        <td style={{ padding: '8px', border: '1px solid #ddd', textAlign: 'center' }}>
                           <button onClick={() => handleDeleteRow(rowIndex + 1)} style={{ background: '#f44336', color: 'white', border: 'none', borderRadius: 4, padding: '4px 8px', cursor: 'pointer', fontSize: '12px'}} title="Remove row">
                            🗑
                          </button>
                        </td>
                        {row.map((cell, cellIndex) => (
                          <td key={cellIndex} style={{ padding: '4px', border: '1px solid #ddd' }}>
                            <input
                              type="text"
                              value={cell}
                              onChange={(e) => handleCellChange(rowIndex + 1, cellIndex, e.target.value)}
                              style={{ width: '100%', border: 'none', padding: '8px', background: 'transparent', fontSize: '14px' }}
                            />
                          </td>
                        ))}
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>

          </div>
        </div>
      )}

      {/* Help/Info Modal */}
      <HelpModal
        show={showHelpModal}
        onClose={() => setShowHelpModal(false)}
        title="RAN LLD Management - User Guide"
        sections={helpSections}
        closeButtonText="Got it!"
      />
    </div>
  );
}
