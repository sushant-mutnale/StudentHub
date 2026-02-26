import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { learningService } from '../services/learningService';
import SidebarLeft from './SidebarLeft';
import { FiBook, FiCheckCircle, FiCircle, FiPlay, FiAward, FiClock, FiExternalLink, FiMessageCircle, FiSend, FiLoader, FiZap, FiTarget } from 'react-icons/fi';
import '../App.css';

// Animated Progress Ring Component
const ProgressRing = ({ value, size = 60, strokeWidth = 5 }) => {
    const radius = (size - strokeWidth) / 2;
    const circumference = radius * 2 * Math.PI;
    const offset = circumference - (value / 100) * circumference;

    return (
        <svg width={size} height={size} style={{ transform: 'rotate(-90deg)' }}>
            <circle
                cx={size / 2}
                cy={size / 2}
                r={radius}
                fill="none"
                stroke="rgba(255,255,255,0.2)"
                strokeWidth={strokeWidth}
            />
            <circle
                cx={size / 2}
                cy={size / 2}
                r={radius}
                fill="none"
                stroke="white"
                strokeWidth={strokeWidth}
                strokeLinecap="round"
                strokeDasharray={circumference}
                strokeDashoffset={offset}
                style={{ transition: 'stroke-dashoffset 1s ease-out' }}
            />
        </svg>
    );
};

const LearningPath = () => {
    const navigate = useNavigate();
    const { user } = useAuth();
    const [paths, setPaths] = useState([]);
    const [activePath, setActivePath] = useState(null);
    const [loading, setLoading] = useState(true);
    const [newSkill, setNewSkill] = useState('');
    const [generating, setGenerating] = useState(false);
    const chatEndRef = useRef(null);

    useEffect(() => {
        if (!user) {
            navigate('/');
            return;
        }
        loadPaths();
    }, [user, navigate]);

    const loadPaths = async () => {
        try {
            const data = await learningService.getMyPaths();
            const list = data.learning_paths || data.paths || (Array.isArray(data) ? data : []);
            setPaths(list);
            if (list.length > 0) {
                setActivePath(list[0]);
            }
        } catch (err) {
            console.error('Failed to load paths:', err);
        } finally {
            setLoading(false);
        }
    };

    const handleGeneratePath = async () => {
        if (!newSkill.trim()) return;
        setGenerating(true);
        try {
            const newPath = await learningService.generatePath(newSkill);
            setPaths([newPath, ...paths]);
            setActivePath(newPath);
            setNewSkill('');
        } catch (err) {
            console.error('Failed to generate path:', err);
        } finally {
            setGenerating(false);
        }
    };

    const handleCompleteStage = async (stageIndex) => {
        if (!activePath) return;
        try {
            const updated = await learningService.completeStage(activePath._id || activePath.id, stageIndex);
            setActivePath(updated);
            setPaths(paths.map(p => (p._id || p.id) === (activePath._id || activePath.id) ? updated : p));
        } catch (err) {
            console.error('Failed to complete stage:', err);
        }
    };

    const getProgress = (path) => {
        if (!path?.stages) return 0;
        const completed = path.stages.filter(s => s.completed).length;
        return Math.round((completed / path.stages.length) * 100);
    };

    // Chatbot State
    const [isChatOpen, setIsChatOpen] = useState(false);
    const [chatHistory, setChatHistory] = useState([
        { role: 'assistant', content: 'Hi! I\'m your AI Mentor. Ask me anything about your learning path!' }
    ]);
    const [chatInput, setChatInput] = useState('');
    const [asking, setAsking] = useState(false);

    useEffect(() => {
        if (chatEndRef.current) {
            chatEndRef.current.scrollIntoView({ behavior: 'smooth' });
        }
    }, [chatHistory]);

    const handleAskAI = async () => {
        if (!chatInput.trim()) return;

        const userMsg = { role: 'user', content: chatInput };
        setChatHistory(prev => [...prev, userMsg]);
        setAsking(true);
        setChatInput('');

        try {
            const context = activePath ?
                `Learning Path: ${activePath.skill || activePath.name}. Structure: ${activePath.stages?.map(s => s.stage_name).join(', ')}`
                : 'General Learning';

            const res = await learningService.askCoach({
                context: context,
                question: userMsg.content
            });

            setChatHistory(prev => [...prev, { role: 'assistant', content: res.answer }]);
        } catch (err) {
            setChatHistory(prev => [...prev, { role: 'assistant', content: 'Sorry, I couldn\'t reach the server. Try again!' }]);
        } finally {
            setAsking(false);
        }
    };

    if (!user) return null;

    return (
        <div className="dashboard-container">
            <SidebarLeft />
            <div className="dashboard-main">
                <div className="dashboard-header animate-fade-in">
                    <h1 className="dashboard-title" style={{
                        background: 'var(--gradient-primary)',
                        WebkitBackgroundClip: 'text',
                        WebkitTextFillColor: 'transparent',
                        backgroundClip: 'text'
                    }}>Learning Paths</h1>
                </div>

                <div className="dashboard-content">
                    {/* Generate New Path */}
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
                            top: '-40px',
                            right: '-40px',
                            width: '150px',
                            height: '150px',
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
                                <FiZap size={18} />
                            </span>
                            Start a New Learning Path
                        </h3>

                        <div style={{ display: 'flex', gap: '1rem' }}>
                            <input
                                type="text"
                                value={newSkill}
                                onChange={(e) => setNewSkill(e.target.value)}
                                placeholder="e.g., Docker, System Design, React, Machine Learning"
                                style={{
                                    flex: 1,
                                    padding: '1rem 1.25rem',
                                    borderRadius: 'var(--radius-md)',
                                    border: '2px solid var(--color-border)',
                                    fontSize: '1rem',
                                    transition: 'var(--transition-normal)',
                                    outline: 'none'
                                }}
                                onKeyDown={(e) => e.key === 'Enter' && handleGeneratePath()}
                            />
                            <button
                                onClick={handleGeneratePath}
                                disabled={generating || !newSkill.trim()}
                                className="btn-glow"
                                style={{
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: '0.5rem',
                                    padding: '0 2rem',
                                    background: !newSkill.trim() ? 'var(--color-bg-alt)' : 'var(--gradient-primary)',
                                    color: !newSkill.trim() ? 'var(--color-text-muted)' : 'white',
                                    border: 'none',
                                    borderRadius: 'var(--radius-md)',
                                    fontSize: '1rem',
                                    fontWeight: '600',
                                    cursor: !newSkill.trim() ? 'not-allowed' : 'pointer',
                                    whiteSpace: 'nowrap',
                                    boxShadow: newSkill.trim() ? 'var(--shadow-md)' : 'none',
                                    transition: 'var(--transition-normal)'
                                }}
                            >
                                {generating ? (
                                    <>
                                        <FiLoader className="animate-spin" size={18} />
                                        Creating...
                                    </>
                                ) : (
                                    <>
                                        <FiPlay size={18} />
                                        Generate Path
                                    </>
                                )}
                            </button>
                        </div>
                    </div>

                    <div style={{ display: 'grid', gridTemplateColumns: '300px 1fr', gap: '1.5rem' }}>
                        {/* Path List */}
                        <div className="glass-card animate-fade-in-up delay-100" style={{
                            height: 'fit-content',
                            padding: '1.5rem',
                            borderRadius: 'var(--radius-lg)'
                        }}>
                            <h4 style={{
                                marginBottom: '1rem',
                                color: 'var(--color-text)',
                                display: 'flex',
                                alignItems: 'center',
                                gap: '0.5rem',
                                fontSize: '1rem'
                            }}>
                                <FiBook size={16} />
                                Your Learning Paths
                            </h4>

                            {loading ? (
                                <div style={{
                                    textAlign: 'center',
                                    padding: '2rem',
                                    color: 'var(--color-text-muted)'
                                }}>
                                    <FiLoader className="animate-spin" size={24} style={{ marginBottom: '0.5rem' }} />
                                    <p>Loading paths...</p>
                                </div>
                            ) : paths.length === 0 ? (
                                <div style={{
                                    textAlign: 'center',
                                    padding: '2rem',
                                    color: 'var(--color-text-muted)'
                                }}>
                                    <FiTarget size={32} style={{ marginBottom: '0.5rem', opacity: 0.5 }} />
                                    <p style={{ fontSize: '0.9rem' }}>No learning paths yet.<br />Create one above!</p>
                                </div>
                            ) : (
                                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                                    {paths.map((path, idx) => {
                                        const progress = getProgress(path);
                                        const isActive = activePath === path;
                                        return (
                                            <div
                                                key={path._id || path.id || idx}
                                                onClick={() => setActivePath(path)}
                                                className={`interactive-card animate-fade-in-up ${isActive ? 'animate-pulse-glow' : ''}`}
                                                style={{
                                                    padding: '1rem',
                                                    background: isActive ? 'linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%)' : 'var(--color-bg-alt)',
                                                    border: `2px solid ${isActive ? 'var(--color-primary)' : 'transparent'}`,
                                                    borderRadius: 'var(--radius-md)',
                                                    animationDelay: `${idx * 50}ms`
                                                }}
                                            >
                                                <div style={{
                                                    fontWeight: '600',
                                                    color: 'var(--color-text)',
                                                    marginBottom: '0.75rem',
                                                    display: 'flex',
                                                    alignItems: 'center',
                                                    justifyContent: 'space-between'
                                                }}>
                                                    <span>{path.skill || path.name}</span>
                                                    {progress === 100 && (
                                                        <span style={{
                                                            display: 'inline-flex',
                                                            alignItems: 'center',
                                                            justifyContent: 'center',
                                                            width: '20px',
                                                            height: '20px',
                                                            background: 'var(--gradient-success)',
                                                            borderRadius: '50%'
                                                        }}>
                                                            <FiCheckCircle size={12} color="white" />
                                                        </span>
                                                    )}
                                                </div>
                                                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                                                    <div style={{
                                                        flex: 1,
                                                        height: '6px',
                                                        background: 'var(--color-border)',
                                                        borderRadius: '3px',
                                                        overflow: 'hidden'
                                                    }}>
                                                        <div style={{
                                                            height: '100%',
                                                            width: `${progress}%`,
                                                            background: progress === 100 ? 'var(--gradient-success)' : 'var(--gradient-primary)',
                                                            borderRadius: '3px',
                                                            transition: 'width 0.5s ease'
                                                        }} />
                                                    </div>
                                                    <span style={{
                                                        fontSize: '0.75rem',
                                                        fontWeight: '600',
                                                        color: progress === 100 ? 'var(--color-success)' : 'var(--color-primary)',
                                                        minWidth: '35px'
                                                    }}>
                                                        {progress}%
                                                    </span>
                                                </div>
                                            </div>
                                        );
                                    })}
                                </div>
                            )}
                        </div>

                        {/* Active Path Details */}
                        <div className="glass-card animate-fade-in-up delay-200" style={{
                            padding: '2rem',
                            borderRadius: 'var(--radius-lg)'
                        }}>
                            {!activePath ? (
                                <div style={{
                                    textAlign: 'center',
                                    padding: '4rem 2rem',
                                    color: 'var(--color-text-muted)'
                                }}>
                                    <div style={{
                                        display: 'inline-flex',
                                        alignItems: 'center',
                                        justifyContent: 'center',
                                        width: '80px',
                                        height: '80px',
                                        background: 'var(--color-bg-alt)',
                                        borderRadius: '50%',
                                        marginBottom: '1.5rem'
                                    }}>
                                        <FiBook size={36} style={{ opacity: 0.5 }} />
                                    </div>
                                    <p style={{ fontSize: '1.1rem' }}>Select a path or create a new one to get started</p>
                                </div>
                            ) : (
                                <>
                                    {/* Path Header */}
                                    <div style={{ marginBottom: '2rem' }}>
                                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '1rem' }}>
                                            <div>
                                                <h2 style={{
                                                    color: 'var(--color-text)',
                                                    margin: 0,
                                                    fontSize: '1.5rem',
                                                    marginBottom: '0.5rem'
                                                }}>{activePath.skill || activePath.name}</h2>
                                                {activePath.description && (
                                                    <p style={{ color: 'var(--color-text-secondary)', margin: 0 }}>
                                                        {activePath.description}
                                                    </p>
                                                )}
                                            </div>
                                            <div style={{ display: 'flex', gap: '1rem', alignItems: 'center', flexShrink: 0 }}>
                                                <button
                                                    onClick={() => setIsChatOpen(!isChatOpen)}
                                                    className="btn-glow hover-lift"
                                                    style={{
                                                        display: 'flex',
                                                        alignItems: 'center',
                                                        gap: '0.5rem',
                                                        padding: '0.75rem 1.25rem',
                                                        background: isChatOpen ? 'var(--gradient-success)' : 'linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%)',
                                                        color: 'white',
                                                        border: 'none',
                                                        borderRadius: 'var(--radius-md)',
                                                        fontWeight: '600',
                                                        cursor: 'pointer',
                                                        boxShadow: 'var(--shadow-md)'
                                                    }}
                                                >
                                                    <FiMessageCircle size={16} />
                                                    {isChatOpen ? 'Close Chat' : 'Ask AI Mentor'}
                                                </button>
                                                <div style={{
                                                    display: 'flex',
                                                    alignItems: 'center',
                                                    gap: '0.75rem',
                                                    padding: '0.75rem 1.25rem',
                                                    background: 'var(--gradient-primary)',
                                                    borderRadius: 'var(--radius-full)',
                                                    color: 'white'
                                                }}>
                                                    <ProgressRing value={getProgress(activePath)} size={36} strokeWidth={3} />
                                                    <span style={{ fontWeight: '600' }}>{getProgress(activePath)}% Complete</span>
                                                </div>
                                            </div>
                                        </div>
                                    </div>

                                    {/* AI Mentor Chat */}
                                    {isChatOpen && (
                                        <div className="animate-fade-in-down" style={{
                                            marginBottom: '2rem',
                                            padding: '1.5rem',
                                            background: 'linear-gradient(135deg, rgba(139, 92, 246, 0.05) 0%, rgba(124, 58, 237, 0.05) 100%)',
                                            borderRadius: 'var(--radius-lg)',
                                            border: '1px solid rgba(139, 92, 246, 0.2)'
                                        }}>
                                            <h4 style={{
                                                marginBottom: '1rem',
                                                color: 'var(--color-text)',
                                                display: 'flex',
                                                alignItems: 'center',
                                                gap: '0.5rem'
                                            }}>
                                                <span style={{
                                                    display: 'inline-flex',
                                                    alignItems: 'center',
                                                    justifyContent: 'center',
                                                    width: '28px',
                                                    height: '28px',
                                                    background: 'linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%)',
                                                    borderRadius: 'var(--radius-sm)',
                                                    color: 'white',
                                                    fontSize: '0.9rem'
                                                }}>🤖</span>
                                                AI Learning Mentor
                                            </h4>

                                            <div style={{
                                                height: '220px',
                                                overflowY: 'auto',
                                                marginBottom: '1rem',
                                                display: 'flex',
                                                flexDirection: 'column',
                                                gap: '0.75rem',
                                                paddingRight: '0.5rem'
                                            }}>
                                                {chatHistory.map((msg, i) => (
                                                    <div
                                                        key={i}
                                                        className="animate-fade-in"
                                                        style={{
                                                            alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start',
                                                            background: msg.role === 'user'
                                                                ? 'linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)'
                                                                : 'rgba(255, 255, 255, 0.9)',
                                                            color: msg.role === 'user' ? 'white' : 'var(--color-text)',
                                                            padding: '0.75rem 1rem',
                                                            borderRadius: msg.role === 'user' ? '12px 12px 4px 12px' : '12px 12px 12px 4px',
                                                            maxWidth: '80%',
                                                            boxShadow: 'var(--shadow-sm)'
                                                        }}
                                                    >
                                                        {msg.content}
                                                    </div>
                                                ))}
                                                {asking && (
                                                    <div
                                                        className="animate-pulse"
                                                        style={{
                                                            alignSelf: 'flex-start',
                                                            background: 'rgba(255, 255, 255, 0.9)',
                                                            padding: '0.75rem 1rem',
                                                            borderRadius: '12px 12px 12px 4px',
                                                            color: 'var(--color-text-muted)'
                                                        }}
                                                    >
                                                        Thinking...
                                                    </div>
                                                )}
                                                <div ref={chatEndRef} />
                                            </div>

                                            <div style={{ display: 'flex', gap: '0.75rem' }}>
                                                <input
                                                    type="text"
                                                    value={chatInput}
                                                    onChange={e => setChatInput(e.target.value)}
                                                    onKeyDown={e => e.key === 'Enter' && handleAskAI()}
                                                    placeholder="Ask about this topic..."
                                                    style={{
                                                        flex: 1,
                                                        padding: '0.875rem 1rem',
                                                        borderRadius: 'var(--radius-md)',
                                                        border: '2px solid var(--color-border)',
                                                        outline: 'none',
                                                        transition: 'var(--transition-normal)'
                                                    }}
                                                />
                                                <button
                                                    onClick={handleAskAI}
                                                    disabled={asking || !chatInput.trim()}
                                                    className="btn-glow"
                                                    style={{
                                                        display: 'flex',
                                                        alignItems: 'center',
                                                        justifyContent: 'center',
                                                        width: '48px',
                                                        background: chatInput.trim() ? 'linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%)' : 'var(--color-bg-alt)',
                                                        color: chatInput.trim() ? 'white' : 'var(--color-text-muted)',
                                                        border: 'none',
                                                        borderRadius: 'var(--radius-md)',
                                                        cursor: chatInput.trim() ? 'pointer' : 'not-allowed'
                                                    }}
                                                >
                                                    <FiSend size={18} />
                                                </button>
                                            </div>
                                        </div>
                                    )}

                                    {/* Timeline */}
                                    <div style={{ position: 'relative' }}>
                                        {(activePath.stages || []).map((stage, idx) => {
                                            const isCompleted = stage.completed;
                                            const isLast = idx === activePath.stages.length - 1;

                                            return (
                                                <div
                                                    key={idx}
                                                    className="animate-fade-in-up"
                                                    style={{
                                                        display: 'flex',
                                                        gap: '1.5rem',
                                                        marginBottom: isLast ? 0 : '1.5rem',
                                                        position: 'relative',
                                                        animationDelay: `${idx * 100}ms`
                                                    }}
                                                >
                                                    {/* Timeline line */}
                                                    {!isLast && (
                                                        <div style={{
                                                            position: 'absolute',
                                                            left: '23px',
                                                            top: '48px',
                                                            width: '2px',
                                                            height: 'calc(100% - 8px)',
                                                            background: isCompleted ? 'var(--gradient-success)' : 'var(--color-border)',
                                                            transition: 'background 0.5s ease'
                                                        }} />
                                                    )}

                                                    {/* Status icon */}
                                                    <div
                                                        onClick={() => !isCompleted && handleCompleteStage(idx)}
                                                        className={`${isCompleted ? '' : 'hover-scale'}`}
                                                        style={{
                                                            width: '48px',
                                                            height: '48px',
                                                            borderRadius: '50%',
                                                            background: isCompleted ? 'var(--gradient-success)' : 'var(--color-bg-alt)',
                                                            border: `3px solid ${isCompleted ? 'transparent' : 'var(--color-border)'}`,
                                                            display: 'flex',
                                                            alignItems: 'center',
                                                            justifyContent: 'center',
                                                            cursor: isCompleted ? 'default' : 'pointer',
                                                            flexShrink: 0,
                                                            zIndex: 1,
                                                            boxShadow: isCompleted ? 'var(--shadow-glow-success)' : 'none',
                                                            transition: 'var(--transition-normal)'
                                                        }}
                                                    >
                                                        {isCompleted ? (
                                                            <FiCheckCircle size={22} color="white" />
                                                        ) : (
                                                            <FiCircle size={22} color="var(--color-text-muted)" />
                                                        )}
                                                    </div>

                                                    {/* Stage content */}
                                                    <div
                                                        className="interactive-card"
                                                        style={{
                                                            flex: 1,
                                                            padding: '1.5rem',
                                                            background: isCompleted
                                                                ? 'linear-gradient(135deg, rgba(16, 185, 129, 0.08) 0%, rgba(5, 150, 105, 0.08) 100%)'
                                                                : 'var(--color-bg-alt)',
                                                            borderRadius: 'var(--radius-lg)',
                                                            border: `1px solid ${isCompleted ? 'rgba(16, 185, 129, 0.2)' : 'var(--color-border-light)'}`
                                                        }}
                                                    >
                                                        <div style={{
                                                            display: 'flex',
                                                            justifyContent: 'space-between',
                                                            alignItems: 'flex-start',
                                                            marginBottom: '0.75rem',
                                                            gap: '1rem'
                                                        }}>
                                                            <h4 style={{
                                                                margin: 0,
                                                                color: 'var(--color-text)',
                                                                fontSize: '1.1rem'
                                                            }}>
                                                                {stage.title || stage.name || stage.stage_name}
                                                            </h4>
                                                            {stage.duration && (
                                                                <span style={{
                                                                    display: 'flex',
                                                                    alignItems: 'center',
                                                                    gap: '0.35rem',
                                                                    fontSize: '0.85rem',
                                                                    color: 'var(--color-text-muted)',
                                                                    padding: '0.3rem 0.75rem',
                                                                    background: 'rgba(0,0,0,0.03)',
                                                                    borderRadius: 'var(--radius-full)'
                                                                }}>
                                                                    <FiClock size={14} />
                                                                    {stage.duration}
                                                                </span>
                                                            )}
                                                        </div>

                                                        <p style={{
                                                            color: 'var(--color-text-secondary)',
                                                            fontSize: '0.9rem',
                                                            marginBottom: stage.resources?.length > 0 || !isCompleted ? '1rem' : 0,
                                                            lineHeight: '1.6'
                                                        }}>
                                                            {stage.description || stage.goal}
                                                        </p>

                                                        {/* Resources */}
                                                        {stage.resources && stage.resources.length > 0 && (
                                                            <div style={{
                                                                display: 'flex',
                                                                flexWrap: 'wrap',
                                                                gap: '0.5rem',
                                                                marginBottom: isCompleted ? 0 : '1rem'
                                                            }}>
                                                                {stage.resources.map((resource, rIdx) => (
                                                                    <a
                                                                        key={rIdx}
                                                                        href={resource.url}
                                                                        target="_blank"
                                                                        rel="noopener noreferrer"
                                                                        className="hover-lift"
                                                                        style={{
                                                                            display: 'flex',
                                                                            alignItems: 'center',
                                                                            gap: '0.375rem',
                                                                            padding: '0.5rem 0.875rem',
                                                                            background: 'linear-gradient(135deg, rgba(59, 130, 246, 0.1) 0%, rgba(37, 99, 235, 0.1) 100%)',
                                                                            color: 'var(--color-info)',
                                                                            borderRadius: 'var(--radius-full)',
                                                                            fontSize: '0.85rem',
                                                                            textDecoration: 'none',
                                                                            fontWeight: '500',
                                                                            transition: 'var(--transition-normal)'
                                                                        }}
                                                                    >
                                                                        <FiExternalLink size={14} />
                                                                        {resource.title || resource.name || 'Resource'}
                                                                    </a>
                                                                ))}
                                                            </div>
                                                        )}

                                                        {!isCompleted && (
                                                            <button
                                                                onClick={() => handleCompleteStage(idx)}
                                                                className="btn-glow hover-lift"
                                                                style={{
                                                                    display: 'flex',
                                                                    alignItems: 'center',
                                                                    gap: '0.5rem',
                                                                    padding: '0.75rem 1.5rem',
                                                                    background: 'var(--gradient-success)',
                                                                    color: 'white',
                                                                    border: 'none',
                                                                    borderRadius: 'var(--radius-md)',
                                                                    fontWeight: '600',
                                                                    cursor: 'pointer',
                                                                    boxShadow: 'var(--shadow-md)'
                                                                }}
                                                            >
                                                                <FiAward size={16} />
                                                                Mark Complete
                                                            </button>
                                                        )}
                                                    </div>
                                                </div>
                                            );
                                        })}
                                    </div>
                                </>
                            )}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default LearningPath;
