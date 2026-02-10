import React from 'react';
import { useNavigate } from 'react-router-dom';
import '../css/Home.css';

export default function Home({ setActiveSection, user }) {
  const navigate = useNavigate();
  const [showRevenueCards, setShowRevenueCards] = React.useState(false);

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
        {!showRevenueCards ? (
          <>
            <div className="home-card card-link" onClick={() => handleCardClick('/rop-project', 'le-automation')}>
              <h2>LE-Automation</h2>
              <p>Explore and manage Latest Estimation automation projects. ⚙️</p>
            </div>
            <div className="home-card card-link" onClick={() => setShowRevenueCards(true)}>
              <h2>Zain BOQ Automation</h2>
              <p>Automate and manage Zain BOQ processes. 📈</p>
            </div>
            <div className="home-card card-link" onClick={() => handleCardClick('/du-boq-items', 'du-5g')}>
              <h2>DU BOQ Automation</h2>
              <p>Automate and manage DU BOQ processes. 📱</p>
            </div>
            {user?.role === 'senior_admin' && (
              <div className="home-card card-link" onClick={() => navigate('/logs')}>
                <h2>System Logs</h2>
                <p>View and manage system logs and activities. 📋</p>
              </div>
            )}
          </>
        ) : (
          <>
            <div className="home-card card-link" onClick={() => setShowRevenueCards(false)} style={{ marginBottom: 24 }}>
              <h2 style={{ fontWeight: 600 }}>← Back</h2>
            </div>
            <div className="home-card card-link" onClick={() => handleCardClick('/ran-projects', 'ran-boq')}>
              <h2>RAN BOQ</h2>
              <p>Access and manage RAN Bill of Quantities data. 📶</p>
            </div>
            <div className="home-card card-link" onClick={() => handleCardClick('/project', 'boq')}>
              <h2>Microwave BOQ</h2>
              <p>Access and manage Microwave Bill of Quantities data. 📊</p>
            </div>
          </>
        )}
      </div>
    </div>
  );
}