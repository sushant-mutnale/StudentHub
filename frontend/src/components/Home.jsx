import { useNavigate } from 'react-router-dom';
import '../App.css';

const Home = () => {
  const navigate = useNavigate();

  return (
    <div className="home-container modern">
      {/* Decorative Elements */}
      <div className="home-decoration">
        <div className="floating-orb orb-1"></div>
        <div className="floating-orb orb-2"></div>
        <div className="floating-orb orb-3"></div>
        <div className="grid-pattern"></div>
      </div>

      {/* Main Content */}
      <div className="home-content">
        {/* Logo/Icon */}
        <div className="home-logo">
          <span className="logo-icon">🎓</span>
        </div>

        {/* Title */}
        <h1 className="home-title gradient-text">
          Student Hub
        </h1>

        {/* Tagline */}
        <p className="home-tagline">
          Connect. Learn. Grow.
        </p>
        <p className="home-subtitle">
          Your AI-powered career & skill development platform
        </p>

        {/* Feature Cards */}
        <div className="home-features">
          <div className="feature-card glass">
            <span className="feature-icon">🚀</span>
            <span className="feature-text">AI Resume Analysis</span>
          </div>
          <div className="feature-card glass">
            <span className="feature-icon">💼</span>
            <span className="feature-text">Smart Job Matching</span>
          </div>
          <div className="feature-card glass">
            <span className="feature-icon">🎯</span>
            <span className="feature-text">Mock Interviews</span>
          </div>
        </div>

        {/* Login Buttons */}
        <div className="home-buttons">
          <button
            className="home-btn primary"
            onClick={() => navigate('/login/student')}
          >
            <span className="btn-icon">🎓</span>
            <span className="btn-text">Student Login</span>
            <span className="btn-arrow">→</span>
          </button>
          <button
            className="home-btn secondary"
            onClick={() => navigate('/login/recruiter')}
          >
            <span className="btn-icon">💼</span>
            <span className="btn-text">Recruiter Login</span>
            <span className="btn-arrow">→</span>
          </button>
        </div>

        {/* Signup Links */}
        <div className="home-links">
          <span
            className="home-link"
            onClick={() => navigate('/signup/student')}
          >
            New Student? <strong>Create Account</strong>
          </span>
          <span className="link-divider">•</span>
          <span
            className="home-link"
            onClick={() => navigate('/signup/recruiter')}
          >
            Hiring? <strong>Join as Recruiter</strong>
          </span>
        </div>

        {/* Footer */}
        <div className="home-footer">
          <p>© 2026 StudentHub. Empowering the next generation.</p>
        </div>
      </div>
    </div>
  );
};

export default Home;
