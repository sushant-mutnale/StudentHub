import { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { FiArrowLeft } from 'react-icons/fi';
import { useAuth } from '../../contexts/AuthContext';
import { messageService } from '../../services/messageService';
import MessageComposer from './MessageComposer';
import InterviewModal from '../interviews/InterviewModal';
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
    return <div className="messages-layout"><div className="empty-state">Loading conversation...</div></div>;
  }

  if (error && !thread) {
    return (
      <div className="messages-layout">
        <div className="empty-state">
          <p style={{ marginBottom: '1rem' }}>{error}</p>
          <button className="form-button" onClick={loadThread}>
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="messages-layout">
      <div className="messages-panel">
        <div className="conversation-header">
          <button className="back-button" onClick={() => navigate('/messages')}>
            <FiArrowLeft /> Inbox
          </button>
          <div>
            <h2>{participantsLabel}</h2>
            <p style={{ color: '#666', marginTop: '0.25rem' }}>
              {thread?.participants.length} participants
            </p>
          </div>
          {user?.role === 'recruiter' && primaryPartner && (
            <button className="form-button" onClick={() => setShowInterviewModal(true)}>
              Propose Interview
            </button>
          )}
        </div>

        {error && (
          <div className="error-message" style={{ marginBottom: '1rem' }}>
            {error}
          </div>
        )}

        <div className="messages-list">
          {messages.map((message) => {
            const isMine = message.sender_id === user?.id;
            return (
              <div
                key={message.id}
                className={`message-bubble ${isMine ? 'mine' : 'theirs'}`}
              >
                <div className="message-text">{message.text}</div>
                <div className="message-meta">
                  {new Date(message.created_at).toLocaleString()}
                  {message.optimistic && <span className="message-status"> (sending...)</span>}
                </div>
              </div>
            );
          })}
          <div ref={endRef} />
        </div>

        <MessageComposer onSend={onSend} disabled={sending} />
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


