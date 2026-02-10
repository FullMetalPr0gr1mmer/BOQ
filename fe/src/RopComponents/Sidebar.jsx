import { useState, useEffect, useMemo } from 'react';
import { FaSignOutAlt, FaTimes, FaClipboardList, FaChevronDown, FaChevronRight, FaUser, FaCheckCircle, FaFileAlt } from 'react-icons/fa';
import { FaProjectDiagram, FaMapMarkerAlt, FaBox, FaLayerGroup, FaCubes, FaFile, FaRobot, FaNetworkWired, FaBroadcastTower, FaAnchor, FaMobileAlt, FaDatabase } from 'react-icons/fa';
import { useNavigate } from 'react-router-dom';
import '../css/Sidebar.css';
import ChatSidebar from '../AIComponents/ChatSidebar';
import { FiPaperclip } from 'react-icons/fi';
import { logout, apiCall } from '../api';

function Sidebar({ isOpen, onClose, onSelect, user }) {
    const navigate = useNavigate();
    const [expandedSections, setExpandedSections] = useState({});
    const [chatOpen, setChatOpen] = useState(false);
    const [approvalPermissions, setApprovalPermissions] = useState({
        can_access_approval: false,
        can_access_triggering: false,
        can_access_logistics: false
    });

    // Fetch approval permissions on mount
    useEffect(() => {
        const fetchPermissions = async () => {
            try {
                const data = await apiCall('/approvals/user/permissions');
                setApprovalPermissions({
                    can_access_approval: data.can_access_approval,
                    can_access_triggering: data.can_access_triggering,
                    can_access_logistics: data.can_access_logistics
                });
            } catch (error) {
                console.error('Failed to fetch approval permissions:', error);
            }
        };
        fetchPermissions();
    }, []);

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

    // OPTIMIZED: Memoize sections array to prevent re-creation on every render
    const sections = useMemo(() => [
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
                { label: 'BOQ Items', path: '/du-boq-items', icon: <FaCubes /> }
            ]
        },
        {
            key: 'ndpd',
            title: 'NDPD Data',
            icon: <FaDatabase />,
            items: [
                { label: 'NDPD Records', path: '/ndpd-data', icon: <FaDatabase /> }
            ]
        },
        {
            key: 'du-logistics',
            title: 'DU Logistics',
            icon: <FaClipboardList />,
            items: [
                { label: 'Projects', path: '/projects', icon: <FaClipboardList /> }
            ]
        }
    ], []); // Empty deps - sections are static

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

                    {/* Approvals Section */}
                    <div className="nav-section">
                        <button
                            className={`nav-section-header ${expandedSections['approvals'] ? 'expanded' : ''}`}
                            onClick={() => toggleSection('approvals')}
                        >
                            <span className="nav-section-title">
                                <span className="nav-icon"><FaCheckCircle /></span>
                                Approvals
                            </span>
                            <span className="nav-chevron">
                                {expandedSections['approvals'] ? <FaChevronDown /> : <FaChevronRight />}
                            </span>
                        </button>

                        {expandedSections['approvals'] && (
                            <div className="nav-section-items">
                                {approvalPermissions.can_access_approval && (
                                    <button
                                        className="nav-item"
                                        onClick={() => handleNavigation('/approvals', null)}
                                    >
                                        <span className="nav-icon"><FaCheckCircle /></span>
                                        Approval Stage
                                    </button>
                                )}
                                {approvalPermissions.can_access_triggering && (
                                    <button
                                        className="nav-item"
                                        onClick={() => handleNavigation('/triggering', null)}
                                    >
                                        <span className="nav-icon"><FaCheckCircle /></span>
                                        Triggering Stage
                                    </button>
                                )}
                                {approvalPermissions.can_access_logistics && (
                                    <button
                                        className="nav-item"
                                        onClick={() => handleNavigation('/logistics', null)}
                                    >
                                        <span className="nav-icon"><FaCheckCircle /></span>
                                        Logistics Stage
                                    </button>
                                )}
                                {(approvalPermissions.can_access_approval || approvalPermissions.can_access_triggering || approvalPermissions.can_access_logistics) && (
                                    <>
                                        <button
                                            className="nav-item"
                                            onClick={() => handleNavigation('/po-report', null)}
                                        >
                                            <span className="nav-icon"><FaFileAlt /></span>
                                            PO Report
                                        </button>
                                        <button
                                            className="nav-item"
                                            onClick={() => handleNavigation('/price-book', null)}
                                        >
                                            <span className="nav-icon"><FaFileAlt /></span>
                                            Price Book
                                        </button>
                                    </>
                                )}
                            </div>
                        )}
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

                    {/* AI Assistant - Available to all users */}
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
                </nav>

                {/* Footer / Logout */}
                <div className="sidebar-footer">
                    <button className="logout-btn" onClick={() => logout()}>
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
