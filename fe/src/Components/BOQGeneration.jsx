import React, { useState, useEffect, useRef } from 'react';
import { apiCall, setTransient } from '../api.js';
import '../css/Inventory.css';
import StatsCarousel from './shared/StatsCarousel';
import FilterBar from './shared/FilterBar';
import DataTable from './shared/DataTable';
import HelpModal, { HelpList, HelpText, CodeBlock } from './shared/HelpModal';
import TitleWithInfo from './shared/InfoButton';
import Pagination from './shared/Pagination';

const ROWS_PER_PAGE = 100;

// --- Helper Functions ---
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

export default function BOQGeneration() {
  // --- State Variables ---
  const [rows, setRows] = useState([]);
  const [currentPage, setCurrentPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [uploading, setUploading] = useState(false);
  const [loading, setLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [linkedIp, setLinkedIp] = useState('');
  const [generating, setGenerating] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [showForm, setShowForm] = useState(false);
  const [editingRow, setEditingRow] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [editableCsvData, setEditableCsvData] = useState([]);
  const [showHelpModal, setShowHelpModal] = useState(false);

  // --- Project state ---
  const [projects, setProjects] = useState([]);
  const [selectedProject, setSelectedProject] = useState('');

  const [formData, setFormData] = useState({
    linkid: '',
    InterfaceName: '',
    SiteIPA: '',
    SiteIPB: '',
    pid_po: '',
  });

  const fetchAbort = useRef(null);

  // --- Fetch user's projects ---
  const fetchProjects = async () => {
    try {
      const data = await apiCall('/get_project');
      setProjects(data || []);
      // Don't set a default project - let user select one
    } catch (err) {
      setTransient(setError, 'Failed to load projects. Please ensure you have project access.');
      console.error(err);
    }
  };

  // --- Data Fetching ---
  const fetchReferences = async (page = 1, search = '', projectId = selectedProject) => {
    try {
      if (fetchAbort.current) fetchAbort.current.abort();
      const controller = new AbortController();
      fetchAbort.current = controller;
      setLoading(true);
      setError('');

      const skip = (page - 1) * ROWS_PER_PAGE;
      const params = new URLSearchParams({ skip: skip.toString(), limit: ROWS_PER_PAGE.toString() });
      if (search.trim()) params.set('search', search.trim());
      if (projectId) params.set('project_id', projectId);

      const data = await apiCall(`/boq/references?${params.toString()}`, {
        signal: controller.signal,
        method: 'GET',
      });

      setRows((data.items || []).map(r => ({
        id: r.id,
        linkedIp: r.linkid,
        interfaceName: r.InterfaceName,
        siteA: r.SiteIPA,
        siteB: r.SiteIPB,
        pid_po: r.pid_po,
      })));
      setTotal(data.total || 0);
      setCurrentPage(page);
    } catch (err) {
      if (err.name !== 'AbortError') {
        setTransient(setError, err.message || 'Failed to fetch');
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProjects();
    fetchReferences(1, '');
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleProjectChange = (e) => {
    const projectId = e.target.value;
    setSelectedProject(projectId);
    setSearchTerm('');
    setCurrentPage(1);
    fetchReferences(1, '', projectId);
  };

  const onSearchChange = (e) => {
    const v = e.target.value;
    setSearchTerm(v);
    fetchReferences(1, v, selectedProject);
  };

  // --- Handle Upload ---
  const handleUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    if (!selectedProject) {
      setTransient(setError, "Please select a project before uploading.");
      e.target.value = '';
      return;
    }

    setUploading(true);
    setError('');
    setSuccess('');

    const formDataLocal = new FormData();
    formDataLocal.append('file', file);

    try {
      const result = await apiCall(`/boq/upload-reference?project_id=${selectedProject}`, {
        method: 'POST',
        body: formDataLocal,
      });

      setTransient(setSuccess, `Upload successful! ${result.rows_inserted} rows inserted.`);
      fetchReferences(1, searchTerm);
    } catch (err) {
      setTransient(setError, err.message);
    } finally {
      setUploading(false);
      e.target.value = '';
    }
  };

  // --- Generate BOQ ---
  const handleGenerateRow = async (row) => {
    if (!row || !row.linkedIp) {
      setTransient(setError, 'Selected row is invalid');
      return;
    }

    setGenerating(true);
    setError('');
    setLinkedIp(row.linkedIp);

    try {
      const data = await apiCall('/boq/generate-boq', {
        method: 'POST',
        body: JSON.stringify({ siteA: row.siteA, siteB: row.siteB, linkedIp: row.linkedIp }),
      });

      if (data.csv_content) {
        setEditableCsvData(parseCSV(data.csv_content));
        setShowModal(true);
      } else {
        throw new Error('No CSV content received from the server.');
      }
    } catch (err) {
      setTransient(setError, err.message);
    } finally {
      setGenerating(false);
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
    link.setAttribute('download', `BOQ_${linkedIp || 'export'}_edited.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  // --- Create / Edit / Delete ---
  const openCreateModal = () => {
    if (!selectedProject) {
      setTransient(setError, 'Please select a project to create a new reference.');
      return;
    }
    setFormData({
      linkid: '',
      InterfaceName: '',
      SiteIPA: '',
      SiteIPB: '',
      pid_po: selectedProject,
    });
    setEditingRow(null);
    setShowForm(true);
    setError('');
    setSuccess('');
  };

  const openEditModal = async (row) => {
    if (!row || !row.id) {
      setTransient(setError, 'Cannot edit: missing id');
      return;
    }
    setEditingRow(row);
    try {
      setLoading(true);
      const data = await apiCall(`/boq/reference/${row.id}`, {
        method: 'GET',
      });
      setFormData({
        linkid: data.linkid || '',
        InterfaceName: data.InterfaceName || '',
        SiteIPA: data.SiteIPA || '',
        SiteIPB: data.SiteIPB || '',
        pid_po: data.pid_po || '',
      });
      setShowForm(true);
      setError('');
      setSuccess('');
    } catch (err) {
      setTransient(setError, err.message || 'Failed to load reference for editing');
    } finally {
      setLoading(false);
    }
  };

  const closeFormModal = () => {
    setShowForm(false);
    setEditingRow(null);
    setFormData({
      linkid: '',
      InterfaceName: '',
      SiteIPA: '',
      SiteIPB: '',
      pid_po: '',
    });
    setError('');
    setSuccess('');
  };

  const handleFormInputChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleFormSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setError('');
    setSuccess('');
    try {
      const submitData = {
        ...formData,
        pid_po: formData.pid_po || selectedProject
      };
      if (editingRow) {
        await apiCall(`/boq/reference/${editingRow.id}`, {
          method: 'PUT',
          body: JSON.stringify(submitData),
        });
        setTransient(setSuccess, 'Reference updated successfully!');
      } else {
        await apiCall('/boq/reference', {
          method: 'POST',
          body: JSON.stringify(submitData),
        });
        setTransient(setSuccess, 'Reference created successfully!');
      }
      fetchReferences(currentPage, searchTerm);
      setTimeout(() => closeFormModal(), 1200);
    } catch (err) {
      setTransient(setError, err.message);
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (row) => {
    if (!row || !row.id) return;
    if (!window.confirm(`Are you sure you want to delete reference "${row.linkedIp}"?`)) return;
    try {
      await apiCall(`/boq/reference/${row.id}`, {
        method: 'DELETE',
      });
      setTransient(setSuccess, 'Reference deleted successfully!');
      fetchReferences(currentPage, searchTerm);
    } catch (err) {
      setTransient(setError, err.message);
    }
  };

  const totalPages = Math.ceil(total / ROWS_PER_PAGE);
  const csvHeaders = editableCsvData[0] || [];
  const csvBody = editableCsvData.slice(1);

  // Define all stat cards for the carousel
  const statCards = [
    { label: 'Total References', value: total },
    { label: 'Current Page', value: `${currentPage} / ${totalPages || 1}` },
    { label: 'Showing', value: `${rows.length} items` },
  ];

  // Define table columns
  const tableColumns = [
    {
      key: 'generate',
      label: 'Generate',
      render: (row) => (
        <button
          title={`Generate BOQ for ${row.linkedIp}`}
          onClick={() => handleGenerateRow(row)}
          disabled={generating}
          className="btn-generate"
        >
          ▼
        </button>
      )
    },
    { key: 'linkedIp', label: 'Linked-IP' },
    { key: 'interfaceName', label: 'Interface Name' },
    { key: 'siteA', label: 'Site-A IP' },
    { key: 'siteB', label: 'Site-B IP' },
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

  // Define help modal sections
  const helpSections = [
    {
      icon: '📋',
      title: 'Overview',
      content: (
        <HelpText>
          The BOQ Generation component allows you to manage BOQ references and generate Bill of Quantities (BOQ)
          documents for your network links. You can create, edit, and delete references, and bulk upload reference
          data using CSV files.
        </HelpText>
      )
    },
    {
      icon: '✨',
      title: 'Features & Buttons',
      content: (
        <HelpList
          items={[
            { label: '+ New Reference', text: 'Opens a form to create a new BOQ reference. You must select a project first.' },
            { label: '📤 Upload Reference', text: 'Allows you to bulk upload BOQ references from a CSV file. Select a project before uploading.' },
            { label: 'Search', text: 'Filter references by linkid, interface name, or site IP in real-time.' },
            { label: 'Project Dropdown', text: 'Filter all BOQ references by the selected project.' },
            { label: 'Clear Search', text: 'Resets the search filter and shows all references for the selected project.' },
            { label: '▼ Generate', text: 'Click to generate a BOQ document for that specific link reference. The generated BOQ will open in an editable modal.' },
            { label: '✏️ Edit', text: 'Click on any row\'s edit button to modify that reference.' },
            { label: '🗑️ Delete', text: 'Click on any row\'s delete button to remove that reference (requires confirmation).' },
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
            { label: 'Total References', text: 'Total count of BOQ references for the selected project (or all projects if none selected).' },
            { label: 'Current Page', text: 'Shows which page you\'re viewing out of total pages.' },
            { label: 'Showing', text: 'Number of references currently displayed on this page.' },
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
            To upload BOQ references via CSV, your file must contain the following headers (in any order):
          </HelpText>
          <CodeBlock
            items={[
              'linkid', 'InterfaceName', 'SiteIPA', 'SiteIPB'
            ]}
          />
          <HelpText isNote>
            <strong>Note:</strong> Make sure to select a project before uploading. The CSV data will be associated
            with the selected project automatically.
          </HelpText>
        </>
      )
    },
    {
      icon: '🔧',
      title: 'BOQ Generation Modal',
      content: (
        <HelpList
          items={[
            'After clicking the ▼ Generate button, a modal will open with the generated BOQ data in an editable table.',
            'You can edit any cell directly by clicking and typing.',
            'Use the ➕ Add Row button to add new rows to the BOQ.',
            'Use the 🗑 button on each row to delete that row.',
            'Click ⬇ Download CSV to export the BOQ as a CSV file.',
            'The modal displays the total number of data rows (excluding the header).',
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
            'Always select a project before creating references or uploading CSV files.',
            'Use the search feature to quickly find references by link ID, interface name, or site IPs.',
            'The table scrolls horizontally - use the scrollbar at the bottom to see all columns.',
            'All required fields are marked with an asterisk (*) in the form.',
            'Generated BOQs can be edited and downloaded as CSV files for further processing.',
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
          title="BOQ Generation"
          subtitle="Manage BOQ references and generate Bill of Quantities"
          onInfoClick={() => setShowHelpModal(true)}
          infoTooltip="How to use this component"
        />
        <div className="header-actions">
          <button
            className={`btn-primary ${!selectedProject ? 'disabled' : ''}`}
            onClick={openCreateModal}
            disabled={!selectedProject}
            title={!selectedProject ? "Select a project first" : "Create a new reference"}
          >
            <span className="btn-icon">+</span>
            New Reference
          </button>
          <label className={`btn-secondary ${uploading || !selectedProject ? 'disabled' : ''}`}>
            <span className="btn-icon">📤</span>
            Upload Reference
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
        searchPlaceholder="Search by linkid, interface, or site IP..."
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
        onClearSearch={() => { setSearchTerm(''); fetchReferences(1, ''); }}
        clearButtonText="Clear Search"
      />

      {/* Messages */}
      {error && <div className="message error-message">{error}</div>}
      {success && <div className="message success-message">{success}</div>}
      {loading && <div className="loading-indicator">Loading references...</div>}

      {/* Stats Bar - Carousel Style */}
      <StatsCarousel cards={statCards} visibleCount={4} />

      {/* Table Section */}
      <DataTable
        columns={tableColumns}
        data={rows}
        actions={tableActions}
        loading={loading}
        noDataMessage="No BOQ references found"
        className="inventory-table-wrapper"
      />

      {/* Pagination */}
      <Pagination
        currentPage={currentPage}
        totalPages={totalPages}
        onPageChange={(page) => fetchReferences(page, searchTerm)}
        previousText="← Previous"
        nextText="Next →"
      />

      {/* BOQ Generation Modal (kept as-is) */}
      {showModal && (
        <div className="modal-overlay" style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.5)', display: 'flex', justifyContent: 'center', alignItems: 'center', zIndex: 1000 }}>
          <div style={{ background: '#fff', padding: 24, borderRadius: 8, width: '95%', height: '90%', display: 'flex', flexDirection: 'column' }}>

            {/* Modal Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16, flexShrink: 0 }}>
              <h3 style={{ margin: 0 }}>Edit BOQ Data for {linkedIp}</h3>
              <button onClick={() => setShowModal(false)} style={{ fontSize: 18, cursor: 'pointer', background: 'none', border: 'none', padding: '4px 8px' }}>
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

      {/* Form Modal */}
      {showForm && (
        <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && setShowForm(false)}>
          <div className="modal-container">
            <div className="modal-header">
              <h2 className="modal-title">
                {editingRow ? `Edit Reference: '${editingRow.linkedIp}'` : 'Create New Reference'}
              </h2>
              <button className="modal-close" onClick={closeFormModal} type="button">
                ✕
              </button>
            </div>

            <form className="modal-form" onSubmit={handleFormSubmit}>
              {/* Messages */}
              {error && <div className="message error-message">{error}</div>}
              {success && <div className="message success-message">{success}</div>}

              {/* Project Information Section */}
              <div className="form-section">
                <h3 className="section-title">Project Information</h3>
                <div className="form-grid">
                  <div className="form-field full-width">
                    <label>Project ID</label>
                    <input
                      type="text"
                      name="pid_po"
                      value={formData.pid_po}
                      onChange={handleFormInputChange}
                      required
                      disabled
                      className="disabled-input"
                    />
                  </div>
                </div>
              </div>

              {/* Reference Information Section */}
              <div className="form-section">
                <h3 className="section-title">Reference Information</h3>
                <div className="form-grid">
                  <div className="form-field">
                    <label>Linked ID *</label>
                    <input
                      type="text"
                      name="linkid"
                      placeholder="Linked ID (linkid)"
                      value={formData.linkid}
                      onChange={handleFormInputChange}
                      required
                    />
                  </div>
                  <div className="form-field">
                    <label>Interface Name</label>
                    <input
                      type="text"
                      name="InterfaceName"
                      placeholder="Interface Name"
                      value={formData.InterfaceName}
                      onChange={handleFormInputChange}
                    />
                  </div>
                  <div className="form-field">
                    <label>Site A IP *</label>
                    <input
                      type="text"
                      name="SiteIPA"
                      placeholder="Site A IP (SiteIPA)"
                      value={formData.SiteIPA}
                      onChange={handleFormInputChange}
                      required
                    />
                  </div>
                  <div className="form-field">
                    <label>Site B IP *</label>
                    <input
                      type="text"
                      name="SiteIPB"
                      placeholder="Site B IP (SiteIPB)"
                      value={formData.SiteIPB}
                      onChange={handleFormInputChange}
                      required
                    />
                  </div>
                </div>
              </div>

              {/* Form Actions */}
              <div className="form-actions">
                <button type="button" className="btn-cancel" onClick={closeFormModal}>
                  Cancel
                </button>
                <button type="submit" className="btn-submit" disabled={submitting}>
                  {submitting ? 'Saving...' : (editingRow ? 'Update Reference' : 'Create Reference')}
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
        title="BOQ Generation - User Guide"
        sections={helpSections}
        closeButtonText="Got it!"
      />
    </div>
  );
}
