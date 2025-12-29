# Adizon Admin Frontend

React-based admin interface for Adizon User-Management.

## Tech Stack

- **React 18** + **TypeScript**
- **Vite** (Build Tool)
- **TailwindCSS** (Styling)
- **React Router** (Navigation)
- **Axios** (API Client)

## Setup

1. Install dependencies:
```bash
npm install
```

2. Create `.env` file:
```bash
cp .env.example .env
```

Edit `.env`:
```
VITE_API_URL=http://localhost:8000
VITE_ADMIN_TOKEN=your_admin_token_here
```

3. Start development server:
```bash
npm run dev
```

Frontend will be available at: http://localhost:5173

## Features

- **Dashboard**: Overview with statistics and recent registrations
- **Users**: List, search, create, edit, delete users
- **Approvals**: Review and approve pending user registrations
- **Multi-Platform**: Support for Telegram and Slack user linking
- **Real-time**: Auto-refresh on user actions

## Building for Production

```bash
npm run build
```

Build output will be in `dist/` directory.

## API Configuration

The frontend communicates with the Adizon backend API.

**Environment Variables:**
- `VITE_API_URL`: Backend API URL (default: http://localhost:8000)
- `VITE_ADMIN_TOKEN`: Admin API token for authentication

**API Endpoints:**
- `GET /api/users` - List all users
- `GET /api/users/pending` - List pending approvals
- `GET /api/users/stats` - Get statistics
- `POST /api/users` - Create user
- `PATCH /api/users/{id}` - Update user
- `DELETE /api/users/{id}` - Delete user
- `POST /api/users/{id}/approve` - Approve user
- `POST /api/users/{id}/link` - Link platform to user
