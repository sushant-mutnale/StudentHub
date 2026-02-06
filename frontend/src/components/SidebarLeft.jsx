import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { FiHome, FiUser, FiFileText, FiTrendingUp, FiBook, FiMic, FiSearch, FiTarget, FiBell, FiLogOut, FiMessageSquare, FiCalendar, FiClipboard } from 'react-icons/fi';
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
    return location.pathname === path || location.pathname.startsWith(path + '/');
  };

  const navItems = [
    { icon: FiHome, label: 'Dashboard', path: '/dashboard/student' },
    { icon: FiUser, label: 'Profile', path: '/profile/student' },
    { icon: FiFileText, label: 'Resume', path: '/resume' },
    { icon: FiTrendingUp, label: 'Skill Gaps', path: '/skill-gaps' },
    { icon: FiBook, label: 'Learning', path: '/learning' },
    { icon: FiMic, label: 'Mock Interview', path: '/mock-interview' },
    { icon: FiSearch, label: 'Research', path: '/research' },
    { icon: FiTarget, label: 'Opportunities', path: '/opportunities' },
    { icon: FiClipboard, label: 'My Applications', path: '/applications' }, // New Module 5 Link
    { icon: FiClipboard, label: 'Assessment', path: '/assessment' },
    { icon: FiBell, label: 'Notifications', path: '/smart-notifications' },
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
          return (
            <div
              key={item.path}
              className={`nav-item ${isActive(item.path) ? 'active' : ''}`}
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
