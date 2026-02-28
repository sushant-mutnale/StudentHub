import { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import {
  FiHome, FiUser, FiTrendingUp, FiBook,
  FiBell, FiLogOut, FiMessageSquare,
  FiChevronDown, FiChevronRight, FiBriefcase, FiLayers,
  FiSettings, FiHelpCircle
} from 'react-icons/fi';
import Avatar from './Avatar';
import '../App.css';

const SidebarLeft = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout } = useAuth();
  const [scrolled, setScrolled] = useState(false);

  // State for expanded groups
  const [expanded, setExpanded] = useState({
    learning: true,
    career: true,
    assessment: true,
    communication: true
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

  // Handle scroll effect for sidebar if needed in future
  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 20);
    };
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const navStructure = [
    { type: 'link', label: 'Dashboard', icon: FiHome, path: '/dashboard/student' },
    { type: 'link', label: 'Analytics', icon: FiTrendingUp, path: '/analytics' },
    {
      type: 'group',
      label: 'User & Profile',
      key: 'profile',
      icon: FiUser,
      children: [
        { label: 'Profile', path: '/profile/student' },
        { label: 'Resume', path: '/resume' }
      ]
    },

    {
      type: 'group',
      label: 'Evaluation & Matching',
      key: 'evaluation',
      icon: FiLayers,
      children: [
        { label: 'Skill Gaps', path: '/skill-gaps' },
        { label: 'All Assessments', path: '/assessment' }
      ]
    },

    {
      type: 'group',
      label: 'Learning & Feedback',
      key: 'learning',
      icon: FiBook,
      children: [
        { label: 'Learning Paths', path: '/learning' }
      ]
    },

    {
      type: 'group',
      label: 'Recommendations & Alerts',
      key: 'recommendations',
      icon: FiBell,
      children: [
        { label: 'Opportunities', path: '/opportunities' },
        { label: 'Notifications', path: '/smart-notifications' },
        { label: 'Research', path: '/research' }
      ]
    },

    {
      type: 'group',
      label: 'Communication & Tracking',
      key: 'communication',
      icon: FiMessageSquare,
      children: [
        { label: 'Applications', path: '/applications' },
        { label: 'Messages', path: '/messages' },
        { label: 'Interviews', path: '/interviews' },
        { label: 'Mock Interview (Chat)', path: '/mock-interview' },
        { label: '🎤 Voice Interview', path: '/interview/voice' }
      ]
    }
  ];

  const renderNavItem = (item, isNested = false) => {
    const active = isActive(item.path);
    return (
      <div
        key={item.path}
        onClick={() => navigate(item.path)}
        className={`nav-item-modern ${active ? 'active' : ''}`}
        style={{
          paddingLeft: isNested ? '2.5rem' : '1.25rem',
          position: 'relative',
          marginBottom: '0.25rem',
          paddingTop: isNested ? '0.5rem' : '0.75rem',
          paddingBottom: isNested ? '0.5rem' : '0.75rem'
        }}
      >
        {active && (
          <div className="active-indicator" style={{
            position: 'absolute',
            left: 0,
            top: '50%',
            transform: 'translateY(-50%)',
            width: '4px',
            height: '60%',
            background: 'var(--gradient-primary)',
            borderRadius: '0 4px 4px 0',
            boxShadow: '0 0 10px rgba(102, 126, 234, 0.5)'
          }} />
        )}

        {!isNested && item.icon && (
          <span className={`icon-container ${active ? 'active' : ''}`} style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            width: '24px',
            height: '24px',
            marginRight: '0.75rem',
            color: active ? 'var(--color-primary)' : 'var(--color-text-muted)',
            transition: 'color 0.3s ease'
          }}>
            <item.icon size={20} />
          </span>
        )}

        <span style={{
          fontWeight: active ? '600' : '500',
          color: active ? 'var(--color-primary)' : 'var(--color-text)',
          fontSize: '0.95rem',
          transition: 'color 0.3s ease'
        }}>
          {item.label}
        </span>
      </div>
    );
  };

  return (
    <div className="sidebar-left glass-panel" style={{
      borderRight: '1px solid rgba(255,255,255,0.5)',
      background: 'rgba(255, 255, 255, 0.8)',
      backdropFilter: 'blur(20px)',
      boxShadow: '5px 0 25px rgba(0,0,0,0.03)',
      zIndex: 50
    }}>
      {/* Logo Area */}
      <div style={{
        padding: '2rem 1.5rem',
        marginBottom: '1rem',
        display: 'flex',
        alignItems: 'center',
        gap: '0.75rem'
      }}>
        <div style={{
          width: '40px',
          height: '40px',
          background: 'var(--gradient-primary)',
          borderRadius: '12px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          color: 'white',
          fontWeight: 'bold',
          fontSize: '1.2rem',
          boxShadow: 'var(--shadow-glow)'
        }}>S</div>
        <span style={{
          fontSize: '1.5rem',
          fontWeight: '800',
          background: 'var(--gradient-primary)',
          WebkitBackgroundClip: 'text',
          WebkitTextFillColor: 'transparent',
          backgroundClip: 'text',
          letterSpacing: '-0.5px'
        }}>StudentHub</span>
      </div>

      {/* User Quick Profile */}
      {user && (
        <div className="interactive-card" style={{
          margin: '0 1rem 2rem 1rem',
          padding: '0.75rem',
          background: 'white',
          borderRadius: 'var(--radius-lg)',
          display: 'flex',
          alignItems: 'center',
          gap: '0.75rem',
          border: '1px solid var(--color-border-light)',
          boxShadow: 'var(--shadow-sm)'
        }}>
          <Avatar
            src={user.avatar_url}
            alt={user.fullName || user.companyName || user.username}
            size={40}
            style={{ border: '2px solid white', boxShadow: 'var(--shadow-sm)' }}
          />
          <div style={{ overflow: 'hidden' }}>
            <div style={{
              fontSize: '0.9rem',
              fontWeight: 700,
              whiteSpace: 'nowrap',
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              color: 'var(--color-text)'
            }}>
              {user.fullName || user.companyName || 'User'}
            </div>
            <div style={{
              fontSize: '0.75rem',
              color: 'var(--color-text-muted)',
              whiteSpace: 'nowrap',
              overflow: 'hidden',
              textOverflow: 'ellipsis'
            }}>
              @{user.username}
            </div>
          </div>
        </div>
      )}

      {/* Navigation */}
      <nav className="sidebar-nav custom-scrollbar" style={{
        flex: 1,
        overflowY: 'auto',
        padding: '0 0.75rem 2rem 0.75rem'
      }}>
        {navStructure.map((item) => {
          if (item.type === 'link') {
            return renderNavItem(item);
          }

          if (item.type === 'group') {
            const isExpanded = expanded[item.key];
            const Icon = item.icon;

            return (
              <div key={item.key} style={{ marginBottom: '0.5rem' }}>
                <div
                  className="nav-item-modern group-header"
                  onClick={() => toggleGroup(item.key)}
                  style={{
                    padding: '0.75rem 1.25rem',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    borderRadius: 'var(--radius-md)',
                    transition: 'var(--transition-fast)',
                    color: 'var(--color-text-secondary)',
                    fontWeight: '600',
                    fontSize: '0.9rem'
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                    <Icon size={18} />
                    <span>{item.label}</span>
                  </div>
                  {isExpanded ? <FiChevronDown /> : <FiChevronRight />}
                </div>

                <div style={{
                  maxHeight: isExpanded ? '500px' : '0',
                  overflow: 'hidden',
                  transition: 'max-height 0.3s ease-in-out',
                  opacity: isExpanded ? 1 : 0.5,
                  marginTop: '0.25rem'
                }}>
                  {item.children.map(child => renderNavItem(child, true))}
                </div>
              </div>
            );
          }
          return null;
        })}
      </nav>

      {/* Footer Actions */}
      <div style={{
        padding: '1rem',
        borderTop: '1px solid var(--color-border-light)',
        background: 'rgba(255,255,255,0.5)'
      }}>
        <div
          className="nav-item-modern logout"
          onClick={handleLogout}
          style={{
            padding: '0.875rem 1.25rem',
            display: 'flex',
            alignItems: 'center',
            gap: '0.75rem',
            color: 'var(--color-danger)',
            fontWeight: '600',
            cursor: 'pointer',
            borderRadius: 'var(--radius-md)',
            transition: 'var(--transition-normal)'
          }}
        >
          <FiLogOut size={20} />
          <span>Logout</span>
        </div>
      </div>
    </div>
  );
};

export default SidebarLeft;
