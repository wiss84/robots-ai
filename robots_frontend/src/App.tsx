import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import HomePage from './pages/HomePage';
import SignIn from './pages/SignIn';
import SignUp from './pages/SignUp';
import AgentSelection from './pages/AgentSelection';
import Details from './pages/Details';
import ChatUI from './pages/ChatUI';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/signin" element={<SignIn />} />
        <Route path="/signup" element={<SignUp />} />
        <Route path="/agents" element={<AgentSelection />} />
        <Route path="/details" element={<Details />} />
        <Route path="/chat/:agentId" element={<ChatUI />} />
      </Routes>
    </Router>
  );
}

export default App;