import { api } from '../api/client';

export const learningService = {
               // Get my learning paths
               getMyPaths: async () => {
                              const { data } = await api.get('/learning/paths/my');
                              return data;
               },

               // Generate learning path for a skill
               generatePath: async (skill, targetLevel = 'advanced') => {
                              const { data } = await api.post('/learning/paths/generate', {
                                             skill,
                                             target_level: targetLevel
                              });
                              return data;
               },

               // Get specific path details
               getPath: async (pathId) => {
                              const { data } = await api.get(`/learning/paths/${pathId}`);
                              return data;
               },

               // Mark stage complete
               completeStage: async (pathId, stageIndex) => {
                              const { data } = await api.post(`/learning/paths/${pathId}/complete-stage`, {
                                             stage_index: stageIndex
                              });
                              return data;
               },

               // Search courses
               searchCourses: async (query, platform = null) => {
                              const params = { q: query };
                              if (platform) params.platform = platform;
                              const { data } = await api.get('/courses/search', { params });
                              return data;
               },

               // Get recommended courses
               getRecommendedCourses: async (skill) => {
                              const { data } = await api.get('/courses/recommended', { params: { skill } });
                              return data;
               },

               // Get AI coaching for a topic
               getCoaching: async (topic, currentLevel) => {
                              const { data } = await api.post('/learning/coaching', {
                                             topic,
                                             current_level: currentLevel
                              });
                              return data;
               }
};
