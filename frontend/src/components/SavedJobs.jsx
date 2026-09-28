import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { jobService } from '../services/jobService';
import { Loading, EmptyState, ErrorState } from './ui';
import { FiStar, FiMapPin, FiBriefcase } from 'react-icons/fi';
import '../App.css';

const SavedJobs = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const loadSaved = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await jobService.getSavedJobs();
      setJobs(Array.isArray(data) ? data : []);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!user || user.role !== 'student') {
      navigate('/');
      return;
    }
    loadSaved();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user, navigate]);

  const handleUnsave = async (jobId) => {
    try {
      await jobService.unsaveJob(jobId);
      setJobs((prev) => prev.filter((j) => (j.id || j._id) !== jobId));
    } catch (err) {
      setError(err.message);
    }
  };

  if (!user || user.role !== 'student') return null;

  return (
    <div className="dashboard-main custom-scrollbar">
      <div className="dashboard-header glass-panel" style={{
        position: 'sticky', top: 0, zIndex: 10, marginBottom: '1.5rem',
        borderRadius: '0 0 var(--radius-lg) var(--radius-lg)',
        borderBottom: '1px solid rgba(255,255,255,0.5)',
        background: 'rgba(255, 255, 255, 0.8)'
      }}>
        <h1 className="dashboard-title" style={{
          background: 'var(--gradient-primary)',
          WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
          backgroundClip: 'text', display: 'flex', alignItems: 'center',
          gap: '0.75rem', fontSize: '1.5rem'
        }}>
          <FiStar size={24} style={{ color: '#667eea' }} />
          Saved Jobs
        </h1>
      </div>

      <div className="dashboard-content" style={{ maxWidth: '800px', margin: '0 auto' }}>
        {loading && <Loading label="Loading saved jobs..." />}

        {!loading && error && <ErrorState message={error} onRetry={loadSaved} />}

        {!loading && !error && jobs.length === 0 && (
          <EmptyState
            title="No saved jobs yet"
            description="Save interesting jobs and they'll show up here for quick access."
          />
        )}

        {!loading && !error && jobs.length > 0 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {jobs.map((job) => (
              <div key={job.id || job._id} className="interactive-card" style={{
                padding: '1.25rem', background: 'white', borderRadius: '14px',
                border: '1px solid #e2e8f0', display: 'flex',
                justifyContent: 'space-between', alignItems: 'center', gap: '1rem'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', flex: 1 }}>
                  <div style={{
                    width: 44, height: 44, borderRadius: '10px',
                    background: 'linear-gradient(135deg,#e2e8f0,#f1f5f9)',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    color: '#64748b'
                  }}>
                    <FiBriefcase />
                  </div>
                  <div style={{ minWidth: 0 }}>
                    <h3 style={{ margin: 0, color: '#1e293b', fontSize: '1rem' }}>
                      {job.title}
                    </h3>
                    <div style={{ color: '#64748b', fontSize: '0.85rem', display: 'flex', gap: '1rem', marginTop: '0.25rem', flexWrap: 'wrap' }}>
                      <span>{job.company_name || 'Company'}</span>
                      {job.location && (
                        <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                          <FiMapPin size={12} /> {job.location}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  <button onClick={() => navigate(`/jobs/${job.id || job._id}`)} className="edit-button"
                    style={{ margin: 0, padding: '0.5rem 1rem' }}>View</button>
                  <button onClick={() => handleUnsave(job.id || job._id)} className="hover-scale"
                    style={{ margin: 0, padding: '0.5rem', border: '1px solid #e2e8f0', borderRadius: '8px', background: 'white', cursor: 'pointer', color: '#ef4444' }}
                    title="Remove">✕</button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

export default SavedJobs;
