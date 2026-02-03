import { api } from '../api/client';

export const recommendationService = {
               // Get personalized job recommendations
               getJobRecommendations: async (limit = 20, filters = {}) => {
                              const params = { limit, ...filters };
                              const { data } = await api.get('/recommendations/jobs', { params });
                              return data;
               },

               // Get hackathon recommendations
               getHackathonRecommendations: async (limit = 10, filters = {}) => {
                              const params = { limit, ...filters };
                              const { data } = await api.get('/recommendations/hackathons', { params });
                              return data;
               },

               // Get content recommendations
               getContentRecommendations: async (limit = 15, filters = {}) => {
                              const params = { limit, ...filters };
                              const { data } = await api.get('/recommendations/content', { params });
                              return data;
               },

               // Get combined feed
               getFeed: async (jobsLimit = 5, hackathonsLimit = 3, contentLimit = 5) => {
                              const { data } = await api.get('/recommendations/feed', {
                                             params: { jobs_limit: jobsLimit, hackathons_limit: hackathonsLimit, content_limit: contentLimit }
                              });
                              return data;
               },

               // Record feedback on a recommendation
               recordFeedback: async (opportunityId, opportunityType, action, score = null, rank = null) => {
                              const { data } = await api.post('/recommendations/feedback', {
                                             opportunity_id: opportunityId,
                                             opportunity_type: opportunityType,
                                             action,
                                             recommendation_score: score,
                                             recommendation_rank: rank
                              });
                              return data;
               },

               // Get engagement stats
               getStats: async () => {
                              const { data } = await api.get('/recommendations/stats');
                              return data;
               },

               // Demo job recommendations
               getDemoRecommendations: async (limit = 5) => {
                              const { data } = await api.get('/recommendations/demo/jobs', { params: { limit } });
                              return data;
               }
};
