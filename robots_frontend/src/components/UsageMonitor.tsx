import React, { useState, useEffect } from 'react';

interface UsageStats {
  requestsToday: number;
  requestsThisHour: number;
  lastRequestTime: string;
}

const UsageMonitor: React.FC = () => {
  const [usageStats, setUsageStats] = useState<UsageStats>({
    requestsToday: 0,
    requestsThisHour: 0,
    lastRequestTime: ''
  });
  const [showWarning, setShowWarning] = useState(false);

  useEffect(() => {
    // Load usage stats from localStorage
    const savedStats = localStorage.getItem('usageStats');
    if (savedStats) {
      const stats = JSON.parse(savedStats);
      setUsageStats(stats);
    }

    // Check if we should show warning
    if (usageStats.requestsThisHour > 10) {
      setShowWarning(true);
    }
  }, []);

  const updateUsage = () => {
    const now = new Date();
    const today = now.toDateString();
    const currentHour = now.getHours();
    
    const savedStats = localStorage.getItem('usageStats');
    let stats: UsageStats = savedStats ? JSON.parse(savedStats) : {
      requestsToday: 0,
      requestsThisHour: 0,
      lastRequestTime: ''
    };

    // Reset daily count if it's a new day
    if (stats.lastRequestTime && new Date(stats.lastRequestTime).toDateString() !== today) {
      stats.requestsToday = 0;
    }

    // Reset hourly count if it's a new hour
    if (stats.lastRequestTime) {
      const lastHour = new Date(stats.lastRequestTime).getHours();
      if (lastHour !== currentHour) {
        stats.requestsThisHour = 0;
      }
    }

    // Increment counters
    stats.requestsToday += 1;
    stats.requestsThisHour += 1;
    stats.lastRequestTime = now.toISOString();

    // Save to localStorage
    localStorage.setItem('usageStats', JSON.stringify(stats));
    setUsageStats(stats);

    // Show warning if approaching limits
    if (stats.requestsThisHour > 8) {
      setShowWarning(true);
    }
  };

  // Expose updateUsage function globally
  useEffect(() => {
    (window as any).updateUsage = updateUsage;
    return () => {
      delete (window as any).updateUsage;
    };
  }, []);

  if (!showWarning) {
    return null;
  }

  return (
    <div style={{
      position: 'fixed',
      top: '20px',
      right: '20px',
      background: '#fff3cd',
      border: '1px solid #ffeaa7',
      borderRadius: '8px',
      padding: '1rem',
      maxWidth: '300px',
      zIndex: 1000,
      boxShadow: '0 4px 12px rgba(0,0,0,0.15)'
    }}>
      <h4 style={{ margin: '0 0 0.5rem 0', color: '#856404' }}>
        ⚠️ Usage Warning
      </h4>
      <p style={{ margin: '0 0 0.5rem 0', fontSize: '0.9rem', color: '#856404' }}>
        You've made {usageStats.requestsThisHour} requests this hour. 
        Consider taking a short break to avoid hitting API limits.
      </p>
      <button
        onClick={() => setShowWarning(false)}
        style={{
          background: 'transparent',
          border: '1px solid #856404',
          color: '#856404',
          padding: '0.25rem 0.5rem',
          borderRadius: '4px',
          cursor: 'pointer',
          fontSize: '0.8rem'
        }}
      >
        Dismiss
      </button>
    </div>
  );
};

export default UsageMonitor; 