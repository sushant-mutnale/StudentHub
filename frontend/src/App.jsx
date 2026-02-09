import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import Home from './components/Home';
import Login from './components/Login';
import SignupStudent from './components/SignupStudent';
import SignupRecruiter from './components/SignupRecruiter';
import ForgotPassword from './components/ForgotPassword';
import StudentDashboard from './components/StudentDashboard';
import RecruiterDashboard from './components/RecruiterDashboard';
import Profile from './components/Profile';
import PublicProfile from './components/PublicProfile';
import Notifications from './components/Notifications';
import Assessment from './components/Assessment';
import Inbox from './components/messages/Inbox';
import Conversation from './components/messages/Conversation';
import InterviewsPage from './components/interviews/InterviewsPage';
import InterviewDetail from './components/interviews/InterviewDetail';
import InterviewAgent from './components/interviews/InterviewAgent';
import JobDetail from './components/JobDetail';
// Module 1-4 Components
import ResumeUpload from './components/ResumeUpload';
import SkillGapAnalysis from './components/SkillGapAnalysis';
import LearningPath from './components/LearningPath';
import MockInterview from './components/MockInterview';
import CompanyResearch from './components/CompanyResearch';
import Opportunities from './components/Opportunities';
import SmartNotifications from './components/SmartNotifications';
// Module 5 Components
import ApplicationPipeline from './components/ApplicationPipeline';
import ApplicationTracker from './components/ApplicationTracker';
import AdminDashboard from './components/AdminDashboard';
import VerificationStatus from './components/VerificationStatus';
import AnalyticsDashboard from './components/Analytics/AnalyticsDashboard';
import './App.css';

// Protected Route Component
const ProtectedRoute = ({ children, allowedType }) => {
  const { user, loading } = useAuth();

  if (loading) {
    return <div style={{
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center',
      minHeight: '100vh'
    }}>Loading...</div>;
  }

  if (!user) {
    return <Navigate to="/" replace />;
  }

  if (allowedType && user.role !== allowedType) {
    return <Navigate to="/" replace />;
  }

  return children;
};

function App() {
  return (
    <AuthProvider>
      <Router>
        <div className="app">
          <Routes>
            <Route path="/" element={<Home />} />

            <Route path="/login/:userType" element={<Login />} />
            <Route path="/forgot-password" element={<ForgotPassword />} />

            <Route path="/signup/student" element={<SignupStudent />} />
            <Route path="/signup/recruiter" element={<SignupRecruiter />} />

            <Route
              path="/dashboard/student"
              element={
                <ProtectedRoute allowedType="student">
                  <StudentDashboard />
                </ProtectedRoute>
              }
            />

            <Route
              path="/dashboard/recruiter"
              element={
                <ProtectedRoute allowedType="recruiter">
                  <RecruiterDashboard />
                </ProtectedRoute>
              }
            />

            <Route
              path="/profile/student"
              element={
                <ProtectedRoute allowedType="student">
                  <Profile />
                </ProtectedRoute>
              }
            />

            <Route path="/profile/:userId" element={<PublicProfile />} />

            {/* Module 1: Resume & Learning */}
            <Route
              path="/resume"
              element={
                <ProtectedRoute allowedType="student">
                  <ResumeUpload />
                </ProtectedRoute>
              }
            />

            <Route
              path="/skill-gaps"
              element={
                <ProtectedRoute allowedType="student">
                  <SkillGapAnalysis />
                </ProtectedRoute>
              }
            />

            <Route
              path="/learning"
              element={
                <ProtectedRoute allowedType="student">
                  <LearningPath />
                </ProtectedRoute>
              }
            />

            {/* Module 2: Mock Interview */}
            <Route
              path="/mock-interview"
              element={
                <ProtectedRoute allowedType="student">
                  <MockInterview />
                </ProtectedRoute>
              }
            />

            {/* Module 3: Research */}
            <Route
              path="/research"
              element={
                <ProtectedRoute allowedType="student">
                  <CompanyResearch />
                </ProtectedRoute>
              }
            />

            {/* Module 4: Opportunities & Notifications */}
            <Route
              path="/opportunities"
              element={
                <ProtectedRoute allowedType="student">
                  <Opportunities />
                </ProtectedRoute>
              }
            />

            <Route
              path="/smart-notifications"
              element={
                <ProtectedRoute allowedType="student">
                  <SmartNotifications />
                </ProtectedRoute>
              }
            />

            {/* Legacy Notifications */}
            <Route
              path="/notifications"
              element={
                <ProtectedRoute allowedType="student">
                  <SmartNotifications />
                </ProtectedRoute>
              }
            />

            <Route
              path="/assessment"
              element={
                <ProtectedRoute allowedType="student">
                  <Assessment />
                </ProtectedRoute>
              }
            />

            <Route
              path="/messages"
              element={
                <ProtectedRoute>
                  <Inbox />
                </ProtectedRoute>
              }
            />
            <Route
              path="/messages/:threadId"
              element={
                <ProtectedRoute>
                  <Conversation />
                </ProtectedRoute>
              }
            />
            <Route
              path="/interviews"
              element={
                <ProtectedRoute>
                  <InterviewsPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/interviews/:id"
              element={
                <ProtectedRoute>
                  <InterviewDetail />
                </ProtectedRoute>
              }
            />
            <Route
              path="/interviews/agent/:jobId"
              element={
                <ProtectedRoute allowedType="student">
                  <InterviewAgent />
                </ProtectedRoute>
              }
            />

            <Route
              path="/jobs/:jobId"
              element={
                <ProtectedRoute>
                  <JobDetail />
                </ProtectedRoute>
              }
            />

            {/* Module 5: ATS & Tracking */}
            <Route
              path="/pipeline"
              element={
                <ProtectedRoute allowedType="recruiter">
                  <ApplicationPipeline />
                </ProtectedRoute>
              }
            />

            <Route
              path="/applications"
              element={
                <ProtectedRoute allowedType="student">
                  <ApplicationTracker />
                </ProtectedRoute>
              }
            />

            <Route
              path="/admin/dashboard"
              element={
                <ProtectedRoute>
                  <AdminDashboard />
                </ProtectedRoute>
              }
            />

            <Route
              path="/verify"
              element={
                <ProtectedRoute allowedType="recruiter">
                  <VerificationStatus />
                </ProtectedRoute>
              }
            />

            <Route
              path="/analytics"
              element={
                <ProtectedRoute>
                  <AnalyticsDashboard />
                </ProtectedRoute>
              }
            />

            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </div>
      </Router>
    </AuthProvider>
  );
}

export default App;
