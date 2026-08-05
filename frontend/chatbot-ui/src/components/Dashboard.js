import React, { useEffect, useState } from 'react';
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts';
import { MessageSquare, Users, Activity, BarChart2 } from 'lucide-react';
import './Dashboard.css';

const Dashboard = () => {
  const [stats, setStats] = useState(null);

  useEffect(() => {
    // In a real app, use an environment variable for the API base URL
    fetch('http://localhost:5000/api/dashboard/stats', {
      headers: {
        'X-API-Key': 'chatbot-secure-key-2026'
      }
    })
      .then(res => res.json())
      .then(data => setStats(data))
      .catch(err => console.error("Error fetching dashboard stats", err));
  }, []);

  const COLORS = ['#8A2BE2', '#FF69B4', '#00CED1', '#FFD700', '#FF7F50', '#7FFF00', '#DDA0DD'];

  if (!stats) return <div className="dashboard-loading">Loading Dashboard...</div>;

  return (
    <div className="dashboard-container">
      <h1 className="dashboard-title">System Overview</h1>
      
      <div className="stats-grid">
        <div className="stat-card glass-card">
          <div className="stat-icon"><Users size={24} /></div>
          <div className="stat-info">
            <h3>Total Sessions</h3>
            <p>{stats.total_sessions}</p>
          </div>
        </div>
        <div className="stat-card glass-card">
          <div className="stat-icon"><MessageSquare size={24} /></div>
          <div className="stat-info">
            <h3>Total Messages</h3>
            <p>{stats.total_messages}</p>
          </div>
        </div>
        <div className="stat-card glass-card">
          <div className="stat-icon"><Activity size={24} /></div>
          <div className="stat-info">
            <h3>Active Rate</h3>
            <p>98.5%</p>
          </div>
        </div>
        <div className="stat-card glass-card">
          <div className="stat-icon"><BarChart2 size={24} /></div>
          <div className="stat-info">
            <h3>Resolution</h3>
            <p>87%</p>
          </div>
        </div>
      </div>

      <div className="charts-container">
        <div className="chart-card glass-card">
          <h3>Intent Distribution</h3>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={stats.intents_distribution}
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={100}
                paddingAngle={5}
                dataKey="value"
                nameKey="name"
              >
                {stats.intents_distribution.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>

        <div className="activity-card glass-card">
          <h3>Recent Activity</h3>
          <ul className="activity-list">
            {stats.recent_activity.map((act, i) => (
              <li key={i} className="activity-item">
                <span className="activity-intent">{act.intent}</span>
                <span className="activity-text">"{act.user}"</span>
                <span className="activity-time">{new Date(act.time).toLocaleTimeString()}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
