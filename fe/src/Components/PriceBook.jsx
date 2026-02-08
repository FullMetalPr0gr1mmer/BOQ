import React, { useState, useEffect, useRef } from 'react';
import { apiCall, setTransient } from '../api.js';
import '../css/Inventory.css';
import FilterBar from './shared/FilterBar';
import DataTable from './shared/DataTable';
import Pagination from './shared/Pagination';
import TitleWithInfo from './shared/InfoButton';
import StatsCarousel from './shared/StatsCarousel';

const ROWS_PER_PAGE = 50;

export default function PriceBook() {
  const [rows, setRows] = useState([]);
  const [currentPage, setCurrentPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [uploading, setUploading] = useState(false);
  const [loading, setLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedPO, setSelectedPO] = useState('');
  const [poNumbers, setPONumbers] = useState([]);

  // File upload state
  const fileInputRef = useRef(null);

  // Info modal state
  const [showInfoModal, setShowInfoModal] = useState(false);
  const [infoItem, setInfoItem] = useState(null);

  const fetchAbort = useRef(null);
  const searchDebounceTimer = useRef(null);

  const fetchPriceBooks = async (page = 1, search = searchTerm, poNumber = selectedPO) => {
    try {
      if (fetchAbort.current) fetchAbort.current.abort();
      const controller = new AbortController();
      fetchAbort.current = controller;
      setLoading(true);
      setError('');

      const params = new URLSearchParams({
        page: page.toString(),
        page_size: ROWS_PER_PAGE.toString()
      });

      if (search.trim()) {
        params.set('search', search.trim());
      }

      if (poNumber) {
        params.set('po_number', poNumber);
      }

      const data = await apiCall(`/price-books/?${params.toString()}`, {
        signal: controller.signal,
        method: 'GET',
      });

      setRows(data.items || []);
      setTotal(data.total || 0);
      setCurrentPage(page);
    } catch (err) {
      if (err.name !== 'AbortError') {
        setTransient(setError, err.message || 'Failed to fetch price books');
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPriceBooks(1, '', '');
    fetchPONumbers();
  }, []);

  const fetchPONumbers = async () => {
    try {
      const data = await apiCall('/price-books/po-numbers', {
        method: 'GET',
      });
      setPONumbers(data || []);
    } catch (err) {
      console.error('Failed to fetch PO numbers:', err);
    }
  };

  useEffect(() => {
    return () => {
      if (searchDebounceTimer.current) {
        clearTimeout(searchDebounceTimer.current);
      }
    };
  }, []);

  const handleSearchChange = (e) => {
    const value = e.target.value;
    setSearchTerm(value);

    if (searchDebounceTimer.current) {
      clearTimeout(searchDebounceTimer.current);
    }

    searchDebounceTimer.current = setTimeout(() => {
      fetchPriceBooks(1, value, selectedPO);
    }, 300);
  };

  const handlePOChange = (e) => {
    const value = e.target.value;
    setSelectedPO(value);
    fetchPriceBooks(1, searchTerm, value);
  };

  const handleClearFilters = () => {
    setSearchTerm('');
    setSelectedPO('');
    fetchPriceBooks(1, '', '');
  };

  const handleUploadClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    if (!file.name.endsWith('.csv')) {
      setTransient(setError, "File must be a CSV file (.csv)");
      e.target.value = '';
      return;
    }

    setUploading(true);
    setError('');
    setSuccess('');

    const formData = new FormData();
    formData.append('csv_file', file);

    try {
      const result = await apiCall('/price-books/upload', {
        method: 'POST',
        body: formData,
      });

      setTransient(setSuccess, `Successfully uploaded ${result.records_created} records!`);
      fetchPriceBooks(1, searchTerm, selectedPO);
      fetchPONumbers(); // Refresh PO numbers list

      if (fileInputRef.current) fileInputRef.current.value = '';
    } catch (err) {
      setTransient(setError, err.message);
    } finally {
      setUploading(false);
    }
  };

  const handleDeleteAll = async () => {
    if (!selectedPO) {
      setTransient(setError, "Please select a PO# to delete all records.");
      return;
    }

    if (!window.confirm(`Are you sure you want to delete ALL records for PO# ${selectedPO}? This action cannot be undone.`)) {
      return;
    }

    try {
      const result = await apiCall(`/price-books/by-po-number/${encodeURIComponent(selectedPO)}`, {
        method: 'DELETE',
      });

      setTransient(setSuccess, `Successfully deleted ${result.deleted_count} records for PO# ${selectedPO}`);
      setSelectedPO('');
      fetchPriceBooks(1, searchTerm, '');
      fetchPONumbers(); // Refresh PO numbers list
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

  const handleDelete = async (row) => {
    if (!window.confirm(`Are you sure you want to delete this price book record?`)) return;

    try {
      await apiCall(`/price-books/${row.id}`, {
        method: 'DELETE',
      });
      setTransient(setSuccess, 'Deleted successfully!');
      fetchPriceBooks(currentPage, searchTerm, selectedPO);
      fetchPONumbers(); // Refresh PO numbers list
    } catch (err) {
      setTransient(setError, err.message);
    }
  };

  const handleExportCSV = async () => {
    try {
      const response = await fetch(`${import.meta.env.VITE_API_URL}/price-books/export/csv`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
      });

      if (!response.ok) throw new Error('Export failed');

      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `price_books_${new Date().getTime()}.csv`);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    } catch (err) {
      setTransient(setError, err.message || 'Failed to export CSV');
    }
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

  const tableColumns = [
    // { key: 'id', label: 'ID' },
    { key: 'project_name', label: 'Project Name', render: (row) => row.project_name || '-' },
    { key: 'po_number', label: 'PO#', render: (row) => row.po_number || '-' },
    { key: 'merge_poline_uplline', label: 'Merge POLine#UPLLine#', render: (row) => row.merge_poline_uplline || '-' },
    { key: 'quantity', label: 'Quantity', render: (row) => row.quantity || '-' },
    { key: 'unit_price_sar_after_special_discount', label: 'UP(SAR) after Sp. Discount', title: 'Unit Price(SAR) after Special Discount for this project only (% on), not applicable for future reference', render: (row) => row.unit_price_sar_after_special_discount || '-' },
    { key: 'fv_unit_price_after_descope', label: 'FV UP after Descope', title: 'FV Unit Price after Descope', render: (row) => row.fv_unit_price_after_descope || '-' },
    {
      key: 'created_at',
      label: 'Created At',
      render: (row) => formatDate(row.created_at)
    }
  ];

  const getTableActions = () => {
    return [
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
  };

  const statCards = [
    { label: 'Total Records', value: total },
    { label: 'Current Page', value: `${currentPage} / ${totalPages || 1}` },
    { label: 'Selected PO#', value: selectedPO || 'All' }
  ];

  return (
    <div className="inventory-container">
      {/* Header Section */}
      <div className="inventory-header">
        <TitleWithInfo
          title="Price Book"
          subtitle="Manage price book records for MW and RAN projects"
          infoTooltip="Price book information"
        />
        <div className="header-actions">
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv"
            style={{ display: "none" }}
            onChange={handleFileChange}
          />
          <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
            <button
              className={`btn-primary ${uploading ? 'disabled' : ''}`}
              onClick={handleUploadClick}
              disabled={uploading}
              title="Upload CSV file"
            >
              <span className="btn-icon">📤</span>
              {uploading ? 'Uploading...' : 'Upload CSV'}
            </button>
            <button
              className={`btn-danger ${!selectedPO ? 'disabled' : ''}`}
              onClick={handleDeleteAll}
              disabled={!selectedPO}
              title={!selectedPO ? "Select a PO# to delete all records" : `Delete all records for PO# ${selectedPO}`}
            >
              <span className="btn-icon">🗑️</span>
              Delete All by PO#
            </button>
          </div>
        </div>
      </div>

      {/* Filters Section */}
      <FilterBar
        searchTerm={searchTerm}
        onSearchChange={handleSearchChange}
        searchPlaceholder="Search by project name, PO#, or vendor part number..."
        dropdowns={[
          {
            label: 'PO Number',
            value: selectedPO,
            onChange: handlePOChange,
            placeholder: '-- All PO Numbers --',
            options: poNumbers.map(po => ({
              value: po,
              label: po
            }))
          }
        ]}
        showClearButton={!!searchTerm || !!selectedPO}
        onClearSearch={handleClearFilters}
        clearButtonText="Clear Filters"
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
        actions={getTableActions()}
        loading={loading}
        noDataMessage="No price book records found"
        className="inventory-table-wrapper"
      />

      {/* Pagination */}
      <Pagination
        currentPage={currentPage}
        totalPages={totalPages}
        onPageChange={(page) => fetchPriceBooks(page, searchTerm, selectedPO)}
        previousText="← Previous"
        nextText="Next →"
      />

      {/* Info Modal */}
      {showInfoModal && infoItem && (
        <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && closeInfoModal()}>
          <div className="modal-container" style={{ maxWidth: '800px', maxHeight: '90vh', overflow: 'auto' }}>
            <div className="modal-header">
              <h2 className="modal-title">Price Book Details</h2>
              <button className="modal-close" onClick={closeInfoModal} type="button">✕</button>
            </div>

            <div className="modal-form">
              <div style={{ display: 'grid', gap: '16px', gridTemplateColumns: 'repeat(2, 1fr)' }}>
                {/* <div className="info-row">
                  <label className="info-label">ID:</label>
                  <span className="info-value">{infoItem.id}</span>
                </div> */}
                <div className="info-row">
                  <label className="info-label">Project Name:</label>
                  <span className="info-value">{infoItem.project_name || '-'}</span>
                </div>
                <div className="info-row">
                  <label className="info-label">PO Number:</label>
                  <span className="info-value">{infoItem.po_number || '-'}</span>
                </div>
                <div className="info-row">
                  <label className="info-label">Merge POLine#UPLLine#:</label>
                  <span className="info-value">{infoItem.merge_poline_uplline || '-'}</span>
                </div>
                <div className="info-row">
                  <label className="info-label">PO Line:</label>
                  <span className="info-value">{infoItem.po_line || '-'}</span>
                </div>
                <div className="info-row">
                  <label className="info-label">UPL Line:</label>
                  <span className="info-value">{infoItem.upl_line || '-'}</span>
                </div>
                <div className="info-row">
                  <label className="info-label">Merge PO#, POLine#, UPLLine#:</label>
                  <span className="info-value">{infoItem.merge_po_poline_uplline || '-'}</span>
                </div>
                <div className="info-row">
                  <label className="info-label">Vendor Part Number (Item Code):</label>
                  <span className="info-value">{infoItem.vendor_part_number_item_code || '-'}</span>
                </div>
                <div className="info-row">
                  <label className="info-label">Customer Item Type:</label>
                  <span className="info-value">{infoItem.customer_item_type || '-'}</span>
                </div>
                <div className="info-row">
                  <label className="info-label">Local Content:</label>
                  <span className="info-value">{infoItem.local_content || '-'}</span>
                </div>
                <div className="info-row">
                  <label className="info-label">Serialized:</label>
                  <span className="info-value">{infoItem.serialized || '-'}</span>
                </div>
                <div className="info-row">
                  <label className="info-label">Active/Passive:</label>
                  <span className="info-value">{infoItem.active_or_passive || '-'}</span>
                </div>
                <div className="info-row">
                  <label className="info-label">UOM:</label>
                  <span className="info-value">{infoItem.uom || '-'}</span>
                </div>
                <div className="info-row">
                  <label className="info-label">Quantity:</label>
                  <span className="info-value">{infoItem.quantity || '-'}</span>
                </div>
                <div className="info-row">
                  <label className="info-label">Unit:</label>
                  <span className="info-value">{infoItem.unit || '-'}</span>
                </div>
                <div className="info-row">
                  <label className="info-label">Currency:</label>
                  <span className="info-value">{infoItem.currency || '-'}</span>
                </div>
                <div className="info-row">
                  <label className="info-label">Unit Price Before Discount:</label>
                  <span className="info-value">{infoItem.unit_price_before_discount || '-'}</span>
                </div>
                <div className="info-row">
                  <label className="info-label">Discount:</label>
                  <span className="info-value">{infoItem.discount || '-'}</span>
                </div>
                <div className="info-row">
                  <label className="info-label">PO Total Before Discount:</label>
                  <span className="info-value">{infoItem.po_total_amt_before_discount || '-'}</span>
                </div>
                <div className="info-row">
                  <label className="info-label">Unit Price (SAR) After Discount:</label>
                  <span className="info-value">{infoItem.unit_price_sar_after_special_discount || '-'}</span>
                </div>
                <div className="info-row">
                  <label className="info-label">Final Total After Discount:</label>
                  <span className="info-value">{infoItem.final_total_price_after_discount || '-'}</span>
                </div>
                <div className="info-row">
                  <label className="info-label">FV % as per RRB:</label>
                  <span className="info-value">{infoItem.fv_percent_as_per_rrb || '-'}</span>
                </div>
                <div className="info-row">
                  <label className="info-label">FV:</label>
                  <span className="info-value">{infoItem.fv || '-'}</span>
                </div>
                <div className="info-row">
                  <label className="info-label">Total FV SAR:</label>
                  <span className="info-value">{infoItem.total_fv_sar || '-'}</span>
                </div>
                <div className="info-row">
                  <label className="info-label">Revised FV%:</label>
                  <span className="info-value">{infoItem.revised_fv_percent || '-'}</span>
                </div>
                <div className="info-row">
                  <label className="info-label">FV Unit Price After Descope:</label>
                  <span className="info-value">{infoItem.fv_unit_price_after_descope || '-'}</span>
                </div>
                <div className="info-row">
                  <label className="info-label">To Go Contract Price EUR:</label>
                  <span className="info-value">{infoItem.to_go_contract_price_eur || '-'}</span>
                </div>
                <div className="info-row">
                  <label className="info-label">R SSP EUR:</label>
                  <span className="info-value">{infoItem.r_ssp_eur || '-'}</span>
                </div>
                <div className="info-row">
                  <label className="info-label">Old UP:</label>
                  <span className="info-value">{infoItem.old_up || '-'}</span>
                </div>
                <div className="info-row">
                  <label className="info-label">Delta:</label>
                  <span className="info-value">{infoItem.delta || '-'}</span>
                </div>
                <div className="info-row" style={{ gridColumn: 'span 2' }}>
                  <label className="info-label">Zain Item Category:</label>
                  <span className="info-value">{infoItem.zain_item_category || '-'}</span>
                </div>
                <div className="info-row" style={{ gridColumn: 'span 2' }}>
                  <label className="info-label">Special Discount:</label>
                  <span className="info-value">{infoItem.special_discount || '-'}</span>
                </div>
                <div className="info-row" style={{ gridColumn: 'span 2' }}>
                  <label className="info-label">Claimed Percentage After Special Discount:</label>
                  <span className="info-value">{infoItem.claimed_percentage_after_special_discount || '-'}</span>
                </div>
                <div className="info-row" style={{ gridColumn: 'span 2' }}>
                  <label className="info-label">Description:</label>
                  <span className="info-value">{infoItem.po_line_item_description || '-'}</span>
                </div>
                <div className="info-row" style={{ gridColumn: 'span 2' }}>
                  <label className="info-label">Scope:</label>
                  <span className="info-value">{infoItem.scope || '-'}</span>
                </div>
                <div className="info-row" style={{ gridColumn: 'span 2' }}>
                  <label className="info-label">Sub Scope:</label>
                  <span className="info-value">{infoItem.sub_scope || '-'}</span>
                </div>
                <div className="info-row">
                  <label className="info-label">Uploaded By:</label>
                  <span className="info-value">{infoItem.uploader_name || '-'}</span>
                </div>
                <div className="info-row">
                  <label className="info-label">Created At:</label>
                  <span className="info-value">{formatDate(infoItem.created_at)}</span>
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

      {/* Additional Styles */}
      <style>{`
        .info-row {
          display: flex;
          flex-direction: column;
          gap: 4px;
        }
        .info-label {
          font-weight: 600;
          color: #475569;
          font-size: 0.875rem;
        }
        .info-value {
          color: #1e293b;
          font-size: 0.875rem;
        }
      `}</style>
    </div>
  );
}
