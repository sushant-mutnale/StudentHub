import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { resumeService } from '../services/resumeService';
import { gapService } from '../services/gapService';
import { learningService } from '../services/learningService';
import { FiUploadCloud, FiTarget, FiBookOpen, FiCheckCircle, FiArrowRight, FiArrowLeft, FiSkipForward } from 'react-icons/fi';
import '../App.css';

const STEPS = [
  { key: 'resume', label: 'Upload Resume', icon: FiUploadCloud },
  { key: 'gaps', label: 'Analyze Skill Gaps', icon: FiTarget },
  { key: 'learn', label: 'Start Learning', icon: FiBookOpen },
];

const TARGET_ROLES = [
  'Frontend Developer',
  'Backend Developer',
  'Full Stack Developer',
  'Data Scientist',
  'ML Engineer',
  'DevOps Engineer',
  'Mobile Developer',
  'Cloud Engineer',
  'Software Engineer',
  'Product Manager',
];

export default function OnboardingWizard() {
  const navigate = useNavigate();
  const { updateUser, user } = useAuth();
  const [step, setStep] = useState(0);
  const [completedSteps, setCompletedSteps] = useState(new Set());
  const [resumeResult, setResumeResult] = useState(null);
  const [gapResults, setGapResults] = useState(null);
  const [selectedRole, setSelectedRole] = useState('');
  const [learningPath, setLearningPath] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [generatingPath, setGeneratingPath] = useState(false);
  const [error, setError] = useState('');

  const canProceed = () => {
    if (step === 0) return !!resumeResult;
    if (step === 1) return !!gapResults;
    if (step === 2) return !!learningPath;
    return false;
  };

  // Step 1: Upload Resume
  const handleResumeUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setUploading(true);
    setError('');
    try {
      const result = await resumeService.uploadResume(file);
      setResumeResult(result);
      setCompletedSteps(prev => new Set([...prev, 0]));
    } catch (err) {
      setError(err.message || 'Failed to upload resume. Please try again.');
    } finally {
      setUploading(false);
    }
  };

  // Step 2: Analyze skill gaps
  const handleAnalyzeGaps = async () => {
    if (!selectedRole) return;
    setAnalyzing(true);
    setError('');
    try {
      const result = await gapService.getGapWithRecommendations(selectedRole);
      setGapResults(result);
      setCompletedSteps(prev => new Set([...prev, 1]));
    } catch (err) {
      setError(err.message || 'Failed to analyze skill gaps. Please try again.');
    } finally {
      setAnalyzing(false);
    }
  };

  // Step 3: Generate and start learning path
  const handleStartLearning = async () => {
    setGeneratingPath(true);
    setError('');
    try {
      const result = await learningService.generatePath(selectedRole);
      setLearningPath(result);
      setCompletedSteps(prev => new Set([...prev, 2]));
    } catch (err) {
      setError(err.message || 'Failed to generate learning path. Please try again.');
    } finally {
      setGeneratingPath(false);
    }
  };

  // Mark onboarding complete and go to dashboard
  const handleFinish = async () => {
    await updateUser({ onboarding_completed: true });
    navigate('/dashboard/student');
  };

  // Skip onboarding
  const handleSkip = async () => {
    await updateUser({ onboarding_completed: true });
    navigate('/dashboard/student');
  };

  const renderStep = () => {
    switch (step) {
      case 0:
        return (
          <div style={{ textAlign: 'center', padding: '2rem 0' }}>
            <FiUploadCloud size={48} style={{ color: 'var(--color-primary)', marginBottom: '1rem' }} />
            <h3 style={{ color: 'var(--color-text)', marginBottom: '0.5rem' }}>
              Upload Your Resume
            </h3>
            <p style={{ color: 'var(--color-text-secondary)', marginBottom: '1.5rem', fontSize: '0.9rem' }}>
              We'll parse your resume to identify your skills and experience.
            </p>
            {resumeResult ? (
              <div style={{
                padding: '1rem',
                borderRadius: 'var(--radius-md)',
                background: 'rgba(16, 185, 129, 0.1)',
                border: '1px solid rgba(16, 185, 129, 0.3)',
                color: 'var(--color-success)',
                display: 'flex', alignItems: 'center', gap: '0.5rem', justifyContent: 'center'
              }}>
                <FiCheckCircle /> Resume uploaded successfully
              </div>
            ) : (
              <label style={{
                display: 'inline-flex', alignItems: 'center', gap: '0.5rem',
                padding: '0.75rem 1.5rem', borderRadius: 'var(--radius-md)',
                background: 'var(--gradient-primary)', color: '#fff',
                cursor: uploading ? 'wait' : 'pointer',
                fontSize: '0.9rem', fontWeight: 600,
                opacity: uploading ? 0.7 : 1,
              }}>
                <FiUploadCloud />
                {uploading ? 'Uploading...' : 'Choose PDF Resume'}
                <input type="file" accept=".pdf" onChange={handleResumeUpload} style={{ display: 'none' }} disabled={uploading} />
              </label>
            )}
          </div>
        );
      case 1:
        return (
          <div style={{ textAlign: 'center', padding: '2rem 0' }}>
            <FiTarget size={48} style={{ color: 'var(--color-info)', marginBottom: '1rem' }} />
            <h3 style={{ color: 'var(--color-text)', marginBottom: '0.5rem' }}>
              Analyze Skill Gaps
            </h3>
            <p style={{ color: 'var(--color-text-secondary)', marginBottom: '1.5rem', fontSize: '0.9rem' }}>
              Select your target role to identify what skills you need to develop.
            </p>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', justifyContent: 'center', marginBottom: '1.5rem' }}>
              {TARGET_ROLES.map(role => (
                <button
                  key={role}
                  onClick={() => setSelectedRole(role)}
                  style={{
                    padding: '0.5rem 1rem',
                    borderRadius: 'var(--radius-full)',
                    border: `2px solid ${selectedRole === role ? 'var(--color-primary)' : 'var(--color-border)'}`,
                    background: selectedRole === role ? 'rgba(102, 126, 234, 0.15)' : 'var(--color-surface)',
                    color: selectedRole === role ? 'var(--color-primary)' : 'var(--color-text-secondary)',
                    cursor: 'pointer', fontSize: '0.85rem', fontWeight: selectedRole === role ? 600 : 400,
                    transition: 'all 0.2s',
                  }}
                >
                  {role}
                </button>
              ))}
            </div>
            {selectedRole && !gapResults && (
              <button
                onClick={handleAnalyzeGaps}
                disabled={analyzing}
                style={{
                  padding: '0.75rem 1.5rem', borderRadius: 'var(--radius-md)',
                  background: 'var(--gradient-primary)', color: '#fff',
                  border: 'none', cursor: analyzing ? 'wait' : 'pointer',
                  fontWeight: 600, fontSize: '0.9rem',
                  opacity: analyzing ? 0.7 : 1,
                }}
              >
                {analyzing ? 'Analyzing...' : 'Analyze Gaps'}
              </button>
            )}
            {gapResults && (
              <div style={{
                padding: '1rem', borderRadius: 'var(--radius-md)',
                background: 'rgba(16, 185, 129, 0.1)', border: '1px solid rgba(16, 185, 129, 0.3)',
                color: 'var(--color-success)',
              }}>
                <FiCheckCircle style={{ marginRight: '0.5rem' }} />
                Skill gap analysis complete — {gapResults.missing_skills?.length || 0} skills identified
              </div>
            )}
          </div>
        );
      case 2:
        return (
          <div style={{ textAlign: 'center', padding: '2rem 0' }}>
            <FiBookOpen size={48} style={{ color: 'var(--color-success)', marginBottom: '1rem' }} />
            <h3 style={{ color: 'var(--color-text)', marginBottom: '0.5rem' }}>
              Start Your Learning Path
            </h3>
            <p style={{ color: 'var(--color-text-secondary)', marginBottom: '1.5rem', fontSize: '0.9rem' }}>
              We'll generate a personalized learning plan based on your skill gaps.
            </p>
            {learningPath ? (
              <div style={{
                padding: '1rem', borderRadius: 'var(--radius-md)',
                background: 'rgba(16, 185, 129, 0.1)', border: '1px solid rgba(16, 185, 129, 0.3)',
                color: 'var(--color-success)', marginBottom: '1rem',
              }}>
                <FiCheckCircle style={{ marginRight: '0.5rem' }} />
                Learning path created — {learningPath.modules?.length || 0} modules ready
              </div>
            ) : (
              <button
                onClick={handleStartLearning}
                disabled={generatingPath}
                style={{
                  padding: '0.75rem 1.5rem', borderRadius: 'var(--radius-md)',
                  background: 'var(--gradient-success)', color: '#fff',
                  border: 'none', cursor: generatingPath ? 'wait' : 'pointer',
                  fontWeight: 600, fontSize: '0.9rem',
                  opacity: generatingPath ? 0.7 : 1,
                }}
              >
                {generatingPath ? 'Generating...' : 'Generate Learning Path'}
              </button>
            )}
          </div>
        );
      default:
        return null;
    }
  };

  return (
    <div className="dashboard-main" style={{ minHeight: '100vh' }}>
      <div className="dashboard-header animate-fade-in" style={{ borderBottom: '1px solid var(--color-border)' }}>
        <h1 className="dashboard-title" style={{ marginBottom: 0 }}>Welcome to StudentHub</h1>
      </div>
      <div className="dashboard-content" style={{ maxWidth: '640px', margin: '0 auto', padding: '2rem' }}>

        {/* Skip button */}
        <div style={{ textAlign: 'right', marginBottom: '1rem' }}>
          <button
            onClick={handleSkip}
            style={{
              background: 'none', border: 'none', color: 'var(--color-text-muted)',
              cursor: 'pointer', fontSize: '0.85rem', display: 'flex', alignItems: 'center',
              gap: '0.3rem', marginLeft: 'auto',
            }}
          >
            Skip for now <FiSkipForward />
          </button>
        </div>

        {/* Progress bar */}
        <div className="step-progress" style={{ marginBottom: '2rem' }}>
          <div className="progress-bar" style={{ height: '4px', background: 'var(--color-border)', borderRadius: 'var(--radius-full)' }}>
            <div
              className="progress-fill"
              style={{
                height: '100%',
                width: `${((step + 1) / STEPS.length) * 100}%`,
                background: 'var(--gradient-primary)',
                borderRadius: 'var(--radius-full)',
                transition: 'width 0.3s ease',
              }}
            />
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '0.75rem' }}>
            {STEPS.map((s, i) => {
              const Icon = s.icon;
              return (
                <div
                  key={s.key}
                  onClick={() => { if (completedSteps.has(i) || i <= step) setStep(i); }}
                  style={{
                    display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '0.3rem',
                    cursor: completedSteps.has(i) || i <= step ? 'pointer' : 'default',
                    opacity: i <= step ? 1 : 0.5,
                    transition: 'opacity 0.2s',
                  }}
                >
                  <div style={{
                    width: '36px', height: '36px', borderRadius: '50%',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    background: completedSteps.has(i) ? 'var(--color-success)' : i === step ? 'var(--color-primary)' : 'var(--color-surface)',
                    color: i <= step ? '#fff' : 'var(--color-text-muted)',
                    border: `2px solid ${i === step ? 'var(--color-primary)' : 'var(--color-border)'}`,
                    transition: 'all 0.2s',
                  }}>
                    {completedSteps.has(i) ? <FiCheckCircle size={18} /> : <Icon size={16} />}
                  </div>
                  <span style={{ fontSize: '0.75rem', color: 'var(--color-text-secondary)' }}>{s.label}</span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Error */}
        {error && (
          <div style={{
            padding: '0.75rem 1rem', borderRadius: 'var(--radius-md)',
            background: 'rgba(239, 68, 68, 0.1)', border: '1px solid rgba(239, 68, 68, 0.3)',
            color: 'var(--color-danger)', marginBottom: '1.5rem', fontSize: '0.9rem',
          }}>
            {error}
          </div>
        )}

        {/* Step content */}
        {renderStep()}

        {/* Navigation */}
        <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '2rem' }}>
          <button
            onClick={() => setStep(s => Math.max(0, s - 1))}
            disabled={step === 0}
            style={{
              padding: '0.75rem 1.25rem', borderRadius: 'var(--radius-md)',
              background: 'var(--color-surface)', color: 'var(--color-text-secondary)',
              border: '1px solid var(--color-border)', cursor: step === 0 ? 'default' : 'pointer',
              display: 'flex', alignItems: 'center', gap: '0.3rem',
              opacity: step === 0 ? 0.4 : 1, fontWeight: 500,
            }}
          >
            <FiArrowLeft /> Back
          </button>

          {step === STEPS.length - 1 && completedSteps.has(2) ? (
            <button
              onClick={handleFinish}
              style={{
                padding: '0.75rem 1.5rem', borderRadius: 'var(--radius-md)',
                background: 'var(--gradient-success)', color: '#fff',
                border: 'none', cursor: 'pointer', fontWeight: 600,
                display: 'flex', alignItems: 'center', gap: '0.3rem',
              }}
            >
              Go to Dashboard <FiArrowRight />
            </button>
          ) : (
            <button
              onClick={() => setStep(s => Math.min(STEPS.length - 1, s + 1))}
              disabled={!canProceed()}
              style={{
                padding: '0.75rem 1.5rem', borderRadius: 'var(--radius-md)',
                background: canProceed() ? 'var(--gradient-primary)' : 'var(--color-surface)',
                color: canProceed() ? '#fff' : 'var(--color-text-muted)',
                border: canProceed() ? 'none' : '1px solid var(--color-border)',
                cursor: canProceed() ? 'pointer' : 'default',
                display: 'flex', alignItems: 'center', gap: '0.3rem',
                fontWeight: 600,
              }}
            >
              Next <FiArrowRight />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
