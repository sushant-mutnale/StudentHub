import { useState, useRef, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { api } from '../api/client'; // Use shared API client

/**
 * VoiceInterview Component
 * Handles voice-based interviews with dual video states (asking/listening)
 */
const VoiceInterview = ({ company: companyProp, role: roleProp, onComplete }) => {
    const navigate = useNavigate();
    const [searchParams] = useSearchParams();
    // Allow props OR URL query params
    const company = companyProp || searchParams.get('company') || 'Demo Company';
    const role = roleProp || searchParams.get('role') || 'Software Engineer';
    // State management
    const [sessionId, setSessionId] = useState(null);
    const [interviewerState, setInterviewerState] = useState('idle'); // 'idle', 'asking', 'listening', 'thinking', 'completed'
    const [currentQuestion, setCurrentQuestion] = useState('');
    const [transcript, setTranscript] = useState('');
    const [isRecording, setIsRecording] = useState(false);
    const [error, setError] = useState(null);

    // Refs
    const videoRef = useRef(null);
    const audioRef = useRef(null);
    const mediaRecorderRef = useRef(null);
    const audioChunksRef = useRef([]);

    // Video sources
    const videos = {
        asking: '/interviewer/asking.mp4',
        listening: '/interviewer/listening.mp4'
    };

    /**
     * Initialize interview session
     */
    const startInterview = async () => {
        console.log('VoiceInterview: startInterview called', { company, role });
        try {
            // Logic adjusted for /api prefix handled by client or backend config
            // api client usually has base URL http://127.0.0.1:8000
            // In main.py: app.include_router(voice_routes.router, prefix="/api", tags=["voice"])
            // voice_routes.py: router = APIRouter(prefix="/voice", ...)
            // So full path is /api/voice/session/create

            console.log('VoiceInterview: Sending POST to /api/voice/session/create');
            const response = await api.post('/api/voice/session/create', {
                company,
                role,
                interview_type: 'session'
            });
            console.log('VoiceInterview: Response received', response.data);
            // Auth header handling is done by api interceptor in client.js

            const { session_id, audio_url, question_text } = response.data;

            setSessionId(session_id);
            setCurrentQuestion(question_text);
            setInterviewerState('asking');

            // Play interviewer asking question
            console.log('VoiceInterview: Playing initial audio', audio_url);
            await playInterviewerResponse(audio_url, 'asking');

        } catch (err) {
            console.error("VoiceInterview: Start Interview Error:", err);
            if (err.response) {
                console.error("VoiceInterview: Error Details:", err.response.status, err.response.data);
            }
            setError(err.response?.data?.detail || 'Failed to start interview');
        }
    };

    /**
     * Play interviewer response with appropriate video
     */
    const playInterviewerResponse = async (audioUrl, state = 'asking') => {
        return new Promise((resolve) => {
            setInterviewerState(state);

            // Switch video to asking state
            if (videoRef.current) {
                videoRef.current.src = videos[state];
                videoRef.current.loop = true;
                videoRef.current.play().catch(e => console.error("Video play error:", e));
            }

            // Play TTS audio
            if (audioRef.current) {
                // audioUrl is relative static path e.g. /static/audio/...
                // Need full URL if it's from backend
                const fullAudioUrl = audioUrl.startsWith('http') ? audioUrl : `http://127.0.0.1:8000${audioUrl}`;
                audioRef.current.src = fullAudioUrl;
                audioRef.current.play().catch(e => console.error("Audio play error:", e));

                audioRef.current.onended = () => {
                    // Stop video when audio ends
                    if (videoRef.current) {
                        videoRef.current.pause();
                        videoRef.current.currentTime = 0;
                    }

                    // Switch to listening state
                    setInterviewerState('listening');
                    if (videoRef.current) {
                        videoRef.current.src = videos.listening;
                        videoRef.current.loop = true;
                        videoRef.current.play().catch(e => console.error("Video play error:", e));
                    }

                    // Auto-start recording after question
                    setTimeout(() => startRecording(), 500);

                    resolve();
                };
            }
        });
    };

    /**
     * Start recording user's voice
     */
    const startRecording = async () => {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

            mediaRecorderRef.current = new MediaRecorder(stream);
            audioChunksRef.current = [];

            mediaRecorderRef.current.ondataavailable = (event) => {
                audioChunksRef.current.push(event.data);
            };

            mediaRecorderRef.current.onstop = async () => {
                const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/wav' });
                await submitAnswer(audioBlob);

                // Stop all tracks
                stream.getTracks().forEach(track => track.stop());
            };

            mediaRecorderRef.current.start();
            setIsRecording(true);

        } catch (err) {
            console.error("Recording Error:", err);
            setError('Microphone access denied. Please allow microphone permissions.');
        }
    };

    /**
     * Stop recording
     */
    const stopRecording = () => {
        if (mediaRecorderRef.current && isRecording) {
            mediaRecorderRef.current.stop();
            setIsRecording(false);
        }
    };

    /**
     * Submit recorded answer to backend
     */
    const submitAnswer = async (audioBlob) => {
        setInterviewerState('thinking');

        // Pause video during processing
        if (videoRef.current) {
            videoRef.current.pause();
        }

        try {
            const formData = new FormData();
            formData.append('audio_file', audioBlob, 'answer.wav');
            formData.append('session_id', sessionId);

            const response = await api.post('/api/voice/answer/submit', formData, {
                params: { session_id: sessionId },
                headers: {
                    'Content-Type': 'multipart/form-data'
                }
            });

            const { status, audio_url, question_text, transcript: userTranscript } = response.data;

            setTranscript(userTranscript);

            if (status === 'completed') {
                setInterviewerState('completed');
                await playInterviewerResponse(audio_url, 'asking');

                setTimeout(() => {
                    if (onComplete) onComplete();
                    else navigate('/dashboard/student');
                }, 2000);

            } else {
                setCurrentQuestion(question_text);
                await playInterviewerResponse(audio_url, 'asking');
            }

        } catch (err) {
            console.error("Submit Answer Error:", err);
            setError(err.response?.data?.detail || 'Failed to submit answer');
            setInterviewerState('listening');
        }
    };

    /**
     * End interview manually
     */
    const endInterview = async () => {
        try {
            await api.post(`/api/voice/session/${sessionId}/end`);
            setInterviewerState('completed');
            if (onComplete) onComplete();
            else navigate('/dashboard/student');
        } catch (err) {
            console.error("End Interview Error:", err);
            setError('Failed to end interview');
        }
    };

    return (
        <div className="voice-interview-container">
            {/* Interviewer Video */}
            <div className="interviewer-video-wrapper">
                <video
                    ref={videoRef}
                    className="interviewer-video"
                    muted
                    playsInline
                >
                    Your browser does not support video playback.
                </video>

                {/* State indicator overlay */}
                <div className={`state-indicator ${interviewerState}`}>
                    {interviewerState === 'asking' && '🎤 Asking...'}
                    {interviewerState === 'listening' && '👂 Listening...'}
                    {interviewerState === 'thinking' && '🤔 Processing...'}
                    {interviewerState === 'completed' && '✅ Completed'}
                </div>
            </div>

            {/* Hidden audio player for TTS */}
            <audio ref={audioRef} style={{ display: 'none' }} />

            {/* Current Question Display */}
            {currentQuestion && (
                <div className="question-display">
                    <h3>Current Question:</h3>
                    <p>{currentQuestion}</p>
                </div>
            )}

            {/* Transcript Display */}
            {transcript && (
                <div className="transcript-display">
                    <h4>Your answer:</h4>
                    <p>{transcript}</p>
                </div>
            )}

            {/* Controls */}
            <div className="interview-controls">
                {!sessionId ? (
                    <button onClick={startInterview} className="btn-primary">
                        Start Voice Interview
                    </button>
                ) : (
                    <>
                        {isRecording && (
                            <button onClick={stopRecording} className="btn-recording">
                                ⏹ Stop Recording
                            </button>
                        )}

                        {!isRecording && interviewerState === 'listening' && (
                            <button onClick={startRecording} className="btn-secondary">
                                🎤 Start Speaking
                            </button>
                        )}

                        {interviewerState !== 'completed' && (
                            <button onClick={endInterview} className="btn-danger">
                                End Interview
                            </button>
                        )}
                    </>
                )}
            </div>

            {/* Error Display */}
            {error && (
                <div className="error-message">
                    ⚠️ {error}
                </div>
            )}

            {/* Visual feedback */}
            <div className="status-bar">
                <div className={`status-dot ${interviewerState}`}></div>
                <span>{getStatusText(interviewerState)}</span>
            </div>
        </div>
    );
};

/**
 * Helper function to get status text
 */
const getStatusText = (state) => {
    const texts = {
        idle: 'Ready to start',
        asking: 'Interviewer is asking...',
        listening: 'Your turn to speak',
        thinking: 'Processing your answer...',
        completed: 'Interview completed!'
    };
    return texts[state] || '';
};

export default VoiceInterview;
