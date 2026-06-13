import React from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import SidebarLeft from './SidebarLeft';
import SidebarRight from './SidebarRight';
import '../App.css';

const DashboardLayout = () => {
    const { user } = useAuth();
    
    // Some routes might need to hide the right sidebar to provide more space
    // e.g. recruiter dashboard or specific full-width views
    const isStudent = user && user.role === 'student';

    return (
        <div className="dashboard-container">
            <SidebarLeft />
            <Outlet />
            {isStudent && <SidebarRight />}
        </div>
    );
};

export default DashboardLayout;
