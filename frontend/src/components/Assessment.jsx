import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import SidebarLeft from './SidebarLeft';
import '../App.css';

const Assessment = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [assessments, setAssessments] = useState([]);
  const [activeAssessment, setActiveAssessment] = useState(null);
  const [answers, setAnswers] = useState({});
  const [submitted, setSubmitted] = useState(false);
  const [score, setScore] = useState(null);

  // Mock quiz data based on skills
  const quizData = {
    React: [
      {
        id: 'r1',
        question: 'What is a React Hook?',
        options: [
          'A function that lets you use state and other React features',
          'A component lifecycle method',
          'A styling library',
          'A state management tool'
        ],
        correct: 0
      },
      {
        id: 'r2',
        question: 'Explain Virtual DOM.',
        options: [
          'A physical DOM element',
          'A JavaScript representation of the real DOM',
          'A browser API',
          'A React component'
        ],
        correct: 1
      },
      {
        id: 'r3',
        question: 'What does useEffect hook do?',
        options: [
          'Manages component styling',
          'Performs side effects in functional components',
          'Creates new components',
          'Handles routing'
        ],
        correct: 1
      },
      {
        id: 'r4',
        question: 'What is JSX?',
        options: [
          'A JavaScript extension for XML',
          'A CSS framework',
          'A database query language',
          'A testing framework'
        ],
        correct: 0
      },
      {
        id: 'r5',
        question: 'Which hook is used for state management?',
        options: ['useEffect', 'useState', 'useContext', 'useReducer'],
        correct: 1
      }
    ],
    'Node.js': [
      {
        id: 'n1',
        question: 'What is Node.js?',
        options: [
          'A JavaScript runtime built on Chrome\'s V8 engine',
          'A frontend framework',
          'A database',
          'A CSS preprocessor'
        ],
        correct: 0
      },
      {
        id: 'n2',
        question: 'What is npm?',
        options: [
          'Node Package Manager',
          'A JavaScript framework',
          'A database',
          'A server'
        ],
        correct: 0
      },
      {
        id: 'n3',
        question: 'How do you handle asynchronous operations in Node.js?',
        options: ['Promises', 'Callbacks', 'Async/Await', 'All of the above'],
        correct: 3
      },
      {
        id: 'n4',
        question: 'What is Express.js?',
        options: [
          'A web application framework for Node.js',
          'A database',
          'A frontend library',
          'A testing tool'
        ],
        correct: 0
      },
      {
        id: 'n5',
        question: 'What module is used for file system operations?',
        options: ['fs', 'http', 'path', 'url'],
        correct: 0
      }
    ],
    Python: [
      {
        id: 'p1',
        question: 'What is a list comprehension?',
        options: [
          'A concise way to create lists',
          'A type of loop',
          'A function',
          'A variable'
        ],
        correct: 0
      },
      {
        id: 'p2',
        question: 'What is the difference between a tuple and a list?',
        options: [
          'Tuples are immutable, lists are mutable',
          'Lists are immutable, tuples are mutable',
          'They are the same',
          'Tuples can only contain numbers'
        ],
        correct: 0
      },
      {
        id: 'p3',
        question: 'What does __init__ do in a class?',
        options: [
          'Initializes the class instance',
          'Destroys the instance',
          'Imports modules',
          'Exports functions'
        ],
        correct: 0
      },
      {
        id: 'p4',
        question: 'What is a decorator in Python?',
        options: [
          'A function that modifies another function',
          'A variable',
          'A class',
          'A module'
        ],
        correct: 0
      },
      {
        id: 'p5',
        question: 'How do you create a virtual environment?',
        options: [
          'python -m venv venv',
          'npm install venv',
          'pip create venv',
          'create venv'
        ],
        correct: 0
      }
    ],
    'Machine Learning': [
      {
        id: 'm1',
        question: 'What is supervised learning?',
        options: [
          'Learning with labeled data',
          'Learning without data',
          'Learning with unlabeled data',
          'Learning without a teacher'
        ],
        correct: 0
      },
      {
        id: 'm2',
        question: 'What is overfitting?',
        options: [
          'Model performs well on training data but poorly on test data',
          'Model performs poorly on all data',
          'Model performs well on all data',
          'Model has too few parameters'
        ],
        correct: 0
      },
      {
        id: 'm3',
        question: 'What is gradient descent?',
        options: [
          'An optimization algorithm',
          'A data structure',
          'A neural network layer',
          'A loss function'
        ],
        correct: 0
      },
      {
        id: 'm4',
        question: 'What is the purpose of train-test split?',
        options: [
          'To evaluate model performance on unseen data',
          'To speed up training',
          'To reduce memory usage',
          'To increase accuracy'
        ],
        correct: 0
      },
      {
        id: 'm5',
        question: 'What is a neural network?',
        options: [
          'A computing system inspired by biological neural networks',
          'A database',
          'A programming language',
          'A web framework'
        ],
        correct: 0
      }
    ]
  };

  useEffect(() => {
    if (!user || user.role !== 'student') {
      navigate('/');
      return;
    }

    // Initialize assessments based on user skills
    if (user.skills && user.skills.length > 0) {
      const availableAssessments = user.skills
        .map((skill) => {
          const normalizedSkill = skill.trim();
          if (quizData[normalizedSkill]) {
            return {
              skill: normalizedSkill,
              questions: quizData[normalizedSkill],
              completed: false
            };
          }
          return null;
        })
        .filter((a) => a !== null);

      setAssessments(availableAssessments);
    }
  }, [user, navigate]);

  const handleStartAssessment = (assessment) => {
    setActiveAssessment(assessment);
    setAnswers({});
    setSubmitted(false);
    setScore(null);
  };

  const handleAnswerChange = (questionId, answerIndex) => {
    setAnswers({
      ...answers,
      [questionId]: answerIndex
    });
  };

  const handleSubmit = () => {
    if (!activeAssessment) return;

    let correctCount = 0;
    activeAssessment.questions.forEach((q) => {
      if (answers[q.id] === q.correct) {
        correctCount++;
      }
    });

    const totalQuestions = activeAssessment.questions.length;
    const percentage = (correctCount / totalQuestions) * 100;

    setScore({
      correct: correctCount,
      total: totalQuestions,
      percentage: percentage.toFixed(0)
    });
    setSubmitted(true);

    // Mark assessment as completed
    setAssessments((prev) =>
      prev.map((a) =>
        a.skill === activeAssessment.skill
          ? { ...a, completed: true }
          : a
      )
    );
  };

  if (!user || user.role !== 'student') {
    return null;
  }

  return (
    <div className="dashboard-container">
      <SidebarLeft />
      <div className="dashboard-main">
        <div className="dashboard-header">
          <h1 className="dashboard-title">Skill Assessment</h1>
        </div>
        <div className="dashboard-content">
          {!activeAssessment ? (
            <div>
              <p style={{ marginBottom: '2rem', color: '#666' }}>
                Test your knowledge in your listed skills. Select a skill to start an assessment.
              </p>

              {assessments.length === 0 ? (
                <div
                  style={{
                    textAlign: 'center',
                    padding: '3rem',
                    backgroundColor: 'white',
                    borderRadius: '12px',
                    border: '1px solid #e1e8ed'
                  }}
                >
                  <p style={{ color: '#666', marginBottom: '1rem' }}>
                    No assessments available. Add skills to your profile to see assessments.
                  </p>
                </div>
              ) : (
                <div className="assessments-list">
                  {assessments.map((assessment, index) => (
                    <div
                      key={index}
                      className="assessment-card"
                      style={{
                        backgroundColor: 'white',
                        borderRadius: '12px',
                        padding: '1.5rem',
                        marginBottom: '1rem',
                        border: '1px solid #e1e8ed',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center'
                      }}
                    >
                      <div>
                        <h3 style={{ fontSize: '1.25rem', fontWeight: 700, marginBottom: '0.5rem' }}>
                          {assessment.skill} Assessment
                        </h3>
                        <p style={{ color: '#666' }}>
                          {assessment.questions.length} questions
                        </p>
                        {assessment.completed && (
                          <span
                            style={{
                              display: 'inline-block',
                              marginTop: '0.5rem',
                              padding: '0.25rem 0.75rem',
                              backgroundColor: '#d4edda',
                              color: '#155724',
                              borderRadius: '12px',
                              fontSize: '0.85rem'
                            }}
                          >
                            ✓ Completed
                          </span>
                        )}
                      </div>
                      <button
                        className="form-button"
                        onClick={() => handleStartAssessment(assessment)}
                      >
                        {assessment.completed ? 'Retake' : 'Start Assessment'}
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ) : (
            <div>
              <button
                className="form-button"
                style={{ marginBottom: '1.5rem', backgroundColor: '#999' }}
                onClick={() => {
                  setActiveAssessment(null);
                  setAnswers({});
                  setSubmitted(false);
                  setScore(null);
                }}
              >
                ← Back to Assessments
              </button>

              <div
                style={{
                  backgroundColor: 'white',
                  borderRadius: '12px',
                  padding: '2rem',
                  border: '1px solid #e1e8ed'
                }}
              >
                <h2 style={{ fontSize: '1.5rem', fontWeight: 700, marginBottom: '1.5rem' }}>
                  {activeAssessment.skill} Assessment
                </h2>

                {!submitted ? (
                  <>
                    {activeAssessment.questions.map((q, index) => (
                      <div
                        key={q.id}
                        style={{
                          marginBottom: '2rem',
                          paddingBottom: '2rem',
                          borderBottom: index < activeAssessment.questions.length - 1 ? '1px solid #e1e8ed' : 'none'
                        }}
                      >
                        <h3 style={{ marginBottom: '1rem', fontSize: '1.1rem', fontWeight: 600 }}>
                          {index + 1}. {q.question}
                        </h3>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                          {q.options.map((option, optIndex) => (
                            <label
                              key={optIndex}
                              style={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: '0.75rem',
                                padding: '0.75rem',
                                border: '2px solid #e1e8ed',
                                borderRadius: '8px',
                                cursor: 'pointer',
                                transition: 'all 0.2s'
                              }}
                              onMouseEnter={(e) => {
                                e.currentTarget.style.borderColor = '#667eea';
                                e.currentTarget.style.backgroundColor = '#f0f4ff';
                              }}
                              onMouseLeave={(e) => {
                                e.currentTarget.style.borderColor = '#e1e8ed';
                                e.currentTarget.style.backgroundColor = 'transparent';
                              }}
                            >
                              <input
                                type="radio"
                                name={q.id}
                                value={optIndex}
                                checked={answers[q.id] === optIndex}
                                onChange={() => handleAnswerChange(q.id, optIndex)}
                                style={{ cursor: 'pointer' }}
                              />
                              <span>{option}</span>
                            </label>
                          ))}
                        </div>
                      </div>
                    ))}

                    <button
                      className="form-button"
                      onClick={handleSubmit}
                      style={{ width: '100%', marginTop: '1rem' }}
                    >
                      Submit Assessment
                    </button>
                  </>
                ) : (
                  <div style={{ textAlign: 'center', padding: '2rem' }}>
                    <div
                      style={{
                        fontSize: '3rem',
                        fontWeight: 700,
                        color: '#667eea',
                        marginBottom: '1rem'
                      }}
                    >
                      {score.percentage}%
                    </div>
                    <h3 style={{ fontSize: '1.5rem', marginBottom: '1rem' }}>
                      Great! You got {score.correct}/{score.total} correct in {activeAssessment.skill} skills.
                    </h3>
                    <p style={{ color: '#666', marginBottom: '2rem' }}>
                      {score.percentage >= 80
                        ? 'Excellent work! You have a strong understanding of this skill.'
                        : score.percentage >= 60
                        ? 'Good job! Consider reviewing some topics for better mastery.'
                        : 'Keep learning! Review the topics and try again.'}
                    </p>

                    <div style={{ marginTop: '2rem' }}>
                      <h4 style={{ marginBottom: '1rem', fontWeight: 600 }}>Review Answers:</h4>
                      {activeAssessment.questions.map((q, index) => {
                        const userAnswer = answers[q.id];
                        const isCorrect = userAnswer === q.correct;
                        return (
                          <div
                            key={q.id}
                            style={{
                              marginBottom: '1rem',
                              padding: '1rem',
                              backgroundColor: isCorrect ? '#d4edda' : '#f8d7da',
                              borderRadius: '8px',
                              textAlign: 'left'
                            }}
                          >
                            <div style={{ fontWeight: 600, marginBottom: '0.5rem' }}>
                              {index + 1}. {q.question}
                            </div>
                            <div style={{ fontSize: '0.9rem' }}>
                              <div>
                                Your answer: {q.options[userAnswer]}{' '}
                                {isCorrect ? '✓' : '✗'}
                              </div>
                              {!isCorrect && (
                                <div style={{ marginTop: '0.5rem', fontWeight: 600 }}>
                                  Correct answer: {q.options[q.correct]}
                                </div>
                              )}
                            </div>
                          </div>
                        );
                      })}
                    </div>

                    <button
                      className="form-button"
                      onClick={() => {
                        setActiveAssessment(null);
                        setAnswers({});
                        setSubmitted(false);
                        setScore(null);
                      }}
                      style={{ marginTop: '2rem' }}
                    >
                      Back to Assessments
                    </button>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Assessment;

