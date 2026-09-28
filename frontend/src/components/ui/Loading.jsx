import React from 'react';

const Loading = ({ label = 'Loading...', size = 'md', full = false }) => {
  const sizeMap = {
    sm: 20,
    md: 32,
    lg: 48,
  };

  return (
    <div
      className="loading-state"
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: '0.75rem',
        padding: full ? '0' : '2.5rem 1rem',
        width: '100%',
        minHeight: full ? '100%' : 'auto',
        color: 'var(--color-text-muted, #64748b)',
      }}
    >
      <div
        className="loading-spinner"
        role="status"
        aria-label={label}
        style={{
          width: sizeMap[size] ?? 32,
          height: sizeMap[size] ?? 32,
          border: `3px solid rgba(102, 126, 234, 0.25)`,
          borderTopColor: '#667eea',
          borderRadius: '50%',
          animation: 'spinner-rotate 0.8s linear infinite',
        }}
      />
      <span className="loading-label" style={{ fontSize: '0.9rem' }}>
        {label}
      </span>
      <style>{`
        @keyframes spinner-rotate {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
};

export default Loading;
