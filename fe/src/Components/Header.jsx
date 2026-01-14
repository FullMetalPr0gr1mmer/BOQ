import { NavLink, useNavigate, useLocation } from 'react-router-dom';
import { useState, useEffect } from 'react';
import { apiCall } from '../api';
import '../css/header.css';

const boqTabs = ['Project', 'Site', 'Inventory', 'Level1', 'Level3', 'BOQ Generation', 'LLD', 'Dismantling', 'LogOut'];
const leAutomationTabs = ['ROP Project', 'ROP Package', 'LogOut'];
const ranBoqTabs = ['Ran Projects', 'RAN BOQ Generation', 'Ran Level3', 'Ran Inventory', 'Ran Antenna Serials', 'LogOut'];
const du5gTabs = ['DU Projects', 'DU BOQ Generation', 'DU BOQ Items', 'DU Customer PO', 'LogOut'];

export default function Header({ onLogout, activeSection, user }) {
  const navigate = useNavigate();
  const location = useLocation();
  const [approvalPermissions, setApprovalPermissions] = useState({
    can_access_approval: false,
    can_access_triggering: false,
    can_access_logistics: false
  });

  // Fetch approval permissions on mount
  useEffect(() => {
    const fetchPermissions = async () => {
      try {
        const data = await apiCall('/approvals/user/permissions');
        setApprovalPermissions({
          can_access_approval: data.can_access_approval,
          can_access_triggering: data.can_access_triggering,
          can_access_logistics: data.can_access_logistics
        });
      } catch (error) {
        console.error('Failed to fetch approval permissions:', error);
      }
    };
    fetchPermissions();
  }, []);

  // Hide the header if the current path is the home page
  if (location.pathname === '/*' || location.pathname === '/logs' || location.pathname === '/') {
    return null;
  }

  // Show approval tabs when on approvals page
  const isApprovalsPage = location.pathname.startsWith('/approvals') || location.pathname.startsWith('/triggering') || location.pathname.startsWith('/logistics');

  // Build approval tabs based on user permissions
  const approvalTabs = [];
  if (approvalPermissions.can_access_approval) {
    approvalTabs.push('Approvals');
  }
  if (approvalPermissions.can_access_triggering) {
    approvalTabs.push('Triggering');
  }
  if (approvalPermissions.can_access_logistics) {
    approvalTabs.push('Logistics');
  }
  approvalTabs.push('LogOut');

  let tabs = activeSection === 'le-automation' ? leAutomationTabs : boqTabs;
  if (isApprovalsPage) {
    tabs = approvalTabs;
  } else if (activeSection === 'ran-boq') {
    tabs = ranBoqTabs;
  } else if (activeSection === 'du-5g') {
    tabs = du5gTabs;
  }
  // Hide Level1 tab
  tabs = tabs.filter(tab => tab !== 'Level1');

  const handleTabClick = (tab, e) => {
    if (tab === 'LogOut') {
      e.preventDefault();
      onLogout();
      navigate('/');
    }
  };

  return (
    <header className="nokia-header">
      <div className="logo"><img src='logo.svg' alt="Logo" /></div>
      <nav className="tabs">
        {tabs.map(tab => (
          <NavLink
            key={tab}
            to={tab === 'LogOut' ? '#' : `/${tab.toLowerCase().replace(/ /g, '-')}`}
            className={({ isActive }) =>
              tab !== 'LogOut' && isActive ? 'tab active' : 'tab'
            }
            onClick={(e) => handleTabClick(tab, e)}
          >
            {tab}
          </NavLink>
        ))}
      </nav>
    </header>
  );
}