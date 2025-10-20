import { useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import '../css/RopLvl1.css';
import { apiCall, setTransient } from '../api';
import StatsCarousel from '../Components/shared/StatsCarousel';
import FilterBar from '../Components/shared/FilterBar';
import HelpModal, { HelpList, HelpText } from '../Components/shared/HelpModal';
import TitleWithInfo from '../Components/shared/InfoButton';
import DataTable from '../Components/shared/DataTable';
import Pagination from '../Components/shared/Pagination';

const ENTRIES_PER_PAGE = 15;
const VITE_API_URL = import.meta.env.VITE_API_URL;

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

// Utility function to generate monthly periods
const generateMonthlyPeriods = (startDate, endDate) => {
	if (!startDate || !endDate) return [];

	const periods = [];
	const start = new Date(startDate);
	const end = new Date(endDate);

	// Set to first day of start month
	const current = new Date(start.getFullYear(), start.getMonth(), 1);
	const endMonth = new Date(end.getFullYear(), end.getMonth(), 1);

	while (current <= endMonth) {
		periods.push({
			year: current.getFullYear(),
			month: current.getMonth() + 1, // 1-based month
			display: current.toLocaleDateString('en-US', { month: 'short', year: 'numeric' })
		});
		current.setMonth(current.getMonth() + 1);
	}

	return periods;
};

// Draft Management Utilities
const DRAFT_EXPIRY_HOURS = 24;

const getDraftKey = (projectId) => `package_draft_${projectId}`;

const saveDraftToLocalStorage = (projectId, draftData) => {
	try {
		const draft = {
			...draftData,
			timestamp: new Date().toISOString(),
			projectId
		};
		localStorage.setItem(getDraftKey(projectId), JSON.stringify(draft));
		console.log('✅ Draft saved to localStorage:', getDraftKey(projectId), draft);
	} catch (error) {
		console.error('❌ Failed to save draft:', error);
	}
};

const loadDraftFromLocalStorage = (projectId) => {
	try {
		const draftString = localStorage.getItem(getDraftKey(projectId));
		if (!draftString) {
			console.log('ℹ️ No draft found for:', getDraftKey(projectId));
			return null;
		}

		const draft = JSON.parse(draftString);

		// Check if draft has expired (24 hours)
		const draftTime = new Date(draft.timestamp);
		const now = new Date();
		const hoursDiff = (now - draftTime) / (1000 * 60 * 60);

		if (hoursDiff > DRAFT_EXPIRY_HOURS) {
			console.log('⏰ Draft expired (older than 24h), clearing...');
			clearDraftFromLocalStorage(projectId);
			return null;
		}

		console.log('✅ Draft loaded from localStorage:', draft);
		return draft;
	} catch (error) {
		console.error('❌ Failed to load draft:', error);
		return null;
	}
};

const clearDraftFromLocalStorage = (projectId) => {
	try {
		localStorage.removeItem(getDraftKey(projectId));
	} catch (error) {
		console.error('Failed to clear draft:', error);
	}
};

const hasDraft = (projectId) => {
	const draft = loadDraftFromLocalStorage(projectId);
	return draft !== null;
};

const getTimeSince = (timestamp) => {
	const now = new Date();
	const then = new Date(timestamp);
	const seconds = Math.floor((now - then) / 1000);

	if (seconds < 60) return 'just now';
	const minutes = Math.floor(seconds / 60);
	if (minutes < 60) return `${minutes} minute${minutes > 1 ? 's' : ''} ago`;
	const hours = Math.floor(minutes / 60);
	if (hours < 24) return `${hours} hour${hours > 1 ? 's' : ''} ago`;
	const days = Math.floor(hours / 24);
	return `${days} day${days > 1 ? 's' : ''} ago`;
};

export default function RopLvl1() {
	const location = useLocation();
	const navigate = useNavigate();
	const projectState = location.state;
	const [entries, setEntries] = useState([]);
	const [filteredEntries, setFilteredEntries] = useState([]);
	const [searchQuery, setSearchQuery] = useState('');
	const [showForm, setShowForm] = useState(false);
	const [showLvl1Form, setShowLvl1Form] = useState(false);
	const [showLvl2Form, setShowLvl2Form] = useState(false);
	const [isEditing, setIsEditing] = useState(false);
	const [editId, setEditId] = useState(null);
	const [formData, setFormData] = useState({
		project_id: projectState?.pid_po || '',
		project_name: projectState?.project_name || '',
		package_name: '',
		start_date: '',
		end_date: '',
		quantity: '',
		lead_time: '',
		currency: projectState?.currency || '',
	});

	// Monthly distributions state
	const [monthlyDistributions, setMonthlyDistributions] = useState([]);
	const [monthlyPeriods, setMonthlyPeriods] = useState([]);
	const [distributionError, setDistributionError] = useState('');

	// Lvl1 form data
	const [lvl1FormData, setLvl1FormData] = useState({
		id: '',
		project_id: projectState?.pid_po || '',
		project_name: projectState?.project_name || '',
		item_name: '',
		region: '',
		total_quantity: '',
		price: '',
		product_number: '',
		start_date: '',
		end_date: ''
	});

	// Lvl2 form data
	const [lvl2FormData, setLvl2FormData] = useState({
		id: '',
		project_id: projectState?.pid_po || '',
		lvl1_id: '',
		lvl1_item_name: '',
		item_name: '',
		region: '',
		total_quantity: '',
		price: '',
		start_date: '',
		end_date: '',
		product_number: '',
		distributions: []
	});

	const cur = projectState?.currency || '';
	// State to hold selected Lvl1 items with their quantities
	const [selectedLvl1Items, setSelectedLvl1Items] = useState([]);
	const [lvl2Details, setLvl2Details] = useState({});
	const [error, setError] = useState('');
	const [success, setSuccess] = useState('');
	const [currentPage, setCurrentPage] = useState(1);
	const [expandedRows, setExpandedRows] = useState({});
	const [lvl2Items, setLvl2Items] = useState({});
	const [showLvl1Dropdown, setShowLvl1Dropdown] = useState(false);
	const [pciSearchQuery, setPciSearchQuery] = useState('');

	// New state for calculated prices
	const [calculatedPackagePrice, setCalculatedPackagePrice] = useState(0);
	const [calculatedTotalPrice, setCalculatedTotalPrice] = useState(0);

	// Modern UI state
	const [showHelpModal, setShowHelpModal] = useState(false);

	// Draft management state
	const [showDraftPrompt, setShowDraftPrompt] = useState(false);
	const [loadedDraft, setLoadedDraft] = useState(null);

	useEffect(() => {
		fetchEntries();

		// Check for draft on component mount
		if (projectState?.pid_po) {
			const draft = loadDraftFromLocalStorage(projectState.pid_po);
			if (draft && draft.formData.package_name) {
				setLoadedDraft(draft);
			}
		}
	}, []);

	// Generate monthly periods when dates change
	useEffect(() => {
		if (formData.start_date && formData.end_date) {
			const periods = generateMonthlyPeriods(formData.start_date, formData.end_date);
			setMonthlyPeriods(periods);

			// Initialize distributions with zero quantities
			const initialDistributions = periods.map(period => ({
				year: period.year,
				month: period.month,
				quantity: 0
			}));
			setMonthlyDistributions(initialDistributions);
		} else {
			setMonthlyPeriods([]);
			setMonthlyDistributions([]);
		}
		setDistributionError('');
	}, [formData.start_date, formData.end_date]);

	// Validate distributions when quantities change
	useEffect(() => {
		if (monthlyDistributions.length > 0 && formData.quantity) {
			const totalDistributed = monthlyDistributions.reduce((sum, dist) => sum + (parseInt(dist.quantity) || 0), 0);
			const packageQuantity = parseInt(formData.quantity) || 0;

			if (totalDistributed !== packageQuantity && packageQuantity > 0) {
				setDistributionError(`Total distributed quantity (${totalDistributed}) must equal package quantity (${packageQuantity})`);
			} else {
				setDistributionError('');
			}
		} else {
			setDistributionError('');
		}
	}, [monthlyDistributions, formData.quantity]);

	// Validate selected item quantities and show a general error message
	useEffect(() => {
		const validateQuantities = () => {
			let hasError = false;
			for (const selectedItem of selectedLvl1Items) {
				const entry = entries.find(e => e.id === selectedItem.id);
				if (entry) {
					const selectedQty = parseInt(selectedItem.quantity) || 0;
					const availableQty = parseInt(entry.total_quantity) || 0;
					const packageQty = parseInt(formData.quantity) || 1;
					const totalNeeded = selectedQty * packageQty;

					if (selectedQty > availableQty || totalNeeded > availableQty) {
						hasError = true;
						break;
					}
				}
			}

			if (hasError) {
				// Use the user's requested error message
				setError("The selected PCI quantity is not sufficient.");
			} else if (error === "The selected PCI quantity is not sufficient.") {
				setError(''); // Clear the error if it's no longer applicable
			}
		};

		validateQuantities();
	}, [selectedLvl1Items, formData.quantity, entries, error]);

	// Auto-save draft to localStorage (debounced by 2 seconds)
	useEffect(() => {
		// Only auto-save if modal is open and there's meaningful data
		if (!showForm || !formData.package_name) return;

		const timeoutId = setTimeout(() => {
			const draftData = {
				formData,
				selectedLvl1Items,
				monthlyDistributions,
				monthlyPeriods
			};
			saveDraftToLocalStorage(projectState?.pid_po, draftData);
		}, 2000); // 2-second debounce

		return () => clearTimeout(timeoutId);
	}, [showForm, formData, selectedLvl1Items, monthlyDistributions, monthlyPeriods, projectState?.pid_po]);

	// Check for draft when modal opens
	useEffect(() => {
		if (showForm && !isEditing) {
			// Check if we already have a loaded draft
			if (loadedDraft && loadedDraft.formData.package_name) {
				setShowDraftPrompt(true);
			} else {
				// Try to load draft
				const draft = loadDraftFromLocalStorage(projectState?.pid_po);
				if (draft && draft.formData.package_name) {
					setLoadedDraft(draft);
					setShowDraftPrompt(true);
				}
			}
		}
	}, [showForm, isEditing, projectState?.pid_po, loadedDraft]);

	// Auto-distribute quantity evenly
	const handleAutoDistribute = () => {
		if (!formData.quantity || monthlyPeriods.length === 0) return;

		const totalQuantity = parseInt(formData.quantity);
		const monthsCount = monthlyPeriods.length;
		const baseQuantity = Math.floor(totalQuantity / monthsCount);
		const remainder = totalQuantity % monthsCount;

		const autoDistributions = monthlyPeriods.map((period, index) => ({
			year: period.year,
			month: period.month,
			quantity: baseQuantity + (index < remainder ? 1 : 0)
		}));

		setMonthlyDistributions(autoDistributions);
	};

	// Handle monthly distribution quantity change
	const handleMonthlyQuantityChange = (year, month, quantity) => {
		setMonthlyDistributions(prev =>
			prev.map(dist =>
				dist.year === year && dist.month === month
					? { ...dist, quantity: parseInt(quantity) || 0 }
					: dist
			)
		);
	};

	// Search functionality
	useEffect(() => {
		if (searchQuery.trim() === '') {
			setFilteredEntries(entries);
		} else {
			const filtered = entries.filter(entry =>
				entry.item_name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
				entry.product_number?.toLowerCase().includes(searchQuery.toLowerCase())
			);
			setFilteredEntries(filtered);
		}
		setCurrentPage(1); // Reset to first page when searching
	}, [searchQuery, entries]);

	useEffect(() => {
		const fetchDetailsForSelectedLvl1 = async () => {
			const newLvl2Details = {};
			for (const item of selectedLvl1Items) {
				// Only fetch if details aren't already loaded
				if (!lvl2Details[item.id]) {
					try {
						const res = await fetch(`${VITE_API_URL}/rop-lvl2/by-lvl1/${item.id}`, { headers: getAuthHeaders() });
						if (!res.ok) throw new Error('Failed to fetch Level 2 items');
						const data = await res.json();
						newLvl2Details[item.id] = data;
					} catch (err) {
						newLvl2Details[item.id] = [];
					}
				} else {
					// Use existing details
					newLvl2Details[item.id] = lvl2Details[item.id];
				}
			}
			setLvl2Details(prev => ({ ...prev, ...newLvl2Details }));
		};
		if (selectedLvl1Items.length > 0) {
			fetchDetailsForSelectedLvl1();
		}
	}, [selectedLvl1Items]);

	// Effect to calculate prices when dependencies change
	useEffect(() => {
		const calculatePrices = () => {
			let packagePrice = 0;
			selectedLvl1Items.forEach(item => {
				const lvl2s = lvl2Details[item.id] || [];
				const parentQuantity = parseFloat(item.quantity);
				let parentUnitPrice = 0;
				if (!isNaN(parentQuantity) && parentQuantity > 0) {
					if (lvl2s.length === 0) {
						parentUnitPrice = 0;
					} else {
						// Sum(child unit price * child quantity)
						const sum = lvl2s.reduce((acc, child) => {
							const childUnitPrice = parseFloat(child.price) || 0;
							const childQuantity = parseFloat(child.total_quantity) || 0;
							return acc + (childUnitPrice * childQuantity);
						}, 0);
						parentUnitPrice = sum / parentQuantity;
					}
					packagePrice += parentUnitPrice * parentQuantity;
				}
			});

			setCalculatedPackagePrice(packagePrice);

			const totalQuantity = parseFloat(formData.quantity);
			const totalPrice = !isNaN(totalQuantity) && totalQuantity > 0 ? packagePrice * totalQuantity : 0;
			setCalculatedTotalPrice(totalPrice);
		};

		calculatePrices();
	}, [selectedLvl1Items, lvl2Details, formData.quantity]);

	const fetchEntries = async () => {
		try {
			const url = projectState?.pid_po
				? `/rop-lvl1/by-project/${projectState.pid_po}`
				: `/rop-lvl1/`;
			const lvl1Entries = await apiCall(url);

			// Fetch Lvl2 children for all Lvl1 entries in parallel
			const lvl2Promises = lvl1Entries.map(entry =>
				fetch(`${VITE_API_URL}/rop-lvl2/by-lvl1/${entry.id}`, { headers: getAuthHeaders() })
					.then(res => res.ok ? res.json() : []) // Gracefully handle errors
					.catch(() => []) // Handle fetch failures
			);

			const allLvl2Items = await Promise.all(lvl2Promises);

			// Prepare a new state object for lvl2Items to avoid multiple re-renders
			const newLvl2ItemsState = {};

			// Augment Lvl1 entries with calculated prices
			const augmentedEntries = lvl1Entries.map((entry, index) => {
				const children = allLvl2Items[index] || [];

				// Populate the lvl2Items state object
				newLvl2ItemsState[entry.id] = children;

				const parentQuantity = parseFloat(entry.total_quantity);
				let calculatedUnitPrice = 0;

				if (children.length > 0 && parentQuantity > 0) {
					const sumOfChildTotals = children.reduce((acc, child) => {
						const childUnitPrice = parseFloat(child.price) || 0;
						const childQuantity = parseFloat(child.total_quantity) || 0;
						return acc + (childUnitPrice * childQuantity);
					}, 0);
					calculatedUnitPrice = sumOfChildTotals / parentQuantity;
				}
				// If children.length is 0 or parentQuantity is 0, calculatedUnitPrice remains 0.

				return { ...entry, calculatedUnitPrice };
			});

			// Set both states together
			setEntries(augmentedEntries);
			setLvl2Items(newLvl2ItemsState);

		} catch (err) {
			setTransient(setError, err.message || 'Failed to fetch or process ROP entries');
			console.error(err);
		}
	};

	const fetchLvl2Items = async (lvl1_id) => {
		try {
			const data = await apiCall(`/rop-lvl2/by-lvl1/${lvl1_id}`);
			setLvl2Items(prev => ({ ...prev, [lvl1_id]: data }));
		} catch (err) {
			setLvl2Items(prev => ({ ...prev, [lvl1_id]: [] }));
		}
	};

	// Restore draft from localStorage
	const handleRestoreDraft = () => {
		if (!loadedDraft) return;

		setFormData(loadedDraft.formData);
		setSelectedLvl1Items(loadedDraft.selectedLvl1Items || []);
		setMonthlyDistributions(loadedDraft.monthlyDistributions || []);
		setMonthlyPeriods(loadedDraft.monthlyPeriods || []);

		setShowDraftPrompt(false);
		setLoadedDraft(null);
	};

	// Discard draft and start fresh
	const handleDiscardDraft = () => {
		clearDraftFromLocalStorage(projectState?.pid_po);
		setShowDraftPrompt(false);
		setLoadedDraft(null);
	};

	const resetForm = () => {
		setFormData({
			project_id: projectState?.pid_po || '',
			project_name: projectState?.project_name || '',
			package_name: '',
			start_date: '',
			end_date: '',
			quantity: '',
			lead_time: '',
			currency: projectState?.currency || '',

		});
		setSelectedLvl1Items([]);
		setLvl2Details({});
		setMonthlyDistributions([]);
		setMonthlyPeriods([]);
		setDistributionError('');
		setEditId(null);
		setIsEditing(false);
		setShowForm(false);
		setCalculatedPackagePrice(0);
		setCalculatedTotalPrice(0);
		// Clear draft from localStorage when form is reset
		clearDraftFromLocalStorage(projectState?.pid_po);
	};

	const resetLvl1Form = () => {
		setLvl1FormData({
			id: '',
			project_id: projectState?.pid_po || '',
			project_name: projectState?.project_name || '',
			item_name: '',
			region: '',
			total_quantity: '',
			price: '',
			product_number: '',
			start_date: '',
			end_date: ''
		});
		setEditId(null);
		setIsEditing(false);
		setShowLvl1Form(false);
	};

	const resetLvl2Form = () => {
		setLvl2FormData({
			id: '',
			project_id: projectState?.pid_po || '',
			lvl1_id: '',
			lvl1_item_name: '',
			item_name: '',
			region: '',
			total_quantity: '',
			price: '',
			start_date: '',
			end_date: '',
			product_number: '',
			distributions: []
		});
		setEditId(null);
		setIsEditing(false);
		setShowLvl2Form(false);
	};

	const handleSubmit = async (e) => {
		e.preventDefault();
		setError('');
		setSuccess('');

		if (!formData.package_name || selectedLvl1Items.length === 0) {
			setError('Package Name and at least one Lvl1 item are required.');
			return;
		}

		// Validate quantities before submission
		const quantityErrors = [];
		selectedLvl1Items.forEach(selectedItem => {
			const entry = entries.find(e => e.id === selectedItem.id);
			if (entry) {
				const selectedQty = parseInt(selectedItem.quantity) || 0;
				const availableQty = parseInt(entry.total_quantity) || 0;
				const packageQty = parseInt(formData.quantity) || 1;
				const totalNeeded = selectedQty * packageQty;

				if (selectedQty > availableQty || totalNeeded > availableQty) {
					quantityErrors.push(`PCI "${entry.item_name}" has insufficient quantity`);
				}
			}
		});

		if (quantityErrors.length > 0) {
			setError('Cannot create package: ' + quantityErrors.join(', '));
			return;
		}

		// Check distribution validation if dates and quantity are provided
		if (distributionError && formData.start_date && formData.end_date && formData.quantity) {
			setError(distributionError);
			return;
		}

		const payload = {
			project_id: formData.project_id,
			package_name: formData.package_name,
			start_date: formData.start_date || null,
			end_date: formData.end_date || null,
			quantity: formData.quantity ? parseInt(formData.quantity) : null,
			lvl1_ids: selectedLvl1Items,
			price: calculatedPackagePrice,
			lead_time: formData.lead_time ? parseInt(formData.lead_time) : null,
			// Include monthly distributions if they exist and are valid
			monthly_distributions: monthlyDistributions.length > 0 && !distributionError ? monthlyDistributions : [],
			currency: formData.currency
		};

		try {
			await apiCall(`/rop-package/create`, {
				method: 'POST',
				body: JSON.stringify(payload),
			});

			setTransient(setSuccess, 'ROP Package created successfully!');
			resetForm();
			fetchEntries();
			navigate('/rop-package');
		} catch (err) {
			setTransient(setError, err.message || 'Failed to create package');
		}
	};

	const handleLvl1Submit = async (e) => {
		e.preventDefault();
		setError('');
		setSuccess('');

		const payload = {
			id: lvl1FormData.id,
			project_id: lvl1FormData.project_id,
			project_name: lvl1FormData.project_name,
			item_name: lvl1FormData.item_name,
			region: lvl1FormData.region || null,
			total_quantity: lvl1FormData.total_quantity ? parseInt(lvl1FormData.total_quantity) : null,
			price: lvl1FormData.price ? parseFloat(lvl1FormData.price) : null,
			product_number: lvl1FormData.product_number || null,
			start_date: lvl1FormData.start_date || null,
			end_date: lvl1FormData.end_date || null
		};

		try {
			const url = isEditing
				? `/rop-lvl1/update/${editId}`
				: `/rop-lvl1/create`;

			const method = isEditing ? 'PUT' : 'POST';

			await apiCall(url, {
				method: method,
				body: JSON.stringify(payload),
			});

			setTransient(setSuccess, `ROP Lvl1 ${isEditing ? 'updated' : 'created'} successfully!`);
			resetLvl1Form();
			fetchEntries();
		} catch (err) {
			setTransient(setError, err.message || `Failed to ${isEditing ? 'update' : 'create'} Lvl1 item`);
		}
	};

	const handleLvl2Submit = async (e) => {
		e.preventDefault();
		setError('');
		setSuccess('');

		const payload = {
			id: lvl2FormData.id,
			project_id: lvl2FormData.project_id,
			lvl1_id: lvl2FormData.lvl1_id,
			lvl1_item_name: lvl2FormData.lvl1_item_name,
			item_name: lvl2FormData.item_name,
			region: lvl2FormData.region,
			total_quantity: parseInt(lvl2FormData.total_quantity),
			price: parseFloat(lvl2FormData.price),
			start_date: lvl2FormData.start_date,
			end_date: lvl2FormData.end_date,
			product_number: lvl2FormData.product_number || null,
			distributions: lvl2FormData.distributions
		};

		try {
			const url = isEditing
				? `/rop-lvl2/update/${editId}`
				: `/rop-lvl2/create`;

			const method = isEditing ? 'PUT' : 'POST';

			await apiCall(url, {
				method: method,
				body: JSON.stringify(payload),
			});

			setTransient(setSuccess, `ROP Lvl2 ${isEditing ? 'updated' : 'created'} successfully!`);
			resetLvl2Form();
			fetchEntries();
			// Refresh lvl2 items for the parent lvl1
			if (lvl2FormData.lvl1_id) {
				await fetchLvl2Items(lvl2FormData.lvl1_id);
			}
		} catch (err) {
			setTransient(setError, err.message || `Failed to ${isEditing ? 'update' : 'create'} Lvl2 item`);
		}
	};

	const handleEditLvl1 = (entry) => {
		setLvl1FormData({
			id: entry.id,
			project_id: entry.project_id,
			project_name: entry.project_name,
			item_name: entry.item_name,
			region: entry.region || '',
			total_quantity: entry.total_quantity?.toString() || '',
			price: entry.price?.toString() || '',
			product_number: entry.product_number || '',
			start_date: entry.start_date || '',
			end_date: entry.end_date || ''
		});
		setEditId(entry.id);
		setIsEditing(true);
		setShowLvl1Form(true);
	};

	const handleEditLvl2 = (lvl2Item) => {
		setLvl2FormData({
			id: lvl2Item.id,
			project_id: lvl2Item.project_id,
			lvl1_id: lvl2Item.lvl1_id,
			lvl1_item_name: lvl2Item.lvl1_item_name,
			item_name: lvl2Item.item_name,
			region: lvl2Item.region,
			total_quantity: lvl2Item.total_quantity?.toString() || '',
			price: lvl2Item.price?.toString() || '',
			start_date: lvl2Item.start_date || '',
			end_date: lvl2Item.end_date || '',
			product_number: lvl2Item.product_number || '',
			distributions: lvl2Item.distributions || []
		});
		setEditId(lvl2Item.id);
		setIsEditing(true);
		setShowLvl2Form(true);
	};

	const handleCreateLvl2 = (lvl1Item) => {
		setLvl2FormData({
			id: `lvl2_${Date.now()}`,
			project_id: projectState?.pid_po || '',
			lvl1_id: lvl1Item.id,
			lvl1_item_name: lvl1Item.item_name,
			item_name: '',
			region: '',
			total_quantity: '',
			price: '',
			start_date: '',
			end_date: '',
			product_number: '',
			distributions: []
		});
		setIsEditing(false);
		setShowLvl2Form(true);
	};

	const handleDeleteLvl1 = async (id) => {
		if (!window.confirm('Are you sure you want to delete this Lvl1 item and all its Lvl2 children?')) {
			return;
		}

		try {
			await apiCall(`/rop-lvl1/${id}`, {
				method: 'DELETE'
			});

			setTransient(setSuccess, 'ROP Lvl1 deleted successfully!');
			fetchEntries();
		} catch (err) {
			setTransient(setError, err.message || 'Failed to delete Lvl1 item');
		}
	};

	const handleDeleteLvl2 = async (id, lvl1_id) => {
		if (!window.confirm('Are you sure you want to delete this Lvl2 item?')) {
			return;
		}

		try {
			await apiCall(`/rop-lvl2/${id}`, {
				method: 'DELETE'
			});

			setTransient(setSuccess, 'ROP Lvl2 deleted successfully!');
			// Refresh lvl2 items for the parent lvl1
			await fetchLvl2Items(lvl1_id);
			fetchEntries(); // Also refresh main entries to update totals
		} catch (err) {
			setTransient(setError, err.message || 'Failed to delete Lvl2 item');
		}
	};

	const handleSelectLvl1Item = (item) => {
		setSelectedLvl1Items(prev => {
			const itemExists = prev.find(i => i.id === item.id);
			if (itemExists) {
				return prev.filter(i => i.id !== item.id);
			} else {
				return [...prev, { id: item.id, quantity: '1' }];
			}
		});
	};

	const handleQuantityChange = (id, quantity) => {
		setSelectedLvl1Items(prev =>
			prev.map(item =>
				item.id === id ? { ...item, quantity: quantity } : item
			)
		);
	};

	// Use filtered entries for pagination
	const paginatedEntries = filteredEntries.slice(
		(currentPage - 1) * ENTRIES_PER_PAGE,
		currentPage * ENTRIES_PER_PAGE
	);
	const totalPages = Math.ceil(filteredEntries.length / ENTRIES_PER_PAGE);

	// Statistics calculations (using original entries, not filtered)
	const totalItems = entries.length;
	const totalQuantity = entries.reduce((sum, e) => sum + (e.total_quantity || 0), 0);
	const totalLE = entries.reduce((sum, e) => sum + ((e.total_quantity || 0) * (e.price || 0)), 0);
	const avgQuantityPerItem = totalItems > 0 ? Math.round(totalQuantity / totalItems) : 0;
	const avgLEPerItem = totalItems > 0 ? Math.round(totalLE / totalItems) : 0;
	const avgPrice = totalItems > 0 ? (entries.reduce((sum, e) => sum + (e.price || 0), 0) / totalItems).toFixed(2) : 0;
	const highestLEItem = entries.reduce((highest, e) => {
		const le = (e.total_quantity || 0) * (e.price || 0);
		return le > (highest.le || 0) ? { ...e, le } : highest;
	}, {});
	const earliestStart = entries
		.filter(e => e.start_date)
		.reduce((earliest, e) => (!earliest || new Date(e.start_date) < earliest ? new Date(e.start_date) : earliest), null);
	const latestEnd = entries
		.filter(e => e.end_date)
		.reduce((latest, e) => (!latest || new Date(e.end_date) > latest ? new Date(e.end_date) : latest), null);

	// Regional distribution
	const regionCounts = entries.reduce((acc, e) => {
		const region = e.region || 'Unknown';
		acc[region] = (acc[region] || 0) + 1;
		return acc;
	}, {});
	const topRegion = Object.entries(regionCounts).reduce((max, [region, count]) =>
		count > max.count ? { region, count } : max, { region: 'None', count: 0 });

	// Format currency
	const formatCurrency = (num) => {
		if (num === null || num === undefined) return '';
		if (Math.abs(num) >= 1_000_000) {
			return (num / 1_000_000).toFixed(1).replace(/\.0$/, '') + 'M';
		}
		if (Math.abs(num) >= 1_000) {
			return (num / 1_000).toFixed(0).replace(/\.0$/, '') + 'K';
		}
		return num.toString();
	};

	// Define stat cards for carousel
	const statCards = [
		{ label: 'Total PCIs', value: totalItems },
		{ label: 'Total Quantity', value: totalQuantity.toLocaleString() },
		{ label: 'Total Price', value: formatCurrency(totalLE) },
		{ label: 'Avg Price/Item', value: formatCurrency(avgLEPerItem) },
		{ label: 'Avg Qty/Item', value: avgQuantityPerItem.toLocaleString() },
		{ label: 'Avg Price', value: avgPrice },
		{ label: 'Top Item', value: highestLEItem.item_name?.substring(0, 15) || '-' },
		{ label: 'Top Region', value: `${topRegion.region} (${topRegion.count})` }
	];

	// Help modal sections
	const helpSections = [
		{
			icon: '📋',
			title: 'Overview',
			content: <HelpText>ROP Level 1 Analytics allows you to manage Product Component Items (PCIs) and Sub Items (SIs) for your project. You can create packages, manage items hierarchically, and track monthly distributions.</HelpText>
		},
		{
			icon: '✨',
			title: 'Features',
			content: (
				<HelpList items={[
					{ label: '+ New Package', text: 'Create a package by selecting PCIs, setting dates, quantities, and monthly distributions.' },
					{ label: 'Search', text: 'Filter PCIs by item name, region, or product number.' },
					{ label: 'Expand (▶)', text: 'Click to view Sub Items (SIs) within each PCI.' },
					{ label: 'Edit (✏️)', text: 'Modify PCI details including quantity, price, and dates.' },
					{ label: 'Delete (🗑️)', text: 'Remove a PCI and its associated sub items.' },
					{ label: 'Monthly Distributions', text: 'Distribute package quantities across months within the date range.' },
					{ label: 'Auto Distribute', text: 'Automatically spread quantities evenly across all months.' },
				]} />
			)
		},
		{
			icon: '📦',
			title: 'Creating Packages',
			content: (
				<>
					<HelpText>To create a package:</HelpText>
					<HelpList items={[
						'1. Click "+ New Package" button',
						'2. Enter package details (name, dates, quantity, lead time)',
						'3. Select PCIs from the dropdown and assign quantities',
						'4. Set monthly distributions (or use Auto Distribute)',
						'5. Ensure total monthly quantities equal package quantity',
						'6. Click "Create Package" to save'
					]} />
					<HelpText isNote>Package quantities are validated against available PCI quantities to prevent over-allocation.</HelpText>
				</>
			)
		},
		{
			icon: '🔢',
			title: 'Monthly Distributions',
			content: (
				<HelpText>Monthly distributions allow you to spread package quantities across specific months. The system validates that the sum of monthly quantities matches the total package quantity. Use the "Auto Distribute" button to evenly allocate quantities across all months between start and end dates.</HelpText>
			)
		},
		{
			icon: '📊',
			title: 'Statistics Explained',
			content: (
				<HelpList items={[
					{ label: 'Total PCIs', text: 'Total number of Product Component Items' },
					{ label: 'Total Quantity', text: 'Sum of all PCI quantities' },
					{ label: 'Total Price', text: 'Total value (quantity × price for all PCIs)' },
					{ label: 'Avg Price/Item', text: 'Average value per PCI' },
					{ label: 'Avg Qty/Item', text: 'Average quantity per PCI' },
					{ label: 'Avg Price', text: 'Average unit price across all PCIs' },
					{ label: 'Top Item', text: 'PCI with highest total value' },
					{ label: 'Top Region', text: 'Region with most PCIs' }
				]} />
			)
		},
		{
			icon: '💡',
			title: 'Tips',
			content: (
				<HelpList items={[
					'Use the search bar to quickly find specific PCIs',
					'Expand rows to view and manage Sub Items (SIs)',
					'Monthly distributions must sum to the package quantity',
					'Package creation validates PCI availability',
					'Edit PCIs to update quantities, prices, or dates',
					'Top statistics help identify key items and regions'
				]} />
			)
		}
	];

	return (
		<div className="dashboard-container">
			{/* Header Section */}
			<div className="dashboard-header">
				<TitleWithInfo
					title="ROP Level 1 Analytics"
					subtitle={formData.project_name ? `${formData.project_name} • Project ID: ${formData.project_id}` : 'Project Management Dashboard'}
					onInfoClick={() => setShowHelpModal(true)}
				/>
				<div style={{ display: 'flex', gap: '10px' }}>
					<button className="new-entry-btn" style={{ visibility: 'hidden' }} onClick={() => { resetLvl1Form(); setShowLvl1Form(!showLvl1Form); }}>
						{showLvl1Form ? '✕ Cancel' : '+ New PCI'}
					</button>
					<button className="new-entry-btn" onClick={() => { resetForm(); setShowForm(!showForm); }}>
						{showForm ? '✕ Cancel' : '+ New Package'}
					</button>
				</div>
			</div>



			{/* Chart Cards Section */}
			<div className="dashboard-chart-section">
				<div className="chart-card">
					<h3 className="chart-title">📊 Project Overview</h3>

					<div className="metric-row">
						<span className="metric-label">Project Progress</span>
						<span className="metric-value">{totalItems} Items</span>
					</div>
					<div className="progress-bar">
						<div className="progress-fill" style={{ width: `${Math.min((totalItems / 10) * 100, 100)}%` }}></div>
					</div>

					<div className="metric-row">
						<span className="metric-label">Budget Utilization</span>
						<span className="metric-value">{totalLE.toLocaleString()} LE</span>
					</div>
					<div className="progress-bar">
						<div className="progress-fill" style={{ width: `${Math.min((totalLE / 100000) * 100, 100)}%` }}></div>
					</div>
					<div className="metric-row">
						<span className="metric-label">Quantity Target</span>
						<span className="metric-value">{totalQuantity.toLocaleString()} Units</span>
					</div>
					<div className="progress-bar">
						<div className="progress-fill" style={{ width: `${Math.min((totalQuantity / 1000) * 100, 100)}%` }}></div>
					</div>
				</div>
				<div className="chart-card">
					<h3 className="chart-title">📅 Timeline Analysis</h3>
					<div className="metric-row">
						<span className="metric-label">Project Start</span>
						<span className="metric-value">
							{earliestStart ? earliestStart.toLocaleDateString() : 'Not Set'}
						</span>
					</div>
					<div className="metric-row">
						<span className="metric-label">Project End</span>
						<span className="metric-value">
							{latestEnd ? latestEnd.toLocaleDateString() : 'Not Set'}
						</span>
					</div>

					<div className="metric-row">
						<span className="metric-label">Duration</span>
						<span className="metric-value">
							{earliestStart && latestEnd
								? `${Math.ceil((latestEnd - earliestStart) / (1000 * 60 * 60 * 24))} days`
								: 'TBD'}
						</span>
					</div>

					<div className="metric-row">
						<span className="metric-label">Active Regions</span>
						<span className="metric-value">{Object.keys(regionCounts).length}</span>
					</div>

					<div className="metric-row">
						<span className="metric-label">Efficiency Rate</span>
						<span className="metric-value">
							{totalItems > 0 ? `${((totalLE / totalItems) / 1000).toFixed(1)}K LE/Item` : '0'}
						</span>
					</div>
				</div>
			</div>

			{/* Alerts */}
			{error && <div className="dashboard-alert dashboard-alert-error">⚠️ {error}</div>}
			{success && <div className="dashboard-alert dashboard-alert-success">✅ {success}</div>}

			{/* Stats Carousel */}
			<StatsCarousel cards={statCards} visibleCount={4} />
			{/* Filter Bar */}
			<FilterBar
				searchTerm={searchQuery}
				onSearchChange={(e) => setSearchQuery(e.target.value)}
				searchPlaceholder="Search by Item Name, Region, or Product Number..."
				showClearButton={!!searchQuery}
				onClearSearch={() => setSearchQuery('')}
			/>

			{/* Draft Restoration Prompt */}
			{showDraftPrompt && loadedDraft && (
				<div className="modal-overlay" style={{ zIndex: 1001 }}>
					<div className="modal-container" style={{ maxWidth: '500px', width: '90%' }}>
						<div className="modal-header" style={{ background: 'linear-gradient(135deg, #e0f2fe 0%, #bae6fd 100%)', borderBottom: '3px solid #0284c7' }}>
							<div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
								<span style={{ fontSize: '1.5rem' }}>💾</span>
								<h2 className="modal-title" style={{ color: '#0c4a6e' }}>Draft Found</h2>
							</div>
						</div>
						<div style={{ padding: '1.5rem' }}>
							<p style={{ marginBottom: '1rem', color: '#374151', fontSize: '0.95rem' }}>
								We found an unsaved draft from <strong>{getTimeSince(loadedDraft.timestamp)}</strong>.
							</p>
							<div style={{
								backgroundColor: '#f8fafc',
								padding: '1rem',
								borderRadius: '8px',
								marginBottom: '1.5rem',
								border: '1px solid #e2e8f0'
							}}>
								<div style={{ marginBottom: '0.5rem' }}>
									<strong style={{ color: '#124191' }}>Package Name:</strong>
									<span style={{ marginLeft: '0.5rem', color: '#1f2937' }}>{loadedDraft.formData.package_name}</span>
								</div>
								<div style={{ marginBottom: '0.5rem' }}>
									<strong style={{ color: '#124191' }}>Quantity:</strong>
									<span style={{ marginLeft: '0.5rem', color: '#1f2937' }}>{loadedDraft.formData.quantity || 'Not set'}</span>
								</div>
								<div>
									<strong style={{ color: '#124191' }}>PCI Items Selected:</strong>
									<span style={{ marginLeft: '0.5rem', color: '#1f2937' }}>
										{loadedDraft.selectedLvl1Items?.length || 0} item(s)
									</span>
								</div>
							</div>
							<p style={{ fontSize: '0.9rem', color: '#6b7280', marginBottom: '1.5rem' }}>
								Would you like to continue where you left off?
							</p>
							<div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'flex-end' }}>
								<button
									type="button"
									onClick={handleDiscardDraft}
									style={{
										padding: '0.625rem 1.25rem',
										backgroundColor: '#ef4444',
										color: 'white',
										border: 'none',
										borderRadius: '6px',
										fontSize: '0.95rem',
										fontWeight: '500',
										cursor: 'pointer',
										transition: 'all 0.2s'
									}}
									onMouseOver={(e) => e.target.style.backgroundColor = '#dc2626'}
									onMouseOut={(e) => e.target.style.backgroundColor = '#ef4444'}
								>
									Discard & Start Fresh
								</button>
								<button
									type="button"
									onClick={handleRestoreDraft}
									style={{
										padding: '0.625rem 1.25rem',
										backgroundColor: '#10b981',
										color: 'white',
										border: 'none',
										borderRadius: '6px',
										fontSize: '0.95rem',
										fontWeight: '500',
										cursor: 'pointer',
										transition: 'all 0.2s'
									}}
									onMouseOver={(e) => e.target.style.backgroundColor = '#059669'}
									onMouseOut={(e) => e.target.style.backgroundColor = '#10b981'}
								>
									Restore Draft
								</button>
							</div>
						</div>
					</div>
				</div>
			)}

			{/* Package Creation Form Modal */}
			{showForm && (
				<div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && setShowForm(false)}>
					<div className="modal-container" style={{ maxWidth: '1200px', width: '95%' }}>
						<div className="modal-header">
							<h2 className="modal-title">Create New Package</h2>
							<button
								className="modal-close"
								onClick={() => setShowForm(false)}
								type="button"
							>✕</button>
						</div>
						<form className="modal-form" onSubmit={handleSubmit}>
							<div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1rem' }}>
								<div className="form-field">
									<label>Project ID</label>
									<input
										type="text"
										value={formData.project_id}
										disabled
										style={{ backgroundColor: '#f5f5f5', cursor: 'not-allowed' }}
									/>
								</div>
								<div className="form-field">
									<label>Project Name</label>
									<input
										type="text"
										value={formData.project_name}
										disabled
										style={{ backgroundColor: '#f5f5f5', cursor: 'not-allowed' }}
									/>
								</div>
							</div>

							<div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '1rem', marginBottom: '1rem' }}>
								<div className="form-field">
									<label>Package Name *</label>
									<input
										type="text"
										value={formData.package_name}
										onChange={e => setFormData({ ...formData, package_name: e.target.value })}
										required
										placeholder="Enter package name"
									/>
								</div>
								<div className="form-field">
									<label>Quantity</label>
									<input
										type="number"
										value={formData.quantity}
										onChange={e => setFormData({ ...formData, quantity: e.target.value })}
										placeholder="Enter quantity"
									/>
								</div>
								<div className="form-field">
									<label>Revenue Lead Time (days)</label>
									<input
										type="number"
										value={formData.lead_time || ''}
										onChange={e => setFormData({ ...formData, lead_time: e.target.value })}
										placeholder="Lead time in days"
									/>
								</div>
							</div>

							<div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1.5rem' }}>
								<div className="form-field">
									<label>Start Date</label>
									<input
										type="date"
										value={formData.start_date}
										onChange={e => setFormData({ ...formData, start_date: e.target.value })}
									/>
								</div>
								<div className="form-field">
									<label>End Date</label>
									<input
										type="date"
										value={formData.end_date}
										onChange={e => setFormData({ ...formData, end_date: e.target.value })}
									/>
								</div>
							</div>

							{/* Monthly Distribution Table */}
							{monthlyPeriods.length > 0 && (
								<div style={{ marginBottom: 20, border: '1px solid #e0e0e0', borderRadius: '8px', padding: '16px', backgroundColor: '#f9f9f9' }}>
									<div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
										<h4 style={{ margin: 0, color: '#333', fontSize: '1.1em' }}>Monthly Distribution</h4>
										<button
											type="button"
											onClick={handleAutoDistribute}
											disabled={!formData.quantity}
											style={{
												backgroundColor: '#4CAF50',
												color: 'white',
												border: 'none',
												padding: '8px 16px',
												borderRadius: '4px',
												cursor: formData.quantity ? 'pointer' : 'not-allowed',
												fontSize: '0.9em',
												opacity: formData.quantity ? 1 : 0.6
											}}
										>
											Auto Distribute
										</button>
									</div>

									{distributionError && (
										<div style={{
											backgroundColor: '#ffebee',
											border: '1px solid #f44336',
											color: '#d32f2f',
											padding: '10px',
											borderRadius: '4px',
											marginBottom: '12px',
											fontSize: '0.9em'
										}}>
											⚠️ {distributionError}
										</div>
									)}

									<div style={{ maxHeight: '200px', overflowY: 'auto' }}>
										<table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.95em' }}>
											<thead>
												<tr style={{ backgroundColor: '#e3f2fd' }}>
													<th style={{ padding: '8px 12px', borderBottom: '2px solid #1976d2', textAlign: 'left', fontWeight: 600 }}>Month</th>
													<th style={{ padding: '8px 12px', borderBottom: '2px solid #1976d2', textAlign: 'center', fontWeight: 600 }}>Quantity</th>
												</tr>
											</thead>
											<tbody>
												{monthlyPeriods.map((period, index) => {
													const distribution = monthlyDistributions.find(d => d.year === period.year && d.month === period.month);
													return (
														<tr key={`${period.year}-${period.month}`} style={{ borderBottom: '1px solid #e0e0e0' }}>
															<td style={{ padding: '10px 12px', fontWeight: 500 }}>
																{period.display}
															</td>
															<td style={{ padding: '8px 12px', textAlign: 'center' }}>
																<input
																	type="number"
																	min="0"
																	value={distribution?.quantity || 0}
																	onChange={e => handleMonthlyQuantityChange(period.year, period.month, e.target.value)}
																	style={{
																		width: '80px',
																		padding: '6px 8px',
																		border: '1px solid #ccc',
																		borderRadius: '4px',
																		textAlign: 'center',
																		fontSize: '0.9em'
																	}}
																/>
															</td>
														</tr>
													);
												})}
											</tbody>
											<tfoot>
												<tr style={{ backgroundColor: '#f5f5f5', fontWeight: 'bold' }}>
													<td style={{ padding: '10px 12px', borderTop: '2px solid #1976d2' }}>Total:</td>
													<td style={{ padding: '10px 12px', textAlign: 'center', borderTop: '2px solid #1976d2' }}>
														{monthlyDistributions.reduce((sum, d) => sum + (parseInt(d.quantity) || 0), 0)}
													</td>
												</tr>
											</tfoot>
										</table>
									</div>
								</div>
							)}

							<div className="form-group" style={{ position: 'relative' }}>
								<label htmlFor="lvl1-select">Select PCI Items:</label>
								<div
									className="custom-dropdown-select"
									onClick={() => {
										setShowLvl1Dropdown(!showLvl1Dropdown);
										if (!showLvl1Dropdown) {
											setPciSearchQuery(''); // Clear search when opening dropdown
										}
									}}
									style={{
										padding: '16px',
										border: '1.5px solid #1976d2',
										borderRadius: '6px',
										cursor: 'pointer',
										backgroundColor: '#fff',
										display: 'flex',
										justifyContent: 'space-between',
										alignItems: 'center',
										fontSize: '1.1em',
										minWidth: 320,
										maxWidth: '100%',
									}}
								>
									{selectedLvl1Items.length > 0
										? `${selectedLvl1Items.length} item(s) selected`
										: 'Click to select items'}
									<span>{showLvl1Dropdown ? '▲' : '▼'}</span>
								</div>
								{showLvl1Dropdown && (
									<div
										style={{
											position: 'absolute',
											top: '100%',
											left: 0,
											zIndex: 100,
											minWidth: 820,
											maxWidth: 1200,
											border: '1.5px solid #1976d2',
											borderRadius: '6px',
											backgroundColor: '#fff',
											maxHeight: '400px',
											display: 'flex',
											flexDirection: 'column',
											fontSize: '0.92em',
										}}
									>
										{/* Search Bar */}
										<div style={{
											padding: '12px',
											borderBottom: '1.5px solid #e0e0e0',
											backgroundColor: '#f8f9fa',
											position: 'sticky',
											top: 0,
											zIndex: 1
										}}>
											<input
												type="text"
												placeholder="🔍 Search PCI items..."
												value={pciSearchQuery}
												onChange={(e) => setPciSearchQuery(e.target.value)}
												onClick={(e) => e.stopPropagation()}
												style={{
													width: '100%',
													padding: '10px 12px',
													border: '1.5px solid #1976d2',
													borderRadius: '6px',
													fontSize: '0.95em',
													outline: 'none',
													backgroundColor: '#fff'
												}}
											/>
										</div>

										{/* Items List */}
										<div style={{ overflowY: 'auto', maxHeight: '340px' }}>
											{(() => {
												const filteredEntries = entries.filter(entry => {
													if (!pciSearchQuery.trim()) return true;
													const searchLower = pciSearchQuery.toLowerCase();
													return (
														entry.item_name?.toLowerCase().includes(searchLower) ||
														entry.product_number?.toLowerCase().includes(searchLower) ||
														entry.region?.toLowerCase().includes(searchLower)
													);
												});

												if (filteredEntries.length === 0) {
													return (
														<div style={{
															padding: '30px 20px',
															textAlign: 'center',
															color: '#999',
															fontSize: '0.95em'
														}}>
															<div style={{ fontSize: '2em', marginBottom: '10px' }}>🔍</div>
															<div>No PCI items found matching "{pciSearchQuery}"</div>
														</div>
													);
												}

												return filteredEntries.map(entry => {
											const isSelected = selectedLvl1Items.some(item => item.id === entry.id);
											const selectedItem = selectedLvl1Items.find(item => item.id === entry.id);
											const lvl2Children = lvl2Items[entry.id] || [];

											return (
												<div key={entry.id} style={{ borderBottom: '1px solid #f0f0f0' }}>
													{/* Level 1 Item */}
													<div
														style={{
															padding: '8px 10px',
															cursor: 'pointer',
															backgroundColor: isSelected ? '#e6f7ff' : 'transparent',
															display: 'flex',
															alignItems: 'center',
															borderBottom: lvl2Children.length > 0 ? '1px solid #e8f4f8' : 'none'
														}}
													>
														<input
															type="checkbox"
															checked={isSelected}
															onChange={() => handleSelectLvl1Item(entry)}
															style={{ marginRight: '10px', width: 16, height: 16 }}
														/>
														<span style={{ flexGrow: 1, fontWeight: '600', color: '#1976d2' }}>
															📦 {entry.item_name}
														</span>
														{entry.calculatedUnitPrice > 0 && (
															<span style={{
																fontSize: '0.85em',
																color: '#666',
																marginRight: '10px',
																backgroundColor: '#f5f5f5',
																padding: '2px 6px',
																borderRadius: '3px'
															}}>
																{entry.calculatedUnitPrice.toFixed(2)} {cur}
															</span>
														)}
														<span style={{
															marginRight: '10px',
															color: '#666',
															fontSize: '0.8em',
															backgroundColor: '#f5f5f5',
															padding: '2px 6px',
															borderRadius: '3px'
														}}>
															Available: {entry.total_quantity - (entry.consumption || 0) || 0}
														</span>
														{isSelected && (
															<span style={{ display: 'flex', alignItems: 'center' }}>
																<span style={{ fontWeight: 600, fontSize: '1.08em', marginRight: 6 }}>Qty:</span>
																<input
																	type="number"
																	placeholder="Quantity"
																	value={selectedItem.quantity}
																	onChange={e => handleQuantityChange(entry.id, e.target.value)}
																	style={{
																		width: '120px',
																		fontSize: '1.08em',
																		padding: '6px 10px',
																		borderRadius: '4px',
																		border: (() => {
																			const selectedQty = parseInt(selectedItem.quantity) || 0;
																			const availableQty = parseInt(entry.total_quantity) || 0;
																			const packageQty = parseInt(formData.quantity) || 1;
																			const totalNeeded = selectedQty * packageQty;

																			if (selectedQty > availableQty || totalNeeded > availableQty) {
																				return '2px solid #f44336'; // Red border for error
																			}
																			return '1px solid #1976d2'; // Normal blue border
																		})(),
																		backgroundColor: (() => {
																			const selectedQty = parseInt(selectedItem.quantity) || 0;
																			const availableQty = parseInt(entry.total_quantity) || 0;
																			const packageQty = parseInt(formData.quantity) || 1;
																			const totalNeeded = selectedQty * packageQty;

																			if (selectedQty > availableQty || totalNeeded > availableQty) {
																				return '#ffebee'; // Light red background for error
																			}
																			return 'white';
																		})()
																	}}
																	onClick={e => e.stopPropagation()}
																/>
																{(() => {
																	const selectedQty = parseInt(selectedItem.quantity) || 0;
																	const availableQty = entry.total_quantity - (entry.consumption || 0) || 0
																	const packageQty = parseInt(formData.quantity) || 1;
																	const totalNeeded = selectedQty * packageQty;

																	if (selectedQty > availableQty) {
																		return (
																			<span style={{
																				marginLeft: '8px',
																				color: '#f44336',
																				fontSize: '0.85em',
																				fontWeight: '500'
																			}}>
																				⚠️ Exceeds available ({availableQty})
																			</span>
																		);
																	} else if (totalNeeded > availableQty) {
																		return (
																			<span style={{
																				marginLeft: '8px',
																				color: '#f44336',
																				fontSize: '0.85em',
																				fontWeight: '500'
																			}}>
																				⚠️ Total needed: {totalNeeded} {'>'} {availableQty}
																			</span>
																		);
																	}
																	return null;
																})()}
															</span>
														)}
													</div>

													{/* Level 2 Items (if any) */}
													{lvl2Children.length > 0 && (
														<div style={{
															backgroundColor: '#f8fdff',
															paddingLeft: '30px',
															maxHeight: '120px',
															overflowY: 'auto'
														}}>
															{lvl2Children.map(lvl2 => (
																<div
																	key={lvl2.id}
																	style={{
																		padding: '4px 10px',
																		fontSize: '0.88em',
																		color: '#555',
																		borderBottom: '1px solid #f0f8ff',
																		display: 'flex',
																		alignItems: 'center',
																		justifyContent: 'space-between'
																	}}
																>
																	<span style={{ display: 'flex', alignItems: 'center' }}>
																		<span style={{ marginRight: '8px', color: '#888' }}>└─</span>
																		<span style={{ fontWeight: '500' }}>
																			🔧 {lvl2.item_name}
																		</span>
																		{lvl2.product_number && (
																			<span style={{
																				marginLeft: '8px',
																				color: '#888',
																				fontSize: '0.85em',
																				fontStyle: 'italic'
																			}}>
																				({lvl2.product_number})
																			</span>
																		)}
																	</span>
																	<div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
																		{lvl2.total_quantity && (
																			<span style={{
																				fontSize: '0.8em',
																				color: '#666',
																				backgroundColor: '#fff',
																				padding: '1px 4px',
																				borderRadius: '2px',
																				border: '1px solid #e0e0e0'
																			}}>
																				Qty: {lvl2.total_quantity.toLocaleString()}
																			</span>
																		)}
																		{lvl2.price && (
																			<span style={{
																				fontSize: '0.8em',
																				color: '#2e7d32',
																				backgroundColor: '#fff',
																				padding: '1px 4px',
																				borderRadius: '2px',
																				border: '1px solid #e0e0e0',
																				fontWeight: '500'
																			}}>
																				{lvl2.price.toFixed(2)} {cur}
																			</span>
																		)}
																	</div>
																</div>
															))}
														</div>
													)}

													{/* No Level 2 items indicator */}
													{lvl2Children.length === 0 && (
														<div style={{
															paddingLeft: '30px',
															padding: '4px 10px 4px 30px',
															fontSize: '0.85em',
															color: '#999',
															fontStyle: 'italic',
															backgroundColor: '#fafafa'
														}}>
															└─ No SI items configured
														</div>
													)}
												</div>
											);
										});
											})()}
										</div>
									</div>
								)}
							</div>
							<div className="form-group">
								<label>Associated SI Items:</label>
								<div style={{ border: '1px solid #ccc', padding: '10px', maxHeight: '150px', overflowY: 'auto' }}>
									{selectedLvl1Items.length === 0 ? (
										<p style={{ color: '#888' }}>Select Lvl1 items to see their Lvl2 details.</p>
									) : (
										selectedLvl1Items.map(item => (
											<div key={item.id} style={{ marginBottom: '10px' }}>
												<strong>Lvl1 Item ID: {item.id} (Quantity: {item.quantity || 'Not specified'})</strong>
												<ul>
													{(lvl2Details[item.id] || []).length > 0 ? (
														lvl2Details[item.id].map(lvl2 => (
															<li key={lvl2.id}>
																{lvl2.item_name} (ID: {lvl2.id})
															</li>
														))
													) : (
														<li>Loading Lvl2 items...</li>
													)}
												</ul>
											</div>
										))
									)}
								</div>
							</div>

							<div style={{ marginTop: '1.5rem', paddingTop: '1.5rem', borderTop: '2px solid #e5e7eb' }}>
								<div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', padding: '1rem', backgroundColor: '#f8f9fa', borderRadius: '8px' }}>
									<div>
										<div style={{ fontSize: '0.9rem', color: '#6b7280', marginBottom: '0.25rem' }}>Package Price</div>
										<div style={{ fontSize: '1.5rem', fontWeight: '600', color: '#124191' }}>
											{calculatedPackagePrice.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })} {cur}
										</div>
									</div>
									<div style={{ textAlign: 'right' }}>
										<div style={{ fontSize: '0.9rem', color: '#6b7280', marginBottom: '0.25rem' }}>Total Price</div>
										<div style={{ fontSize: '1.5rem', fontWeight: '600', color: '#124191' }}>
											{calculatedTotalPrice.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })} {cur}
										</div>
									</div>
								</div>
							</div>

							<div className="form-actions">
								<button type="button" className="btn-cancel" onClick={() => setShowForm(false)}>
									Cancel
								</button>
								<button type="submit" className="btn-submit" disabled={distributionError && monthlyPeriods.length > 0}>
									Create Package
								</button>
							</div>
						</form>
					</div>
				</div>
			)}

			{/* Lvl1 Form Modal */}
			{showLvl1Form && (
				<div className="dashboard-modal">
					<div className="dashboard-modal-content" style={{ minWidth: 700, maxWidth: 900, margin: '0 auto' }}>
						<div className="dashboard-modal-header">
							<h2 className="dashboard-modal-title">
								{isEditing ? '✏️ Edit ROP Lvl1' : '✨ Create New ROP Lvl1'}
							</h2>
							<button
								className="dashboard-modal-close"
								onClick={() => setShowLvl1Form(false)}
								type="button"
							>✕</button>
						</div>
						<form className="dashboard-form" onSubmit={handleLvl1Submit}>
							<div style={{ display: 'flex', gap: 20, marginBottom: 15 }}>
								<input
									type="text"
									placeholder="Project ID"
									value={lvl1FormData.project_id}
									disabled
									style={{ flex: 1 }}
								/>
								<input
									type="text"
									placeholder="Project Name"
									value={lvl1FormData.project_name}
									disabled
									style={{ flex: 1 }}
								/>
							</div>
							<div style={{ display: 'flex', gap: 20, marginBottom: 15 }}>
								<input
									type="text"
									placeholder="Item ID"
									value={lvl1FormData.id}
									onChange={e => setLvl1FormData({ ...lvl1FormData, id: e.target.value })}
									required
									disabled={isEditing}
									style={{ flex: 1 }}
								/>
								<input
									type="text"
									placeholder="Item Name"
									value={lvl1FormData.item_name}
									onChange={e => setLvl1FormData({ ...lvl1FormData, item_name: e.target.value })}
									required
									style={{ flex: 1 }}
								/>
							</div>
							<div style={{ display: 'flex', gap: 20, marginBottom: 15 }}>
								<input
									type="text"
									placeholder="Region"
									value={lvl1FormData.region}
									onChange={e => setLvl1FormData({ ...lvl1FormData, region: e.target.value })}
									style={{ flex: 1 }}
								/>
								<input
									type="text"
									placeholder="Product Number"
									value={lvl1FormData.product_number}
									onChange={e => setLvl1FormData({ ...lvl1FormData, product_number: e.target.value })}
									style={{ flex: 1 }}
								/>
							</div>
							<div style={{ display: 'flex', gap: 20, marginBottom: 15 }}>
								<input
									type="number"
									placeholder="Total Quantity"
									value={lvl1FormData.total_quantity}
									onChange={e => setLvl1FormData({ ...lvl1FormData, total_quantity: e.target.value })}
									style={{ flex: 1 }}
								/>
								<input
									type="number"
									step="0.01"
									placeholder="Price"
									value={lvl1FormData.price}
									onChange={e => setLvl1FormData({ ...lvl1FormData, price: e.target.value })}
									style={{ flex: 1 }}
								/>
							</div>
							<div style={{ display: 'flex', gap: 20, marginBottom: 15 }}>
								<div style={{ flex: 1 }}>
									<label>Start Date:</label>
									<input
										type="date"
										value={lvl1FormData.start_date}
										onChange={e => setLvl1FormData({ ...lvl1FormData, start_date: e.target.value })}
										style={{ width: '100%' }}
									/>
								</div>
								<div style={{ flex: 1 }}>
									<label>End Date:</label>
									<input
										type="date"
										value={lvl1FormData.end_date}
										onChange={e => setLvl1FormData({ ...lvl1FormData, end_date: e.target.value })}
										style={{ width: '100%' }}
									/>
								</div>
							</div>
							<button type="submit">
								{isEditing ? '💾 Update Lvl1' : '🚀 Create Lvl1'}
							</button>
						</form>
					</div>
				</div>
			)}

			{/* Lvl2 Form Modal */}
			{showLvl2Form && (
				<div className="dashboard-modal">
					<div className="dashboard-modal-content" style={{ minWidth: 700, maxWidth: 900, margin: '0 auto' }}>
						<div className="dashboard-modal-header">
							<h2 className="dashboard-modal-title">
								{isEditing ? '✏️ Edit ROP Lvl2' : '✨ Create New ROP Lvl2'}
							</h2>
							<button
								className="dashboard-modal-close"
								onClick={() => setShowLvl2Form(false)}
								type="button"
							>✕</button>
						</div>
						<form className="dashboard-form" onSubmit={handleLvl2Submit}>
							<div style={{ display: 'flex', gap: 20, marginBottom: 15 }}>
								<input
									type="text"
									placeholder="Project ID"
									value={lvl2FormData.project_id}
									disabled
									style={{ flex: 1 }}
								/>
								<input
									type="text"
									placeholder="Lvl1 Item Name"
									value={lvl2FormData.lvl1_item_name}
									disabled
									style={{ flex: 1 }}
								/>
							</div>
							<div style={{ display: 'flex', gap: 20, marginBottom: 15 }}>
								<input
									type="text"
									placeholder="Item ID"
									value={lvl2FormData.id}
									onChange={e => setLvl2FormData({ ...lvl2FormData, id: e.target.value })}
									required
									disabled={isEditing}
									style={{ flex: 1 }}
								/>
								<input
									type="text"
									placeholder="Item Name"
									value={lvl2FormData.item_name}
									onChange={e => setLvl2FormData({ ...lvl2FormData, item_name: e.target.value })}
									required
									style={{ flex: 1 }}
								/>
							</div>
							<div style={{ display: 'flex', gap: 20, marginBottom: 15 }}>
								<input
									type="text"
									placeholder="Region"
									value={lvl2FormData.region}
									onChange={e => setLvl2FormData({ ...lvl2FormData, region: e.target.value })}
									required
									style={{ flex: 1 }}
								/>
								<input
									type="text"
									placeholder="Product Number"
									value={lvl2FormData.product_number}
									onChange={e => setLvl2FormData({ ...lvl2FormData, product_number: e.target.value })}
									style={{ flex: 1 }}
								/>
							</div>
							<div style={{ display: 'flex', gap: 20, marginBottom: 15 }}>
								<input
									type="number"
									placeholder="Total Quantity"
									value={lvl2FormData.total_quantity}
									onChange={e => setLvl2FormData({ ...lvl2FormData, total_quantity: e.target.value })}
									required
									style={{ flex: 1 }}
								/>
								<input
									type="number"
									step="0.01"
									placeholder="Price"
									value={lvl2FormData.price}
									onChange={e => setLvl2FormData({ ...lvl2FormData, price: e.target.value })}
									required
									style={{ flex: 1 }}
								/>
							</div>
							<div style={{ display: 'flex', gap: 20, marginBottom: 15 }}>
								<div style={{ flex: 1 }}>
									<label>Start Date:</label>
									<input
										type="date"
										value={lvl2FormData.start_date}
										onChange={e => setLvl2FormData({ ...lvl2FormData, start_date: e.target.value })}
										required
										style={{ width: '100%' }}
									/>
								</div>
								<div style={{ flex: 1 }}>
									<label>End Date:</label>
									<input
										type="date"
										value={lvl2FormData.end_date}
										onChange={e => setLvl2FormData({ ...lvl2FormData, end_date: e.target.value })}
										required
										style={{ width: '100%' }}
									/>
								</div>
							</div>
							<button type="submit">
								{isEditing ? '💾 Update Lvl2' : '🚀 Create Lvl2'}
							</button>
						</form>
					</div>
				</div>
			)}

			{/* Main Content Section */}
			<div className="dashboard-content-section">
				<div className="data-table-wrapper">
					{filteredEntries.length > 0 ? (
						<table className="data-table">
							<thead>
								<tr>
									
									<th></th>
									<th style={{ textAlign: 'center' }}>Product Number</th>
									<th style={{ textAlign: 'center' }}>PCI Name</th>
									<th style={{ textAlign: 'center' }}>Quantity</th>
									<th style={{ textAlign: 'center' }}>Unit Price</th>
									<th style={{ textAlign: 'center' }}>Total Price</th>
									<th style={{ textAlign: 'center' }}>Actions</th>
								</tr>
							</thead>
							<tbody>
								{paginatedEntries.map(entry => (
									<>
										<tr key={entry.id}>
											<td>
												<button
													style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: '1.2rem' }}
													onClick={async () => {
														setExpandedRows(prev => ({ ...prev, [entry.id]: !prev[entry.id] }));
														if (!lvl2Items[entry.id]) await fetchLvl2Items(entry.id);
													}}
													aria-label={expandedRows[entry.id] ? 'Collapse' : 'Expand'}
												>
													{expandedRows[entry.id] ? '▼' : '▶'}
												</button>
											</td>
											<td>{entry.product_number || '-'}</td>
											<td><strong>{entry.item_name}</strong></td>
											<td>{entry.total_quantity?.toLocaleString() || '-'}</td>
											<td>{entry.calculatedUnitPrice ? `${entry.calculatedUnitPrice.toFixed(2)}` : '0.00'} {cur}</td>
											<td>
												<strong style={{ color: 'var(--nokia-success)' }}>
													{((entry.total_quantity || 0) * (entry.calculatedUnitPrice || 0)).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })} {cur}
												</strong>
											</td>
											<td>
												<div style={{ display: 'flex', gap: '8px', justifyContent: 'center' }}>
													<button
														onClick={() => handleCreateLvl2(entry)}
														style={{
															background: '#4caf50',
															color: 'white',
															border: 'none',
															padding: '4px 8px',
															borderRadius: '3px',
															cursor: 'pointer',
															fontSize: '11px',
															visibility: 'hidden'
														}}
													>
														Add SI
													</button>
													<button
														onClick={() => handleEditLvl1(entry)}
														className="btn-action btn-edit"
														title="Edit PCI"
													>
														✏️
													</button>
													<button
														onClick={() => handleDeleteLvl1(entry.id)}
														className="btn-action btn-delete"
														title="Delete PCI"
													>
														🗑️
													</button>
												</div>
											</td>
										</tr>
										{expandedRows[entry.id] && (
											<tr>
												<td colSpan={7} style={{ background: '#f6f8fc', padding: 0 }}>
													<div style={{ width: '100%' }}>
														<table style={{ width: '100%', borderCollapse: 'collapse' }}>
															<thead>
																<tr>
																	<th style={{ textAlign: 'center' }}>Product Number</th>
																	<th style={{ textAlign: 'center' }}>SI Name</th>
																	<th style={{ textAlign: 'center' }}>Quantity</th>
																	<th style={{ textAlign: 'center' }}>Price</th>
																	<th style={{ textAlign: 'center' }}>Total Price</th>
																	<th style={{ textAlign: 'center' }}>Actions</th>
																</tr>
															</thead>
															<tbody>
																{(lvl2Items[entry.id] || []).map(lvl2 => (
																	<tr key={lvl2.id}>
																		<td>{lvl2.product_number || '-'}</td>
																		<td>{lvl2.item_name}</td>
																		<td>{lvl2.total_quantity?.toLocaleString() || '-'}</td>
																		<td>{lvl2.price ? `${lvl2.price.toFixed(2)} ${cur}` : '-'}</td>
																		<td>{((lvl2.total_quantity || 0) * (lvl2.price || 0)).toLocaleString()} {cur}</td>
																		<td>
																			<div style={{ display: 'flex', gap: '4px', justifyContent: 'center' }}>
																				<button
																					onClick={() => handleEditLvl2(lvl2)}
																					style={{
																						background: '#2196f3',
																						color: 'white',
																						border: 'none',
																						padding: '4px 8px',
																						borderRadius: '3px',
																						cursor: 'pointer',
																						fontSize: '11px'
																					}}
																				>
																					Details
																				</button>
																				<button
																					onClick={() => handleDeleteLvl2(lvl2.id, entry.id)}
																					style={{
																						background: '#f44336',
																						color: 'white',
																						border: 'none',
																						padding: '4px 8px',
																						borderRadius: '3px',
																						cursor: 'pointer',
																						fontSize: '11px'
																					}}
																				>
																					Delete
																				</button>
																			</div>
																		</td>
																	</tr>
																))}
																{(lvl2Items[entry.id] && lvl2Items[entry.id].length === 0) && (
																	<tr>
																		<td colSpan={6} style={{ textAlign: 'center', color: '#888' }}>No Level 2 items found.</td>
																	</tr>
																)}
															</tbody>
														</table>
													</div>
												</td>
											</tr>
										)}
									</>
								))}
							</tbody>
						</table>
					) : (
						<div className="dashboard-empty-state">
							<div className="dashboard-empty-icon">📋</div>
							<div className="dashboard-empty-text">
								{searchQuery ? `No entries found matching "${searchQuery}". Try a different search term.` : 'No entries found. Create your first entry to get started!'}
							</div>
						</div>
					)}
				</div>

				{totalPages > 1 && (
					<Pagination
						currentPage={currentPage}
						totalPages={totalPages}
						onPageChange={(page) => setCurrentPage(page)}
					/>
				)}
			</div>

			{/* Help Modal */}
			<HelpModal
				show={showHelpModal}
				onClose={() => setShowHelpModal(false)}
				title="ROP Level 1 Analytics - User Guide"
				sections={helpSections}
			/>
		</div>
	);
}