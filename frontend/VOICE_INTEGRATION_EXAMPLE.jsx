// Import VoiceInterview component in your main app or router
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import VoiceInterview from './components/VoiceInterview';
import './components/VoiceInterview.css';

// Example: Add voice interview route
function App() {
    return (
        <BrowserRouter>
            <Routes>
                {/* ... existing routes ... */}

                {/* Voice Interview Route */}
                <Route
                    path="/interview/voice"
                    element={
                        <VoiceInterview
                            company="Amazon"
                            role="Software Engineer"
                            onComplete={() => {
                                // Navigate to results page or show completion modal
                                window.location.href = '/interview/results';
                            }}
                        />
                    }
                />
            </Routes>
        </BrowserRouter>
    );
}

export default App;
