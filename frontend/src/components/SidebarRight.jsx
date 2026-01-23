import '../App.css';

const contests = [
  {
    id: '1',
    title: 'Weekly Coding Challenge',
    description: 'Solve 5 algorithmic problems',
    date: '2025-01-20',
    participants: 150,
  },
  {
    id: '2',
    title: 'Data Science Competition',
    description: 'Build a predictive model',
    date: '2025-01-25',
    participants: 75,
  },
  {
    id: '3',
    title: 'Frontend Development Contest',
    description: 'Create a responsive web app',
    date: '2025-02-01',
    participants: 200,
  },
];

const resources = [
  {
    title: 'React Documentation',
    description: 'Official React docs for learning hooks and components',
  },
  {
    title: 'Algorithm Practice',
    description: 'Practice coding problems on LeetCode and HackerRank',
  },
  {
    title: 'System Design Basics',
    description: 'Learn about scalable system architecture',
  },
];

const formatDate = (dateString) => {
  const date = new Date(dateString);
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
};

const SidebarRight = () => {
  return (
    <div className="sidebar-right">
      <div className="sidebar-section">
        <h2 className="sidebar-section-title">Weekly Contests</h2>
        {contests.map((contest) => (
          <div key={contest.id} className="contest-item">
            <div className="contest-title">{contest.title}</div>
            <div className="contest-description">{contest.description}</div>
            <div className="contest-date">Date: {formatDate(contest.date)}</div>
            <div className="contest-participants">
              {contest.participants} participants
            </div>
          </div>
        ))}
      </div>

      <div className="sidebar-section">
        <h2 className="sidebar-section-title">Recommended Resources</h2>
        {resources.map((resource, index) => (
          <div key={index} className="resource-item">
            <div className="resource-title">{resource.title}</div>
            <div className="resource-description">{resource.description}</div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default SidebarRight;
