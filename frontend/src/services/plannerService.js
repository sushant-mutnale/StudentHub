import { api } from '../api/client';

export const plannerService = {
               // Generate study plan
               generatePlan: async (targetRole, duration = '4 weeks', focusAreas = []) => {
                              const { data } = await api.post('/planner/generate', {
                                             target_role: targetRole,
                                             duration,
                                             focus_areas: focusAreas
                              });
                              return data;
               },

               // Get my current plan
               getMyPlan: async () => {
                              const { data } = await api.get('/planner/my');
                              return data;
               },

               // Update plan progress
               updateProgress: async (planId, weekIndex, taskIndex, completed) => {
                              const { data } = await api.post(`/planner/${planId}/progress`, {
                                             week_index: weekIndex,
                                             task_index: taskIndex,
                                             completed
                              });
                              return data;
               },

               // Get daily focus
               getDailyFocus: async () => {
                              const { data } = await api.get('/planner/daily-focus');
                              return data;
               },

               // Regenerate plan
               regeneratePlan: async (planId, feedback = null) => {
                              const { data } = await api.post(`/planner/${planId}/regenerate`, { feedback });
                              return data;
               }
};
