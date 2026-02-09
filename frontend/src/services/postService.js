import { api } from '../api/client';
import { mockPosts } from './mockData';

const mapPost = (post) => ({
  ...post,
  likes: post.likes || [],
  comments: post.comments || [],
});

export const postService = {
  fetchPosts: async () => {
    try {
      const { data } = await api.get('/posts');
      if (!data || data.length === 0) return mockPosts;
      return data.map(mapPost);
    } catch (error) {
      console.warn('Backend unavailable, using mock posts for demo.');
      return mockPosts;
    }
  },
  fetchUserPosts: async (userId) => {
    const { data } = await api.get(`/users/${userId}/posts`);
    return data.map(mapPost);
  },
  createPost: async (payload) => {
    const { data } = await api.post('/posts', payload);
    return mapPost(data);
  },
  updatePost: async (postId, payload) => {
    const { data } = await api.put(`/posts/${postId}`, payload);
    return mapPost(data);
  },
  deletePost: async (postId) => {
    await api.delete(`/posts/${postId}`);
  },
  likePost: async (postId) => {
    const { data } = await api.post(`/posts/${postId}/like`);
    return mapPost(data);
  },
  addComment: async (postId, text) => {
    const { data } = await api.post(`/posts/${postId}/comments`, { text });
    return mapPost(data);
  },
};