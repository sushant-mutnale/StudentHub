import { useNavigate } from 'react-router-dom';
import '../App.css';

const Home = () => {
  const navigate = useNavigate();

  return (
    <div className="home-container">
      <h1 className="home-title">Student Hub</h1>
      <p className="home-subtitle">
        Connect. Learn. Grow. Your career & skill development platform.
      </p>
      <div className="home-buttons">
        <button
          className="login-button"
          onClick={() => navigate('/login/student')}
        >
          Student Login
        </button>
        <button
          className="login-button"
          onClick={() => navigate('/login/recruiter')}
        >
          Recruiter Login
        </button>
      </div>
      <div className="home-links">
        <a
          className="home-link"
          onClick={() => navigate('/signup/student')}
          style={{ cursor: 'pointer' }}
        >
          Don't have an account? Sign Up as Student
        </a>
        <a
          className="home-link"
          onClick={() => navigate('/signup/recruiter')}
          style={{ cursor: 'pointer' }}
        >
          Don't have an account? Sign Up as Recruiter
        </a>
      </div>
    </div>
  );
};

export default Home;


