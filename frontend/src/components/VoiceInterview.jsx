import { useState, useRef, useEffect, useCallback } from 'react';
import { usePersistedState } from '../hooks/usePersistedState';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { api } from '../api/client';
import './VoiceInterview.css';

// ─────────────────────────────────────────────
// Animated SVG Avatar — Alex the AI Interviewer
// ─────────────────────────────────────────────
const InterviewerAvatar = ({ state }) => {
    const isTalking = state === 'asking';
    const isThinking = state === 'thinking';
    const isListening = state === 'listening';

    return (
        <div className={`avatar-wrapper ${state}`}>
            <svg viewBox="0 0 120 120" className="avatar-svg" aria-label="AI Interviewer Alex">
                {/* Glow ring */}
                <circle cx="60" cy="60" r="57" className={`avatar-ring ${isTalking ? 'ring-talking' : isListening ? 'ring-listening' : 'ring-idle'}`} />

                {/* Head */}
                <circle cx="60" cy="58" r="40" fill="#4F46E5" className="avatar-head" />

                {/* Face highlight */}
                <ellipse cx="50" cy="46" rx="10" ry="6" fill="rgba(255,255,255,0.12)" />

                {/* Eyes */}
                <g className={`avatar-eyes ${isThinking ? 'eyes-thinking' : ''}`}>
                    <ellipse cx="48" cy="54" rx="5" ry={isTalking ? 4 : 5} fill="white" className="avatar-eye blink" />
                    <ellipse cx="72" cy="54" rx="5" ry={isTalking ? 4 : 5} fill="white" className="avatar-eye blink" />
                    {/* Pupils */}
                    <circle cx={isThinking ? 46 : 48} cy={isThinking ? 52 : 54} r="2.5" fill="#1e1b4b" />
                    <circle cx={isThinking ? 70 : 72} cy={isThinking ? 52 : 54} r="2.5" fill="#1e1b4b" />
                    {/* Eye shine */}
                    <circle cx="49.5" cy="52.5" r="1" fill="white" opacity="0.7" />
                    <circle cx="73.5" cy="52.5" r="1" fill="white" opacity="0.7" />
                </g>

                {/* Eyebrows */}
                <g opacity="0.7">
                    <path d={isThinking ? "M43 46 Q48 43 53 46" : "M43 47 Q48 44.5 53 47"} stroke="white" strokeWidth="1.8" fill="none" strokeLinecap="round" />
                    <path d={isThinking ? "M67 46 Q72 43 77 46" : "M67 47 Q72 44.5 77 47"} stroke="white" strokeWidth="1.8" fill="none" strokeLinecap="round" />
                </g>

                {/* Mouth — animated when talking */}
                <g className="avatar-mouth">
                    {isTalking ? (
                        <ellipse cx="60" cy="70" rx="8" ry="5" fill="white" opacity="0.9" className="mouth-open" />
                    ) : (
                        <path d="M52 70 Q60 75 68 70" stroke="white" strokeWidth="2" fill="none" strokeLinecap="round" />
                    )}
                </g>

                {/* Collar / shirt */}
                <ellipse cx="60" cy="110" rx="28" ry="12" fill="#312e81" />
                <polygon points="60,95 52,105 68,105" fill="#6366f1" />
                <polygon points="60,95 56,108 64,108" fill="#4F46E5" />
            </svg>

            <div className="avatar-name-badge">Alex · AI Interviewer</div>

            {/* State indicator dots */}
            {isTalking && <div className="avatar-sound-wave"><span /><span /><span /><span /><span /></div>}
            {isThinking && <div className="avatar-thinking-dots"><span /><span /><span /></div>}
            {isListening && <div className="avatar-listening-ring" />}
        </div>
    );
};

// ─────────────────────────────────────────────
// Candidate Placeholder Panel
// ─────────────────────────────────────────────
const CandidatePanel = ({ name, isMicOn, isRecording }) => (
    <div className="candidate-panel">
        <div className="candidate-avatar-placeholder">
            <svg viewBox="0 0 80 80" width="80" height="80">
                <circle cx="40" cy="30" r="20" fill="#4b5563" />
                <ellipse cx="40" cy="75" rx="30" ry="20" fill="#374151" />
            </svg>
        </div>
        <div className="candidate-name">{name || 'You'}</div>
        <div className={`candidate-mic-indicator ${isMicOn ? (isRecording ? 'mic-active' : 'mic-on') : 'mic-off'}`}>
            {isRecording ? '🔴 Speaking…' : isMicOn ? '🎤 Ready' : '🔇 Muted'}
        </div>
    </div>
);

// ─────────────────────────────────────────────
// Feedback Screen
// ─────────────────────────────────────────────
const FeedbackScreen = ({ feedback, onDone }) => {
    const rating = feedback?.overall_rating || 3;
    const stars = Math.round(rating);

    const Meter = ({ label, value, color }) => (
        <div className="feedback-meter">
            <div className="feedback-meter-label">
                <span>{label}</span>
                <span>{value}%</span>
            </div>
            <div className="feedback-meter-bar">
                <div className="feedback-meter-fill" style={{ width: `${value}%`, background: color }} />
            </div>
        </div>
    );

    return (
        <div className="feedback-screen animate-fade-in">
            <div className="feedback-header">
                <h2>🎉 Interview Complete!</h2>
                <div className="feedback-stars">
                    {'★'.repeat(stars)}{'☆'.repeat(5 - stars)}
                    <span className="feedback-rating-num">{rating.toFixed(1)} / 5.0</span>
                </div>
            </div>

            <p className="feedback-summary">{feedback?.summary}</p>

            <div className="feedback-metrics">
                <Meter label="Communication Clarity" value={feedback?.communication_clarity || 70} color="linear-gradient(90deg,#3b82f6,#6366f1)" />
                <Meter label="Technical Depth" value={feedback?.technical_depth || 65} color="linear-gradient(90deg,#8b5cf6,#d946ef)" />
                <Meter label="Confidence" value={feedback?.confidence || 72} color="linear-gradient(90deg,#10b981,#059669)" />
            </div>

            <div className="feedback-columns">
                <div className="feedback-col feedback-strengths">
                    <h4>✅ Strengths</h4>
                    <ul>{(feedback?.strengths || []).map((s, i) => <li key={i}>{s}</li>)}</ul>
                </div>
                <div className="feedback-col feedback-improvements">
                    <h4>📈 Areas to Improve</h4>
                    <ul>{(feedback?.improvements || []).map((s, i) => <li key={i}>{s}</li>)}</ul>
                </div>
            </div>

            {feedback?.suggested_answers && (
                <div className="feedback-suggested">
                    <h4>💡 Suggested Answers</h4>
                    <div className="feedback-suggested-item">
                        <strong>Best moment:</strong> {feedback.suggested_answers.best_moment}
                    </div>
                    <div className="feedback-suggested-item">
                        <strong>Improve this:</strong> {feedback.suggested_answers.improve_this}
                    </div>
                </div>
            )}

            <button className="feedback-done-btn" onClick={onDone}>
                Return to Dashboard →
            </button>
        </div>
    );
};

// ─────────────────────────────────────────────
// Main Component
// ─────────────────────────────────────────────
const MIN_QUESTIONS = 15;

const FILLER_PHRASES = [
    "Hmm, let me think about that.",
    "Got it. Interesting.",
    "Okay, I see.",
    "Right, thanks for sharing that.",
    "Mmm-hmm.",
    "I appreciate that answer.",
];

const VoiceInterview = () => {
    const navigate = useNavigate();
    const [searchParams] = useSearchParams();
    const { user } = useAuth();

    // ── Setup state ─────────────────────────────
    const [phase, setPhase] = useState('setup');  // setup | loading | room | feedback
    const [config, setConfig] = usePersistedState('voice_interview_config', {
        company: searchParams.get('company') || '',
        role: searchParams.get('role') || 'Software Engineer',
        interviewType: 'mixed',  // behavioral | technical | mixed
        difficulty: 'medium',
        resumeText: '',
        resumeLoaded: false,
    });

    // ── Interview state ──────────────────────────
    const [sessionId, setSessionId] = useState(null);
    const [interviewerState, setInterviewerState] = useState('idle');
    const [currentQuestion, setCurrentQuestion] = useState('');
    const [liveTranscript, setLiveTranscript] = useState('');
    const [isRecording, setIsRecording] = useState(false);
    const [isMicMuted, setIsMicMuted] = useState(false);
    const [questionCount, setQuestionCount] = useState(0);
    const [messages, setMessages] = useState([]);
    const [error, setError] = useState(null);
    const [feedback, setFeedback] = useState(null);
    const [loadingFeedback, setLoadingFeedback] = useState(false);

    // ── Refs ────────────────────────────────────
    const synthRef = useRef(window.speechSynthesis);
    const recognitionRef = useRef(null);
    const fillerTimerRef = useRef(null);
    const transcriptRef = useRef('');
    const chatBottomRef = useRef(null);
    // Ref-stable values — avoid stale closures in async callbacks
    const sessionIdRef = useRef(null);
    const questionCountRef = useRef(0);
    const isMicMutedRef = useRef(false);
    const runTurnRef = useRef(null);  // holds latest runTurn for recursive calls
    const isEndingRef = useRef(false); // prevent double-end

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const supported = !!SpeechRecognition && 'speechSynthesis' in window;

    // Load latest resume on mount
    useEffect(() => {
        const fetchResume = async () => {
            try {
                const { data } = await api.get('/resumes/latest');
                if (data?.extracted_text || data?.text) {
                    setConfig(c => ({ ...c, resumeText: data.extracted_text || data.text, resumeLoaded: true }));
                }
            } catch { /* no resume on file */ }
        };
        fetchResume();
    }, []);

    // Cleanup on unmount
    useEffect(() => {
        return () => {
            synthRef.current?.cancel();
            recognitionRef.current?.abort();
            clearTimeout(fillerTimerRef.current);
            clearTimeout(silenceTimerRef.current);
        };
    }, []);

    // Auto-scroll transcript
    useEffect(() => {
        chatBottomRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    // Sync isMicMuted state → ref
    useEffect(() => { isMicMutedRef.current = isMicMuted; }, [isMicMuted]);

    // ── TTS: speak text ──────────────────────────
    const speak = useCallback((text) =>
        new Promise((resolve) => {
            synthRef.current.cancel();
            const utt = new SpeechSynthesisUtterance(text);
            utt.rate = 0.92;
            utt.pitch = 1.0;
            utt.volume = 1.0;

            const voices = synthRef.current.getVoices();
            const preferred = voices.find(v => /en[-_](US|GB)/i.test(v.lang) && !v.name.includes('Google'))
                || voices.find(v => /en/i.test(v.lang));
            if (preferred) utt.voice = preferred;

            utt.onend = resolve;
            utt.onerror = resolve;
            synthRef.current.speak(utt);
        }), []);

    // ── STT: listen with 5.5s silence timeout ────────────────────────────
    const SILENCE_TIMEOUT_MS = 5500; // stop after 5.5s of sustained silence
    const silenceTimerRef = useRef(null);

    const listenOnce = useCallback(() =>
        new Promise((resolve, reject) => {
            if (!SpeechRecognition) { reject(new Error('Not supported')); return; }

            const recog = new SpeechRecognition();
            recognitionRef.current = recog;
            recog.lang = 'en-US';
            recog.interimResults = true;
            recog.maxAlternatives = 1;
            recog.continuous = true;   // ← keep listening through pauses

            setIsRecording(true);
            setLiveTranscript('Listening… speak now');
            transcriptRef.current = '';

            // Helper: reset the silence countdown each time speech is heard
            const resetSilenceTimer = () => {
                clearTimeout(silenceTimerRef.current);
                silenceTimerRef.current = setTimeout(() => {
                    // 5.5s of silence → finalize
                    recog.stop();
                }, SILENCE_TIMEOUT_MS);
            };

            recog.onstart = () => {
                // Start the initial silence timer immediately
                resetSilenceTimer();
            };

            recog.onresult = (e) => {
                let interim = '';
                for (let i = e.resultIndex; i < e.results.length; i++) {
                    if (e.results[i].isFinal) {
                        transcriptRef.current += e.results[i][0].transcript + ' ';
                    } else {
                        interim = e.results[i][0].transcript;
                    }
                }
                // Show combined final + live interim
                setLiveTranscript((transcriptRef.current + interim).trim() || 'Listening…');

                // Any speech activity resets the silence countdown
                resetSilenceTimer();
            };

            recog.onerror = (e) => {
                clearTimeout(silenceTimerRef.current);
                setIsRecording(false);
                setLiveTranscript('');
                // 'no-speech' is not fatal — it just means silence; resolve with whatever we have
                if (e.error === 'no-speech') {
                    resolve(transcriptRef.current.trim());
                } else {
                    reject(new Error(e.error));
                }
            };

            recog.onend = () => {
                clearTimeout(silenceTimerRef.current);
                setIsRecording(false);
                setLiveTranscript('');
                resolve(transcriptRef.current.trim());
            };

            recog.start();
        }), [SpeechRecognition]);


    const stopRecording = useCallback(() => {
        recognitionRef.current?.stop();
    }, []);

    // ── Filler phrase helper (does NOT cancel existing TTS) ───────────────
    const speakFiller = useCallback((phrase) => {
        // Queue a filler utterance without cancelling the current synthesis
        const utt = new SpeechSynthesisUtterance(phrase);
        utt.rate = 0.9;
        utt.pitch = 1.05;
        utt.volume = 0.85;
        const voices = synthRef.current.getVoices();
        const preferred = voices.find(v => /en[-_](US|GB)/i.test(v.lang) && !v.name.includes('Google'))
            || voices.find(v => /en/i.test(v.lang));
        if (preferred) utt.voice = preferred;
        synthRef.current.speak(utt);
    }, []);

    // ── Filler phrase when AI takes >3s ──────────
    const scheduleFillerPhrase = useCallback(() => {
        clearTimeout(fillerTimerRef.current);
        fillerTimerRef.current = setTimeout(() => {
            if (isEndingRef.current) return;
            const phrase = FILLER_PHRASES[Math.floor(Math.random() * FILLER_PHRASES.length)];
            speakFiller(phrase);
        }, 3200);  // 3.2s threshold
    }, [speakFiller]);

    const cancelFillerPhrase = useCallback(() => {
        clearTimeout(fillerTimerRef.current);
    }, []);

    // ── One conversation turn ─────────────────────
    // NOTE: stored in a ref so recursive calls always invoke the latest version
    // and async closures read current sessionId/questionCount from refs (not stale state).
    useEffect(() => {
        runTurnRef.current = async (questionText) => {
            if (isEndingRef.current) return;

            setCurrentQuestion(questionText);
            setInterviewerState('asking');
            setMessages(prev => [...prev, { role: 'interviewer', content: questionText }]);

            await speak(questionText);
            if (isEndingRef.current) return;

            if (isMicMutedRef.current) {
                setInterviewerState('listening');
                return; // user must unmute and manually retrigger
            }

            setInterviewerState('listening');
            let userAnswer = '';
            try {
                userAnswer = await listenOnce();
            } catch {
                if (!isEndingRef.current) {
                    setError('Could not capture your answer. Check microphone permissions.');
                    setInterviewerState('listening');
                }
                return;
            }

            if (!userAnswer.trim()) {
                if (!isEndingRef.current) {
                    setError('No speech detected — please speak clearly after the question.');
                    setInterviewerState('listening');
                }
                return;
            }

            setMessages(prev => [...prev, { role: 'user', content: userAnswer }]);
            setInterviewerState('thinking');

            // Schedule filler phrase if API takes >3s
            scheduleFillerPhrase();

            try {
                // Read session id and count from REFS (not stale state)
                const currentSessionId = sessionIdRef.current;
                const { data } = await api.post('/agent-interview/answer', {
                    session_id: currentSessionId,
                    answer: userAnswer,
                });

                cancelFillerPhrase();
                // synthRef.current.cancel(); // cut off any filler that started speaking - REMOVED: filler should not self-cancel

                if (isEndingRef.current) return;

                // Increment question counter via ref first, then sync to state
                questionCountRef.current += 1;
                setQuestionCount(questionCountRef.current);

                const nextQ = data.next_question;

                if (!nextQ || data.status === 'completed' || questionCountRef.current >= 25) {
                    await speak('Great job! The interview is wrapping up. Let me generate your feedback now.');
                    setInterviewerState('completed');
                    isEndingRef.current = true;
                    triggerFeedback();
                } else {
                    // Recursive call via ref — always calls the latest version
                    runTurnRef.current(nextQ);
                }
            } catch (err) {
                cancelFillerPhrase();
                if (!isEndingRef.current) {
                    setError(err.message || 'Failed to submit answer. Retrying…');
                    setInterviewerState('listening');
                }
            }
        };
    }); // No dep array: re-assign on every render so it always has fresh closures

    // ── Fetch structured feedback ─────────────────
    const triggerFeedback = useCallback(async () => {
        setLoadingFeedback(true);
        try {
            const { data } = await api.post('/agent-interview/feedback', { session_id: sessionIdRef.current });
            setFeedback(data.feedback || data);
        } catch {
            setFeedback(null);
        } finally {
            setLoadingFeedback(false);
            setPhase('feedback');
        }
    }, []);

    // ── Start session ─────────────────────────────
    const startInterview = async () => {
        setError(null);
        isEndingRef.current = false;
        sessionIdRef.current = null;
        questionCountRef.current = 0;
        setPhase('loading');

        try {
            const { data } = await api.post('/agent-interview/start', {
                company: config.company || 'Tech Company',
                role: config.role || 'Software Engineer',
                difficulty: config.difficulty,
                interview_type: config.interviewType,
                resume_text: config.resumeText || undefined,
            });

            // Store session id in REF first so runTurn can read it immediately
            sessionIdRef.current = data.session_id;
            setSessionId(data.session_id);

            questionCountRef.current = 1;
            setQuestionCount(1);
            setPhase('room');

            // Use ref-based runTurn — avoids stale closure from useCallback
            runTurnRef.current(
                data.interviewer_message || data.question || 'Hello! Welcome to your interview. Please tell me a bit about yourself.'
            );
        } catch (err) {
            setError(err.message || 'Failed to start interview');
            setPhase('setup');
        }
    };

    // ── End interview ────────────────────────────
    const endInterview = async (force = false) => {
        if (!force && questionCountRef.current < MIN_QUESTIONS) {
            const confirmed = window.confirm(
                `You've only answered ${questionCountRef.current} question${questionCountRef.current === 1 ? '' : 's'}. ` +
                `The minimum is ${MIN_QUESTIONS} for a full assessment.\n\nEnd anyway?`
            );
            if (!confirmed) return;
        }

        isEndingRef.current = true;
        synthRef.current?.cancel();
        recognitionRef.current?.abort();
        cancelFillerPhrase();

        try {
            await api.post('/agent-interview/end', { session_id: sessionIdRef.current });
        } catch { /* ignore */ }

        setInterviewerState('completed');
        await speak('Thanks for completing the interview. Generating your feedback now…');
        await triggerFeedback();
    };

    // ── Browser check ────────────────────────────
    if (!supported) {
        return (
            <div className="vi-unsupported">
                <h3>⚠️ Browser Not Supported</h3>
                <p>Voice Interview requires the Web Speech API.<br />Please use Chrome or Edge.</p>
                <button onClick={() => navigate(-1)}>← Go Back</button>
            </div>
        );
    }

    // ════════════════════════════════════════════
    // PHASE: SETUP SCREEN
    // ════════════════════════════════════════════
    if (phase === 'setup') {
        return (
            <div className="vi-setup-bg">
                <div className="vi-setup-card animate-slide-up">
                    <div className="vi-setup-title">
                        <span className="vi-setup-icon">🎙️</span>
                        <h2>AI Mock Interview</h2>
                        <p>Configure your interview session</p>
                    </div>

                    {config.resumeLoaded && (
                        <div className="vi-resume-banner">
                            ✅ Resume loaded — questions will be personalized to your background
                        </div>
                    )}

                    <div className="vi-setup-fields">
                        <div className="vi-field-group">
                            <label>Target Company</label>
                            <input
                                type="text"
                                placeholder="e.g. Google, Amazon, Startup..."
                                value={config.company}
                                onChange={e => setConfig(c => ({ ...c, company: e.target.value }))}
                                className="vi-input"
                            />
                        </div>

                        <div className="vi-field-group">
                            <label>Role</label>
                            <input
                                type="text"
                                placeholder="e.g. Software Engineer, Data Analyst..."
                                value={config.role}
                                onChange={e => setConfig(c => ({ ...c, role: e.target.value }))}
                                className="vi-input"
                            />
                        </div>

                        <div className="vi-field-group">
                            <label>Interview Type</label>
                            <div className="vi-toggle-row">
                                {[
                                    { value: 'behavioral', label: '🧠 Behavioral' },
                                    { value: 'technical', label: '💻 Technical' },
                                    { value: 'mixed', label: '⚡ Mixed' },
                                ].map(({ value, label }) => (
                                    <button
                                        key={value}
                                        className={`vi-toggle-btn ${config.interviewType === value ? 'active' : ''}`}
                                        onClick={() => setConfig(c => ({ ...c, interviewType: value }))}
                                    >{label}</button>
                                ))}
                            </div>
                        </div>

                        <div className="vi-field-group">
                            <label>Difficulty</label>
                            <div className="vi-toggle-row">
                                {['easy', 'medium', 'hard'].map(d => (
                                    <button
                                        key={d}
                                        className={`vi-toggle-btn ${config.difficulty === d ? 'active' : ''}`}
                                        onClick={() => setConfig(c => ({ ...c, difficulty: d }))}
                                    >{d}</button>
                                ))}
                            </div>
                        </div>

                        {!config.resumeLoaded && (
                            <div className="vi-field-group">
                                <label>Resume (paste text — optional)</label>
                                <textarea
                                    rows={4}
                                    placeholder="Paste your resume text to get personalized questions..."
                                    value={config.resumeText}
                                    onChange={e => setConfig(c => ({ ...c, resumeText: e.target.value }))}
                                    className="vi-input vi-textarea"
                                />
                            </div>
                        )}
                    </div>

                    {error && <div className="vi-error">{error}</div>}

                    <div className="vi-setup-info">
                        🎯 Interview ends after {MIN_QUESTIONS} questions or when you click "End Interview"
                    </div>

                    <button className="vi-start-btn" onClick={startInterview}>
                        🎙️ Start Interview
                    </button>

                    <button className="vi-back-btn" onClick={() => navigate(-1)}>← Back</button>
                </div>
            </div>
        );
    }

    // ════════════════════════════════════════════
    // PHASE: LOADING
    // ════════════════════════════════════════════
    if (phase === 'loading') {
        return (
            <div className="vi-loading-screen">
                <div className="vi-loading-spinner" />
                <h3>Setting up your interview environment…</h3>
                <p>Preparing AI interviewer for {config.company || 'your session'}</p>
            </div>
        );
    }

    // ════════════════════════════════════════════
    // PHASE: FEEDBACK
    // ════════════════════════════════════════════
    if (phase === 'feedback') {
        if (loadingFeedback) {
            return (
                <div className="vi-loading-screen">
                    <div className="vi-loading-spinner" />
                    <h3>Generating your feedback…</h3>
                    <p>Analyzing {questionCount} responses…</p>
                </div>
            );
        }
        return <FeedbackScreen feedback={feedback} onDone={() => navigate('/dashboard/student')} />;
    }

    // ════════════════════════════════════════════
    // PHASE: ROOM (Zoom-like interview room)
    // ════════════════════════════════════════════
    return (
        <div className="vi-room">
            {/* Top bar */}
            <div className="vi-room-topbar">
                <div className="vi-room-title">
                    <span className="vi-room-dot" />
                    <span>{config.company || 'AI Interview'} · {config.role}</span>
                </div>
                <div className="vi-room-qcounter">
                    Q {questionCount}/{MIN_QUESTIONS}
                </div>
            </div>

            {/* Main video grid */}
            <div className="vi-room-grid">
                {/* Left: Interviewer */}
                <div className="vi-room-panel vi-interviewer-panel">
                    <InterviewerAvatar state={interviewerState} />

                    {/* Subtitle / current question */}
                    {currentQuestion && (
                        <div className={`vi-subtitle ${interviewerState === 'asking' ? 'vi-subtitle-active' : ''}`}>
                            {currentQuestion}
                        </div>
                    )}
                </div>

                {/* Right: Candidate */}
                <div className="vi-room-panel vi-candidate-panel">
                    <CandidatePanel
                        name={user?.name || user?.email?.split('@')[0] || 'You'}
                        isMicOn={!isMicMuted}
                        isRecording={isRecording}
                    />

                    {/* Live transcript bubble */}
                    {liveTranscript && (
                        <div className="vi-live-transcript">
                            <span className="vi-live-dot" />
                            {liveTranscript}
                        </div>
                    )}
                </div>
            </div>

            {/* State indicator */}
            <div className="vi-state-banner">
                {interviewerState === 'asking' && '🔊 Alex is speaking…'}
                {interviewerState === 'listening' && '🎤 Your turn — speak now'}
                {interviewerState === 'thinking' && '⏳ Alex is thinking…'}
                {interviewerState === 'completed' && '✅ Interview complete — generating feedback…'}
            </div>

            {/* Bottom controls */}
            <div className="vi-room-controls">
                {/* Mic toggle */}
                <button
                    className={`vi-ctrl-btn ${isMicMuted ? 'vi-ctrl-muted' : ''}`}
                    onClick={() => setIsMicMuted(m => !m)}
                    title={isMicMuted ? 'Unmute mic' : 'Mute mic'}
                >
                    {isMicMuted ? '🔇' : '🎤'}
                    <span>{isMicMuted ? 'Unmuted' : 'Muted'}</span>
                </button>

                {/* Stop speaking button */}
                {isRecording && (
                    <button className="vi-ctrl-btn vi-ctrl-stop" onClick={stopRecording} title="Done speaking">
                        ⏹ <span>Done Speaking</span>
                    </button>
                )}

                {/* End interview */}
                <button
                    className="vi-ctrl-btn vi-ctrl-end"
                    onClick={() => endInterview(false)}
                    title="End interview"
                >
                    📵 <span>End Interview</span>
                </button>
            </div>

            {/* Error toast */}
            {error && (
                <div className="vi-error-toast">
                    ⚠️ {error}
                    <button onClick={() => setError(null)}>×</button>
                </div>
            )}

            {/* Conversation transcript panel (collapsible) */}
            {messages.length > 0 && (
                <details className="vi-transcript-panel">
                    <summary>📝 Conversation ({messages.length} messages)</summary>
                    <div className="vi-transcript-messages">
                        {messages.map((m, i) => (
                            <div key={i} className={`vi-msg vi-msg-${m.role}`}>
                                <span className="vi-msg-label">{m.role === 'interviewer' ? '🤖 Alex' : '👤 You'}</span>
                                <p>{m.content}</p>
                            </div>
                        ))}
                        <div ref={chatBottomRef} />
                    </div>
                </details>
            )}
        </div>
    );
};

export default VoiceInterview;
