import React from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import Navbar from '../components/Navbar';
import './HomePage.css';

const HomePage = () => {
  const navigate = useNavigate();
  const { loading } = useAuth();

  // Show loading state while checking authentication
  if (loading) {
    return (
      <div className="homepage">
        <Navbar showAgentSelectionLink={true} showHomeLink={true} />
        <main className="welcome-section">
          <h1>Welcome to Robots-AI</h1>
          <p>Choose your assistant from our intelligent agents</p>
          <button disabled>Loading...</button>
        </main>
      </div>
    );
  }

  return (
    <div className="homepage">
      <Navbar showAgentSelectionLink={true} showHomeLink={true} />
      <main className="welcome-section">
        <h1>Welcome to Robots-AI</h1>
        <p>Choose your assistant from our intelligent agents</p>
        <button onClick={() => navigate('/agents')}>Choose Your Agent</button>
      </main>
    </div>
  );
};

export default HomePage;