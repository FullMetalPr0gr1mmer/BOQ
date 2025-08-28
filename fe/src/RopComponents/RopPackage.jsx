import { useEffect, useState } from "react";
import DatePicker from "react-datepicker";
import "react-datepicker/dist/react-datepicker.css";
import { useLocation } from "react-router-dom";
import "../css/RopPackage.css";
import moment from "moment";

const VITE_API_URL = import.meta.env.VITE_API_URL;
const MONTH_WIDTH = 60; // width of 1 month column in px

export default function RopPackage() {
  const location = useLocation();
  const projectState = location.state;

  const [packages, setPackages] = useState([]);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [expandedRows, setExpandedRows] = useState({});
  const [timeline, setTimeline] = useState([]);
  const [editingQuantities, setEditingQuantities] = useState({});
  const [savingPkgId, setSavingPkgId] = useState(null);
  const [editingQuantityCol, setEditingQuantityCol] = useState({});
  const [savingQuantityColPkgId, setSavingQuantityColPkgId] = useState(null);
  // Check if any monthly quantity changed for a package
  const isMonthlyChanged = (pkg, monthlyQuantities) => {
    const edits = editingMonthly[pkg.id] || {};
    return Object.keys(edits).some(idx => String(edits[idx]) !== String(monthlyQuantities[idx]));
  };

  // Check if quantity column changed for a package
  const isQuantityColChanged = (pkg) => {
    return editingQuantityCol[pkg.id] !== undefined && String(editingQuantityCol[pkg.id]) !== String(pkg.quantity);
  };
  const handleQuantityColChange = (pkgId, value) => {
    setEditingQuantityCol(prev => ({
      ...prev,
      [pkgId]: value
    }));
  };

  const handleSaveQuantityCol = async (pkg) => {
    setSavingQuantityColPkgId(pkg.id);
    try {
      const res = await fetch(`${VITE_API_URL}/rop-package/update/${pkg.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ quantity: Number(editingQuantityCol[pkg.id]) })
      });
      if (!res.ok) throw new Error("Failed to save quantity");
      setSuccess("Quantity updated!");
      setEditingQuantityCol(prev => ({ ...prev, [pkg.id]: undefined }));
      fetchPackages();
    } catch (err) {
      setError(err.message);
    } finally {
      setSavingQuantityColPkgId(null);
    }
  };
  const [editingMonthly, setEditingMonthly] = useState({});
  const [savingMonthlyPkgId, setSavingMonthlyPkgId] = useState(null);

  useEffect(() => {
    fetchPackages();
  }, []);

  useEffect(() => {
    if (packages.length > 0) {
      calculateTimeline();
    }
  }, [packages]);

  const fetchPackages = async () => {
    try {
      const url = VITE_API_URL + "/rop-package/";
      const res = await fetch(url);
      if (!res.ok) throw new Error("Failed to fetch packages");
      const data = await res.json();
      setPackages(data);
    } catch (err) {
      setError(err.message);
    }
  };

  const calculateTimeline = () => {
    if (packages.length === 0) {
      setTimeline([]);
      return;
    }

    const allStartDates = packages.map((p) => moment(p.start_date));
    const allEndDates = packages.map((p) => moment(p.end_date));

    const minDate = moment.min(allStartDates.filter((d) => d.isValid()));
    const maxDate = moment.max(allEndDates.filter((d) => d.isValid()));

    if (!minDate.isValid() || !maxDate.isValid()) {
      setTimeline([]);
      return;
    }

    const months = [];
    let currentDate = minDate.clone().startOf("month");
    const endDate = maxDate.clone().endOf("month");

    while (currentDate.isSameOrBefore(endDate)) {
      months.push(currentDate.clone());
      currentDate.add(1, "month");
    }
    setTimeline(months);
  };

  const handleUpdatePackage = async (packageId, updatedData) => {
    try {
      const res = await fetch(`${VITE_API_URL}/rop-package/update/${packageId}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(updatedData),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Failed to update package");
      }

      setSuccess("Package updated successfully!");
      fetchPackages();
    } catch (err) {
      setError(err.message);
    }
  };

  const getBarProperties = (pkg) => {
    const barStart = moment(pkg.start_date);
    const barEnd = moment(pkg.end_date);
    const timelineStart = timeline[0];

    if (!barStart.isValid() || !barEnd.isValid() || !timelineStart) {
      return { left: 0, width: 0 };
    }

    const totalDays = moment(timeline[timeline.length - 1])
      .endOf("month")
      .diff(timelineStart, "days");

    const startDayOffset = barStart.diff(timelineStart, "days");
    const barDays = barEnd.diff(barStart, "days");

    const left = (startDayOffset / totalDays) * (timeline.length * MONTH_WIDTH);
    const width = (barDays / totalDays) * (timeline.length * MONTH_WIDTH);

    return { left, width };
  };

  const getMonthlyQuantities = (pkg) => {
    if (!pkg.quantity || !pkg.start_date || !pkg.end_date || timeline.length === 0) {
      return [];
    }

    const quantities = new Array(timeline.length).fill(null);
    const pkgStart = moment(pkg.start_date);
    const pkgEnd = moment(pkg.end_date);

    let totalQuantity = pkg.quantity;
    let monthsWithQuantity = 0;

    for (let i = 0; i < timeline.length; i++) {
      const monthStart = timeline[i].clone().startOf("month");
      const monthEnd = timeline[i].clone().endOf("month");

      if (pkgStart.isSameOrBefore(monthEnd) && pkgEnd.isSameOrAfter(monthStart)) {
        monthsWithQuantity++;
      }
    }

    const baseQuantity = monthsWithQuantity > 0 ? Math.floor(totalQuantity / monthsWithQuantity) : 0;
    let remainder = monthsWithQuantity > 0 ? totalQuantity % monthsWithQuantity : 0;

    for (let i = 0; i < timeline.length; i++) {
      const monthStart = timeline[i].clone().startOf("month");
      const monthEnd = timeline[i].clone().endOf("month");

      if (pkgStart.isSameOrBefore(monthEnd) && pkgEnd.isSameOrAfter(monthStart)) {
        let monthlyQty = baseQuantity;
        if (remainder > 0) {
          monthlyQty += 1;
          remainder--;
        }
        quantities[i] = monthlyQty;
      }
    }
    return quantities;
  };

  const toggleRow = (id) => {
    setExpandedRows((prev) => ({
      ...prev,
      [id]: !prev[id],
    }));
  };

  const handleQuantityChange = (pkgId, itemIdx, value) => {
    setEditingQuantities(prev => ({
      ...prev,
      [pkgId]: {
        ...(prev[pkgId] || {}),
        [itemIdx]: value
      }
    }));
  };

  const handleSaveQuantities = async (pkg) => {
    setSavingPkgId(pkg.id);
    const updatedLvl1 = pkg.lvl1_items.map((item, idx) => ({
      id: item.id,
      quantity: Number(editingQuantities[pkg.id]?.[idx] ?? item.quantity)
    }));
    try {
      const res = await fetch(`${VITE_API_URL}/rop-package/update/${pkg.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ lvl1_ids: updatedLvl1 })
      });
      if (!res.ok) throw new Error("Failed to save quantities");
      setSuccess("Quantities updated!");
      setEditingQuantities(prev => ({ ...prev, [pkg.id]: {} }));
      fetchPackages();
    } catch (err) {
      setError(err.message);
    } finally {
      setSavingPkgId(null);
    }
  };

  const handleMonthlyChange = (pkgId, idx, value) => {
    setEditingMonthly(prev => ({
      ...prev,
      [pkgId]: {
        ...(prev[pkgId] || {}),
        [idx]: value
      }
    }));
  };

  const handleSaveMonthly = async (pkg, timeline) => {
    setSavingMonthlyPkgId(pkg.id);
    const monthlyArr = timeline.map((_, idx) => Number(editingMonthly[pkg.id]?.[idx] ?? getMonthlyQuantities(pkg)[idx] ?? 0));
    const totalQty = monthlyArr.reduce((sum, v) => sum + (Number(v) || 0), 0);
    try {
      const res = await fetch(`${VITE_API_URL}/rop-package/update/${pkg.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ quantity: totalQty })
      });
      if (!res.ok) throw new Error("Failed to save monthly quantities");
      setSuccess("Monthly quantities updated!");
      setEditingMonthly(prev => ({ ...prev, [pkg.id]: {} }));
      fetchPackages();
    } catch (err) {
      setError(err.message);
    } finally {
      setSavingMonthlyPkgId(null);
    }
  };

  // Dragging and resizing
  const handleBarDrag = (e, pkg, type) => {
    e.preventDefault();
    const timelineStart = timeline[0];
    let updatedPkg = { ...pkg };

    const onMouseMove = (moveEvent) => {
      const tableRect = e.target.closest(".gantt-chart-cell").getBoundingClientRect();
      const offsetX = moveEvent.clientX - tableRect.left;
      const totalDays = moment(timeline[timeline.length - 1]).endOf("month").diff(timelineStart, "days");
      const days = Math.round((offsetX / (timeline.length * MONTH_WIDTH)) * totalDays);
      const newDate = timelineStart.clone().add(days, "days");

      if (type === "move") {
        const duration = moment(pkg.end_date).diff(moment(pkg.start_date), "days");
        updatedPkg.start_date = newDate.format("YYYY-MM-DD");
        updatedPkg.end_date = newDate.clone().add(duration, "days").format("YYYY-MM-DD");
      } else if (type === "start") {
        // Prevent end date before start date
        if (moment(pkg.end_date).isAfter(newDate)) {
          updatedPkg.start_date = newDate.format("YYYY-MM-DD");
        }
      } else if (type === "end") {
        // Prevent start date after end date
        if (moment(pkg.start_date).isBefore(newDate)) {
          updatedPkg.end_date = newDate.format("YYYY-MM-DD");
        }
      }

      setPackages((prev) => prev.map((p) => (p.id === pkg.id ? updatedPkg : p)));
    };

    const onMouseUp = () => {
      document.removeEventListener("mousemove", onMouseMove);
      document.removeEventListener("mouseup", onMouseUp);
      // Persist the updated start/end dates to backend
      handleUpdatePackage(pkg.id, updatedPkg);
    };

    document.addEventListener("mousemove", onMouseMove);
    document.addEventListener("mouseup", onMouseUp);
  };

  return (
    <div className="dashboard-container">
      <div className="dashboard-header">
        <div>
          <h1 className="dashboard-title">ROP Packages</h1>
          <p className="dashboard-subtitle">Gantt Chart and Package Management</p>
        </div>
      </div>

      {error && <div className="dashboard-alert dashboard-alert-error">⚠️ {error}</div>}
      {success && <div className="dashboard-alert dashboard-alert-success">✅ {success}</div>}

      <div className="dashboard-content-section">
        <div className="dashboard-section-header">📋 Package Timeline</div>

        <div className="gantt-table-container">
          <table className="gantt-table">
            <thead>
              <tr>
                <th style={{ width: "150px" }}>Package Name</th>
                <th style={{ width: "100px" }}>Start Date</th>
                <th style={{ width: "100px" }}>End Date</th>
                <th>Quantity</th>
                <th className="gantt-header-cell">
                  <div
                    className="timeline-header"
                    style={{
                      display: 'grid',
                      gridTemplateColumns: `repeat(${timeline.length}, 1fr)`,
                      alignItems: 'center',
                      minWidth: '400px',
                      position: 'relative',
                    }}
                  >
                    {timeline.map((month, index) => (
                      <span key={index} className="timeline-month-header" style={{ textAlign: 'center', fontWeight: 'bold', position: 'relative' }}>
                        {month.format("MMM YY")}
                        {index < timeline.length - 1 && (
                          <span style={{
                            position: 'absolute',
                            right: 0,
                            top: '10%',
                            height: '80%',
                            width: '1px',
                            background: '#ccc',
                            zIndex: 1,
                          }} />
                        )}
                      </span>
                    ))}
                  </div>
                </th>
              </tr>
            </thead>
            <tbody>
              {packages.map((pkg) => {
                const barProps = getBarProperties(pkg);
                const monthlyQuantities = getMonthlyQuantities(pkg);
                return (
                  <>
                    <tr key={pkg.id}>
                      <td>
                        <div className="package-name-cell">
                          <button className="expand-btn" onClick={() => toggleRow(pkg.id)}>
                            {expandedRows[pkg.id] ? "▼" : "▶"}
                          </button>
                          <span>{pkg.package_name}</span>
                        </div>
                      </td>
                      <td>
                          <DatePicker
                            selected={pkg.start_date ? moment(pkg.start_date).toDate() : null}
                            onChange={(date) =>
                              handleUpdatePackage(pkg.id, { ...pkg, start_date: moment(date).format("YYYY-MM-DD") })
                            }
                            dateFormat="yyyy-MM-dd"
                            customInput={<input style={{ width: '100px' }} readOnly />}
                            calendarIcon
                          />
                      </td>
                      <td>
                          <DatePicker
                            selected={pkg.end_date ? moment(pkg.end_date).toDate() : null}
                            onChange={(date) =>
                              handleUpdatePackage(pkg.id, { ...pkg, end_date: moment(date).format("YYYY-MM-DD") })
                            }
                            dateFormat="yyyy-MM-dd"
                            customInput={<input style={{ width: '100px' }} readOnly />}
                            calendarIcon
                          />
                      </td>
                      <td style={{ minWidth: 120 }}>
                        <input
                          type="number"
                          value={editingQuantityCol[pkg.id] !== undefined ? editingQuantityCol[pkg.id] : pkg.quantity}
                          min={0}
                          style={{ width: 80, padding: '2px 6px', borderRadius: 4, border: '1px solid #ccc' }}
                          onChange={e => handleQuantityColChange(pkg.id, e.target.value)}
                          disabled={savingQuantityColPkgId === pkg.id}
                        />
                      </td>
                    {isQuantityColChanged(pkg) && (
                      <tr>
                        <td colSpan={5}>
                          <button
                            className="stylish-btn"
                            style={{ marginTop: 8, float: 'left' }}
                            onClick={() => handleSaveQuantityCol(pkg)}
                            disabled={savingQuantityColPkgId === pkg.id}
                          >
                            {savingQuantityColPkgId === pkg.id ? 'Saving...' : 'Save Quantity'}
                          </button>
                        </td>
                      </tr>
                    )}
                      <td className="gantt-chart-cell">
                        <div
                          className="gantt-bar-container"
                          style={{
                            position: 'relative',
                            display: 'grid',
                            gridTemplateColumns: `repeat(${timeline.length}, 1fr)`,
                            minWidth: '400px',
                            alignItems: 'center',
                          }}
                        >
                          {pkg.start_date && pkg.end_date && (
                            <div
                              className="gantt-bar"
                              style={{
                                position: 'absolute',
                                left: `${barProps.left}px`,
                                width: `${barProps.width}px`,
                                top: '8px',
                                height: '24px',
                              }}
                            >
                              {/* Left pointer: affects start date only */}
                              <div
                                className="resize-pointer left"
                                style={{ position: 'absolute', left: '-8px', top: '50%', transform: 'translateY(-50%)', width: '16px', height: '24px', cursor: 'ew-resize', background: '#388e3c', borderRadius: '50%', border: '2px solid #fff', zIndex: 2 }}
                                title="Drag to change start date"
                                onMouseDown={(e) => handleBarDrag(e, pkg, "start")}
                              ></div>
                              {/* Bar content */}
                              <span className="gantt-quantity-label" style={{ position: 'absolute', left: '50%', top: '50%', transform: 'translate(-50%, -50%)', zIndex: 1 }}>{pkg.quantity}</span>
                              {/* Right pointer: affects end date only */}
                              <div
                                className="resize-pointer right"
                                style={{ position: 'absolute', right: '-8px', top: '50%', transform: 'translateY(-50%)', width: '16px', height: '24px', cursor: 'ew-resize', background: '#1976d2', borderRadius: '50%', border: '2px solid #fff', zIndex: 2 }}
                                title="Drag to change end date"
                                onMouseDown={(e) => handleBarDrag(e, pkg, "end")}
                              ></div>
                            </div>
                          )}
                        </div>
                        <div
                          className="monthly-quantities-row"
                          style={{
                            display: 'grid',
                            gridTemplateColumns: `repeat(${timeline.length}, 1fr)`,
                            minWidth: '400px',
                            alignItems: 'center',
                            position: 'relative',
                          }}
                        >
                          {monthlyQuantities.map((qty, index) => (
                            <div key={index} className="monthly-quantity-cell" style={{ textAlign: 'center', position: 'relative' }}>
                              <input
                                type="number"
                                value={editingMonthly[pkg.id]?.[index] ?? qty ?? ''}
                                min={0}
                                style={{ width: 60, padding: '2px 6px', borderRadius: 4, border: '1px solid #ccc' }}
                                onChange={e => handleMonthlyChange(pkg.id, index, e.target.value)}
                                disabled={savingMonthlyPkgId === pkg.id}
                              />
                              {index < timeline.length - 1 && (
                                <span style={{
                                  position: 'absolute',
                                  right: 0,
                                  top: '10%',
                                  height: '80%',
                                  width: '1px',
                                  background: '#eee',
                                  zIndex: 1,
                                }} />
                              )}
                            </div>
                          ))}
                        </div>
                        {isMonthlyChanged(pkg, monthlyQuantities) && (
                          <button
                            className="stylish-btn"
                            style={{ marginTop: 8, float: 'right' }}
                            onClick={() => handleSaveMonthly(pkg, timeline)}
                            disabled={savingMonthlyPkgId === pkg.id}
                          >
                            {savingMonthlyPkgId === pkg.id ? 'Saving...' : 'Save Monthly Quantities'}
                          </button>
                        )}
                      </td>
                    </tr>
                    {expandedRows[pkg.id] && (
                      <tr className="expanded-row">
                        <td colSpan="5">
                          <div className="sub-table-container">
                            <h4>ROP Lvl1 Items</h4>
                            <table className="sub-table" style={{ width: 'fit-content', minWidth: 0, maxWidth: 'none' }}>
                              <thead>
                                <tr>
                                  <th style={{ width: 'auto', whiteSpace: 'nowrap' }}>Item Name</th>
                                  <th style={{ width: 'auto', whiteSpace: 'nowrap' }}>Quantity</th>
                                  <th style={{ width: '32px' }}></th>
                                </tr>
                              </thead>
                              <tbody>
                                {pkg.lvl1_items.length > 0 ? (
                                  pkg.lvl1_items.map((item, index) => (
                                    <tr key={index}>
                                      <td style={{ width: 'auto', whiteSpace: 'nowrap', fontSize: '0.95em' }}>{item.name || item}</td>
                                      <td style={{ width: 'auto', whiteSpace: 'nowrap' }}>
                                        <input
                                          type="number"
                                          value={editingQuantities[pkg.id]?.[index] ?? item.quantity ?? ''}
                                          min={0}
                                          style={{ width: 'auto', minWidth: 24, padding: '1px 2px', borderRadius: 3, border: '1px solid #ccc', fontSize: '0.95em' }}
                                          onChange={e => handleQuantityChange(pkg.id, index, e.target.value)}
                                          disabled={savingPkgId === pkg.id}
                                        />
                                      </td>
                                    </tr>
                                  ))
                                ) : (
                                  <tr>
                                    <td colSpan={2}>No Lvl1 items found for this package.</td>
                                  </tr>
                                )}
                              </tbody>
                            </table>
                            <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'flex-start', marginBottom: 8 }}>
                              <button
                                className="stylish-btn"
                                style={{ marginTop: 0 }}
                                onClick={() => handleSaveQuantities(pkg)}
                                disabled={savingPkgId === pkg.id}
                              >
                                {savingPkgId === pkg.id ? 'Saving...' : 'Save Quantities'}
                              </button>
                            </div>
                          </div>
                        </td>
                      </tr>
                    )}
                  </>
                );
              })}
              {packages.length === 0 && (
                <tr>
                  <td colSpan="5" className="empty-state">
                    No ROP Packages found.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
