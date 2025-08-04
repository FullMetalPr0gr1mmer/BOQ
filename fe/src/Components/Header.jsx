import { NavLink, useNavigate } from 'react-router-dom';
import '../css/header.css';

const tabs = ['Project', 'Site', 'Inventory', 'Level1', 'Level3','Level3 Items', 'LogOut'];

export default function Header({ onLogout }) {
  const navigate = useNavigate();

  const handleTabClick = (tab, e) => {
    if (tab === 'LogOut') {
      e.preventDefault(); // prevent navigation
      onLogout();         // call logout passed from App
      navigate('/');      // redirect to login screen (optional)
    }
  };

  return (
    <header className="nokia-header">
      <div className="logo"><img src='logo.svg'/></div>
      <nav className="tabs">
        {tabs.map(tab => (
          <NavLink
            key={tab}
            to={tab === 'LogOut' ? '#' : `/${tab.toLowerCase()}`}
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
