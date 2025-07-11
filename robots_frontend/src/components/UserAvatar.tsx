import React, { useState, useRef, useEffect } from 'react';
import type { User } from '@supabase/supabase-js';

interface UserAvatarProps {
  user: User;
  onSignOut: () => void;
  showThemeToggle?: boolean;
  theme?: string;
  setTheme?: (theme: string) => void;
}

const UserAvatar: React.FC<UserAvatarProps> = ({ user, onSignOut, showThemeToggle = false, theme, setTheme }) => {
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Get user initials from metadata
  const getInitials = () => {
    const firstName = user.user_metadata?.first_name || '';
    const lastName = user.user_metadata?.last_name || '';
    
    if (firstName && lastName) {
      return `${firstName.charAt(0).toUpperCase()}${lastName.charAt(0).toUpperCase()}`;
    }
    
    // Fallback to email initials if no first/last name
    const email = user.email || '';
    const emailParts = email.split('@')[0];
    return emailParts.slice(0, 2).toUpperCase();
  };

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsDropdownOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSignOut = () => {
    setIsDropdownOpen(false);
    onSignOut();
  };

  return (
    <div className="user-avatar-wrapper" ref={dropdownRef}>
      <div
        className="user-avatar"
        onClick={() => setIsDropdownOpen((open) => !open)}
        style={{ cursor: 'pointer' }}
      >
        {getInitials()}
      </div>
      {isDropdownOpen && (
        <div className="user-dropdown">
          <div className="user-email">{user.email}</div>
          {showThemeToggle && setTheme && (
            <button
              className="theme-toggle-btn"
              style={{ width: '100%', margin: '10px 0', fontSize: 18, color: '#00bcd4', background: 'none', border: 'none', cursor: 'pointer' }}
              onClick={() => setTheme(theme === 'light' ? 'dark' : 'light')}
            >
              {theme === 'light' ? '🌙 Dark Mode' : '☀️ Light Mode'}
            </button>
          )}
          <button className="signout-btn" style={{ color: 'red', width: '100%', marginTop: 8 }} onClick={handleSignOut}>
            Sign Out
          </button>
        </div>
      )}
    </div>
  );
};

export default UserAvatar;
