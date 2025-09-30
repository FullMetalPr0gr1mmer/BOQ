import { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, useLocation } from 'react-router-dom';
import Header from './Components/Header';
import Logs from './Components/Logs';
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
import RopLvl2 from './RopComponents/RopLvl2';
import BOQGeneration from './Components/BOQGeneration';
import RopPackage from './RopComponents/RopPackage';
import LLDManagement from './Components/LLDManagement';
import Dismantling from './Components/Dismantling';
import Home from './Components/Home';
import RANLLD from './RanComponents/RanLLD';
import RANLvl3 from './RanComponents/RanLvl3';
import RANInventory from './RanComponents/RanInventory';
import RanProjects from './RanComponents/RanProjects';

// Helper function to determine section from URL
const getSectionFromPath = (pathname) => {
  if (pathname.startsWith('/rop-') || pathname.startsWith('/rop_')) {
    return 'le-automation';
  } else if (pathname.startsWith('/ran-') || pathname.startsWith('/ran_')) {
    return 'ran-boq';
  }
  return 'boq';
};

function AppContent() {
  const location = useLocation();
  const [auth, setAuth] = useState(() => {
    const token = localStorage.getItem('token');
    const userStr = localStorage.getItem('user');
    const user = userStr ? JSON.parse(userStr) : null;
    return { token, user };
  });
  const [sidebarOpen, setSidebarOpen] = useState(false);

  // Initialize activeSection from localStorage or URL
  const [activeSection, setActiveSection] = useState(() => {
    const savedSection = localStorage.getItem('activeSection');
    if (savedSection) {
      return savedSection;
    }
    return getSectionFromPath(location.pathname);
  });

  // Update activeSection when URL changes
  useEffect(() => {
    const section = getSectionFromPath(location.pathname);
    setActiveSection(section);
    localStorage.setItem('activeSection', section);
  }, [location.pathname]);

  // Save activeSection to localStorage whenever it changes
  useEffect(() => {
    localStorage.setItem('activeSection', activeSection);
  }, [activeSection]);

  const handleLogin = ({ token, user }) => {
    localStorage.setItem('token', token);
    localStorage.setItem('user', JSON.stringify(user));
    setAuth({ token, user });
  };

  const logout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    localStorage.removeItem('activeSection');
    setAuth({ token: null, user: null });
  };

  return (
    <>
      {/* Check if a token exists in state to determine what to render */}
      {!auth.token ? (
        // Pass the function reference, NOT the result of calling it
        <AuthForm onLogin={handleLogin} />
      ) : (
        <>
          <Header onLogout={logout} activeSection={activeSection} user={auth.user} />
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
              <Route path="/rop-lvl2" element={<RopLvl2 />} />
              <Route path="/rop-lvl1/:pid_po" element={<RopLvl1 />} />
              <Route path="/logs" element={<Logs user={auth.user} />} />
              <Route path="/boq-generation" element={<BOQGeneration />} />
              <Route path="/rop-package" element={<RopPackage />} />
              <Route path="/lld" element={<LLDManagement />} />
              <Route path="/dismantling" element={<Dismantling />} />
              <Route path="/ran-lld" element={<RANLLD />} />
              <Route path="/ran-level3" element={<RANLvl3 />} />
              <Route path="/ran-inventory" element={<RANInventory />} />
              <Route path="/ran-projects" element={<RanProjects />} />
              <Route path="*" element={<Home setActiveSection={setActiveSection} user={auth.user}/>} />
            </Routes>
          </div>

          <button className="hamburger" onClick={() => setSidebarOpen(!sidebarOpen)}>
            ☰
          </button>

          <Sidebar
            isOpen={sidebarOpen}
            onClose={() => setSidebarOpen(false)}
            user={auth.user}
            onSelect={(section) => {
              if (section === 'logout') {
                logout();
              } else if (section === 'boq' || section === 'le-automation' || section === 'ran-boq') {
                setActiveSection(section);
              }
              setSidebarOpen(false);
            }}
          />
        </>
      )}
    </>
  );
}

function App() {
  return (
    <Router>
      <AppContent />
    </Router>
  );
}

export default App;