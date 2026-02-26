import { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { postService } from '../services/postService';
import { FiEdit2, FiTag, FiSend, FiLoader } from 'react-icons/fi';
import Avatar from './Avatar';
import '../App.css';

const PostBox = ({ onPostCreated }) => {
  const { user } = useAuth();
  const [content, setContent] = useState('');
  const [tags, setTags] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [isFocused, setIsFocused] = useState(false);

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
    <div className={`glass-card ${isFocused ? 'active' : ''}`} style={{
      marginBottom: '1.5rem',
      padding: '1.5rem',
      borderRadius: 'var(--radius-lg)',
      transition: 'var(--transition-normal)',
      border: isFocused ? '1px solid var(--color-primary)' : '1px solid rgba(255,255,255,0.5)',
      boxShadow: isFocused ? 'var(--shadow-glow)' : 'var(--shadow-sm)'
    }}>
      <div style={{ display: 'flex', gap: '1rem' }}>
        <div style={{ flexShrink: 0 }}>
          <Avatar
            src={user.avatar_url}
            alt={user.fullName}
            size={48}
            style={{
              border: '2px solid white',
              boxShadow: 'var(--shadow-sm)'
            }}
          />
        </div>

        <form onSubmit={handleSubmit} style={{ flex: 1 }}>
          <div style={{
            background: 'var(--color-bg-alt)',
            borderRadius: 'var(--radius-md)',
            padding: '0.5rem',
            marginBottom: '1rem',
            transition: 'var(--transition-fast)',
            border: '1px solid transparent',
            ...(isFocused ? { background: 'white', borderColor: 'var(--color-primary)' } : {})
          }}>
            <textarea
              className="custom-scrollbar"
              placeholder={`What's on your mind, ${user.fullName?.split(' ')[0]}?`}
              value={content}
              onChange={(e) => setContent(e.target.value)}
              onFocus={() => setIsFocused(true)}
              onBlur={() => !content && !tags && setIsFocused(false)}
              rows={isFocused || content ? 4 : 2}
              style={{
                width: '100%',
                border: 'none',
                outline: 'none',
                background: 'transparent',
                resize: 'none',
                fontSize: '1rem',
                fontFamily: 'inherit',
                color: 'var(--color-text)',
                padding: '0.5rem'
              }}
            />
          </div>

          {(isFocused || content || tags) && (
            <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
                padding: '0.5rem 1rem',
                background: 'rgba(255,255,255,0.5)',
                borderRadius: 'var(--radius-md)',
                border: '1px solid var(--color-border-light)'
              }}>
                <FiTag size={16} color="var(--color-text-muted)" />
                <input
                  type="text"
                  placeholder="Add tags (e.g., career, interview, react)"
                  value={tags}
                  onChange={(e) => setTags(e.target.value)}
                  style={{
                    flex: 1,
                    border: 'none',
                    outline: 'none',
                    background: 'transparent',
                    fontSize: '0.9rem',
                    color: 'var(--color-text)'
                  }}
                />
              </div>

              {error && (
                <div style={{
                  fontSize: '0.85rem',
                  color: 'var(--color-danger)',
                  padding: '0.5rem',
                  background: 'rgba(239, 68, 68, 0.1)',
                  borderRadius: 'var(--radius-sm)'
                }}>
                  {error}
                </div>
              )}

              <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                <button
                  type="submit"
                  className="btn-glow"
                  disabled={loading || !content.trim()}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.5rem',
                    padding: '0.75rem 1.5rem',
                    background: !content.trim() ? 'var(--color-bg-alt)' : 'var(--gradient-primary)',
                    color: !content.trim() ? 'var(--color-text-muted)' : 'white',
                    border: 'none',
                    borderRadius: 'var(--radius-md)',
                    fontWeight: '600',
                    cursor: !content.trim() ? 'not-allowed' : 'pointer',
                    boxShadow: content.trim() ? 'var(--shadow-md)' : 'none',
                    transition: 'var(--transition-normal)'
                  }}
                >
                  {loading ? (
                    <>
                      <FiLoader className="animate-spin" size={18} />
                      Posting...
                    </>
                  ) : (
                    <>
                      <FiSend size={18} />
                      Post
                    </>
                  )}
                </button>
              </div>
            </div>
          )}
        </form>
      </div>
    </div>
  );
};

export default PostBox;
