
import React, { useEffect, useState } from 'react';
import '../css/Project.css';

const LOGS_PER_PAGE = 5;

export default function Logs({ user }) {
  const [logs, setLogs] = useState([]);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [currentPage, setCurrentPage] = useState(1);

  const VITE_API_URL = import.meta.env.VITE_API_URL;

  useEffect(() => {
    if (user?.role === 'admin') {
      fetchLogs();
    }
  }, [user]);

  const fetchLogs = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await fetch(`${VITE_API_URL}/get-logs`);
      if (!res.ok) throw new Error('Failed to fetch logs');
      const data = await res.json();
      setLogs(data);
    } catch (err) {
      setError(err.message || 'Failed to fetch logs');
    } finally {
      setLoading(false);
    }
  };

  if (user?.role !== 'admin') return null;

  // Pagination logic
  const paginatedLogs = logs.slice((currentPage - 1) * LOGS_PER_PAGE, currentPage * LOGS_PER_PAGE);
  const totalPages = Math.ceil(logs.length / LOGS_PER_PAGE);

  return (
    <div className="logs-container stylish-table" style={{ maxWidth: '700px', margin: '0 auto' }}>
      <h2 style={{ marginBottom: '1rem' }}>System Logs</h2>
      {loading ? (
        <div>Loading logs...</div>
      ) : error ? (
        <div className="error">{error}</div>
      ) : (
        <table className="project-table" style={{ fontSize: '0.95rem', width: '100%' }}>
          <thead>
            <tr>
              <th>Details</th>
              <th>User</th>
              <th>Timestamp</th>
            </tr>
          </thead>
          <tbody>
            {paginatedLogs.length === 0 ? (
              <tr><td colSpan={3} style={{ textAlign: 'center' }}>No logs found.</td></tr>
            ) : (
              paginatedLogs.map((log, idx) => (
                <tr key={idx}>
                  <td>{log.details || log.log || log.action}</td>
                  <td>{log.user}</td>
                  <td>{log.timestamp}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      )}
      {totalPages > 1 && (
        <div className="pagination" style={{ marginTop: '1rem', justifyContent: 'center', display: 'flex' }}>
          {Array.from({ length: totalPages }, (_, i) => (
            <button
              key={i}
              className={i + 1 === currentPage ? 'active-page' : ''}
              onClick={() => setCurrentPage(i + 1)}
              style={{ minWidth: '32px', margin: '0 2px' }}
            >
              {i + 1}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
