# 🤖 Robots-AI Frontend

Modern React TypeScript frontend for the Robots-AI multi-agent platform. Features a responsive chat interface with real-time agent interactions, file upload capabilities, and dynamic agent avatars.

## 🏗️ Architecture

- **Framework**: React 18 with TypeScript
- **Build Tool**: Vite
- **Styling**: CSS Modules
- **State Management**: React Hooks
- **Routing**: React Router v6
- **Authentication**: Supabase Auth
- **UI Components**: Custom components with modern design

## 🚀 Quick Start

### Prerequisites
- Node.js 18+
- Conda environment with Node.js
- Backend server running on port 8000

### Installation

1. **Activate your conda environment**
   ```bash
   conda activate robots_app
   ```

2. **Install dependencies**
   ```bash
   cd robots_frontend
   npm install
   ```

3. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your Supabase credentials
   ```

4. **Start development server**
   ```bash
   npm run dev
   ```

5. **Open your browser**
   Navigate to `http://localhost:5173`

## 🔑 Environment Variables

Create a `.env` file in the `robots_frontend` directory:

```env
# Supabase Configuration (for authentication)
VITE_SUPABASE_URL=your_supabase_project_url
VITE_SUPABASE_ANON_KEY=your_supabase_anon_key

# Optional: Google Analytics
VITE_GA_TRACKING_ID=your_google_analytics_id

# Optional: Feature Flags
VITE_ENABLE_ANALYTICS=true
VITE_ENABLE_ERROR_TRACKING=false
```

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
  created_at timestamp with time zone default now()
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
- **Real-time Chat**: Interactive chat with typing indicators
- **Agent Selection**: Choose from 7 specialized AI agents
- **File Upload**: Drag-and-drop file upload with preview
- **Message History**: Persistent conversation history
- **Responsive Design**: Works on desktop and mobile

### Agent Avatars
- **Dynamic Poses**: Agents change poses based on activity
- **Personalization**: Agents address users by name
- **Visual Feedback**: Greeting, thinking, typing, and idle poses

### File Processing
- **Multi-format Support**: Images, PDFs, documents
- **OCR Processing**: Text extraction from images
- **Preview System**: File preview before upload
- **Progress Indicators**: Upload progress tracking

### User Experience
- **Dark/Light Theme**: Toggle between themes (only in the Chat UI)
- **Loading States**: Smooth loading animations
- **Error Handling**: User-friendly error messages

## 📁 Project Structure

```
robots_frontend/
├── public/                    # Static assets
│   ├── avatars/              # Agent avatar images
│   │   ├── coding_agent/     # Coding agent poses
│   │   ├── finance_agent/    # Finance agent poses
│   │   ├── news_agent/       # News agent poses
│   │   ├── realestate_agent/ # Real estate agent poses
│   │   ├── travel_agent/     # Travel agent poses
│   │   ├── image_agent/      # Image agent poses
│   │   └── shopping_agent/   # Shopping agent poses
│   ├── assets/               # Other static assets
│   └── service-worker.js     # Service worker for caching
├── src/                      # Source code
│   ├── components/           # React components
│   │   ├── ChatInput.tsx     # Chat input component
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
│   │   ├── Navbar.tsx        # Navigation component
│   │   └── UserAvatar.tsx    # User avatar component
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
│   │   └── AgentDescriptions.ts # Agent descriptions
│   ├── utils/                # Utility functions
│   │   └── mapDataParser.ts  # Map data parsing
│   ├── assets/               # Static assets
│   │   └── react.svg         # React logo
│   ├── App.tsx               # Main app component
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
└── .env.example              # Environment variables template
```

## 🎨 Component Documentation

### Core Components

#### ChatInput.tsx & ChatInput.css
- **Purpose**: Text input and file upload for chat
- **Props**: `input`, `setInput`, `loadingMessages`, `handleSend`
- **Features**: File drag-and-drop, upload progress, typing indicators

#### ChatMessages.tsx & ChatMessages.css
- **Purpose**: Display chat messages and agent responses
- **Props**: `messages`, `loadingMessages`, `userName`, `agentName`
- **Features**: Message formatting, markdown rendering, image display, message timestamps

#### ChatPoses.tsx & ChatPoses.css
- **Purpose**: Display agent avatar poses
- **Props**: `agentId`, `pose`
- **Features**: Dynamic pose changes, fallback images, pose transitions

#### ChatSidebar.tsx & ChatSidebar.css
- **Purpose**: Sidebar for conversation management
- **Features**: Conversation list, agent switching, user profile

#### FileUpload.tsx & FileUpload.css
- **Purpose**: File upload interface
- **Props**: `onFileUpload`, `loading`
- **Features**: Drag-and-drop, file validation, progress tracking, file preview

#### Map.tsx & Map.css
- **Purpose**: Map integration component
- **Features**: Interactive maps, location display, route visualization

#### MapMessage.tsx & MapMessage.css
- **Purpose**: Map message display component
- **Features**: Map data rendering, location information display

#### Navbar.tsx
- **Purpose**: Navigation component
- **Features**: User authentication, navigation links, responsive design

#### UserAvatar.tsx
- **Purpose**: User avatar display
- **Features**: User profile pictures, fallback avatars, authentication status

### Page Components

#### AgentSelection.tsx & AgentSelection.css
- **Purpose**: Agent selection interface
- **Features**: Agent cards, search functionality, filtering, agent descriptions

#### ChatUI.tsx & ChatUI.css
- **Purpose**: Main chat interface
- **Features**: Chat sidebar, message history, real-time updates, theme toggle

#### Details.tsx & Details.css
- **Purpose**: Agent details page
- **Features**: Agent information, capabilities, usage examples

#### HomePage.tsx & HomePage.css
- **Purpose**: Landing page
- **Features**: Welcome message, navigation to agent selection, feature highlights

#### SignIn.tsx & Auth.css
- **Purpose**: Sign in page
- **Features**: User authentication, form validation, error handling

#### SignUp.tsx & Auth.css
- **Purpose**: Sign up page
- **Features**: User registration, form validation, password requirements

### Data & Utilities

#### AgentDescriptions.ts
- **Purpose**: Static agent descriptions and metadata
- **Content**: Agent names, descriptions, capabilities, keywords

#### useAuth.ts
- **Purpose**: Authentication hook
- **Features**: User authentication state, login/logout functions

#### mapDataParser.ts
- **Purpose**: Map data parsing utilities
- **Features**: Location data processing, map coordinate handling

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
npm run type-check   # Run TypeScript type checking
```

## 🔧 Configuration Files

- **vite.config.ts**: Vite build configuration
- **tsconfig.json**: TypeScript configuration
- **eslint.config.js**: ESLint rules and formatting
- **package.json**: Dependencies and scripts
