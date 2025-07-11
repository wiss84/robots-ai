import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import './Auth.css';
import Navbar from '../components/Navbar';

const SignIn = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [rememberMe, setRememberMe] = useState(false);
  const navigate = useNavigate();
  const { user, supabase, signOut } = useAuth();
    // useEffect(() => {
    //     localStorage.clear(); // This goes here!
    //     console.log('localStorage cleared');
    //   }, []);
  // Load saved credentials only if 'rememberMe' was checked previously
  useEffect(() => {
    const savedRememberMe = localStorage.getItem('rememberMe') === 'true';
    if (savedRememberMe) {
      const savedEmail = localStorage.getItem('savedEmail') || '';
      const savedPassword = localStorage.getItem('savedPassword') || '';
      setEmail(savedEmail);
      setPassword(savedPassword);
      setRememberMe(true);
    } else {
      // Clear form if remember me is not checked
      setEmail('');
      setPassword('');
      setRememberMe(false);
    }
  }, []);

  useEffect(() => {
    const { data: { subscription } } = supabase.auth.onAuthStateChange((event, session) => {
      if (event === 'SIGNED_IN' && session?.user) {
        navigate('/');
      }
    });

    return () => subscription.unsubscribe();
  }, [navigate, supabase.auth]);

  const handleSignIn = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    if (!email || !password) {
      setError('Please enter both email and password');
      setLoading(false);
      return;
    }

    try {
      // Sign in with Supabase
      const { data, error } = await supabase.auth.signInWithPassword({
        email,
        password,
      });

      if (error) {
        setError(error.message);
      } else {
        // Only save credentials if "Remember Me" is checked
        if (rememberMe) {
          localStorage.setItem('savedEmail', email);
          localStorage.setItem('savedPassword', password);
          localStorage.setItem('rememberMe', 'true');
        } else {
          // Clear any previously saved credentials
          localStorage.removeItem('savedEmail');
          localStorage.removeItem('savedPassword');
          localStorage.setItem('rememberMe', 'false');
        }
        
        console.log('User signed in:', data.user);
      }
    } catch (err) {
      setError('An unexpected error occurred');
      console.error('Sign in error:', err);
    }

    setLoading(false);
  };

  // Clear credentials on sign out
  const handleSignOut = async () => {
    try {
      // Always clear saved credentials when signing out
      localStorage.removeItem('savedEmail');
      localStorage.removeItem('savedPassword');
      localStorage.setItem('rememberMe', 'false');
      
      // Sign out from Supabase
      await signOut();
      
      // Clear form fields
      setEmail('');
      setPassword('');
      setRememberMe(false);
      
      navigate('/signin');
    } catch (error) {
      console.error('Sign out error:', error);
    }
  };

  // If user is signed in, show signed in state
  if (user) {
    return (
      <>
        <Navbar />
        <div className="auth-container">
          <h2>You're Already Signed In!</h2>
          <p style={{ textAlign: 'center', color: '#ccc' }}>
            Welcome back, {user?.email}
          </p>
          <div style={{ display: 'flex', gap: '1rem', marginTop: '1rem' }}>
            <Link to="/" className="nav-button">
              Go to Homepage
            </Link>
            <button 
              className="signout-button" 
              onClick={handleSignOut}
            >
              Sign Out
            </button>
          </div>
        </div>
      </>
    );
  }

  return (
    <>
      <Navbar />
      <div className="auth-container">
        <h2>Sign In</h2>
        <form onSubmit={handleSignIn}>
          <div className="form-group">
            <label>Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              disabled={loading}
              placeholder="Enter your email"
            />
          </div>

          <div className="form-group">
            <label>Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={loading}
              placeholder="Enter your password"
            />
          </div>

          <div className="form-group remember-me">
            <input
              type="checkbox"
              id="rememberMe"
              checked={rememberMe}
              onChange={(e) => setRememberMe(e.target.checked)}
              disabled={loading}
            />
            <label htmlFor="rememberMe">Remember me</label>
          </div>

          {error && <p className="error">{error}</p>}
          
          <button type="submit" disabled={loading}>
            {loading ? 'Signing In...' : 'Sign In'}
          </button>
        </form>
        
        <p style={{ textAlign: 'center', marginTop: '1rem', color: '#ccc' }}>
          Don't have an account?{' '}
          <Link to="/signup" style={{ color: '#00bcd4', textDecoration: 'none' }}>
            Sign Up
          </Link>
        </p>
      </div>
    </>
  );
};

export default SignIn;