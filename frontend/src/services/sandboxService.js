import { api } from '../api/client';

export const sandboxService = {
               // Execute code
               runCode: async (code, language = 'python', testCases = []) => {
                              const { data } = await api.post('/sandbox/run', {
                                             code,
                                             language,
                                             test_cases: testCases
                              });
                              return data;
               },

               // Validate DSA solution
               validateSolution: async (code, language, problemId) => {
                              const { data } = await api.post('/sandbox/validate', {
                                             code,
                                             language,
                                             problem_id: problemId
                              });
                              return data;
               },

               // Get supported languages
               getLanguages: async () => {
                              const { data } = await api.get('/sandbox/languages');
                              return data;
               },

               // Get execution history
               getHistory: async (limit = 10) => {
                              const { data } = await api.get('/sandbox/history', { params: { limit } });
                              return data;
               }
};
