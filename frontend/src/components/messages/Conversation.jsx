import { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { FiArrowLeft } from 'react-icons/fi';
import { useAuth } from '../../contexts/AuthContext';
import { messageService } from '../../services/messageService';
import MessageComposer from './MessageComposer';
import InterviewModal from '../interviews/InterviewModal';
import SidebarLeft from '../SidebarLeft';
import '../../App.css';

const Conversation = () => {
  const { threadId } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const [thread, setThread] = useState(null);
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [sending, setSending] = useState(false);
  const [showInterviewModal, setShowInterviewModal] = useState(false);
  const endRef = useRef(null);

  const loadThread = async () => {
    setLoading(true);
    try {
      const data = await messageService.getThread(threadId);
      setThread(data.thread);
      setMessages(data.messages);
      await messageService.markThreadRead(threadId);
      setError('');
    } catch (err) {
      setError(err.message || 'Failed to load conversation.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadThread();
  }, [threadId]);

  useEffect(() => {
    if (endRef.current) {
      endRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);

  const onSend = async (text) => {
    setSending(true);
    const tempId = `temp-${Date.now()}`;
    const optimisticMessage = {
      id: tempId,
      thread_id: threadId,
      sender_id: user?.id,
      text,
      created_at: new Date().toISOString(),
      read_by: [user?.id],
      optimistic: true,
    };
    setMessages((prev) => [...prev, optimisticMessage]);

    try {
      const savedMessage = await messageService.sendMessage(threadId, { text });
      setMessages((prev) =>
        prev.map((msg) => (msg.id === tempId ? savedMessage : msg))
      );
      await messageService.markThreadRead(threadId);
    } catch (err) {
      setMessages((prev) => prev.filter((msg) => msg.id !== tempId));
      setError(err.message || 'Failed to send message.');
      throw err;
    } finally {
      setSending(false);
    }
  };

  const primaryPartner = useMemo(() => {
    if (!thread || !user) return null;
    return thread.participants.find((p) => p.id !== user.id) || thread.participants[0];
  }, [thread, user]);

  const participantsLabel = useMemo(() => {
    if (!thread || !user) return 'Conversation';
    const others = thread.participants.filter((p) => p.id !== user.id);
    if (others.length === 0) {
      return thread.participants.map((p) => p.username).join(', ');
    }
    return others.map((p) => p.full_name || p.username).join(', ');
  }, [thread, user]);

  if (loading) {
    return (
      <div className="dashboard-container">
        <SidebarLeft />
        <div className="dashboard-main" style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '50vh' }}>
          <div style={{ color: 'var(--color-text-muted)' }}>Loading conversation...</div>
        </div>
      </div>
    );
  }

  if (error && !thread) {
    return (
      <div className="dashboard-container">
        <SidebarLeft />
        <div className="dashboard-main" style={{ padding: '2rem' }}>
          <div className="glass-card animate-fade-in-up" style={{ padding: '2rem', textAlign: 'center', borderRadius: 'var(--radius-lg)' }}>
            <p style={{ color: 'var(--color-text)', marginBottom: '1.5rem', fontSize: '1.1rem' }}>{error}</p>
            <button className="btn-glow hover-lift" onClick={loadThread} style={{ padding: '0.75rem 1.5rem' }}>
              Retry
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="dashboard-container">
      <SidebarLeft />
      <div className="dashboard-main" style={{ display: 'flex', flexDirection: 'column', height: '100vh', paddingBottom: '1rem' }}>
        <div className="dashboard-header animate-fade-in" style={{ paddingBottom: '1rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
              <button
                onClick={() => navigate('/messages')}
                style={{
                  background: 'none', border: 'none', color: 'var(--color-text-muted)',
                  cursor: 'pointer', display: 'flex', alignItems: 'center', fontSize: '1.5rem',
                  padding: '0.25rem', borderRadius: '50%', transition: 'background 0.2s'
                }}
                onMouseOver={(e) => e.currentTarget.style.background = 'var(--color-bg-alt)'}
                onMouseOut={(e) => e.currentTarget.style.background = 'transparent'}
              >
                <FiArrowLeft size={24} />
              </button>
              <div>
                <h2 style={{
                  margin: 0,
                  fontSize: '1.25rem',
                  background: 'var(--gradient-primary)',
                  WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', backgroundClip: 'text'
                }}>{participantsLabel}</h2>
                <p style={{ color: 'var(--color-text-muted)', margin: 0, fontSize: '0.85rem' }}>
                  {thread?.participants.length} participants
                </p>
              </div>
            </div>
            {user?.role === 'recruiter' && primaryPartner && (
              <button className="btn-glow" onClick={() => setShowInterviewModal(true)}>
                Propose Interview
              </button>
            )}
          </div>
        </div>

        <div className="dashboard-content" style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', padding: '1rem 1.5rem' }}>
          <div className="glass-card animate-fade-in-up" style={{ flex: 1, display: 'flex', flexDirection: 'column', borderRadius: 'var(--radius-lg)', overflow: 'hidden' }}>

            {error && (
              <div className="error-message" style={{ margin: '1rem', borderRadius: 'var(--radius-md)' }}>
                {error}
              </div>
            )}

            <div className="messages-list" style={{ flex: 1, overflowY: 'auto', padding: '1.5rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              {messages.map((message) => {
                const isMine = message.sender_id === user?.id;
                return (
                  <div
                    key={message.id}
                    className="animate-fade-in-up"
                    style={{
                      alignSelf: isMine ? 'flex-end' : 'flex-start',
                      maxWidth: '75%',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '0.25rem'
                    }}
                  >
                    <div style={{
                      padding: '0.75rem 1rem',
                      borderRadius: isMine ? '16px 16px 4px 16px' : '16px 16px 16px 4px',
                      background: isMine ? 'var(--gradient-primary)' : 'var(--color-bg-alt)',
                      color: isMine ? 'white' : 'var(--color-text)',
                      boxShadow: 'var(--shadow-sm)',
                      lineHeight: '1.5',
                      whiteSpace: 'pre-wrap',
                      wordBreak: 'break-word',
                      border: isMine ? 'none' : '1px solid var(--color-border)'
                    }}>
                      {message.text}
                    </div>
                    <div style={{
                      fontSize: '0.75rem',
                      color: 'var(--color-text-muted)',
                      textAlign: isMine ? 'right' : 'left',
                      padding: '0 0.25rem'
                    }}>
                      {new Date(message.created_at).toLocaleString([], { dateStyle: 'short', timeStyle: 'short' })}
                      {message.optimistic && <span style={{ fontStyle: 'italic', marginLeft: '0.25rem' }}>(sending...)</span>}
                    </div>
                  </div>
                );
              })}
              <div ref={endRef} />
            </div>

            <div style={{ padding: '1rem 1.5rem', borderTop: '1px solid var(--color-border)', background: 'var(--color-bg)' }}>
              <MessageComposer onSend={onSend} disabled={sending} />
            </div>

          </div>
        </div>
      </div>

      {showInterviewModal && (
        <InterviewModal
          isOpen
          onClose={() => setShowInterviewModal(false)}
          candidateId={primaryPartner?.id}
          initialCandidate={primaryPartner}
          threadId={threadId}
          onCreated={() => {
            setShowInterviewModal(false);
            loadThread();
          }}
        />
      )}
    </div>
  );
};

export default Conversation;


