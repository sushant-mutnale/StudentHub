import { useEffect, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { interviewService } from '../../services/interviewService';
import InterviewCard from './InterviewCard';
import FeedbackForm from './FeedbackForm';
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
    return <div className="messages-layout"><div className="empty-state">Loading interview...</div></div>;
  }

  if (!interview) {
    return (
      <div className="messages-layout">
        <div className="empty-state">
          <p>{error || 'Interview not found.'}</p>
          <button className="form-button" onClick={() => navigate('/interviews')}>
            Back
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="messages-layout">
      <div className="messages-panel">
        <button className="back-button" onClick={() => navigate('/interviews')}>
          ← Back to interviews
        </button>
        <InterviewCard
          interview={interview}
          currentUser={user}
          onUpdated={(updated) => setInterview(updated)}
          onFeedback={() => setShowFeedback(true)}
        />
        {interview.feedback?.length > 0 && (
          <div className="feedback-list">
            <h3>Feedback</h3>
            {interview.feedback.map((fb, idx) => (
              <div key={idx} className="feedback-item">
                <strong>Rating:</strong> {fb.rating || 'n/a'} <br />
                <strong>Comment:</strong> {fb.comment || 'n/a'}
              </div>
            ))}
          </div>
        )}
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


