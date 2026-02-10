import React, { useState, useEffect, useRef } from "react";
import { apiCall, setTransient } from "../api.js";
import "../css/Inventory.css";
import '../css/shared/DownloadButton.css';
import StatsCarousel from '../Components/shared/StatsCarousel';
import FilterBar from '../Components/shared/FilterBar';
import HelpModal, { HelpList, HelpText, CodeBlock } from '../Components/shared/HelpModal';
import TitleWithInfo from '../Components/shared/InfoButton';
import Pagination from '../Components/shared/Pagination';
import DeleteConfirmationModal from '../Components/shared/DeleteConfirmationModal';
import { downloadCustomCSVTemplate } from '../utils/csvTemplateDownloader';

export default function ODBOQItems() {
  // State for sites (main table)
  const [sites, setSites] = useState([]);
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

  // State for site editing
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [editingSite, setEditingSite] = useState(null);
  const [editForm, setEditForm] = useState({});
  const [updating, setUpdating] = useState(false);

  // State for products mini-table (View Products)
  const [expandedSiteId, setExpandedSiteId] = useState(null); // Now tracks site.id (not site_id)
  const [currentSiteProducts, setCurrentSiteProducts] = useState(null);
  const [loadingProducts, setLoadingProducts] = useState(false);

  // State for product editing within expanded row
  const [showProductForm, setShowProductForm] = useState(false);
  const [editingProduct, setEditingProduct] = useState(null);
  const [productFormData, setProductFormData] = useState({
    description: '',
    line_number: '',
    code: '',
    category: '',
    total_po_qty: '',
    consumed_in_year: '',
    remaining_in_po: ''
  });

  // State for filters and projects
  const [projects, setProjects] = useState([]);
  const [selectedProject, setSelectedProject] = useState('');
  const [stats, setStats] = useState({
    total_sites: 0,
    total_products: 0,
    total_site_products: 0,
    unique_scopes: 0,
    unique_subscopes: 0,
    unique_categories: 0
  });

  // Filter options
  const [filterOptions, setFilterOptions] = useState({
    regions: [],
    scopes: [],
    subscopes: [],
    categories: [],
    projects: []
  });
  const [selectedRegion, setSelectedRegion] = useState('');
  const [selectedScope, setSelectedScope] = useState('');
  const [selectedSubscope, setSelectedSubscope] = useState('');

  // CSV upload state
  const [consumedYear, setConsumedYear] = useState(new Date().getFullYear());

  // BOQ Generation State
  const [generatingBoqId, setGeneratingBoqId] = useState(null);
  const [showBoqModal, setShowBoqModal] = useState(false);
  const [editableCsvData, setEditableCsvData] = useState([]);
  const [currentBoqSiteInfo, setCurrentBoqSiteInfo] = useState(null);

  // Multi-selection for bulk BOQ
  const [selectedSites, setSelectedSites] = useState(new Set());
  const [selectAllForBoq, setSelectAllForBoq] = useState(false);

  // Bulk BOQ data
  const [bulkGenerating, setBulkGenerating] = useState(false);
  const [bulkBoqData, setBulkBoqData] = useState([]);
  const [currentBoqIndex, setCurrentBoqIndex] = useState(0);

  const fetchAbort = useRef(null);

  // CSV Helper Functions
  const parseCSV = (csvString) => {
    if (!csvString) return [];
    const lines = csvString.split('\n');
    return lines.map(line => {
      const regex = /(".*?"|[^",]+)(?=\s*,|\s*$)/g;
      const matches = line.match(regex) || [];
      return matches.map(field => field.replace(/^"|"$/g, '').replace(/""/g, '"'));
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

  // Fetch projects
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

  // Fetch stats
  const fetchStats = async (projectId = '') => {
    try {
      const params = new URLSearchParams();
      if (projectId) params.append('project_id', projectId);

      const data = await apiCall(`/od-boq/stats?${params.toString()}`);
      setStats(data || {
        total_sites: 0,
        total_products: 0,
        total_site_products: 0,
        unique_scopes: 0,
        unique_subscopes: 0,
        unique_categories: 0
      });
    } catch (err) {
      console.error('Failed to fetch stats:', err);
    }
  };

  // Fetch filter options
  const fetchFilterOptions = async () => {
    try {
      const data = await apiCall('/od-boq/filters/options');
      setFilterOptions(data || {
        regions: [],
        scopes: [],
        subscopes: [],
        categories: [],
        projects: []
      });
    } catch (err) {
      console.error('Failed to fetch filter options:', err);
    }
  };

  // Fetch sites (main data)
  const fetchSites = async (
    page = 1,
    search = "",
    limit = rowsPerPage,
    projectId = selectedProject,
    region = selectedRegion,
    scope = selectedScope,
    subscope = selectedSubscope
  ) => {
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
      if (region) params.append('region', region);
      if (scope) params.append('scope', scope);
      if (subscope) params.append('subscope', subscope);

      const { records, total } = await apiCall(`/od-boq/sites?${params.toString()}`, {
        signal: controller.signal,
      });

      setSites(records || []);
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
    fetchFilterOptions();
    fetchSites(1, "", rowsPerPage, '', '', '', '');
    fetchStats('');
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Handle project change
  const handleProjectChange = (e) => {
    const projectId = e.target.value;
    setSelectedProject(projectId);
    setSearchTerm('');
    setCurrentPage(1);
    fetchSites(1, '', rowsPerPage, projectId, selectedRegion, selectedScope, selectedSubscope);
    fetchStats(projectId);
  };

  // Handle filter changes
  const handleRegionChange = (e) => {
    const region = e.target.value;
    setSelectedRegion(region);
    setCurrentPage(1);
    fetchSites(1, searchTerm, rowsPerPage, selectedProject, region, selectedScope, selectedSubscope);
  };

  const handleScopeChange = (e) => {
    const scope = e.target.value;
    setSelectedScope(scope);
    setCurrentPage(1);
    fetchSites(1, searchTerm, rowsPerPage, selectedProject, selectedRegion, scope, selectedSubscope);
  };

  const handleSubscopeChange = (e) => {
    const subscope = e.target.value;
    setSelectedSubscope(subscope);
    setCurrentPage(1);
    fetchSites(1, searchTerm, rowsPerPage, selectedProject, selectedRegion, selectedScope, subscope);
  };

  // Handle search
  const onSearchChange = (e) => {
    const v = e.target.value;
    setSearchTerm(v);
    fetchSites(1, v, rowsPerPage, selectedProject, selectedRegion, selectedScope, selectedSubscope);
  };

  // Handle CSV upload
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
    formData.append("consumed_year", consumedYear.toString());

    try {
      const result = await apiCall('/od-boq/upload-csv', {
        method: "POST",
        body: formData,
      });
      setTransient(setSuccess, `Upload successful! ${result.message}`);
      fetchSites(1, searchTerm, rowsPerPage, selectedProject, selectedRegion, selectedScope, selectedSubscope);
      fetchStats(selectedProject);
      fetchFilterOptions();
    } catch (err) {
      setTransient(setError, err.message);
    } finally {
      setUploading(false);
      e.target.value = "";
    }
  };

  // Handle site delete
  const handleDeleteSite = async (site) => {
    if (!window.confirm(`Are you sure you want to delete site ${site.site_id}? This will also delete all associated product quantities.`)) return;
    try {
      await apiCall(`/od-boq/sites/${site.id}`, { method: "DELETE" });
      setTransient(setSuccess, "Site deleted successfully");
      fetchSites(currentPage, searchTerm, rowsPerPage, selectedProject, selectedRegion, selectedScope, selectedSubscope);
      fetchStats(selectedProject);
    } catch (err) {
      setTransient(setError, err.message);
    }
  };

  // Handle delete all sites for project
  const handleDeleteAllSites = () => {
    if (!selectedProject) {
      setTransient(setError, 'Please select a project first.');
      return;
    }
    setShowDeleteAllModal(true);
  };

  const confirmDeleteAllSites = async () => {
    if (!selectedProject) return;

    setDeleteAllLoading(true);
    setError('');
    setSuccess('');

    try {
      const result = await apiCall(`/od-boq/sites/delete-all/${selectedProject}`, { method: 'DELETE' });
      const message = `Successfully deleted ${result.deleted_sites} sites and ${result.deleted_site_products} site-product records.`;
      setTransient(setSuccess, message);
      setShowDeleteAllModal(false);
      setSelectedProject('');
      fetchSites(1, '', rowsPerPage, '', '', '', '');
      fetchStats('');
      fetchFilterOptions();
    } catch (err) {
      setTransient(setError, err.message || 'Failed to delete sites');
      setShowDeleteAllModal(false);
    } finally {
      setDeleteAllLoading(false);
    }
  };

  const cancelDeleteAllSites = () => {
    if (!deleteAllLoading) {
      setShowDeleteAllModal(false);
    }
  };

  const getSelectedProjectName = () => {
    const project = projects.find(p => p.pid_po === selectedProject);
    return project ? `${project.project_name} (${project.pid_po})` : selectedProject;
  };

  // Handle site edit
  const openEditModal = (site) => {
    setEditingSite(site);
    const { id, site_id, ...formFields } = site; // Exclude id and site_id from form fields
    setEditForm(formFields);
    setIsEditModalOpen(true);
  };

  const closeEditModal = () => {
    setIsEditModalOpen(false);
    setEditingSite(null);
    setEditForm({});
    setError("");
    setSuccess("");
  };

  const onEditChange = (key, value) => {
    setEditForm((prev) => ({ ...prev, [key]: value }));
  };

  const handleUpdateSite = async () => {
    if (!editingSite) return;
    setUpdating(true);
    setError("");
    setSuccess("");
    try {
      await apiCall(`/od-boq/sites/${editingSite.id}`, {
        method: "PUT",
        body: JSON.stringify(editForm),
      });
      setTransient(setSuccess, "Site updated successfully!");
      closeEditModal();
      fetchSites(currentPage, searchTerm, rowsPerPage, selectedProject, selectedRegion, selectedScope, selectedSubscope);
      fetchStats(selectedProject);
    } catch (err) {
      setTransient(setError, err.message);
    } finally {
      setUpdating(false);
    }
  };

  // Handle View Products (Toggle expand/collapse)
  const toggleExpandSite = async (site) => {
    // If clicking on already expanded site, collapse it
    if (expandedSiteId === site.id) {
      setExpandedSiteId(null);
      setCurrentSiteProducts(null);
      return;
    }

    // Expand new site and load products
    setExpandedSiteId(site.id);
    setLoadingProducts(true);
    setCurrentSiteProducts(null);
    setError("");

    try {
      const data = await apiCall(`/od-boq/sites/${site.id}/with-products`);
      setCurrentSiteProducts(data);
    } catch (err) {
      setTransient(setError, `Failed to load products for site ${site.site_id}: ${err.message}`);
      setExpandedSiteId(null);
    } finally {
      setLoadingProducts(false);
    }
  };

  // Product Management Handlers
  const handleAddProduct = () => {
    setProductFormData({
      description: '',
      line_number: '',
      code: '',
      category: '',
      total_po_qty: '',
      consumed_in_year: '',
      remaining_in_po: ''
    });
    setEditingProduct(null);
    setShowProductForm(true);
  };

  const handleEditProduct = (product) => {
    setProductFormData({
      description: product.description || '',
      line_number: product.line_number || '',
      code: product.code || '',
      category: product.category || '',
      total_po_qty: product.total_po_qty || '',
      consumed_in_year: product.consumed_in_year || '',
      remaining_in_po: product.remaining_in_po || ''
    });
    setEditingProduct(product);
    setShowProductForm(true);
  };

  const handleProductFormChange = (e) => {
    const { name, value } = e.target;
    setProductFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleSaveProduct = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    const payload = {
      ...productFormData,
      total_po_qty: parseFloat(productFormData.total_po_qty) || 0,
      consumed_in_year: parseFloat(productFormData.consumed_in_year) || 0,
      remaining_in_po: parseFloat(productFormData.remaining_in_po) || 0,
      consumed_year: consumedYear
    };

    try {
      if (editingProduct) {
        await apiCall(`/od-boq/products/${editingProduct.product_id}`, {
          method: 'PUT',
          body: JSON.stringify(payload)
        });
        setTransient(setSuccess, 'Product updated successfully!');
      } else {
        await apiCall('/od-boq/products', {
          method: 'POST',
          body: JSON.stringify(payload)
        });
        setTransient(setSuccess, 'Product created successfully!');
      }
      setShowProductForm(false);
      setEditingProduct(null);
      // Refresh the current site's products if expanded
      if (expandedSiteId) {
        const data = await apiCall(`/od-boq/sites/${expandedSiteId}/with-products`);
        setCurrentSiteProducts(data);
      }
    } catch (err) {
      setTransient(setError, err.message);
    }
  };

  const handleDeleteProduct = async (product) => {
    if (!window.confirm(`Are you sure you want to delete product "${product.description}"?`)) return;

    try {
      await apiCall(`/od-boq/products/${product.product_id}`, {
        method: 'DELETE'
      });
      setTransient(setSuccess, 'Product deleted successfully!');
      // Refresh the current site's products if expanded
      if (expandedSiteId) {
        const data = await apiCall(`/od-boq/sites/${expandedSiteId}/with-products`);
        setCurrentSiteProducts(data);
      }
    } catch (err) {
      setTransient(setError, err.message);
    }
  };

  // ===========================
  // BOQ Generation Handlers
  // ===========================

  // Generate BOQ for a single site
  const handleGenerateBoq = async (site) => {
    setGeneratingBoqId(site.id);
    setError("");
    setSuccess("");
    try {
      const csvContent = await apiCall(`/od-boq/sites/${site.id}/generate-boq`);
      setEditableCsvData(parseCSV(csvContent));
      setCurrentBoqSiteInfo({ id: site.id, site_id: site.site_id, subscope: site.subscope });
      setShowBoqModal(true);
      setTransient(setSuccess, `BOQ for site ${site.site_id} generated successfully.`);
    } catch (err) {
      setTransient(setError, err.message);
    } finally {
      setGeneratingBoqId(null);
    }
  };

  // Direct Excel download for a single site
  const handleDownloadSingleExcel = async (site) => {
    setGeneratingBoqId(site.id);
    setError("");
    try {
      const token = localStorage.getItem('token');
      const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8003';
      const response = await fetch(`${API_BASE}/od-boq/sites/${site.id}/download-boq-excel`, {
        method: 'GET',
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to download');
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `BOQ_${site.site_id}_${new Date().toISOString().slice(0,10)}.xlsx`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      setTransient(setSuccess, `Excel BOQ for site ${site.site_id} downloaded.`);
    } catch (err) {
      setTransient(setError, err.message);
    } finally {
      setGeneratingBoqId(null);
    }
  };

  // Toggle site selection for bulk BOQ
  const handleSelectSiteForBoq = (siteId) => {
    const newSelected = new Set(selectedSites);
    if (newSelected.has(siteId)) {
      newSelected.delete(siteId);
    } else {
      newSelected.add(siteId);
    }
    setSelectedSites(newSelected);
    setSelectAllForBoq(newSelected.size === sites.length && sites.length > 0);
  };

  // Select/deselect all sites for BOQ
  const handleSelectAllForBoq = () => {
    if (selectAllForBoq) {
      setSelectedSites(new Set());
      setSelectAllForBoq(false);
    } else {
      const allIds = sites.map(site => site.id);
      setSelectedSites(new Set(allIds));
      setSelectAllForBoq(true);
    }
  };

  // Bulk BOQ generation
  const handleBulkGenerateBoq = async () => {
    if (selectedSites.size === 0) {
      setTransient(setError, 'Please select at least one site.');
      return;
    }

    setBulkGenerating(true);
    setError("");

    try {
      const siteRecordIds = Array.from(selectedSites);
      const response = await apiCall('/od-boq/sites/bulk-generate-boq', {
        method: 'POST',
        body: JSON.stringify({ site_record_ids: siteRecordIds })
      });

      const successfulBoqs = response.results
        .filter(r => r.success)
        .map(r => ({
          site_record_id: r.site_record_id,
          site_id: r.site_id,
          subscope: r.subscope,
          csvData: parseCSV(r.csv_content)
        }));

      if (successfulBoqs.length === 0) {
        setTransient(setError, 'Failed to generate BOQs for all selected sites.');
        return;
      }

      setBulkBoqData(successfulBoqs);
      setCurrentBoqIndex(0);
      setShowBoqModal(true);
      setTransient(setSuccess, `Generated ${successfulBoqs.length} BOQs successfully.`);
    } catch (err) {
      setTransient(setError, err.message);
    } finally {
      setBulkGenerating(false);
    }
  };

  // Bulk Excel download - all sites in single Excel file ordered by BPO Line No
  const handleBulkDownloadExcel = async () => {
    if (selectedSites.size === 0) {
      setTransient(setError, 'Please select at least one site.');
      return;
    }

    setBulkGenerating(true);
    setError("");

    try {
      const token = localStorage.getItem('token');
      const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8003';
      const siteRecordIds = Array.from(selectedSites);

      const response = await fetch(`${API_BASE}/od-boq/sites/bulk-download-boq-zip`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ site_record_ids: siteRecordIds })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to download');
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `BOQ_Bulk_${siteRecordIds.length}_sites_${new Date().toISOString().slice(0,10)}.xlsx`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      setTransient(setSuccess, `Downloaded BOQ for ${siteRecordIds.length} sites in single Excel.`);
    } catch (err) {
      setTransient(setError, err.message);
    } finally {
      setBulkGenerating(false);
    }
  };

  // CSV Modal Handlers
  const handleCellChange = (rowIndex, cellIndex, value) => {
    if (bulkBoqData.length > 0) {
      const updatedBulkData = [...bulkBoqData];
      updatedBulkData[currentBoqIndex].csvData[rowIndex][cellIndex] = value;
      setBulkBoqData(updatedBulkData);
    } else {
      const updatedData = [...editableCsvData];
      updatedData[rowIndex][cellIndex] = value;
      setEditableCsvData(updatedData);
    }
  };

  const handleAddBoqRow = () => {
    const currentData = bulkBoqData.length > 0
      ? bulkBoqData[currentBoqIndex].csvData
      : editableCsvData;
    const numColumns = currentData[0]?.length || 1;
    const newRow = Array(numColumns).fill('');

    if (bulkBoqData.length > 0) {
      const updatedBulkData = [...bulkBoqData];
      updatedBulkData[currentBoqIndex].csvData = [...currentData, newRow];
      setBulkBoqData(updatedBulkData);
    } else {
      setEditableCsvData([...editableCsvData, newRow]);
    }
  };

  const handleDeleteBoqRow = (rowIndex) => {
    if (rowIndex < 6) return; // Don't delete header rows (first 6 rows are metadata/headers)

    if (bulkBoqData.length > 0) {
      const updatedBulkData = [...bulkBoqData];
      updatedBulkData[currentBoqIndex].csvData =
        updatedBulkData[currentBoqIndex].csvData.filter((_, i) => i !== rowIndex);
      setBulkBoqData(updatedBulkData);
    } else {
      setEditableCsvData(editableCsvData.filter((_, i) => i !== rowIndex));
    }
  };

  const downloadBoqCSV = () => {
    const currentData = bulkBoqData.length > 0
      ? bulkBoqData[currentBoqIndex].csvData
      : editableCsvData;
    const siteId = bulkBoqData.length > 0
      ? bulkBoqData[currentBoqIndex].site_id
      : currentBoqSiteInfo?.site_id;

    const csvContent = stringifyCSV(currentData);
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `BOQ_${siteId || 'export'}_${new Date().toISOString().slice(0,10)}.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const downloadCurrentBoqAsExcel = async () => {
    const currentData = bulkBoqData.length > 0
      ? bulkBoqData[currentBoqIndex]
      : { csvData: editableCsvData, site_id: currentBoqSiteInfo?.site_id, site_record_id: currentBoqSiteInfo?.id };

    try {
      const token = localStorage.getItem('token');
      const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8003';
      const response = await fetch(`${API_BASE}/od-boq/download-boq-excel-from-csv`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          site_record_id: currentData.site_record_id,
          site_id: currentData.site_id,
          csv_data: currentData.csvData
        })
      });

      if (!response.ok) throw new Error('Failed to download Excel');

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `BOQ_${currentData.site_id}_${new Date().toISOString().slice(0,10)}.xlsx`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (err) {
      setTransient(setError, err.message);
    }
  };

  const closeBoqModal = () => {
    setShowBoqModal(false);
    setEditableCsvData([]);
    setCurrentBoqSiteInfo(null);
    setBulkBoqData([]);
    setCurrentBoqIndex(0);
    setSelectedSites(new Set());
    setSelectAllForBoq(false);
  };

  // Download all edited data as single Excel (uses bulkBoqData from modal)
  const handleDownloadAllEditedAsExcel = async () => {
    if (bulkBoqData.length === 0) {
      setTransient(setError, 'No bulk data available.');
      return;
    }

    setBulkGenerating(true);
    setError("");

    try {
      const token = localStorage.getItem('token');
      const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8003';

      // Prepare the edited data for the backend
      const sitesData = bulkBoqData.map(item => ({
        site_record_id: item.site_record_id,
        site_id: item.site_id,
        subscope: item.subscope || null,
        smp: item.smp || null,
        csv_data: item.csvData
      }));

      const response = await fetch(`${API_BASE}/od-boq/sites/bulk-download-boq-excel-from-edited`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ sites_data: sitesData })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to download');
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `BOQ_Bulk_${bulkBoqData.length}_sites_${new Date().toISOString().slice(0,10)}.xlsx`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      setTransient(setSuccess, `Downloaded edited BOQ for ${bulkBoqData.length} sites.`);
    } catch (err) {
      setTransient(setError, err.message);
    } finally {
      setBulkGenerating(false);
    }
  };

  // Pagination
  const totalPages = Math.ceil(total / rowsPerPage);

  const handleRowsPerPageChange = (e) => {
    const newLimit = parseInt(e.target.value);
    setRowsPerPage(newLimit);
    setCurrentPage(1);
    fetchSites(1, searchTerm, newLimit, selectedProject, selectedRegion, selectedScope, selectedSubscope);
  };

  // Define stat cards
  const statCards = [
    { label: 'Total Sites', value: stats.total_sites || total },
    { label: 'Total Products', value: stats.total_products || 0 },
    { label: 'Scopes', value: stats.unique_scopes || 0 },
    { label: 'Subscopes', value: stats.unique_subscopes || 0 },
    { label: 'Current Page', value: `${currentPage} / ${totalPages || 1}` },
    { label: 'Showing', value: `${sites.length} sites` },
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

  // Help modal sections
  const helpSections = [
    {
      icon: '📋',
      title: 'Overview',
      content: (
        <HelpText>
          The OD BOQ Management component uses a 3-table structure: Sites (parent), Products (master catalog),
          and Site-Product (junction with quantities). Upload CSVs to populate all tables automatically.
        </HelpText>
      )
    },
    {
      icon: '✨',
      title: 'Features & Buttons',
      content: (
        <HelpList
          items={[
            { label: 'View Products', text: 'Expands the row to show a mini-table with all products and quantities for that site.' },
            { label: 'Hide Products', text: 'Collapses the expanded products mini-table.' },
            { label: 'Edit', text: 'Modify site information (region, scope, etc.).' },
            { label: 'Delete', text: 'Remove a site and all its product quantities.' },
            { label: '📤 Upload CSV', text: 'Bulk upload BOQ data from a CSV file with multi-header structure.' },
            { label: '🗑️ Delete All', text: 'Deletes ALL sites and related data for the selected project.' },
            { label: 'Search', text: 'Filter sites by Site ID, Region, Scope, Subscope.' },
            { label: 'Filters', text: 'Use dropdowns to filter by Project, Region, Scope, or Subscope.' },
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
            Your CSV file must follow this structure:
          </HelpText>
          <CodeBlock
            items={[
              'Row 1: Product descriptions (starting column H)',
              'Row 2: Line numbers',
              'Row 3: Product codes',
              'Row 4: Categories (Hardware/SW/Service)',
              'Row 5: Total PO QTY',
              'Row 6: Consumed in [Year]',
              'Row 7: Column headers (Region, Distance, Scope, Subscope, Site ID, PO Model, Remaining in PO)',
              'Row 8+: Site data rows with quantities'
            ]}
          />
          <HelpText isNote>
            <strong>Note:</strong> Select a project and set the consumed year before uploading.
            The system automatically creates products from column headers and populates all site-product quantities.
          </HelpText>
          <div style={{ marginTop: '1rem', textAlign: 'center' }}>
            <button
              className="btn-secondary"
              onClick={() => {
                const headers = [
                  'Region', 'Distance', 'Scope', 'Subscope', 'Site ID', 'PO Model', 'Remaining in PO',
                  'Product 1', 'Product 2', 'Product 3', 'Product 4', 'Product 5'
                ];
                const sampleRows = [
                  ['Description:', '', '', '', '', '', '', 'ODU - External', 'IDU - Indoor', 'Cable - 10m', 'Antenna 0.6m', 'Mounting Kit'],
                  ['Line Number:', '', '', '', '', '', '', 'LINE-001', 'LINE-002', 'LINE-003', 'LINE-004', 'LINE-005'],
                  ['Code:', '', '', '', '', '', '', 'ODU-EXT-001', 'IDU-IN-001', 'CBL-10M-001', 'ANT-06M-001', 'MNT-KIT-001'],
                  ['Category:', '', '', '', '', '', '', 'Hardware', 'Hardware', 'Hardware', 'Hardware', 'Hardware'],
                  ['Total PO QTY:', '', '', '', '', '', '', '100', '100', '200', '50', '50'],
                  [`Consumed in ${consumedYear}:`, '', '', '', '', '', '', '20', '20', '40', '10', '10'],
                  ['', '', '', '', '', '', '', '', '', '', '', ''],
                  ['North', '5km', 'New', 'Installation', 'SITE001', 'Model A', '80', '2', '2', '4', '1', '1'],
                  ['South', '10km', 'Upgrade', 'Enhancement', 'SITE002', 'Model B', '75', '3', '3', '6', '2', '2']
                ];
                downloadCustomCSVTemplate(headers, 'od_boq_template', sampleRows);
              }}
              style={{ padding: '0.75rem 1.5rem' }}
            >
              📥 Download CSV Template
            </button>
          </div>
        </>
      )
    },
    {
      icon: '🏗️',
      title: 'Database Structure',
      content: (
        <HelpList
          items={[
            'OD_BOQ_Site: Stores site information (Site ID, Region, Distance, Scope, Subscope, PO Model)',
            'OD_BOQ_Product: Master product catalog (Description, Line#, Code, Category, Total PO QTY, etc.)',
            'OD_BOQ_Site_Product: Junction table with quantities for each site-product combination',
          ]}
        />
      )
    }
  ];

  // Form field renderer helper
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
          title="OD BOQ Site Management"
          subtitle="Manage Outdoor Bill of Quantities - 3-Table Structure"
          onInfoClick={() => setShowHelpModal(true)}
          infoTooltip="How to use this component"
        />
        <div className="header-actions">
          <div className="form-field" style={{ marginRight: '1rem', minWidth: '120px' }}>
            <label style={{ fontSize: '0.85rem', marginBottom: '0.25rem' }}>Consumed Year</label>
            <input
              type="number"
              value={consumedYear}
              onChange={(e) => setConsumedYear(parseInt(e.target.value))}
              min="2020"
              max="2099"
              style={{ width: '100%', padding: '0.5rem' }}
            />
          </div>
          {/* BOQ Generation Buttons */}
          <button
            className={`btn-primary ${selectedSites.size === 0 || bulkGenerating ? 'disabled' : ''}`}
            onClick={handleBulkGenerateBoq}
            disabled={selectedSites.size === 0 || bulkGenerating}
            title={selectedSites.size === 0 ? "Select sites first" : `Generate BOQ CSV for ${selectedSites.size} sites`}
          >
            <span className="btn-icon">{bulkGenerating ? '...' : '📋'}</span>
            {bulkGenerating ? 'Processing...' : `Bulk CSV (${selectedSites.size})`}
          </button>
          <button
            className={`btn-primary ${selectedSites.size === 0 || bulkGenerating ? 'disabled' : ''}`}
            onClick={handleBulkDownloadExcel}
            disabled={selectedSites.size === 0 || bulkGenerating}
            title={selectedSites.size === 0 ? "Select sites first" : `Download BOQ Excel for ${selectedSites.size} sites`}
          >
            <span className="btn-icon">{bulkGenerating ? '...' : '📊'}</span>
            {bulkGenerating ? 'Processing...' : `Bulk Excel (${selectedSites.size})`}
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
            onClick={handleDeleteAllSites}
            disabled={!selectedProject}
            title={!selectedProject ? "Select a project first" : "Delete all sites for this project"}
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
        searchPlaceholder="Search by Site ID, Region, Scope, Subscope..."
        dropdowns={[
          {
            label: 'Project',
            value: selectedProject,
            onChange: handleProjectChange,
            placeholder: '-- All Projects --',
            options: projects.map(p => ({
              value: p.pid_po,
              label: `${p.project_name} (${p.pid_po})`
            }))
          },
          {
            label: 'Region',
            value: selectedRegion,
            onChange: handleRegionChange,
            placeholder: '-- All Regions --',
            options: filterOptions.regions.map(r => ({ value: r, label: r }))
          },
          {
            label: 'Scope',
            value: selectedScope,
            onChange: handleScopeChange,
            placeholder: '-- All Scopes --',
            options: filterOptions.scopes.map(s => ({ value: s, label: s }))
          },
          {
            label: 'Subscope',
            value: selectedSubscope,
            onChange: handleSubscopeChange,
            placeholder: '-- All Subscopes --',
            options: filterOptions.subscopes.map(s => ({ value: s, label: s }))
          }
        ]}
        showClearButton={!!searchTerm || !!selectedRegion || !!selectedScope || !!selectedSubscope}
        onClearSearch={() => {
          setSearchTerm('');
          setSelectedRegion('');
          setSelectedScope('');
          setSelectedSubscope('');
          fetchSites(1, '', rowsPerPage, selectedProject, '', '', '');
        }}
        clearButtonText="Clear Filters"
      />

      {/* Messages */}
      {error && <div className="message error-message">{error}</div>}
      {success && <div className="message success-message">{success}</div>}
      {loading && <div className="loading-indicator">Loading Sites...</div>}

      {/* Stats Bar */}
      <StatsCarousel cards={statCards} visibleCount={4} />

      {/* Table Section with Expandable Rows */}
      <div className="project-table-container">
        <table className="project-table">
          <thead>
            <tr>
              <th style={{ width: '40px' }}>
                <input
                  type="checkbox"
                  checked={selectAllForBoq}
                  onChange={handleSelectAllForBoq}
                  title="Select all for BOQ generation"
                />
              </th>
              <th style={{ width: '40px' }}></th>
              <th>Site ID</th>
              <th>Region</th>
              <th>Distance</th>
              <th>Scope</th>
              <th>Subscope</th>
              <th>PO Model</th>
              <th>Project</th>
              <th style={{ width: '140px' }}>BOQ Actions</th>
              <th style={{ width: '100px' }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr>
                <td colSpan="11" style={{ textAlign: 'center', padding: '2rem' }}>
                  Loading sites...
                </td>
              </tr>
            )}
            {!loading && sites.length === 0 && (
              <tr>
                <td colSpan="11" style={{ textAlign: 'center', padding: '2rem' }}>
                  No sites found
                </td>
              </tr>
            )}
            {!loading && sites.map((site) => (
              <React.Fragment key={site.id}>
                {/* Main Site Row */}
                <tr className="parent-row">
                  <td>
                    <input
                      type="checkbox"
                      checked={selectedSites.has(site.id)}
                      onChange={() => handleSelectSiteForBoq(site.id)}
                      title="Select for BOQ generation"
                    />
                  </td>
                  <td>
                    <button
                      onClick={() => toggleExpandSite(site)}
                      className="expand-btn"
                      title="Expand/Collapse products"
                    >
                      {expandedSiteId === site.id ? '▼' : '▶'}
                    </button>
                  </td>
                  <td>{site.site_id}</td>
                  <td>{site.region || 'N/A'}</td>
                  <td>{site.distance || 'N/A'}</td>
                  <td>{site.scope || 'N/A'}</td>
                  <td>{site.subscope || 'N/A'}</td>
                  <td>{site.po_model || 'N/A'}</td>
                  <td>{site.project_id || 'N/A'}</td>
                  <td style={{ textAlign: 'center' }}>
                    <div className="action-buttons">
                      <button
                        className="btn-action btn-generate"
                        onClick={() => handleGenerateBoq(site)}
                        disabled={generatingBoqId === site.id}
                        title="Generate BOQ (CSV editor)"
                        style={{ background: '#2196F3', color: 'white' }}
                      >
                        {generatingBoqId === site.id ? '...' : '📋'}
                      </button>
                      <button
                        className="btn-action btn-generate"
                        onClick={() => handleDownloadSingleExcel(site)}
                        disabled={generatingBoqId === site.id}
                        title="Download BOQ as Excel"
                        style={{ background: '#4CAF50', color: 'white' }}
                      >
                        {generatingBoqId === site.id ? '...' : '📊'}
                      </button>
                    </div>
                  </td>
                  <td style={{ textAlign: 'center' }}>
                    <div className="action-buttons">
                      <button
                        className="btn-action btn-edit"
                        onClick={() => openEditModal(site)}
                        title="Edit"
                      >
                        ✏️
                      </button>
                      <button
                        className="btn-action btn-delete"
                        onClick={() => handleDeleteSite(site)}
                        title="Delete"
                      >
                        🗑️
                      </button>
                    </div>
                  </td>
                </tr>

                {/* Expandable Products Mini-Table */}
                {expandedSiteId === site.id && (
                  <tr className="expanded-row">
                    <td colSpan="11">
                      <div className="nested-items-container">
                        <div className="nested-items-header">
                          <h4 className="nested-items-title">Products for {site.site_id}</h4>
                          <div className="nested-items-actions">
                            <button
                              className="btn-secondary"
                              onClick={handleAddProduct}
                            >
                              <span className="btn-icon">+</span>
                              Add Product
                            </button>
                          </div>
                        </div>
                        {loadingProducts && (
                          <div style={{ textAlign: 'center', padding: '1rem' }}>
                            Loading products...
                          </div>
                        )}
                        {!loadingProducts && currentSiteProducts && (
                          <div className="nested-table-wrapper">
                            {currentSiteProducts.products && currentSiteProducts.products.length > 0 ? (
                              <>
                                <table className="nested-table">
                                  <thead>
                                    <tr>
                                      <th>Description</th>
                                      <th>Line #</th>
                                      <th>Code</th>
                                      <th>Category</th>
                                      <th>Total PO QTY</th>
                                      <th>Consumed</th>
                                      <th>Remaining</th>
                                      <th>Qty for Site</th>
                                      <th>Actions</th>
                                    </tr>
                                  </thead>
                                  <tbody>
                                    {currentSiteProducts.products.map((product, idx) => (
                                      <tr key={`${site.id}-product-${idx}`}>
                                        <td title={product.description}>{product.description || 'N/A'}</td>
                                        <td title={product.line_number}>{product.line_number || 'N/A'}</td>
                                        <td title={product.code}>{product.code || 'N/A'}</td>
                                        <td title={product.category}>{product.category || 'N/A'}</td>
                                        <td title={product.total_po_qty}>{product.total_po_qty != null ? product.total_po_qty : 'N/A'}</td>
                                        <td title={product.consumed_in_year}>{product.consumed_in_year != null ? product.consumed_in_year : 'N/A'}</td>
                                        <td title={product.remaining_in_po}>{product.remaining_in_po != null ? product.remaining_in_po : 'N/A'}</td>
                                        <td title={product.qty_per_site}>{product.qty_per_site != null ? product.qty_per_site : 'N/A'}</td>
                                        <td>
                                          <div className="action-buttons">
                                            <button
                                              className="btn-action btn-edit"
                                              onClick={() => handleEditProduct(product)}
                                              title="Edit"
                                            >
                                              ✏️
                                            </button>
                                            <button
                                              className="btn-action btn-delete"
                                              onClick={() => handleDeleteProduct(product)}
                                              title="Delete"
                                            >
                                              🗑️
                                            </button>
                                          </div>
                                        </td>
                                      </tr>
                                    ))}
                                  </tbody>
                                </table>
                                {currentSiteProducts.total_qty_sum != null && (
                                  <div style={{
                                    marginTop: '1rem',
                                    padding: '0.75rem',
                                    background: '#f0f8ff',
                                    border: '1px solid #d0e8f2',
                                    borderRadius: '4px',
                                    fontWeight: 'bold',
                                    textAlign: 'right'
                                  }}>
                                    Total Quantity Sum for {site.site_id}: {currentSiteProducts.total_qty_sum.toFixed(2)}
                                  </div>
                                )}
                              </>
                            ) : (
                              <div className="no-data" style={{ textAlign: 'center', padding: '1rem', color: '#666' }}>
                                No products found for this site
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    </td>
                  </tr>
                )}
              </React.Fragment>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      <Pagination
        currentPage={currentPage}
        totalPages={totalPages}
        onPageChange={(page) => fetchSites(page, searchTerm, rowsPerPage, selectedProject, selectedRegion, selectedScope, selectedSubscope)}
        previousText="← Previous"
        nextText="Next →"
      />

      {/* Edit Site Modal */}
      {isEditModalOpen && (
        <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && closeEditModal()}>
          <div className="modal-container" style={{ maxWidth: '600px' }}>
            <div className="modal-header">
              <h2 className="modal-title">Edit Site: {editingSite?.site_id}</h2>
              <button className="modal-close" onClick={closeEditModal} type="button">✕</button>
            </div>

            <div className="modal-form">
              {error && <div className="message error-message">{error}</div>}
              {success && <div className="message success-message">{success}</div>}

              <div className="form-section">
                <h3 className="section-title">Site Information</h3>
                <div className="form-grid">
                  {renderFormField('Region', 'region', editForm.region, (e) => onEditChange('region', e.target.value))}
                  {renderFormField('Distance', 'distance', editForm.distance, (e) => onEditChange('distance', e.target.value))}
                  {renderFormField('Scope', 'scope', editForm.scope, (e) => onEditChange('scope', e.target.value))}
                  {renderFormField('Subscope', 'subscope', editForm.subscope, (e) => onEditChange('subscope', e.target.value))}
                  {renderFormField('PO Model', 'po_model', editForm.po_model, (e) => onEditChange('po_model', e.target.value))}
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

              <div className="form-section">
                <h3 className="section-title">Additional Site Metadata</h3>
                <div className="form-grid">
                  {renderFormField('AC ARMOD Cable', 'ac_armod_cable', editForm.ac_armod_cable, (e) => onEditChange('ac_armod_cable', e.target.value))}
                  {renderFormField('Additional Cost', 'additional_cost', editForm.additional_cost, (e) => onEditChange('additional_cost', e.target.value))}
                  {renderFormField('Partner', 'partner', editForm.partner, (e) => onEditChange('partner', e.target.value))}
                  {renderFormField('Request Status', 'request_status', editForm.request_status, (e) => onEditChange('request_status', e.target.value))}
                  {renderFormField('Requested Date', 'requested_date', editForm.requested_date, (e) => onEditChange('requested_date', e.target.value))}
                  {renderFormField('DU PO Number', 'du_po_number', editForm.du_po_number, (e) => onEditChange('du_po_number', e.target.value))}
                  {renderFormField('SMP', 'smp', editForm.smp, (e) => onEditChange('smp', e.target.value))}
                  {renderFormField('Year Scope', 'year_scope', editForm.year_scope, (e) => onEditChange('year_scope', e.target.value))}
                  {renderFormField('Integration Status', 'integration_status', editForm.integration_status, (e) => onEditChange('integration_status', e.target.value))}
                  {renderFormField('Integration Date', 'integration_date', editForm.integration_date, (e) => onEditChange('integration_date', e.target.value))}
                  {renderFormField('DU PO Convention Name', 'du_po_convention_name', editForm.du_po_convention_name, (e) => onEditChange('du_po_convention_name', e.target.value))}
                  {renderFormField('PO Year Issuance', 'po_year_issuance', editForm.po_year_issuance, (e) => onEditChange('po_year_issuance', e.target.value))}
                  <div className="form-field full-width">
                    <label>Remark</label>
                    <textarea
                      name="remark"
                      value={editForm.remark != null ? editForm.remark : ''}
                      onChange={(e) => onEditChange('remark', e.target.value)}
                      rows="3"
                      style={{ width: '100%', padding: '0.5rem', fontFamily: 'inherit' }}
                    />
                  </div>
                </div>
              </div>

              <div className="form-actions">
                <button type="button" className="btn-cancel" onClick={closeEditModal}>
                  Cancel
                </button>
                <button className="btn-submit" onClick={handleUpdateSite} disabled={updating}>
                  {updating ? 'Updating...' : 'Update Site'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Delete All Confirmation Modal */}
      <DeleteConfirmationModal
        show={showDeleteAllModal}
        onConfirm={confirmDeleteAllSites}
        onCancel={cancelDeleteAllSites}
        title="Delete All Sites for Project"
        itemName={selectedProject ? getSelectedProjectName() : ''}
        warningText="Are you sure you want to delete ALL sites for project"
        additionalInfo="This will permanently delete all related data from the following tables:"
        affectedItems={[
          'OD BOQ Sites - All sites for this project',
          'OD BOQ Site-Product Records - All quantity records for these sites'
        ]}
        confirmButtonText="Delete All Sites"
        loading={deleteAllLoading}
      />

      {/* Product Add/Edit Modal */}
      {showProductForm && (
        <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && setShowProductForm(false)}>
          <div className="modal-container" style={{ maxWidth: '700px' }}>
            <div className="modal-header">
              <h2 className="modal-title">{editingProduct ? `Edit Product: ${editingProduct.description}` : 'Create New Product'}</h2>
              <button className="modal-close" onClick={() => setShowProductForm(false)} type="button">✕</button>
            </div>

            <form className="modal-form" onSubmit={handleSaveProduct}>
              <div className="form-section">
                <h3 className="section-title">Product Information</h3>
                <div className="form-grid">
                  <div className="form-field full-width">
                    <label>Description *</label>
                    <input
                      type="text"
                      name="description"
                      value={productFormData.description}
                      onChange={handleProductFormChange}
                      required
                    />
                  </div>
                  <div className="form-field">
                    <label>Line Number</label>
                    <input
                      type="text"
                      name="line_number"
                      value={productFormData.line_number}
                      onChange={handleProductFormChange}
                    />
                  </div>
                  <div className="form-field">
                    <label>Code</label>
                    <input
                      type="text"
                      name="code"
                      value={productFormData.code}
                      onChange={handleProductFormChange}
                    />
                  </div>
                  <div className="form-field">
                    <label>Category</label>
                    <input
                      type="text"
                      name="category"
                      value={productFormData.category}
                      onChange={handleProductFormChange}
                    />
                  </div>
                  <div className="form-field">
                    <label>Total PO QTY *</label>
                    <input
                      type="number"
                      name="total_po_qty"
                      value={productFormData.total_po_qty}
                      onChange={handleProductFormChange}
                      step="0.01"
                      required
                    />
                  </div>
                  <div className="form-field">
                    <label>Consumed in {consumedYear}</label>
                    <input
                      type="number"
                      name="consumed_in_year"
                      value={productFormData.consumed_in_year}
                      onChange={handleProductFormChange}
                      step="0.01"
                    />
                  </div>
                  <div className="form-field">
                    <label>Remaining in PO</label>
                    <input
                      type="number"
                      name="remaining_in_po"
                      value={productFormData.remaining_in_po}
                      onChange={handleProductFormChange}
                      step="0.01"
                    />
                  </div>
                </div>
              </div>

              <div className="form-actions">
                <button type="button" className="btn-cancel" onClick={() => setShowProductForm(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn-submit">
                  {editingProduct ? 'Update Product' : 'Create Product'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* BOQ Generation Modal - Editable CSV */}
      {showBoqModal && (
        <div className="modal-overlay" style={{
          position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
          background: 'rgba(0,0,0,0.5)', display: 'flex',
          justifyContent: 'center', alignItems: 'center', zIndex: 1000
        }}>
          <div style={{
            background: '#fff', padding: 24, borderRadius: 8,
            width: '95%', height: '90%', display: 'flex', flexDirection: 'column'
          }}>
            {/* Modal Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                <h3 style={{ margin: 0 }}>
                  Edit BOQ Data for {bulkBoqData.length > 0
                    ? bulkBoqData[currentBoqIndex].site_id
                    : currentBoqSiteInfo?.site_id}
                  {bulkBoqData.length > 0 && bulkBoqData[currentBoqIndex].subscope &&
                    ` (${bulkBoqData[currentBoqIndex].subscope})`}
                </h3>

                {bulkBoqData.length > 1 && (
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <button
                      onClick={() => setCurrentBoqIndex(prev => Math.max(0, prev - 1))}
                      disabled={currentBoqIndex === 0}
                      style={{ padding: '6px 12px', borderRadius: 4, border: '1px solid #ddd', cursor: currentBoqIndex === 0 ? 'not-allowed' : 'pointer' }}
                    >
                      Previous
                    </button>
                    <span style={{ fontWeight: 'bold' }}>Site {currentBoqIndex + 1} of {bulkBoqData.length}</span>
                    <button
                      onClick={() => setCurrentBoqIndex(prev => Math.min(bulkBoqData.length - 1, prev + 1))}
                      disabled={currentBoqIndex === bulkBoqData.length - 1}
                      style={{ padding: '6px 12px', borderRadius: 4, border: '1px solid #ddd', cursor: currentBoqIndex === bulkBoqData.length - 1 ? 'not-allowed' : 'pointer' }}
                    >
                      Next
                    </button>
                  </div>
                )}
              </div>

              <button onClick={closeBoqModal} style={{ fontSize: 24, cursor: 'pointer', background: 'none', border: 'none', fontWeight: 'bold' }}>
                ×
              </button>
            </div>

            {/* Action Buttons */}
            <div style={{ display: 'flex', gap: 12, marginBottom: 16 }}>
              <button onClick={handleAddBoqRow} style={{ padding: '8px 16px', background: '#4CAF50', color: 'white', border: 'none', borderRadius: 6, cursor: 'pointer' }}>
                + Add Row
              </button>
              <button onClick={downloadBoqCSV} style={{ padding: '8px 16px', background: '#2196F3', color: 'white', border: 'none', borderRadius: 6, cursor: 'pointer' }}>
                Download CSV
              </button>
              <button onClick={downloadCurrentBoqAsExcel} style={{ padding: '8px 16px', background: '#FF9800', color: 'white', border: 'none', borderRadius: 6, cursor: 'pointer' }}>
                Download as Excel
              </button>
              {bulkBoqData.length > 1 && (
                <button onClick={handleDownloadAllEditedAsExcel} style={{ padding: '8px 16px', background: '#9C27B0', color: 'white', border: 'none', borderRadius: 6, cursor: 'pointer' }}>
                  Download All ({bulkBoqData.length} sites in Excel)
                </button>
              )}
            </div>

            {/* Editable Table */}
            <div style={{ flex: 1, overflow: 'auto', border: '1px solid #ddd', borderRadius: 6 }}>
              <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: '800px' }}>
                <tbody>
                  {(bulkBoqData.length > 0
                    ? bulkBoqData[currentBoqIndex].csvData
                    : editableCsvData
                  ).map((row, rowIndex) => (
                      <tr key={rowIndex} style={{ background: rowIndex < 6 ? '#f5f5f5' : 'white' }}>
                        <td style={{ padding: '4px 8px', border: '1px solid #ddd', width: 80, textAlign: 'center' }}>
                          {rowIndex >= 6 ? (
                            <button
                              onClick={() => handleDeleteBoqRow(rowIndex)}
                              style={{ background: '#f44336', color: 'white', border: 'none', borderRadius: 4, padding: '4px 8px', cursor: 'pointer' }}
                            >
                              Delete
                            </button>
                          ) : (
                            <span style={{ color: '#999', fontSize: '0.8rem' }}>Header</span>
                          )}
                        </td>
                        {row.map((cell, cellIndex) => (
                          <td key={cellIndex} style={{ padding: '2px', border: '1px solid #ddd', minWidth: 100 }}>
                            <input
                              type="text"
                              value={cell}
                              onChange={(e) => handleCellChange(rowIndex, cellIndex, e.target.value)}
                              style={{
                                width: '100%', border: 'none', padding: '6px',
                                background: rowIndex < 6 ? '#f5f5f5' : 'transparent',
                                fontWeight: rowIndex === 5 ? 'bold' : 'normal'
                              }}
                            />
                          </td>
                        ))}
                      </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Footer info */}
            <div style={{ marginTop: 12, color: '#666', fontSize: '0.9rem' }}>
              Rows 1-5 are metadata headers. Row 6 contains column headers. Data rows start from row 7.
            </div>
          </div>
        </div>
      )}

      {/* Help/Info Modal */}
      <HelpModal
        show={showHelpModal}
        onClose={() => setShowHelpModal(false)}
        title="OD BOQ Site Management - User Guide"
        sections={helpSections}
        closeButtonText="Got it!"
      />
    </div>
  );
}
