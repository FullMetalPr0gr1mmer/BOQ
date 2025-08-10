
import { NavLink, useNavigate } from 'react-router-dom';
import '../css/header.css';

const boqTabs = ['Project', 'Site', 'Inventory', 'Level1', 'Level3', 'Level3 Items', 'LogOut'];
const leAutomationTabs = ['ROP Lvl1', 'ROP Project', 'LogOut'];

export default function Header({ onLogout, activeSection }) {
  const navigate = useNavigate();

  const handleTabClick = (tab, e) => {
    if (tab === 'LogOut') {
      e.preventDefault();
      onLogout();
      navigate('/');
    }
  };

  const tabs = activeSection === 'le-automation' ? leAutomationTabs : boqTabs;

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
