import { FiCalendar, FiUsers, FiBookOpen, FiCode, FiLayers, FiTrendingUp } from 'react-icons/fi';
import '../App.css';

const contests = [
  {
    id: '1',
    title: 'Weekly Coding Challenge',
    category: 'Algorithms',
    date: '2025-01-20',
    participants: 150,
    icon: FiCode,
    color: '#3b82f6'
  },
  {
    id: '2',
    title: 'Data Science Sprint',
    category: 'Data Science',
    date: '2025-01-25',
    participants: 75,
    icon: FiTrendingUp,
    color: '#8b5cf6'
  },
  {
    id: '3',
    title: 'UI/UX Design Battle',
    category: 'Design',
    date: '2025-02-01',
    participants: 200,
    icon: FiLayers,
    color: '#ec4899'
  },
];

const resources = [
  {
    title: 'React Documentation',
    description: 'Official docs for modern React',
    link: 'https://react.dev'
  },
  {
    title: 'System Design Primer',
    description: 'Learn scalable architecture',
    link: '#'
  },
  {
    title: 'Interview Handbook',
    description: 'Curated interview prep guide',
    link: '#'
  },
];

const formatDate = (dateString) => {
  const date = new Date(dateString);
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
};

const SidebarRight = () => {
  return (
    <div className="sidebar-right animate-fade-in-left">
      {/* Contests Section */}
      <div className="glass-card" style={{
        padding: '1.5rem',
        borderRadius: 'var(--radius-lg)',
        marginBottom: '1.5rem',
        border: '1px solid rgba(255,255,255,0.6)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1.25rem' }}>
          <h3 style={{ fontSize: '1.1rem', fontWeight: '700', color: 'var(--color-text)', margin: 0 }}>
            Upcoming Contests
          </h3>
          <span style={{ fontSize: '0.8rem', color: 'var(--color-primary)', fontWeight: '600', cursor: 'pointer' }}>View All</span>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {contests.map((contest, idx) => {
            const Icon = contest.icon;
            return (
              <div key={contest.id} className="interactive-card" style={{
                padding: '0.75rem',
                borderRadius: 'var(--radius-md)',
                background: 'rgba(255, 255, 255, 0.5)',
                transition: 'var(--transition-normal)'
              }}>
                <div style={{ display: 'flex', gap: '0.75rem' }}>
                  <div style={{
                    width: '36px',
                    height: '36px',
                    borderRadius: '10px',
                    background: `${contest.color}15`,
                    color: contest.color,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    flexShrink: 0
                  }}>
                    <Icon size={18} />
                  </div>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontWeight: '600', fontSize: '0.9rem', marginBottom: '0.2rem', color: 'var(--color-text)' }}>
                      {contest.title}
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>
                      <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                        <FiCalendar size={12} /> {formatDate(contest.date)}
                      </span>
                      <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                        <FiUsers size={12} /> {contest.participants}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Suggested Resources Section */}
      <div className="glass-card" style={{
        padding: '1.5rem',
        borderRadius: 'var(--radius-lg)',
        border: '1px solid rgba(255,255,255,0.6)'
      }}>
        <h3 style={{ fontSize: '1.1rem', fontWeight: '700', color: 'var(--color-text)', margin: '0 0 1.25rem 0' }}>
          Learning Resources
        </h3>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
          {resources.map((resource, index) => (
            <a
              key={index}
              href={resource.link}
              className="hover-lift"
              style={{
                display: 'flex',
                alignItems: 'start',
                gap: '0.75rem',
                padding: '0.75rem',
                borderRadius: 'var(--radius-md)',
                textDecoration: 'none',
                color: 'inherit',
                transition: 'var(--transition-fast)'
              }}
            >
              <div style={{ mt: '3px', color: 'var(--color-primary)' }}>
                <FiBookOpen size={18} />
              </div>
              <div>
                <div style={{ fontWeight: '600', fontSize: '0.9rem', color: 'var(--color-text)' }}>
                  {resource.title}
                </div>
                <div style={{ fontSize: '0.8rem', color: 'var(--color-text-secondary)', lineHeight: '1.4' }}>
                  {resource.description}
                </div>
              </div>
            </a>
          ))}
        </div>

        <button className="btn-ghost" style={{
          width: '100%',
          marginTop: '0.5rem',
          fontSize: '0.85rem',
          fontWeight: '600',
          color: 'var(--color-primary)'
        }}>
          Explore More Resources
        </button>
      </div>
    </div>
  );
};

export default SidebarRight;
