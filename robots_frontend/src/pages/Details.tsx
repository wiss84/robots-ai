import { useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { agentDescriptions } from '../data/AgentDescriptions';
import ReactMarkdown from 'react-markdown';
import './Details.css';
import Navbar from '../components/Navbar';

const Details = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const agent = location.state?.agent;

  useEffect(() => {
    if (!agent) {
      navigate('/agents', { replace: true });
    }
  }, [agent, navigate]);

  if (!agent) return null;

  const agentFolder = agent.id + '_agent';
  const greetingPosePath = `/avatars/${agentFolder}/greeting_pose.webp`;

  return (
    <>
      <Navbar showHomeLink={true} showAgentSelectionLink={false} />
      <div className="agent-detail-horizontal">
        <img
          src={greetingPosePath}
          className="agent-greeting-pose"
          alt={`${agent.name} greeting`}
        />
        <div className="agent-detail-info">
          <h2>{agent.name}</h2>
          <ReactMarkdown>
            {agentDescriptions[agent.id]}
          </ReactMarkdown>
          <div className="detail-buttons">
            <button onClick={() => navigate('/agents')}>Back</button>
            <button onClick={() => navigate(`/chat/${agent.id}`)}>Proceed</button>
          </div>
        </div>
      </div>
    </>
  );
};

export default Details;