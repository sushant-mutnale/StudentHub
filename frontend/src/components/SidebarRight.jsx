import { useState, useEffect } from 'react';
import { FiCalendar, FiUsers, FiBookOpen, FiCode, FiLayers, FiTrendingUp, FiBriefcase } from 'react-icons/fi';
import { api } from '../api/client';
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
  const [contests, setContests] = useState([]);
  const [resources, setResources] = useState([]);
  const [loadingContests, setLoadingContests] = useState(true);
  const [loadingResources, setLoadingResources] = useState(true);

  useEffect(() => {
    const fetchSidebarData = async () => {
      try {
        setLoadingContests(true);
        const { data: eventsData } = await api.get('/events/upcoming?limit=3');
        setContests(eventsData || []);
      } catch (err) {
        console.error('Failed to fetch events:', err);
      } finally {
        setLoadingContests(false);
      }

      try {
        setLoadingResources(true);
        const { data: resourcesData } = await api.get('/resources/recommended?limit=3');
        setResources(resourcesData || []);
      } catch (err) {
        console.error('Failed to fetch resources:', err);
      } finally {
        setLoadingResources(false);
      }
    };

    fetchSidebarData();
  }, []);

  return (
    <div className="sidebar-right animate-fade-in-left">
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
          <span style={{ fontSize: '0.8rem', color: 'var(--color-primary)', fontWeight: '600', cursor: 'pointer' }}>View All</span>
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
              return (
                <div
                  key={contest.id}
                  className="interactive-card hover-lift"
                  onClick={() => window.open(contest.url, '_blank', 'noopener,noreferrer')}
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
            resources.map((resource) => (
              <a
                key={resource.id}
                href={resource.url || '#'}
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
            ))
          )}
        </div>

        <button className="btn-ghost" style={{
          width: '100%',
          marginTop: '0.5rem',
          fontSize: '0.85rem',
          fontWeight: '600',
          color: 'var(--color-primary)'
        }}>
          Explore More Resources
        </button>
      </div>
    </div>
  );
};

export default SidebarRight;
