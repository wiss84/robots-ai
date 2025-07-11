import React, { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import './Auth.css';
import Navbar from '../components/Navbar';

const SignUp = () => {
  const [form, setForm] = useState({
    firstName: '',
    lastName: '',
    day: '',
    month: '',
    year: '',
    email: '',
    password: '',
    confirmPassword: ''
  });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState('');
  const navigate = useNavigate();
  const { user, supabase, signOut } = useAuth();

  // Clear form fields on mount and ensure no saved credentials are displayed
  useEffect(() => {
    setForm({
      firstName: '', 
      lastName: '', 
      day: '', 
      month: '', 
      year: '',
      email: '', 
      password: '', 
      confirmPassword: ''
    });
  }, []);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  const handleSignUp = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    setLoading(true);

    // Validation
    if (!form.firstName || !form.lastName || !form.email || !form.password || !form.confirmPassword) {
      setError('Please fill in all required fields');
      setLoading(false);
      return;
    }
    
    if (form.password !== form.confirmPassword) {
      setError('Passwords do not match');
      setLoading(false);
      return;
    }

    if (form.password.length < 6) {
      setError('Password must be at least 6 characters long');
      setLoading(false);
      return;
    }

    // Create date of birth if provided
    let dateOfBirth = null;
    if (form.day && form.month && form.year) {
      dateOfBirth = `${form.year}-${form.month.padStart(2, '0')}-${form.day.padStart(2, '0')}`;
    }

    try {
      const { error } = await supabase.auth.signUp({
        email: form.email,
        password: form.password,
        options: {
          data: {
            first_name: form.firstName,
            last_name: form.lastName,
            date_of_birth: dateOfBirth,
          }
        }
      });

      if (error) {
        setError(error.message);
      } else {
        setSuccess('Account created successfully! Please check your email to verify your account.');
        
        // Clear form after successful signup
        setForm({
          firstName: '', 
          lastName: '', 
          day: '', 
          month: '', 
          year: '',
          email: '', 
          password: '', 
          confirmPassword: ''
        });
        
        // Ensure no credentials are saved for the new account
        localStorage.removeItem('savedEmail');
        localStorage.removeItem('savedPassword');
        localStorage.setItem('rememberMe', 'false');
        
        // Redirect to sign-in after 2 seconds
        setTimeout(() => {
          navigate('/signin');
        }, 2000);
      }
    } catch (err) {
      setError('An unexpected error occurred');
      console.error('Sign up error:', err);
    }

    setLoading(false);
  };

  // Clear credentials and sign out
  const handleSignOut = async () => {
    try {
      // Always clear saved credentials when signing out
      localStorage.removeItem('savedEmail');
      localStorage.removeItem('savedPassword');
      localStorage.setItem('rememberMe', 'false');
      
      // Sign out from Supabase
      await signOut();
      
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
            Welcome, {user.email}
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
        <h2>Sign Up</h2>
        <form onSubmit={handleSignUp}>
          <div className="form-group">
            <label>First Name *</label>
            <input 
              name="firstName" 
              value={form.firstName} 
              onChange={handleChange}
              disabled={loading}
              placeholder="Enter your first name"
            />
          </div>

          <div className="form-group">
            <label>Last Name *</label>
            <input 
              name="lastName" 
              value={form.lastName} 
              onChange={handleChange}
              disabled={loading}
              placeholder="Enter your last name"
            />
          </div>

          <div className="form-group">
            <label>Date of Birth (Optional)</label>
            <div className="dob-group">
              <div className="dob-input day">
                <input 
                  name="day" 
                  type="number" 
                  placeholder="DD" 
                  min="1" 
                  max="31"
                  value={form.day} 
                  onChange={handleChange}
                  disabled={loading}
                />
              </div>
              <div className="dob-input month">
                <input 
                  name="month" 
                  type="number" 
                  placeholder="MM" 
                  min="1" 
                  max="12"
                  value={form.month} 
                  onChange={handleChange}
                  disabled={loading}
                />
              </div>
              <div className="dob-input year">
                <input 
                  name="year" 
                  type="number" 
                  placeholder="YYYY" 
                  min="1900" 
                  max="2024"
                  value={form.year} 
                  onChange={handleChange}
                  disabled={loading}
                />
              </div>
            </div>
          </div>

          <div className="form-group">
            <label>Email *</label>
            <input 
              name="email" 
              type="email" 
              value={form.email} 
              onChange={handleChange}
              disabled={loading}
              placeholder="Enter your email"
            />
          </div>

          <div className="form-group">
            <label>Password * (min 6 characters)</label>
            <input 
              name="password" 
              type="password" 
              value={form.password} 
              onChange={handleChange}
              disabled={loading}
              placeholder="Enter your password"
            />
          </div>

          <div className="form-group">
            <label>Confirm Password *</label>
            <input 
              name="confirmPassword" 
              type="password" 
              value={form.confirmPassword} 
              onChange={handleChange}
              disabled={loading}
              placeholder="Confirm your password"
            />
          </div>

          {error && <p className="error">{error}</p>}
          {success && <p className="success">{success}</p>}
          
          <button type="submit" disabled={loading}>
            {loading ? 'Creating Account...' : 'Sign Up'}
          </button>
        </form>
        
        <p style={{ textAlign: 'center', marginTop: '1rem', color: '#ccc' }}>
          Already have an account?{' '}
          <Link to="/signin" style={{ color: '#00bcd4', textDecoration: 'none' }}>
            Sign In
          </Link>
        </p>
      </div>
    </>
  );
};

export default SignUp;