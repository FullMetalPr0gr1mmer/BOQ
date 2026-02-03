import React, { useState, useEffect, useRef, useMemo } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { apiCall, setTransient } from "../api.js";
import "../css/Inventory.css";
import "../css/DURPALogistics.css";
import '../css/shared/DownloadButton.css';
import StatsCarousel from '../Components/shared/StatsCarousel';
import FilterBar from '../Components/shared/FilterBar';
import HelpModal, { HelpList, HelpText } from '../Components/shared/HelpModal';
import TitleWithInfo from '../Components/shared/InfoButton';
import Pagination from '../Components/shared/Pagination';
import DeleteConfirmationModal from '../Components/shared/DeleteConfirmationModal';

export default function DURPALogistics() {
  const location = useLocation();
  const navigate = useNavigate();

  // Determine active view from URL path
  const activeView = location.pathname.includes('/invoices') ? 'invoices' : 'projects';

  // Project state
  const [projects, setProjects] = useState([]);
  const [projectsLoading, setProjectsLoading] = useState(false);
  const [projectsTotal, setProjectsTotal] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const rowsPerPage = 50;

  // Expanded row state
  const [expandedProjectId, setExpandedProjectId] = useState(null);
  const [descriptions, setDescriptions] = useState([]);
  const [descriptionsLoading, setDescriptionsLoading] = useState(false);

  // UI state
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [searchTerm, setSearchTerm] = useState("");
  const [showHelpModal, setShowHelpModal] = useState(false);
  const [uploading, setUploading] = useState(false);

  // Invoices state
  const [invoices, setInvoices] = useState([]);
  const [invoicesLoading, setInvoicesLoading] = useState(false);
  const [invoicesTotal, setInvoicesTotal] = useState(0);
  const [invoicesPage, setInvoicesPage] = useState(1);
  const [expandedInvoiceId, setExpandedInvoiceId] = useState(null);
  const [invoicePoFilter, setInvoicePoFilter] = useState(''); // Filter by PO#
  const [editingCustomerInvoice, setEditingCustomerInvoice] = useState(null); // For inline editing

  // Modal state
  const [showProjectModal, setShowProjectModal] = useState(false);
  const [showDescModal, setShowDescModal] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [deleteLoading, setDeleteLoading] = useState(false);

  // Form state
  const [projectForm, setProjectForm] = useState({ po_number: '' });
  const [descForm, setDescForm] = useState({
    description: '',
    po_line_item: '',
    po_qty_as_per_po: '',
    po_qty_per_unit: '',
    price_per_unit: ''
  });
  const [currentProjectForDesc, setCurrentProjectForDesc] = useState(null);

  const fetchAbort = useRef(null);
  const searchDebounceTimer = useRef(null);
  const projectsCache = useRef({ data: null, timestamp: 0 });
  const descriptionsCache = useRef({}); // Cache by project ID
  const invoicesCache = useRef({ data: null, timestamp: 0, search: '', poFilter: '' }); // Cache for invoices
  const CACHE_DURATION = 30000; // 30 seconds cache

  // ==================== FETCH FUNCTIONS ====================

  const fetchProjects = async (page = 1, search = '', limit = rowsPerPage, useCache = false) => {
    try {
      // OPTIMIZED: Check cache first (if enabled and no search)
      if (useCache && !search && projectsCache.current.data) {
        const cacheAge = Date.now() - projectsCache.current.timestamp;
        if (cacheAge < CACHE_DURATION) {
          setProjects(projectsCache.current.data.records || []);
          setProjectsTotal(projectsCache.current.data.total || 0);
          setCurrentPage(page);
          return;
        }
      }

      if (fetchAbort.current) fetchAbort.current.abort();
      const controller = new AbortController();
      fetchAbort.current = controller;

      setProjectsLoading(true);
      const skip = (page - 1) * limit;
      const params = new URLSearchParams({ skip: String(skip), limit: String(limit) });
      if (search.trim()) params.append('search', search.trim());

      const data = await apiCall(`/du-rpa/projects?${params.toString()}`, {
        signal: controller.signal
      });

      // OPTIMIZED: Cache the results if no search
      if (!search) {
        projectsCache.current = { data, timestamp: Date.now() };
      }

      setProjects(data.records || []);
      setProjectsTotal(data.total || 0);
      setCurrentPage(page);
    } catch (err) {
      if (err.name !== 'AbortError') {
        setTransient(setError, err.message || 'Failed to fetch projects');
      }
    } finally {
      setProjectsLoading(false);
    }
  };

  const fetchDescriptions = async (projectId, useCache = true) => {
    if (!projectId) return;

    // OPTIMIZED: Check cache first
    if (useCache && descriptionsCache.current[projectId]) {
      const cached = descriptionsCache.current[projectId];
      const cacheAge = Date.now() - cached.timestamp;
      if (cacheAge < CACHE_DURATION) {
        setDescriptions(cached.data.records || []);
        return;
      }
    }

    try {
      setDescriptionsLoading(true);
      const data = await apiCall(`/du-rpa/projects/${projectId}/descriptions?skip=0&limit=500`);

      // OPTIMIZED: Cache the results
      descriptionsCache.current[projectId] = { data, timestamp: Date.now() };

      setDescriptions(data.records || []);
    } catch (err) {
      setTransient(setError, err.message || 'Failed to fetch descriptions');
    } finally {
      setDescriptionsLoading(false);
    }
  };

  const fetchInvoices = async (page = 1, search = '', poFilter = '', limit = rowsPerPage, useCache = false) => {
    try {
      // OPTIMIZED: Check cache first (if enabled and no search/filter changes)
      if (useCache && !search && !poFilter && invoicesCache.current.data) {
        const cacheAge = Date.now() - invoicesCache.current.timestamp;
        if (cacheAge < CACHE_DURATION) {
          setInvoices(invoicesCache.current.data.records || []);
          setInvoicesTotal(invoicesCache.current.data.total || 0);
          setInvoicesPage(page);
          return;
        }
      }

      setInvoicesLoading(true);
      const skip = (page - 1) * limit;
      const params = new URLSearchParams({ skip: String(skip), limit: String(limit) });
      if (search.trim()) params.append('search', search.trim());
      if (poFilter.trim()) params.append('po_filter', poFilter.trim());

      const data = await apiCall(`/du-rpa/invoices?${params.toString()}`);

      // OPTIMIZED: Cache the results if no search or filter
      if (!search && !poFilter) {
        invoicesCache.current = { data, timestamp: Date.now(), search: '', poFilter: '' };
      }

      setInvoices(data.records || []);
      setInvoicesTotal(data.total || 0);
      setInvoicesPage(page);
    } catch (err) {
      setTransient(setError, err.message || 'Failed to fetch invoices');
    } finally {
      setInvoicesLoading(false);
    }
  };

  // ==================== EFFECTS ====================

  useEffect(() => {
    if (activeView === 'projects') {
      fetchProjects(1, '', rowsPerPage, true); // OPTIMIZED: Use cache
    } else {
      // OPTIMIZED: Fetch both with cache enabled
      fetchProjects(1, '', rowsPerPage, true);
      fetchInvoices(1, '', '', rowsPerPage, true);
    }
  }, [activeView]);

  // OPTIMIZED: Cleanup debounce timer on unmount
  useEffect(() => {
    return () => {
      if (searchDebounceTimer.current) {
        clearTimeout(searchDebounceTimer.current);
      }
    };
  }, []);

  // ==================== TOGGLE EXPAND ====================

  const toggleExpandRow = async (projectId) => {
    if (expandedProjectId === projectId) {
      setExpandedProjectId(null);
      setDescriptions([]);
    } else {
      setExpandedProjectId(projectId);
      await fetchDescriptions(projectId);
    }
  };

  // ==================== PROJECT HANDLERS ====================

  const openProjectModal = (project = null) => {
    if (project) {
      setIsEditing(true);
      setEditingId(project.id);
      setProjectForm({ po_number: project.po_number });
    } else {
      setIsEditing(false);
      setEditingId(null);
      setProjectForm({ po_number: '' });
    }
    setShowProjectModal(true);
  };

  const handleProjectSubmit = async (e) => {
    e.preventDefault();
    try {
      if (isEditing) {
        await apiCall(`/du-rpa/projects/${editingId}`, {
          method: 'PUT',
          body: JSON.stringify(projectForm)
        });
        setTransient(setSuccess, 'Project updated successfully!');
      } else {
        await apiCall('/du-rpa/projects', {
          method: 'POST',
          body: JSON.stringify(projectForm)
        });
        setTransient(setSuccess, 'Project created successfully!');
      }
      setShowProjectModal(false);
      // OPTIMIZED: Invalidate cache after modification
      projectsCache.current = { data: null, timestamp: 0 };
      fetchProjects(currentPage, searchTerm);
    } catch (err) {
      setTransient(setError, err.message);
    }
  };

  const handleProjectDelete = async () => {
    if (!deleteTarget) return;
    setDeleteLoading(true);
    try {
      await apiCall(`/du-rpa/projects/${deleteTarget.id}`, { method: 'DELETE' });
      setTransient(setSuccess, 'Project deleted successfully!');
      setShowDeleteModal(false);
      setDeleteTarget(null);
      if (expandedProjectId === deleteTarget.id) {
        setExpandedProjectId(null);
        setDescriptions([]);
      }
      // OPTIMIZED: Invalidate cache after deletion
      projectsCache.current = { data: null, timestamp: 0 };
      fetchProjects(currentPage, searchTerm);
    } catch (err) {
      setTransient(setError, err.message);
    } finally {
      setDeleteLoading(false);
    }
  };

  // ==================== DESCRIPTION HANDLERS ====================

  const openDescModal = (projectId, desc = null) => {
    setCurrentProjectForDesc(projectId);
    if (desc) {
      setIsEditing(true);
      setEditingId(desc.id);
      setDescForm({
        description: desc.description || '',
        po_line_item: desc.po_line_item || '',
        po_qty_as_per_po: desc.po_qty_as_per_po ?? '',
        po_qty_per_unit: desc.po_qty_per_unit ?? '',
        price_per_unit: desc.price_per_unit ?? ''
      });
    } else {
      setIsEditing(false);
      setEditingId(null);
      setDescForm({
        description: '',
        po_line_item: '',
        po_qty_as_per_po: '',
        po_qty_per_unit: '',
        price_per_unit: ''
      });
    }
    setShowDescModal(true);
  };

  const handleDescSubmit = async (e) => {
    e.preventDefault();
    const payload = {
      ...descForm,
      po_qty_as_per_po: descForm.po_qty_as_per_po ? parseFloat(descForm.po_qty_as_per_po) : null,
      po_qty_per_unit: descForm.po_qty_per_unit ? parseFloat(descForm.po_qty_per_unit) : null,
      price_per_unit: descForm.price_per_unit ? parseFloat(descForm.price_per_unit) : null
    };

    try {
      if (isEditing) {
        await apiCall(`/du-rpa/descriptions/${editingId}`, {
          method: 'PUT',
          body: JSON.stringify(payload)
        });
        setTransient(setSuccess, 'Description updated successfully!');
      } else {
        await apiCall(`/du-rpa/projects/${currentProjectForDesc}/descriptions`, {
          method: 'POST',
          body: JSON.stringify(payload)
        });
        setTransient(setSuccess, 'Description created successfully!');
      }
      setShowDescModal(false);
      // OPTIMIZED: Invalidate both caches after modification
      projectsCache.current = { data: null, timestamp: 0 };
      if (expandedProjectId) {
        delete descriptionsCache.current[expandedProjectId];
      }
      fetchDescriptions(expandedProjectId, false); // Force refresh
      fetchProjects(currentPage, searchTerm); // Refresh project stats
    } catch (err) {
      setTransient(setError, err.message);
    }
  };

  const handleDescDelete = async (desc) => {
    if (!window.confirm('Are you sure you want to delete this description?')) return;
    try {
      await apiCall(`/du-rpa/descriptions/${desc.id}`, { method: 'DELETE' });
      setTransient(setSuccess, 'Description deleted successfully!');
      // OPTIMIZED: Invalidate both caches after deletion
      projectsCache.current = { data: null, timestamp: 0 };
      if (expandedProjectId) {
        delete descriptionsCache.current[expandedProjectId];
      }
      fetchDescriptions(expandedProjectId, false); // Force refresh
      fetchProjects(currentPage, searchTerm);
    } catch (err) {
      setTransient(setError, err.message);
    }
  };

  // ==================== UPLOAD HANDLERS ====================

  const handleDescCSVUpload = (projectId) => async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setUploading(true);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const result = await apiCall(`/du-rpa/projects/${projectId}/descriptions/upload-csv`, {
        method: 'POST',
        body: formData
      });
      setTransient(setSuccess, `Uploaded ${result.inserted} descriptions. ${result.errors?.length || 0} errors.`);
      // OPTIMIZED: Invalidate both caches after data modification
      projectsCache.current = { data: null, timestamp: 0 };
      delete descriptionsCache.current[projectId];
      fetchDescriptions(projectId, false); // Force refresh
      fetchProjects(currentPage, searchTerm);
    } catch (err) {
      setTransient(setError, err.message);
    } finally {
      setUploading(false);
      e.target.value = '';
    }
  };

  const handleInvoiceCSVUpload = (projectId) => async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setUploading(true);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const result = await apiCall(`/du-rpa/projects/${projectId}/invoices/upload-csv`, {
        method: 'POST',
        body: formData
      });
      let msg = `Uploaded ${result.inserted} invoices.`;
      if (result.errors?.length > 0) {
        msg += ` ${result.errors.length} errors: ${result.errors.slice(0, 3).join('; ')}`;
      }
      setTransient(setSuccess, msg);
      // OPTIMIZED: Invalidate all caches after invoice upload (affects stats)
      projectsCache.current = { data: null, timestamp: 0 };
      invoicesCache.current = { data: null, timestamp: 0, search: '', poFilter: '' };
      delete descriptionsCache.current[projectId];
      fetchDescriptions(projectId, false); // Force refresh to show updated stats
      fetchProjects(currentPage, searchTerm);
      fetchInvoices(invoicesPage, searchTerm, invoicePoFilter);
    } catch (err) {
      setTransient(setError, err.message);
    } finally {
      setUploading(false);
      e.target.value = '';
    }
  };

  const handleInvoiceDelete = async (invoice) => {
    if (!window.confirm(`Are you sure you want to delete invoice ${invoice.sap_invoice_number || invoice.customer_invoice_number}?`)) return;
    try {
      await apiCall(`/du-rpa/invoices/${invoice.id}`, { method: 'DELETE' });
      setTransient(setSuccess, 'Invoice deleted successfully!');
      // OPTIMIZED: Invalidate all caches after deletion (affects stats)
      projectsCache.current = { data: null, timestamp: 0 };
      invoicesCache.current = { data: null, timestamp: 0, search: '', poFilter: '' };
      if (invoice.project_id && descriptionsCache.current[invoice.project_id]) {
        delete descriptionsCache.current[invoice.project_id];
      }
      fetchInvoices(invoicesPage, searchTerm, invoicePoFilter);
      fetchProjects(currentPage, searchTerm);
    } catch (err) {
      setTransient(setError, err.message);
    }
  };

  const handleCustomerInvoiceUpdate = async (invoiceId, newValue) => {
    try {
      const params = new URLSearchParams({ customer_invoice: newValue });
      await apiCall(`/du-rpa/invoices/${invoiceId}/customer-invoice?${params.toString()}`, { method: 'PATCH' });
      setTransient(setSuccess, 'Customer invoice updated successfully!');
      setEditingCustomerInvoice(null);
      // OPTIMIZED: Invalidate invoice cache after update
      invoicesCache.current = { data: null, timestamp: 0, search: '', poFilter: '' };
      fetchInvoices(invoicesPage, searchTerm, invoicePoFilter);
    } catch (err) {
      setTransient(setError, err.message);
    }
  };

  // ==================== SEARCH HANDLER ====================

  const onSearchChange = (e) => {
    const v = e.target.value;
    setSearchTerm(v);

    // OPTIMIZED: Debounce search - wait 300ms after user stops typing
    if (searchDebounceTimer.current) {
      clearTimeout(searchDebounceTimer.current);
    }

    searchDebounceTimer.current = setTimeout(() => {
      fetchProjects(1, v);
    }, 300);
  };

  const onInvoiceSearchChange = (e) => {
    const v = e.target.value;
    setSearchTerm(v);

    // OPTIMIZED: Debounce invoice search too
    if (searchDebounceTimer.current) {
      clearTimeout(searchDebounceTimer.current);
    }

    searchDebounceTimer.current = setTimeout(() => {
      fetchInvoices(1, v, invoicePoFilter);
    }, 300);
  };

  // ==================== FORMAT HELPERS ====================

  const formatCurrency = (value) => {
    if (value == null || value === '') return '-';
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'SAR' }).format(value);
  };

  const formatNumber = (value) => {
    if (value == null || value === '') return '-';
    return new Intl.NumberFormat('en-US').format(value);
  };

  // ==================== CSV DOWNLOAD HELPERS ====================

  const downloadDescriptionsTemplate = () => {
    const csvContent = `description,po_line_item,po_qty_as_per_po,po_qty_per_unit,price_per_unit
"Supply and install fiber optic cable",10,1000,1000,25.50
"Router configuration and setup",20,50,50,150.00
"Network switch installation",30,100,100,85.75`;

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = 'descriptions_template.csv';
    link.click();
    URL.revokeObjectURL(link.href);
  };

  const downloadInvoicesTemplate = () => {
    const row1 = `,,,,,,,,,,,,,,,,`;
    const row2 = `,,,,,,,,,,,,,,,,`;
    const headers = `PO#,New PO number,PR #,PPO#,Site ID,Model/Scope,LI#,Description,QTY,Unit Price,PAC Date,SAP Invoice,Invoice date,Customer Invoice #,PRF %,VAT Rate`;
    const csvContent = `${row1}\n${row2}\n${headers}
PO-123456,NEW-PO-001,PR-001,PPO-INV-001,SITE001,Model-A,LI-001,Microwave indoor unit - including minimum 2x25G interface,100,1500.00,2024-01-15,SAP-INV-001,2024-01-16,CUST-INV-001,85,15
PO-123456,NEW-PO-001,PR-001,PPO-INV-001,SITE001,Model-A,LI-002,E1 card with accessories,50,250.00,2024-01-15,SAP-INV-001,2024-01-16,CUST-INV-001,85,15
PO-123456,NEW-PO-002,PR-002,PPO-INV-002,SITE002,Model-B,LI-001,STM-1 card with accessories,75,350.00,2024-01-20,SAP-INV-002,2024-01-22,CUST-INV-002,100,15`;

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = 'invoices_template.csv';
    link.click();
    URL.revokeObjectURL(link.href);
  };

  // ==================== STATS CARDS ====================

  // OPTIMIZED: Memoize expensive calculations to avoid recalculating on every render
  const projectStatCards = useMemo(() => {
    const totalPOValue = projects.reduce((sum, p) => sum + (p.total_po_value || 0), 0);
    const totalBilled = projects.reduce((sum, p) => sum + (p.total_billed_value || 0), 0);

    return [
      { label: 'Total Projects', value: projectsTotal },
      { label: 'Total PO Value', value: formatCurrency(totalPOValue) },
      { label: 'Total Billed', value: formatCurrency(totalBilled) },
      { label: 'Page', value: `${currentPage} / ${Math.ceil(projectsTotal / rowsPerPage) || 1}` }
    ];
  }, [projects, projectsTotal, currentPage, rowsPerPage]);

  const invoiceStatCards = useMemo(() => {
    const uniqueSites = new Set(invoices.map(inv => inv.site_id)).size;
    const totalItems = invoices.reduce((sum, inv) => sum + (inv.items_count || 0), 0);

    return [
      { label: 'Total Invoices', value: invoicesTotal },
      { label: 'Unique Sites', value: uniqueSites },
      { label: 'Total Items', value: totalItems },
      { label: 'Page', value: `${invoicesPage} / ${Math.ceil(invoicesTotal / rowsPerPage) || 1}` }
    ];
  }, [invoices, invoicesTotal, invoicesPage, rowsPerPage]);

  const statCards = activeView === 'projects' ? projectStatCards : invoiceStatCards;

  // ==================== HELP SECTIONS ====================

  const helpSections = [
    {
      icon: '📋',
      title: 'Overview',
      content: (
        <HelpText>
          DU RPA Logistics manages projects with descriptions (line items) and invoices.
          Each project is identified by a unique PO#. Click the arrow to expand and see descriptions.
        </HelpText>
      )
    },
    {
      icon: '📁',
      title: 'Projects',
      content: (
        <HelpList items={[
          'Create projects with unique PO numbers',
          'Click ▶ to expand and view descriptions',
          'Upload descriptions via CSV',
          'Upload invoices to track billing against descriptions'
        ]} />
      )
    },
    {
      icon: '📝',
      title: 'Descriptions CSV Upload',
      content: (
        <>
          <HelpText>Upload descriptions for a project using a CSV file with the following structure:</HelpText>
          <HelpList items={[
            '<strong>Required:</strong> description - The description text',
            '<strong>Optional:</strong> po_line_item - PO Line Item identifier',
            '<strong>Optional:</strong> po_qty_as_per_po - PO Qty as per PO (numeric)',
            '<strong>Optional:</strong> po_qty_per_unit - PO Qty per unit (numeric)',
            '<strong>Optional:</strong> price_per_unit - Price per unit (numeric)'
          ]} />
          <div style={{ marginTop: '1rem' }}>
            <button
              onClick={downloadDescriptionsTemplate}
              style={{
                padding: '0.5rem 1rem',
                background: '#124191',
                color: 'white',
                border: 'none',
                borderRadius: '6px',
                cursor: 'pointer',
                fontSize: '0.9rem',
                fontWeight: '500'
              }}
            >
              📥 Download Template
            </button>
          </div>
        </>
      )
    },
    {
      icon: '🧾',
      title: 'Invoices CSV Upload',
      content: (
        <>
          <HelpText>Upload invoices using a CSV file (one row per invoice item). Headers must be in the 3rd row:</HelpText>
          <HelpList items={[
            '<strong>1. PO#</strong> - Must match the project PO number',
            '<strong>2. New PO number</strong> - New PO identifier (optional)',
            '<strong>3. PR #</strong> - PR number (optional)',
            '<strong>4. PPO#</strong> - Unique per invoice (required, prevents duplicates)',
            '<strong>5. Site ID</strong> - Site identifier (optional)',
            '<strong>6. Model/Scope</strong> - Model information (optional)',
            '<strong>7. LI#</strong> - Line Item number (optional)',
            '<strong>8. Description</strong> - Must match existing descriptions exactly (required)',
            '<strong>9. QTY</strong> - Quantity (required, numeric)',
            '<strong>10. Unit Price</strong> - Must match description price (optional)',
            '<strong>11. PAC Date</strong> - PAC date (optional)',
            '<strong>12. SAP Invoice</strong> - SAP invoice number (optional)',
            '<strong>13. Invoice date</strong> - Invoice date (optional)',
            '<strong>14. Customer Invoice #</strong> - Customer invoice number (optional)',
            '<strong>15. PRF %</strong> - PRF percentage (optional, numeric)',
            '<strong>16. VAT Rate</strong> - VAT rate percentage (optional, numeric)',
            '<strong>Note:</strong> Rows with same PPO# are grouped into one invoice. If any description doesn\'t match or unit price is wrong, entire invoice is declined.'
          ]} />
          <div style={{ marginTop: '1rem' }}>
            <button
              onClick={downloadInvoicesTemplate}
              style={{
                padding: '0.5rem 1rem',
                background: '#124191',
                color: 'white',
                border: 'none',
                borderRadius: '6px',
                cursor: 'pointer',
                fontSize: '0.9rem',
                fontWeight: '500'
              }}
            >
              📥 Download Template
            </button>
          </div>
        </>
      )
    },
    {
      icon: '💡',
      title: 'How It Works',
      content: (
        <HelpList items={[
          'Step 1: Create a project with a unique PO number',
          'Step 2: Upload descriptions CSV to define line items',
          'Step 3: Upload invoices CSV to track billing against descriptions',
          'Step 4: View calculated stats: Total PO Value, Actual Qty Billed, Balance',
          'Balance shown in red indicates over-billing, green indicates fully billed'
        ]} />
      )
    }
  ];

  const totalPages = Math.ceil(projectsTotal / rowsPerPage);

  // ==================== RENDER ====================

  return (
    <div className="inventory-container">
      {/* Header */}
      <div className="inventory-header">
        <TitleWithInfo
          title="DU RPA Logistics"
          subtitle={activeView === 'projects' ? "Manage Projects & Descriptions" : "Manage Invoices"}
          onInfoClick={() => setShowHelpModal(true)}
        />
        <div className="header-actions">
          {activeView === 'projects' && (
            <button className="btn-primary" onClick={() => openProjectModal()}>
              <span className="btn-icon">+</span> New Project
            </button>
          )}
        </div>
      </div>

      {/* Filter Bar */}
      <FilterBar
        searchTerm={searchTerm}
        onSearchChange={activeView === 'projects' ? onSearchChange : onInvoiceSearchChange}
        searchPlaceholder={activeView === 'projects' ? "Search by PO#..." : "Search by PPO#, Site ID, Invoices..."}
        dropdowns={activeView === 'invoices' ? [
          {
            label: 'Filter by PO#',
            value: invoicePoFilter,
            onChange: (e) => {
              const v = e.target.value;
              setInvoicePoFilter(v);
              fetchInvoices(1, searchTerm, v);
            },
            options: projects.map(p => ({ value: p.po_number, label: p.po_number })),
            placeholder: 'All Projects'
          }
        ] : []}
        showClearButton={!!searchTerm}
        onClearSearch={() => {
          setSearchTerm('');
          // OPTIMIZED: Clear debounce timer on manual clear
          if (searchDebounceTimer.current) {
            clearTimeout(searchDebounceTimer.current);
          }
          if (activeView === 'projects') {
            fetchProjects(1, '');
          } else {
            fetchInvoices(1, '', invoicePoFilter);
          }
        }}
      />

      {/* Messages */}
      {error && <div className="message error-message">{error}</div>}
      {success && <div className="message success-message">{success}</div>}

      {/* Stats */}
      <StatsCarousel cards={statCards} visibleCount={4} />

      {/* Projects Table with Expandable Rows */}
      {activeView === 'projects' && (
        <>
          <div className="data-table-wrapper">
            {projectsLoading && <div className="loading-indicator">Loading projects...</div>}
        <table className="data-table">
          <thead>
            <tr>
              <th style={{ width: '50px' }}></th>
              <th>PO#</th>
              <th>Descriptions</th>
              <th>Invoices</th>
              <th>Total PO Value</th>
              <th>Total Billed</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {projects.length === 0 && !projectsLoading ? (
              <tr>
                <td colSpan={7} className="no-data">No projects found. Create your first project!</td>
              </tr>
            ) : (
              projects.map((project) => (
                <React.Fragment key={project.id}>
                  {/* Project Row */}
                  <tr className="parent-row">
                    <td>
                      <button
                        onClick={() => toggleExpandRow(project.id)}
                        className="expand-btn"
                        title="Expand/Collapse descriptions"
                      >
                        {expandedProjectId === project.id ? '▼' : '▶'}
                      </button>
                    </td>
                    <td><strong>{project.po_number}</strong></td>
                    <td>{project.description_count || 0}</td>
                    <td>{project.invoice_count || 0}</td>
                    <td>{formatCurrency(project.total_po_value)}</td>
                    <td>{formatCurrency(project.total_billed_value)}</td>
                    <td>
                      <div className="action-buttons">
                        <button
                          className="btn-action btn-edit"
                          onClick={() => openProjectModal(project)}
                          title="Edit Project"
                        >
                          ✏️
                        </button>
                        <button
                          className="btn-action btn-delete"
                          onClick={() => { setDeleteTarget(project); setShowDeleteModal(true); }}
                          title="Delete Project"
                        >
                          🗑️
                        </button>
                      </div>
                    </td>
                  </tr>

                  {/* Expanded Descriptions Row */}
                  {expandedProjectId === project.id && (
                    <tr className="expanded-row">
                      <td colSpan={7}>
                        <div className="nested-items-container">
                          <div className="nested-items-header">
                            <h4 className="nested-items-title">Descriptions for PO# {project.po_number}</h4>
                            <div className="nested-items-actions">
                              <button
                                className="btn-secondary"
                                onClick={() => openDescModal(project.id)}
                              >
                                <span className="btn-icon">+</span>
                                Add Description
                              </button>
                              <label className={`btn-secondary ${uploading ? 'disabled' : ''}`}>
                                <span className="btn-icon">📤</span>
                                Upload Descriptions CSV
                                <input
                                  type="file"
                                  accept=".csv"
                                  style={{ display: 'none' }}
                                  disabled={uploading}
                                  onChange={handleDescCSVUpload(project.id)}
                                />
                              </label>
                              <label className={`btn-secondary ${uploading ? 'disabled' : ''}`}>
                                <span className="btn-icon">🧾</span>
                                Upload Invoices CSV
                                <input
                                  type="file"
                                  accept=".csv"
                                  style={{ display: 'none' }}
                                  disabled={uploading}
                                  onChange={handleInvoiceCSVUpload(project.id)}
                                />
                              </label>
                            </div>
                          </div>

                          {descriptionsLoading ? (
                            <div className="loading-indicator">Loading descriptions...</div>
                          ) : (
                            <div className="nested-table-wrapper">
                              <table className="nested-table">
                                <thead>
                                  <tr>
                                    <th>Description</th>
                                    <th>PO Line Item</th>
                                    <th>PO Qty (as per PO)</th>
                                    <th>PO Qty (per unit)</th>
                                    <th>Price/Unit</th>
                                    <th>Total PO Value</th>
                                    <th>Actual Qty Billed</th>
                                    <th>Actual Value Billed</th>
                                    <th>Balance</th>
                                    <th>Actions</th>
                                  </tr>
                                </thead>
                                <tbody>
                                  {descriptions.length === 0 ? (
                                    <tr>
                                      <td colSpan={10} className="no-data">
                                        No descriptions found. Add descriptions manually or upload CSV.
                                      </td>
                                    </tr>
                                  ) : (
                                    descriptions.map((desc) => (
                                      <tr key={desc.id}>
                                        <td title={desc.description}>{desc.description}</td>
                                        <td>{desc.po_line_item || '-'}</td>
                                        <td>{formatNumber(desc.po_qty_as_per_po)}</td>
                                        <td>{formatNumber(desc.po_qty_per_unit)}</td>
                                        <td>{formatCurrency(desc.price_per_unit)}</td>
                                        <td>{formatCurrency(desc.total_po_value)}</td>
                                        <td>{formatNumber(desc.actual_qty_billed)}</td>
                                        <td>{formatCurrency(desc.actual_value_billed)}</td>
                                        <td style={{
                                          color: desc.balance < 0 ? '#dc2626' : desc.balance === 0 ? '#16a34a' : 'inherit',
                                          fontWeight: desc.balance <= 0 ? 'bold' : 'normal'
                                        }}>
                                          {formatNumber(desc.balance)}
                                        </td>
                                        <td>
                                          <div className="action-buttons">
                                            <button
                                              className="btn-action btn-edit"
                                              onClick={() => openDescModal(project.id, desc)}
                                              title="Edit"
                                            >
                                              ✏️
                                            </button>
                                            <button
                                              className="btn-action btn-delete"
                                              onClick={() => handleDescDelete(desc)}
                                              title="Delete"
                                            >
                                              🗑️
                                            </button>
                                          </div>
                                        </td>
                                      </tr>
                                    ))
                                  )}
                                </tbody>
                              </table>
                            </div>
                          )}
                        </div>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              ))
            )}
          </tbody>
        </table>
      </div>

          {/* Pagination */}
          <Pagination
            currentPage={currentPage}
            totalPages={totalPages}
            onPageChange={(page) => fetchProjects(page, searchTerm)}
            previousText="← Previous"
            nextText="Next →"
          />
        </>
      )}

      {/* Invoices Table */}
      {activeView === 'invoices' && (
        <>
          <div className="data-table-wrapper">
        {invoicesLoading && <div className="loading-indicator">Loading invoices...</div>}
        <table className="data-table">
          <thead>
            <tr>
              <th style={{width: '50px'}}>Details</th>
              <th>PPO#</th>
              <th>PO#</th>
              <th>New PO#</th>
              <th>PR#</th>
              <th>Site ID</th>
              <th>Model</th>
              <th>SAP Invoice</th>
              <th>Invoice Date</th>
              <th>Customer Invoice</th>
              <th>PRF %</th>
              <th>VAT Rate</th>
              <th>Items</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {invoices.length === 0 && !invoicesLoading ? (
              <tr>
                <td colSpan={14} className="no-data">No invoices found. Upload invoices via CSV in the Projects view!</td>
              </tr>
            ) : (
              invoices.map((invoice) => (
                <React.Fragment key={invoice.id}>
                  <tr className="parent-row">
                    <td>
                      <button
                        className="expand-btn"
                        onClick={() => setExpandedInvoiceId(expandedInvoiceId === invoice.id ? null : invoice.id)}
                        title={expandedInvoiceId === invoice.id ? 'Collapse' : 'Expand'}
                      >
                        {expandedInvoiceId === invoice.id ? '▼' : '▶'}
                      </button>
                    </td>
                    <td><strong>{invoice.ppo_number}</strong></td>
                    <td>{invoice.po_number || '-'}</td>
                    <td>{invoice.new_po_number || '-'}</td>
                    <td>{invoice.pr_number || '-'}</td>
                    <td>{invoice.site_id || '-'}</td>
                    <td title={invoice.model}>{invoice.model || '-'}</td>
                    <td>{invoice.sap_invoice_number || '-'}</td>
                    <td>{invoice.invoice_date ? new Date(invoice.invoice_date).toLocaleDateString() : '-'}</td>
                    <td onDoubleClick={() => setEditingCustomerInvoice({ id: invoice.id, value: invoice.customer_invoice_number || '' })}>
                      {editingCustomerInvoice?.id === invoice.id ? (
                        <input
                          type="text"
                          defaultValue={editingCustomerInvoice.value}
                          autoFocus
                          onBlur={(e) => handleCustomerInvoiceUpdate(invoice.id, e.target.value)}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter') handleCustomerInvoiceUpdate(invoice.id, e.target.value);
                            if (e.key === 'Escape') setEditingCustomerInvoice(null);
                          }}
                          style={{
                            width: '100%',
                            padding: '0.2rem 0.4rem',
                            border: '2px solid #124191',
                            borderRadius: '4px',
                            fontSize: '0.85rem'
                          }}
                        />
                      ) : (
                        <span style={{ cursor: 'pointer' }} title="Double-click to edit">
                          {invoice.customer_invoice_number || '-'}
                        </span>
                      )}
                    </td>
                    <td>{invoice.prf_percentage != null ? `${invoice.prf_percentage}%` : '-'}</td>
                    <td>{invoice.vat_rate != null ? `${invoice.vat_rate}%` : '-'}</td>
                    <td>{invoice.items?.length || 0}</td>
                    <td>
                      <div className="action-buttons">
                        <button
                          className="btn-action btn-delete"
                          onClick={() => handleInvoiceDelete(invoice)}
                          title="Delete Invoice"
                        >
                          🗑️
                        </button>
                      </div>
                    </td>
                  </tr>

                  {/* Expanded Invoice Items Row */}
                  {expandedInvoiceId === invoice.id && (
                    <tr className="expanded-row">
                      <td colSpan={14}>
                        <div className="nested-items-container">
                          <div className="nested-items-header">
                            <h4 className="nested-items-title">Invoice Items for PPO# {invoice.ppo_number}</h4>
                          </div>

                          <div className="nested-table-wrapper">
                            <table className="nested-table">
                              <thead>
                                <tr>
                                  <th>LI#</th>
                                  <th>Description</th>
                                  <th>QTY</th>
                                  <th>Unit Price</th>
                                  <th>PAC Date</th>
                                </tr>
                              </thead>
                              <tbody>
                                {!invoice.items || invoice.items.length === 0 ? (
                                  <tr>
                                    <td colSpan={5} className="no-data">
                                      No items found for this invoice.
                                    </td>
                                  </tr>
                                ) : (
                                  invoice.items.map((item) => (
                                    <tr key={item.id}>
                                      <td>{item.li_number || '-'}</td>
                                      <td title={item.description_text}>{item.description_text || '-'}</td>
                                      <td>{formatNumber(item.quantity)}</td>
                                      <td>{item.unit_price ? formatCurrency(item.unit_price) : '-'}</td>
                                      <td>{item.pac_date ? new Date(item.pac_date).toLocaleDateString() : '-'}</td>
                                    </tr>
                                  ))
                                )}
                              </tbody>
                            </table>
                          </div>
                        </div>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Invoices Pagination */}
      <Pagination
        currentPage={invoicesPage}
        totalPages={Math.ceil(invoicesTotal / rowsPerPage)}
        onPageChange={(page) => fetchInvoices(page, searchTerm, invoicePoFilter)}
        previousText="← Previous"
        nextText="Next →"
      />
        </>
      )}

      {/* Project Modal */}
      {showProjectModal && (
        <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && setShowProjectModal(false)}>
          <div className="modal-container">
            <div className="modal-header">
              <h2 className="modal-title">{isEditing ? 'Edit Project' : 'Create New Project'}</h2>
              <button className="modal-close" onClick={() => setShowProjectModal(false)}>✕</button>
            </div>
            <form className="modal-form" onSubmit={handleProjectSubmit}>
              <div className="form-section">
                <div className="form-field">
                  <label>PO# *</label>
                  <input
                    type="text"
                    value={projectForm.po_number}
                    onChange={(e) => setProjectForm({ po_number: e.target.value })}
                    required
                    placeholder="Enter unique PO number"
                  />
                </div>
              </div>
              <div className="form-actions">
                <button type="button" className="btn-cancel" onClick={() => setShowProjectModal(false)}>Cancel</button>
                <button type="submit" className="btn-submit">{isEditing ? 'Update' : 'Create'}</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Description Modal */}
      {showDescModal && (
        <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && setShowDescModal(false)}>
          <div className="modal-container" style={{ maxWidth: '700px' }}>
            <div className="modal-header">
              <h2 className="modal-title">{isEditing ? 'Edit Description' : 'Create New Description'}</h2>
              <button className="modal-close" onClick={() => setShowDescModal(false)}>✕</button>
            </div>
            <form className="modal-form" onSubmit={handleDescSubmit}>
              <div className="form-section">
                <h3 className="section-title">Description Details</h3>
                <div className="form-field" style={{ gridColumn: '1 / -1' }}>
                  <label>Description *</label>
                  <input
                    type="text"
                    value={descForm.description}
                    onChange={(e) => setDescForm({ ...descForm, description: e.target.value })}
                    required
                    placeholder="Enter description text"
                  />
                </div>
                <div className="form-grid">
                  <div className="form-field">
                    <label>PO Line Item</label>
                    <input
                      type="text"
                      value={descForm.po_line_item}
                      onChange={(e) => setDescForm({ ...descForm, po_line_item: e.target.value })}
                      placeholder="e.g., 10, 20, 30"
                    />
                  </div>
                  <div className="form-field">
                    <label>PO Qty (as per PO)</label>
                    <input
                      type="number"
                      step="0.01"
                      value={descForm.po_qty_as_per_po}
                      onChange={(e) => setDescForm({ ...descForm, po_qty_as_per_po: e.target.value })}
                    />
                  </div>
                  <div className="form-field">
                    <label>PO Qty (per unit)</label>
                    <input
                      type="number"
                      step="0.01"
                      value={descForm.po_qty_per_unit}
                      onChange={(e) => setDescForm({ ...descForm, po_qty_per_unit: e.target.value })}
                    />
                  </div>
                  <div className="form-field">
                    <label>Price per Unit</label>
                    <input
                      type="number"
                      step="0.01"
                      value={descForm.price_per_unit}
                      onChange={(e) => setDescForm({ ...descForm, price_per_unit: e.target.value })}
                    />
                  </div>
                </div>
              </div>
              <div className="form-actions">
                <button type="button" className="btn-cancel" onClick={() => setShowDescModal(false)}>Cancel</button>
                <button type="submit" className="btn-submit">{isEditing ? 'Update' : 'Create'}</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      <DeleteConfirmationModal
        show={showDeleteModal}
        onConfirm={handleProjectDelete}
        onCancel={() => { setShowDeleteModal(false); setDeleteTarget(null); }}
        title="Delete Project"
        itemName={deleteTarget?.po_number || ''}
        warningText="Are you sure you want to delete project"
        additionalInfo="This will permanently delete all related data:"
        affectedItems={['All descriptions for this project', 'All invoices for this project']}
        confirmButtonText="Delete Project"
        loading={deleteLoading}
      />

      {/* Help Modal */}
      <HelpModal
        show={showHelpModal}
        onClose={() => setShowHelpModal(false)}
        title="DU RPA Logistics - User Guide"
        sections={helpSections}
        closeButtonText="Got it!"
      />
    </div>
  );
}
