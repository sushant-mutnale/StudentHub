import React from 'react';
import { Outlet } from 'react-router-dom';
import SidebarLeft from './SidebarLeft';
import '../App.css';

const DashboardLayout = () => {
    return (
        <div className="dashboard-container">
            <SidebarLeft />
            <Outlet />
        </div>
    );
};

export default DashboardLayout;
