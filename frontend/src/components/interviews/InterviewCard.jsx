import { useState } from 'react';
import { interviewService } from '../../services/interviewService';
import '../../App.css';

const formatSlot = (slot) => {
  if (!slot) return 'Not scheduled';
  return `${new Date(slot.start).toLocaleString()} → ${new Date(slot.end).toLocaleTimeString()} (${slot.timezone})`;
};

const InterviewCard = ({ interview, currentUser, onUpdated, onFeedback }) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const isRecruiter = currentUser?.role === 'recruiter' && currentUser?.id === interview.recruiter_id;
  const isCandidate = currentUser?.id === interview.candidate_id;

  const act = async (action, payload) => {
    setLoading(true);
    setError('');
    try {
      let updated;
      if (action === 'accept') {
        updated = await interviewService.accept(interview.id, payload);
      } else if (action === 'decline') {
        updated = await interviewService.decline(interview.id, payload);
      } else if (action === 'cancel') {
        updated = await interviewService.cancel(interview.id, payload);
      }
      onUpdated?.(updated);
    } catch (err) {
      setError(err.message || 'Action failed.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="interview-card">
      <div>
        <div className="interview-title">
          Interview • {interview.status.toUpperCase()}
        </div>
        <div className="interview-slot">{formatSlot(interview.scheduled_slot)}</div>
        <div className="interview-location">
          {interview.location?.type === 'online'
            ? `Online: ${interview.location?.url || 'TBD'}`
            : `Onsite: ${interview.location?.address || 'TBD'}`}
        </div>
        {interview.description && (
          <p className="interview-desc">{interview.description}</p>
        )}
        {error && <div className="error-message">{error}</div>}
      </div>

      <div className="interview-actions">
        {isCandidate && interview.status === 'proposed' && (
          <>
            <button
              className="form-button"
              disabled={loading}
              onClick={() => act('accept', { slot_index: 0 })}
            >
              Accept first slot
            </button>
            <button
              className="form-button outline"
              disabled={loading}
              onClick={() => act('decline', { reason: 'Not available' })}
            >
              Decline
            </button>
          </>
        )}
        {interview.status === 'scheduled' && (
          <button
            className="form-button outline"
            disabled={loading}
            onClick={() => act('cancel', { reason: 'Need to cancel' })}
          >
            Cancel
          </button>
        )}
        {isRecruiter && interview.status === 'scheduled' && (
          <button
            className="form-button outline"
            type="button"
            disabled={loading}
            onClick={() => onFeedback?.(interview.id)}
          >
            Add Feedback
          </button>
        )}
      </div>
    </div>
  );
};

export default InterviewCard;


