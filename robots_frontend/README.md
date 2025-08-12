# 🤖 Robots-AI Frontend

Modern React TypeScript frontend for the Robots-AI multi-agent platform. Features a responsive chat interface with real-time agent interactions, file upload capabilities, interactive maps, and dynamic agent avatars with pose animations.

## 🏗️ Architecture

- **Framework**: React 19 with TypeScript
- **Build Tool**: Vite 6
- **Styling**: CSS with modern design system
- **State Management**: React Hooks
- **Routing**: React Router v7
- **Authentication**: Supabase Auth
- **Maps**: Leaflet with React-Leaflet
- **UI Components**: Custom components with modern design

## 🚀 Quick Start

### Prerequisites
- Node.js 18+
- Conda environment with Node.js
- Backend server running on port 8000

### Installation

1. **Activate your conda environment**
   ```bash
   conda activate cs_agent
   ```

2. **Install dependencies**
   ```bash
   cd robots_frontend
   npm install
   ```

3. **Set up environment variables**
   Create a `.env` file in the `robots_frontend` directory with your Supabase credentials.

4. **Start development server**
   ```bash
   npm run dev
   ```

5. **Open your browser**
   Navigate to `http://localhost:5173`

## 🔑 Environment Variables

Create a `.env` file in the `robots_frontend` directory:

## 🔑 How to Get Your Free Supabase Project URL and Anon Key

You will need to add the following variables to your frontend `.env` file:

```env
VITE_SUPABASE_URL=your_supabase_project_url
VITE_SUPABASE_ANON_KEY=your_supabase_anon_key
```

**How to get them:**
1. Go to [Supabase](https://supabase.com/) and sign up for a free account.
2. After logging in, click **“New Project”** and follow the prompts to create a project.
3. Once your project is created, go to your project dashboard.
4. In the left sidebar, click **“Project Settings”** → **“API”**.
5. Copy the **Project URL** and **anon public key** (found under “Project API keys”).
6. Paste them into your `.env` file as shown above.

> [Official Supabase Documentation: Getting Started](https://supabase.com/docs/guides/getting-started)

## 🗄️ Supabase Database Setup

### 1. Create Tables
Run this SQL in the Supabase SQL Editor:

```sql
-- Conversations table
create table if not exists public.conversations (
  id uuid primary key default uuid_generate_v4(),
  user_id uuid references auth.users(id) on delete cascade,
  agent_id text not null,
  title text,
  summary text,
  last_summary_created_at timestamp with time zone,
  created_at timestamp with time zone default now()
);

-- Messages table
create table if not exists public.messages (
  id uuid primary key default uuid_generate_v4(),
  conversation_id uuid references public.conversations(id) on delete cascade,
  user_id uuid references auth.users(id) on delete cascade,
  agent_id text not null,
  role text not null,
  content text,
  created_at timestamp with time zone default now(),
  type text,
  file_url text
);
```

### 2. Enable Row Level Security (RLS)
Run this SQL in the Supabase SQL Editor:

```sql
-- Enable RLS on conversations table
alter table conversations enable row level security;

-- Enable RLS on messages table
alter table messages enable row level security;

-- Create policy for conversations
create policy "Users can access their own conversations"
on conversations
for all
using (user_id = auth.uid());

-- Create policy for messages
create policy "Users can access their own messages"
on messages
for all
using (user_id = auth.uid());
```

### 3. Get Your Supabase Credentials
1. Go to your Supabase project dashboard
2. Navigate to Settings → API
3. Copy the **Project URL** and **anon public key**
4. Add them to your frontend `.env` file as `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY`

## 🎨 Features

### Chat Interface
- **Real-time Chat**: Interactive chat with typing indicators and pose animations
- **Agent Selection**: Choose from 7 specialized AI agents with unique avatars
- **File Upload**: Drag-and-drop file upload with content extraction
- **Message History**: Persistent conversation history with Supabase
- **Responsive Design**: Works on desktop and mobile devices
- **Error Handling**: User-friendly error messages and retry mechanisms

### Agent Avatars & Poses
- **Dynamic Poses**: 6 different poses per agent (greeting, typing, thinking, arms_crossing, wondering, painting)
- **Personalization**: Agents address users by name from Supabase profile
- **Visual Feedback**: Real-time pose changes based on agent activity
- **Agent-Specific**: Each agent has unique avatar and pose sets

### File Processing
- **Multi-format Support**: PDF, DOCX, XLSX, images, text files
- **Content Extraction**: Automatic text extraction with backend processing
- **Preview System**: File upload status and success indicators
- **Progress Tracking**: Upload progress and error handling

### Interactive Maps
- **Leaflet Integration**: Interactive maps with OpenStreetMap tiles
- **Location Display**: Show points of interest, routes, and areas
- **Custom Markers**: Color-coded markers for different POI types
- **Route Visualization**: Display routes with distance and duration
- **Map Messages**: Special message component for map data

### Chess Game Integration
- **Interactive Chessboard**: Real-time chess gameplay with chess.js
- **Move Validation**: Automatic validation of legal moves
- **Natural Language Communication**: Chat with the agent about moves and strategy
- **Game State Tracking**: Automatic detection of checkmate, stalemate, and draw
- **Response Parsing**: Intelligent parsing of agent responses to extract FEN positions
- **Visual Feedback**: Clean UI that hides technical FEN data from users

### Conversation Memory & Context Management
- **Rolling Summarization**: The system uses a rolling summarization approach that incorporates new messages into existing summaries
- **Automatic Context Loading**: When users open old conversations, the system automatically loads conversation context
- **Intelligent Summarization**: Conversation history is summarized using backend AI to provide essential context
- **Efficient Memory Usage**: Only relevant context is loaded, avoiding memory overload
- **Seamless Experience**: Users can continue conversations naturally without losing context
- **One-time Loading**: Context is loaded once per conversation session for optimal performance
- **Database Integration**: Summaries are stored in the `conversations` table with `summary` and `last_summary_created_at` columns
- **Smart Context Injection**: Previous conversation summaries are prepended to new messages as context for agents

### User Experience
- **Authentication**: Supabase-based user authentication
- **Loading States**: Smooth loading animations and indicators
- **Error Boundaries**: Graceful error handling with fallbacks
- **Usage Monitoring**: Track API usage and quotas
- **Conversation Management**: Create, rename, and delete conversations
- **Conversation Memory**: Automatic loading of conversation context when reopening old conversations
- **Context Summarization**: Intelligent summarization of conversation history for efficient memory usage

## 📁 Project Structure

```
robots_frontend/
├── public/                    # Static assets
│   ├── avatars/              # Agent avatar images
│   │   ├── coding_agent/     # Coding agent poses (6 poses)
│   │   ├── finance_agent/    # Finance agent poses (6 poses)
│   │   ├── news_agent/       # News agent poses (6 poses)
│   │   ├── realestate_agent/ # Real estate agent poses (6 poses)
│   │   ├── travel_agent/     # Travel agent poses (6 poses)
│   │   ├── image_agent/      # Image agent poses (7 poses incl. painting)
│   │   ├── shopping_agent/   # Shopping agent poses (6 poses)
│   │   └── games_agent/      # Games agent poses (6 poses)
│   ├── assets/               # Other static assets
│   │   ├── homepage.webp     # Homepage background
│   │   ├── left.webp         # Left side image
│   │   ├── right.webp        # Right side image
│   │   └── image-not-found.png # Fallback image
│   └── service-worker.js     # Service worker for caching
├── src/                      # Source code
│   ├── components/           # React components
│   │   ├── ChatInput.tsx     # Chat input with file upload
│   │   ├── ChatInput.css     # Chat input styles
│   │   ├── ChatMessages.tsx  # Message display component
│   │   ├── ChatMessages.css  # Message display styles
│   │   ├── ChatPoses.tsx     # Agent pose component
│   │   ├── ChatPoses.css     # Agent pose styles
│   │   ├── ChatSidebar.tsx   # Sidebar component
│   │   ├── ChatSidebar.css   # Sidebar styles
│   │   ├── FileUpload.tsx    # File upload component
│   │   ├── FileUpload.css    # File upload styles
│   │   ├── Map.tsx           # Map integration component
│   │   ├── Map.css           # Map styles
│   │   ├── MapMessage.tsx    # Map message component
│   │   ├── MapMessage.css    # Map message styles
│   │   ├── Chessboard.tsx    # Interactive chessboard component
│   │   ├── Chessboard.css    # Chessboard styles
│   │   ├── ErrorBoundary.tsx # Error boundary component
│   │   ├── Navbar.tsx        # Navigation component
│   │   ├── UsageMonitor.tsx  # Usage monitoring component
│   │   └── UserAvatar.tsx    # User avatar component
│   │   ├── Chessboard.css    # Chessboard styles
│   │   ├── Navbar.tsx        # Navigation component
│   │   ├── UserAvatar.tsx    # User avatar component
│   │   ├── ErrorBoundary.tsx # Error boundary component
│   │   └── UsageMonitor.tsx  # Usage monitoring component
│   ├── pages/                # Page components
│   │   ├── AgentSelection.tsx # Agent selection page
│   │   ├── AgentSelection.css # Agent selection styles
│   │   ├── ChatUI.tsx        # Main chat interface
│   │   ├── ChatUI.css        # Chat UI styles
│   │   ├── Details.tsx       # Agent details page
│   │   ├── Details.css       # Details page styles
│   │   ├── HomePage.tsx      # Homepage
│   │   ├── HomePage.css      # Homepage styles
│   │   ├── SignIn.tsx        # Sign in page
│   │   ├── SignUp.tsx        # Sign up page
│   │   └── Auth.css          # Authentication styles
│   ├── hooks/                # Custom React hooks
│   │   └── useAuth.ts        # Authentication hook
│   ├── data/                 # Static data
│   │   └── AgentDescriptions.ts # Agent descriptions and names
│   ├── utils/                # Utility functions
│   │   ├── mapDataParser.ts  # Map data parsing utilities
│   │   ├── chessParser.ts    # Chess response parsing utilities
│   │   └── conversationSummarizer.ts # Rolling conversation summarization utility
│   ├── assets/               # Static assets
│   │   └── react.svg         # React logo
│   ├── App.tsx               # Main app component with routing
│   ├── App.css               # App styles
│   ├── main.tsx              # App entry point
│   ├── index.css             # Global styles
│   └── vite-env.d.ts         # Vite environment types
├── package.json              # Dependencies and scripts
├── package-lock.json         # Locked dependencies
├── tsconfig.json             # TypeScript configuration
├── tsconfig.app.json         # App TypeScript config
├── tsconfig.node.json        # Node TypeScript config
├── vite.config.ts            # Vite configuration
├── eslint.config.js          # ESLint configuration
└── index.html                # HTML entry point
```

## 🎨 Component Documentation

### Core Components

#### ChatInput.tsx & ChatInput.css
- **Purpose**: Text input and file upload for chat
- **Props**: `input`, `setInput`, `loadingMessages`, `handleSend`, `onFileSelected`
- **Features**: File drag-and-drop, upload progress, typing indicators, file attachment

#### ChatMessages.tsx & ChatMessages.css
- **Purpose**: Display chat messages and agent responses
- **Props**: `messages`, `loadingMessages`, `userName`, `agentName`
- **Features**: Message formatting, markdown rendering, image display, message timestamps, map integration

#### ChatPoses.tsx & ChatPoses.css
- **Purpose**: Display agent avatar poses with animations
- **Props**: `agentId`, `pose`
- **Features**: Dynamic pose changes, agent-specific avatars, pose transitions, fallback images

#### Chessboard.tsx & Chessboard.css
- **Purpose**: Interactive chessboard for games agent
- **Props**: `onMove`, `onGameStateChange`, `isAgentTurn`, `position`, `onReset`
- **Features**: Real-time chess gameplay, move validation, game state tracking, responsive design

#### ChatSidebar.tsx & ChatSidebar.css
- **Purpose**: Sidebar for conversation management
- **Features**: Conversation list, agent switching, user profile, conversation CRUD operations

#### FileUpload.tsx & FileUpload.css
- **Purpose**: File upload interface with backend integration
- **Props**: `conversationId`, `onUploadSuccess`, `onFileSelected`
- **Features**: Drag-and-drop, file validation, progress tracking, content extraction

#### Map.tsx & Map.css
- **Purpose**: Interactive map integration with Leaflet
- **Features**: OpenStreetMap tiles, custom markers, route visualization, polygon display, popup information

#### MapMessage.tsx & MapMessage.css
- **Purpose**: Specialized message component for map data
- **Features**: Map data rendering, location information display, interactive elements

#### Navbar.tsx
- **Purpose**: Navigation component with authentication
- **Features**: User authentication, navigation links, responsive design, user profile

#### UserAvatar.tsx
- **Purpose**: User avatar display component
- **Features**: User profile pictures, fallback avatars, authentication status

#### ErrorBoundary.tsx
- **Purpose**: Error boundary for graceful error handling
- **Features**: Error catching, fallback UI, error reporting

#### UsageMonitor.tsx
- **Purpose**: Monitor API usage and quotas
- **Features**: Usage tracking, quota monitoring, user feedback

### Page Components

#### AgentSelection.tsx & AgentSelection.css
- **Purpose**: Agent selection interface with descriptions
- **Features**: Agent cards, search functionality, filtering, agent descriptions, avatar display

#### ChatUI.tsx & ChatUI.css
- **Purpose**: Main chat interface with full functionality
- **Features**: Chat sidebar, message history, real-time updates, file upload, map integration, pose animations

#### Details.tsx & Details.css
- **Purpose**: Agent details and information page
- **Features**: Agent information, capabilities, usage examples, feature highlights

#### HomePage.tsx & HomePage.css
- **Purpose**: Landing page with modern design
- **Features**: Welcome message, navigation to agent selection, feature highlights, responsive design

#### SignIn.tsx & Auth.css
- **Purpose**: Sign in page with Supabase authentication
- **Features**: User authentication, form validation, error handling, responsive design

#### SignUp.tsx & Auth.css
- **Purpose**: Sign up page with user registration
- **Features**: User registration, form validation, password requirements, error handling

### Data & Utilities

#### AgentDescriptions.ts
- **Purpose**: Static agent descriptions and metadata
- **Content**: Agent names, descriptions, capabilities, keywords for all 7 agents

#### useAuth.ts
- **Purpose**: Authentication hook with Supabase integration
- **Features**: User authentication state, login/logout functions, user profile management

#### mapDataParser.ts
- **Purpose**: Map data parsing utilities for backend integration
- **Features**: Location data processing, map coordinate handling, route data parsing

#### conversationSummarizer.ts
- **Purpose**: Conversation summarization utility for rolling context management
- **Features**: Backend summarization calls, rolling summary updates, error handling, previous summary integration

## 🛠️ Development Workflow

1. **Start backend server**
   ```bash
   cd robots_backend
   uvicorn main:app --reload --host 0.0.0.0 --port 8000 --log-level debug
   ```

2. **Start frontend development server**
   ```bash
   cd robots_frontend
   npm run dev
   ```
   
   **Note**: The frontend runs on `http://localhost:5173` (Vite's default port)

## 🎯 Available Scripts

```bash
# Development
npm run dev          # Start development server
npm run build        # Build for production
npm run preview      # Preview production build
npm run lint         # Run ESLint
```

## 🔧 Configuration Files

- **vite.config.ts**: Vite build configuration
- **tsconfig.json**: TypeScript configuration
- **eslint.config.js**: ESLint rules and formatting
- **package.json**: Dependencies and scripts

## 🚨 Troubleshooting

### Common Issues

1. **Backend Connection Errors**
   ```
   Error: Failed to fetch from backend
   Solution: Ensure backend is running on port 8000
   ```

2. **Supabase Authentication Issues**
   ```
   Error: Supabase connection failed
   Solution: Check VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY in .env
   ```

3. **File Upload Errors**
   ```
   Error: File upload failed
   Solution: Check backend file upload endpoint and file size limits
   ```

4. **Map Loading Issues**
   ```
   Error: Map tiles not loading
   Solution: Check internet connection and Leaflet CDN
   ```

### Debug Mode
Enable debug logging in browser console and check network tab for API calls.

## 🔒 Security

### Authentication
- Supabase-based user authentication
- Secure token management
- Row-level security for user data

### File Upload
- File type validation
- Size limits enforced
- Secure content extraction

### API Security
- Bearer token authentication
- CORS properly configured
- Error handling for sensitive data

## 📈 Performance

### Optimization Tips
1. **Use React.memo** for expensive components
2. **Implement lazy loading** for large components
3. **Optimize images** and use WebP format
4. **Use service worker** for caching

### Scaling
- Vite for fast development builds
- Code splitting for production
- Optimized bundle sizes
- CDN for static assets

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License.

---

**Frontend for Robots-AI Multi-Agent Platform**
