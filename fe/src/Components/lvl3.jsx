import React, { useEffect, useState, useRef } from 'react';
import { apiCall, setTransient } from '../api.js';
import '../css/lvl3.css';
import StatsCarousel from './shared/StatsCarousel';
import FilterBar from './shared/FilterBar';
import ModalForm, { FormSection, FormField } from './shared/ModalForm';
import HelpModal, { HelpList, HelpText, CodeBlock } from './shared/HelpModal';
import TitleWithInfo from './shared/InfoButton';
import Pagination from './shared/Pagination';

const SERVICE_LABELS = {
  "1": "Software",
  "2": "Hardware",
  "3": "Service"
};

const SERVICE_VALUES = {
  "Software": "1",
  "Hardware": "2",
  "Service": "3"
};

const initialLvl3State = {
  project_id: '',
  project_name: '',
  item_name: '',
  uom: '',
  total_quantity: '',
  total_price: '',
  service_type: '',
};

const initialItemState = {
  item_name: '',
  item_details: '',
  vendor_part_number: '',
  service_type: '',
  category: '',
  uom: '',
  upl_line: '',
  quantity: '',
  price: ''
};

export default function Lvl3() {
  const [entries, setEntries] = useState([]);
  const [currentPage, setCurrentPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(10);
  const [showForm, setShowForm] = useState(false);
  const [editingEntry, setEditingEntry] = useState(null);
  const [formData, setFormData] = useState(initialLvl3State);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [projects, setProjects] = useState([]);
  const [selectedProject, setSelectedProject] = useState('');
  const [stats, setStats] = useState({ total_items: 0, total_value: 0, unique_projects: 0 });
  const [showHelpModal, setShowHelpModal] = useState(false);
  const [expandedRowId, setExpandedRowId] = useState(null);
  const [showItemForm, setShowItemForm] = useState(false);
  const [editingItemData, setEditingItemData] = useState(null);
  const [itemFormData, setItemFormData] = useState(initialItemState);
  const [userPermissions, setUserPermissions] = useState({});
  const fetchAbort = useRef(null);

  useEffect(() => {
    fetchProjects();
    fetchLvl3();
    fetchStats();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

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

  const fetchStats = async (projectId = '') => {
    try {
      const params = new URLSearchParams();
      if (projectId) params.append('project_id', projectId);

      // Calculate stats from entries
      const filtered = projectId ? entries.filter(e => e.project_id === projectId) : entries;
      const totalItems = filtered.length;
      const totalValue = filtered.reduce((sum, e) => sum + (e.total_price || 0), 0);
      const uniqueProjects = new Set(entries.map(e => e.project_id)).size;

      setStats({
        total_items: totalItems,
        total_value: totalValue,
        unique_projects: uniqueProjects
      });
    } catch (err) {
      console.error('Failed to calculate stats:', err);
    }
  };

  const fetchLvl3 = async (page = 1, search = '', limit = rowsPerPage, projectId = selectedProject) => {
    try {
      if (fetchAbort.current) fetchAbort.current.abort();
      const controller = new AbortController();
      fetchAbort.current = controller;

      setLoading(true);
      setError('');

      const data = await apiCall('/lvl3/', {
        signal: controller.signal,
        method: 'GET'
      });

      let filtered = data || [];

      // Apply project filter
      if (projectId) {
        filtered = filtered.filter(entry => entry.project_id === projectId);
      }

      // Apply search filter
      if (search.trim()) {
        const searchLower = search.toLowerCase();
        filtered = filtered.filter(entry =>
          entry.project_name?.toLowerCase().includes(searchLower) ||
          entry.item_name?.toLowerCase().includes(searchLower) ||
          entry.project_id?.toLowerCase().includes(searchLower)
        );
      }

      setTotal(filtered.length);
      setEntries(filtered);
      setCurrentPage(page);
      fetchStats(projectId);
    } catch (err) {
      if (err.name !== 'AbortError') {
        setTransient(setError, err.message || 'Failed to fetch entries');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleProjectChange = (e) => {
    const projectId = e.target.value;
    setSelectedProject(projectId);
    setSearchTerm('');
    setCurrentPage(1);
    fetchLvl3(1, '', rowsPerPage, projectId);
  };

  const onSearchChange = (e) => {
    const v = e.target.value;
    setSearchTerm(v);
    setCurrentPage(1);
    fetchLvl3(1, v, rowsPerPage, selectedProject);
  };

  const checkLvl3Permission = async (lvl3Id) => {
    try {
      const permissions = await apiCall(`/lvl3/check_permission/${lvl3Id}`);
      setUserPermissions(prev => ({ ...prev, [lvl3Id]: permissions }));
      return permissions;
    } catch (err) {
      console.error('Failed to check permissions:', err);
      return { can_view: false, can_edit: false, can_delete: false };
    }
  };

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleItemChange = (e) => {
    const { name, value } = e.target;
    setItemFormData(prev => ({ ...prev, [name]: value }));
  };

  const openCreateForm = () => {
    if (!selectedProject) {
      setTransient(setError, 'Please select a project to create a new Lvl3 entry.');
      return;
    }

    const selectedProjectObj = projects.find(p => p.pid_po === selectedProject);
    setFormData({
      ...initialLvl3State,
      project_id: selectedProject,
      project_name: selectedProjectObj?.project_name || ''
    });
    setEditingEntry(null);
    setShowForm(true);
    setError('');
    setSuccess('');
  };

  const openEditForm = async (entry) => {
    const permissions = await checkLvl3Permission(entry.id);
    if (!permissions.can_edit) {
      setTransient(setError, 'You do not have permission to edit this entry.');
      return;
    }

    setEditingEntry(entry);
    setFormData({
      project_id: entry.project_id,
      project_name: entry.project_name,
      item_name: entry.item_name,
      uom: entry.uom,
      total_quantity: entry.total_quantity,
      total_price: entry.total_price,
      service_type: (entry.service_type && entry.service_type.length > 0)
        ? (SERVICE_VALUES[entry.service_type[0]] || entry.service_type[0])
        : '',
    });
    setShowForm(true);
    setError('');
    setSuccess('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    const payload = {
      ...formData,
      total_quantity: parseInt(formData.total_quantity, 10),
      total_price: parseFloat(formData.total_price),
      service_type: formData.service_type ? [formData.service_type] : [],
    };

    try {
      if (editingEntry) {
        await apiCall(`/lvl3/${editingEntry.id}`, {
          method: 'PUT',
          body: JSON.stringify(payload)
        });
      } else {
        await apiCall('/lvl3/create', {
          method: 'POST',
          body: JSON.stringify(payload)
        });
      }

      setTransient(setSuccess, editingEntry ? 'Lvl3 entry updated!' : 'Lvl3 entry created!');
      setShowForm(false);
      setFormData(initialLvl3State);
      setEditingEntry(null);
      fetchLvl3(currentPage, searchTerm, rowsPerPage, selectedProject);
    } catch (err) {
      setTransient(setError, err.message);
    }
  };

  const handleDelete = async (entry) => {
    const permissions = await checkLvl3Permission(entry.id);
    if (!permissions.can_delete) {
      setTransient(setError, 'You do not have permission to delete this entry.');
      return;
    }

    if (!window.confirm(`Delete entry ${entry.project_id} - ${entry.item_name}?`)) return;
    try {
      await apiCall(`/lvl3/${entry.id}`, {
        method: 'DELETE'
      });
      setTransient(setSuccess, 'Entry deleted!');
      fetchLvl3(currentPage, searchTerm, rowsPerPage, selectedProject);
    } catch (err) {
      setTransient(setError, err.message);
    }
  };

  // Item Management Functions
  const handleAddItem = (lvl3Id, parentItemName) => {
    setItemFormData({
      ...initialItemState,
      item_name: parentItemName // Auto-populate item_name from parent
    });
    setEditingItemData({ lvl3Id, itemId: null });
    setShowItemForm(true);
  };

  const handleEditItem = (lvl3Id, item) => {
    setItemFormData({
      ...item,
      service_type: (item.service_type && item.service_type.length > 0)
        ? (SERVICE_VALUES[item.service_type[0]] || item.service_type[0])
        : ''
    });
    setEditingItemData({ lvl3Id, itemId: item.id });
    setShowItemForm(true);
  };

  const handleSaveItem = async (e) => {
    e.preventDefault();
    setError('');
    setSuccess('');

    const payload = {
      ...itemFormData,
      quantity: parseInt(itemFormData.quantity, 10),
      price: parseFloat(itemFormData.price),
      service_type: itemFormData.service_type ? [itemFormData.service_type] : []
    };

    const { lvl3Id, itemId } = editingItemData;

    try {
      if (itemId) {
        await apiCall(`/lvl3/${lvl3Id}/items/${itemId}`, {
          method: 'PUT',
          body: JSON.stringify(payload)
        });
      } else {
        await apiCall(`/lvl3/${lvl3Id}/items`, {
          method: 'POST',
          body: JSON.stringify(payload)
        });
      }

      setTransient(setSuccess, itemId ? 'Item updated successfully!' : 'Item added successfully!');
      setShowItemForm(false);
      setEditingItemData(null);
      fetchLvl3(currentPage, searchTerm, rowsPerPage, selectedProject);
    } catch (err) {
      setTransient(setError, err.message);
    }
  };

  const handleDeleteItem = async (lvl3Id, itemId) => {
    if (!window.confirm("Are you sure you want to delete this item?")) return;
    try {
      await apiCall(`/lvl3/${lvl3Id}/items/${itemId}`, {
        method: 'DELETE'
      });
      setTransient(setSuccess, 'Item deleted!');
      fetchLvl3(currentPage, searchTerm, rowsPerPage, selectedProject);
    } catch (err) {
      setTransient(setError, err.message);
    }
  };

  const handleUploadCSV = (lvl3Id, parentItemName) => async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setError('');
    setSuccess('');

    const reader = new FileReader();
    reader.onload = async (event) => {
      const text = event.target.result;
      const lines = text.split('\n').filter(line => line.trim() !== '');

      if (lines.length === 0) {
        setTransient(setError, 'CSV file is empty.');
        return;
      }

      const parseCSVLine = (line) => {
        const result = [];
        let current = '';
        let inQuotes = false;

        for (let i = 0; i < line.length; i++) {
          const char = line[i];

          if (char === '"') {
            inQuotes = !inQuotes;
          } else if (char === ',' && !inQuotes) {
            result.push(current.trim());
            current = '';
          } else {
            current += char;
          }
        }

        result.push(current.trim());
        return result;
      };

      const payloadItems = [];
      for (let i = 0; i < lines.length; i++) {
        const line = lines[i].trim();
        const columns = parseCSVLine(line);

        if (columns.length < 4) {
          setTransient(setError, `Error on row ${i + 1}: Expected at least 4 columns, got ${columns.length}.`);
          return;
        }

        let item_details = columns[0].replace(/^"|"$/g, '');
        let vendor_part_number = columns[1].replace(/^"|"$/g, '');
        let uom = columns[2].replace(/^"|"$/g, '');
        let priceColumn = columns[3].replace(/^"|"$/g, '');

        let cleanedPriceString = priceColumn;
        cleanedPriceString = cleanedPriceString.replace(/SAR/gi, '');
        cleanedPriceString = cleanedPriceString.trim();
        cleanedPriceString = cleanedPriceString.replace(/[^0-9.,]/g, '');
        cleanedPriceString = cleanedPriceString.replace(/,/g, '');

        const parsedPrice = parseFloat(cleanedPriceString);

        if (isNaN(parsedPrice)) {
          setTransient(setError, `Error on row ${i + 1}: Could not parse price from "${priceColumn}".`);
          return;
        }

        payloadItems.push({
          item_name: parentItemName,
          item_details: item_details,
          vendor_part_number: vendor_part_number,
          service_type: ["2"],
          category: "MW",
          uom: uom,
          quantity: 0,
          price: parsedPrice
        });
      }

      try {
        await apiCall(`/lvl3/${lvl3Id}/items/bulk`, {
          method: 'POST',
          body: JSON.stringify(payloadItems)
        });

        setTransient(setSuccess, 'Items uploaded successfully!');
        e.target.value = null;
        fetchLvl3(currentPage, searchTerm, rowsPerPage, selectedProject);
      } catch (err) {
        setTransient(setError, err.message);
        e.target.value = null;
      }
    };

    reader.readAsText(file);
  };

  const toggleExpandRow = (entryId) => {
    setExpandedRowId(expandedRowId === entryId ? null : entryId);
  };

  const handleRowsPerPageChange = (e) => {
    const newLimit = parseInt(e.target.value);
    setRowsPerPage(newLimit);
    setCurrentPage(1);
    fetchLvl3(1, searchTerm, newLimit, selectedProject);
  };

  const paginatedEntries = entries.slice(
    (currentPage - 1) * rowsPerPage,
    currentPage * rowsPerPage
  );

  const totalPages = Math.ceil(total / rowsPerPage);

  // Define stat cards for the carousel
  const statCards = [
    { label: 'Total Lvl3 Items', value: stats.total_items },
    { label: 'Total Value', value: `${stats.total_value.toLocaleString()} SAR` },
    { label: 'Unique Projects', value: stats.unique_projects },
    { label: 'Current Page', value: `${currentPage} / ${totalPages || 1}` },
    { label: 'Showing', value: `${paginatedEntries.length} items` },
    {
      label: 'Rows Per Page',
      isEditable: true,
      component: (
        <select
          className="stat-select"
          value={rowsPerPage}
          onChange={handleRowsPerPageChange}
        >
          <option value={10}>10</option>
          <option value={25}>25</option>
          <option value={50}>50</option>
          <option value={100}>100</option>
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
          The Level 3 Management component allows you to manage Level 3 BOQ items with nested sub-items.
          Each Level 3 entry can contain multiple child items with detailed specifications. You can filter
          by project, search entries, and bulk upload items via CSV.
        </HelpText>
      )
    },
    {
      icon: '✨',
      title: 'Features & Buttons',
      content: (
        <HelpList
          items={[
            { label: '+ Create Level 3 Item', text: 'Opens a form to create a new Level 3 entry. You must select a project first.' },
            { label: '▶ Expand Row', text: 'Click the arrow to expand/collapse and view child items for each Level 3 entry.' },
            { label: '📤 Upload Items CSV', text: 'Bulk upload child items for a specific Level 3 entry using CSV format.' },
            { label: 'Search Bar', text: 'Filter Level 3 entries by Project Name, Item Name, or Project ID in real-time.' },
            { label: 'Project Dropdown', text: 'Filter all Level 3 entries and statistics by the selected project.' },
            { label: '✏️ Edit', text: 'Click to modify a Level 3 entry or child item.' },
            { label: '🗑️ Delete', text: 'Click to remove a Level 3 entry or child item (requires confirmation).' },
            { label: '‹ › Navigation Arrows', text: 'Cycle through statistics cards to view different metrics.' }
          ]}
        />
      )
    },
    {
      icon: '🔍',
      title: 'Nested Items Table',
      content: (
        <HelpText>
          Each Level 3 entry can have multiple child items. Click the expand arrow (▶) on any row to reveal
          the nested items table. This table shows detailed item information including Item Details, Vendor Part Number,
          Category, UOM, UPL Line, Quantity, Price, and Service Type. You can add, edit, or delete individual items,
          or bulk upload them via CSV. When adding a new item, the Item Name is automatically inherited from the parent Level 3 entry.
        </HelpText>
      )
    },
    {
      icon: '📊',
      title: 'Statistics Cards',
      content: (
        <HelpList
          items={[
            { label: 'Total Lvl3 Items', text: 'Total count of Level 3 entries for the selected project (or all if none selected).' },
            { label: 'Total Value', text: 'Sum of all total_price values across Level 3 entries.' },
            { label: 'Unique Projects', text: 'Number of distinct projects containing Level 3 entries.' },
            { label: 'Current Page', text: 'Shows which page you\'re viewing out of total pages.' },
            { label: 'Showing', text: 'Number of Level 3 entries currently displayed on this page.' },
            { label: 'Rows Per Page', text: 'Adjustable dropdown to control pagination size (10-100).' }
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
            To upload child items for a Level 3 entry via CSV, your file must contain exactly 4 columns in this order:
          </HelpText>
          <CodeBlock
            items={[
              'item_details, vendor_part_number, uom, price'
            ]}
          />
          <HelpText isNote>
            <strong>Example CSV row:</strong> "Fiber Cable","VPN-12345","Meter","1500 SAR"
          </HelpText>
          <HelpText isNote>
            <strong>Note:</strong> The price column can include "SAR" text and commas - they will be automatically removed.
            The item_name will be inherited from the parent Level 3 entry, and service_type defaults to "Hardware".
          </HelpText>
        </>
      )
    },
    {
      icon: '💡',
      title: 'Tips',
      content: (
        <HelpList
          items={[
            'Always select a project before creating Level 3 entries.',
            'Use the expand arrow to view and manage child items for each Level 3 entry.',
            'The search feature filters by Project Name, Item Name, or Project ID.',
            'When creating a new child item, the Item Name is automatically inherited from the parent (disabled field).',
            'Child items can be added individually or in bulk via CSV upload.',
            'Service types: 1=Software, 2=Hardware, 3=Service.',
            'All required fields are marked with an asterisk (*) in the forms.'
          ]}
        />
      )
    }
  ];

  return (
    <div className="lvl3-container">
      {/* Header Section */}
      <div className="lvl3-header">
        <TitleWithInfo
          title="Level 3 Records"
          subtitle="Manage Level 3 BOQ items and their nested sub-items"
          onInfoClick={() => setShowHelpModal(true)}
          infoTooltip="How to use this component"
        />
        <div className="header-actions">
          <button
            className={`btn-primary ${!selectedProject ? 'disabled' : ''}`}
            onClick={openCreateForm}
            disabled={!selectedProject}
            title={!selectedProject ? "Select a project first" : "Create a new Lvl3 entry"}
          >
            <span className="btn-icon">+</span>
            Create Level 3 Item
          </button>
        </div>
      </div>

      {/* Filters Section */}
      <FilterBar
        searchTerm={searchTerm}
        onSearchChange={onSearchChange}
        searchPlaceholder="Filter by Project Name or Item Name..."
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
        onClearSearch={() => {
          setSearchTerm('');
          fetchLvl3(1, '', rowsPerPage, selectedProject);
        }}
        clearButtonText="Clear Search"
      />

      {/* Messages */}
      {error && <div className="message error-message">{error}</div>}
      {success && <div className="message success-message">{success}</div>}
      {loading && <div className="loading-indicator">Loading entries...</div>}

      {/* Stats Carousel */}
      <StatsCarousel cards={statCards} visibleCount={4} />

      {/* Custom Expandable Table */}
      <div className="data-table-wrapper lvl3-table-wrapper">
        <table className="data-table">
          <thead>
            <tr>
              <th style={{ width: '40px' }}></th>
              <th>Project ID</th>
              <th>Project Name</th>
              <th>Item Name</th>
              <th>UOM</th>
              <th>Total Quantity</th>
              <th>Total Price</th>
              <th>Service Type</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {paginatedEntries.length === 0 && !loading ? (
              <tr>
                <td colSpan={9} className="no-data">No Level 3 entries found</td>
              </tr>
            ) : (
              paginatedEntries.map((entry) => (
                <React.Fragment key={entry.id}>
                  <tr className="parent-row">
                    <td>
                      <button
                        onClick={() => toggleExpandRow(entry.id)}
                        className="expand-btn"
                        title="Expand/Collapse items"
                      >
                        {expandedRowId === entry.id ? '▼' : '▶'}
                      </button>
                    </td>
                    <td>{entry.project_id}</td>
                    <td>{entry.project_name}</td>
                    <td>{entry.item_name}</td>
                    <td>{entry.uom}</td>
                    <td>{entry.total_quantity?.toLocaleString()}</td>
                    <td>{entry.total_price?.toLocaleString()}</td>
                    <td>{(entry.service_type || []).map(val => SERVICE_LABELS[val] || val).join(', ')}</td>
                    <td>
                      <div className="action-buttons">
                        <button
                          className="btn-action btn-edit"
                          onClick={() => openEditForm(entry)}
                          title="Edit"
                        >
                          ✏️
                        </button>
                        <button
                          className="btn-action btn-delete"
                          onClick={() => handleDelete(entry)}
                          title="Delete"
                        >
                          🗑️
                        </button>
                      </div>
                    </td>
                  </tr>
                  {expandedRowId === entry.id && (
                    <tr className="expanded-row">
                      <td colSpan={9}>
                        <div className="nested-items-container">
                          <div className="nested-items-header">
                            <h4 className="nested-items-title">Items for {entry.item_name}</h4>
                            <div className="nested-items-actions">
                              <button
                                className="btn-secondary"
                                onClick={() => handleAddItem(entry.id, entry.item_name)}
                              >
                                <span className="btn-icon">+</span>
                                Add Item
                              </button>
                              <label className="btn-secondary">
                                <span className="btn-icon">📤</span>
                                Upload CSV
                                <input
                                  type="file"
                                  accept=".csv"
                                  style={{ display: 'none' }}
                                  onChange={handleUploadCSV(entry.id, entry.item_name)}
                                />
                              </label>
                            </div>
                          </div>
                          <div className="nested-table-wrapper">
                            <table className="nested-table">
                              <thead>
                                <tr>
                                  <th>Item Name</th>
                                  <th>Details</th>
                                  <th>Vendor Part #</th>
                                  <th>Category</th>
                                  <th>UOM</th>
                                  <th>UPL Line</th>
                                  <th>Quantity</th>
                                  <th>Price</th>
                                  <th>Service Type</th>
                                  <th>Actions</th>
                                </tr>
                              </thead>
                              <tbody>
                                {(entry.items || []).length === 0 ? (
                                  <tr>
                                    <td colSpan={10} className="no-data">No items found</td>
                                  </tr>
                                ) : (
                                  (entry.items || []).map((item) => (
                                    <tr key={item.id}>
                                      <td>{item.item_name}</td>
                                      <td>{item.item_details}</td>
                                      <td>{item.vendor_part_number}</td>
                                      <td>{item.category}</td>
                                      <td>{item.uom}</td>
                                      <td>{item.upl_line || 'N/A'}</td>
                                      <td>{item.quantity}</td>
                                      <td>{item.price?.toLocaleString()}</td>
                                      <td>{(item.service_type || []).map(val => SERVICE_LABELS[val] || val).join(', ')}</td>
                                      <td>
                                        <div className="action-buttons">
                                          <button
                                            className="btn-action btn-edit"
                                            onClick={() => handleEditItem(entry.id, item)}
                                            title="Edit"
                                          >
                                            ✏️
                                          </button>
                                          <button
                                            className="btn-action btn-delete"
                                            onClick={() => handleDeleteItem(entry.id, item.id)}
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
        onPageChange={(page) => fetchLvl3(page, searchTerm, rowsPerPage, selectedProject)}
        previousText="← Previous"
        nextText="Next →"
      />

      {/* Parent Lvl3 Modal Form */}
      <ModalForm
        show={showForm}
        onClose={() => {
          setShowForm(false);
          setFormData(initialLvl3State);
          setEditingEntry(null);
        }}
        title={editingEntry ? `Edit Level 3: ${formData.item_name}` : 'Create New Level 3 Item'}
        onSubmit={handleSubmit}
        submitText={editingEntry ? 'Update' : 'Create'}
        cancelText="Cancel"
      >
        <FormSection title="Project Information">
          <FormField
            label="Project ID"
            name="project_id"
            value={formData.project_id}
            onChange={handleChange}
            required
            disabled
            fullWidth
          />
          <FormField
            label="Project Name"
            name="project_name"
            value={formData.project_name}
            onChange={handleChange}
            required
          />
        </FormSection>

        <FormSection title="Item Details">
          <FormField
            label="Item Name"
            name="item_name"
            value={formData.item_name}
            onChange={handleChange}
            required
          />
          <FormField
            label="UOM"
            name="uom"
            value={formData.uom}
            onChange={handleChange}
            required
          />
          <FormField
            label="Total Quantity"
            name="total_quantity"
            type="number"
            value={formData.total_quantity}
            onChange={handleChange}
            required
          />
          <FormField
            label="Total Price"
            name="total_price"
            type="number"
            value={formData.total_price}
            onChange={handleChange}
            required
          />
          <FormField
            label="Service Type"
            name="service_type"
            type="select"
            value={formData.service_type}
            onChange={handleChange}
            required
            placeholder="Select Service Type"
            options={[
              { value: '1', label: 'Software' },
              { value: '2', label: 'Hardware' },
              { value: '3', label: 'Service' }
            ]}
          />
        </FormSection>
      </ModalForm>

      {/* Item Modal Form */}
      <ModalForm
        show={showItemForm}
        onClose={() => {
          setShowItemForm(false);
          setItemFormData(initialItemState);
          setEditingItemData(null);
        }}
        title={editingItemData?.itemId ? `Edit Item: ${itemFormData.item_name}` : 'Add New Item'}
        onSubmit={handleSaveItem}
        submitText="Save Item"
        cancelText="Cancel"
      >
        <FormSection title="Item Information">
          <FormField
            label="Item Name"
            name="item_name"
            value={itemFormData.item_name}
            onChange={handleItemChange}
            required
            disabled={!editingItemData?.itemId}
            fullWidth
          />
          <FormField
            label="Item Details"
            name="item_details"
            value={itemFormData.item_details}
            onChange={handleItemChange}
          />
          <FormField
            label="Vendor Part Number"
            name="vendor_part_number"
            value={itemFormData.vendor_part_number}
            onChange={handleItemChange}
          />
          <FormField
            label="Category"
            name="category"
            value={itemFormData.category}
            onChange={handleItemChange}
          />
          <FormField
            label="UOM"
            name="uom"
            value={itemFormData.uom}
            onChange={handleItemChange}
          />
          <FormField
            label="UPL Line"
            name="upl_line"
            value={itemFormData.upl_line}
            onChange={handleItemChange}
          />
          <FormField
            label="Quantity"
            name="quantity"
            type="number"
            value={itemFormData.quantity}
            onChange={handleItemChange}
            required
          />
          <FormField
            label="Price"
            name="price"
            type="number"
            value={itemFormData.price}
            onChange={handleItemChange}
            required
          />
          <FormField
            label="Service Type"
            name="service_type"
            type="select"
            value={itemFormData.service_type}
            onChange={handleItemChange}
            required
            placeholder="Select Service Type"
            options={[
              { value: '1', label: 'Software' },
              { value: '2', label: 'Hardware' },
              { value: '3', label: 'Service' }
            ]}
          />
        </FormSection>
      </ModalForm>

      {/* Help Modal */}
      <HelpModal
        show={showHelpModal}
        onClose={() => setShowHelpModal(false)}
        title="Level 3 Management - User Guide"
        sections={helpSections}
        closeButtonText="Got it!"
      />
    </div>
  );
}
