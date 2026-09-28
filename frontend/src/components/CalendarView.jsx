import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { calendarService } from '../services/calendarService';
import { Loading, EmptyState, ErrorState } from './ui';
import { FiCalendar, FiExternalLink } from 'react-icons/fi';
import '../App.css';

const KIND_META = {
  job: { label: 'Job deadline', bg: '#eff6ff', color: '#3b82f6' },
  hackathon: { label: 'Hackathon', bg: '#faf5ff', color: '#9333ea' },
  interview: { label: 'Interview', bg: '#ecfdf5', color: '#10b981' },
  application: { label: 'Application', bg: '#f8fafc', color: '#64748b' },
};

const CalendarView = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    if (!user) return;
    setLoading(true);
    setError(null);
    try {
      const data = await calendarService.getDeadlines();
      setEvents(data.events || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [user]);

  useEffect(() => {
    if (!user || user.role !== 'student') {
      navigate('/');
      return;
    }
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user, navigate]);

  if (!user || user.role !== 'student') return null;

  const formatDate = (d) => {
    if (!d) return '';
    const date = new Date(d);
    return date.toLocaleDateString(undefined, { weekday: 'short', year: 'numeric', month: 'short', day: 'numeric' });
  };
  const daysUntil = (d) => {
    if (!d) return Infinity;
    const diff = Math.ceil((new Date(d) - new Date()) / (1000 * 60 * 60 * 24));
    return diff;
  };

  return (
    <div className="dashboard-main custom-scrollbar">
      <div className="dashboard-header glass-panel" style={{
        position: 'sticky', top: 0, zIndex: 10, marginBottom: '1.5rem',
        borderRadius: '0 0 var(--radius-lg) var(--radius-lg)',
        borderBottom: '1px solid rgba(255,255,255,0.5)',
        background: 'rgba(255, 255, 255, 0.8)',
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        padding: '1rem 1.5rem',
      }}>
        <h1 className="dashboard-title" style={{
          background: 'var(--gradient-primary)',
          WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
          backgroundClip: 'text', display: 'flex', alignItems: 'center',
          gap: '0.75rem', fontSize: '1.5rem', margin: 0,
        }}>
          <FiCalendar size={24} style={{ color: '#667eea' }} />
          Deadline Calendar
        </h1>
        <a href={calendarService.getICalDownloadUrl()} target="_blank" rel="noopener noreferrer"
          className="edit-button" style={{ margin: 0, textDecoration: 'none', display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.85rem' }}>
          Export .ics
        </a>
      </div>

      <div className="dashboard-content" style={{ maxWidth: '800px', margin: '0 auto' }}>
        {loading && <Loading label="Loading deadlines..." />}
        {!loading && error && <ErrorState message={error} onRetry={load} />}
        {!loading && !error && events.length === 0 && (
          <EmptyState
            title="No upcoming deadlines"
            description="Your deadlines for jobs, hackathons, and interviews will appear here."
          />
        )}
        {!loading && !error && events.length > 0 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            {events.map((ev) => {
              const meta = KIND_META[ev.kind] || KIND_META.application;
              const remaining = daysUntil(ev.start);
              return (
                <div key={ev.id} className="interactive-card" style={{
                  padding: '1rem 1.25rem', background: 'white', borderRadius: '14px',
                  border: '1px solid #e2e8f0', display: 'flex', gap: '1rem',
                  alignItems: 'center', justifyContent: 'space-between',
                }}>
                  <div style={{ display: 'flex', gap: '1rem', alignItems: 'center', flex: 1, minWidth: 0 }}>
                    <div style={{
                      width: 44, height: 44, borderRadius: '10px', flexShrink: 0,
                      background: meta.bg, color: meta.color,
                      display: 'flex', flexDirection: 'column',
                      alignItems: 'center', justifyContent: 'center',
                      lineHeight: 1,
                    }}>
                      <span style={{ fontSize: '1.1rem', fontWeight: 700 }}>{new Date(ev.start).getDate()}</span>
                      <span style={{ fontSize: '0.55rem', textTransform: 'uppercase', letterSpacing: '0.03em' }}>
                        {new Date(ev.start).toLocaleString(undefined, { month: 'short' })}
                      </span>
                    </div>
                    <div style={{ minWidth: 0 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.15rem' }}>
                        <span style={{
                          fontSize: '0.65rem', fontWeight: 700, textTransform: 'uppercase',
                          background: meta.bg, color: meta.color,
                          padding: '0.15rem 0.5rem', borderRadius: '9999px'
                        }}>{meta.label}</span>
                        {remaining <= 2 && remaining >= 0 && (
                          <span style={{
                            fontSize: '0.65rem', fontWeight: 700, textTransform: 'uppercase',
                            background: '#fee2e2', color: '#dc2626',
                            padding: '0.15rem 0.5rem', borderRadius: '9999px'
                          }}>{remaining === 0 ? 'Today' : `${remaining}d left`}</span>
                        )}
                      </div>
                      <h3 style={{ margin: 0, color: '#1e293b', fontSize: '0.95rem' }}>{ev.title}</h3>
                      <p style={{ margin: 0, color: '#64748b', fontSize: '0.8rem' }}>
                        {formatDate(ev.start)}
                        {ev.location ? ` — ${ev.location}` : ''}
                      </p>
                    </div>
                  </div>
                  <div>
                    <button
                      onClick={() => ev.url && navigate(ev.url)}
                      className="hover-scale"
                      style={{
                        border: 'none', background: 'transparent', cursor: 'pointer',
                        color: '#6366f1', padding: '0.5rem',
                        display: 'flex', alignItems: 'center', gap: '0.35rem', fontSize: '0.8rem',
                      }}
                    >
                      View <FiExternalLink size={14} />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};

export default CalendarView;
