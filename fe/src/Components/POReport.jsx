import React, { useState, useEffect, useRef } from 'react';
import { apiCall, setTransient } from '../api.js';
import '../css/Inventory.css';
import FilterBar from './shared/FilterBar';
import DataTable from './shared/DataTable';
import Pagination from './shared/Pagination';
import TitleWithInfo from './shared/InfoButton';
import StatsCarousel from './shared/StatsCarousel';
import HelpModal, { HelpList, HelpText, CodeBlock } from './shared/HelpModal';

const ROWS_PER_PAGE = 50;

export default function POReport() {
  const [rows, setRows] = useState([]);
  const [currentPage, setCurrentPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [uploadingCSV, setUploadingCSV] = useState(false);

  // Info modal state
  const [showInfoModal, setShowInfoModal] = useState(false);
  const [infoItem, setInfoItem] = useState(null);
  const [showHelpModal, setShowHelpModal] = useState(false);

  const fetchAbort = useRef(null);
  const fileInputRef = useRef(null);

  const fetchReports = async (page = 1, search = searchTerm) => {
    try {
      if (fetchAbort.current) fetchAbort.current.abort();
      const controller = new AbortController();
      fetchAbort.current = controller;
      setLoading(true);
      setError('');

      const params = new URLSearchParams({
        skip: ((page - 1) * ROWS_PER_PAGE).toString(),
        limit: ROWS_PER_PAGE.toString()
      });

      if (search.trim()) {
        params.set('search', search.trim());
      }

      const data = await apiCall(`/po-report/reports?${params.toString()}`, {
        signal: controller.signal,
        method: 'GET',
      });

      setRows(data.items || []);
      setTotal(data.total || 0);
      setCurrentPage(page);
    } catch (err) {
      if (err.name !== 'AbortError') {
        setTransient(setError, err.message || 'Failed to fetch reports');
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchReports();
  }, []);

  const handleSearchChange = (e) => {
    const value = e.target.value;
    setSearchTerm(value);
    fetchReports(1, value);
  };

  const handleClearSearch = () => {
    setSearchTerm('');
    fetchReports(1, '');
  };

  const handleFileSelect = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    if (!file.name.endsWith('.csv')) {
      setTransient(setError, 'Please select a valid CSV file');
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
      return;
    }

    try {
      setUploadingCSV(true);
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch(`${import.meta.env.VITE_API_URL}/po-report/upload-csv`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: formData
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to upload CSV');
      }

      const result = await response.json();
      setTransient(setSuccess, `${result.message} (${result.successful_rows}/${result.total_rows} rows imported)`);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
      fetchReports(currentPage, searchTerm);
    } catch (err) {
      setTransient(setError, err.message || 'Failed to upload CSV');
    } finally {
      setUploadingCSV(false);
    }
  };

  const handleDeleteAll = async () => {
    const confirmMessage = 'Are you sure you want to delete ALL reports? This action cannot be undone!';

    if (!window.confirm(confirmMessage)) return;

    const secondConfirm = window.confirm('This is your final warning. Are you absolutely sure?');
    if (!secondConfirm) return;

    try {
      setLoading(true);
      const params = new URLSearchParams({ confirm: 'true' });

      const result = await apiCall(`/po-report/delete-all?${params.toString()}`, {
        method: 'DELETE',
      });

      setTransient(setSuccess, result.message || `Deleted ${result.deleted_count} report(s)`);
      fetchReports(1, searchTerm);
    } catch (err) {
      setTransient(setError, err.message || 'Failed to delete reports');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (row) => {
    if (!window.confirm(`Are you sure you want to delete this record (Pur. Doc: ${row.pur_doc})?`)) return;

    try {
      await apiCall(`/po-report/report/${row.id}`, {
        method: 'DELETE',
      });
      setTransient(setSuccess, 'Report deleted successfully!');
      fetchReports(currentPage, searchTerm);
    } catch (err) {
      setTransient(setError, err.message);
    }
  };

  const openInfoModal = (row) => {
    setInfoItem(row);
    setShowInfoModal(true);
  };

  const closeInfoModal = () => {
    setShowInfoModal(false);
    setInfoItem(null);
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '-';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-GB', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const totalPages = Math.ceil(total / ROWS_PER_PAGE);

  // Help sections for the guide modal
  const helpSections = [
    {
      icon: '📋',
      title: 'Overview',
      content: (
        <HelpText>
          The PO Report Management component allows you to upload, view, search, and manage Purchase Order (PO) reports
          from CSV files. Track purchase orders, invoicing, supplier information, and financial data all in one place.
        </HelpText>
      )
    },
    {
      icon: '✨',
      title: 'Features & Buttons',
      content: (
        <HelpList
          items={[
            { label: '⬆️ Upload CSV', text: 'Bulk upload PO reports from a CSV file. Accepts files with 26 specific columns.' },
            { label: '🗑️ Delete All', text: 'Deletes ALL PO reports (Senior Admin only). Requires two confirmations and cannot be undone.' },
            { label: 'Search', text: 'Filter reports by any field including Pur. Doc., Site Ref, Project, Supplier, Material, etc.' },
            { label: 'Clear Search', text: 'Resets the search filter and shows all reports.' },
            { label: 'ℹ️ View Details', text: 'Click on any row\'s info button to see all 26 fields in a detailed modal.' },
            { label: '🗑️ Delete Row', text: 'Click on any row\'s delete button to remove that specific report (requires confirmation).' },
            { label: 'Pagination', text: 'Navigate through pages showing 50 records per page.' }
          ]}
        />
      )
    },
    {
      icon: '📊',
      title: 'Table Columns (18 visible)',
      content: (
        <HelpList
          items={[
            { label: 'Pur. Doc.', text: 'Purchase Document Number' },
            { label: 'Site Ref', text: 'Customer Site Reference' },
            { label: 'Project', text: 'Project Name' },
            { label: 'SO#', text: 'Sales Order Number' },
            { label: 'Material', text: 'Material Description' },
            { label: 'Site Name', text: 'Site Name' },
            { label: 'WBS Element', text: 'Work Breakdown Structure Element' },
            { label: 'Supplier', text: 'Supplier Code' },
            { label: 'Supplier Name', text: 'Supplier Company Name' },
            { label: 'Order Date', text: 'Order Date' },
            { label: 'GR Date', text: 'Goods Receipt Date' },
            { label: 'PO Value SAR', text: 'Purchase Order Value in SAR' },
            { label: 'Invoiced SAR', text: 'Invoiced Value in SAR' },
            { label: '% Invoiced', text: 'Percentage Invoiced' },
            { label: 'Balance SAR', text: 'Balance Value in SAR' },
            { label: 'SVO Number', text: 'SVO Number' },
            { label: 'Header Text', text: 'Header Text' },
            { label: 'SMP ID', text: 'SMP ID' }
          ]}
        />
      )
    },
    {
      icon: '📁',
      title: 'CSV Upload Requirements',
      content: (
        <>
          <HelpText>
            Your CSV file must contain these <strong>26 headers</strong> (exact names, spaces are automatically handled):
          </HelpText>
          <CodeBlock
            items={[
              'Pur. Doc.',
              'Customer Site Ref',
              'Project',
              'SO#',
              'Material DES',
              'RR Date',
              'Site name',
              'WBS Element',
              'Supplier',
              'Name 1',
              'Order date',
              'GR date',
              'Supplier Invoice',
              'IR Docdate',
              'Pstng Date',
              'PO Value SAR',
              'Invoiced Value SAR',
              '% Invoiced',
              'Balance Value SAR',
              'SVO Number',
              'Header text',
              'SMP ID',
              'Remarks',
              'AInd',
              'Accounting indicator desc'
            ]}
          />
          <HelpText isNote>
            <strong>Note:</strong> Leading/trailing spaces in headers are automatically handled.
            File must be in .csv format. Empty rows are skipped. Multiple encodings supported (UTF-8, Latin-1, Windows-1252).
          </HelpText>
        </>
      )
    },
    {
      icon: '🔍',
      title: 'Search & Filter',
      content: (
        <>
          <HelpText>
            The search feature searches across multiple fields simultaneously:
          </HelpText>
          <HelpList
            items={[
              'Pur. Doc., Customer Site Ref, Project, SO#',
              'Material DES, Site Name, Supplier, Supplier Name',
              'Header Text, Remarks',
              'Case-insensitive and supports partial matching'
            ]}
          />
          <HelpText isNote>
            <strong>Tip:</strong> Search is real-time - results update as you type. Use specific terms for faster results.
          </HelpText>
        </>
      )
    },
    {
      icon: '📄',
      title: 'Detail View (All 26 Fields)',
      content: (
        <HelpText>
          Click the info icon (ℹ️) on any row to see a complete modal with <strong>all 26 fields</strong>, including:
          RR Date, Supplier Invoice, IR Docdate, Pstng Date, Remarks, AInd, Accounting Indicator Description,
          and timestamps (Created At, Updated At).
        </HelpText>
      )
    },
    {
      icon: '💡',
      title: 'Tips & Best Practices',
      content: (
        <HelpList
          items={[
            'Validate your CSV format before uploading - ensure all 26 headers are present.',
            'Use search to quickly find specific PO documents or suppliers instead of browsing pages.',
            'The table shows 50 records per page for optimal performance.',
            'Upload progress shows successful/failed rows - check error messages if some rows fail.',
            'Delete operations require confirmation and cannot be undone.',
            'All data is stored as text, preserving original formatting from your CSV (dates, numbers with commas, percentages).',
            'Horizontal scrolling is available if columns extend beyond screen width.',
            'Only Senior Admins can delete all reports - individual row deletion is available to all users.'
          ]}
        />
      )
    }
  ];

  // Define table columns
  const tableColumns = [
    { key: 'pur_doc', label: 'Pur. Doc.' },
    { key: 'customer_site_ref', label: 'Site Ref' },
    { key: 'project', label: 'Project' },
    { key: 'so_number', label: 'SO#' },
    { key: 'material_des', label: 'Material' },
    { key: 'site_name', label: 'Site Name' },
    { key: 'wbs_element', label: 'WBS Element' },
    { key: 'supplier', label: 'Supplier' },
    { key: 'name_1', label: 'Supplier Name' },
    { key: 'order_date', label: 'Order Date' },
    { key: 'gr_date', label: 'GR Date' },
    { key: 'po_value_sar', label: 'PO Value SAR' },
    { key: 'invoiced_value_sar', label: 'Invoiced SAR' },
    { key: 'percent_invoiced', label: '% Invoiced' },
    { key: 'balance_value_sar', label: 'Balance SAR' },
    { key: 'svo_number', label: 'SVO Number' },
    { key: 'header_text', label: 'Header Text' },
    { key: 'smp_id', label: 'SMP ID' }
  ];

  // Define table actions
  const tableActions = [
    {
      icon: 'ℹ️',
      onClick: openInfoModal,
      title: 'View Details',
      className: 'btn-info'
    },
    {
      icon: '🗑️',
      onClick: handleDelete,
      title: 'Delete',
      className: 'btn-danger'
    }
  ];

  // Define stat cards
  const statCards = [
    { label: 'Total Records', value: total },
    { label: 'Current Page', value: `${currentPage} / ${totalPages || 1}` },
    { label: 'Records/Page', value: ROWS_PER_PAGE }
  ];

  return (
    <div className="inventory-container">
      {/* Header Section */}
      <div className="inventory-header">
        <TitleWithInfo
          title="PO Report Management"
          subtitle="Upload and manage purchase order reports from CSV"
          onInfoClick={() => setShowHelpModal(true)}
          infoTooltip="How to use this component"
        />
        <div className="header-actions" style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
          <input
            type="file"
            accept=".csv"
            ref={fileInputRef}
            onChange={handleFileSelect}
            style={{ display: 'none' }}
          />
          <button
            className="btn-primary"
            onClick={() => fileInputRef.current?.click()}
            disabled={uploadingCSV}
          >
            <span className="btn-icon">⬆️</span>
            {uploadingCSV ? 'Uploading...' : 'Upload CSV'}
          </button>
          <button
            className="btn-danger"
            onClick={handleDeleteAll}
            disabled={loading}
          >
            <span className="btn-icon">🗑️</span>
            Delete All
          </button>
        </div>
      </div>

      {/* Filters Section */}
      <FilterBar
        searchTerm={searchTerm}
        onSearchChange={handleSearchChange}
        searchPlaceholder="Search reports..."
        showClearButton={!!searchTerm}
        onClearSearch={handleClearSearch}
        clearButtonText="Clear Search"
      />

      {/* Messages */}
      {error && <div className="message error-message">{error}</div>}
      {success && <div className="message success-message">{success}</div>}
      {loading && <div className="loading-indicator">Loading...</div>}

      {/* Stats */}
      <StatsCarousel cards={statCards} visibleCount={3} />

      {/* Table Section */}
      <DataTable
        columns={tableColumns}
        data={rows}
        actions={tableActions}
        loading={loading}
        noDataMessage="No reports found"
        className="inventory-table-wrapper"
      />

      {/* Pagination */}
      <Pagination
        currentPage={currentPage}
        totalPages={totalPages}
        onPageChange={(page) => fetchReports(page, searchTerm)}
        previousText="← Previous"
        nextText="Next →"
      />

      {/* Info Modal */}
      {showInfoModal && infoItem && (
        <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && closeInfoModal()}>
          <div className="modal-container" style={{ maxWidth: '900px', maxHeight: '90vh', overflow: 'auto' }}>
            <div className="modal-header">
              <h2 className="modal-title">PO Report Details</h2>
              <button className="modal-close" onClick={closeInfoModal} type="button">✕</button>
            </div>

            <div className="modal-form">
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                <div className="info-row">
                  <label className="info-label">Pur. Doc.:</label>
                  <span className="info-value">{infoItem.pur_doc || '-'}</span>
                </div>

                <div className="info-row">
                  <label className="info-label">Customer Site Ref:</label>
                  <span className="info-value">{infoItem.customer_site_ref || '-'}</span>
                </div>

                <div className="info-row">
                  <label className="info-label">Project:</label>
                  <span className="info-value">{infoItem.project || '-'}</span>
                </div>

                <div className="info-row">
                  <label className="info-label">SO#:</label>
                  <span className="info-value">{infoItem.so_number || '-'}</span>
                </div>

                <div className="info-row" style={{ gridColumn: '1 / -1' }}>
                  <label className="info-label">Material DES:</label>
                  <span className="info-value">{infoItem.material_des || '-'}</span>
                </div>

                <div className="info-row">
                  <label className="info-label">RR Date:</label>
                  <span className="info-value">{infoItem.rr_date || '-'}</span>
                </div>

                <div className="info-row">
                  <label className="info-label">Site Name:</label>
                  <span className="info-value">{infoItem.site_name || '-'}</span>
                </div>

                <div className="info-row">
                  <label className="info-label">WBS Element:</label>
                  <span className="info-value">{infoItem.wbs_element || '-'}</span>
                </div>

                <div className="info-row">
                  <label className="info-label">Supplier:</label>
                  <span className="info-value">{infoItem.supplier || '-'}</span>
                </div>

                <div className="info-row" style={{ gridColumn: '1 / -1' }}>
                  <label className="info-label">Name 1:</label>
                  <span className="info-value">{infoItem.name_1 || '-'}</span>
                </div>

                <div className="info-row">
                  <label className="info-label">Order Date:</label>
                  <span className="info-value">{infoItem.order_date || '-'}</span>
                </div>

                <div className="info-row">
                  <label className="info-label">GR Date:</label>
                  <span className="info-value">{infoItem.gr_date || '-'}</span>
                </div>

                <div className="info-row">
                  <label className="info-label">Supplier Invoice:</label>
                  <span className="info-value">{infoItem.supplier_invoice || '-'}</span>
                </div>

                <div className="info-row">
                  <label className="info-label">IR Docdate:</label>
                  <span className="info-value">{infoItem.ir_docdate || '-'}</span>
                </div>

                <div className="info-row">
                  <label className="info-label">Pstng Date:</label>
                  <span className="info-value">{infoItem.pstng_date || '-'}</span>
                </div>

                <div className="info-row">
                  <label className="info-label">PO Value SAR:</label>
                  <span className="info-value">{infoItem.po_value_sar || '-'}</span>
                </div>

                <div className="info-row">
                  <label className="info-label">Invoiced Value SAR:</label>
                  <span className="info-value">{infoItem.invoiced_value_sar || '-'}</span>
                </div>

                <div className="info-row">
                  <label className="info-label">% Invoiced:</label>
                  <span className="info-value">{infoItem.percent_invoiced || '-'}</span>
                </div>

                <div className="info-row">
                  <label className="info-label">Balance Value SAR:</label>
                  <span className="info-value">{infoItem.balance_value_sar || '-'}</span>
                </div>

                <div className="info-row">
                  <label className="info-label">SVO Number:</label>
                  <span className="info-value">{infoItem.svo_number || '-'}</span>
                </div>

                <div className="info-row">
                  <label className="info-label">Header Text:</label>
                  <span className="info-value">{infoItem.header_text || '-'}</span>
                </div>

                <div className="info-row">
                  <label className="info-label">SMP ID:</label>
                  <span className="info-value">{infoItem.smp_id || '-'}</span>
                </div>

                <div className="info-row" style={{ gridColumn: '1 / -1' }}>
                  <label className="info-label">Remarks:</label>
                  <span className="info-value">{infoItem.remarks || '-'}</span>
                </div>

                <div className="info-row">
                  <label className="info-label">AInd:</label>
                  <span className="info-value">{infoItem.aind || '-'}</span>
                </div>

                <div className="info-row">
                  <label className="info-label">Accounting Indicator:</label>
                  <span className="info-value">{infoItem.accounting_indicator_desc || '-'}</span>
                </div>

                <div className="info-row">
                  <label className="info-label">Created At:</label>
                  <span className="info-value">{formatDate(infoItem.created_at)}</span>
                </div>

                <div className="info-row">
                  <label className="info-label">Updated At:</label>
                  <span className="info-value">{formatDate(infoItem.updated_at)}</span>
                </div>
              </div>

              <div className="form-actions">
                <button type="button" className="btn-secondary" onClick={closeInfoModal}>
                  Close
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Help/Info Modal */}
      <HelpModal
        show={showHelpModal}
        onClose={() => setShowHelpModal(false)}
        title="PO Report Management - User Guide"
        sections={helpSections}
        closeButtonText="Got it!"
      />

      {/* Additional Styles */}
      <style>{`
        .info-row {
          display: flex;
          align-items: center;
          padding: 12px 0;
          border-bottom: 1px solid #e2e8f0;
        }
        .info-row:last-child {
          border-bottom: none;
        }
        .info-label {
          font-weight: 600;
          color: #475569;
          font-size: 0.875rem;
          min-width: 160px;
          margin-right: 16px;
        }
        .info-value {
          color: #1e293b;
          font-size: 0.875rem;
          flex: 1;
        }
      `}</style>
    </div>
  );
}
