import React, { useState, useEffect, useRef } from 'react';
import '../css/Project.css';

const ROWS_PER_PAGE = 100;
const VITE_API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Helper functions to parse and stringify CSV data
const parseCSV = (csvString) => {
  if (!csvString) return [];
  // Handles cases where a cell might contain a comma by splitting only on commas not inside quotes
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
      // Add quotes around fields containing a comma or a quote
      const fieldStr = String(field || '');
      if (fieldStr.includes(',') || fieldStr.includes('"')) {
        return `"${fieldStr.replace(/"/g, '""')}"`;
      }
      return fieldStr;
    }).join(',')
  ).join('\n');
};


export default function BOQGeneration() {
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
  
  // State to hold the editable CSV data as a 2D array ([ [row1-cell1, row1-cell2], [row2-cell1, ...] ])
  const [editableCsvData, setEditableCsvData] = useState([]);

  const fetchAbort = useRef(null);

  const fetchReferences = async (page = 1, search = '') => {
    try {
      if (fetchAbort.current) fetchAbort.current.abort();
      const controller = new AbortController();
      fetchAbort.current = controller;
      setLoading(true);
      setError('');
      const skip = (page - 1) * ROWS_PER_PAGE;
      const params = new URLSearchParams({ skip, limit: ROWS_PER_PAGE });
      if (search.trim()) params.set('search', search.trim());
      
      const res = await fetch(`${VITE_API_URL}/boq/references?${params.toString()}`, { signal: controller.signal });
      if (!res.ok) throw new Error('Failed to fetch references');
      const data = await res.json();
      
      setRows((data.items || []).map(r => ({
        linkedIp: r.linkid,
        interfaceName: r.InterfaceName,
        siteA: r.SiteIPA,
        siteB: r.SiteIPB,
      })));
      setTotal(data.total || 0);
      setCurrentPage(page);
    } catch (err) {
      if (err.name !== 'AbortError') setError(err.message || 'Failed to fetch');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchReferences(1, '');
  }, []);

  const onSearchChange = (e) => {
    const v = e.target.value;
    setSearchTerm(v);
    fetchReferences(1, v);
  };
  
  const handleUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setUploading(true);
    setError('');
    setSuccess('');
    const formData = new FormData();
    formData.append('file', file);
    try {
      const res = await fetch(`${VITE_API_URL}/boq/upload-reference`, { method: 'POST', body: formData });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Upload failed');
      }
      const result = await res.json();
      setSuccess(`Upload successful! ${result.rows_inserted} rows inserted.`);
      fetchReferences(1, searchTerm);
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
      e.target.value = '';
    }
  };

  const handleGenerateRow = async (row) => {
    if (!row || !row.linkedIp) {
      setError('Selected row is invalid');
      return;
    }
    setGenerating(true);
    setError('');
    setLinkedIp(row.linkedIp);

    try {
      const res = await fetch(`${VITE_API_URL}/boq/generate-boq`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(row),
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Failed to generate BOQ');
      }
      const data = await res.json();
      if (data.csv_content) {
        setEditableCsvData(parseCSV(data.csv_content));
        setShowModal(true);
      } else {
        throw new Error('No CSV content received from the server.');
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setGenerating(false);
    }
  };
  
  // Handlers for editing the 2D array data
  const handleCellChange = (rowIndex, cellIndex, value) => {
    const updatedData = editableCsvData.map((row, rIdx) => 
      rIdx === rowIndex ? row.map((cell, cIdx) => (cIdx === cellIndex ? value : cell)) : row
    );
    setEditableCsvData(updatedData);
  };

  const handleAddRow = () => {
    const numColumns = editableCsvData[0]?.length || 1;
    const newRow = Array(numColumns).fill('----------------');
    // Add new row after the header
    const updatedData = [editableCsvData[0], ...editableCsvData.slice(1), newRow];
    setEditableCsvData(updatedData);
  };

  const handleDeleteRow = (rowIndexToDelete) => {
    // Prevent deleting the header row
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

  const totalPages = Math.ceil(total / ROWS_PER_PAGE);
  const csvHeaders = editableCsvData[0] || [];
  const csvBody = editableCsvData.slice(1);

  return (
    <div className="project-container">
      {/* --- Main Page UI (Unchanged) --- */}
      <div className="header-row" style={{ display: 'flex', gap: 16, alignItems: 'center' }}>
        <h2 style={{ margin: 0 }}>BOQ Generation</h2>
        <label className="new-project-btn" style={{ width: 220, cursor: uploading ? 'not-allowed' : 'pointer' }}>
          📤 Upload Reference
          <input type="file" accept=".csv" style={{ display: 'none' }} disabled={uploading} onChange={handleUpload} />
        </label>
      </div>
      <div style={{ marginTop: 12, display: 'flex', gap: 8, alignItems: 'center' }}>
        <input
          type="text"
          placeholder="Type to filter (linkid / interface / site IP)..."
          value={searchTerm}
          onChange={onSearchChange}
          style={{ padding: 8, borderRadius: 6, border: '1px solid #dbe3f4', width: 360 }}
        />
        {searchTerm && (
          <button onClick={() => { setSearchTerm(''); fetchReferences(1, ''); }} style={{ padding: '6px 10px', borderRadius: 6, cursor: 'pointer' }}>
            Clear
          </button>
        )}
      </div>
      {error && <div className="error" style={{ marginTop: 10 }}>{error}</div>}
      {success && <div className="success" style={{ marginTop: 10 }}>{success}</div>}
      {loading && <div style={{ marginTop: 10 }}>Loading references...</div>}
      <div className="project-table-container" style={{ marginTop: 16 }}>
        <table className="project-table">
          <thead>
            <tr>
              <th></th>
              <th>Linked-IP</th>
              <th>Interface Name</th>
              <th>Site-A IP</th>
              <th>Site-B IP</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 && !loading ? (
              <tr><td colSpan={5} style={{ textAlign: 'center', padding: 16 }}>No results</td></tr>
            ) : (
              rows.map((row, idx) => (
                <tr key={idx}>
                  <td style={{ textAlign: 'center' }}>
                    <button
                      title={`Generate BOQ for ${row.linkedIp}`}
                      onClick={() => handleGenerateRow(row)}
                      disabled={generating}
                      style={{ padding: '4px 8px', borderRadius: 6, cursor: generating ? 'not-allowed' : 'pointer', border: '1px solid #ccc' }}
                    >
                      ▼
                    </button>
                  </td>
                  <td>{row.linkedIp}</td>
                  <td>{row.interfaceName}</td>
                  <td>{row.siteA}</td>
                  <td>{row.siteB}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
      {totalPages > 1 && (
        <div className="pagination" style={{ marginTop: 12 }}>
            <button disabled={currentPage === 1} onClick={() => fetchReferences(currentPage - 1, searchTerm)}>Prev</button>
            <span style={{ margin: '0 8px' }}>Page {currentPage} of {totalPages}</span>
            <button disabled={currentPage === totalPages} onClick={() => fetchReferences(currentPage + 1, searchTerm)}>Next</button>
        </div>
      )}

      {/* --- Enhanced Editable Modal (Styled like the new template) --- */}
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
                      // Filter out empty rows that might come from the BE
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
    </div>
  );
}
