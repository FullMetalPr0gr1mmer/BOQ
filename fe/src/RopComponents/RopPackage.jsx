import { useEffect, useState } from "react";
import DatePicker from "react-datepicker";
import "react-datepicker/dist/react-datepicker.css";
import { useLocation } from "react-router-dom";
import "../css/RopPackage.css";
import moment from "moment";

const VITE_API_URL = import.meta.env.VITE_API_URL;
const MONTH_WIDTH = 60; // width of 1 month column in px

const getAuthHeaders = () => {
  const token = localStorage.getItem('token');
  if (token) {
    return {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    };
  }
  return { 'Content-Type': 'application/json' };
};

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
  const [editingMonthly, setEditingMonthly] = useState({});
  const [savingMonthlyPkgId, setSavingMonthlyPkgId] = useState(null);

  // Utility function to check if a date/month is in the past
  const isDateInPast = (date) => {
    return moment(date).isBefore(moment(), 'month');
  };

  const isMonthInPast = (year, month) => {
    return moment({ year, month: month - 1 }).isBefore(moment(), 'month');
  };

  const isMonthlyChanged = (pkg) => {
    const edits = editingMonthly[pkg.id] || {};
    return Object.keys(edits).some(monthKey => {
      const [year, month] = monthKey.split('-').map(Number);
      const editedValue = edits[monthKey];
      const originalDistribution = pkg.monthly_distributions?.find(d => d.year === year && d.month === month);
      const originalValue = originalDistribution?.quantity || 0;
      return String(editedValue) !== String(originalValue);
    });
  };

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
      const newQuantity = Number(editingQuantityCol[pkg.id]);
      const res = await fetch(`${VITE_API_URL}/rop-package/update/${pkg.id}`, {
        method: "PUT",
        headers: getAuthHeaders(),
        body: JSON.stringify({ quantity: newQuantity })
      });
      if (!res.ok) throw new Error("Failed to save quantity");
      setSuccess("Quantity updated! Monthly distributions may need adjustment.");
      setEditingQuantityCol(prev => ({ ...prev, [pkg.id]: undefined }));
      fetchPackages();
    } catch (err) {
      setError(err.message);
    } finally {
      setSavingQuantityColPkgId(null);
    }
  };

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
      const res = await fetch(url, { headers: getAuthHeaders() });
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

    const allPossibleEndDates = [];
    packages.forEach(p => {
      const endDate = moment(p.end_date);
      if (endDate.isValid()) {
        allPossibleEndDates.push(endDate);
        const leadTimeMonths = p.lead_time ? Math.floor(p.lead_time / 30) : 0;
        if (leadTimeMonths > 0) {
          allPossibleEndDates.push(endDate.clone().add(leadTimeMonths, 'months'));
        }
      }
    });

    const minDate = moment.min(allStartDates.filter((d) => d.isValid()));
    const maxDate = allPossibleEndDates.length > 0 ? moment.max(allPossibleEndDates.filter((d) => d && d.isValid())) : null;

    if (!minDate.isValid() || !maxDate || !maxDate.isValid()) {
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
        headers: getAuthHeaders(),
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

  // FIXED: Auto-distribute functionality with added safety filter
  const handleAutoDistributeMonthly = async (pkg) => {
    const packageStart = moment(pkg.start_date);
    const packageEnd = moment(pkg.end_date);
    
    const distributionsMap = new Map();
    pkg.monthly_distributions?.forEach(d => {
        distributionsMap.set(`${d.year}-${d.month}`, d.quantity);
    });

    let pastQuantity = 0;
    const futureMonthsForDistribution = [];

    timeline.forEach(month => {
        if (month.isBetween(packageStart, packageEnd, 'month', '[]')) {
            const year = month.year();
            const monthNum = month.month() + 1;
            const monthKey = `${year}-${monthNum}`;

            if (isMonthInPast(year, monthNum)) {
                pastQuantity += distributionsMap.get(monthKey) || 0;
            } else {
                futureMonthsForDistribution.push({ year, month: monthNum });
            }
        }
    });

    const remainingQuantity = pkg.quantity - pastQuantity;
    const futureMonthsCount = futureMonthsForDistribution.length;

    if (remainingQuantity < 0) {
        setError("Cannot auto-distribute: Past quantities exceed total package quantity.");
        return;
    }

    if (futureMonthsCount > 0) {
        const baseQty = Math.floor(remainingQuantity / futureMonthsCount);
        const remainder = remainingQuantity % futureMonthsCount;
        
        futureMonthsForDistribution.forEach((dist, index) => {
            const monthKey = `${dist.year}-${dist.month}`;
            const newQuantity = baseQty + (index < remainder ? 1 : 0);
            distributionsMap.set(monthKey, newQuantity);
        });
    }

    // Convert map back to the format required by the API
    const finalDistributions = [];
    distributionsMap.forEach((quantity, key) => {
        const [year, month] = key.split('-').map(Number);
        const monthMoment = moment({ year, month: month - 1 });

        // **FIX**: Only include distributions that are within the package's date range
        if (monthMoment.isBetween(packageStart, packageEnd, 'month', '[]')) {
            finalDistributions.push({ year, month, quantity });
        }
    });

    try {
        const res = await fetch(`${VITE_API_URL}/rop-package/update/${pkg.id}`, {
            method: "PUT",
            headers: getAuthHeaders(),
            body: JSON.stringify({ monthly_distributions: finalDistributions }),
        });

        if (!res.ok) {
            const err = await res.json();
            throw new Error(err.detail || "Failed to auto-distribute quantities");
        }

        setSuccess("Future monthly quantities auto-distributed successfully!");
        fetchPackages();
    } catch (err) {
        setError(err.message);
    }
  };

  const handleDeletePackage = async (packageId) => {
    if (!window.confirm("Are you sure you want to delete this package?")) {
      return;
    }
    try {
      const res = await fetch(`${VITE_API_URL}/rop-package/${packageId}`, {
        method: "DELETE",
        headers: getAuthHeaders(),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || "Failed to delete package");
      }
      setSuccess("Package deleted successfully!");
      fetchPackages();
    } catch (err) {
      setError(err.message);
    }
  };

  const getBarProperties = (pkg) => {
    const barStart = moment(pkg.start_date);
    const barEnd = moment(pkg.end_date);
    const timelineStart = timeline[0];
    const timelineEnd = timeline[timeline.length - 1];

    if (!barStart.isValid() || !barEnd.isValid() || !timelineStart || !timelineEnd) {
      return { left: 0, width: 0 };
    }

    const totalTimelineWidth = timeline.length * MONTH_WIDTH;
    
    let startMonthIndex = -1;
    let endMonthIndex = -1;
    
    for (let i = 0; i < timeline.length; i++) {
      const monthStart = timeline[i].clone().startOf('month');
      const monthEnd = timeline[i].clone().endOf('month');
      
      if (startMonthIndex === -1 && barStart.isSameOrAfter(monthStart) && barStart.isSameOrBefore(monthEnd)) {
        startMonthIndex = i;
        const daysInMonth = monthEnd.diff(monthStart, 'days') + 1;
        const dayInMonth = barStart.diff(monthStart, 'days');
        const monthProgress = dayInMonth / daysInMonth;
        startMonthIndex = i + monthProgress;
      }
      
      if (barEnd.isSameOrAfter(monthStart) && barEnd.isSameOrBefore(monthEnd)) {
        const daysInMonth = monthEnd.diff(monthStart, 'days') + 1;
        const dayInMonth = barEnd.diff(monthStart, 'days');
        const monthProgress = dayInMonth / daysInMonth;
        endMonthIndex = i + monthProgress;
      }
    }
    
    if (startMonthIndex === -1) {
      if (barStart.isBefore(timelineStart)) {
        startMonthIndex = 0;
      } else if (barStart.isAfter(timelineEnd.clone().endOf('month'))) {
        startMonthIndex = timeline.length;
      }
    }
    
    if (endMonthIndex === -1) {
      if (barEnd.isBefore(timelineStart)) {
        endMonthIndex = 0;
      } else if (barEnd.isAfter(timelineEnd.clone().endOf('month'))) {
        endMonthIndex = timeline.length;
      }
    }
    
    const left = Math.max(0, startMonthIndex * MONTH_WIDTH);
    const right = Math.min(totalTimelineWidth, endMonthIndex * MONTH_WIDTH);
    const width = Math.max(0, right - left);

    return { left, width };
  };

  const getMonthlyQuantities = (pkg) => {
    if (!pkg.monthly_distributions || timeline.length === 0) {
      return new Array(timeline.length).fill(null);
    }

    const quantities = new Array(timeline.length).fill(null);
    
    pkg.monthly_distributions.forEach(dist => {
      const timelineIndex = timeline.findIndex(month => 
        month.year() === dist.year && month.month() + 1 === dist.month
      );
      if (timelineIndex !== -1) {
        quantities[timelineIndex] = dist.quantity;
      }
    });

    return quantities;
  };

  const getPaymentShiftedQuantities = (pkg) => {
    const monthlyQuantities = getMonthlyQuantities(pkg);
    if (!pkg.lead_time || monthlyQuantities.length === 0) {
      return monthlyQuantities;
    }

    const shiftedQuantities = new Array(timeline.length).fill(null);
    const leadTimeMonths = Math.floor(pkg.lead_time / 30);

    for (let i = 0; i < monthlyQuantities.length; i++) {
      if (monthlyQuantities[i] !== null) {
        const shiftedIndex = i + leadTimeMonths;
        if (shiftedIndex < timeline.length) {
          shiftedQuantities[shiftedIndex] = monthlyQuantities[i];
        }
      }
    }

    return shiftedQuantities;
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
        headers: getAuthHeaders(),
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

  const handleMonthlyChange = (pkgId, timelineIndex, value) => {
    const month = timeline[timelineIndex];
    const monthKey = `${month.year()}-${month.month() + 1}`;
    
    setEditingMonthly(prev => ({
      ...prev,
      [pkgId]: {
        ...(prev[pkgId] || {}),
        [monthKey]: value
      }
    }));
  };

  // FIXED: Save monthly quantities with added filter
  const handleSaveMonthly = async (pkg) => {
    setSavingMonthlyPkgId(pkg.id);
    
    const packageStart = moment(pkg.start_date);
    const packageEnd = moment(pkg.end_date);
    const finalMonthlyDistributions = [];
    
    try {
      const allDistributions = new Map();

      // Start with existing distributions
      pkg.monthly_distributions?.forEach(dist => {
        const monthKey = `${dist.year}-${dist.month}`;
        allDistributions.set(monthKey, dist.quantity);
      });

      // Override with edited values
      const edits = editingMonthly[pkg.id] || {};
      Object.entries(edits).forEach(([monthKey, quantity]) => {
        allDistributions.set(monthKey, Number(quantity) || 0);
      });

      // Filter final list to ensure all items are within the date range
      allDistributions.forEach((quantity, monthKey) => {
        const [year, month] = monthKey.split('-').map(Number);
        const monthMoment = moment({ year, month: month - 1 });

        // **FIX**: Only include distributions that are within the package's date range
        if (monthMoment.isBetween(packageStart, packageEnd, 'month', '[]')) {
          finalMonthlyDistributions.push({ year, month, quantity });
        }
      });

      const res = await fetch(`${VITE_API_URL}/rop-package/update/${pkg.id}`, {
        method: "PUT",
        headers: getAuthHeaders(),
        body: JSON.stringify({ monthly_distributions: finalMonthlyDistributions })
      });
      
      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || "Failed to save monthly quantities");
      }
      
      setSuccess("Monthly quantities updated!");
      setEditingMonthly(prev => ({ ...prev, [pkg.id]: {} }));
      fetchPackages();
    } catch (err) {
      setError(err.message);
    } finally {
      setSavingMonthlyPkgId(null);
    }
  };

  const handleDateChange = async (pkg, field, date) => {
    const newDate = moment(date).format("YYYY-MM-DD");
    
    if (isDateInPast(newDate)) {
      setError("Cannot set dates in the past");
      return;
    }

    const updatedPkg = { ...pkg, [field]: newDate };
    
    if (pkg.monthly_distributions && pkg.monthly_distributions.length > 0) {
      const newStart = moment(field === 'start_date' ? newDate : pkg.start_date);
      const newEnd = moment(field === 'end_date' ? newDate : pkg.end_date);
      
      const hasOutOfRangeDistributions = pkg.monthly_distributions.some(dist => {
        const distMonth = moment({ year: dist.year, month: dist.month - 1 });
        return distMonth.isBefore(newStart, 'month') || distMonth.isAfter(newEnd, 'month');
      });
      
      if (hasOutOfRangeDistributions && !window.confirm(
        "Changing dates will remove distributions outside the new range. Continue?"
      )) {
        return;
      }
    }

    await handleUpdatePackage(pkg.id, { [field]: newDate });
  };

  const handleBarDrag = (e, pkg, type) => {
    e.preventDefault();
    if (timeline.length === 0) return;
    
    let updatedPkg = { ...pkg };

    const onMouseMove = (moveEvent) => {
      const ganttCell = e.target.closest(".gantt-chart-cell");
      if (!ganttCell) return;

      const tableRect = ganttCell.getBoundingClientRect();
      const offsetX = Math.max(0, moveEvent.clientX - tableRect.left);

      const timelineStartMoment = timeline[0].clone().startOf('month');
      const timelineEndMoment = timeline[timeline.length - 1].clone().endOf('month');
      const totalTimelineWidth = timeline.length * MONTH_WIDTH;
      const totalTimelineDays = timelineEndMoment.diff(timelineStartMoment, 'days');

      if (totalTimelineWidth === 0 || totalTimelineDays <= 0) return;

      const daysFromStart = (offsetX / totalTimelineWidth) * totalTimelineDays;
      const newDate = timelineStartMoment.clone().add(daysFromStart, 'days');

      if (isDateInPast(newDate)) {
        return;
      }

      if (type === "move") {
        const duration = moment(pkg.end_date).diff(moment(pkg.start_date), "days");
        updatedPkg.start_date = newDate.format("YYYY-MM-DD");
        updatedPkg.end_date = newDate.clone().add(duration, "days").format("YYYY-MM-DD");
      } else if (type === "start") {
        if (moment(pkg.end_date).isAfter(newDate)) {
          updatedPkg.start_date = newDate.format("YYYY-MM-DD");
        }
      } else if (type === "end") {
        if (moment(pkg.start_date).isBefore(newDate)) {
          updatedPkg.end_date = newDate.format("YYYY-MM-DD");
        }
      }

      setPackages((prev) => prev.map((p) => (p.id === pkg.id ? updatedPkg : p)));
    };

    const onMouseUp = () => {
      document.removeEventListener("mousemove", onMouseMove);
      document.removeEventListener("mouseup", onMouseUp);
      handleUpdatePackage(pkg.id, {
        start_date: updatedPkg.start_date,
        end_date: updatedPkg.end_date,
      });
    };

    document.addEventListener("mousemove", onMouseMove);
    document.addEventListener("mouseup", onMouseUp);
  };

  const getPaymentDetails = (pkg) => {
    const { start_date, lead_time, quantity, price } = pkg;
    if (!start_date || !lead_time || !quantity || !price || timeline.length === 0) {
      return {
        paymentOf: "N/A",
        paymentDate: "N/A",
        paymentAmount: "N/A",
      };
    }

    const monthlyQuantities = getMonthlyQuantities(pkg);
    const currentDate = moment();

    let firstMonthIndex = -1;
    for (let i = 0; i < monthlyQuantities.length; i++) {
      if (monthlyQuantities[i] > 0) {
        firstMonthIndex = i;
        break;
      }
    }

    if (firstMonthIndex === -1) {
      return {
        paymentOf: "N/A",
        paymentDate: "N/A",
        paymentAmount: "N/A",
      };
    }

    let paymentDate = moment(start_date).add(lead_time, 'days');
    let paymentMonthIndex = firstMonthIndex;
    let monthlyQuantity = monthlyQuantities[firstMonthIndex];

    while (paymentDate.isBefore(currentDate, 'day') && paymentMonthIndex < monthlyQuantities.length - 1) {
      let nextMonthIndex = -1;
      for (let i = paymentMonthIndex + 1; i < monthlyQuantities.length; i++) {
        if (monthlyQuantities[i] > 0) {
          nextMonthIndex = i;
          break;
        }
      }

      if (nextMonthIndex === -1) {
        break;
      }

      paymentMonthIndex = nextMonthIndex;
      monthlyQuantity = monthlyQuantities[nextMonthIndex];
      paymentDate = timeline[paymentMonthIndex].clone().startOf('month').add(lead_time % 30, 'days');
    }

    const paymentMonth = timeline[paymentMonthIndex];
    const paymentAmount = monthlyQuantity * price;

    return {
      paymentOf: paymentMonth.format("MMMM/YYYY"),
      paymentDate: paymentDate.format("YYYY-MM-DD"),
      paymentAmount: paymentAmount.toLocaleString(),
    };
  };

  const getCurrentMonthlyQuantity = (pkg, timelineIndex) => {
    const month = timeline[timelineIndex];
    const monthKey = `${month.year()}-${month.month() + 1}`;
    const editedValue = editingMonthly[pkg.id]?.[monthKey];
    
    if (editedValue !== undefined) {
      return editedValue;
    }
    
    const originalDistribution = pkg.monthly_distributions?.find(d => 
      d.year === month.year() && d.month === month.month() + 1
    );
    
    return originalDistribution?.quantity || 0;
  };

  const getTotalEditedQuantity = (pkg) => {
    let total = 0;
    timeline.forEach((month, index) => {
      const quantity = getCurrentMonthlyQuantity(pkg, index);
      if (quantity !== null && quantity !== '') {
        total += Number(quantity) || 0;
      }
    });
    return total;
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
                <th style={{ width: "fit-content" }}></th>
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
                      <span key={index} className="timeline-month-header" style={{ 
                        textAlign: 'center', 
                        fontWeight: 'bold', 
                        position: 'relative',
                        color: isMonthInPast(month.year(), month.month() + 1) ? '#999' : '#000'
                      }}>
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
                const paymentShiftedQuantities = getPaymentShiftedQuantities(pkg);
                const paymentDetails = getPaymentDetails(pkg);
                const totalEdited = getTotalEditedQuantity(pkg);
                const hasQuantityMismatch = totalEdited !== pkg.quantity;

                return (
                  <>
                    <tr key={pkg.id}>
                      <td style={{ cursor: 'pointer', color: '#d32f2f', margin: '0' }}>
                        <span
                          onClick={() => handleDeletePackage(pkg.id)}
                          style={{ cursor: 'pointer', color: '#d32f2f', margin: '0' }}
                        >
                          🗑️
                        </span>
                      </td>
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
                          onChange={(date) => handleDateChange(pkg, 'start_date', date)}
                          dateFormat="yyyy-MM-dd"
                          customInput={<input style={{ width: '100px' }} readOnly />}
                          calendarIcon
                        />
                      </td>
                      <td>
                        <DatePicker
                          selected={pkg.end_date ? moment(pkg.end_date).toDate() : null}
                          onChange={(date) => handleDateChange(pkg, 'end_date', date)}
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
                          style={{ 
                            width: 80, 
                            padding: '2px 6px', 
                            borderRadius: 4, 
                            border: isQuantityColChanged(pkg) ? '2px solid #ff9800' : '1px solid #ccc',
                            backgroundColor: isQuantityColChanged(pkg) ? '#fff3e0' : 'white'
                          }}
                          onChange={e => handleQuantityColChange(pkg.id, e.target.value)}
                          disabled={savingQuantityColPkgId === pkg.id}
                        />
                        {isQuantityColChanged(pkg) && (
                          <button
                            onClick={() => handleSaveQuantityCol(pkg)}
                            style={{
                              marginLeft: '5px',
                              padding: '2px 6px',
                              fontSize: '10px',
                              background: '#4caf50',
                              color: 'white',
                              border: 'none',
                              borderRadius: '3px',
                              cursor: 'pointer'
                            }}
                            disabled={savingQuantityColPkgId === pkg.id}
                          >
                            {savingQuantityColPkgId === pkg.id ? '...' : 'Save'}
                          </button>
                        )}
                      </td>

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
                                left: barProps.left,
                                width: barProps.width,
                                top: '8px',
                                height: '24px',
                                backgroundColor: '#36a2eb',
                                borderRadius: '4px',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                color: '#fff',
                                fontWeight: 'bold',
                                fontSize: '0.8em',
                                boxShadow: '0 2px 4px rgba(0, 0, 0, 0.2)',
                                zIndex: 2,
                                cursor: 'move',
                              }}
                              onMouseDown={(e) => handleBarDrag(e, pkg, "move")}
                            >
                              <div
                                className="resize-pointer left"
                                style={{ 
                                  position: 'absolute', 
                                  left: '-8px', 
                                  top: '50%', 
                                  transform: 'translateY(-50%)', 
                                  width: '16px', 
                                  height: '24px', 
                                  cursor: 'ew-resize', 
                                  background: '#388e3c', 
                                  borderRadius: '50%', 
                                  border: '2px solid #fff', 
                                  zIndex: 2 
                                }}
                                title="Drag to change start date"
                                onMouseDown={(e) => { e.stopPropagation(); handleBarDrag(e, pkg, "start"); }}
                              ></div>
                              <span className="gantt-quantity-label" style={{ position: 'absolute', left: '50%', top: '50%', transform: 'translate(-50%, -50%)', zIndex: 1, pointerEvents: 'none' }}>{pkg.quantity}</span>
                              <div
                                className="resize-pointer right"
                                style={{ 
                                  position: 'absolute', 
                                  right: '-8px', 
                                  top: '50%', 
                                  transform: 'translateY(-50%)', 
                                  width: '16px', 
                                  height: '24px', 
                                  cursor: 'ew-resize', 
                                  background: '#1976d2', 
                                  borderRadius: '50%', 
                                  border: '2px solid #fff', 
                                  zIndex: 2 
                                }}
                                title="Drag to change end date"
                                onMouseDown={(e) => { e.stopPropagation(); handleBarDrag(e, pkg, "end"); }}
                              ></div>
                            </div>
                          )}
                        </div>
                        
                        {hasQuantityMismatch && (
                          <div style={{ 
                            color: '#d32f2f', 
                            fontSize: '12px', 
                            fontWeight: 'bold', 
                            marginBottom: '5px',
                            textAlign: 'center'
                          }}>
                            Total: {totalEdited} ≠ Package: {pkg.quantity}
                          </div>
                        )}

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
                          {timeline.map((month, index) => {
                            const currentQuantity = getCurrentMonthlyQuantity(pkg, index);
                            const isInPast = isMonthInPast(month.year(), month.month() + 1);
                            const isWithinPackageDateRange = month.isSameOrAfter(moment(pkg.start_date), 'month') && 
                                                            month.isSameOrBefore(moment(pkg.end_date), 'month');
                            
                            return (
                              <div
                                key={index}
                                className="monthly-quantity-cell"
                                style={{
                                  textAlign: 'center',
                                  position: 'relative',
                                  visibility: isWithinPackageDateRange ? 'visible' : 'hidden'
                                }}
                              >
                                <input
                                  type="number"
                                  value={currentQuantity || ''}
                                  min={0}
                                  style={{ 
                                    width: 60, 
                                    padding: '2px 6px', 
                                    borderRadius: 4, 
                                    border: '1px solid #ccc',
                                    backgroundColor: isInPast ? '#f5f5f5' : 'white',
                                    color: isInPast ? '#999' : 'black'
                                  }}
                                  onChange={e => handleMonthlyChange(pkg.id, index, e.target.value)}
                                  disabled={isInPast || savingMonthlyPkgId === pkg.id}
                                  readOnly={isInPast}
                                  title={isInPast ? 'Past months cannot be modified' : ''}
                                />
                                
                                {paymentShiftedQuantities[index] !== null && (
                                  <div className="monthly-cost-label" >
                                    {`${(paymentShiftedQuantities[index] * pkg.price).toLocaleString()}`}
                                  </div>
                                )}
                                
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
                            );
                          })}
                        </div>
                        
                        <div style={{ marginTop: '8px', display: 'flex', gap: '8px', justifyContent: 'center' }}>
                          {isMonthlyChanged(pkg) && (
                            <button
                              className="stylish-btn"
                              style={{ 
                                fontSize: '12px', 
                                padding: '4px 8px',
                                backgroundColor: hasQuantityMismatch ? '#ff9800' : '#4caf50'
                              }}
                              onClick={() => handleSaveMonthly(pkg)}
                              disabled={savingMonthlyPkgId === pkg.id}
                            >
                              {savingMonthlyPkgId === pkg.id ? 'Saving...' : 'Save Monthly'}
                            </button>
                          )}
                          
                          {pkg.start_date && pkg.end_date && pkg.quantity && (
                            <button
                              style={{
                                fontSize: '12px',
                                padding: '4px 8px',
                                backgroundColor: '#2196f3',
                                color: 'white',
                                border: 'none',
                                borderRadius: '4px',
                                cursor: 'pointer'
                              }}
                              onClick={() => handleAutoDistributeMonthly(pkg)}
                              title="Auto-distribute quantity evenly across future months"
                            >
                              Auto Distribute
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                    {expandedRows[pkg.id] && (
                      <tr className="expanded-row">
                        <td colSpan="6">
                          <div className="sub-table-container" style={{ display: 'flex', gap: '20px' }}>
                            <div className="pci-items-table">
                              <h4>PCI Items (Cost : {pkg.price ? pkg.price.toLocaleString() : 'N/A'})</h4>
                              <table className="sub-table" style={{ width: 'fit-content', minWidth: 0, maxWidth: 'none' }}>
                                <thead>
                                  <tr>
                                    <th style={{ width: 'fit-content', whiteSpace: 'nowrap' }}>Item Name</th>
                                    <th style={{ width: 'auto', whiteSpace: 'nowrap' }}>Quantity</th>
                                  </tr>
                                </thead>
                                <tbody>
                                  {pkg.lvl1_items && pkg.lvl1_items.length > 0 ? (
                                    pkg.lvl1_items.map((item, index) => (
                                      <tr key={index}>
                                        <td style={{ width: 'fit-content', whiteSpace: 'nowrap', fontSize: '0.95em' }}>{item.name || item}</td>
                                        <td style={{ width: 'auto', whiteSpace: 'nowrap' }}>
                                          <input
                                            type="number"
                                            value={editingQuantities[pkg.id]?.[index] ?? item.quantity ?? ''}
                                            min={0}
                                            style={{ width: 'auto', minWidth: 24, padding: '1px 2px', borderRadius: 3, border: '1px solid #ccc', fontSize: '0.95em' }}
                                            onChange={e => handleQuantityChange(pkg.id, index, e.target.value)}
                                            disabled={true} 
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
                            </div>
                            
                            <div className="monthly-distributions-summary">
                              <h4>Monthly Distribution Summary</h4>
                              <table className="sub-table" style={{ width: 'fit-content', minWidth: 0, maxWidth: 'none' }}>
                                <thead>
                                  <tr>
                                    <th>Month</th>
                                    <th>Quantity</th>
                                    <th>Cost</th>
                                  </tr>
                                </thead>
                                <tbody>
                                  {pkg.monthly_distributions && pkg.monthly_distributions.length > 0 ? (
                                    pkg.monthly_distributions
                                      .filter(d => d.quantity > 0)
                                      .sort((a, b) => a.year - b.year || a.month - b.month)
                                      .map((dist, index) => (
                                        <tr key={index}>
                                          <td>{moment({ year: dist.year, month: dist.month - 1 }).format('MMM YYYY')}</td>
                                          <td>{dist.quantity}</td>
                                          <td>{(dist.quantity * (pkg.price || 0)).toLocaleString()}</td>
                                        </tr>
                                      ))
                                  ) : (
                                    <tr>
                                      <td colSpan={3}>No monthly distributions found.</td>
                                    </tr>
                                  )}
                                </tbody>
                              </table>
                            </div>
                            
                            <div className="payment-details-table">
                              <h4>Payment Details</h4>
                              <table className="sub-table" style={{ width: 'fit-content', minWidth: 0, maxWidth: 'none' }}>
                                <tbody>
                                  <tr>
                                    <td style={{ fontWeight: 'bold' }}>Payment of:</td>
                                    <td>{paymentDetails.paymentOf}</td>
                                  </tr>
                                  <tr>
                                    <td style={{ fontWeight: 'bold' }}>Payment Date:</td>
                                    <td>{paymentDetails.paymentDate}</td>
                                  </tr>
                                  <tr>
                                    <td style={{ fontWeight: 'bold' }}>Payment Amount:</td>
                                    <td>{paymentDetails.paymentAmount}</td>
                                  </tr>
                                  <tr>
                                    <td style={{ fontWeight: 'bold' }}>Payment Lead Time:</td>
                                    <td>{pkg.lead_time || 'N/A'}</td>
                                  </tr>
                                </tbody>
                              </table>
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
                  <td colSpan="6" className="empty-state">
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