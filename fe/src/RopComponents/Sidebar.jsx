import { useState } from 'react';
import { FaSignOutAlt, FaTimes, FaClipboardList, FaChevronDown, FaChevronRight, FaUser, FaCheckCircle } from 'react-icons/fa';
import { FaProjectDiagram, FaMapMarkerAlt, FaBox, FaLayerGroup, FaCubes, FaFile, FaRobot, FaNetworkWired, FaBroadcastTower, FaAnchor, FaMobileAlt } from 'react-icons/fa';
import { useNavigate } from 'react-router-dom';
import '../css/Sidebar.css';
import ChatSidebar from '../AIComponents/ChatSidebar';
import { FiPaperclip } from 'react-icons/fi';

function Sidebar({ isOpen, onClose, onSelect, user }) {
    const navigate = useNavigate();
    const [expandedSections, setExpandedSections] = useState({});
    const [chatOpen, setChatOpen] = useState(false);

    const toggleSection = (sectionKey) => {
        setExpandedSections(prev => ({
            ...prev,
            [sectionKey]: !prev[sectionKey]
        }));
    };

    const handleNavigation = (path, section) => {
        navigate(path);
        if (section) {
            onSelect(section);
        }
        onClose();
    };

    const sections = [
        {
            key: 'boq',
            title: 'MW BOQ',
            icon: <FaNetworkWired />,
            items: [
                { label: 'Projects', path: '/project', icon: <FaProjectDiagram /> },
                { label: 'Sites', path: '/site', icon: <FaMapMarkerAlt /> },
                { label: 'Inventory', path: '/inventory', icon: <FaBox /> },
                { label: 'Level 3', path: '/level3', icon: <FaCubes /> },
                { label: 'Level 3 Items', path: '/level3-items', icon: <FaCubes /> },
                { label: 'BOQ Generation', path: '/boq-generation', icon: <FaFile /> },
                { label: 'LLD Management', path: '/lld', icon: <FaFile /> },
                { label: 'Dismantling', path: '/dismantling', icon: <FaBox /> }
            ]
        },
        {
            key: 'le-automation',
            title: 'LE Automation',
            icon: <FiPaperclip />,
            items: [
                { label: 'Projects', path: '/rop-project', icon: <FaProjectDiagram /> },
                { label: 'Level 1', path: '/rop-lvl1', icon: <FaLayerGroup /> },
                { label: 'Package', path: '/rop-package', icon: <FaBox /> }
            ]
        },
        {
            key: 'ran-boq',
            title: 'RAN BOQ',
            icon: <FaBroadcastTower />,
            items: [
                { label: 'Projects', path: '/ran-projects', icon: <FaProjectDiagram /> },
                { label: 'Inventory', path: '/ran-inventory', icon: <FaBox /> },
                { label: 'Level 3', path: '/ran-level3', icon: <FaCubes /> },
                { label: 'BOQ Generation', path: '/ran-boq-generation', icon: <FaFile /> },
                { label: 'Antenna Serials', path: '/ran-antenna-serials', icon: <FaAnchor /> }
            ]
        },
        {
            key: 'du-5g',
            title: 'DU BOQ',
            icon: <FaMobileAlt />,
            items: [
                { label: 'Projects', path: '/du-projects', icon: <FaProjectDiagram /> },
                { label: 'BOQ Generation', path: '/du-rollout-sheet', icon: <FaFile /> },
                { label: 'OD BOQ Items', path: '/du-boq-items', icon: <FaCubes /> },
                { label: 'Customer PO', path: '/du-customer-po', icon: <FaClipboardList /> }
            ]
        }
    ];

    return (
        <>
            {/* Overlay */}
            {isOpen && <div className="sidebar-overlay" onClick={onClose}></div>}

            {/* Sidebar */}
            <div className={`modern-sidebar ${isOpen ? 'open' : ''}`}>
                {/* Header */}
                <div className="sidebar-header">
                    <div className="user-info">
                        <div className="user-avatar">
                            <FaUser />
                        </div>
                        <div className="user-details">
                            <span className="user-name">{user?.username || 'User'}</span>
                            <span className="user-role">{user?.role?.replace('_', ' ').toUpperCase() || 'ADMIN'}</span>
                        </div>
                    </div>
                    <button className="sidebar-close-btn" onClick={onClose}>
                        <FaTimes />
                    </button>
                </div>

                {/* Navigation */}
                <nav className="sidebar-nav">
                    {sections.map((section) => (
                        <div key={section.key} className="nav-section">
                            <button
                                className={`nav-section-header ${expandedSections[section.key] ? 'expanded' : ''}`}
                                onClick={() => toggleSection(section.key)}
                            >
                                <span className="nav-section-title">
                                    <span className="nav-icon">{section.icon}</span>
                                    {section.title}
                                </span>
                                <span className="nav-chevron">
                                    {expandedSections[section.key] ? <FaChevronDown /> : <FaChevronRight />}
                                </span>
                            </button>

                            {expandedSections[section.key] && (
                                <div className="nav-section-items">
                                    {section.items.map((item) => (
                                        <button
                                            key={item.path}
                                            className="nav-item"
                                            onClick={() => handleNavigation(item.path, section.key)}
                                        >
                                            <span className="nav-icon">{item.icon}</span>
                                            {item.label}
                                        </button>
                                    ))}
                                </div>
                            )}
                        </div>
                    ))}

                    {/* Approvals Workflow */}
                    <div className="nav-section">
                        <button
                            className="nav-section-header single-item"
                            onClick={() => handleNavigation('/approvals', null)}
                        >
                            <span className="nav-section-title">
                                <span className="nav-icon"><FaCheckCircle /></span>
                                Approvals
                            </span>
                        </button>
                    </div>

                    {/* System Logs - Only for senior_admin */}
                    {user?.role === 'senior_admin' && (
                        <div className="nav-section">
                            <button
                                className="nav-section-header single-item"
                                onClick={() => handleNavigation('/logs', null)}
                            >
                                <span className="nav-section-title">
                                    <span className="nav-icon"><FaClipboardList /></span>
                                    System Logs
                                </span>
                            </button>
                        </div>
                    )}

                    {/* AI Assistant - Only for senior_admin */}
                    {user?.role === 'senior_admin' && (
                        <div className="nav-section">
                            <button
                                className="nav-section-header single-item"
                                onClick={() => setChatOpen(true)}
                            >
                                <span className="nav-section-title">
                                    <span className="nav-icon"><FaRobot /></span>
                                    AI Assistant
                                </span>
                            </button>
                        </div>
                    )}
                </nav>

                {/* Footer / Logout */}
                <div className="sidebar-footer">
                    <button className="logout-btn" onClick={() => { onSelect('logout'); onClose(); }}>
                        <FaSignOutAlt />
                        Logout
                    </button>
                </div>
            </div>

            {/* AI Chat Sidebar */}
            <ChatSidebar
                isOpen={chatOpen}
                onClose={() => setChatOpen(false)}
                projectContext={null}
            />
        </>
    );
}

export default Sidebar;
