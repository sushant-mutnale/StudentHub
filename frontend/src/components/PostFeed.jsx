import { useEffect, useState, useRef } from 'react';
import { Link } from 'react-router-dom';
import { FiEdit3, FiHeart, FiMoreVertical, FiTrash2, FiX } from 'react-icons/fi';
import { useAuth } from '../contexts/AuthContext';
import { postService } from '../services/postService';
import Avatar from './Avatar';
import '../App.css';

const PostFeed = ({ refreshTrigger = 0 }) => {
  const { user } = useAuth();
  const [posts, setPosts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [editingPostId, setEditingPostId] = useState(null);
  const [editContent, setEditContent] = useState('');
  const [editTags, setEditTags] = useState('');
  const [openMenuId, setOpenMenuId] = useState(null);
  const [commentInputs, setCommentInputs] = useState({});
  const menuRef = useRef(null);

  useEffect(() => {
    loadPosts();
  }, [refreshTrigger]);

  const loadPosts = async () => {
    setLoading(true);
    try {
      const data = await postService.fetchPosts();
      setPosts(data);
      setError('');
    } catch (err) {
      setError(err.message || 'Unable to load posts');
    } finally {
      setLoading(false);
    }
  };

  const formatTimestamp = (timestamp) => {
    const date = new Date(timestamp);
    return date.toLocaleString();
  };

  const startEditing = (post) => {
    setEditingPostId(post.id);
    setEditContent(post.content);
    setEditTags(post.tags?.join(', ') || '');
  };

  const cancelEditing = () => {
    setEditingPostId(null);
    setEditContent('');
    setEditTags('');
  };

  const saveEdit = async () => {
    if (!editContent.trim()) return;
    const tagsArray = editTags
      .split(',')
      .map((tag) => tag.trim())
      .filter((tag) => tag.length > 0);
    try {
      await postService.updatePost(editingPostId, {
        content: editContent,
        tags: tagsArray,
      });
      cancelEditing();
      loadPosts();
    } catch (err) {
      setError(err.message || 'Failed to update post');
    }
  };

  const deletePost = async (postId) => {
    if (!window.confirm('Delete this post?')) return;
    try {
      await postService.deletePost(postId);
      loadPosts();
    } catch (err) {
      setError(err.message || 'Failed to delete post');
    }
  };

  const toggleLike = async (postId) => {
    try {
      await postService.likePost(postId);
      loadPosts();
    } catch (err) {
      setError(err.message || 'Failed to like post');
    }
  };

  const handleCommentChange = (postId, value) => {
    setCommentInputs((prev) => ({
      ...prev,
      [postId]: value,
    }));
  };

  const handleAddComment = async (postId) => {
    const text = (commentInputs[postId] || '').trim();
    if (!text) return;
    try {
      await postService.addComment(postId, text);
      setCommentInputs((prev) => ({ ...prev, [postId]: '' }));
      loadPosts();
    } catch (err) {
      setError(err.message || 'Failed to add comment');
    }
  };

  const canManagePost = (post) =>
    user && user.role === 'student' && post.author_id === user.id;

  // Close menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (menuRef.current && !menuRef.current.contains(event.target)) {
        setOpenMenuId(null);
      }
    };

    if (openMenuId) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }
  }, [openMenuId]);

  const toggleMenu = (postId) => {
    setOpenMenuId(openMenuId === postId ? null : postId);
  };

  const handleEdit = (post) => {
    setOpenMenuId(null);
    startEditing(post);
  };

  const handleDelete = (postId) => {
    setOpenMenuId(null);
    deletePost(postId);
  };

  if (loading) {
    return (
      <div className="post-feed">
        <div style={{ textAlign: 'center', padding: '2rem' }}>Loading posts...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="post-feed">
        <div className="error-message" style={{ marginBottom: '1rem' }}>
          {error}
        </div>
        <button className="form-button" onClick={loadPosts}>
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="post-feed">
      {posts.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '2rem', color: '#666' }}>
          No posts yet. Be the first to post!
        </div>
      ) : (
        posts.map((post) => {
          const liked = user ? post.likes?.includes(user.id) : false;
          return (
            <div key={post.id} className="post-item student-post">
              <div className="post-header">
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                  <Link to={`/profile/${post.author_id}`}>
                    <Avatar
                      src={post.author_avatar_url}
                      alt={post.author_name}
                      size={40}
                    />
                  </Link>
                  <div>
                    <div className="post-author">
                      <Link to={`/profile/${post.author_id}`} className="post-author-link">
                        {post.author_name}
                      </Link>
                    </div>
                    <div className="post-username">@{post.author_username}</div>
                  </div>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <div className="post-timestamp">
                    {formatTimestamp(post.created_at || post.updated_at)}
                  </div>
                  {canManagePost(post) && (
                    <div className="post-menu-container" ref={menuRef}>
                      <button
                        className="post-menu-button"
                        onClick={() => toggleMenu(post.id)}
                        aria-label="More options"
                      >
                        <FiMoreVertical />
                      </button>
                      {openMenuId === post.id && (
                        <div className="post-menu-dropdown">
                          <button
                            className="post-menu-item"
                            onClick={() => handleEdit(post)}
                          >
                            <FiEdit3 /> Edit
                          </button>
                          <button
                            className="post-menu-item danger"
                            onClick={() => handleDelete(post.id)}
                          >
                            <FiTrash2 /> Delete
                          </button>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>

              {editingPostId === post.id ? (
                <div className="edit-post-form">
                  <textarea
                    className="post-box-textarea"
                    rows="3"
                    value={editContent}
                    onChange={(e) => setEditContent(e.target.value)}
                  />
                  <input
                    type="text"
                    className="post-box-input"
                    value={editTags}
                    onChange={(e) => setEditTags(e.target.value)}
                    placeholder="Tags (comma separated)"
                  />
                  <div className="edit-actions">
                    <button className="post-button" onClick={saveEdit}>
                      Save
                    </button>
                    <button className="comment-cancel" onClick={cancelEditing}>
                      Cancel
                    </button>
                  </div>
                </div>
              ) : (
                <>
                  <div className="post-content">{post.content}</div>
                  {post.tags?.length > 0 && (
                    <div className="post-tags">
                      {post.tags.map((tag) => (
                        <span key={tag} className="skill-tag">
                          #{tag}
                        </span>
                      ))}
                    </div>
                  )}
                </>
              )}

              <div className="post-actions">
                <button
                  className={`post-action ${liked ? 'liked' : ''}`}
                  onClick={() => toggleLike(post.id)}
                >
                  <FiHeart /> <span>{post.likes?.length || 0}</span>
                </button>
              </div>
              <div className="post-comments">
                {post.comments && post.comments.length > 0 && (
                  <div className="comments-list">
                    {post.comments.map((comment) => (
                      <div key={comment.id} className="comment-item">
                        <div className="comment-meta">
                          <span className="comment-author">Comment</span>
                          <span className="comment-timestamp">
                            {formatTimestamp(comment.created_at)}
                          </span>
                        </div>
                        <div className="comment-text">{comment.text}</div>
                      </div>
                    ))}
                  </div>
                )}
                <div className="comment-form">
                  <input
                    type="text"
                    className="post-box-input"
                    placeholder="Write a comment..."
                    value={commentInputs[post.id] || ''}
                    onChange={(e) => handleCommentChange(post.id, e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        e.preventDefault();
                        handleAddComment(post.id);
                      }
                    }}
                  />
                  <button
                    type="button"
                    className="post-button"
                    onClick={() => handleAddComment(post.id)}
                    disabled={!((commentInputs[post.id] || '').trim())}
                  >
                    Comment
                  </button>
                </div>
              </div>
            </div>
          );
        })
      )}
    </div>
  );
};

export default PostFeed;

