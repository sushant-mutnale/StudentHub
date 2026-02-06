import axios from 'axios';

const API_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const getAuthHeader = () => {
               const token = localStorage.getItem('token');
               return { headers: { Authorization: `Bearer ${token}` } };
};

export const scorecardService = {
               // Get templates
               getTemplates: async () => {
                              const response = await axios.get(`${API_URL}/scorecards/templates`, getAuthHeader());
                              return response.data;
               },

               // Submit scorecard
               submitScorecard: async (scorecardData) => {
                              const response = await axios.post(`${API_URL}/scorecards`, scorecardData, getAuthHeader());
                              return response.data;
               },

               // Get application scorecards
               getApplicationScorecards: async (applicationId) => {
                              const response = await axios.get(`${API_URL}/scorecards/application/${applicationId}`, getAuthHeader());
                              return response.data;
               },

               // Get aggregation (average scores)
               getAggregation: async (applicationId) => {
                              const response = await axios.get(`${API_URL}/scorecards/application/${applicationId}/aggregate`, getAuthHeader());
                              return response.data;
               }
};
