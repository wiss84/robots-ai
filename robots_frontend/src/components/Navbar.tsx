import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import UserAvatar from './UserAvatar';
import './Navbar.css';

interface NavbarProps {
  showLogo?: boolean;
  logoText?: string;
  showHomeLink?: boolean;
  showAgentSelectionLink?: boolean;
  searchBox?: React.ReactNode;
}

const Navbar: React.FC<NavbarProps> = ({ 
  showLogo = true, 
  logoText = "Robots-AI",
  showHomeLink = true,
  showAgentSelectionLink = false,
  searchBox
}) => {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, loading, signOut } = useAuth();

  // Only show sign in/up or sign out on homepage
  const isHomePage = location.pathname === '/';
  const isChatUI = location.pathname.startsWith('/chat');
  const [theme, setTheme] = React.useState(() => localStorage.getItem('theme') || 'dark');

  // Keep theme in sync with localStorage
  React.useEffect(() => {
    document.body.classList.toggle('light-theme', theme === 'light');
    localStorage.setItem('theme', theme);
  }, [theme]);

  return (
    <nav className="navbar">
      <div className="navbar-left">
        {showLogo && (
          <div 
            className="logo" 
            onClick={() => navigate('/')}
          >
            {logoText}
          </div>
        )}
        {showHomeLink && (
          <button className="nav-link" onClick={() => navigate('/')}>Home</button>
        )}
        {showAgentSelectionLink && (
          <button className="nav-link" onClick={() => navigate('/agents')}>Agent Selection</button>
        )}
      </div>
      <div className="nav-actions">
        {searchBox}
        {loading ? (
          <div>Loading...</div>
        ) : user ? (
          <UserAvatar user={user} onSignOut={signOut} showThemeToggle={isChatUI} theme={theme} setTheme={setTheme} />
        ) : (
          isHomePage && (
            <>
              <button onClick={() => navigate('/signin')}>Sign In</button>
              <button onClick={() => navigate('/signup')}>Sign Up</button>
            </>
          )
        )}
      </div>
    </nav>
  );
};

export default Navbar;
