import React from 'react';
import { useNavigate } from 'react-router-dom';
import '../css/Home.css';

export default function Home({ setActiveSection }) {
  const navigate = useNavigate();

  const handleCardClick = (path, section) => {
    setActiveSection(section);
    navigate(path);
  };

  return (
    <div className="home-container">
      <div className="home-header">
        <h1>Welcome!</h1>
        <p>Choose a project to get started.</p>
      </div>
      <div className="cards-wrapper">
        <div 
          className="home-card card-link" 
          onClick={() => handleCardClick('/project', 'boq')}
        >
          <h2>Microwave BOQ</h2>
          <p>Access and manage Microwave Bill of Quantities data. 📊</p>
        </div>
        <div 
          className="home-card card-link" 
          onClick={() => handleCardClick('/rop-project', 'le-automation')}
        >
          <h2>LE-Automation</h2>
          <p>Explore and manage Link Estimation automation projects. ⚙️</p>
        </div>
      </div>
    </div>
  );
}