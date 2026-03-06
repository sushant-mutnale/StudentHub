import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { FiMapPin, FiBriefcase, FiClock, FiDollarSign, FiSearch, FiArrowRight } from 'react-icons/fi';
import { useAuth } from '../contexts/AuthContext';
import { jobService } from '../services/jobService';
import '../App.css';

const PAGE_SIZE = 20;

const JobFeed = ({ refreshTrigger = 0 }) => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [page, setPage] = useState(0);
  const [hasMore, setHasMore] = useState(false);

  useEffect(() => {
    setPage(0);
    loadJobs(0, true);
  }, [refreshTrigger]);

  const loadJobs = async (pageToLoad = page, replace = false) => {
    setLoading(true);
    try {
      const skip = pageToLoad * PAGE_SIZE;
      const data = await jobService.getJobs({ limit: PAGE_SIZE, skip });
      setJobs((prev) => (replace ? data : [...prev, ...data]));
      setHasMore(data.length === PAGE_SIZE);
      setError('');
    } catch (err) {
      setError(err.message || 'Unable to load jobs');
    } finally {
      setLoading(false);
    }
  };

  const handleLoadMore = () => {
    const nextPage = page + 1;
    setPage(nextPage);
    loadJobs(nextPage);
  };

  const formatTimestamp = (timestamp) => {
    if (!timestamp) return '';
    const date = new Date(timestamp);
    const now = new Date();
    const diff = (now - date) / (1000 * 60 * 60 * 24); // days

    if (diff < 1) return 'Today';
    if (diff < 2) return 'Yesterday';
    if (diff < 7) return `${Math.floor(diff)}d ago`;
    return date.toLocaleDateString();
  };

  if (!user || user.role !== 'student') {
    return null;
  }

  return (
    <div className="jobs-section animate-fade-in">
      {/* Header not needed as it's handled by parent section title */}

      {loading && jobs.length === 0 && (
        <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--color-text-muted)' }}>
          Loading opportunities...
        </div>
      )}

      {error && (
        <div style={{
          padding: '1rem',
          background: 'rgba(239, 68, 68, 0.1)',
          borderRadius: 'var(--radius-md)',
          color: 'var(--color-danger)',
          textAlign: 'center',
          marginBottom: '1rem'
        }}>
          {error}
        </div>
      )}

      {!loading && jobs.length === 0 && !error && (
        <div style={{
          textAlign: 'center',
          padding: '3rem',
          background: 'var(--color-bg-alt)',
          borderRadius: 'var(--radius-lg)',
          color: 'var(--color-text-muted)'
        }}>
          <FiBriefcase size={32} style={{ opacity: 0.5, marginBottom: '0.5rem' }} />
          <p>No jobs available right now.</p>
        </div>
      )}

      <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        {jobs.map((job, idx) => (
          <div
            key={job.id || idx}
            className="glass-card hover-lift"
            style={{
              padding: '1.25rem',
              borderRadius: 'var(--radius-md)',
              cursor: 'pointer',
              animationDelay: `${idx * 50}ms`
            }}
            onClick={() => {
              const applyUrl = job.url || job.apply_url || job.link;
              if (applyUrl) {
                window.open(applyUrl, '_blank', 'noopener,noreferrer');
              } else {
                navigate(`/jobs/${job.id}`);
              }
            }}
          >
            <div style={{ display: 'flex', gap: '1rem' }}>
              {/* Company Icon Placeholder */}
              <div style={{
                flexShrink: 0,
                width: '48px',
                height: '48px',
                background: 'linear-gradient(135deg, #f0f4ff 0%, #e0e7ff 100%)',
                borderRadius: '12px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'var(--color-primary)',
                fontSize: '1.2rem',
                fontWeight: '700'
              }}>
                {job.company_name ? job.company_name[0].toUpperCase() : <FiBriefcase />}
              </div>

              <div style={{ flex: 1 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <h3 style={{
                    margin: '0 0 0.25rem 0',
                    fontSize: '1.1rem',
                    color: 'var(--color-text)'
                  }}>
                    {job.title}
                  </h3>
                  <span style={{
                    fontSize: '0.8rem',
                    color: 'var(--color-text-muted)',
                    whiteSpace: 'nowrap',
                    background: 'var(--color-bg-alt)',
                    padding: '0.2rem 0.6rem',
                    borderRadius: 'var(--radius-full)'
                  }}>
                    {formatTimestamp(job.created_at)}
                  </span>
                </div>

                <div style={{
                  color: 'var(--color-primary)',
                  fontWeight: '500',
                  fontSize: '0.9rem',
                  marginBottom: '0.75rem',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem'
                }}>
                  {job.company_name || 'Hidden Company'}
                </div>

                <div style={{
                  display: 'flex',
                  flexWrap: 'wrap',
                  gap: '1rem',
                  fontSize: '0.85rem',
                  color: 'var(--color-text-secondary)',
                  marginBottom: '0.75rem'
                }}>
                  <span style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                    <FiMapPin size={14} /> {job.location || 'Remote'}
                  </span>
                  {job.salary_range && (
                    <span style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                      <FiDollarSign size={14} /> {job.salary_range}
                    </span>
                  )}
                  <span style={{ display: 'flex', alignItems: 'center', gap: '0.3rem' }}>
                    <FiClock size={14} /> {job.type || 'Full-time'}
                  </span>
                </div>

                <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                  {job.skills_required?.slice(0, 3).map((skill) => (
                    <span key={skill} style={{
                      fontSize: '0.75rem',
                      padding: '0.2rem 0.6rem',
                      background: 'rgba(102, 126, 234, 0.08)',
                      color: 'var(--color-primary)',
                      borderRadius: 'var(--radius-sm)',
                      fontWeight: '500'
                    }}>
                      {skill}
                    </span>
                  ))}
                  {job.skills_required?.length > 3 && (
                    <span style={{
                      fontSize: '0.75rem',
                      padding: '0.2rem 0.6rem',
                      background: 'var(--color-bg-alt)',
                      color: 'var(--color-text-muted)',
                      borderRadius: 'var(--radius-sm)'
                    }}>
                      +{job.skills_required.length - 3} more
                    </span>
                  )}
                </div>
              </div>
            </div>
            {/* Apply link */}
            {(job.url || job.apply_url) && (
              <div style={{ marginTop: '0.75rem', display: 'flex', justifyContent: 'flex-end' }}>
                <a
                  href={job.url || job.apply_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  onClick={e => e.stopPropagation()}
                  className="btn-glow"
                  style={{
                    display: 'inline-flex', alignItems: 'center', gap: '0.35rem',
                    padding: '0.4rem 1rem', background: 'var(--gradient-primary)',
                    color: 'white', borderRadius: 'var(--radius-full)', fontSize: '0.8rem',
                    fontWeight: '600', textDecoration: 'none'
                  }}
                >
                  Apply Now <FiArrowRight size={13} />
                </a>
              </div>
            )}
          </div>
        ))}
      </div>

      {hasMore && !loading && (
        <button
          onClick={handleLoadMore}
          className="btn-ghost"
          style={{ width: '100%', marginTop: '1rem', color: 'var(--color-primary)' }}
        >
          Load More Opportunities
        </button>
      )}
    </div>
  );
};

export default JobFeed;
