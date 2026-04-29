import { useEffect, useState } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { interviewService } from '../../services/interviewService';
import InterviewCard from './InterviewCard';
import InterviewModal from './InterviewModal';
import FeedbackForm from './FeedbackForm';
import SidebarLeft from '../SidebarLeft';
import '../../App.css';

const InterviewsPage = () => {
  const { user } = useAuth();
  const [list, setList] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [filter, setFilter] = useState('all');
  const [showModal, setShowModal] = useState(false);
  const [feedbackInterview, setFeedbackInterview] = useState(null);

  const load = async () => {
    setLoading(true);
    try {
      const params = {};
      if (filter === 'upcoming') {
        params.upcoming_only = true;
      } else if (filter !== 'all') {
        params.status_filter = filter;
      }
      const data = await interviewService.listMine(params);
      setList(data.interviews || []);
      setError('');
    } catch (err) {
      setError(err.message || 'Failed to load interviews.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, [filter]);

  const handleUpdated = () => load();

  return (
    <div className="dashboard-container">
      <SidebarLeft />
      <div className="dashboard-main">
        <div className="dashboard-header animate-fade-in">
          <h1 className="dashboard-title" style={{
            background: 'var(--gradient-primary)',
            WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', backgroundClip: 'text'
          }}>Interviews</h1>
          <p style={{ color: '#666', marginTop: '0.25rem', fontSize: '0.9rem' }}>
            Track proposals and scheduled interviews.
          </p>
        </div>

        <div className="dashboard-content">
          <div className="glass-card animate-fade-in-up" style={{ padding: '1.5rem', borderRadius: 'var(--radius-lg)' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
              <div className="filter-row">
                <select
                  className="form-input"
                  style={{ minWidth: '150px' }}
                  value={filter}
                  onChange={(e) => setFilter(e.target.value)}
                >
                  <option value="all">All</option>
                  <option value="upcoming">Upcoming</option>
                  <option value="proposed">Proposed</option>
                  <option value="scheduled">Scheduled</option>
                  <option value="rescheduled">Rescheduled</option>
                </select>
              </div>

              {user?.role === 'recruiter' && (
                <button className="btn-glow" onClick={() => setShowModal(true)}>
                  + Propose Interview
                </button>
              )}
            </div>

            {error && <div className="error-message" style={{ marginBottom: '1rem' }}>{error}</div>}
            
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              {loading ? (
                <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--color-text-muted)' }}>Loading interviews...</div>
              ) : list.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--color-text-muted)' }}>No interviews yet.</div>
              ) : (
                list.map((interview) => (
                  <InterviewCard
                    key={interview.id}
                    interview={interview}
                    currentUser={user}
                    onUpdated={handleUpdated}
                    onFeedback={(id) => setFeedbackInterview(id)}
                  />
                ))
              )}
            </div>
          </div>
        </div>
      </div>

      {showModal && user?.role === 'recruiter' && (
        <InterviewModal
          isOpen
          onClose={() => setShowModal(false)}
          candidateId={null}
          onCreated={handleUpdated}
        />
      )}
      {feedbackInterview && (
        <FeedbackForm
          interviewId={feedbackInterview}
          onClose={() => setFeedbackInterview(null)}
          onSubmitted={handleUpdated}
        />
      )}
    </div>
  );
};

export default InterviewsPage;


