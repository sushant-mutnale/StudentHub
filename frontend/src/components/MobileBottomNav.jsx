import React from 'react';
import { NavLink } from 'react-router-dom';
import { FiHome, FiSearch, FiMessageSquare, FiUser } from 'react-icons/fi';
import { useAuth } from '../contexts/AuthContext';
import './MobileBottomNav.css'; // We will create this

const MobileBottomNav = () => {
    const { user } = useAuth();

    if (!user) return null;

    const navItems = [
        { path: user.role === 'recruiter' ? '/dashboard/recruiter' : '/dashboard/student', icon: FiHome, label: 'Home' },
        { path: user.role === 'recruiter' ? '/recruiter/search' : '/learning', icon: FiSearch, label: 'Discover' },
        { path: '/messages', icon: FiMessageSquare, label: 'Messages' },
        { path: user.role === 'recruiter' ? '/profile/recruiter' : '/profile/student', icon: FiUser, label: 'Profile' },
    ];

    return (
        <nav className="mobile-bottom-nav">
            {navItems.map((item, index) => (
                <NavLink
                    key={index}
                    to={item.path}
                    className={({ isActive }) => `bottom-nav-item ${isActive ? 'active' : ''}`}
                >
                    <item.icon className="bottom-nav-icon" size={24} />
                    {/* Twitter usually relies solely on icons for the bottom nav, omitting text for clean UI */}
                </NavLink>
            ))}
        </nav>
    );
};

export default MobileBottomNav;
