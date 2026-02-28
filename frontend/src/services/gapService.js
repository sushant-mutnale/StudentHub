import { api } from '../api/client';
import { mockGapAnalysis } from './mockData';

export const gapService = {
    // Analyze skill gaps against a specific job
    analyzeForJob: async (jobId) => {
        try {
            const { data } = await api.get(`/learning/gap-analysis/${jobId}`);
            return data;
        } catch (error) {
            console.warn('Backend unavailable, using mock gap analysis for demo.');
            return mockGapAnalysis;
        }
    },

    // Get overall skill gaps
    getMyGaps: async () => {
        const { data } = await api.get('/learning/my-gaps');
        return data;
    },

    // Get gap analysis with recommendations
    getGapWithRecommendations: async (targetRole = null) => {
        try {
            const { data } = await api.get('/learning/gap-recommendations', {
                params: { target_role: targetRole }
            });

            // The backend now returns the full AI analysis structure (data.gaps, data.recommendations, etc)
            return data;
        } catch (error) {
            console.warn('Backend unavailable, using mock gap recommendations for demo.');
            return mockGapAnalysis;
        }
    }
};
