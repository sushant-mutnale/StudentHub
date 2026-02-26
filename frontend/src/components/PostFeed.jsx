import { useEffect, useState, useRef } from 'react';
import { Link } from 'react-router-dom';
import { FiEdit3, FiHeart, FiMoreVertical, FiTrash2, FiMessageSquare, FiSend, FiLoader, FiTag } from 'react-icons/fi';
import { useAuth } from '../contexts/AuthContext';
import { postService } from '../services/postService';
import Avatar from './Avatar';
import '../App.css';
import './PostFeed.css';

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
  const [activeCommentPostId, setActiveCommentPostId] = useState(null);
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
    const now = new Date();
    const diff = (now - date) / 1000; // seconds

    if (diff < 60) return 'Just now';
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    if (diff < 604800) return `${Math.floor(diff / 86400)}d ago`;

    return date.toLocaleDateString();
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

  if (loading && posts.length === 0) {
    return (
      <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--color-text-muted)' }}>
        <FiLoader className="animate-spin" size={24} style={{ marginBottom: '1rem' }} />
        <p>Loading your feed...</p>
      </div>
    );
  }

  if (error && posts.length === 0) {
    return (
      <div style={{
        padding: '1.5rem',
        background: 'rgba(239, 68, 68, 0.1)',
        borderRadius: 'var(--radius-lg)',
        color: 'var(--color-danger)',
        textAlign: 'center'
      }}>
        {error}
        <button
          onClick={loadPosts}
          style={{
            display: 'block',
            margin: '1rem auto 0',
            padding: '0.5rem 1rem',
            background: 'white',
            border: '1px solid var(--color-danger)',
            borderRadius: 'var(--radius-md)',
            color: 'var(--color-danger)',
            cursor: 'pointer'
          }}
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="post-feed" style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {posts.length === 0 ? (
        <div style={{
          textAlign: 'center',
          padding: '4rem 2rem',
          background: 'rgba(255,255,255,0.5)',
          backdropFilter: 'blur(10px)',
          borderRadius: 'var(--radius-lg)',
          color: 'var(--color-text-muted)'
        }}>
          <div style={{
            width: '64px',
            height: '64px',
            background: 'var(--color-bg-alt)',
            borderRadius: '50%',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            margin: '0 auto 1.5rem auto'
          }}>
            <FiMessageSquare size={32} style={{ opacity: 0.5 }} />
          </div>
          <h3>No posts yet</h3>
          <p>Be the first to share something with the community!</p>
        </div>
      ) : (
        posts.map((post, idx) => {
          const liked = user ? post.likes?.includes(user.id) : false;
          const isMenuOpen = openMenuId === post.id;

          return (
            <div
              key={post.id}
              className="glass-card animate-fade-in-up"
              style={{
                padding: '1.5rem',
                borderRadius: 'var(--radius-lg)',
                animationDelay: `${idx * 100}ms`
              }}
            >
              {/* Post Header */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                  <Link to={`/profile/${post.author_id}`} className="hover-scale">
                    <Avatar
                      src={post.author_avatar_url}
                      alt={post.author_name}
                      size={48}
                      style={{ border: '2px solid white', boxShadow: 'var(--shadow-sm)' }}
                    />
                  </Link>
                  <div>
                    <Link
                      to={`/profile/${post.author_id}`}
                      style={{
                        textDecoration: 'none',
                        color: 'var(--color-text)',
                        fontWeight: '700',
                        fontSize: '1.05rem',
                        display: 'block'
                      }}
                    >
                      {post.author_name}
                    </Link>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.85rem', color: 'var(--color-text-muted)' }}>
                      <span>@{post.author_username}</span>
                      <span>•</span>
                      <span>{formatTimestamp(post.created_at || post.updated_at)}</span>
                    </div>
                  </div>
                </div>

                {canManagePost(post) && (
                  <div className="post-menu-container" ref={menuRef} style={{ position: 'relative' }}>
                    <button
                      className="btn-icon hover-scale"
                      onClick={() => toggleMenu(post.id)}
                      style={{
                        background: isMenuOpen ? 'var(--color-bg-alt)' : 'transparent',
                        color: 'var(--color-text-muted)'
                      }}
                    >
                      <FiMoreVertical size={20} />
                    </button>
                    {isMenuOpen && (
                      <div className="glass-panel animate-scale-in" style={{
                        position: 'absolute',
                        top: '100%',
                        right: 0,
                        width: '150px',
                        background: 'white',
                        padding: '0.5rem',
                        borderRadius: 'var(--radius-md)',
                        boxShadow: 'var(--shadow-lg)',
                        zIndex: 10,
                        marginTop: '0.5rem'
                      }}>
                        <button
                          onClick={() => handleEdit(post)}
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.75rem',
                            width: '100%',
                            padding: '0.75rem',
                            border: 'none',
                            background: 'transparent',
                            textAlign: 'left',
                            cursor: 'pointer',
                            borderRadius: 'var(--radius-sm)',
                            color: 'var(--color-text)',
                            transition: 'var(--transition-fast)'
                          }}
                          onMouseEnter={(e) => e.currentTarget.style.background = 'var(--color-bg-alt)'}
                          onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                        >
                          <FiEdit3 size={16} /> Edit
                        </button>
                        <button
                          onClick={() => handleDelete(post.id)}
                          style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '0.75rem',
                            width: '100%',
                            padding: '0.75rem',
                            border: 'none',
                            background: 'transparent',
                            textAlign: 'left',
                            cursor: 'pointer',
                            borderRadius: 'var(--radius-sm)',
                            color: 'var(--color-danger)',
                            transition: 'var(--transition-fast)'
                          }}
                          onMouseEnter={(e) => e.currentTarget.style.background = 'rgba(239, 68, 68, 0.1)'}
                          onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                        >
                          <FiTrash2 size={16} /> Delete
                        </button>
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Post Content */}
              {editingPostId === post.id ? (
                <div className="animate-fade-in" style={{
                  background: 'var(--color-bg-alt)',
                  padding: '1rem',
                  borderRadius: 'var(--radius-md)',
                  marginBottom: '1rem'
                }}>
                  <textarea
                    value={editContent}
                    onChange={(e) => setEditContent(e.target.value)}
                    rows="4"
                    style={{
                      width: '100%',
                      border: '1px solid var(--color-border)',
                      borderRadius: 'var(--radius-sm)',
                      padding: '0.75rem',
                      fontFamily: 'inherit',
                      fontSize: '1rem',
                      marginBottom: '1rem',
                      outline: 'none'
                    }}
                  />
                  <input
                    type="text"
                    value={editTags}
                    onChange={(e) => setEditTags(e.target.value)}
                    placeholder="Tags (comma separated)"
                    style={{
                      width: '100%',
                      border: '1px solid var(--color-border)',
                      borderRadius: 'var(--radius-sm)',
                      padding: '0.75rem',
                      fontFamily: 'inherit',
                      marginBottom: '1rem',
                      outline: 'none'
                    }}
                  />
                  <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem' }}>
                    <button
                      onClick={cancelEditing}
                      style={{
                        padding: '0.5rem 1rem',
                        border: '1px solid var(--color-border)',
                        background: 'white',
                        borderRadius: 'var(--radius-md)',
                        cursor: 'pointer'
                      }}
                    >
                      Cancel
                    </button>
                    <button
                      onClick={saveEdit}
                      className="btn-glow"
                      style={{
                        padding: '0.5rem 1.5rem',
                        border: 'none',
                        background: 'var(--gradient-primary)',
                        color: 'white',
                        borderRadius: 'var(--radius-md)',
                        cursor: 'pointer',
                        fontWeight: '600'
                      }}
                    >
                      Save Changes
                    </button>
                  </div>
                </div>
              ) : (
                <>
                  <div style={{
                    color: 'var(--color-text)',
                    fontSize: '1.05rem',
                    lineHeight: '1.6',
                    marginBottom: '1rem',
                    whiteSpace: 'pre-wrap'
                  }}>
                    {post.content}
                  </div>
                  {post.tags?.length > 0 && (
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', marginBottom: '1.5rem' }}>
                      {post.tags.map((tag) => (
                        <span key={tag} style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '0.25rem',
                          padding: '0.35rem 0.85rem',
                          background: 'rgba(102, 126, 234, 0.1)',
                          color: 'var(--color-primary)',
                          borderRadius: 'var(--radius-full)',
                          fontSize: '0.85rem',
                          fontWeight: '500'
                        }}>
                          <FiTag size={12} /> {tag}
                        </span>
                      ))}
                    </div>
                  )}
                </>
              )}

              {/* Actions Divider */}
              <div style={{ height: '1px', background: 'var(--color-border-light)', marginBottom: '1rem' }} />

              {/* Interaction Buttons */}
              <div style={{ display: 'flex', gap: '1.5rem' }}>
                <button
                  onClick={() => toggleLike(post.id)}
                  className="hover-lift"
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.5rem',
                    background: 'transparent',
                    border: 'none',
                    padding: '0.5rem',
                    borderRadius: 'var(--radius-md)',
                    cursor: 'pointer',
                    color: liked ? 'var(--color-danger)' : 'var(--color-text-muted)',
                    fontWeight: liked ? '600' : '500',
                    transition: 'var(--transition-fast)'
                  }}
                >
                  <FiHeart size={20} fill={liked ? 'currentColor' : 'none'} />
                  <span>{post.likes?.length || 0}</span>
                  <span className="hide-on-mobile">Likes</span>
                </button>

                <button
                  onClick={() => setActiveCommentPostId(activeCommentPostId === post.id ? null : post.id)}
                  className="hover-lift"
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '0.5rem',
                    background: 'transparent',
                    border: 'none',
                    padding: '0.5rem',
                    borderRadius: 'var(--radius-md)',
                    cursor: 'pointer',
                    color: activeCommentPostId === post.id ? 'var(--color-primary)' : 'var(--color-text-muted)',
                    fontWeight: '500',
                    transition: 'var(--transition-fast)'
                  }}
                >
                  <FiMessageSquare size={20} />
                  <span>{post.comments?.length || 0}</span>
                  <span className="hide-on-mobile">Comments</span>
                </button>
              </div>

              {/* Comments Section */}
              {(activeCommentPostId === post.id || (post.comments && post.comments.length > 0 && activeCommentPostId === post.id)) && (
                <div className="animate-fade-in" style={{ marginTop: '1.5rem' }}>
                  <div style={{
                    background: 'var(--color-bg-alt)',
                    borderRadius: 'var(--radius-lg)',
                    padding: '1rem',
                    marginBottom: '1rem'
                  }}>
                    {post.comments && post.comments.length > 0 ? (
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', marginBottom: '1rem' }}>
                        {post.comments.map((comment) => (
                          <div key={comment.id} style={{ display: 'flex', gap: '0.75rem' }}>
                            <div style={{
                              width: '32px',
                              height: '32px',
                              background: 'var(--color-border)',
                              borderRadius: '50%',
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'center',
                              fontSize: '0.8rem',
                              color: 'var(--color-text-muted)',
                              fontWeight: '600'
                            }}>
                              {(comment.author_name || 'U')[0]}
                            </div>
                            <div style={{
                              flex: 1,
                              background: 'white',
                              padding: '0.75rem 1rem',
                              borderRadius: '0 12px 12px 12px',
                              boxShadow: 'var(--shadow-sm)'
                            }}>
                              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.25rem' }}>
                                <span style={{ fontWeight: '600', fontSize: '0.9rem' }}>{comment.author_name || 'User'}</span>
                                <span style={{ fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>{formatTimestamp(comment.created_at)}</span>
                              </div>
                              <div style={{ fontSize: '0.95rem', color: 'var(--color-text)' }}>{comment.text}</div>
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div style={{ textAlign: 'center', padding: '1rem', color: 'var(--color-text-muted)', fontSize: '0.9rem' }}>
                        No comments yet. Be the first to share your thoughts!
                      </div>
                    )}
                  </div>

                  {/* Add Comment Input */}
                  <div style={{ display: 'flex', gap: '0.75rem' }}>
                    <input
                      type="text"
                      placeholder="Write a comment..."
                      value={commentInputs[post.id] || ''}
                      onChange={(e) => handleCommentChange(post.id, e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') {
                          e.preventDefault();
                          handleAddComment(post.id);
                        }
                      }}
                      style={{
                        flex: 1,
                        padding: '0.75rem 1rem',
                        borderRadius: 'var(--radius-full)',
                        border: '1px solid var(--color-border)',
                        outline: 'none',
                        fontSize: '0.95rem',
                        transition: 'var(--transition-fast)'
                      }}
                    />
                    <button
                      onClick={() => handleAddComment(post.id)}
                      disabled={!((commentInputs[post.id] || '').trim())}
                      className="btn-icon"
                      style={{
                        width: '42px',
                        height: '42px',
                        borderRadius: '50%',
                        background: (commentInputs[post.id] || '').trim() ? 'var(--gradient-primary)' : 'var(--color-bg-alt)',
                        color: (commentInputs[post.id] || '').trim() ? 'white' : 'var(--color-text-muted)',
                        border: 'none',
                        cursor: (commentInputs[post.id] || '').trim() ? 'pointer' : 'default',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        transition: 'var(--transition-normal)'
                      }}
                    >
                      <FiSend size={18} />
                    </button>
                  </div>
                </div>
              )}
            </div>
          );
        })
      )}
    </div>
  );
};

export default PostFeed;
