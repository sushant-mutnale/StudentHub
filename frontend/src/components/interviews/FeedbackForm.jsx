import { useState } from 'react';
import { interviewService } from '../../services/interviewService';
import '../../App.css';

const FeedbackForm = ({ interviewId, onClose, onSubmitted }) => {
  const [rating, setRating] = useState(5);
  const [comment, setComment] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError('');
    setLoading(true);
    try {
      const updated = await interviewService.feedback(interviewId, {
        rating,
        comment,
      });
      onSubmitted?.(updated);
      onClose();
    } catch (err) {
      setError(err.message || 'Failed to submit feedback.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay">
      <div className="modal-card">
        <div className="modal-header">
          <h2>Interview Feedback</h2>
          <button className="modal-close" type="button" onClick={onClose}>
            ✕
          </button>
        </div>
        <form className="auth-form" onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label">Rating (1-5)</label>
            <input
              type="number"
              min="1"
              max="5"
              className="form-input"
              value={rating}
              onChange={(e) => setRating(parseInt(e.target.value, 10))}
              required
            />
          </div>
          <div className="form-group">
            <label className="form-label">Comment</label>
            <textarea
              className="form-textarea"
              rows={4}
              value={comment}
              onChange={(e) => setComment(e.target.value)}
            />
          </div>
          {error && <div className="error-message">{error}</div>}
          <div className="composer-actions" style={{ gap: '0.5rem' }}>
            <button type="button" className="form-button outline" onClick={onClose}>
              Close
            </button>
            <button type="submit" className="form-button" disabled={loading}>
              {loading ? 'Saving...' : 'Submit'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default FeedbackForm;


