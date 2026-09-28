import React from 'react';

const EmptyState = ({ title = 'Nothing here yet', description, icon, action, compact = false }) => {
  return (
    <div
      className="empty-state"
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
          width: 56,
          height: 56,
          borderRadius: '50%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: 'rgba(102, 126, 234, 0.12)',
          color: '#667eea',
          fontSize: '1.5rem',
        }}
        aria-hidden
      >
        {icon || '📭'}
      </div>
      <p style={{ margin: 0, fontWeight: 600, fontSize: '1.05rem' }}>{title}</p>
      {description && (
        <p style={{ margin: 0, maxWidth: 420, color: 'var(--color-text-muted, #64748b)' }}>{description}</p>
      )}
      {action}
    </div>
  );
};

export default EmptyState;
