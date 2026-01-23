import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { FiHome, FiUser, FiClipboard, FiBell, FiLogOut, FiMessageSquare, FiCalendar } from 'react-icons/fi';
import Avatar from './Avatar';
import '../App.css';

const SidebarLeft = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout } = useAuth();

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  const isActive = (path) => {
    return location.pathname.includes(path);
  };

  const navItems = [
    { icon: FiHome, label: 'Account', path: '/dashboard/student' },
    { icon: FiUser, label: 'Profile', path: '/profile/student' },
    { icon: FiClipboard, label: 'Assessment', path: '/assessment' },
    { icon: FiBell, label: 'Notifications', path: '/notifications' },
    { icon: FiMessageSquare, label: 'Messages', path: '/messages' },
    { icon: FiCalendar, label: 'Interviews', path: '/interviews' },
  ];

  return (
    <div className="sidebar-left">
      <div className="sidebar-logo">Student Hub</div>
      {user && (
        <div style={{ padding: '0 1.5rem', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <Avatar
            src={user.avatar_url}
            alt={user.fullName || user.companyName || user.username}
            size={40}
          />
          <div>
            <div style={{ fontSize: '0.9rem', fontWeight: 600 }}>
              {user.fullName || user.companyName}
            </div>
            <div style={{ fontSize: '0.8rem', color: '#999' }}>@{user.username}</div>
          </div>
        </div>
      )}
      <nav className="sidebar-nav">
        {navItems.map((item) => {
          const Icon = item.icon;
          const pathToCheck = item.path.replace('#assessment', '');
          return (
            <div
              key={item.path}
              className={`nav-item ${isActive(pathToCheck) ? 'active' : ''}`}
              onClick={() => navigate(item.path)}
            >
              <Icon />
              <span>{item.label}</span>
            </div>
          );
        })}
        <div className="nav-item logout" onClick={handleLogout}>
          <FiLogOut />
          <span>Logout</span>
        </div>
      </nav>
    </div>
  );
};

export default SidebarLeft;

