import React, { useState, useEffect, useRef } from "react";
import { apiCall, setTransient } from "../api.js";
import "../css/Inventory.css";
import '../css/shared/DownloadButton.css';
import StatsCarousel from '../Components/shared/StatsCarousel';
import FilterBar from '../Components/shared/FilterBar';
import DataTable from '../Components/shared/DataTable';
import HelpModal, { HelpList, HelpText, CodeBlock } from '../Components/shared/HelpModal';
import TitleWithInfo from '../Components/shared/InfoButton';
import { downloadDURolloutSheetUploadTemplate } from '../utils/csvTemplateDownloader';
import Pagination from '../Components/shared/Pagination';
import DeleteConfirmationModal from '../Components/shared/DeleteConfirmationModal';

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

export default function RolloutSheet() {
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
  const [showDeleteAllModal, setShowDeleteAllModal] = useState(false);
  const [deleteAllLoading, setDeleteAllLoading] = useState(false);

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingRow, setEditingRow] = useState(null);
  const [editForm, setEditForm] = useState({});
  const [updating, setUpdating] = useState(false);

  const [projects, setProjects] = useState([]);
  const [selectedProject, setSelectedProject] = useState('');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [createForm, setCreateForm] = useState({
    site_id: '',
    scope: '',
    year_target_scope: '',
    partner: '',
    partner_requester_name: '',
    date_of_partner_request: '',
    survey_partner: '',
    implementation_partner: '',
    ant_swap: '',
    additional_cost: '',
    wr_transportation: '',
    crane: '',
    ac_armod_cable_new_sran: '',
    military_factor: '',
    cicpa_factor: '',
    nokia_rollout_requester: '',
    services_validation_by_rollout: '',
    date_of_validation_by_rollout: '',
    request_status: '',
    du_po_number: '',
    integration_status: '',
    integration_date: '',
    du_po_convention_name: '',
    po_year_issuance: '',
    smp_number: '',
    wo_number: '',
    sps_category: '',
    submission_date: '',
    po_status: '',
    pac_received: '',
    date_of_pac: '',
    hardware_remark: '',
    project_id: ''
  });
  const [creating, setCreating] = useState(false);
  const [stats, setStats] = useState({ total_items: 0, unique_sites: 0, unique_partners: 0 });
  const [filterOptions, setFilterOptions] = useState({ partners: [], request_statuses: [], integration_statuses: [] });
  const [selectedPartner, setSelectedPartner] = useState('');
  const [selectedStatus, setSelectedStatus] = useState('');

  // BOQ Generation Modal State
  const [generatingBoqId, setGeneratingBoqId] = useState(null);
  const [showBoqModal, setShowBoqModal] = useState(false);
  const [editableCsvData, setEditableCsvData] = useState([]);
  const [currentSiteId, setCurrentSiteId] = useState('');

  // Multi-selection State
  const [selectedRows, setSelectedRows] = useState(new Set());
  const [selectAll, setSelectAll] = useState(false);

  // Bulk BOQ Generation State
  const [bulkGenerating, setBulkGenerating] = useState(false);
  const [bulkBoqData, setBulkBoqData] = useState([]); // Array of {entry_id, site_id, scope, csvData}
  const [currentBoqIndex, setCurrentBoqIndex] = useState(0);

  const fetchAbort = useRef(null);

  const fetchProjects = async () => {
    try {
      const data = await apiCall('/du-projects');
      const projectsList = data?.records || data || [];
      setProjects(projectsList);
    } catch (err) {
      setTransient(setError, 'Failed to load projects.');
      console.error(err);
    }
  };

  const fetchFilterOptions = async () => {
    try {
      const data = await apiCall('/rollout-sheet/filters/options');
      setFilterOptions(data || { partners: [], request_statuses: [], integration_statuses: [] });
    } catch (err) {
      console.error('Failed to fetch filter options:', err);
    }
  };

  const fetchStats = async (projectId = '') => {
    try {
      const params = new URLSearchParams();
      if (projectId) params.append('project_id', projectId);

      const data = await apiCall(`/rollout-sheet/stats?${params.toString()}`);
      setStats(data || { total_items: 0, unique_sites: 0, unique_partners: 0 });
    } catch (err) {
      console.error('Failed to fetch stats:', err);
    }
  };

  const fetchRolloutSheet = async (page = 1, search = "", limit = rowsPerPage, projectId = selectedProject) => {
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
      if (selectedPartner) params.append('partner', selectedPartner);
      if (selectedStatus) params.append('request_status', selectedStatus);

      const { records, total } = await apiCall(`/rollout-sheet?${params.toString()}`, {
        signal: controller.signal,
      });

      setRows(records || []);
      setTotal(total || 0);
      setCurrentPage(page);
    } catch (err) {
      if (err.name !== "AbortError") setTransient(setError, err.message || "Failed to fetch records");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProjects();
    fetchFilterOptions();
    fetchRolloutSheet(1, "", rowsPerPage, '');
    fetchStats('');
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleProjectChange = (e) => {
    const projectId = e.target.value;
    setSelectedProject(projectId);
    setSearchTerm('');
    setCurrentPage(1);
    fetchRolloutSheet(1, '', rowsPerPage, projectId);
    fetchStats(projectId);
  };

  const onSearchChange = (e) => {
    const v = e.target.value;
    setSearchTerm(v);
    fetchRolloutSheet(1, v, rowsPerPage, selectedProject);
  };

  const handleUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    if (!selectedProject) {
      setTransient(setError, 'Please select a project before uploading.');
      e.target.value = "";
      return;
    }

    setUploading(true);
    setError("");
    setSuccess("");
    const formData = new FormData();
    formData.append("file", file);
    formData.append("project_id", selectedProject);

    try {
      const result = await apiCall('/rollout-sheet/upload-csv', {
        method: "POST",
        body: formData,
      });
      setTransient(setSuccess, `Upload successful! ${result.message}`);
      fetchRolloutSheet(1, searchTerm);
      fetchStats(selectedProject);
      fetchFilterOptions();
    } catch (err) {
      setTransient(setError, err.message);
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  };

  const handleDelete = async (row) => {
    if (!window.confirm("Are you sure you want to delete this record?")) return;
    try {
      await apiCall(`/rollout-sheet/${row.id}`, { method: "DELETE" });
      setTransient(setSuccess, "Record deleted successfully");
      fetchRolloutSheet(currentPage, searchTerm);
      fetchStats(selectedProject);
    } catch (err) {
      setTransient(setError, err.message);
    }
  };

  const handleDeleteAllRolloutSheet = () => {
    if (!selectedProject) {
      setTransient(setError, 'Please select a project first.');
      return;
    }
    setShowDeleteAllModal(true);
  };

  const confirmDeleteAllRolloutSheet = async () => {
    if (!selectedProject) return;

    setDeleteAllLoading(true);
    setError('');
    setSuccess('');

    try {
      const result = await apiCall(`/rollout-sheet/delete-all/${selectedProject}`, { method: 'DELETE' });
      const message = `Successfully deleted ${result.deleted_count} rollout sheet entries.`;
      setTransient(setSuccess, message);
      setShowDeleteAllModal(false);
      setSelectedProject('');
      fetchRolloutSheet(1, '', rowsPerPage, '');
      fetchStats('');
    } catch (err) {
      setTransient(setError, err.message || 'Failed to delete rollout sheet entries');
      setShowDeleteAllModal(false);
    } finally {
      setDeleteAllLoading(false);
    }
  };

  const cancelDeleteAllRolloutSheet = () => {
    if (!deleteAllLoading) {
      setShowDeleteAllModal(false);
    }
  };

  const getSelectedProjectName = () => {
    const project = projects.find(p => p.pid_po === selectedProject);
    return project ? `${project.project_name} (${project.pid_po})` : selectedProject;
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
      await apiCall(`/rollout-sheet/${editingRow.id}`, {
        method: "PUT",
        body: JSON.stringify(editForm),
      });
      setTransient(setSuccess, "Record updated successfully!");
      closeModal();
      fetchRolloutSheet(currentPage, searchTerm);
      fetchStats(selectedProject);
    } catch (err) {
      setTransient(setError, err.message);
    } finally {
      setUpdating(false);
    }
  };

  const openCreateModal = () => {
    if (!selectedProject) {
      setTransient(setError, 'Please select a project to create a new record.');
      return;
    }
    setCreateForm({
      site_id: '',
      scope: '',
      year_target_scope: '',
      partner: '',
      partner_requester_name: '',
      date_of_partner_request: '',
      survey_partner: '',
      implementation_partner: '',
      ant_swap: '',
      additional_cost: '',
      wr_transportation: '',
      crane: '',
      ac_armod_cable_new_sran: '',
      military_factor: '',
      cicpa_factor: '',
      nokia_rollout_requester: '',
      services_validation_by_rollout: '',
      date_of_validation_by_rollout: '',
      request_status: '',
      du_po_number: '',
      integration_status: '',
      integration_date: '',
      du_po_convention_name: '',
      po_year_issuance: '',
      smp_number: '',
      wo_number: '',
      sps_category: '',
      submission_date: '',
      po_status: '',
      pac_received: '',
      date_of_pac: '',
      hardware_remark: '',
      project_id: selectedProject
    });
    setShowCreateModal(true);
    setError('');
    setSuccess('');
  };

  const closeCreateModal = () => {
    setShowCreateModal(false);
    setCreateForm({});
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
      await apiCall('/rollout-sheet', {
        method: 'POST',
        body: JSON.stringify(createForm),
      });
      setTransient(setSuccess, 'Record created successfully!');
      fetchRolloutSheet(currentPage, searchTerm);
      fetchStats(selectedProject);
      fetchFilterOptions();
      setTimeout(() => closeCreateModal(), 1200);
    } catch (err) {
      setTransient(setError, err.message);
    } finally {
      setCreating(false);
    }
  };

  // BOQ Generation Handlers
  const handleGenerateBoq = async (row) => {
    if (!row.scope) {
      setTransient(setError, 'This entry has no scope defined. Cannot generate BOQ.');
      return;
    }
    setGeneratingBoqId(row.id);
    setError("");
    setSuccess("");
    try {
      const csvContent = await apiCall(`/rollout-sheet/${row.id}/generate-boq`);
      setEditableCsvData(parseCSV(csvContent));
      setCurrentSiteId(row.site_id);
      setShowBoqModal(true);
      setTransient(setSuccess, `BOQ for site ${row.site_id} generated successfully.`);
    } catch (err) {
      setTransient(setError, err.message);
    } finally {
      setGeneratingBoqId(null);
    }
  };

  // Excel Download Handlers
  const handleDownloadSingleExcel = async (row) => {
    if (!row.scope) {
      setTransient(setError, 'This entry has no scope defined. Cannot download BOQ.');
      return;
    }
    setGeneratingBoqId(row.id);
    setError("");
    try {
      const token = localStorage.getItem('token');
      const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8003';
      const response = await fetch(`${API_BASE}/rollout-sheet/${row.id}/download-boq-excel`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (!response.ok) {
        const errorText = await response.text();
        let errorMessage = 'Failed to download Excel file';
        try {
          const errorData = JSON.parse(errorText);
          errorMessage = errorData.detail || errorMessage;
        } catch (e) {
          errorMessage = errorText || errorMessage;
        }
        throw new Error(errorMessage);
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `BOQ_${row.site_id}_${new Date().toISOString().slice(0,10)}.xlsx`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      setTransient(setSuccess, `Excel BOQ for site ${row.site_id} downloaded successfully.`);
    } catch (err) {
      setTransient(setError, err.message);
    } finally {
      setGeneratingBoqId(null);
    }
  };

  // Selection Handlers
  const handleSelectRow = (rowId) => {
    const newSelected = new Set(selectedRows);
    if (newSelected.has(rowId)) {
      newSelected.delete(rowId);
    } else {
      newSelected.add(rowId);
    }
    setSelectedRows(newSelected);
    // Update selectAll state based on whether all rows with scope are selected
    const selectableRows = rows.filter(row => row.scope);
    setSelectAll(newSelected.size === selectableRows.length && selectableRows.length > 0);
  };

  const handleSelectAll = () => {
    if (selectAll) {
      setSelectedRows(new Set());
      setSelectAll(false);
    } else {
      const allIds = rows
        .filter(row => row.scope) // Only select rows with scope
        .map(row => row.id);
      setSelectedRows(new Set(allIds));
      setSelectAll(true);
    }
  };

  // Bulk BOQ Generation Handler
  const handleBulkGenerateBoq = async () => {
    if (selectedRows.size === 0) {
      setTransient(setError, 'Please select at least one site to generate BOQ.');
      return;
    }

    setBulkGenerating(true);
    setError("");
    setSuccess("");

    try {
      const entryIds = Array.from(selectedRows);
      const response = await apiCall('/rollout-sheet/bulk-generate-boq', {
        method: 'POST',
        body: JSON.stringify({ entry_ids: entryIds })
      });

      console.log('Bulk BOQ Response:', response);
      console.log('Total results:', response.results.length);
      console.log('Successful:', response.successful);
      console.log('Failed:', response.failed);

      const successfulBoqs = response.results
        .filter(r => r.success)
        .map(r => ({
          entry_id: r.entry_id,
          site_id: r.site_id,
          scope: r.scope,
          csvData: parseCSV(r.csv_content)
        }));

      const failedBoqs = response.results
        .filter(r => !r.success)
        .map(r => ({
          site_id: r.site_id || `Entry ID: ${r.entry_id}`,
          error: r.error
        }));

      if (successfulBoqs.length === 0) {
        const failedSites = failedBoqs.map(f => f.site_id).join(', ');
        setTransient(setError, `Failed to generate BOQs for all selected sites: ${failedSites}`);
        return;
      }

      setBulkBoqData(successfulBoqs);
      setCurrentBoqIndex(0);
      setShowBoqModal(true);

      const failedCount = response.failed;
      if (failedCount > 0) {
        const failedSites = failedBoqs.map(f => f.site_id).join(', ');
        setTransient(setSuccess,
          `Generated ${successfulBoqs.length} BOQs successfully. ${failedCount} failed: ${failedSites}`);
      } else {
        setTransient(setSuccess,
          `Generated ${successfulBoqs.length} BOQs successfully.`);
      }
    } catch (err) {
      setTransient(setError, err.message);
    } finally {
      setBulkGenerating(false);
    }
  };

  // Bulk Excel Download Handler
  const handleBulkDownloadExcel = async () => {
    if (selectedRows.size === 0) {
      setTransient(setError, 'Please select at least one site to download BOQ.');
      return;
    }

    setBulkGenerating(true);
    setError("");
    try {
      const entryIds = Array.from(selectedRows);
      const token = localStorage.getItem('token');
      const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8003';
      const response = await fetch(`${API_BASE}/rollout-sheet/bulk-download-boq-excel`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ entry_ids: entryIds })
      });

      if (!response.ok) {
        const errorText = await response.text();
        let errorMessage = 'Failed to download Excel file';
        try {
          const errorData = JSON.parse(errorText);
          errorMessage = errorData.detail || errorMessage;
        } catch (e) {
          errorMessage = errorText || errorMessage;
        }
        throw new Error(errorMessage);
      }

      // Check for partial success (some sites failed)
      const failedCount = response.headers.get('X-BOQ-Failed-Count');
      const successCount = response.headers.get('X-BOQ-Success-Count');
      const failedSites = response.headers.get('X-BOQ-Failed-Sites');

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `BOQ_Bulk_${selectedRows.size}_sites_${new Date().toISOString().slice(0,10)}.xlsx`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      // Show appropriate message based on success/failure
      if (failedCount && parseInt(failedCount) > 0) {
        const warningMsg = `Downloaded BOQ for ${successCount} sites successfully. ${failedCount} sites failed: ${failedSites}`;
        setTransient(setError, warningMsg);
      } else {
        setTransient(setSuccess, `Bulk Excel BOQ for ${selectedRows.size} sites downloaded successfully.`);
      }
      setSelectedRows(new Set());
      setSelectAll(false);
    } catch (err) {
      setTransient(setError, err.message);
    } finally {
      setBulkGenerating(false);
    }
  };

  // Navigation Handlers
  const handlePreviousBoq = () => {
    if (currentBoqIndex > 0) {
      setCurrentBoqIndex(currentBoqIndex - 1);
    }
  };

  const handleNextBoq = () => {
    if (currentBoqIndex < bulkBoqData.length - 1) {
      setCurrentBoqIndex(currentBoqIndex + 1);
    }
  };

  const getCurrentBoq = () => {
    return bulkBoqData[currentBoqIndex];
  };

  const handleCellChange = (rowIndex, cellIndex, value) => {
    // Check if we're in bulk mode
    if (bulkBoqData.length > 0) {
      const currentBoq = getCurrentBoq();
      const updatedData = currentBoq.csvData.map((row, rIdx) =>
        rIdx === rowIndex ? row.map((cell, cIdx) =>
          cIdx === cellIndex ? value : cell
        ) : row
      );

      // Update the current BOQ's data in bulkBoqData
      const updatedBulkData = [...bulkBoqData];
      updatedBulkData[currentBoqIndex].csvData = updatedData;
      setBulkBoqData(updatedBulkData);
    } else {
      // Single mode - use legacy state
      const updatedData = editableCsvData.map((row, rIdx) =>
        rIdx === rowIndex ? row.map((cell, cIdx) => (cIdx === cellIndex ? value : cell)) : row
      );
      setEditableCsvData(updatedData);
    }
  };

  const handleAddRow = () => {
    if (bulkBoqData.length > 0) {
      const currentBoq = getCurrentBoq();
      const numColumns = currentBoq.csvData[0]?.length || 1;
      const newRow = Array(numColumns).fill('');
      const updatedData = [
        currentBoq.csvData[0],
        ...currentBoq.csvData.slice(1),
        newRow
      ];

      const updatedBulkData = [...bulkBoqData];
      updatedBulkData[currentBoqIndex].csvData = updatedData;
      setBulkBoqData(updatedBulkData);
    } else {
      // Single mode - use legacy state
      const numColumns = editableCsvData[0]?.length || 1;
      const newRow = Array(numColumns).fill('');
      const updatedData = [editableCsvData[0], ...editableCsvData.slice(1), newRow];
      setEditableCsvData(updatedData);
    }
  };

  const handleDeleteRow = (rowIndexToDelete) => {
    if (rowIndexToDelete === 0) return; // Don't delete header

    if (bulkBoqData.length > 0) {
      const currentBoq = getCurrentBoq();
      const updatedData = currentBoq.csvData.filter((_, index) =>
        index !== rowIndexToDelete
      );

      const updatedBulkData = [...bulkBoqData];
      updatedBulkData[currentBoqIndex].csvData = updatedData;
      setBulkBoqData(updatedBulkData);
    } else {
      // Single mode - use legacy state
      setEditableCsvData(editableCsvData.filter((_, index) => index !== rowIndexToDelete));
    }
  };

  const downloadCSV = () => {
    // Get the current data based on mode (bulk vs single)
    let dataToDownload;
    let filename;

    if (bulkBoqData.length > 0) {
      // Bulk mode - use current BOQ's data
      const currentBoq = getCurrentBoq();
      dataToDownload = currentBoq.csvData;
      filename = `boq_${currentBoq.site_id}_generated.csv`;
    } else {
      // Single mode - use editableCsvData
      dataToDownload = editableCsvData;
      filename = `boq_${currentSiteId || 'export'}_generated.csv`;
    }

    if (!dataToDownload || !dataToDownload.length) {
      setTransient(setError, 'No data to download');
      return;
    }

    const csvContent = stringifyCSV(dataToDownload);
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', filename);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
    setTransient(setSuccess, 'CSV downloaded successfully');
  };

  // Download current BOQ as Excel using template (with edited data)
  const downloadCurrentAsExcel = async () => {
    // Get the current data based on mode
    let csvData, siteId, entryId;

    if (bulkBoqData.length > 0) {
      // Bulk mode - use current BOQ's data
      const currentBoq = getCurrentBoq();
      csvData = currentBoq.csvData;
      siteId = currentBoq.site_id;
      entryId = currentBoq.entry_id;
    } else {
      // Single mode - use editableCsvData
      csvData = editableCsvData;
      siteId = currentSiteId;
      entryId = rows.find(r => r.site_id === currentSiteId)?.id;
    }

    if (!csvData || !csvData.length || !entryId) {
      setTransient(setError, 'No data available for download or could not determine entry ID.');
      return;
    }

    try {
      const token = localStorage.getItem('token');
      const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8003';

      // Send CSV data to backend for Excel generation
      const response = await fetch(`${API_BASE}/rollout-sheet/download-boq-excel-from-csv`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          entry_id: entryId,
          csv_data: csvData,
          site_id: siteId
        })
      });

      if (!response.ok) {
        const errorText = await response.text();
        let errorMessage = 'Failed to download Excel file';
        try {
          const errorData = JSON.parse(errorText);
          errorMessage = errorData.detail || errorMessage;
        } catch (e) {
          errorMessage = errorText || errorMessage;
        }
        throw new Error(errorMessage);
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `BOQ_${siteId}_${new Date().toISOString().slice(0,10)}.xlsx`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      setTransient(setSuccess, `Excel BOQ for site ${siteId} downloaded successfully.`);
    } catch (err) {
      setTransient(setError, err.message);
    }
  };

  // Download all BOQs as Excel using template (bulk mode only, with edited data)
  const downloadAllAsExcel = async () => {
    if (bulkBoqData.length === 0) {
      setTransient(setError, 'No bulk data available.');
      return;
    }

    try {
      // Prepare all BOQ data with their CSV data
      const boqDataList = bulkBoqData.map(boq => ({
        entry_id: boq.entry_id,
        site_id: boq.site_id,
        csv_data: boq.csvData
      }));

      const token = localStorage.getItem('token');
      const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8003';
      const response = await fetch(`${API_BASE}/rollout-sheet/bulk-download-boq-excel-from-csv`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ boq_data_list: boqDataList })
      });

      if (!response.ok) {
        const errorText = await response.text();
        let errorMessage = 'Failed to download Excel file';
        try {
          const errorData = JSON.parse(errorText);
          errorMessage = errorData.detail || errorMessage;
        } catch (e) {
          errorMessage = errorText || errorMessage;
        }
        throw new Error(errorMessage);
      }

      // Check for partial success (some sites failed)
      const failedCount = response.headers.get('X-BOQ-Failed-Count');
      const successCount = response.headers.get('X-BOQ-Success-Count');
      const failedSites = response.headers.get('X-BOQ-Failed-Sites');

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `BOQ_Bulk_${bulkBoqData.length}_sites_${new Date().toISOString().slice(0,10)}.xlsx`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      // Show appropriate message based on success/failure
      if (failedCount && parseInt(failedCount) > 0) {
        const warningMsg = `Downloaded BOQ for ${successCount} sites successfully. ${failedCount} sites failed: ${failedSites}`;
        setTransient(setError, warningMsg);
      } else {
        setTransient(setSuccess, `Bulk Excel BOQ for ${bulkBoqData.length} sites downloaded successfully.`);
      }
    } catch (err) {
      setTransient(setError, err.message);
    }
  };

  const closeBoqModal = () => {
    setShowBoqModal(false);
    setEditableCsvData([]);
    setCurrentSiteId('');
    setBulkBoqData([]);
    setCurrentBoqIndex(0);
    setSelectedRows(new Set());
    setSelectAll(false);
  };

  const totalPages = Math.ceil(total / rowsPerPage);

  const handleRowsPerPageChange = (e) => {
    const newLimit = parseInt(e.target.value);
    setRowsPerPage(newLimit);
    setCurrentPage(1);
    fetchRolloutSheet(1, searchTerm, newLimit);
  };

  // Define stat cards
  const statCards = [
    { label: 'Total Items', value: stats.total_items || total },
    { label: 'Unique Sites', value: stats.unique_sites || 0 },
    { label: 'Unique Partners', value: stats.unique_partners || 0 },
    { label: 'Current Page', value: `${currentPage} / ${totalPages || 1}` },
    { label: 'Showing', value: `${rows.length} items` },
    {
      label: 'Rows Per Page',
      isEditable: true,
      component: (
        <select className="stat-select" value={rowsPerPage} onChange={handleRowsPerPageChange}>
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

  // CSV data for modal - support both single and bulk modes
  const currentBoq = bulkBoqData.length > 0 ? getCurrentBoq() : null;
  const csvHeaders = currentBoq ? currentBoq.csvData[0] : editableCsvData[0] || [];
  const csvBody = currentBoq ? currentBoq.csvData.slice(1) : editableCsvData.slice(1);

  // Define table columns (all fields)
  const tableColumns = [
    {
      key: 'select',
      label: (
        <input
          type="checkbox"
          checked={selectAll}
          onChange={handleSelectAll}
          title="Select all sites with scope"
        />
      ),
      render: (row) => (
        <input
          type="checkbox"
          checked={selectedRows.has(row.id)}
          onChange={() => handleSelectRow(row.id)}
          disabled={!row.scope}
          title={!row.scope ? "No scope defined" : "Select site"}
        />
      )
    },
    {
      key: 'boq',
      label: 'BoQ',
      render: (row) => (
        <button
          onClick={() => handleGenerateBoq(row)}
          className="btn-generate"
          disabled={generatingBoqId === row.id || !row.scope}
          title={!row.scope ? "No scope defined for BoQ" : "Generate single BoQ (CSV editor)"}
        >
          {generatingBoqId === row.id ? '⚙️' : '📥'}
        </button>
      )
    },
    {
      key: 'excel',
      label: 'Excel',
      render: (row) => (
        <button
          onClick={() => handleDownloadSingleExcel(row)}
          className="btn-generate"
          disabled={generatingBoqId === row.id || !row.scope}
          title={!row.scope ? "No scope defined for Excel" : "Download BOQ as Excel"}
        >
          {generatingBoqId === row.id ? '⚙️' : '📊'}
        </button>
      )
    },
    { key: 'site_id', label: 'Site ID' },
    { key: 'scope', label: 'Scope' },
    { key: 'year_target_scope', label: 'Year Target Scope' },
    { key: 'partner', label: 'Partner' },
    { key: 'partner_requester_name', label: 'Partner Requester' },
    { key: 'date_of_partner_request', label: 'Date of Partner Request' },
    { key: 'survey_partner', label: 'Survey Partner' },
    { key: 'implementation_partner', label: 'Implementation Partner' },
    { key: 'ant_swap', label: 'Ant Swap' },
    { key: 'additional_cost', label: 'Additional Cost' },
    { key: 'wr_transportation', label: 'WR Transportation' },
    { key: 'crane', label: 'Crane' },
    { key: 'ac_armod_cable_new_sran', label: 'AC Armod Cable New SRAN' },
    { key: 'military_factor', label: 'Military Factor' },
    { key: 'cicpa_factor', label: 'CICPA Factor' },
    { key: 'nokia_rollout_requester', label: 'Nokia Rollout Requester' },
    { key: 'services_validation_by_rollout', label: 'Services Validation' },
    { key: 'date_of_validation_by_rollout', label: 'Date of Validation' },
    { key: 'request_status', label: 'Request Status' },
    { key: 'du_po_number', label: 'DU PO Number' },
    { key: 'integration_status', label: 'Integration Status' },
    { key: 'integration_date', label: 'Integration Date' },
    { key: 'du_po_convention_name', label: 'DU PO Convention Name' },
    { key: 'po_year_issuance', label: 'PO Year Issuance' },
    { key: 'smp_number', label: 'SMP Number' },
    { key: 'wo_number', label: 'WO Number' },
    { key: 'sps_category', label: 'SPS Category' },
    { key: 'submission_date', label: 'Submission Date' },
    { key: 'po_status', label: 'PO Status' },
    { key: 'pac_received', label: 'PAC Received' },
    { key: 'date_of_pac', label: 'Date of PAC' },
    { key: 'hardware_remark', label: 'Hardware Remark' },
    { key: 'project_id', label: 'Project' }
  ];

  // Define table actions
  const tableActions = [
    { icon: '✏️', onClick: (row) => openEditModal(row), title: 'Edit', className: 'btn-edit' },
    { icon: '🗑️', onClick: (row) => handleDelete(row), title: 'Delete', className: 'btn-delete' }
  ];

  // Help modal sections
  const helpSections = [
    {
      icon: '📋',
      title: 'Overview',
      content: (
        <HelpText>
          The 5G Rollout Sheet Management component allows you to track and manage 5G deployment activities.
          You can create, view, edit, and delete rollout entries, upload data via CSV, and filter by project, partner, and status.
        </HelpText>
      )
    },
    {
      icon: '✨',
      title: 'Features & Buttons',
      content: (
        <HelpList
          items={[
            { label: '+ New Record', text: 'Opens a form to create a new rollout entry. Select a project first.' },
            { label: 'Bulk CSV', text: 'Generate BOQ for selected sites and open in CSV editor for review/editing.' },
            { label: 'Bulk Excel', text: 'Download BOQ for all selected sites as one Excel file using the template (ordered by line).' },
            { label: '📤 Upload CSV', text: 'Bulk upload rollout data from a CSV file.' },
            { label: '🗑️ Delete All', text: 'Deletes ALL rollout entries for the selected project.' },
            { label: 'Search', text: 'Filter entries by Site ID, Partner, PO Number, etc.' },
            { label: 'Project Dropdown', text: 'Filter all entries by project.' },
            { label: '📥 BoQ', text: 'Generate single BOQ in CSV format (opens editor for review).' },
            { label: '📊 Excel', text: 'Download single BOQ as Excel file using the template.' },
            { label: '✏️ Edit', text: 'Modify an existing rollout entry.' },
            { label: '🗑️ Delete', text: 'Remove a rollout entry (requires confirmation).' },
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
            Your CSV file must have these exact headers (in order):
          </HelpText>
          <CodeBlock
            items={[
              'Site ID',
              'Scope',
              'Year Target Scope',
              'Partner',
              'Partner Requester Name',
              'Date of Partner Request',
              'Survey Partner',
              'Implementation Partner',
              'Ant Swap',
              'Additional Cost',
              'WR Transportation',
              'Crane',
              'AC Armod Cable New SRAN',
              'Military Factor',
              'CICPA Factor',
              'Nokia Rollout Requester',
              'Services Validation by Rollout',
              'Date of Validation by Rollout',
              'Request Status',
              'DU PO Number',
              'Integration Status',
              'Integration Date',
              'DU PO Convention Name',
              'PO Year Issuance',
              'SMP Number',
              'WO Number',
              'SPS Category',
              'Submission Date',
              'PO Status',
              'PAC Received',
              'Date of PAC',
              'Hardware Remark'
            ]}
          />
          <button className="btn-download-template" onClick={downloadDURolloutSheetUploadTemplate} type="button">
            Download CSV Template
          </button>
          <HelpText isNote>
            <strong>Note:</strong> Select a project before uploading to associate the data with that project.
          </HelpText>
        </>
      )
    },
    {
      icon: '📊',
      title: 'Excel Download Features',
      content: (
        <>
          <HelpText>
            The BOQ Excel download uses the official template and preserves all formatting, colors, and logos.
          </HelpText>
          <HelpList
            items={[
              { label: 'Single Site', text: 'Click the 📊 Excel button in any row to download BOQ for that site.' },
              { label: 'Bulk Download', text: 'Select multiple sites using checkboxes, then click "Bulk Excel" to download all sites in one file.' },
              { label: 'Ordered Output', text: 'All BOQ items are automatically sorted by line number.' },
              { label: 'Mapped Fields', text: 'ERP Item Code, Budget Line, SMP, and all other fields are automatically populated.' },
            ]}
          />
        </>
      )
    },
    {
      icon: '💡',
      title: 'Tips',
      content: (
        <HelpList
          items={[
            'Always select a project before creating entries or uploading CSV files.',
            'Use the search feature to quickly find entries.',
            'The table scrolls horizontally - use the scrollbar to see all columns.',
            'Statistics update automatically when you filter by project.',
            'For bulk Excel download, select multiple sites and click "Bulk Excel" - all sites will be combined in one file.',
            'Only sites with a defined scope can generate BOQs.',
          ]}
        />
      )
    }
  ];

  // Form field renderer helper - uses != null to properly show 0 values
  const renderFormField = (label, name, value, onChange, required = false, disabled = false) => (
    <div className="form-field">
      <label>{label}{required && ' *'}</label>
      <input
        type="text"
        name={name}
        value={value != null ? value : ''}
        onChange={onChange}
        required={required}
        disabled={disabled}
        className={disabled ? 'disabled-input' : ''}
      />
    </div>
  );

  return (
    <div className="inventory-container">
      {/* Header Section */}
      <div className="inventory-header">
        <TitleWithInfo
          title="5G Rollout Sheet Management"
          subtitle="Track and manage 5G deployment activities"
          onInfoClick={() => setShowHelpModal(true)}
          infoTooltip="How to use this component"
        />
        <div className="header-actions">
          <button
            className={`btn-primary ${!selectedProject ? 'disabled' : ''}`}
            onClick={openCreateModal}
            disabled={!selectedProject}
            title={!selectedProject ? "Select a project first" : "Create a new entry"}
          >
            <span className="btn-icon">+</span>
            New Record
          </button>
          <button
            className={`btn-primary ${selectedRows.size === 0 || bulkGenerating ? 'disabled' : ''}`}
            onClick={handleBulkGenerateBoq}
            disabled={selectedRows.size === 0 || bulkGenerating}
            title={selectedRows.size === 0 ? "Select sites first" : `Generate BOQ CSV for ${selectedRows.size} sites (opens editor)`}
          >
            <span className="btn-icon">{bulkGenerating ? '⚙️' : '📥'}</span>
            {bulkGenerating ? 'Processing...' : `Bulk CSV (${selectedRows.size})`}
          </button>
          <button
            className={`btn-primary ${selectedRows.size === 0 || bulkGenerating ? 'disabled' : ''}`}
            onClick={handleBulkDownloadExcel}
            disabled={selectedRows.size === 0 || bulkGenerating}
            title={selectedRows.size === 0 ? "Select sites first" : `Download BOQ Excel for ${selectedRows.size} sites`}
          >
            <span className="btn-icon">{bulkGenerating ? '⚙️' : '📊'}</span>
            {bulkGenerating ? 'Processing...' : `Bulk Excel (${selectedRows.size})`}
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
          <button
            className={`btn-danger ${!selectedProject ? 'disabled' : ''}`}
            onClick={handleDeleteAllRolloutSheet}
            disabled={!selectedProject}
            title={!selectedProject ? "Select a project first" : "Delete all entries for this project"}
          >
            <span className="btn-icon">🗑️</span>
            Delete All
          </button>
        </div>
      </div>

      {/* Filters Section */}
      <FilterBar
        searchTerm={searchTerm}
        onSearchChange={onSearchChange}
        searchPlaceholder="Search by Site ID, Partner, PO Number..."
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
        onClearSearch={() => { setSearchTerm(''); fetchRolloutSheet(1, ''); }}
        clearButtonText="Clear Search"
      />

      {/* Messages */}
      {error && <div className="message error-message">{error}</div>}
      {success && <div className="message success-message">{success}</div>}
      {loading && <div className="loading-indicator">Loading 5G Rollout Sheet...</div>}

      {/* Stats Bar */}
      <StatsCarousel cards={statCards} visibleCount={4} />

      {/* Table Section */}
      <DataTable
        columns={tableColumns}
        data={rows}
        actions={tableActions}
        loading={loading}
        noDataMessage="No rollout sheet entries found"
        className="inventory-table-wrapper"
      />

      {/* Pagination */}
      <Pagination
        currentPage={currentPage}
        totalPages={totalPages}
        onPageChange={(page) => fetchRolloutSheet(page, searchTerm, rowsPerPage)}
        previousText="← Previous"
        nextText="Next →"
      />

      {/* Create Modal */}
      {showCreateModal && (
        <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && closeCreateModal()}>
          <div className="modal-container" style={{ maxWidth: '900px' }}>
            <div className="modal-header">
              <h2 className="modal-title">Create New 5G Rollout Entry</h2>
              <button className="modal-close" onClick={closeCreateModal} type="button">✕</button>
            </div>

            <form className="modal-form" onSubmit={handleCreate}>
              {error && <div className="message error-message">{error}</div>}
              {success && <div className="message success-message">{success}</div>}

              {/* Project Information */}
              <div className="form-section">
                <h3 className="section-title">Project Information</h3>
                <div className="form-grid">
                  {renderFormField('Project ID', 'project_id', createForm.project_id, (e) => onCreateChange('project_id', e.target.value), true, true)}
                  {renderFormField('Site ID', 'site_id', createForm.site_id, (e) => onCreateChange('site_id', e.target.value), true)}
                  {renderFormField('Scope', 'scope', createForm.scope, (e) => onCreateChange('scope', e.target.value))}
                  {renderFormField('Year Target Scope', 'year_target_scope', createForm.year_target_scope, (e) => onCreateChange('year_target_scope', e.target.value))}
                </div>
              </div>

              {/* Partner Information */}
              <div className="form-section">
                <h3 className="section-title">Partner Information</h3>
                <div className="form-grid">
                  {renderFormField('Partner', 'partner', createForm.partner, (e) => onCreateChange('partner', e.target.value))}
                  {renderFormField('Partner Requester Name', 'partner_requester_name', createForm.partner_requester_name, (e) => onCreateChange('partner_requester_name', e.target.value))}
                  {renderFormField('Date of Partner Request', 'date_of_partner_request', createForm.date_of_partner_request, (e) => onCreateChange('date_of_partner_request', e.target.value))}
                  {renderFormField('Survey Partner', 'survey_partner', createForm.survey_partner, (e) => onCreateChange('survey_partner', e.target.value))}
                  {renderFormField('Implementation Partner', 'implementation_partner', createForm.implementation_partner, (e) => onCreateChange('implementation_partner', e.target.value))}
                </div>
              </div>

              {/* Status Information */}
              <div className="form-section">
                <h3 className="section-title">Status Information</h3>
                <div className="form-grid">
                  {renderFormField('Request Status', 'request_status', createForm.request_status, (e) => onCreateChange('request_status', e.target.value))}
                  {renderFormField('Integration Status', 'integration_status', createForm.integration_status, (e) => onCreateChange('integration_status', e.target.value))}
                  {renderFormField('Integration Date', 'integration_date', createForm.integration_date, (e) => onCreateChange('integration_date', e.target.value))}
                  {renderFormField('PO Status', 'po_status', createForm.po_status, (e) => onCreateChange('po_status', e.target.value))}
                </div>
              </div>

              {/* PO Information */}
              <div className="form-section">
                <h3 className="section-title">PO Information</h3>
                <div className="form-grid">
                  {renderFormField('DU PO Number', 'du_po_number', createForm.du_po_number, (e) => onCreateChange('du_po_number', e.target.value))}
                  {renderFormField('DU PO Convention Name', 'du_po_convention_name', createForm.du_po_convention_name, (e) => onCreateChange('du_po_convention_name', e.target.value))}
                  {renderFormField('PO Year Issuance', 'po_year_issuance', createForm.po_year_issuance, (e) => onCreateChange('po_year_issuance', e.target.value))}
                  {renderFormField('SMP Number', 'smp_number', createForm.smp_number, (e) => onCreateChange('smp_number', e.target.value))}
                  {renderFormField('WO Number', 'wo_number', createForm.wo_number, (e) => onCreateChange('wo_number', e.target.value))}
                  {renderFormField('SPS Category', 'sps_category', createForm.sps_category, (e) => onCreateChange('sps_category', e.target.value))}
                  {renderFormField('Submission Date', 'submission_date', createForm.submission_date, (e) => onCreateChange('submission_date', e.target.value))}
                </div>
              </div>

              {/* Additional Information */}
              <div className="form-section">
                <h3 className="section-title">Additional Information</h3>
                <div className="form-grid">
                  {renderFormField('Nokia Rollout Requester', 'nokia_rollout_requester', createForm.nokia_rollout_requester, (e) => onCreateChange('nokia_rollout_requester', e.target.value))}
                  {renderFormField('PAC Received', 'pac_received', createForm.pac_received, (e) => onCreateChange('pac_received', e.target.value))}
                  {renderFormField('Date of PAC', 'date_of_pac', createForm.date_of_pac, (e) => onCreateChange('date_of_pac', e.target.value))}
                  {renderFormField('Hardware Remark', 'hardware_remark', createForm.hardware_remark, (e) => onCreateChange('hardware_remark', e.target.value))}
                </div>
              </div>

              {/* Form Actions */}
              <div className="form-actions">
                <button type="button" className="btn-cancel" onClick={closeCreateModal}>
                  Cancel
                </button>
                <button type="submit" className="btn-submit" disabled={creating}>
                  {creating ? 'Creating...' : 'Create Record'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Edit Modal */}
      {isModalOpen && (
        <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && closeModal()}>
          <div className="modal-container" style={{ maxWidth: '900px' }}>
            <div className="modal-header">
              <h2 className="modal-title">Edit 5G Rollout Entry</h2>
              <button className="modal-close" onClick={closeModal} type="button">✕</button>
            </div>

            <div className="modal-form">
              {error && <div className="message error-message">{error}</div>}
              {success && <div className="message success-message">{success}</div>}

              {/* Site & Project Information */}
              <div className="form-section">
                <h3 className="section-title">Site & Project Information</h3>
                <div className="form-grid">
                  {renderFormField('Site ID', 'site_id', editForm.site_id, (e) => onEditChange('site_id', e.target.value))}
                  {renderFormField('Scope', 'scope', editForm.scope, (e) => onEditChange('scope', e.target.value))}
                  {renderFormField('Year Target Scope', 'year_target_scope', editForm.year_target_scope, (e) => onEditChange('year_target_scope', e.target.value))}
                  <div className="form-field">
                    <label>Project</label>
                    <select
                      value={editForm.project_id || ''}
                      onChange={(e) => onEditChange('project_id', e.target.value)}
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

              {/* Partner Information */}
              <div className="form-section">
                <h3 className="section-title">Partner Information</h3>
                <div className="form-grid">
                  {renderFormField('Partner', 'partner', editForm.partner, (e) => onEditChange('partner', e.target.value))}
                  {renderFormField('Partner Requester Name', 'partner_requester_name', editForm.partner_requester_name, (e) => onEditChange('partner_requester_name', e.target.value))}
                  {renderFormField('Survey Partner', 'survey_partner', editForm.survey_partner, (e) => onEditChange('survey_partner', e.target.value))}
                  {renderFormField('Implementation Partner', 'implementation_partner', editForm.implementation_partner, (e) => onEditChange('implementation_partner', e.target.value))}
                </div>
              </div>

              {/* Status Information */}
              <div className="form-section">
                <h3 className="section-title">Status Information</h3>
                <div className="form-grid">
                  {renderFormField('Request Status', 'request_status', editForm.request_status, (e) => onEditChange('request_status', e.target.value))}
                  {renderFormField('Integration Status', 'integration_status', editForm.integration_status, (e) => onEditChange('integration_status', e.target.value))}
                  {renderFormField('Integration Date', 'integration_date', editForm.integration_date, (e) => onEditChange('integration_date', e.target.value))}
                  {renderFormField('PO Status', 'po_status', editForm.po_status, (e) => onEditChange('po_status', e.target.value))}
                </div>
              </div>

              {/* PO Information */}
              <div className="form-section">
                <h3 className="section-title">PO Information</h3>
                <div className="form-grid">
                  {renderFormField('DU PO Number', 'du_po_number', editForm.du_po_number, (e) => onEditChange('du_po_number', e.target.value))}
                  {renderFormField('DU PO Convention Name', 'du_po_convention_name', editForm.du_po_convention_name, (e) => onEditChange('du_po_convention_name', e.target.value))}
                  {renderFormField('SMP Number', 'smp_number', editForm.smp_number, (e) => onEditChange('smp_number', e.target.value))}
                  {renderFormField('WO Number', 'wo_number', editForm.wo_number, (e) => onEditChange('wo_number', e.target.value))}
                </div>
              </div>

              {/* Form Actions */}
              <div className="form-actions">
                <button type="button" className="btn-cancel" onClick={closeModal}>
                  Cancel
                </button>
                <button className="btn-submit" onClick={handleUpdate} disabled={updating}>
                  {updating ? 'Updating...' : 'Update Record'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Delete All Confirmation Modal */}
      <DeleteConfirmationModal
        show={showDeleteAllModal}
        onConfirm={confirmDeleteAllRolloutSheet}
        onCancel={cancelDeleteAllRolloutSheet}
        title="Delete All 5G Rollout Entries for Project"
        itemName={selectedProject ? getSelectedProjectName() : ''}
        warningText="Are you sure you want to delete ALL 5G rollout entries for project"
        additionalInfo="This will permanently delete all related data from the following tables:"
        affectedItems={['5G Rollout Sheet - All entries for this project']}
        confirmButtonText="Delete All Entries"
        loading={deleteAllLoading}
      />

      {/* Editable CSV Modal (same style as RAN LLD) */}
      {showBoqModal && (
        <div className="modal-overlay" style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.5)', display: 'flex', justifyContent: 'center', alignItems: 'center', zIndex: 1000 }}>
          <div style={{ background: '#fff', padding: 24, borderRadius: 8, width: '95%', height: '90%', display: 'flex', flexDirection: 'column' }}>

            {/* Modal Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16, flexShrink: 0 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                <h3 style={{ margin: 0 }}>
                  Edit BoQ Data for {currentBoq?.site_id || currentSiteId}
                </h3>

                {bulkBoqData.length > 1 && (
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <button
                      onClick={handlePreviousBoq}
                      disabled={currentBoqIndex === 0}
                      style={{
                        padding: '6px 12px',
                        borderRadius: 4,
                        border: '1px solid #ddd',
                        background: currentBoqIndex === 0 ? '#f5f5f5' : '#fff',
                        cursor: currentBoqIndex === 0 ? 'not-allowed' : 'pointer'
                      }}
                    >
                      ← Previous
                    </button>

                    <span style={{ color: '#666', fontSize: 14 }}>
                      Site {currentBoqIndex + 1} of {bulkBoqData.length}
                    </span>

                    <button
                      onClick={handleNextBoq}
                      disabled={currentBoqIndex === bulkBoqData.length - 1}
                      style={{
                        padding: '6px 12px',
                        borderRadius: 4,
                        border: '1px solid #ddd',
                        background: currentBoqIndex === bulkBoqData.length - 1 ? '#f5f5f5' : '#fff',
                        cursor: currentBoqIndex === bulkBoqData.length - 1 ? 'not-allowed' : 'pointer'
                      }}
                    >
                      Next →
                    </button>
                  </div>
                )}
              </div>

              <button onClick={closeBoqModal} style={{ fontSize: 18, cursor: 'pointer', background: 'none', border: 'none', padding: '4px 8px' }}>
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
              <button onClick={downloadCurrentAsExcel} style={{ padding: '8px 16px', borderRadius: 6, cursor: 'pointer', background: '#FF9800', color: 'white', border: 'none' }}>
                📊 Download Current as Excel
              </button>
              {bulkBoqData.length > 1 && (
                <button onClick={downloadAllAsExcel} style={{ padding: '8px 16px', borderRadius: 6, cursor: 'pointer', background: '#9C27B0', color: 'white', border: 'none' }}>
                  📊 Download All as Excel ({bulkBoqData.length} sites)
                </button>
              )}
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
                          <button onClick={() => handleDeleteRow(rowIndex + 1)} style={{ background: '#f44336', color: 'white', border: 'none', borderRadius: 4, padding: '4px 8px', cursor: 'pointer', fontSize: '12px' }} title="Remove row">
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
        title="5G Rollout Sheet Management - User Guide"
        sections={helpSections}
        closeButtonText="Got it!"
      />
    </div>
  );
}
