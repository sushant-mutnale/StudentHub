import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { FiCalendar, FiUsers, FiBookOpen, FiCode, FiLayers, FiTrendingUp, FiBriefcase, FiUserPlus } from 'react-icons/fi';
import { api } from '../api/client';
import { useAuth } from '../contexts/AuthContext';
import { userService } from '../services/userService';
import Avatar from './Avatar';
import '../App.css';

const formatDate = (dateString) => {
  if (!dateString) return 'TBA';
  const date = new Date(dateString);
  if (isNaN(date)) return 'TBA';
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
};

// Map categories to dynamic icons and colors
const getCategoryIcon = (category) => {
  const cat = (category || '').toLowerCase();
  if (cat.includes('ai') || cat.includes('machine learning')) return { icon: FiTrendingUp, color: '#8b5cf6' };
  if (cat.includes('design') || cat.includes('ui')) return { icon: FiLayers, color: '#ec4899' };
  if (cat.includes('dev') || cat.includes('code') || cat.includes('web')) return { icon: FiCode, color: '#3b82f6' };
  return { icon: FiBriefcase, color: '#10b981' };
};

const SidebarRight = () => {
  const { user } = useAuth();
  const [contests, setContests] = useState([]);
  const [resources, setResources] = useState([]);
  const [connections, setConnections] = useState([]);
  const [loadingContests, setLoadingContests] = useState(true);
  const [loadingResources, setLoadingResources] = useState(true);
  const [loadingConnections, setLoadingConnections] = useState(true);

  useEffect(() => {
    const fetchSidebarData = async () => {
      try {
        setLoadingContests(true);
        const { data: eventsData } = await api.get('/events/upcoming?limit=3');
        // Handle case where eventsData is an object wrapping the array or just an object
        const finalEvents = Array.isArray(eventsData) ? eventsData : (eventsData?.data || []);
        setContests(finalEvents);
      } catch (err) {
        console.error('Failed to fetch events:', err);
      } finally {
        setLoadingContests(false);
      }

      try {
        setLoadingResources(true);
        const { data: resourcesData } = await api.get('/resources/recommended?limit=3');
        // Handle case where resourcesData is an object wrapping the array or just an object
        const finalResources = Array.isArray(resourcesData) ? resourcesData : (resourcesData?.data || []);
        setResources(finalResources);
      } catch (err) {
        console.error('Failed to fetch resources:', err);
      } finally {
        setLoadingResources(false);
      }
    };

    fetchSidebarData();
  }, []);

  useEffect(() => {
    const fetchConnections = async () => {
      if (!user) return;
      try {
        setLoadingConnections(true);
        const { data: suggested } = await api.get('/users/suggested');
        setConnections(suggested || []);
      } catch (err) {
        console.error('Failed to fetch connections:', err);
      } finally {
        setLoadingConnections(false);
      }
    };
    fetchConnections();
  }, [user]);

  const handleConnect = async (targetId) => {
    try {
      await userService.addConnection(targetId);
      setConnections(prev => prev.filter(c => c.id !== targetId));
    } catch (err) {
      console.error('Failed to connect:', err);
    }
  };

  return (
    <div className="sidebar-right animate-fade-in-left">
      {/* Suggested Connections Section */}
      {user && user.role === 'student' && (
        <div className="glass-card" style={{
          padding: '1.5rem',
          borderRadius: 'var(--radius-lg)',
          marginBottom: '1.5rem',
          border: '1px solid rgba(255,255,255,0.6)'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.25rem' }}>
            <h3 style={{ fontSize: '1.1rem', fontWeight: '700', color: 'var(--color-text)', margin: 0 }}>
              Suggested Connections
            </h3>
            <span style={{ fontSize: '0.8rem', color: 'var(--color-primary)', fontWeight: '600', cursor: 'pointer' }}>View All</span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {loadingConnections ? (
              Array(3).fill(0).map((_, i) => (
                <div key={`sk-cn-${i}`} className="skeleton" style={{ height: '50px', borderRadius: '10px' }}></div>
              ))
            ) : connections.length === 0 ? (
              <div style={{ fontSize: '0.9rem', color: 'var(--color-text-muted)', textAlign: 'center', padding: '1rem 0' }}>No new suggestions.</div>
            ) : (
              connections.map((conn) => (
                <div key={conn.id} style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                  <Link to={`/profile/${conn.id}`}>
                    <Avatar src={conn.avatar_url} alt={conn.full_name || conn.username} size={40} />
                  </Link>
                  <div style={{ flex: 1, overflow: 'hidden' }}>
                    <Link to={`/profile/${conn.id}`} style={{ textDecoration: 'none', color: 'var(--color-text)', fontWeight: '600', fontSize: '0.9rem', display: 'block', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {conn.full_name || conn.username}
                    </Link>
                    <div style={{ fontSize: '0.75rem', color: 'var(--color-primary)', fontWeight: '600', opacity: 0.8 }}>
                      {conn.reason}
                    </div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {conn.location}
                    </div>
                  </div>
                  <button
                    onClick={() => handleConnect(conn.id)}
                    className="btn-icon hover-scale"
                    title={user.connections?.includes(conn.id) ? "Connected" : "Connect"}
                    disabled={user.connections?.includes(conn.id)}
                    style={{
                      width: '32px',
                      height: '32px',
                      borderRadius: '50%',
                      background: user.connections?.includes(conn.id) ? 'rgba(46, 204, 113, 0.1)' : 'rgba(102, 126, 234, 0.1)',
                      color: user.connections?.includes(conn.id) ? '#2ecc71' : 'var(--color-primary)',
                      border: 'none',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      cursor: user.connections?.includes(conn.id) ? 'default' : 'pointer',
                      opacity: user.connections?.includes(conn.id) ? 0.8 : 1
                    }}
                  >
                    {user.connections?.includes(conn.id) ? <FiCheckCircle size={16} /> : <FiUserPlus size={16} />}
                  </button>
                </div>
              ))
            )}
          </div>
        </div>
      )}

      {/* Contests Section */}
      <div className="glass-card" style={{
        padding: '1.5rem',
        borderRadius: 'var(--radius-lg)',
        marginBottom: '1.5rem',
        border: '1px solid rgba(255,255,255,0.6)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.25rem' }}>
          <h3 style={{ fontSize: '1.1rem', fontWeight: '700', color: 'var(--color-text)', margin: 0 }}>
            Upcoming Contests
          </h3>
          <span 
            onClick={() => navigate('/opportunities?tab=hackathons')} 
            style={{ fontSize: '0.8rem', color: 'var(--color-primary)', fontWeight: '600', cursor: 'pointer' }}
          >
            View All
          </span>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {loadingContests ? (
            Array(3).fill(0).map((_, i) => (
              <div key={`sk-ev-${i}`} className="skeleton" style={{ height: '60px', borderRadius: '10px' }}></div>
            ))
          ) : contests.length === 0 ? (
            <div style={{ fontSize: '0.9rem', color: 'var(--color-text-muted)', textAlign: 'center', padding: '1rem 0' }}>No upcoming events right now.</div>
          ) : (
            contests.map((contest) => {
              const { icon: Icon, color } = getCategoryIcon(contest.category);

              // Ensure absolute URLs
              let contestUrl = contest.url || '#';
              if (contestUrl !== '#' && !contestUrl.startsWith('http://') && !contestUrl.startsWith('https://')) {
                contestUrl = 'https://' + contestUrl;
              }

              return (
                <div
                  key={contest.id}
                  className="interactive-card hover-lift"
                  onClick={() => window.open(contestUrl, '_blank', 'noopener,noreferrer')}
                  style={{
                    padding: '0.75rem',
                    borderRadius: 'var(--radius-md)',
                    background: 'rgba(255, 255, 255, 0.5)',
                    transition: 'var(--transition-normal)',
                    cursor: 'pointer'
                  }}
                >
                  <div style={{ display: 'flex', gap: '0.75rem' }}>
                    <div style={{
                      width: '36px',
                      height: '36px',
                      borderRadius: '10px',
                      background: `${color}15`,
                      color: color,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      flexShrink: 0
                    }}>
                      <Icon size={18} />
                    </div>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontWeight: '600', fontSize: '0.9rem', marginBottom: '0.2rem', color: 'var(--color-text)' }}>
                        {contest.title}
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>
                        <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                          <FiCalendar size={12} /> {formatDate(contest.date)}
                        </span>
                        {contest.status && (
                          <span style={{
                            fontSize: '0.7rem',
                            padding: '0.1rem 0.4rem',
                            borderRadius: '4px',
                            background: contest.status === 'live' ? 'var(--color-danger)' : 'var(--color-primary-light)',
                            color: contest.status === 'live' ? 'white' : 'var(--color-primary)'
                          }}>
                            {contest.status.toUpperCase()}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* Suggested Resources Section */}
      <div className="glass-card" style={{
        padding: '1.5rem',
        borderRadius: 'var(--radius-lg)',
        border: '1px solid rgba(255,255,255,0.6)'
      }}>
        <h3 style={{ fontSize: '1.1rem', fontWeight: '700', color: 'var(--color-text)', margin: '0 0 1.25rem 0' }}>
          Learning Resources
        </h3>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          {loadingResources ? (
            Array(3).fill(0).map((_, i) => (
              <div key={`sk-rs-${i}`} className="skeleton" style={{ height: '50px', borderRadius: '8px' }}></div>
            ))
          ) : resources.length === 0 ? (
            <div style={{ fontSize: '0.9rem', color: 'var(--color-text-muted)', textAlign: 'center', padding: '1rem 0' }}>No recommended resources yet.</div>
          ) : (
            resources.map((resource) => {
              // Ensure absolute URLs
              let resourceUrl = resource.url || '#';
              if (resourceUrl !== '#' && !resourceUrl.startsWith('http://') && !resourceUrl.startsWith('https://')) {
                resourceUrl = 'https://' + resourceUrl;
              }

              return (
                <a
                  key={resource.id}
                  href={resourceUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="hover-lift"
                  style={{
                    display: 'flex',
                    alignItems: 'start',
                    gap: '0.75rem',
                    padding: '0.75rem',
                    borderRadius: 'var(--radius-md)',
                    textDecoration: 'none',
                    color: 'inherit',
                    transition: 'var(--transition-fast)'
                  }}
                >
                  <div style={{ mt: '3px', color: 'var(--color-primary)' }}>
                    <FiBookOpen size={18} />
                  </div>
                  <div>
                    <div style={{ fontWeight: '600', fontSize: '0.9rem', color: 'var(--color-text)' }}>
                      {resource.title}
                    </div>
                    <div style={{ fontSize: '0.8rem', color: 'var(--color-text-secondary)', lineHeight: '1.4' }}>
                      {resource.source} • {resource.category}
                    </div>
                  </div>
                </a>
              );
            })
          )}
        </div>

        <button 
          onClick={() => navigate('/opportunities?tab=content')}
          className="btn-ghost" 
          style={{
            width: '100%',
            marginTop: '0.5rem',
            fontSize: '0.85rem',
            fontWeight: '600',
            color: 'var(--color-primary)'
          }}
        >
          Explore More Resources
        </button>
      </div>
    </div>
  );
};

export default SidebarRight;
