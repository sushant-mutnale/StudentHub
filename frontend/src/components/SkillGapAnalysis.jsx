import { useState, useEffect } from 'react';
import { usePersistedState } from '../hooks/usePersistedState';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { gapService } from '../services/gapService';
import { learningService } from '../services/learningService';
import { FiTarget, FiTrendingUp, FiZap, FiArrowRight, FiBook, FiAlertTriangle, FiCheckCircle, FiLoader, FiSearch, FiAward, FiClock } from 'react-icons/fi';
import '../App.css';

const SkillGapAnalysis = () => {
    const navigate = useNavigate();
    const { user } = useAuth();
    const [gaps, setGaps] = usePersistedState('gap_results', []);
    const [loading, setLoading] = useState(true);
    const [targetRole, setTargetRole] = usePersistedState('gap_targetRole', '');
    const [analyzing, setAnalyzing] = useState(false);
    const [generating, setGenerating] = useState(null);
    const [historyGroups, setHistoryGroups] = useState([]);

    useEffect(() => {
        if (!user) {
            navigate('/');
            return;
        }
        // Only fetch from network if we don't have cached gaps
        if (!gaps || gaps.length === 0) {
            loadGaps();
        } else {
            setLoading(false);
        }
    }, [user, navigate, gaps]);

    const loadGaps = async () => {
        try {
            const data = await gapService.getMyGaps();
            setGaps(data.gaps || data || []);
            loadHistory();
        } catch (err) {
            console.error('Failed to load gaps:', err);
        } finally {
            setLoading(false);
        }
    };

    const loadHistory = async () => {
        try {
            const histData = await gapService.getGapHistory();
            if (histData.history) {
                setHistoryGroups(histData.history);
            }
        } catch (err) {
            console.error('Failed to load history:', err);
        }
    };

    const handleAnalyzeRole = async () => {
        if (!targetRole.trim()) return;
        setAnalyzing(true);
        setLoading(true);
        try {
            const data = await gapService.getGapWithRecommendations(targetRole);
            setGaps(data.gaps || data || []);
            loadHistory(); // refresh history after new analysis
        } catch (err) {
            console.error('Failed to analyze:', err);
        } finally {
            setLoading(false);
            setAnalyzing(false);
        }
    };

    const handleGeneratePath = (skill) => {
        navigate('/learning', {
            state: { autoGenerateSkill: skill }
        });
    };

    const handleKeyPress = (e) => {
        if (e.key === 'Enter') {
            handleAnalyzeRole();
        }
    };

    const getPriorityStyles = (priority) => {
        switch (priority?.toUpperCase()) {
            case 'HIGH':
                return {
                    bg: 'linear-gradient(135deg, rgba(239, 68, 68, 0.08) 0%, rgba(220, 38, 38, 0.08) 100%)',
                    border: 'rgba(239, 68, 68, 0.2)',
                    text: '#dc2626',
                    badge: 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)',
                    icon: '#ef4444',
                    glow: '0 0 20px rgba(239, 68, 68, 0.2)'
                };
            case 'MEDIUM':
                return {
                    bg: 'linear-gradient(135deg, rgba(245, 158, 11, 0.08) 0%, rgba(217, 119, 6, 0.08) 100%)',
                    border: 'rgba(245, 158, 11, 0.2)',
                    text: '#d97706',
                    badge: 'linear-gradient(135deg, #f59e0b 0%, #d97706 100%)',
                    icon: '#f59e0b',
                    glow: '0 0 20px rgba(245, 158, 11, 0.2)'
                };
            case 'LOW':
                return {
                    bg: 'linear-gradient(135deg, rgba(16, 185, 129, 0.08) 0%, rgba(5, 150, 105, 0.08) 100%)',
                    border: 'rgba(16, 185, 129, 0.2)',
                    text: '#059669',
                    badge: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
                    icon: '#10b981',
                    glow: '0 0 20px rgba(16, 185, 129, 0.2)'
                };
            default:
                return {
                    bg: 'linear-gradient(135deg, rgba(100, 116, 139, 0.08) 0%, rgba(71, 85, 105, 0.08) 100%)',
                    border: 'rgba(100, 116, 139, 0.2)',
                    text: '#475569',
                    badge: 'linear-gradient(135deg, #64748b 0%, #475569 100%)',
                    icon: '#64748b',
                    glow: 'none'
                };
        }
    };

    if (!user) return null;

    return (
        <>
            
            <div className="dashboard-main">
                <div className="dashboard-header animate-fade-in">
                    <h1 className="dashboard-title" style={{
                        background: 'var(--gradient-primary)',
                        WebkitBackgroundClip: 'text',
                        WebkitTextFillColor: 'transparent',
                        backgroundClip: 'text'
                    }}>Skill Gap Analysis</h1>
                </div>

                <div className="dashboard-content">
                    {/* Target Role Input Section */}
                    <div className="glass-card animate-fade-in-up" style={{
                        marginBottom: '2rem',
                        padding: '2rem',
                        borderRadius: 'var(--radius-lg)',
                        position: 'relative',
                        overflow: 'hidden'
                    }}>
                        {/* Decorative background */}
                        <div style={{
                            position: 'absolute',
                            top: '-30px',
                            right: '-30px',
                            width: '120px',
                            height: '120px',
                            background: 'radial-gradient(circle, rgba(102, 126, 234, 0.15) 0%, transparent 70%)',
                            borderRadius: '50%'
                        }} />

                        <h3 style={{
                            marginBottom: '1.25rem',
                            color: 'var(--color-text)',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.75rem',
                            fontSize: '1.15rem'
                        }}>
                            <span style={{
                                display: 'inline-flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                width: '36px',
                                height: '36px',
                                background: 'var(--gradient-primary)',
                                borderRadius: 'var(--radius-md)',
                                color: 'white'
                            }}>
                                <FiTarget size={18} />
                            </span>
                            Target Role Analysis
                        </h3>

                        <div style={{ display: 'flex', gap: '1rem', alignItems: 'stretch' }}>
                            <div style={{ flex: 1, position: 'relative' }}>
                                <FiSearch style={{
                                    position: 'absolute',
                                    left: '1rem',
                                    top: '50%',
                                    transform: 'translateY(-50%)',
                                    color: 'var(--color-text-muted)',
                                    fontSize: '1.1rem'
                                }} />
                                <input
                                    type="text"
                                    value={targetRole}
                                    onChange={(e) => setTargetRole(e.target.value)}
                                    onKeyPress={handleKeyPress}
                                    placeholder="Enter target role (e.g., Backend Developer, Data Scientist, ML Engineer)"
                                    style={{
                                        width: '100%',
                                        padding: '1rem 1rem 1rem 3rem',
                                        borderRadius: 'var(--radius-md)',
                                        border: '2px solid var(--color-border)',
                                        fontSize: '1rem',
                                        transition: 'var(--transition-normal)',
                                        outline: 'none'
                                    }}
                                />
                            </div>
                            <button
                                onClick={handleAnalyzeRole}
                                disabled={analyzing || !targetRole.trim()}
                                className="btn-glow"
                                style={{
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '0.5rem',
                                    padding: '0 2rem',
                                    background: !targetRole.trim() ? 'var(--color-bg-alt)' : 'var(--gradient-primary)',
                                    color: !targetRole.trim() ? 'var(--color-text-muted)' : 'white',
                                    border: 'none',
                                    borderRadius: 'var(--radius-md)',
                                    fontSize: '1rem',
                                    fontWeight: '600',
                                    cursor: !targetRole.trim() ? 'not-allowed' : 'pointer',
                                    whiteSpace: 'nowrap',
                                    transition: 'var(--transition-normal)',
                                    boxShadow: targetRole.trim() ? 'var(--shadow-md)' : 'none'
                                }}
                            >
                                {analyzing ? (
                                    <>
                                        <FiLoader className="animate-spin" size={18} />
                                        Analyzing...
                                    </>
                                ) : (
                                    <>
                                        <FiZap size={18} />
                                        Analyze Gaps
                                    </>
                                )}
                            </button>
                        </div>
                    </div>

                    {/* Current Skills Section */}
                    {user.skills && user.skills.length > 0 && (
                        <div className="glass-card animate-fade-in-up delay-100" style={{
                            marginBottom: '2rem',
                            padding: '1.5rem 2rem',
                            borderRadius: 'var(--radius-lg)'
                        }}>
                            <h3 style={{
                                marginBottom: '1rem',
                                color: 'var(--color-text)',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '0.75rem',
                                fontSize: '1rem'
                            }}>
                                <span style={{
                                    display: 'inline-flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    width: '28px',
                                    height: '28px',
                                    background: 'var(--gradient-success)',
                                    borderRadius: 'var(--radius-sm)',
                                    color: 'white'
                                }}>
                                    <FiCheckCircle size={14} />
                                </span>
                                Your Current Skills
                            </h3>
                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.75rem' }}>
                                {user.skills.map((skill, idx) => (
                                    <div
                                        key={idx}
                                        className="hover-scale"
                                        style={{
                                            padding: '0.6rem 1.25rem',
                                            background: 'linear-gradient(135deg, rgba(16, 185, 129, 0.1) 0%, rgba(5, 150, 105, 0.1) 100%)',
                                            border: '1px solid rgba(16, 185, 129, 0.2)',
                                            borderRadius: 'var(--radius-full)',
                                            display: 'flex',
                                            alignItems: 'center',
                                            gap: '0.6rem',
                                            transition: 'var(--transition-normal)'
                                        }}
                                    >
                                        <span style={{ fontWeight: '600', color: 'var(--color-text)' }}>
                                            {typeof skill === 'string' ? skill : skill.name}
                                        </span>
                                        {skill.level !== undefined && (
                                            <span style={{
                                                fontSize: '0.7rem',
                                                padding: '0.15rem 0.5rem',
                                                background: 'var(--gradient-success)',
                                                color: 'white',
                                                borderRadius: 'var(--radius-full)',
                                                fontWeight: '700'
                                            }}>
                                                {skill.level}%
                                            </span>
                                        )}
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Gap Analysis Results */}
                    <div className="glass-card animate-fade-in-up delay-200" style={{
                        padding: '2rem',
                        borderRadius: 'var(--radius-lg)'
                    }}>
                        <h3 style={{
                            marginBottom: '1.5rem',
                            color: 'var(--color-text)',
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.75rem',
                            fontSize: '1.15rem'
                        }}>
                            <span style={{
                                display: 'inline-flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                width: '36px',
                                height: '36px',
                                background: 'linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)',
                                borderRadius: 'var(--radius-md)',
                                color: 'white'
                            }}>
                                <FiTrendingUp size={18} />
                            </span>
                            Skill Gaps {targetRole && <span style={{
                                fontSize: '0.9rem',
                                color: 'var(--color-text-muted)',
                                fontWeight: '400'
                            }}>for {targetRole}</span>}
                        </h3>

                        {loading ? (
                            <div style={{
                                textAlign: 'center',
                                padding: '4rem 2rem',
                                color: 'var(--color-text-muted)'
                            }}>
                                <div className="animate-pulse" style={{
                                    display: 'inline-flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    width: '80px',
                                    height: '80px',
                                    background: 'var(--gradient-primary)',
                                    borderRadius: '50%',
                                    marginBottom: '1.5rem',
                                    boxShadow: 'var(--shadow-glow)'
                                }}>
                                    <FiZap size={36} color="white" className="animate-pulse" />
                                </div>
                                <p style={{ fontSize: '1.1rem' }}>Analyzing your skill gaps against market data...</p>
                                <p style={{ fontSize: '0.9rem', marginTop: '0.5rem' }}>This may take a moment</p>
                            </div>
                        ) : gaps.length === 0 ? (
                            <div style={{
                                textAlign: 'center',
                                padding: '4rem 2rem'
                            }}>
                                <div style={{
                                    display: 'inline-flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    width: '80px',
                                    height: '80px',
                                    background: targetRole ? 'var(--gradient-success)' : 'var(--color-bg-alt)',
                                    borderRadius: '50%',
                                    marginBottom: '1.5rem',
                                    boxShadow: targetRole ? 'var(--shadow-glow-success)' : 'none'
                                }}>
                                    {targetRole ? (
                                        <FiAward size={36} color="white" />
                                    ) : (
                                        <FiTarget size={36} color="var(--color-text-muted)" />
                                    )}
                                </div>
                                <p style={{ fontSize: '1.1rem', color: 'var(--color-text-secondary)' }}>
                                    {targetRole
                                        ? '🎉 Great! You have most skills for this role.'
                                        : 'Enter a target role above to analyze skill gaps.'}
                                </p>
                            </div>
                        ) : (
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                                {gaps.map((gap, idx) => {
                                    const styles = getPriorityStyles(gap.priority);
                                    return (
                                        <div
                                            key={idx}
                                            className="interactive-card animate-fade-in-up"
                                            style={{
                                                padding: '1.5rem',
                                                background: styles.bg,
                                                border: `1px solid ${styles.border}`,
                                                borderRadius: 'var(--radius-lg)',
                                                display: 'flex',
                                                alignItems: 'center',
                                                gap: '1.5rem',
                                                animationDelay: `${idx * 80}ms`,
                                                boxShadow: gap.priority?.toUpperCase() === 'HIGH' ? styles.glow : 'none'
                                            }}
                                        >
                                            {/* Priority Icon */}
                                            <div style={{
                                                display: 'flex',
                                                alignItems: 'center',
                                                justifyContent: 'center',
                                                width: '48px',
                                                height: '48px',
                                                background: styles.badge,
                                                borderRadius: 'var(--radius-md)',
                                                color: 'white',
                                                flexShrink: 0
                                            }}>
                                                <FiAlertTriangle size={22} />
                                            </div>

                                            {/* Gap Details */}
                                            <div style={{ flex: 1, minWidth: 0 }}>
                                                <div style={{
                                                    display: 'flex',
                                                    alignItems: 'center',
                                                    gap: '0.75rem',
                                                    marginBottom: '0.5rem',
                                                    flexWrap: 'wrap'
                                                }}>
                                                    <span style={{
                                                        fontWeight: '700',
                                                        fontSize: '1.15rem',
                                                        color: 'var(--color-text)'
                                                    }}>
                                                        {gap.skill || gap.name}
                                                    </span>
                                                    <span style={{
                                                        fontSize: '0.7rem',
                                                        padding: '0.25rem 0.75rem',
                                                        background: styles.badge,
                                                        color: 'white',
                                                        borderRadius: 'var(--radius-full)',
                                                        fontWeight: '700',
                                                        textTransform: 'uppercase',
                                                        letterSpacing: '0.5px'
                                                    }}>
                                                        {gap.priority || 'MEDIUM'} PRIORITY
                                                    </span>
                                                </div>

                                                <p style={{
                                                    color: 'var(--color-text-secondary)',
                                                    fontSize: '0.9rem',
                                                    marginBottom: gap.current_level !== undefined ? '0.75rem' : 0,
                                                    lineHeight: '1.5'
                                                }}>
                                                    {gap.reason || gap.description || `Essential for ${targetRole || 'your target role'}`}
                                                </p>

                                                {gap.current_level !== undefined && (
                                                    <div style={{
                                                        display: 'flex',
                                                        alignItems: 'center',
                                                        gap: '1rem',
                                                        fontSize: '0.85rem'
                                                    }}>
                                                        <div style={{
                                                            display: 'flex',
                                                            alignItems: 'center',
                                                            gap: '0.5rem',
                                                            padding: '0.4rem 0.75rem',
                                                            background: 'rgba(0,0,0,0.05)',
                                                            borderRadius: 'var(--radius-full)'
                                                        }}>
                                                            <span style={{ color: 'var(--color-text-muted)' }}>Current:</span>
                                                            <span style={{ fontWeight: '600', color: 'var(--color-text)' }}>
                                                                {gap.current_level}%
                                                            </span>
                                                        </div>
                                                        <FiArrowRight style={{ color: 'var(--color-text-muted)' }} />
                                                        <div style={{
                                                            display: 'flex',
                                                            alignItems: 'center',
                                                            gap: '0.5rem',
                                                            padding: '0.4rem 0.75rem',
                                                            background: 'rgba(16, 185, 129, 0.1)',
                                                            borderRadius: 'var(--radius-full)'
                                                        }}>
                                                            <span style={{ color: 'var(--color-text-muted)' }}>Required:</span>
                                                            <span style={{ fontWeight: '600', color: 'var(--color-success)' }}>
                                                                {gap.required_level || gap.target_level || 70}%
                                                            </span>
                                                        </div>
                                                    </div>
                                                )}
                                            </div>

                                            {/* Action Button */}
                                            <button
                                                onClick={() => handleGeneratePath(gap.skill || gap.name)}
                                                disabled={generating === (gap.skill || gap.name)}
                                                className="btn-glow"
                                                style={{
                                                    display: 'flex',
                                                    alignItems: 'center',
                                                    gap: '0.5rem',
                                                    padding: '0.875rem 1.5rem',
                                                    background: 'var(--gradient-primary)',
                                                    color: 'white',
                                                    border: 'none',
                                                    borderRadius: 'var(--radius-md)',
                                                    fontWeight: '600',
                                                    cursor: generating === (gap.skill || gap.name) ? 'not-allowed' : 'pointer',
                                                    whiteSpace: 'nowrap',
                                                    boxShadow: 'var(--shadow-md)',
                                                    opacity: generating === (gap.skill || gap.name) ? 0.7 : 1,
                                                    transition: 'var(--transition-normal)',
                                                    flexShrink: 0
                                                }}
                                            >
                                                {generating === (gap.skill || gap.name) ? (
                                                    <>
                                                        <FiLoader className="animate-spin" size={16} />
                                                        Creating...
                                                    </>
                                                ) : (
                                                    <>
                                                        <FiBook size={16} />
                                                        Start Learning
                                                    </>
                                                )}
                                            </button>
                                        </div>
                                    );
                                })}
                            </div>
                        )}
                    </div>

                    {/* Past Analyses History */}
                    {historyGroups.length > 0 && (
                        <div className="glass-card animate-fade-in-up delay-300" style={{
                            padding: '2rem',
                            borderRadius: 'var(--radius-lg)',
                            marginTop: '2rem'
                        }}>
                            <h3 style={{
                                marginBottom: '1.5rem',
                                color: 'var(--color-text)',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '0.75rem',
                                fontSize: '1.15rem'
                            }}>
                                <span style={{
                                    display: 'inline-flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    width: '36px',
                                    height: '36px',
                                    background: 'linear-gradient(135deg, rgba(100, 116, 139, 0.15) 0%, rgba(71, 85, 105, 0.15) 100%)',
                                    borderRadius: 'var(--radius-md)',
                                    color: 'var(--color-text-secondary)'
                                }}>
                                    <FiClock size={18} />
                                </span>
                                Previous Analyses
                            </h3>
                            <div style={{ display: 'grid', gap: '1rem', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))' }}>
                                {historyGroups.map((group, idx) => {
                                    const date = new Date(group.created_at).toLocaleDateString([], { year: 'numeric', month: 'short', day: 'numeric' });
                                    const score = group.match_percentage || Math.round(group.gap_score * 100) || 0;
                                    return (
                                        <div key={idx} className="interactive-card" style={{
                                            padding: '1.25rem',
                                            background: 'var(--color-bg-alt)',
                                            border: '1px solid var(--color-border)',
                                            borderRadius: 'var(--radius-md)',
                                            cursor: 'pointer'
                                        }} onClick={() => {
                                            if (group.target_role) setTargetRole(group.target_role);
                                            setGaps(group.gaps || []);
                                            window.scrollTo({ top: 0, behavior: 'smooth' });
                                        }}>
                                            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                                                <h4 style={{ margin: 0, fontSize: '1rem', color: 'var(--color-text)' }}>
                                                    {group.target_role || group.job_id || 'General Analysis'}
                                                </h4>
                                                <span style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)' }}>
                                                    {date}
                                                </span>
                                            </div>
                                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.9rem', color: 'var(--color-text-secondary)' }}>
                                                <span>{group.gaps?.length || 0} gaps found</span>
                                                <span style={{ fontWeight: '600', color: score > 70 ? 'var(--color-success)' : score > 40 ? 'var(--color-warning)' : 'var(--color-error)' }}>
                                                    Match: {score}%
                                                </span>
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </>
    );
};

export default SkillGapAnalysis;
