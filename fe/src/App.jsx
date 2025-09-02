import { useState } from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
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
function App() {
  const [auth, setAuth] = useState(null); // { token, user }
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [activeSection, setActiveSection] = useState('boq');

  const logout = () => {
    setAuth(null);
  };

  return (
    <Router>
      {!auth ? (
        <AuthForm onLogin={setAuth} />
      ) : (
        <>
          <Header onLogout={logout} activeSection={activeSection} user={auth.user} />
          {/* Logs is now only rendered via route, not fixed in header */}
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
              <Route path="*" element={<Home setActiveSection={setActiveSection} />} /></Routes>
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
