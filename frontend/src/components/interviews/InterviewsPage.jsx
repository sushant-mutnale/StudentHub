import { useEffect, useState } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import { interviewService } from '../../services/interviewService';
import InterviewCard from './InterviewCard';
import InterviewModal from './InterviewModal';
import FeedbackForm from './FeedbackForm';
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
    <div className="messages-layout">
      <div className="messages-panel">
        <div className="conversation-header">
          <div>
            <h2>Interviews</h2>
            <p style={{ color: '#666', marginTop: '0.25rem' }}>
              Track proposals and scheduled interviews.
            </p>
          </div>
          {user?.role === 'recruiter' && (
            <button className="form-button" onClick={() => setShowModal(true)}>
              + Propose Interview
            </button>
          )}
        </div>

        <div className="filter-row">
          <select
            className="form-input"
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

        {error && <div className="error-message">{error}</div>}
        {loading ? (
          <div className="empty-state">Loading interviews...</div>
        ) : list.length === 0 ? (
          <div className="empty-state">No interviews yet.</div>
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


