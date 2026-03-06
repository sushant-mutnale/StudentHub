import { useState } from 'react';

const MessageComposer = ({ onSend, disabled }) => {
  const [text, setText] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = async (event) => {
    event.preventDefault();
    const trimmed = text.trim();
    if (!trimmed) {
      setError('Type a message before sending.');
      return;
    }
    try {
      await onSend(trimmed);
      setText('');
      setError('');
    } catch (err) {
      setError(err.message || 'Failed to send message.');
    }
  };

  return (
    <form className="message-composer" onSubmit={handleSubmit}>
      <textarea
        className="message-input"
        placeholder="Write a message..."
        value={text}
        disabled={disabled}
        onChange={(e) => {
          setText(e.target.value);
          setError('');
        }}
        rows={3}
      />
      {error && <div className="error-message" style={{ marginTop: '0.5rem' }}>{error}</div>}
      <div className="composer-actions">
        <button type="submit" className="form-button" disabled={disabled}>
          Send
        </button>
      </div>
    </form>
  );
};

export default MessageComposer;


