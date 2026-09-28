import React from 'react';

const ErrorState = ({ message = 'Something went wrong', onRetry, retryLabel = 'Try again', compact = false }) => {
  return (
    <div
      className="error-state"
      role="alert"
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: '0.75rem',
        padding: compact ? '1.5rem 1rem' : '3rem 1rem',
        textAlign: 'center',
        color: 'var(--color-text, #0f172a)',
      }}
    >
      <div
        style={{
          width: 44,
          height: 44,
          borderRadius: '50%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: 'rgba(239, 68, 68, 0.12)',
          color: '#ef4444',
          fontSize: '1.25rem',
          fontWeight: 700,
        }}
        aria-hidden
      >
        !
      </div>
      <p style={{ margin: 0, color: '#ef4444', fontWeight: 600 }}>Error</p>
      <p style={{ margin: 0, maxWidth: 420, color: 'var(--color-text-muted, #64748b)' }}>{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          style={{
            marginTop: '0.5rem',
            padding: '0.5rem 1.25rem',
            borderRadius: '8px',
            border: 'none',
            background: 'var(--gradient-primary, linear-gradient(135deg,#667eea,#764ba2))',
            color: '#fff',
            cursor: 'pointer',
            fontSize: '0.9rem',
          }}
        >
          {retryLabel}
        </button>
      )}
    </div>
  );
};

export default ErrorState;
