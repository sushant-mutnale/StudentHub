import { useState, useEffect, useRef } from 'react';
import { usePersistedState } from '../hooks/usePersistedState';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { learningService } from '../services/learningService';
import SidebarLeft from './SidebarLeft';
import {
    FiBook, FiCheckCircle, FiCircle, FiPlay, FiAward, FiClock,
    FiExternalLink, FiMessageCircle, FiSend, FiLoader, FiZap,
    FiTarget, FiAlertCircle, FiX, FiCheck
} from 'react-icons/fi';
import '../App.css';

// ─── Progress Ring ────────────────────────────────────────────────
const ProgressRing = ({ value, size = 60, strokeWidth = 5 }) => {
    const radius = (size - strokeWidth) / 2;
    const circumference = radius * 2 * Math.PI;
    const offset = circumference - (value / 100) * circumference;
    return (
        <svg width={size} height={size} style={{ transform: 'rotate(-90deg)' }}>
            <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke="rgba(255,255,255,0.2)" strokeWidth={strokeWidth} />
            <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke="white" strokeWidth={strokeWidth}
                strokeLinecap="round" strokeDasharray={circumference} strokeDashoffset={offset}
                style={{ transition: 'stroke-dashoffset 1s ease-out' }} />
        </svg>
    );
};

// ─── MCQ Modal ────────────────────────────────────────────────────
const MCQModal = ({ quiz, onPass, onFail, onClose }) => {
    const [answers, setAnswers] = useState(Array(5).fill(null));
    const [submitted, setSubmitted] = useState(false);
    const [result, setResult] = useState(null);
    const [submitting, setSubmitting] = useState(false);

    const handleSelect = (qIdx, optIdx) => {
        if (submitted) return;
        setAnswers(prev => { const a = [...prev]; a[qIdx] = optIdx; return a; });
    };

    const handleSubmit = async () => {
        if (answers.some(a => a === null)) {
            alert('Please answer all 5 questions before submitting.');
            return;
        }
        setSubmitting(true);
        try {
            const res = await learningService.submitMCQ(quiz.pathId, quiz.stageNumber, quiz.questions, answers);
            const evaluation = res.evaluation || res;
            setResult(evaluation);
            setSubmitted(true);
            if (evaluation.passed) {
                setTimeout(() => onPass(evaluation), 1500);
            }
        } catch (err) {
            console.error('MCQ submit failed:', err);
            setSubmitting(false);
        }
    };

    const questions = quiz.questions || [];

    return (
        <div style={{
            position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)', zIndex: 1000,
            display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '1rem'
        }}>
            <div style={{
                background: 'var(--color-bg)', borderRadius: 'var(--radius-xl)',
                padding: '2rem', maxWidth: '680px', width: '100%', maxHeight: '90vh',
                overflowY: 'auto', boxShadow: '0 25px 60px rgba(0,0,0,0.4)',
                border: '1px solid var(--color-border)'
            }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
                    <div>
                        <h2 style={{ margin: 0, color: 'var(--color-text)', fontSize: '1.3rem' }}>
                            📝 Stage Quiz
                        </h2>
                        <p style={{ margin: '0.25rem 0 0', color: 'var(--color-text-muted)', fontSize: '0.9rem' }}>
                            {quiz.stageName} — Score ≥3/5 to pass
                        </p>
                    </div>
                    {!submitted && (
                        <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--color-text-muted)' }}>
                            <FiX size={22} />
                        </button>
                    )}
                </div>

                {/* Result Banner */}
                {submitted && result && (
                    <div style={{
                        padding: '1rem 1.5rem', borderRadius: 'var(--radius-md)', marginBottom: '1.5rem',
                        background: result.passed
                            ? 'linear-gradient(135deg, rgba(16,185,129,0.15) 0%, rgba(5,150,105,0.15) 100%)'
                            : 'linear-gradient(135deg, rgba(239,68,68,0.15) 0%, rgba(220,38,38,0.15) 100%)',
                        border: `1px solid ${result.passed ? 'rgba(16,185,129,0.3)' : 'rgba(239,68,68,0.3)'}`,
                        textAlign: 'center'
                    }}>
                        <div style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>
                            {result.passed ? '🎉' : '😅'}
                        </div>
                        <div style={{
                            fontWeight: '700', fontSize: '1.1rem',
                            color: result.passed ? 'var(--color-success)' : '#ef4444'
                        }}>
                            {result.score}/5 — {result.passed ? 'Passed!' : 'Not yet'}
                        </div>
                        <p style={{ margin: '0.5rem 0 0', color: 'var(--color-text-secondary)', fontSize: '0.9rem' }}>
                            {result.message}
                        </p>
                        {!result.passed && (
                            <button onClick={onFail} style={{
                                marginTop: '1rem', padding: '0.6rem 1.5rem',
                                background: 'var(--color-bg-alt)', border: '1px solid var(--color-border)',
                                borderRadius: 'var(--radius-md)', cursor: 'pointer', color: 'var(--color-text)', fontWeight: '600'
                            }}>
                                Review Material & Try Again
                            </button>
                        )}
                    </div>
                )}

                {/* Questions */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
                    {questions.map((q, qIdx) => {
                        const feedback = submitted && result?.feedback?.[qIdx];
                        return (
                            <div key={qIdx} style={{
                                padding: '1.25rem', borderRadius: 'var(--radius-lg)',
                                background: 'var(--color-bg-alt)', border: '1px solid var(--color-border)'
                            }}>
                                <p style={{ fontWeight: '600', color: 'var(--color-text)', marginBottom: '0.875rem', lineHeight: '1.5' }}>
                                    <span style={{ color: 'var(--color-primary)', marginRight: '0.5rem' }}>Q{qIdx + 1}.</span>
                                    {q.question}
                                </p>
                                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                                    {q.options.map((opt, oIdx) => {
                                        const isSelected = answers[qIdx] === oIdx;
                                        const isCorrect = feedback && oIdx === q.correct_index;
                                        const isWrong = feedback && isSelected && !feedback.is_correct;
                                        return (
                                            <div key={oIdx}
                                                onClick={() => handleSelect(qIdx, oIdx)}
                                                style={{
                                                    padding: '0.75rem 1rem', borderRadius: 'var(--radius-md)',
                                                    cursor: submitted ? 'default' : 'pointer',
                                                    border: `2px solid ${isCorrect ? 'var(--color-success)' : isWrong ? '#ef4444' : isSelected ? 'var(--color-primary)' : 'var(--color-border)'}`,
                                                    background: isCorrect ? 'rgba(16,185,129,0.08)' : isWrong ? 'rgba(239,68,68,0.08)' : isSelected ? 'rgba(102,126,234,0.08)' : 'transparent',
                                                    color: 'var(--color-text)', fontSize: '0.9rem',
                                                    transition: 'all 0.2s',
                                                    display: 'flex', alignItems: 'center', gap: '0.75rem'
                                                }}>
                                                <span style={{
                                                    width: '22px', height: '22px', borderRadius: '50%', flexShrink: 0,
                                                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                                                    background: isCorrect ? 'var(--color-success)' : isWrong ? '#ef4444' : isSelected ? 'var(--color-primary)' : 'var(--color-border)',
                                                    color: 'white', fontSize: '0.75rem', fontWeight: '700'
                                                }}>
                                                    {isCorrect ? '✓' : isWrong ? '✗' : ['A', 'B', 'C', 'D'][oIdx]}
                                                </span>
                                                {opt}
                                            </div>
                                        );
                                    })}
                                </div>
                                {feedback && (
                                    <p style={{
                                        marginTop: '0.75rem', padding: '0.5rem 0.75rem',
                                        background: 'rgba(0,0,0,0.03)', borderRadius: 'var(--radius-sm)',
                                        fontSize: '0.85rem', color: 'var(--color-text-secondary)', fontStyle: 'italic'
                                    }}>
                                        💡 {q.explanation}
                                    </p>
                                )}
                            </div>
                        );
                    })}
                </div>

                {!submitted && (
                    <button onClick={handleSubmit} disabled={submitting || answers.some(a => a === null)}
                        className="btn-glow" style={{
                            width: '100%', marginTop: '1.5rem', padding: '1rem',
                            background: answers.some(a => a === null) ? 'var(--color-bg-alt)' : 'var(--gradient-primary)',
                            color: answers.some(a => a === null) ? 'var(--color-text-muted)' : 'white',
                            border: 'none', borderRadius: 'var(--radius-md)', fontSize: '1rem',
                            fontWeight: '700', cursor: answers.some(a => a === null) ? 'not-allowed' : 'pointer',
                            display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem'
                        }}>
                        {submitting ? <><FiLoader className="animate-spin" size={18} /> Evaluating...</> : <><FiCheck size={18} />Submit Answers</>}
                    </button>
                )}
            </div>
        </div>
    );
};

// ─── Toast ────────────────────────────────────────────────────────
const Toast = ({ message, type = 'success', onClose }) => (
    <div style={{
        position: 'fixed', bottom: '2rem', right: '2rem', zIndex: 2000,
        padding: '1rem 1.5rem', borderRadius: 'var(--radius-lg)',
        background: type === 'success' ? 'var(--gradient-success)' : 'linear-gradient(135deg,#ef4444,#dc2626)',
        color: 'white', fontWeight: '600', boxShadow: '0 8px 30px rgba(0,0,0,0.3)',
        display: 'flex', alignItems: 'center', gap: '0.75rem', maxWidth: '380px',
        animation: 'fadeIn 0.3s ease'
    }}>
        <span style={{ fontSize: '1.3rem' }}>{type === 'success' ? '🎉' : '❌'}</span>
        <span>{message}</span>
        <button onClick={onClose} style={{ background: 'none', border: 'none', color: 'white', cursor: 'pointer', marginLeft: 'auto' }}>
            <FiX size={16} />
        </button>
    </div>
);

// ─── Main Component ───────────────────────────────────────────────
const LearningPath = () => {
    const navigate = useNavigate();
    const location = useLocation();
    const { user } = useAuth();

    const [paths, setPaths] = useState([]);
    const [activePath, setActivePath] = usePersistedState('learning_activePath', null);
    const [loading, setLoading] = useState(true);
    const [newSkill, setNewSkill] = usePersistedState('learning_newSkill', '');
    const [availableTime, setAvailableTime] = usePersistedState('learning_availableTime', '4 weeks');
    const [goalLevel, setGoalLevel] = usePersistedState('learning_goalLevel', 'Job-ready');
    const [generating, setGenerating] = useState(false);
    const [normalizing, setNormalizing] = useState(false);
    const [correctedSkill, setCorrectedSkill] = useState('');

    // MCQ state
    const [mcqModal, setMcqModal] = useState(null); // { pathId, stageNumber, stageName, questions }
    const [loadingMCQ, setLoadingMCQ] = useState(null); // stage_number being loaded

    // Toast
    const [toast, setToast] = useState(null);

    // Chat
    const chatEndRef = useRef(null);
    const [isChatOpen, setIsChatOpen] = useState(false);
    const [chatHistory, setChatHistory] = useState([{ role: 'assistant', content: 'Hi! I\'m your AI Mentor. Ask me anything about your learning path!' }]);
    const [chatInput, setChatInput] = useState('');
    const [asking, setAsking] = useState(false);

    useEffect(() => { if (!user) navigate('/'); else loadPaths(); }, [user, navigate]);
    useEffect(() => { chatEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [chatHistory]);

    const showToast = (message, type = 'success') => {
        setToast({ message, type });
        setTimeout(() => setToast(null), 4500);
    };

    const loadPaths = async () => {
        try {
            const data = await learningService.getMyPaths();
            const list = data.learning_paths || data.paths || (Array.isArray(data) ? data : []);
            setPaths(list);

            // Check if we came from Skill Gap with a new path immediately created
            const newPathId = location.state?.newPathId;
            if (newPathId && list.length > 0) {
                const targetPath = list.find(p => (p._id || p.id) === newPathId);
                if (targetPath) {
                    setActivePath(targetPath);
                    // Clear state so a page refresh doesn't lock us here
                    window.history.replaceState({}, document.title);
                } else if (!activePath) {
                    setActivePath(list[0]);
                }
            } else if (list.length > 0 && (!activePath || !list.find(p => (p._id || p.id) === (activePath._id || activePath.id)))) {
                setActivePath(list[0]);
            }
        } catch (err) {
            console.error('Failed to load paths:', err);
        } finally {
            setLoading(false);
        }
    };

    // Normalize skill as user types (debounced)
    const handleSkillInput = (e) => {
        const val = e.target.value;
        setNewSkill(val);
        setCorrectedSkill('');
    };

    const handleGeneratePath = async () => {
        if (!newSkill.trim()) return;
        setGenerating(true);
        try {
            // Step 1: Normalize skill
            setNormalizing(true);
            const normalized = await learningService.normalizeSkill(newSkill.trim());
            setNormalizing(false);
            if (normalized.toLowerCase() !== newSkill.trim().toLowerCase()) {
                setCorrectedSkill(normalized);
            }

            // Step 2: Generate path with normalized skill
            const newPath = await learningService.generatePath(normalized, availableTime, goalLevel);
            setPaths(prev => [newPath, ...prev]);
            setActivePath(newPath);
            setNewSkill('');
            setCorrectedSkill('');
            showToast(`Learning path for "${normalized}" created!`);
        } catch (err) {
            console.error('Failed to generate path:', err);
            showToast('Failed to generate path. Please try again.', 'error');
        } finally {
            setGenerating(false);
            setNormalizing(false);
        }
    };

    // "Take Quiz" button clicked for a stage
    const handleTakeQuiz = async (stageIdx) => {
        if (!activePath) return;
        const stage = activePath.stages?.[stageIdx];
        if (!stage) return;

        const pathId = activePath._id || activePath.id;
        const stageNumber = stage.stage_number ?? (stageIdx + 1);

        setLoadingMCQ(stageNumber);
        try {
            const result = await learningService.generateMCQ(pathId, stageNumber);
            setMcqModal({
                pathId,
                stageNumber,
                stageName: stage.stage_name || stage.name,
                questions: result.questions
            });
        } catch (err) {
            console.error('MCQ generation failed:', err);
            showToast('Could not load quiz. Try again.', 'error');
        } finally {
            setLoadingMCQ(null);
        }
    };

    // MCQ passed — refresh path
    const handleMCQPass = async (evaluation) => {
        setMcqModal(null);
        showToast(`Stage complete! You scored ${evaluation.score}/5 🎉`);

        // Refresh the path to get updated progress
        const pathId = activePath._id || activePath.id;
        try {
            const updated = await learningService.getPath(pathId);
            setActivePath(updated);
            setPaths(prev => prev.map(p => (p._id || p.id) === pathId ? updated : p));

            // Check if path is now 100% complete
            const pct = updated.progress?.completion_percentage ?? getProgress(updated);
            if (pct >= 100) {
                await handlePathComplete(pathId);
            }
        } catch {
            loadPaths();
        }
    };

    const handlePathComplete = async (pathId) => {
        try {
            const result = await learningService.completePath(pathId);
            const update = result.profile_update;
            showToast(update?.message || '🎓 Profile updated with new skill level!');
        } catch (err) {
            console.error('Profile update failed:', err);
        }
    };

    const getProgress = (path) => {
        if (!path?.stages) return 0;
        const pct = path?.progress?.completion_percentage;
        if (pct !== undefined) return Math.round(pct);
        const completed = path.stages.filter(s => s.status === 'completed' || s.completed).length;
        return Math.round((completed / path.stages.length) * 100);
    };

    const handleAskAI = async () => {
        if (!chatInput.trim()) return;
        const userMsg = { role: 'user', content: chatInput };
        setChatHistory(prev => [...prev, userMsg]);
        setAsking(true);
        setChatInput('');
        try {
            const activeStage = activePath?.stages?.find(s => s.status !== 'completed');
            const context = activePath
                ? `Learning Path: ${activePath.skill || activePath.name}. Current Stage: ${activeStage?.stage_name || 'N/A'}. Topics: ${activeStage?.topics?.join(', ') || 'General'}`
                : 'General Learning';
            const res = await learningService.askCoach({ context, question: userMsg.content });
            setChatHistory(prev => [...prev, { role: 'assistant', content: res.answer }]);
        } catch {
            setChatHistory(prev => [...prev, { role: 'assistant', content: 'Sorry, AI Mentor is busy. Try again!' }]);
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
                        WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', backgroundClip: 'text'
                    }}>Learning Paths</h1>
                </div>

                <div className="dashboard-content">
                    {/* Generate New Path */}
                    <div className="glass-card animate-fade-in-up" style={{ marginBottom: '2rem', padding: '2rem', borderRadius: 'var(--radius-lg)', position: 'relative', overflow: 'hidden' }}>
                        <div style={{ position: 'absolute', top: '-40px', right: '-40px', width: '150px', height: '150px', background: 'radial-gradient(circle, rgba(102,126,234,0.15) 0%, transparent 70%)', borderRadius: '50%' }} />
                        <h3 style={{ marginBottom: '1.25rem', color: 'var(--color-text)', display: 'flex', alignItems: 'center', gap: '0.75rem', fontSize: '1.15rem' }}>
                            <span style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: '36px', height: '36px', background: 'var(--gradient-primary)', borderRadius: 'var(--radius-md)', color: 'white' }}>
                                <FiZap size={18} />
                            </span>
                            Start a New Learning Path
                        </h3>
                        <div style={{ display: 'flex', gap: '1rem', flexDirection: 'column' }}>
                            <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
                                <input type="text" value={newSkill} onChange={handleSkillInput}
                                    placeholder="e.g., Docker, System Design, React"
                                    style={{ flex: 1, minWidth: '200px', padding: '1rem 1.25rem', borderRadius: 'var(--radius-md)', border: '2px solid var(--color-border)', fontSize: '1rem', outline: 'none' }}
                                    onKeyDown={(e) => e.key === 'Enter' && handleGeneratePath()} />
                                <select value={availableTime} onChange={e => setAvailableTime(e.target.value)}
                                    style={{ padding: '1rem', borderRadius: 'var(--radius-md)', border: '2px solid var(--color-border)', fontSize: '1rem', outline: 'none', background: 'var(--color-bg)' }}>
                                    <option value="1 week">1 week</option>
                                    <option value="2 weeks">2 weeks</option>
                                    <option value="4 weeks">4 weeks</option>
                                    <option value="8 weeks">8 weeks</option>
                                </select>
                                <select value={goalLevel} onChange={e => setGoalLevel(e.target.value)}
                                    style={{ padding: '1rem', borderRadius: 'var(--radius-md)', border: '2px solid var(--color-border)', fontSize: '1rem', outline: 'none', background: 'var(--color-bg)' }}>
                                    <option value="Beginner">Beginner</option>
                                    <option value="Intermediate">Intermediate</option>
                                    <option value="Job-ready">Job-ready</option>
                                </select>
                                <button onClick={handleGeneratePath} disabled={generating || !newSkill.trim()} className="btn-glow"
                                    style={{
                                        display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0 2rem',
                                        background: !newSkill.trim() ? 'var(--color-bg-alt)' : 'var(--gradient-primary)',
                                        color: !newSkill.trim() ? 'var(--color-text-muted)' : 'white',
                                        border: 'none', borderRadius: 'var(--radius-md)', fontSize: '1rem', fontWeight: '600',
                                        cursor: !newSkill.trim() ? 'not-allowed' : 'pointer', whiteSpace: 'nowrap'
                                    }}>
                                    {generating ? <><FiLoader className="animate-spin" size={18} />{normalizing ? 'Correcting...' : 'Creating...'}</> : <><FiPlay size={18} />Generate Path</>}
                                </button>
                            </div>
                            {correctedSkill && (
                                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', color: 'var(--color-success)', fontSize: '0.875rem' }}>
                                    <FiCheck size={14} />
                                    Auto-corrected: <strong>"{correctedSkill}"</strong>
                                </div>
                            )}
                        </div>
                    </div>

                    <div style={{ display: 'grid', gridTemplateColumns: '300px 1fr', gap: '1.5rem' }}>
                        {/* Path List */}
                        <div className="glass-card animate-fade-in-up delay-100" style={{ height: 'fit-content', padding: '1.5rem', borderRadius: 'var(--radius-lg)' }}>
                            <h4 style={{ marginBottom: '1rem', color: 'var(--color-text)', display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '1rem' }}>
                                <FiBook size={16} /> Your Learning Paths
                            </h4>
                            {loading ? (
                                <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--color-text-muted)' }}>
                                    <FiLoader className="animate-spin" size={24} style={{ marginBottom: '0.5rem' }} />
                                    <p>Loading paths...</p>
                                </div>
                            ) : paths.length === 0 ? (
                                <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--color-text-muted)' }}>
                                    <FiTarget size={32} style={{ marginBottom: '0.5rem', opacity: 0.5 }} />
                                    <p style={{ fontSize: '0.9rem' }}>No learning paths yet.<br />Create one above!</p>
                                </div>
                            ) : (
                                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                                    {paths.map((path, idx) => {
                                        const progress = getProgress(path);
                                        const isActive = (activePath?._id || activePath?.id) === (path._id || path.id);
                                        return (
                                            <div key={path._id || path.id || idx}
                                                onClick={() => setActivePath(path)}
                                                className={`interactive-card animate-fade-in-up ${isActive ? 'animate-pulse-glow' : ''}`}
                                                style={{
                                                    padding: '1rem', animationDelay: `${idx * 50}ms`,
                                                    background: isActive ? 'linear-gradient(135deg, rgba(102,126,234,0.1) 0%, rgba(118,75,162,0.1) 100%)' : 'var(--color-bg-alt)',
                                                    border: `2px solid ${isActive ? 'var(--color-primary)' : 'transparent'}`,
                                                    borderRadius: 'var(--radius-md)'
                                                }}>
                                                <div style={{ fontWeight: '600', color: 'var(--color-text)', marginBottom: '0.75rem', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                                                    <span>{path.skill || path.name}</span>
                                                    {progress === 100 && <span style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: '20px', height: '20px', background: 'var(--gradient-success)', borderRadius: '50%' }}><FiCheckCircle size={12} color="white" /></span>}
                                                </div>
                                                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                                                    <div style={{ flex: 1, height: '6px', background: 'var(--color-border)', borderRadius: '3px', overflow: 'hidden' }}>
                                                        <div style={{ height: '100%', width: `${progress}%`, background: progress === 100 ? 'var(--gradient-success)' : 'var(--gradient-primary)', borderRadius: '3px', transition: 'width 0.5s ease' }} />
                                                    </div>
                                                    <span style={{ fontSize: '0.75rem', fontWeight: '600', color: progress === 100 ? 'var(--color-success)' : 'var(--color-primary)', minWidth: '35px' }}>{progress}%</span>
                                                </div>
                                            </div>
                                        );
                                    })}
                                </div>
                            )}
                        </div>

                        {/* Active Path Details */}
                        <div className="glass-card animate-fade-in-up delay-200" style={{ padding: '2rem', borderRadius: 'var(--radius-lg)' }}>
                            {!activePath ? (
                                <div style={{ textAlign: 'center', padding: '4rem 2rem', color: 'var(--color-text-muted)' }}>
                                    <div style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: '80px', height: '80px', background: 'var(--color-bg-alt)', borderRadius: '50%', marginBottom: '1.5rem' }}>
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
                                                <h2 style={{ color: 'var(--color-text)', margin: 0, fontSize: '1.5rem', marginBottom: '0.5rem' }}>{activePath.skill || activePath.name}</h2>
                                                {activePath.ai_advice && <p style={{ color: 'var(--color-text-secondary)', margin: 0, fontSize: '0.9rem' }}>{activePath.ai_advice}</p>}
                                                {activePath.estimated_completion_weeks > 0 && (
                                                    <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.35rem', fontSize: '0.85rem', color: 'var(--color-text-muted)', marginTop: '0.5rem' }}>
                                                        <FiClock size={14} />{activePath.estimated_completion_weeks} week{activePath.estimated_completion_weeks !== 1 ? 's' : ''} roadmap
                                                    </span>
                                                )}
                                            </div>
                                            <div style={{ display: 'flex', gap: '1rem', alignItems: 'center', flexShrink: 0 }}>
                                                <button onClick={() => setIsChatOpen(!isChatOpen)} className="btn-glow hover-lift"
                                                    style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.75rem 1.25rem', background: isChatOpen ? 'var(--gradient-success)' : 'linear-gradient(135deg,#8b5cf6 0%,#7c3aed 100%)', color: 'white', border: 'none', borderRadius: 'var(--radius-md)', fontWeight: '600', cursor: 'pointer' }}>
                                                    <FiMessageCircle size={16} />{isChatOpen ? 'Close Chat' : 'Ask AI Mentor'}
                                                </button>
                                                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', padding: '0.75rem 1.25rem', background: 'var(--gradient-primary)', borderRadius: 'var(--radius-full)', color: 'white' }}>
                                                    <ProgressRing value={getProgress(activePath)} size={36} strokeWidth={3} />
                                                    <span style={{ fontWeight: '600' }}>{getProgress(activePath)}% Complete</span>
                                                </div>
                                            </div>
                                        </div>
                                    </div>

                                    {/* AI Mentor Chat */}
                                    {isChatOpen && (
                                        <div className="animate-fade-in-down" style={{ marginBottom: '2rem', padding: '1.5rem', background: 'linear-gradient(135deg,rgba(139,92,246,0.05) 0%,rgba(124,58,237,0.05) 100%)', borderRadius: 'var(--radius-lg)', border: '1px solid rgba(139,92,246,0.2)' }}>
                                            <h4 style={{ marginBottom: '1rem', color: 'var(--color-text)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                                <span style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', width: '28px', height: '28px', background: 'linear-gradient(135deg,#8b5cf6 0%,#7c3aed 100%)', borderRadius: 'var(--radius-sm)', color: 'white', fontSize: '0.9rem' }}>🤖</span>
                                                AI Learning Mentor
                                            </h4>
                                            <div style={{ height: '220px', overflowY: 'auto', marginBottom: '1rem', display: 'flex', flexDirection: 'column', gap: '0.75rem', paddingRight: '0.5rem' }}>
                                                {chatHistory.map((msg, i) => (
                                                    <div key={i} className="animate-fade-in" style={{
                                                        alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start',
                                                        background: msg.role === 'user' ? 'linear-gradient(135deg,#3b82f6 0%,#2563eb 100%)' : 'rgba(255,255,255,0.9)',
                                                        color: msg.role === 'user' ? 'white' : 'var(--color-text)',
                                                        padding: '0.75rem 1rem', borderRadius: msg.role === 'user' ? '12px 12px 4px 12px' : '12px 12px 12px 4px',
                                                        maxWidth: '80%', boxShadow: 'var(--shadow-sm)', lineHeight: '1.5', whiteSpace: 'pre-wrap'
                                                    }}>{msg.content}</div>
                                                ))}
                                                {asking && <div className="animate-pulse" style={{ alignSelf: 'flex-start', background: 'rgba(255,255,255,0.9)', padding: '0.75rem 1rem', borderRadius: '12px 12px 12px 4px', color: 'var(--color-text-muted)' }}>Thinking...</div>}
                                                <div ref={chatEndRef} />
                                            </div>
                                            <div style={{ display: 'flex', gap: '0.75rem' }}>
                                                <input type="text" value={chatInput} onChange={e => setChatInput(e.target.value)}
                                                    onKeyDown={e => e.key === 'Enter' && handleAskAI()}
                                                    placeholder="Ask about this topic..."
                                                    style={{ flex: 1, padding: '0.875rem 1rem', borderRadius: 'var(--radius-md)', border: '2px solid var(--color-border)', outline: 'none' }} />
                                                <button onClick={handleAskAI} disabled={asking || !chatInput.trim()} className="btn-glow"
                                                    style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', width: '48px', background: chatInput.trim() ? 'linear-gradient(135deg,#8b5cf6 0%,#7c3aed 100%)' : 'var(--color-bg-alt)', color: chatInput.trim() ? 'white' : 'var(--color-text-muted)', border: 'none', borderRadius: 'var(--radius-md)', cursor: chatInput.trim() ? 'pointer' : 'not-allowed' }}>
                                                    <FiSend size={18} />
                                                </button>
                                            </div>
                                        </div>
                                    )}

                                    {/* Timeline */}
                                    <div style={{ position: 'relative' }}>
                                        {(activePath.stages || []).map((stage, idx) => {
                                            const isCompleted = stage.status === 'completed' || stage.completed;
                                            const isLast = idx === activePath.stages.length - 1;
                                            const stageNum = stage.stage_number ?? (idx + 1);
                                            const isLoadingThisQuiz = loadingMCQ === stageNum;

                                            return (
                                                <div key={idx} className="animate-fade-in-up"
                                                    style={{ display: 'flex', gap: '1.5rem', marginBottom: isLast ? 0 : '1.5rem', position: 'relative', animationDelay: `${idx * 100}ms` }}>
                                                    {!isLast && (
                                                        <div style={{ position: 'absolute', left: '23px', top: '48px', width: '2px', height: 'calc(100% - 8px)', background: isCompleted ? 'var(--gradient-success)' : 'var(--color-border)', transition: 'background 0.5s ease' }} />
                                                    )}
                                                    {/* Status icon */}
                                                    <div style={{
                                                        width: '48px', height: '48px', borderRadius: '50%',
                                                        background: isCompleted ? 'var(--gradient-success)' : 'var(--color-bg-alt)',
                                                        border: `3px solid ${isCompleted ? 'transparent' : 'var(--color-border)'}`,
                                                        display: 'flex', alignItems: 'center', justifyContent: 'center',
                                                        flexShrink: 0, zIndex: 1,
                                                        boxShadow: isCompleted ? 'var(--shadow-glow-success)' : 'none'
                                                    }}>
                                                        {isCompleted ? <FiCheckCircle size={22} color="white" /> : <FiCircle size={22} color="var(--color-text-muted)" />}
                                                    </div>

                                                    {/* Stage Card */}
                                                    <div className="interactive-card" style={{
                                                        flex: 1, padding: '1.5rem',
                                                        background: isCompleted ? 'linear-gradient(135deg,rgba(16,185,129,0.08) 0%,rgba(5,150,105,0.08) 100%)' : 'var(--color-bg-alt)',
                                                        borderRadius: 'var(--radius-lg)',
                                                        border: `1px solid ${isCompleted ? 'rgba(16,185,129,0.2)' : 'var(--color-border-light)'}`
                                                    }}>
                                                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.75rem', gap: '1rem' }}>
                                                            <h4 style={{ margin: 0, color: 'var(--color-text)', fontSize: '1.1rem' }}>
                                                                {stage.stage_name || stage.name}
                                                                {stage.mcq_score !== undefined && (
                                                                    <span style={{ marginLeft: '0.5rem', fontSize: '0.75rem', background: 'var(--gradient-success)', color: 'white', padding: '0.15rem 0.5rem', borderRadius: 'var(--radius-full)', verticalAlign: 'middle' }}>
                                                                        Quiz: {stage.mcq_score}/5
                                                                    </span>
                                                                )}
                                                            </h4>
                                                            {stage.goal && (
                                                                <span style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)', background: 'rgba(0,0,0,0.03)', padding: '0.3rem 0.75rem', borderRadius: 'var(--radius-full)', whiteSpace: 'nowrap', flexShrink: 0 }}>
                                                                    <FiClock size={12} style={{ marginRight: '0.25rem', verticalAlign: 'middle' }} />
                                                                    1 week
                                                                </span>
                                                            )}
                                                        </div>

                                                        {stage.goal && <p style={{ color: 'var(--color-text-secondary)', fontSize: '0.9rem', marginBottom: '1rem', lineHeight: '1.6' }}>{stage.goal}</p>}

                                                        {/* Topics (Legacy) */}
                                                        {stage.topics?.length > 0 && !stage.subtopics?.length && (
                                                            <div style={{ marginBottom: '1rem' }}>
                                                                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem' }}>
                                                                    {stage.topics.map((topic, ti) => (
                                                                        <span key={ti} style={{ fontSize: '0.8rem', padding: '0.25rem 0.65rem', background: 'rgba(102,126,234,0.1)', color: 'var(--color-primary)', borderRadius: 'var(--radius-full)', border: '1px solid rgba(102,126,234,0.2)' }}>{topic}</span>
                                                                    ))}
                                                                </div>
                                                            </div>
                                                        )}

                                                        {/* Subtopics */}
                                                        {stage.subtopics && stage.subtopics.length > 0 && (
                                                            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', marginBottom: '1.5rem' }}>
                                                                {stage.subtopics.map((sub, sIdx) => {
                                                                    const isSubComplete = sub.completed;
                                                                    return (
                                                                        <div key={sIdx} style={{
                                                                            padding: '1.25rem', borderRadius: 'var(--radius-md)',
                                                                            background: 'var(--color-bg)', border: `1px solid ${isSubComplete ? 'var(--color-success)' : 'var(--color-border)'}`,
                                                                            position: 'relative', overflow: 'hidden'
                                                                        }}>
                                                                            {isSubComplete && <div style={{ position: 'absolute', top: 0, left: 0, width: '4px', height: '100%', background: 'var(--color-success)' }} />}
                                                                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
                                                                                <h5 style={{ margin: 0, fontSize: '1.05rem', color: 'var(--color-text)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                                                                    {isSubComplete && <FiCheckCircle size={14} color="var(--color-success)" />}
                                                                                    {sub.title}
                                                                                </h5>
                                                                                <span style={{ fontSize: '0.8rem', color: 'var(--color-text-muted)', display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                                                                                    <FiClock size={12} /> {sub.estimated_time_minutes} min
                                                                                </span>
                                                                            </div>

                                                                            {sub.acceptance_criteria?.length > 0 && (
                                                                                <div style={{ marginBottom: '1rem' }}>
                                                                                    <p style={{ margin: '0 0 0.5rem 0', fontSize: '0.85rem', fontWeight: '600', color: 'var(--color-text-secondary)' }}>Acceptance Criteria:</p>
                                                                                    <ul style={{ margin: 0, paddingLeft: '1.5rem', fontSize: '0.9rem', color: 'var(--color-text-muted)' }}>
                                                                                        {sub.acceptance_criteria.map((crit, cIdx) => (
                                                                                            <li key={cIdx} style={{ marginBottom: '0.25rem' }}>
                                                                                                {crit}
                                                                                            </li>
                                                                                        ))}
                                                                                    </ul>
                                                                                </div>
                                                                            )}

                                                                            {sub.resources?.length > 0 && (
                                                                                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.6rem' }}>
                                                                                    {sub.resources.map((resource, rIdx) => (
                                                                                        <a key={rIdx} href={resource.url} target="_blank" rel="noopener noreferrer" className="hover-lift"
                                                                                            style={{ display: 'flex', alignItems: 'center', gap: '0.375rem', padding: '0.5rem 0.875rem', background: resource.type === 'video' ? 'linear-gradient(135deg,rgba(239,68,68,0.1) 0%,rgba(220,38,38,0.1) 100%)' : resource.type === 'documentation' ? 'linear-gradient(135deg,rgba(59,130,246,0.1) 0%,rgba(37,99,235,0.1) 100%)' : 'linear-gradient(135deg,rgba(16,185,129,0.1) 0%,rgba(5,150,105,0.1) 100%)', color: resource.type === 'video' ? '#ef4444' : resource.type === 'documentation' ? 'var(--color-info)' : 'var(--color-success)', borderRadius: 'var(--radius-full)', fontSize: '0.85rem', textDecoration: 'none', fontWeight: '500' }}>
                                                                                            {resource.type === 'video' ? '▶' : resource.type === 'documentation' ? '📖' : '💻'}
                                                                                            <FiExternalLink size={12} />
                                                                                            {resource.type.charAt(0).toUpperCase() + resource.type.slice(1)}: {resource.title?.substring(0, 30)}{resource.title?.length > 30 && '...'}
                                                                                        </a>
                                                                                    ))}
                                                                                </div>
                                                                            )}
                                                                        </div>
                                                                    );
                                                                })}
                                                            </div>
                                                        )}

                                                        {/* Resources (Legacy) */}
                                                        {stage.resources?.length > 0 && !stage.subtopics?.length && (
                                                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', marginBottom: '1rem' }}>
                                                                {stage.resources.map((resource, rIdx) => (
                                                                    <a key={rIdx} href={resource.url} target="_blank" rel="noopener noreferrer" className="hover-lift"
                                                                        style={{ display: 'flex', alignItems: 'center', gap: '0.375rem', padding: '0.5rem 0.875rem', background: resource.type === 'video' ? 'linear-gradient(135deg,rgba(239,68,68,0.1) 0%,rgba(220,38,38,0.1) 100%)' : 'linear-gradient(135deg,rgba(59,130,246,0.1) 0%,rgba(37,99,235,0.1) 100%)', color: resource.type === 'video' ? '#ef4444' : 'var(--color-info)', borderRadius: 'var(--radius-full)', fontSize: '0.85rem', textDecoration: 'none', fontWeight: '500' }}>
                                                                        {resource.type === 'video' ? '▶' : resource.type === 'documentation' ? '📖' : '🔗'}
                                                                        <FiExternalLink size={12} />
                                                                        {resource.title?.substring(0, 40) || 'Resource'}
                                                                        {resource.completed && <span style={{ fontSize: '0.7rem', color: 'var(--color-success)' }}>✓</span>}
                                                                    </a>
                                                                ))}
                                                            </div>
                                                        )}

                                                        {/* Action Button */}
                                                        {!isCompleted && (
                                                            <button onClick={() => handleTakeQuiz(idx)} disabled={isLoadingThisQuiz} className="btn-glow hover-lift"
                                                                style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.75rem 1.5rem', background: 'var(--gradient-primary)', color: 'white', border: 'none', borderRadius: 'var(--radius-md)', fontWeight: '600', cursor: isLoadingThisQuiz ? 'wait' : 'pointer', boxShadow: 'var(--shadow-md)' }}>
                                                                {isLoadingThisQuiz ? <><FiLoader className="animate-spin" size={16} />Loading Quiz...</> : <><FiAward size={16} />Take Quiz to Complete</>}
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

            {/* MCQ Modal */}
            {mcqModal && (
                <MCQModal
                    quiz={mcqModal}
                    onPass={handleMCQPass}
                    onFail={() => setMcqModal(null)}
                    onClose={() => setMcqModal(null)}
                />
            )}

            {/* Toast */}
            {toast && <Toast message={toast.message} type={toast.type} onClose={() => setToast(null)} />}
        </div>
    );
};

export default LearningPath;
