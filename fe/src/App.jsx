import { useState } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Header from './Components/Header';
import './App.css';
import AuthForm from './Components/AuthForm';
import Project from './Components/Project';
import Site from './Components/Site';
import Inventory from './Components/Inventory';
import Lvl1 from './Components/lvl1';
import Lvl3 from './Components/lvl3';
import Lvl3Items from './Components/Lvl3Items';
import Sidebar from './RopComponents/Sidebar';
import ROPProject from './RopComponents/RopProject';
import RopLvl1 from './RopComponents/RopLvl1';
function App() {
  const [token, setToken] = useState('');
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [activeSection, setActiveSection] = useState('boq'); // 'boq' or 'le-automation'

  const logout = () => {
    setToken('');
  };

  return (
    <Router>
      {!token ? (
        <AuthForm onLogin={setToken} />
      ) : (
        <>
          <Header onLogout={logout} activeSection={activeSection} />
          <div className="main-content">
            <Routes>
              <Route path="/project" element={<Project />} />
              <Route path="/site" element={<Site />} />
              <Route path="/inventory" element={<Inventory />} />
              <Route path="/level1" element={<Lvl1 />} />
              <Route path="/level3" element={<Lvl3 />} />
              <Route path="/level3-items" element={<Lvl3Items />} />
              <Route path="/rop-project" element={<ROPProject />} />
              <Route path="/rop-lvl1" element={<RopLvl1 />} />
              <Route path="*" element={<Project />} />
            </Routes>
          </div>

          {/* ☰ Sidebar Toggle */}
          <button className="hamburger" onClick={() => setSidebarOpen(!sidebarOpen)}>
            ☰
          </button>

          {/* Sidebar */}
          <Sidebar
            isOpen={sidebarOpen}
            onClose={() => setSidebarOpen(false)}
            onSelect={(section) => {
              if (section === 'logout') {
                logout();
              } else if (section === 'boq' || section === 'le-automation') {
                setActiveSection(section);
              }
              setSidebarOpen(false);
            }}
          />
        </>
      )}
    </Router>
  );
}

export default App;
