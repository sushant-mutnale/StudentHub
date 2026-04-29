import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { FiMessageSquare, FiPlus } from 'react-icons/fi';
import { useAuth } from '../../contexts/AuthContext';
import { messageService } from '../../services/messageService';
import SidebarLeft from '../SidebarLeft';
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
    <div className="dashboard-container">
      <SidebarLeft />
      <div className="dashboard-main">
        <div className="dashboard-header animate-fade-in">
          <h1 className="dashboard-title" style={{
            background: 'var(--gradient-primary)',
            WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', backgroundClip: 'text'
          }}>Inbox</h1>
          <p style={{ color: '#666', marginTop: '0.25rem', fontSize: '0.9rem' }}>
            View recent threads and unread messages.
          </p>
        </div>

        <div className="dashboard-content">

          <div className="glass-card animate-fade-in-up" style={{ marginBottom: '2rem', padding: '1.5rem', borderRadius: 'var(--radius-lg)' }}>
            <form className="new-thread-form" onSubmit={handleCreateThread}>
              <h3 style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem', color: 'var(--color-text)' }}>
                <span style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: '32px', height: '32px', background: 'var(--gradient-primary)', borderRadius: 'var(--radius-md)', color: 'white' }}>
                  <FiPlus size={16} />
                </span>
                Start a new thread
              </h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
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
                <button className="btn-glow" type="submit" disabled={creating} style={{ alignSelf: 'flex-start' }}>
                  {creating ? 'Creating...' : 'Create Thread'}
                </button>
              </div>
            </form>
          </div>

          <div className="glass-card animate-fade-in-up delay-100" style={{ padding: '1.5rem', borderRadius: 'var(--radius-lg)' }}>
            {error && (
              <div className="error-message" style={{ marginBottom: '1rem' }}>
                {error}
              </div>
            )}

            {loading ? (
              <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--color-text-muted)' }}>Loading threads...</div>
            ) : threads.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--color-text-muted)' }}>
                No conversations yet. Start one using the form above.
              </div>
            ) : (
              <ul className="thread-list" style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', padding: 0, margin: 0 }}>
                {sortedThreads.map((thread) => (
                  <li
                    key={thread.id}
                    className="interactive-card"
                    style={{
                      background: 'var(--color-bg-alt)',
                      padding: '1.25rem',
                      borderRadius: 'var(--radius-md)',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      gap: '1rem'
                    }}
                    onClick={() => navigate(`/messages/${thread.id}`)}
                  >
                    <div className="thread-info" style={{ flex: 1, minWidth: 0 }}>
                      <div className="thread-title" style={{ fontWeight: '600', color: 'var(--color-text)', display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
                        <FiMessageSquare style={{ color: 'var(--color-primary)' }} />
                        <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{renderParticipants(thread)}</span>
                      </div>
                      <div className="thread-preview" style={{ color: 'var(--color-text-secondary)', fontSize: '0.9rem', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {thread.last_message_preview || 'No messages yet'}
                      </div>
                    </div>
                    <div className="thread-meta" style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '0.25rem', flexShrink: 0 }}>
                      {thread.last_message_at && (
                        <span className="thread-time" style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)' }}>
                          {new Date(thread.last_message_at).toLocaleString([], { dateStyle: 'short', timeStyle: 'short' })}
                        </span>
                      )}
                      {thread.unread_count > 0 && (
                        <span className="thread-unread" style={{ background: 'var(--gradient-primary)', color: 'white', fontSize: '0.75rem', padding: '0.15rem 0.6rem', borderRadius: 'var(--radius-full)', fontWeight: '600' }}>{thread.unread_count} new</span>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Inbox;


