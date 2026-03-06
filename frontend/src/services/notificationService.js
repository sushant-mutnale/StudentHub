import { api as API } from '../api/client';
import { mockNotifications } from './mockData';

export const notificationService = {
               getNotifications: async () => {
                              try {
                                             const response = await API.get('/notifications/');
                                             return response.data;
                              } catch (error) {
                                             console.warn('Backend unavailable, using mock notifications for demo.');
                                             return mockNotifications;
                              }
               },

               markAsRead: async (notificationId) => {
                              const response = await API.put(`/notifications/${notificationId}/read`);
                              return response.data;
               },

               markAllAsRead: async () => {
                              const response = await API.put('/notifications/read-all');
                              return response.data;
               }
};
