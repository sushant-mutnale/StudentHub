import '../App.css';

const Avatar = ({ src, alt, size = 40, className = '' }) => {
  const sizeStyle = {
    width: `${size}px`,
    height: `${size}px`,
    minWidth: `${size}px`,
    minHeight: `${size}px`,
  };

  if (src) {
    return (
      <img
        src={src}
        alt={alt || 'Avatar'}
        className={`avatar ${className}`}
        style={sizeStyle}
      />
    );
  }

  // Default placeholder with initial
  const initial = alt ? alt.charAt(0).toUpperCase() : '?';
  return (
    <div
      className={`avatar avatar-placeholder ${className}`}
      style={sizeStyle}
      title={alt || 'User'}
    >
      {initial}
    </div>
  );
};

export default Avatar;







