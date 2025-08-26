import React, { useState, useEffect, useRef } from 'react';
import '../css/Project.css';

const ROWS_PER_PAGE = 100;
const VITE_API_URL = import.meta.env.VITE_API_URL;

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
  const [generateResult, setGenerateResult] = useState([]);
  const [generating, setGenerating] = useState(false);
  const [showModal, setShowModal] = useState(false);

  // abort previous fetches to avoid race conditions when typing fast
  const fetchAbort = useRef(null);

  // Fetch reference rows (server-side filtering + pagination)
  const fetchReferences = async (page = 1, search = '') => {
    try {
      // cancel previous in-flight
      if (fetchAbort.current) fetchAbort.current.abort();
      const controller = new AbortController();
      fetchAbort.current = controller;

      setLoading(true);
      setError('');
      const skip = (page - 1) * ROWS_PER_PAGE;

      const params = new URLSearchParams();
      params.set('skip', String(skip));
      params.set('limit', String(ROWS_PER_PAGE));
      if (search.trim()) params.set('search', search.trim());

      const res = await fetch(
        `${VITE_API_URL}/boq/references?${params.toString()}`,
        { signal: controller.signal }
      );
      if (!res.ok) throw new Error('Failed to fetch references');
      const data = await res.json();

      setRows(
        (data.items || []).map((r) => ({
          linkedIp: r.linkid,
          interfaceName: r.InterfaceName,
          siteA: r.SiteIPA,
          siteB: r.SiteIPB,
        }))
      );
      setTotal(data.total || 0);
      setCurrentPage(page);
    } catch (err) {
      if (err.name !== 'AbortError') setError(err.message || 'Failed to fetch references');
    } finally {
      setLoading(false);
    }
  };

  // Initial load
  useEffect(() => {
    fetchReferences(1, '');
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Live filter: fetch page 1 on every keystroke
  const onSearchChange = (e) => {
    const v = e.target.value;
    setSearchTerm(v);
    fetchReferences(1, v); // always reset to first page
  };

  // CSV upload
  const handleUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setUploading(true);
    setError('');
    setSuccess('');
    const formData = new FormData();
    formData.append('file', file);
    try {
      const res = await fetch(`${VITE_API_URL}/boq/upload-reference`, {
        method: 'POST',
        body: formData,
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Failed to upload reference CSV');
      }
      const result = await res.json();
      setSuccess(`Upload successful! ${result.rows_inserted} rows inserted.`);
      // reload first page with current filter
      fetchReferences(1, searchTerm);
    } catch (err) {
      setError(err.message);
    } finally {
      setUploading(false);
      e.target.value = '';
    }
  };

  // Generate BOQ from manual linkedIp input (unchanged)
 
  // Generate BOQ for a specific table row (arrow button)
 const handleGenerateRow = async (row) => {
  if (!row || !row.linkedIp) {
    setError('Selected row is invalid');
    return;
  }
  setGenerating(true);
  setError('');
  setGenerateResult([]);
  setLinkedIp(row.linkedIp);

  try {
    const res = await fetch(`${VITE_API_URL}/boq/generate-boq`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(row), // ✅ send full row: { linkedIp, interfaceName, siteA, siteB }
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to generate BOQ for row');
    }
    const data = await res.json();
    setGenerateResult(data.matches || []);
    setShowModal(true);
  } catch (err) {
    setError(err.message);
  } finally {
    setGenerating(false);
  }
};


  // Flatten inventory for modal/CSV
  const flattenedInventory = generateResult.flatMap((match) => {
    const out = [];
    (match.inventory_site_a_matches || []).forEach((inv) => {
      out.push({
        linkedIp: match.reference.linkid,
        interface: match.reference.InterfaceName,
        site: inv.site_name,
        slot: inv.slot_id,
        port: inv.port_id,
        part_no: inv.part_no,
        sw_no: inv.software_no,
        serial_no: inv.serial_no,
      });
    });
    (match.inventory_site_b_matches || []).forEach((inv) => {
      out.push({
        linkedIp: match.reference.linkid,
        interface: match.reference.InterfaceName,
        site: inv.site_name,
        slot: inv.slot_id,
        port: inv.port_id,
        part_no: inv.part_no,
        sw_no: inv.software_no,
        serial_no: inv.serial_no,
      });
    });
    return out;
  });

  const downloadCSV = () => {
    if (!flattenedInventory.length) return;
    const header = ['Linked-IP', 'Interface', 'Site', 'Slot', 'Port', 'Part Number', 'SW Number', 'Serial Number'];
    const rowsCsv = flattenedInventory.map((r) => [
      r.linkedIp, r.interface, r.site, r.slot, r.port, r.part_no, r.sw_no, r.serial_no,
    ]);
    const csvContent = [header, ...rowsCsv].map((e) => e.join(',')).join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `BOQ_${linkedIp || 'export'}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const totalPages = Math.ceil(total / ROWS_PER_PAGE);

  return (
    <div className="project-container">
      {/* Header & Upload */}
      <div className="header-row" style={{ display: 'flex', gap: 16, alignItems: 'center' }}>
        <h2 style={{ margin: 0 }}>BOQ Generation</h2>
        <label className="new-project-btn" style={{ width: 220, cursor: uploading ? 'not-allowed' : 'pointer' }}>
          📤 Upload Reference
          <input
            type="file"
            accept=".csv"
            style={{ display: 'none' }}
            disabled={uploading}
            onChange={handleUpload}
          />
        </label>
      </div>

      {/* Live server-side search */}
      <div style={{ marginTop: 12, display: 'flex', gap: 8, alignItems: 'center' }}>
        <input
          type="text"
          placeholder="Type to filter (linkid / interface / site IP)..."
          value={searchTerm}
          onChange={onSearchChange}
          style={{ padding: 8, borderRadius: 6, border: '1px solid #dbe3f4', width: 360 }}
        />
        {searchTerm && (
          <button
            onClick={() => { setSearchTerm(''); fetchReferences(1, ''); }}
            style={{ padding: '6px 10px', borderRadius: 6, cursor: 'pointer' }}
          >
            Clear
          </button>
        )}
      </div>

      {/* Messages */}
      {error && <div className="error" style={{ marginTop: 10 }}>{error}</div>}
      {success && <div className="success" style={{ marginTop: 10 }}>{success}</div>}
      {loading && <div style={{ marginTop: 10 }}>Loading references...</div>}

      {/* References Table */}
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
              <tr>
                <td colSpan={5} style={{ textAlign: 'center', padding: 16 }}>No results</td>
              </tr>
            ) : (
              rows.map((row, idx) => (
                <tr key={idx}>
                  <td style={{ textAlign: 'center' }}>
                    <button
                      title={`Generate BOQ for ${row.linkedIp}`}
                      aria-label={`Generate BOQ for ${row.linkedIp}`}
                      onClick={() => handleGenerateRow(row)}
                      disabled={generating}
                      style={{
                        padding: '4px 8px',
                        borderRadius: 6,
                        cursor: generating ? 'not-allowed' : 'pointer',
                        border: '1px solid #dbe3f4',
                        background: '#fff',
                      }}
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

      {/* Pagination (keeps current filter) */}
      {totalPages > 1 && (
        <div className="pagination" style={{ marginTop: 12 }}>
          <button disabled={currentPage === 1} onClick={() => fetchReferences(currentPage - 1, searchTerm)}>Prev</button>
          <span style={{ margin: '0 8px' }}>Page {currentPage} of {totalPages}</span>
          <button disabled={currentPage === totalPages} onClick={() => fetchReferences(currentPage + 1, searchTerm)}>Next</button>
        </div>
      )}

      {/* Modal for Generated BOQ */}
      {showModal && (
        <div
          className="modal-overlay"
          style={{
            position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
            background: 'rgba(0,0,0,0.5)',
            display: 'flex', justifyContent: 'center', alignItems: 'center',
            zIndex: 1000,
          }}
        >
          <div style={{ background: '#fff', padding: 24, borderRadius: 8, maxWidth: '90%', maxHeight: '80%', overflow: 'auto' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12 }}>
              <h3>Generated BOQ for {linkedIp}</h3>
              <button onClick={() => setShowModal(false)} style={{ fontSize: 18, cursor: 'pointer' }}>✖</button>
            </div>
            <button onClick={downloadCSV} style={{ marginBottom: 12, padding: '6px 10px', borderRadius: 6, cursor: 'pointer' }}>
              ⬇ Download CSV
            </button>
            <table className="project-table" style={{ width: '100%' }}>
              <thead>
                <tr>
                  <th>Linked-IP</th>
                  <th>Interface</th>
                  <th>Site</th>
                  <th>Slot</th>
                  <th>Port</th>
                  <th>Part Number</th>
                  <th>SW Number</th>
                  <th>Serial Number</th>
                </tr>
              </thead>
              <tbody>
                {flattenedInventory.map((row, idx) => (
                  <tr key={idx}>
                    <td>{row.linkedIp}</td>
                    <td>{row.interface}</td>
                    <td>{row.site}</td>
                    <td>{row.slot}</td>
                    <td>{row.port}</td>
                    <td>{row.part_no}</td>
                    <td>{row.sw_no}</td>
                    <td>{row.serial_no}</td>
                  </tr>
                ))}
                {flattenedInventory.length === 0 && (
                  <tr>
                    <td colSpan={8} style={{ textAlign: 'center', padding: 12 }}>No inventory matches found for this reference</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
