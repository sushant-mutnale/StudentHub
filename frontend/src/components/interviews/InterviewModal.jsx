import { useEffect, useState } from 'react';
import { interviewService } from '../../services/interviewService';
import '../../App.css';

const defaultSlot = () => ({
  start: '',
  end: '',
  timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC',
});

const InterviewModal = ({
  isOpen,
  onClose,
  candidateId,
  initialCandidate,
  jobId,
  threadId,
  onCreated,
}) => {
  const [slots, setSlots] = useState([defaultSlot()]);
  const [locationType, setLocationType] = useState('online');
  const [url, setUrl] = useState('');
  const [address, setAddress] = useState('');
  const [description, setDescription] = useState('');
  const [selectedCandidate, setSelectedCandidate] = useState(initialCandidate || null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  useEffect(() => {
    setSelectedCandidate(initialCandidate || null);
  }, [initialCandidate]);

  if (!isOpen) return null;

  const updateSlot = (index, field, value) => {
    setSlots((prev) =>
      prev.map((slot, idx) => (idx === index ? { ...slot, [field]: value } : slot))
    );
  };

  const addSlot = () => setSlots((prev) => [...prev, defaultSlot()]);
  const removeSlot = (index) => setSlots((prev) => prev.filter((_, idx) => idx !== index));

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError('');
    setSuccess('');

    const activeCandidateId = candidateId || selectedCandidate?.id;
    if (!activeCandidateId) {
      setError('Please choose a candidate to send this interview proposal to.');
      return;
    }
    if (slots.some((slot) => !slot.start || !slot.end)) {
      setError('Please complete all proposed time slots.');
      return;
    }

    setLoading(true);
    try {
      const payload = {
        candidate_id: activeCandidateId,
        job_id: jobId,
        thread_id: threadId,
        description,
        proposed_times: slots.map((slot) => ({
          start: new Date(slot.start).toISOString(),
          end: new Date(slot.end).toISOString(),
          timezone: slot.timezone,
        })),
        location: {
          type: locationType,
          url: locationType === 'online' ? url : undefined,
          address: locationType === 'onsite' ? address : undefined,
        },
      };
      const interview = await interviewService.create(payload);
      setSuccess('Interview proposed!');
      setSlots([defaultSlot()]);
      setDescription('');
      setUrl('');
      setAddress('');
      onCreated?.(interview);
    } catch (err) {
      setError(err.message || 'Failed to create interview.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="modal-overlay">
      <div className="modal-card">
        <div className="modal-header">
          <h2>Propose Interview</h2>
          <button className="modal-close" type="button" onClick={onClose}>
            ✕
          </button>
        </div>
        <form className="auth-form" onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label">Candidate</label>
            {selectedCandidate ? (
              <div className="candidate-pill">
                <div>
                  <div style={{ fontWeight: 600 }}>
                    {selectedCandidate.full_name || selectedCandidate.username}
                  </div>
                  <div style={{ color: '#666', fontSize: '0.9rem' }}>
                    @{selectedCandidate.username}
                  </div>
                </div>
              </div>
            ) : (
              <div className="info-message">
                Candidate will be selected automatically when launching this modal from a conversation or job match.
              </div>
            )}
          </div>
          <div className="form-group">
            <label className="form-label">Proposed time slots</label>
            {slots.map((slot, index) => (
              <div key={index} className="slot-row">
                <input
                  type="datetime-local"
                  value={slot.start}
                  onChange={(e) => updateSlot(index, 'start', e.target.value)}
                  className="form-input"
                  required
                />
                <input
                  type="datetime-local"
                  value={slot.end}
                  onChange={(e) => updateSlot(index, 'end', e.target.value)}
                  className="form-input"
                  required
                />
                <input
                  type="text"
                  value={slot.timezone}
                  onChange={(e) => updateSlot(index, 'timezone', e.target.value)}
                  className="form-input"
                />
                {slots.length > 1 && (
                  <button
                    type="button"
                    className="form-button outline"
                    onClick={() => removeSlot(index)}
                  >
                    Remove
                  </button>
                )}
              </div>
            ))}
            <button type="button" className="form-button outline" onClick={addSlot}>
              + Add Slot
            </button>
          </div>

          <div className="form-group">
            <label className="form-label">Location</label>
            <select
              className="form-input"
              value={locationType}
              onChange={(e) => setLocationType(e.target.value)}
            >
              <option value="online">Online (URL)</option>
              <option value="onsite">Onsite (address)</option>
            </select>
            {locationType === 'online' ? (
              <input
                type="url"
                placeholder="Meeting link"
                className="form-input"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                required
              />
            ) : (
              <input
                type="text"
                placeholder="Office address"
                className="form-input"
                value={address}
                onChange={(e) => setAddress(e.target.value)}
                required
              />
            )}
          </div>

          <div className="form-group">
            <label className="form-label">Description / Agenda</label>
            <textarea
              className="form-textarea"
              rows={3}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </div>

          {error && <div className="error-message">{error}</div>}
          {success && <div className="success-message">{success}</div>}

          <div className="composer-actions" style={{ gap: '0.5rem' }}>
            <button type="button" className="form-button outline" onClick={onClose}>
              Close
            </button>
            <button type="submit" className="form-button" disabled={loading}>
              {loading ? 'Sending...' : 'Send Proposal'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default InterviewModal;


