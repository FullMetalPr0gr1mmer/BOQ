import { NavLink, useNavigate, useLocation } from 'react-router-dom';
import '../css/header.css';

const boqTabs = ['Project', 'Site', 'Inventory', 'Level1', 'Level3', 'BOQ Generation', 'LLD', 'Dismantling', 'LogOut'];
const leAutomationTabs = ['ROP Project', 'ROP Package', 'LogOut'];
const ranBoqTabs = ['Ran Projects', 'RAN BOQ Generation', 'Ran Level3', 'Ran Inventory', 'Ran Antenna Serials', 'LogOut']
export default function Header({ onLogout, activeSection, user }) {
  const navigate = useNavigate();
  const location = useLocation();

  // Hide the header if the current path is the home page
  if (location.pathname === '/*' || location.pathname === '/logs' || location.pathname === '/') {
    return null;
  }

  let tabs = activeSection === 'le-automation' ? leAutomationTabs : boqTabs;
  if (activeSection==='ran-boq'){
    tabs =ranBoqTabs
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