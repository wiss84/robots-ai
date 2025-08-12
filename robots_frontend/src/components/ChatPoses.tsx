import React from 'react';
import './ChatPoses.css';

interface ChatPosesProps {
  agentId?: string;
  pose: 'greeting'|'typing'|'thinking'|'arms_crossing'|'wondering'|'painting';
  useNewCodingPoses?: boolean;
}

const agentPoses = {
  coding: {
    greeting: '/avatars/coding_agent/greeting_pose.webp',
    typing: '/avatars/coding_agent/typing_pose.png',
    thinking: '/avatars/coding_agent/thinking_pose.webp',
    arms_crossing: '/avatars/coding_agent/arms_crossing_pose.webp',
    wondering: '/avatars/coding_agent/wondering_pose.webp',
  },
  coding_new: {
    greeting: '/avatars/coding_agent/greeting_pose_new.webp',
    typing: '/avatars/coding_agent/typing_pose_new.webp',
    thinking: '/avatars/coding_agent/thinking_pose_new.webp',
    arms_crossing: '/avatars/coding_agent/arms_crossing_pose_new.webp',
    wondering: '/avatars/coding_agent/wondering_pose_new.webp',
  },
  finance: {
    greeting: '/avatars/finance_agent/greeting_pose.webp',
    typing: '/avatars/finance_agent/typing_pose.png',
    thinking: '/avatars/finance_agent/thinking_pose.webp',
    arms_crossing: '/avatars/finance_agent/arms_crossing_pose.webp',
    wondering: '/avatars/finance_agent/wondering_pose.webp',
  },
  image: {
    greeting: '/avatars/image_agent/greeting_pose.webp',
    typing: '/avatars/image_agent/typing_pose.png',
    thinking: '/avatars/image_agent/thinking_pose.webp',
    arms_crossing: '/avatars/image_agent/arms_crossing_pose.webp',
    wondering: '/avatars/image_agent/wondering_pose.webp',
    painting: '/avatars/image_agent/painting_pose.webp',
  },
  news: {
    greeting: '/avatars/news_agent/greeting_pose.webp',
    typing: '/avatars/news_agent/typing_pose.png',
    thinking: '/avatars/news_agent/thinking_pose.webp',
    arms_crossing: '/avatars/news_agent/arms_crossing_pose.webp',
    wondering: '/avatars/news_agent/wondering_pose.webp',
  },
  realestate: {
    greeting: '/avatars/realestate_agent/greeting_pose.webp',
    typing: '/avatars/realestate_agent/typing_pose.png',
    thinking: '/avatars/realestate_agent/thinking_pose.webp',
    arms_crossing: '/avatars/realestate_agent/arms_crossing_pose.webp',
    wondering: '/avatars/realestate_agent/wondering_pose.webp',
  },
  travel: {
    greeting: '/avatars/travel_agent/greeting_pose.webp',
    typing: '/avatars/travel_agent/typing_pose.png',
    thinking: '/avatars/travel_agent/thinking_pose.webp',
    arms_crossing: '/avatars/travel_agent/arms_crossing_pose.webp',
    wondering: '/avatars/travel_agent/wondering_pose.webp',
  },
  shopping: {
    greeting: '/avatars/shopping_agent/greeting_pose.webp',
    typing: '/avatars/shopping_agent/typing_pose.webp',
    thinking: '/avatars/shopping_agent/thinking_pose.webp',
    arms_crossing: '/avatars/shopping_agent/arms_crossing_pose.webp',
    wondering: '/avatars/shopping_agent/wondering_pose.webp',
    standing: '/avatars/shopping_agent/standing_pose.webp',
  },
  games: {
    greeting: '/avatars/games_agent/greeting_pose.webp',
    typing: '/avatars/games_agent/typing_pose.webp',
    thinking: '/avatars/games_agent/thinking_pose.webp',
    arms_crossing: '/avatars/games_agent/arms_crossing_pose.webp',
    wondering: '/avatars/games_agent/wondering_pose.webp',
    standing: '/avatars/games_agent/standing_pose.webp',
  },
};

const ChatPoses: React.FC<ChatPosesProps> = ({ agentId, pose, useNewCodingPoses }) => {
  let agentKey = (agentId?.replace('_agent', '') || 'coding') as keyof typeof agentPoses;
  if (agentKey === 'coding' && useNewCodingPoses) agentKey = 'coding_new' as keyof typeof agentPoses;
  const poses = agentPoses[agentKey];
  const src = poses?.[pose as keyof typeof poses] || poses?.greeting;
  const isCodingNew = agentKey === 'coding_new';
  return (
    <div className="chat-poses-container" style={isCodingNew ? { width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' } : {}}>
      <img src={src} alt={pose} style={isCodingNew ? { maxHeight: '100%', maxWidth: '100%', height: '100%', width: '100%', borderRadius: 12, objectFit: 'fill' } : { width: '90%', height: 'auto', borderRadius: 12 }} />
    </div>
  );
};

export default ChatPoses;
