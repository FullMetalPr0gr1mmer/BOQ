import { FaSignOutAlt, FaTimes, FaClipboardList } from 'react-icons/fa';
import { FaXTwitter } from 'react-icons/fa6';
import { useNavigate } from 'react-router-dom';

function Sidebar({ isOpen, onClose, onSelect, user }) {
    const navigate = useNavigate();

    const handleClick = (section) => {
        onSelect(section);
        if (section === 'boq') {
            navigate('/project');
        } else if (section === 'le-automation') {
            navigate('/rop-project');
        }
        else if(section==='ran-boq'){
            navigate('/ran-lld')
        }
        else if(section==='logs'){
            navigate('/logs')
        }
    };

    return (
        <div className={`sidebar ${isOpen ? 'open' : ''}`}>
            <button style={{
                width: 'fit-content',
                padding: '1px',
            }} onClick={onClose}><FaTimes/></button>
            <button onClick={() => handleClick('boq')}>MW BOQ</button>
            <button onClick={() => handleClick('le-automation')}>LE Automation</button>
            <button onClick={() => handleClick('ran-boq')}>RAN BOQ</button>
            {user?.role === 'senior_admin' && (
                <button onClick={() => handleClick('logs')}><FaClipboardList/> System Logs</button>
            )}
            <button onClick={() => handleClick('logout')}><FaSignOutAlt/>LogOut</button>

        </div>
    );
}

export default Sidebar;
