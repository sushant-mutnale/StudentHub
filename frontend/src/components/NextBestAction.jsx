import { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { nextActionService } from '../services/nextActionService';
import { Loading, ErrorState } from './ui';
import { FiZap, FiArrowRight } from 'react-icons/fi';
import '../App.css';

const ACTION_META = {
  apply_to_job: { emoji: '🎯', color: '#3b82f6', bg: 'rgba(59,130,246,0.12)' },
  complete_onboarding: { emoji: '🚀', color: '#8b5cf6', bg: 'rgba(139,92,246,0.12)' },
  close_skill_gap: { emoji: '📚', color: '#10b981', bg: 'rgba(16,185,129,0.12)' },
  add_skills: { emoji: '✍️', color: '#f59e0b', bg: 'rgba(245,158,11,0.12)' },
  explore: { emoji: '🧭', color: '#6366f1', bg: 'rgba(99,102,241,0.12)' },
  none: { emoji: '⭐', color: '#64748b', bg: 'rgba(100,116,139,0.12)' },
};

const NextBestAction = ({ compact = false }) => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    if (!user) return;
    setLoading(true);
    setError(null);
    try {
      const res = await nextActionService.getNextBestAction();
      setData(res);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [user]);

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user]);

  if (loading) {
    return compact ? <Loading label="Finding your next step..." size="sm" /> : <Loading label="Finding your next step..." />;
  }

  if (error) {
    return <ErrorState message={error} onRetry={load} compact />;
  }

  if (!data?.action) return null;

  const action = data.action;
  const meta = ACTION_META[action.type] || ACTION_META.none;

  return (
    <div className="interactive-card animate-fade-in-up" style={{
      padding: '1.5rem',
      background: 'white',
      borderRadius: '16px',
      border: '1px solid #e2e8f0',
      display: 'flex',
      gap: '1rem',
      alignItems: 'flex-start',
    }}>
      <div style={{
        width: 52, height: 52, borderRadius: '14px', flexShrink: 0,
        background: meta.bg, color: meta.color,
        display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '1.5rem'
      }} aria-hidden>
        {meta.emoji}
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.25rem' }}>
          <span style={{
            display: 'inline-flex', alignItems: 'center', gap: '0.35rem',
            fontSize: '0.7rem', fontWeight: 700, textTransform: 'uppercase',
            letterSpacing: '0.05em', color: meta.color,
            background: meta.bg, padding: '0.2rem 0.6rem', borderRadius: '9999px'
          }}>
            <FiZap size={11} /> Next best action
          </span>
          <span style={{
            display: 'inline-flex', alignItems: 'center',
            padding: '0.2rem 0.6rem', borderRadius: '9999px',
            fontSize: '0.7rem', fontWeight: 600, textTransform: 'uppercase',
            background: action.priority === 'high' ? '#fee2e2' : '#f1f5f9',
            color: action.priority === 'high' ? '#dc2626' : '#64748b'
          }}>
            {action.priority}
          </span>
        </div>
        <h3 style={{ margin: '0.25rem 0', color: '#1e293b', fontSize: '1.1rem' }}>{action.title}</h3>
        <p style={{ margin: '0 0 1rem', color: '#64748b', fontSize: '0.9rem', lineHeight: '1.5' }}>
          {action.description}
        </p>
        <button
          onClick={() => navigate(action.target?.url || '/')}
          className="form-button hover-scale"
          style={{ margin: 0, display: 'inline-flex', alignItems: 'center', gap: '0.5rem' }}
        >
          {action.cta} <FiArrowRight />
        </button>
      </div>
    </div>
  );
};

export default NextBestAction;
