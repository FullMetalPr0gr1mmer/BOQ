import React, { useState, useEffect, useRef } from "react";
import { apiCall, setTransient } from "../api.js";
import "../css/Dismantling.css";

const ROWS_PER_PAGE = 50;

export default function RANAntennaSerials() {
  const [rows, setRows] = useState([]);
  const [currentPage, setCurrentPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [uploading, setUploading] = useState(false);
  const [loading, setLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingRow, setEditingRow] = useState(null);
  const [editForm, setEditForm] = useState({});
  const [updating, setUpdating] = useState(false);

  // State for project management
  const [projects, setProjects] = useState([]);
  const [selectedProject, setSelectedProject] = useState('');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [createForm, setCreateForm] = useState({
    mrbts: '',
    antenna_model: '',
    serial_number: '',
    pid_po: ''
  });
  const [creating, setCreating] = useState(false);

  const fetchAbort = useRef(null);

  // Function to fetch user's accessible projects
  const fetchProjects = async () => {
    try {
      const data = await apiCall('/ran-projects');
      setProjects(data || []);
      // Optionally, auto-select the first project
      if (data && data.length > 0) {
        setSelectedProject(data[0].pid_po);
      }
    } catch (err) {
      setTransient(setError, 'Failed to load projects. Please ensure you have project access.');
      console.error(err);
    }
  };

  const fetchAntennaSerials = async (page = 1, search = "") => {
    try {
      if (fetchAbort.current) fetchAbort.current.abort();
      const controller = new AbortController();
      fetchAbort.current = controller;

      setLoading(true);
      setError("");
      const skip = (page - 1) * ROWS_PER_PAGE;
      const params = new URLSearchParams();
      params.set("skip", String(skip));
      params.set("limit", String(ROWS_PER_PAGE));
      if (search.trim()) params.set("search", search.trim());

      const { records, total } = await apiCall(`/ran-antenna-serials?${params.toString()}`, {
        signal: controller.signal,
      });

      setRows(
        (records || []).map((r) => ({
          id: r.id,
          mrbts: r.mrbts,
          antenna_model: r.antenna_model,
          serial_number: r.serial_number,
          pid_po: r.pid_po,
        }))
      );
      setTotal(total || 0);
      setCurrentPage(page);
    } catch (err) {
      if (err.name !== "AbortError") setTransient(setError, err.message || "Failed to fetch records");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProjects(); // Fetch projects on component mount
    fetchAntennaSerials(1, "");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const onSearchChange = (e) => {
    const v = e.target.value;
    setSearchTerm(v);
    fetchAntennaSerials(1, v);
  };

  // Handle Upload with project selection
  const handleUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    // Check if a project is selected
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
    formData.append("project_id", selectedProject);

    try {
      const result = await apiCall('/ran-antenna-serials/upload-csv', {
        method: "POST",
        body: formData,
      });
      setTransient(setSuccess, `Upload successful! ${result.message}`);
      fetchAntennaSerials(1, searchTerm);
    } catch (err) {
      setTransient(setError, err.message);
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm("Are you sure you want to delete this record?")) return;
    try {
      await apiCall(`/ran-antenna-serials/${id}`, {
        method: "DELETE",
      });
      setTransient(setSuccess, "Record deleted successfully");
      fetchAntennaSerials(currentPage, searchTerm);
    } catch (err) {
      setTransient(setError, err.message);
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
    setEditForm((prev) => ({ ...prev, [key]: value }));
  };

  const handleUpdate = async () => {
    if (!editingRow) return;
    setUpdating(true);
    setError("");
    setSuccess("");
    try {
      await apiCall(`/ran-antenna-serials/${editingRow.id}`, {
        method: "PUT",
        body: JSON.stringify(editForm),
      });
      setTransient(setSuccess, "Record updated successfully!");
      closeModal();
      fetchAntennaSerials(currentPage, searchTerm);
    } catch (err) {
      setTransient(setError, err.message);
    } finally {
      setUpdating(false);
    }
  };

  // Functions for creating records
  const openCreateModal = () => {
    if (!selectedProject) {
      setTransient(setError, 'Please select a project to create a new record.');
      return;
    }
    setCreateForm({
      mrbts: '',
      antenna_model: '',
      serial_number: '',
      pid_po: selectedProject
    });
    setShowCreateModal(true);
    setError('');
    setSuccess('');
  };

  const closeCreateModal = () => {
    setShowCreateModal(false);
    setCreateForm({
      mrbts: '',
      antenna_model: '',
      serial_number: '',
      pid_po: ''
    });
    setError('');
    setSuccess('');
  };

  const onCreateChange = (key, value) => {
    setCreateForm((prev) => ({ ...prev, [key]: value }));
  };

  const handleCreate = async (e) => {
    e.preventDefault();
    setCreating(true);
    setError('');
    setSuccess('');
    try {
      await apiCall('/ran-antenna-serials', {
        method: 'POST',
        body: JSON.stringify(createForm),
      });
      setTransient(setSuccess, 'Record created successfully!');
      fetchAntennaSerials(currentPage, searchTerm);
      setTimeout(() => closeCreateModal(), 1200);
    } catch (err) {
      setTransient(setError, err.message);
    } finally {
      setCreating(false);
    }
  };

  const totalPages = Math.ceil(total / ROWS_PER_PAGE);

  return (
    <>
      <div className="dismantling-container">
        {/* Header & Upload */}
        <div className="dismantling-header-row">
          <h2>RAN Antenna Serials</h2>
          <div style={{ display: 'flex', gap: 16 }}>
            <button
              className="upload-btn"
              onClick={openCreateModal}
              disabled={!selectedProject}
              title={!selectedProject ? "Select a project first" : "Create a new antenna serial record"}
            >
              + New Record
            </button>
            <label className={`upload-btn ${uploading || !selectedProject ? "disabled" : ""}`}
              title={!selectedProject ? "Select a project first" : "Upload Antenna Serials CSV"}
            >
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

        {/* Search & Project Selection */}
        <div className="dismantling-search-container">
          <input
            type="text"
            placeholder="Filter by MRBTS, Antenna Model, or Serial Number..."
            value={searchTerm}
            onChange={onSearchChange}
            className="search-input"
          />
          {searchTerm && (
            <button
              onClick={() => {
                setSearchTerm("");
                fetchAntennaSerials(1, "");
              }}
              className="clear-btn"
            >
              Clear
            </button>
          )}

          <select
            id="project-select"
            className="search-input"
            value={selectedProject}
            onChange={(e) => setSelectedProject(e.target.value)}
          >
            <option value="">-- Select a Project --</option>
            {projects.map((p) => (
              <option key={p.pid_po} value={p.pid_po}>
                {p.project_name} ({p.pid_po})
              </option>
            ))}
          </select>
        </div>

        {/* Messages */}
        {error && <div className="dismantling-message error">{error}</div>}
        {success && <div className="dismantling-message success">{success}</div>}
        {loading && <div className="loading-message">Loading Antenna Serials...</div>}

        {/* Table */}
        <div className="dismantling-table-container">
          <table className="dismantling-table">
            <thead>
              <tr>
                <th>MRBTS</th>
                <th>Antenna Model</th>
                <th>Serial Number</th>
                <th>Project ID</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {rows.length === 0 && !loading ? (
                <tr>
                  <td colSpan={5} className="no-results">
                    No results
                  </td>
                </tr>
              ) : (
                rows.map((row) => (
                  <tr key={row.id}>
                    <td>{row.mrbts}</td>
                    <td>{row.antenna_model}</td>
                    <td>{row.serial_number}</td>
                    <td>{row.pid_po}</td>
                    <td className="actions-cell">
                      <button className="clear-btn" onClick={() => openEditModal(row)}>
                        Edit
                      </button>
                      <button className="clear-btn" onClick={() => handleDelete(row.id)}>
                        Delete
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="dismantling-pagination">
            <button
              className="pagination-btn"
              disabled={currentPage === 1}
              onClick={() => fetchAntennaSerials(currentPage - 1, searchTerm)}
            >
              Prev
            </button>
            <span className="pagination-info">
              Page {currentPage} of {totalPages}
            </span>
            <button
              className="pagination-btn"
              disabled={currentPage === totalPages}
              onClick={() => fetchAntennaSerials(currentPage + 1, searchTerm)}
            >
              Next
            </button>
          </div>
        )}

        {/* Create Modal */}
        {showCreateModal && (
          <div className="modal-overlay">
            <div className="modal-content">
              <form onSubmit={handleCreate}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12 }}>
                  <h3>Create New Antenna Serial Record</h3>
                  <button type="button" onClick={closeCreateModal} className="close-btn">Close</button>
                </div>

                {error && <div className="dismantling-message error">{error}</div>}
                {success && <div className="dismantling-message success">{success}</div>}

                <table className="dismantling-table" style={{ width: '100%', borderSpacing: 0, borderCollapse: 'collapse' }}>
                  <tbody>
                    <tr>
                      <td style={{ fontWeight: 'bold' }}>MRBTS</td>
                      <td>
                        <input
                          type="text"
                          value={createForm.mrbts}
                          onChange={e => onCreateChange('mrbts', e.target.value)}
                          style={{ width: '100%', padding: '8px', boxSizing: 'border-box' }}
                          required
                        />
                      </td>
                    </tr>
                    <tr>
                      <td style={{ fontWeight: 'bold' }}>Antenna Model</td>
                      <td>
                        <input
                          type="text"
                          value={createForm.antenna_model}
                          onChange={e => onCreateChange('antenna_model', e.target.value)}
                          style={{ width: '100%', padding: '8px', boxSizing: 'border-box' }}
                          required
                        />
                      </td>
                    </tr>
                    <tr>
                      <td style={{ fontWeight: 'bold' }}>Serial Number</td>
                      <td>
                        <input
                          type="text"
                          value={createForm.serial_number}
                          onChange={e => onCreateChange('serial_number', e.target.value)}
                          style={{ width: '100%', padding: '8px', boxSizing: 'border-box' }}
                          required
                        />
                      </td>
                    </tr>
                  </tbody>
                </table>
                <button
                  type="submit"
                  disabled={creating}
                  className="pagination-btn"
                  style={{ marginTop: 12, width: '100%' }}
                >
                  {creating ? 'Creating...' : 'Create Record'}
                </button>
              </form>
            </div>
          </div>
        )}

        {/* Edit Modal */}
        {isModalOpen && (
          <div className="modal-overlay">
            <div className="modal-content">
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12 }}>
                <h3>Edit Antenna Serial Record</h3>
                <button onClick={closeModal} className="close-btn">Close</button>
              </div>
              <table className="dismantling-table" style={{ width: '100%', borderSpacing: 0, borderCollapse: 'collapse' }}>
                <tbody>
                  <tr key="mrbts">
                    <td style={{ fontWeight: 'bold' }}>MRBTS</td>
                    <td>
                      <input type="text" value={editForm.mrbts !== null && editForm.mrbts !== undefined ? editForm.mrbts : ''} onChange={e => onEditChange('mrbts', e.target.value)} style={{ width: '100%', padding: '8px', boxSizing: 'border-box' }} />
                    </td>
                  </tr>
                  <tr key="antenna_model">
                    <td style={{ fontWeight: 'bold' }}>Antenna Model</td>
                    <td>
                      <input type="text" value={editForm.antenna_model !== null && editForm.antenna_model !== undefined ? editForm.antenna_model : ''} onChange={e => onEditChange('antenna_model', e.target.value)} style={{ width: '100%', padding: '8px', boxSizing: 'border-box' }} />
                    </td>
                  </tr>
                  <tr key="serial_number">
                    <td style={{ fontWeight: 'bold' }}>Serial Number</td>
                    <td>
                      <input type="text" value={editForm.serial_number !== null && editForm.serial_number !== undefined ? editForm.serial_number : ''} onChange={e => onEditChange('serial_number', e.target.value)} style={{ width: '100%', padding: '8px', boxSizing: 'border-box' }} />
                    </td>
                  </tr>
                  <tr key="pid_po">
                    <td style={{ fontWeight: 'bold' }}>Project</td>
                    <td>
                      <select
                        value={editForm.pid_po || ''}
                        onChange={e => onEditChange('pid_po', e.target.value)}
                        style={{ width: '100%', padding: '8px', boxSizing: 'border-box' }}
                      >
                        <option value="">-- Select Project --</option>
                        {projects.map((p) => (
                          <option key={p.pid_po} value={p.pid_po}>
                            {p.project_name} ({p.pid_po})
                          </option>
                        ))}
                      </select>
                    </td>
                  </tr>
                </tbody>
              </table>
              <button
                onClick={handleUpdate}
                disabled={updating}
                className="pagination-btn"
                style={{ marginTop: 12, width: '100%' }}
              >
                {updating ? 'Updating...' : 'Update'}
              </button>
            </div>
          </div>
        )}
      </div>
    </>
  );
}
