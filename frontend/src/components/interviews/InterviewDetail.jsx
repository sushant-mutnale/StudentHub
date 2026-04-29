import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { interviewService } from '../../services/interviewService';
import InterviewCard from './InterviewCard';
import FeedbackForm from './FeedbackForm';
import SidebarLeft from '../SidebarLeft';
import '../../App.css';

const InterviewDetail = () => {
  const { id } = useParams();
  const { user } = useAuth();
  const navigate = useNavigate();
  const [interview, setInterview] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showFeedback, setShowFeedback] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const data = await interviewService.getById(id);
      setInterview(data);
      setError('');
    } catch (err) {
      setError(err.message || 'Failed to load interview.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [id]);

  if (loading) {
    return (
      <div className="dashboard-container">
        <SidebarLeft />
        <div className="dashboard-main" style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '50vh' }}>
          <div style={{ color: 'var(--color-text-muted)' }}>Loading interview...</div>
        </div>
      </div>
    );
  }

  if (!interview) {
    return (
      <div className="dashboard-container">
        <SidebarLeft />
        <div className="dashboard-main" style={{ padding: '2rem' }}>
          <div className="glass-card animate-fade-in-up" style={{ padding: '2rem', textAlign: 'center', borderRadius: 'var(--radius-lg)' }}>
            <p style={{ color: 'var(--color-text)', marginBottom: '1.5rem', fontSize: '1.1rem' }}>{error || 'Interview not found.'}</p>
            <button className="btn-glow hover-lift" onClick={() => navigate('/interviews')} style={{ padding: '0.75rem 1.5rem' }}>
              Back to Interviews
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="dashboard-container">
      <SidebarLeft />
      <div className="dashboard-main">
        <div className="dashboard-header animate-fade-in">
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <button
              onClick={() => navigate('/interviews')}
              style={{
                background: 'none', border: 'none', color: 'var(--color-text-muted)',
                cursor: 'pointer', display: 'flex', alignItems: 'center', fontSize: '1.5rem',
                padding: '0.25rem', borderRadius: '50%', transition: 'background 0.2s'
              }}
              onMouseOver={(e) => e.currentTarget.style.background = 'var(--color-bg-alt)'}
              onMouseOut={(e) => e.currentTarget.style.background = 'transparent'}
            >
              ←
            </button>
            <h1 className="dashboard-title" style={{
              background: 'var(--gradient-primary)',
              WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', backgroundClip: 'text',
              margin: 0
            }}>Interview Details</h1>
          </div>
        </div>

        <div className="dashboard-content">
          <div className="glass-card animate-fade-in-up" style={{ padding: '1.5rem', borderRadius: 'var(--radius-lg)' }}>
            <InterviewCard
              interview={interview}
              currentUser={user}
              onUpdated={(updated) => setInterview(updated)}
              onFeedback={() => setShowFeedback(true)}
            />
            {interview.feedback?.length > 0 && (
              <div style={{ marginTop: '2rem', borderTop: '1px solid var(--color-border)', paddingTop: '1.5rem' }}>
                <h3 style={{ color: 'var(--color-text)', marginBottom: '1rem', fontSize: '1.1rem' }}>Feedback</h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                  {interview.feedback.map((fb, idx) => (
                    <div key={idx} style={{
                      padding: '1.25rem', background: 'var(--color-bg-alt)',
                      borderRadius: 'var(--radius-md)', border: '1px solid var(--color-border)'
                    }}>
                      <div style={{ marginBottom: '0.5rem', fontWeight: '600', color: 'var(--color-primary)' }}>
                        Rating: <span style={{ color: 'var(--color-text)' }}>{fb.rating || 'n/a'}</span>
                      </div>
                      <div style={{ color: 'var(--color-text-secondary)', lineHeight: '1.5' }}>
                        {fb.comment || 'No comment provided.'}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
      {showFeedback && (
        <FeedbackForm
          interviewId={id}
          onClose={() => setShowFeedback(false)}
          onSubmitted={(updated) => setInterview(updated)}
        />
      )}
    </div>
  );
};

export default InterviewDetail;


