import { useState, useEffect } from 'react'
import './AdminDashboard.css'

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api'
const API_TOKEN = import.meta.env.VITE_API_AUTH_TOKEN || ''

const getHeaders = (extraHeaders = {}) => {
  const headers = { ...extraHeaders }
  if (API_TOKEN) {
    headers['Authorization'] = `Bearer ${API_TOKEN}`
  }
  return headers
}

export default function AdminDashboard({ onClose }) {
  const [stats, setStats] = useState(null)
  const [orders, setOrders] = useState([])
  const [sessions, setSessions] = useState([])
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState('overview') // overview | sessions | orders

  useEffect(() => {
    fetchData()
  }, [])

  const fetchData = async () => {
    setLoading(true)
    try {
      // 1. Fetch Stats
      const statsRes = await fetch(`${API_BASE}/admin/stats`, { headers: getHeaders() })
      if (statsRes.ok) {
        const statsData = await statsRes.json()
        setStats(statsData)
      }

      // 2. Fetch Orders
      const ordersRes = await fetch(`${API_BASE}/admin/orders`, { headers: getHeaders() })
      if (ordersRes.ok) {
        const ordersData = await ordersRes.json()
        setOrders(ordersData.orders || [])
      }

      // 3. Fetch Sessions
      const sessionsRes = await fetch(`${API_BASE}/sessions`, { headers: getHeaders() })
      if (sessionsRes.ok) {
        const sessionsData = await sessionsRes.json()
        setSessions(sessionsData.sessions || [])
      }
    } catch (e) {
      console.error('Error fetching admin data:', e)
    } finally {
      setLoading(false)
    }
  }

  const handleDeleteSession = async (id) => {
    if (!window.confirm(`Are you sure you want to delete session ${id.substring(0, 8)}?`)) return
    try {
      const res = await fetch(`${API_BASE}/session/${id}`, { method: 'DELETE', headers: getHeaders() })
      if (res.ok) {
        alert('Session deleted successfully!')
        fetchData()
      }
    } catch (e) {
      console.error('Error deleting session:', e)
    }
  }

  const handleUpdateOrderStatus = async (orderId, newStatus) => {
    try {
      const res = await fetch(`${API_BASE}/admin/order/${orderId}/status`, {
        method: 'POST',
        headers: getHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify({ status: newStatus })
      })
      if (res.ok) {
        alert(`Order #${orderId} status updated to ${newStatus}`)
        fetchData()
      }
    } catch (e) {
      console.error('Error updating order status:', e)
    }
  }

  if (loading && !stats) {
    return (
      <div className="admin-dashboard-overlay">
        <div className="admin-dashboard-loading">
          <div className="spinner"></div>
          <p>Loading NovaMind Admin metrics...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="admin-dashboard-overlay">
      <div className="admin-dashboard-container">
        {/* Header */}
        <div className="admin-header">
          <div className="admin-header-title">
            <span className="admin-icon">⚙️</span>
            <h2>NovaMind Control Center</h2>
          </div>
          <button className="admin-close-btn" onClick={onClose}>✕ Close</button>
        </div>

        {/* Navigation Tabs */}
        <div className="admin-tabs">
          <button 
            className={`admin-tab-btn ${activeTab === 'overview' ? 'active' : ''}`}
            onClick={() => setActiveTab('overview')}
          >
            📊 Overview Metrics
          </button>
          <button 
            className={`admin-tab-btn ${activeTab === 'sessions' ? 'active' : ''}`}
            onClick={() => setActiveTab('sessions')}
          >
            💬 Active Sessions ({sessions.length})
          </button>
          <button 
            className={`admin-tab-btn ${activeTab === 'orders' ? 'active' : ''}`}
            onClick={() => setActiveTab('orders')}
          >
            📦 Order Repository ({orders.length})
          </button>
        </div>

        {/* Content Body */}
        <div className="admin-content">
          {activeTab === 'overview' && stats && (
            <div className="overview-tab">
              {/* Stat Cards */}
              <div className="stats-grid">
                <div className="stat-card">
                  <div className="stat-label">Total Conversations</div>
                  <div className="stat-value">{stats.total_sessions}</div>
                  <div className="stat-footer">Active in DB history</div>
                </div>
                <div className="stat-card">
                  <div className="stat-label">Total Messages Processed</div>
                  <div className="stat-value">{stats.total_messages}</div>
                  <div className="stat-footer">Conversational traffic</div>
                </div>
                <div className="stat-card">
                  <div className="stat-label">Avg. Messages per Chat</div>
                  <div className="stat-value">
                    {stats.total_sessions > 0 ? (stats.total_messages / stats.total_sessions).toFixed(1) : 0}
                  </div>
                  <div className="stat-footer">Engagement index</div>
                </div>
              </div>

              {/* Distributions */}
              <div className="distributions-grid">
                {/* Intent Distribution */}
                <div className="dist-card">
                  <h3>Intent Distribution</h3>
                  {Object.keys(stats.intent_distribution).length === 0 ? (
                    <p className="no-data">No messages processed yet.</p>
                  ) : (
                    <div className="bars-container">
                      {Object.entries(stats.intent_distribution).map(([intent, count]) => {
                        const maxCount = Math.max(...Object.values(stats.intent_distribution));
                        const pct = (count / maxCount) * 100;
                        return (
                          <div key={intent} className="bar-row">
                            <div className="bar-label">{intent}</div>
                            <div className="bar-wrapper">
                              <div className="bar-fill" style={{ width: `${pct}%` }}></div>
                              <span className="bar-value">{count}</span>
                            </div>
                          </div>
                        )
                      })}
                    </div>
                  )}
                </div>

                {/* Order Breakdown */}
                <div className="dist-card">
                  <h3>Order Status Breakdown</h3>
                  {Object.keys(stats.order_status_breakdown).length === 0 ? (
                    <p className="no-data">No orders tracked in DB.</p>
                  ) : (
                    <div className="bars-container">
                      {Object.entries(stats.order_status_breakdown).map(([status, count]) => {
                        const maxCount = Math.max(...Object.values(stats.order_status_breakdown));
                        const pct = (count / maxCount) * 100;
                        return (
                          <div key={status} className="bar-row">
                            <div className="bar-label">{status}</div>
                            <div className="bar-wrapper">
                              <div className="bar-fill orange" style={{ width: `${pct}%` }}></div>
                              <span className="bar-value">{count}</span>
                            </div>
                          </div>
                        )
                      })}
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}

          {activeTab === 'sessions' && (
            <div className="table-container">
              <div className="table-header-row">
                <h3>Active Customer Sessions</h3>
                <button className="refresh-btn" onClick={fetchData}>🔄 Refresh</button>
              </div>
              {sessions.length === 0 ? (
                <p className="no-data">No sessions found in the database.</p>
              ) : (
                <table className="admin-table">
                  <thead>
                    <tr>
                      <th>Session ID</th>
                      <th>First Query / Title</th>
                      <th>Time</th>
                      <th style={{ textAlign: 'right' }}>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sessions.map(s => (
                      <tr key={s.id}>
                        <td className="mono-text">{s.id.substring(0, 18)}...</td>
                        <td>{s.title}</td>
                        <td>{s.timestamp}</td>
                        <td style={{ textAlign: 'right' }}>
                          <button className="delete-row-btn" onClick={() => handleDeleteSession(s.id)}>
                            🗑️ Delete
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          )}

          {activeTab === 'orders' && (
            <div className="table-container">
              <div className="table-header-row">
                <h3>Order Fulfillment Center</h3>
                <button className="refresh-btn" onClick={fetchData}>🔄 Refresh</button>
              </div>
              {orders.length === 0 ? (
                <p className="no-data">No orders tracked in the database.</p>
              ) : (
                <table className="admin-table">
                  <thead>
                    <tr>
                      <th>Order ID</th>
                      <th>ETA</th>
                      <th>Fulfillment Status</th>
                      <th style={{ textAlign: 'right' }}>Update Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {orders.map(o => (
                      <tr key={o.order_id}>
                        <td className="mono-text font-bold">#{o.order_id}</td>
                        <td>{o.eta}</td>
                        <td>
                          <span className={`badge-status ${o.status.toLowerCase().replace(' ', '-')}`}>
                            {o.status}
                          </span>
                        </td>
                        <td style={{ textAlign: 'right' }}>
                          <select 
                            value={o.status}
                            onChange={(e) => handleUpdateOrderStatus(o.order_id, e.target.value)}
                            className="status-selector"
                          >
                            <option value="Processing">Processing</option>
                            <option value="In Transit">In Transit</option>
                            <option value="Shipped">Shipped</option>
                            <option value="Delivered">Delivered</option>
                            <option value="Cancelled">Cancelled</option>
                            <option value="Refunded">Refunded</option>
                          </select>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
