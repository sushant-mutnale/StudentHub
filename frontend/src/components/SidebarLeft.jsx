import { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import {
  FiHome, FiUser, FiTrendingUp, FiBook,
  FiBell, FiLogOut, FiMessageSquare,
  FiChevronDown, FiChevronRight, FiBriefcase, FiLayers,
  FiSettings, FiHelpCircle, FiArrowLeft
} from 'react-icons/fi';
import Avatar from './Avatar';
import { smartNotificationService } from '../services/smartNotificationService';
import '../App.css';

const SidebarLeft = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout } = useAuth();
  const [scrolled, setScrolled] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);

  const deepRoutes = [
    '/research', '/learning', '/assessment', '/mock-interview',
    '/interview/voice', '/interviews', '/opportunities', '/skill-gaps',
    '/applications', '/profile/student', '/profile/', '/resume',
    '/analytics', '/smart-notifications', '/messages', '/jobs/',
    '/recruiter/pipeline', '/recruiter/search', '/recruiter/matches',
    '/recruiter/jobs', '/recruiter/post-job', '/verify'
  ];
  const isDeepRoute = deepRoutes.some(route => location.pathname.startsWith(route));

  // Load expanded state from localStorage or use defaults
  const [expanded, setExpanded] = useState(() => {
    const saved = localStorage.getItem('sidebar_expanded');
    if (saved) return JSON.parse(saved);
    return {
      learning: true,
      career: true,
      assessment: true,
      communication: true,
      hiring: true,
      sourcing: true
    };
  });

  // Save expanded state
  useEffect(() => {
    localStorage.setItem('sidebar_expanded', JSON.stringify(expanded));
  }, [expanded]);

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

  // Fetch unread notifications count
  useEffect(() => {
    if (user && !isDeepRoute) {
      smartNotificationService.getNotifications(true, 50)
        .then(data => {
          const unread = data.notifications || data || [];
          setUnreadCount(data.total !== undefined ? data.total : unread.length);
        })
        .catch(err => console.error("Failed to load unread count:", err));
    }
  }, [user, location.pathname]); // Refresh when navigating back from deep routes

  const studentNavStructure = [
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

  const recruiterNavStructure = [
    { type: 'link', label: 'Dashboard', icon: FiHome, path: '/dashboard/recruiter' },
    {
      type: 'group',
      label: 'Jobs & Hiring',
      key: 'hiring',
      icon: FiBriefcase,
      children: [
        { label: 'Post a Job', path: '/recruiter/post-job' },
        { label: 'My Jobs', path: '/recruiter/jobs' }
      ]
    },
    {
      type: 'group',
      label: 'Applicants',
      key: 'sourcing',
      icon: FiLayers,
      children: [
        { label: 'Pipeline', path: '/recruiter/pipeline' },
        { label: 'Find Candidates', path: '/recruiter/search' },
        { label: 'Smart Matches', path: '/recruiter/matches' }
      ]
    },
    {
      type: 'group',
      label: 'Communication',
      key: 'communication',
      icon: FiMessageSquare,
      children: [
        { label: 'Messages', path: '/messages' },
        { label: 'Interviews', path: '/interviews' }
      ]
    }
  ];

  const currentNavStructure = user?.role === 'recruiter' ? recruiterNavStructure : (user?.role === 'student' ? studentNavStructure : []);

  const renderNavItem = (item, isNested = false) => {
    const active = isActive(item.path);
    return (
      <div
        key={item.path}
        onClick={() => navigate(item.path)}
        className={`nav-item-modern ${active ? 'active' : ''}`}
        style={{
          paddingLeft: isDeepRoute ? '1rem' : (isNested ? '2.5rem' : '1.25rem'),
          paddingRight: isDeepRoute ? '1rem' : '1.25rem',
          position: 'relative',
          marginBottom: '0.25rem',
          paddingTop: isNested && !isDeepRoute ? '0.5rem' : '0.75rem',
          paddingBottom: isNested && !isDeepRoute ? '0.5rem' : '0.75rem',
          display: 'flex',
          justifyContent: isDeepRoute ? 'center' : 'flex-start',
          alignItems: 'center'
        }}
        title={isDeepRoute ? item.label : undefined}
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

        {item.icon && (
          <span className={`icon-container ${active ? 'active' : ''}`} style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            width: '24px',
            height: '24px',
            marginRight: isDeepRoute ? '0' : '0.75rem',
            color: active ? 'var(--color-primary)' : 'var(--color-text-muted)',
            transition: 'color 0.3s ease'
          }}>
            <item.icon size={isDeepRoute ? 24 : 20} />
          </span>
        )}

        {!isDeepRoute && <span style={{
          fontWeight: active ? '600' : '500',
          color: active ? 'var(--color-primary)' : 'var(--color-text)',
          fontSize: '0.95rem',
          transition: 'color 0.3s ease',
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem'
        }}>
          {item.label}

          {/* Notification Badge */}
          {item.path === '/smart-notifications' && unreadCount > 0 && (
            <span style={{
              width: '8px',
              height: '8px',
              backgroundColor: '#ef4444',
              borderRadius: '50%',
              display: 'inline-block',
              boxShadow: '0 0 0 2px rgba(255, 255, 255, 0.8)'
            }} title={`${unreadCount} unread notifications`} />
          )}
        </span>}
      </div>
    );
  };

  const FloatingButtons = () => (
    <div style={{
      position: 'fixed',
      top: '1rem',
      left: '1rem',
      display: 'flex',
      gap: '0.75rem',
      zIndex: 100
    }}>
      <button
        onClick={() => navigate(-1)}
        className="btn-glow hover-lift"
        style={{
          padding: '0.5rem 1rem',
          background: 'var(--color-surface)',
          color: 'var(--color-text)',
          border: '1px solid var(--color-border)',
          borderRadius: 'var(--radius-md)',
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem',
          boxShadow: 'var(--shadow-md)',
          fontWeight: '600',
          cursor: 'pointer'
        }}
      >
        <FiArrowLeft /> Back
      </button>
      <button
        onClick={() => navigate(user?.role === 'recruiter' ? '/dashboard/recruiter' : '/dashboard/student')}
        className="btn-glow hover-lift"
        style={{
          padding: '0.5rem 1rem',
          background: 'var(--gradient-primary)',
          color: 'white',
          border: 'none',
          borderRadius: 'var(--radius-md)',
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem',
          boxShadow: 'var(--shadow-glow)',
          fontWeight: '600',
          cursor: 'pointer'
        }}
      >
        <FiHome /> Home
      </button>
    </div>
  );

  return (
    <>
      {isDeepRoute && <FloatingButtons />}
      <div className={`sidebar-left glass-panel ${isDeepRoute ? 'collapsed' : ''}`} style={{
        borderRight: '1px solid rgba(255,255,255,0.5)',
        background: 'rgba(255, 255, 255, 0.8)',
        backdropFilter: 'blur(20px)',
        boxShadow: '5px 0 25px rgba(0,0,0,0.03)',
        zIndex: 50,
        width: isDeepRoute ? '80px' : '280px',
        maxWidth: isDeepRoute ? '80px' : '280px',
        minWidth: isDeepRoute ? '80px' : '280px',
        transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
        display: 'flex',
        flexDirection: 'column',
        height: '100vh',
        position: 'sticky',
        top: 0
      }}>
        {/* Header - App Info */}
        <div style={{
          padding: isDeepRoute ? '1.5rem 0' : '1.5rem',
          display: 'flex',
          alignItems: 'center',
          justifyContent: isDeepRoute ? 'center' : 'flex-start',
          gap: '0.75rem',
          borderBottom: '1px solid var(--color-border-light)',
          background: 'rgba(255,255,255,0.5)',
          paddingTop: isDeepRoute ? '6rem' : '1.5rem' // room for floating buttons
        }}>
          <div style={{
            width: isDeepRoute ? '36px' : '40px',
            height: isDeepRoute ? '36px' : '40px',
            borderRadius: '12px',
            background: 'var(--gradient-primary)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'white',
            fontWeight: 'bold',
            fontSize: isDeepRoute ? '1rem' : '1.25rem',
            boxShadow: 'var(--shadow-glow)'
          }}>
            SH
          </div>
          {!isDeepRoute && (
            <div style={{
              fontSize: '1.25rem',
              fontWeight: 800,
              background: 'var(--gradient-primary)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              backgroundClip: 'text',
              letterSpacing: '-0.5px'
            }}>
              StudentHub
            </div>
          )}
        </div>

        {/* User Info */}
        {user && (
          <div className="interactive-card" style={{
            margin: isDeepRoute ? '1rem 0' : '1rem',
            padding: isDeepRoute ? '0.5rem' : '0.75rem',
            background: 'transparent',
            borderRadius: 'var(--radius-lg)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: isDeepRoute ? 'center' : 'flex-start',
            gap: '0.75rem',
            border: 'none',
            boxShadow: 'none'
          }}>
            <Avatar
              src={user.avatar_url}
              alt={user.fullName || user.companyName || user.username}
              size={isDeepRoute ? "sm" : "md"}
              style={{ border: '2px solid white', boxShadow: 'var(--shadow-sm)' }}
            />
            {!isDeepRoute && (
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
            )}
          </div>
        )}

        {/* Navigation */}
        <nav className="sidebar-nav custom-scrollbar" style={{
          flex: 1,
          overflowY: 'auto',
          overflowX: 'hidden',
          padding: '0 0.75rem 2rem 0.75rem'
        }}>
          {currentNavStructure.map((item) => {
            if (item.type === 'link') {
              return renderNavItem(item);
            }

            if (item.type === 'group') {
              const isExpanded = expanded[item.key] && !isDeepRoute;
              const Icon = item.icon;

              return (
                <div key={item.key} style={{ marginBottom: isDeepRoute ? '0.5rem' : '0.5rem' }}>
                  <div
                    className="nav-item-modern group-header"
                    onClick={() => !isDeepRoute && toggleGroup(item.key)}
                    title={isDeepRoute ? item.label : undefined}
                    style={{
                      padding: isDeepRoute ? '0.75rem 0' : '0.75rem 1.25rem',
                      cursor: isDeepRoute ? 'default' : 'pointer',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: isDeepRoute ? 'center' : 'space-between',
                      borderRadius: 'var(--radius-md)',
                      transition: 'var(--transition-fast)',
                      color: 'var(--color-text-secondary)',
                      fontWeight: '600',
                      fontSize: '0.9rem'
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', justifyContent: isDeepRoute ? 'center' : 'flex-start' }}>
                      <Icon size={18} />
                      {!isDeepRoute && <span>{item.label}</span>}
                    </div>
                    {!isDeepRoute && (isExpanded ? <FiChevronDown /> : <FiChevronRight />)}
                  </div>

                  <div style={{
                    maxHeight: isExpanded ? '500px' : '0',
                    overflow: 'hidden',
                    transition: 'max-height 0.3s ease-in-out',
                    opacity: isExpanded ? 1 : 0,
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
          padding: isDeepRoute ? '1rem 0' : '1rem',
          display: 'flex',
          justifyContent: 'center',
          borderTop: '1px solid var(--color-border-light)',
          background: 'rgba(255,255,255,0.5)'
        }}>
          <div
            className="nav-item-modern logout"
            onClick={handleLogout}
            title={isDeepRoute ? "Logout" : undefined}
            style={{
              padding: isDeepRoute ? '0.875rem' : '0.875rem 1.25rem',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '0.75rem',
              color: 'var(--color-danger)',
              fontWeight: '600',
              cursor: 'pointer',
              borderRadius: 'var(--radius-md)',
              transition: 'var(--transition-normal)'
            }}
          >
            <FiLogOut size={20} />
            {!isDeepRoute && <span>Logout</span>}
          </div>
        </div>
      </div>
    </>
  );
};

export default SidebarLeft;
