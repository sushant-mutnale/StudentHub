import { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import {
  FiHome, FiUser, FiFileText, FiTrendingUp, FiBook, FiMic, FiSearch,
  FiTarget, FiBell, FiLogOut, FiMessageSquare, FiCalendar, FiClipboard,
  FiChevronDown, FiChevronRight, FiBriefcase, FiLayers
} from 'react-icons/fi';
import Avatar from './Avatar';
import '../App.css';

const SidebarLeft = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout } = useAuth();

  // State for expanded groups
  const [expanded, setExpanded] = useState({
    learning: true,
    career: true,
    assessment: false,
    communication: false
  });

  const toggleGroup = (key) => {
    setExpanded(prev => ({ ...prev, [key]: !prev[key] }));
  };

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  const isActive = (path) => {
    return location.pathname === path || location.pathname.startsWith(path + '/');
  };

  // Only expand groups if a child is active (on mount)
  useEffect(() => {
    // Logic to auto-expand can be added here
  }, [location.pathname]);

  const navStructure = [
    { type: 'link', label: 'Dashboard', icon: FiHome, path: '/dashboard/student' },
    { type: 'link', label: 'Analytics', icon: FiTrendingUp, path: '/analytics' },
    { type: 'link', label: 'Profile', icon: FiUser, path: '/profile/student' },

    {
      type: 'group',
      label: 'Learning',
      key: 'learning',
      icon: FiBook,
      children: [
        { label: 'Courses', path: '/learning' },
        { label: 'Skill Gaps', path: '/skill-gaps' },
        { label: 'Research', path: '/research' }
      ]
    },

    {
      type: 'group',
      label: 'Career',
      key: 'career',
      icon: FiBriefcase,
      children: [
        { label: 'Opportunities', path: '/opportunities' },
        { label: 'My Applications', path: '/applications' },
        { label: 'Resume', path: '/resume' },
        { label: 'Mock Interview', path: '/mock-interview' },
        { label: 'Interviews', path: '/interviews' }
      ]
    },

    {
      type: 'group',
      label: 'Assessments',
      key: 'assessment',
      icon: FiLayers,
      children: [
        { label: 'All Assessments', path: '/assessment' }
      ]
    },

    {
      type: 'group',
      label: 'Communication',
      key: 'communication',
      icon: FiMessageSquare,
      children: [
        { label: 'Messages', path: '/messages' },
        { label: 'Notifications', path: '/smart-notifications' }
      ]
    }
  ];

  const renderNavItem = (item, isNested = false) => {
    const active = isActive(item.path);
    return (
      <div
        key={item.path}
        className={`nav-item ${active ? 'active' : ''}`}
        style={{ paddingLeft: isNested ? '3rem' : '1rem' }}
        onClick={() => navigate(item.path)}
      >
        {!isNested && item.icon && <item.icon />}
        <span>{item.label}</span>
      </div>
    );
  };

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
        {navStructure.map((item, index) => {
          if (item.type === 'link') {
            return renderNavItem(item);
          }

          if (item.type === 'group') {
            const isExpanded = expanded[item.key];
            const Icon = item.icon;
            return (
              <div key={item.key} className="nav-group">
                <div
                  className="nav-item group-header"
                  onClick={() => toggleGroup(item.key)}
                  style={{ justifyContent: 'space-between' }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                    <Icon />
                    <span>{item.label}</span>
                  </div>
                  {isExpanded ? <FiChevronDown /> : <FiChevronRight />}
                </div>
                {isExpanded && (
                  <div className="nav-group-children">
                    {item.children.map(child => renderNavItem(child, true))}
                  </div>
                )}
              </div>
            );
          }
          return null;
        })}

        <div className="nav-item logout" onClick={handleLogout} style={{ marginTop: 'auto' }}>
          <FiLogOut />
          <span>Logout</span>
        </div>
      </nav>
    </div>
  );
};

export default SidebarLeft;
