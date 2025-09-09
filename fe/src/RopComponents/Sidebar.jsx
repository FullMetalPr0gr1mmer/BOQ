import { FaSignOutAlt, FaTimes } from 'react-icons/fa';
import { FaXTwitter } from 'react-icons/fa6';
import { useNavigate } from 'react-router-dom';

function Sidebar({ isOpen, onClose, onSelect }) {
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
            <button onClick={() => handleClick('logout')}><FaSignOutAlt/>LogOut</button>
            
        </div>
    );
}

export default Sidebar;
