import { NavLink, useNavigate } from 'react-router-dom';
import '../css/header.css';

const boqTabs = ['Project', 'Site', 'Inventory', 'Level1', 'Level3', 'Level3 Items', 'BOQ Generation', 'LogOut'];
const leAutomationTabs = [ 'ROP Project', 'LogOut'];

export default function Header({ onLogout, activeSection, user }) {
  const navigate = useNavigate();

  let tabs = activeSection === 'le-automation' ? leAutomationTabs : boqTabs;
  // Add Logs tab for admin users in BOQ
  if (activeSection === 'boq' && user?.role === 'admin' && !tabs.includes('Logs')) {
    tabs = [...tabs.slice(0, -1), 'Logs', tabs[tabs.length - 1]]; // Insert before LogOut
  }

  const handleTabClick = (tab, e) => {
    if (tab === 'LogOut') {
      e.preventDefault();
      onLogout();
      navigate('/');
    } else if (tab === 'Logs') {
      e.preventDefault();
      navigate('/logs');
    }
  };

  return (
    <header className="nokia-header">
      <div className="logo"><img src='logo.svg' alt="Logo"/></div>
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
