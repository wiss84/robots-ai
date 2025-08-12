import React, { useState, useRef, useEffect } from 'react';
import type { User } from '@supabase/supabase-js';
import { createPortal } from 'react-dom';
import './UserAvatar.css';

interface UserAvatarProps {
  user: User;
  onSignOut: () => void;
  showThemeToggle?: boolean;
  theme?: string;
  setTheme?: (theme: string) => void;
}

const UserAvatar: React.FC<UserAvatarProps> = ({ user, onSignOut, showThemeToggle = false, theme, setTheme }) => {
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const [dropdownPos, setDropdownPos] = useState<{ top: number; left: number } | null>(null);
  const avatarRef = useRef<HTMLDivElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Get user initials from metadata
  const getInitials = () => {
    const firstName = user.user_metadata?.first_name || '';
    const lastName = user.user_metadata?.last_name || '';
    if (firstName && lastName) {
      return `${firstName.charAt(0).toUpperCase()}${lastName.charAt(0).toUpperCase()}`;
    }
    const email = user.email || '';
    const emailParts = email.split('@')[0];
    return emailParts.slice(0, 2).toUpperCase();
  };

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node) &&
        avatarRef.current &&
        !avatarRef.current.contains(event.target as Node)
      ) {
        setIsDropdownOpen(false);
      }
    };
    if (isDropdownOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    } else {
      document.removeEventListener('mousedown', handleClickOutside);
    }
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isDropdownOpen]);

  const handleSignOut = () => {
    setIsDropdownOpen(false);
    onSignOut();
  };

  // Calculate dropdown position when opening
  useEffect(() => {
    if (isDropdownOpen && avatarRef.current) {
      const rect = avatarRef.current.getBoundingClientRect();
      setDropdownPos({
        top: rect.bottom + window.scrollY + 8, // 8px gap
        left: rect.right - 180, // align right edge, 180px min width
      });
    }
  }, [isDropdownOpen]);

  return (
    <div className="user-avatar-wrapper" ref={avatarRef}>
      <div
        className="user-avatar user-avatar-button"
        onClick={() => setIsDropdownOpen((open) => !open)}
      >
        {getInitials()}
      </div>
      {isDropdownOpen && dropdownPos && createPortal(
        <div
          className="user-dropdown user-dropdown-portal user-avatar-menu"
          ref={dropdownRef}
          style={{
            top: dropdownPos.top,
            left: dropdownPos.left
          }}
        >
          <div className="user-email">{user.email}</div>
          {showThemeToggle && setTheme && (
            <button
              className="theme-toggle-btn user-menu-button"
              onClick={() => setTheme(theme === 'light' ? 'dark' : 'light')}
            >
              {theme === 'light' ? '🌙 Dark Mode' : '☀️ Light Mode'}
            </button>
          )}
          <button className="signout-btn" onClick={handleSignOut}>
            Sign Out
          </button>
        </div>,
        document.body
      )}
    </div>
  );
};

export default UserAvatar;
