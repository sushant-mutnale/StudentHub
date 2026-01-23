import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { FiMessageSquare, FiPlus } from 'react-icons/fi';
import { useAuth } from '../../contexts/AuthContext';
import { messageService } from '../../services/messageService';
import '../../App.css';

const Inbox = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [threads, setThreads] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [participantUsername, setParticipantUsername] = useState('');
  const [initialMessage, setInitialMessage] = useState('');
  const [creating, setCreating] = useState(false);

  const fetchThreads = async () => {
    setLoading(true);
    try {
      const data = await messageService.listThreads();
      setThreads(data.threads || []);
      setError('');
    } catch (err) {
      setError(err.message || 'Failed to load threads.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchThreads();
  }, []);

  const handleCreateThread = async (event) => {
    event.preventDefault();
    if (!participantUsername.trim()) {
      setError('Enter a username to start a thread.');
      return;
    }
    setCreating(true);
    try {
      const payload = {
        participant_usernames: [participantUsername.trim()],
        initial_message: initialMessage.trim() || undefined,
      };
      const thread = await messageService.createThread(payload);
      setParticipantUsername('');
      setInitialMessage('');
      await fetchThreads();
      navigate(`/messages/${thread.id}`);
    } catch (err) {
      setError(err.message || 'Unable to create thread.');
    } finally {
      setCreating(false);
    }
  };

  const renderParticipants = (thread) => {
    if (!user) return 'Conversation';
    const others = thread.participants.filter((p) => p.id !== user.id);
    if (others.length === 0) {
      return thread.participants.map((p) => p.username).join(', ');
    }
    return others.map((p) => p.full_name || p.username).join(', ');
  };

  const sortedThreads = useMemo(
    () =>
      [...threads].sort((a, b) => {
        const aTime = a.last_message_at ? new Date(a.last_message_at).getTime() : 0;
        const bTime = b.last_message_at ? new Date(b.last_message_at).getTime() : 0;
        return bTime - aTime;
      }),
    [threads]
  );

  return (
    <div className="messages-layout">
      <div className="messages-panel">
        <div className="dashboard-header" style={{ position: 'static' }}>
          <h1 className="dashboard-title">Inbox</h1>
          <p style={{ color: '#666', marginTop: '0.25rem' }}>
            View recent threads and unread messages.
          </p>
        </div>

        <form className="new-thread-form" onSubmit={handleCreateThread}>
          <h3>
            <FiPlus style={{ marginRight: '0.5rem' }} />
            Start a new thread
          </h3>
          <div className="form-group">
            <label className="form-label">Recipient username</label>
            <input
              type="text"
              className="form-input"
              placeholder="e.g. demo_recruiter"
              value={participantUsername}
              onChange={(e) => setParticipantUsername(e.target.value)}
              disabled={creating}
              required
            />
          </div>
          <div className="form-group">
            <label className="form-label">Initial message (optional)</label>
            <textarea
              className="form-textarea"
              rows={3}
              value={initialMessage}
              onChange={(e) => setInitialMessage(e.target.value)}
              disabled={creating}
            />
          </div>
          <button className="form-button" type="submit" disabled={creating}>
            {creating ? 'Creating...' : 'Create Thread'}
          </button>
        </form>

        {error && (
          <div className="error-message" style={{ marginBottom: '1rem' }}>
            {error}
          </div>
        )}

        {loading ? (
          <div className="empty-state">Loading threads...</div>
        ) : threads.length === 0 ? (
          <div className="empty-state">
            No conversations yet. Start one using the form above.
          </div>
        ) : (
          <ul className="thread-list">
            {sortedThreads.map((thread) => (
              <li
                key={thread.id}
                className="thread-list-item"
                onClick={() => navigate(`/messages/${thread.id}`)}
              >
                <div className="thread-info">
                  <div className="thread-title">
                    <FiMessageSquare style={{ marginRight: '0.5rem' }} />
                    {renderParticipants(thread)}
                  </div>
                  <div className="thread-preview">
                    {thread.last_message_preview || 'No messages yet'}
                  </div>
                </div>
                <div className="thread-meta">
                  {thread.last_message_at && (
                    <span className="thread-time">
                      {new Date(thread.last_message_at).toLocaleString()}
                    </span>
                  )}
                  {thread.unread_count > 0 && (
                    <span className="thread-unread">{thread.unread_count}</span>
                  )}
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
};

export default Inbox;


