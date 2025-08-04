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
// const Project = () => <div className="page-content">📁 Project Page</div>;
// const Site = () => <div className="page-content">🏗️ Site Page</div>;
// const Inventory = () => <div className="page-content">📦 Inventory Page</div>;
// const Level1 = () => <div className="page-content">🧱 Level 1 Page</div>;
// const Level3 = () => <div className="page-content">🏢 Level 3 Page</div>;

function App() {
  const [token, setToken] = useState('');

  const logout = () => {
    setToken('');
  };

  return (
    <Router>
      {!token ? (
        <AuthForm onLogin={setToken} />
      ) : (
        <>
          <Header onLogout={logout} />
          <div className="main-content">
            <Routes>
              <Route path="/project" element={<Project />} />
              <Route path="/site" element={<Site />} />
              <Route path="/inventory" element={<Inventory />} />
              <Route path="/level1" element={<Lvl1 />} />
              <Route path="/level3" element={<Lvl3 />} />

              <Route path="/level3 items" element={<Lvl3Items/>} />
              <Route path="*" element={<Project />} />
            </Routes>
          </div>
        </>
      )}
    </Router>
  );
}

export default App;
