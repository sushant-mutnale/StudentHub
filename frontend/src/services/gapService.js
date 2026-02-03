import { api } from '../api/client';

export const gapService = {
               // Analyze skill gaps against a specific job
               analyzeForJob: async (jobId) => {
                              const { data } = await api.get(`/learning/gap-analysis/${jobId}`);
                              return data;
               },

               // Get overall skill gaps
               getMyGaps: async () => {
                              const { data } = await api.get('/learning/my-gaps');
                              return data;
               },

               // Get gap analysis with recommendations
               getGapWithRecommendations: async (targetRole = null) => {
                              const params = targetRole ? { target_role: targetRole } : {};
                              const { data } = await api.get('/learning/gap-recommendations', { params });
                              return data;
               }
};
