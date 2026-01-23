import { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { postService } from '../services/postService';
import '../App.css';

const PostBox = ({ onPostCreated }) => {
  const { user } = useAuth();
  const [content, setContent] = useState('');
  const [tags, setTags] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!content.trim()) return;

    setLoading(true);
    setError('');
    try {
      const tagsArray = tags
        .split(',')
        .map((tag) => tag.trim())
        .filter((tag) => tag.length > 0);

      await postService.createPost({
        content,
        tags: tagsArray,
      });
      setContent('');
      setTags('');
      if (onPostCreated) {
        onPostCreated();
      }
    } catch (error) {
      setError(error.message || 'Error creating post');
    } finally {
      setLoading(false);
    }
  };

  if (!user || user.role !== 'student') {
    return null;
  }

  return (
    <div className="post-box">
      <form onSubmit={handleSubmit}>
        <textarea
          className="post-box-textarea"
          placeholder="What's on your mind?"
          value={content}
          onChange={(e) => setContent(e.target.value)}
          rows="4"
        />
        <input
          type="text"
          className="post-box-input"
          placeholder="Add comma-separated tags (optional)"
          value={tags}
          onChange={(e) => setTags(e.target.value)}
        />
        {error && <div className="error-message" style={{ marginTop: '0.5rem' }}>{error}</div>}
        <div className="post-box-actions">
          <button
            type="submit"
            className="post-button"
            disabled={loading || !content.trim()}
          >
            {loading ? 'Posting...' : 'Post'}
          </button>
        </div>
      </form>
    </div>
  );
};

export default PostBox;

