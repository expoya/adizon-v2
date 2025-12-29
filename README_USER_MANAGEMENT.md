# Adizon User-Management System

Complete User-Management implementation with PostgreSQL, FastAPI REST API, and React Admin Frontend.

## 📋 Overview

This system adds comprehensive user authentication, authorization, and management to Adizon:

- **Security**: Only approved users can access Adizon via Telegram/Slack
- **Attribution**: All CRM operations are attributed to the user who performed them
- **Multi-Platform**: Users can connect multiple chat platforms to one account
- **Admin UI**: Modern React-based admin interface for user management

## 🏗️ Architecture

```
┌─────────────┐
│ Telegram/   │
│ Slack       │
└──────┬──────┘
       │
       ▼
┌─────────────────┐
│ Auth Middleware │ ◄── Checks if user is approved
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Message Handler │ ◄── Injects user context
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ CRM Handler     │ ◄── Adds attribution to notes/tasks
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ CRM Adapter     │
│ (Twenty/Zoho)   │
└─────────────────┘

Admin manages users via:
┌─────────────────┐
│ React Frontend  │ ◄──► REST API ◄──► PostgreSQL
└─────────────────┘
```

## 🚀 Setup

### 1. Database Setup

Start PostgreSQL via Docker:

```bash
docker-compose up -d postgres
```

Run migrations:

```bash
cd /Users/michaelschiestl/python/adizon-v2
source venv/bin/activate
alembic upgrade head
```

### 2. Backend Configuration

Add to `.env`:

```bash
# PostgreSQL
DATABASE_URL=postgresql://adizon:adizon_dev_password@localhost:5432/adizon_users

# Admin API Token (generate a secure random string)
ADMIN_API_TOKEN=your_secure_admin_token_here

# Admin Telegram ID (for registration notifications)
ADMIN_TELEGRAM_ID=your_telegram_id
```

### 3. Frontend Setup

```bash
cd frontend
npm install
cp .env.example .env
```

Edit `frontend/.env`:

```bash
VITE_API_URL=http://localhost:8000
VITE_ADMIN_TOKEN=your_secure_admin_token_here
```

Start frontend:

```bash
npm run dev
```

### 4. Start Backend

```bash
cd /Users/michaelschiestl/python/adizon-v2
source venv/bin/activate
python main.py
```

## 📖 Usage

### For End Users (Telegram/Slack)

1. User sends first message to Adizon bot
2. System creates pending user and notifies admin
3. User receives: "Waiting for admin approval"
4. After admin approval, user receives notification
5. User can now use all Adizon features

### For Admins (Web UI)

Access admin panel: http://localhost:5173

**Dashboard:**
- View statistics (total, active, pending users)
- Quick approve recent registrations

**Users:**
- List all users
- Search by name/email
- Create users manually
- Edit user details
- Link/unlink platforms
- Delete users

**Approvals:**
- Review pending registrations
- Approve or reject users
- View registration details

## 🔐 Security

**Authentication Middleware:**
- Checks user authorization on every webhook request
- Blocks unapproved users automatically
- Maintains request state for user context

**Admin API:**
- Token-based authentication
- Separate from user authentication
- Required for all admin operations

**CRM Attribution:**
- All notes and tasks show `✍️ via {user_name}`
- Traceable to original user
- Multi-user safe

## 🗄️ Database Schema

**Users Table:**
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    telegram_id VARCHAR(100) UNIQUE,
    slack_id VARCHAR(100) UNIQUE,
    is_active BOOLEAN DEFAULT true,
    is_approved BOOLEAN DEFAULT false,
    role ENUM('user', 'admin') DEFAULT 'user',
    crm_display_name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## 📡 API Endpoints

**User Management:**
- `GET /api/users` - List all users
- `GET /api/users/pending` - Pending approvals
- `GET /api/users/stats` - Statistics
- `GET /api/users/{id}` - Get user details
- `POST /api/users` - Create user
- `PATCH /api/users/{id}` - Update user
- `DELETE /api/users/{id}` - Delete user
- `POST /api/users/{id}/approve` - Approve user
- `POST /api/users/{id}/link` - Link platform

## 🔧 Development

**Run Migrations:**

Create new migration:
```bash
alembic revision --autogenerate -m "description"
```

Apply migrations:
```bash
alembic upgrade head
```

Rollback:
```bash
alembic downgrade -1
```

**Frontend Development:**

```bash
cd frontend
npm run dev      # Start dev server
npm run build    # Build for production
npm run preview  # Preview production build
```

## 🚢 Deployment

### Backend (Railway/Fly.io)

1. Set environment variables:
   - `DATABASE_URL` - PostgreSQL connection string
   - `ADMIN_API_TOKEN` - Admin token
   - `ADMIN_TELEGRAM_ID` - Admin Telegram ID
   - All other Adizon env vars

2. Run migrations on deployment:
```bash
alembic upgrade head
```

3. Start server:
```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

### Frontend (Vercel/Netlify)

1. Build command: `npm run build`
2. Output directory: `dist`
3. Environment variables:
   - `VITE_API_URL` - Production API URL
   - `VITE_ADMIN_TOKEN` - Admin token

## 🎨 Customization

**Add New User Fields:**

1. Update `models/user.py`
2. Create migration: `alembic revision --autogenerate -m "add_field"`
3. Update `UserRepository` methods
4. Update API schemas in `api/users.py`
5. Update frontend types in `frontend/src/services/api.ts`
6. Update UI components

**Add New Platforms:**

1. Update `User` model with new platform ID field
2. Update `AuthMiddleware` to extract user info
3. Update `RegistrationService` for notifications
4. Update frontend badges/UI

## 📝 Notes

- User emails are unique across the system
- Platform IDs (telegram_id, slack_id) are unique and nullable
- CRM display name is used for attribution (defaults to user name)
- Pending users can't access Adizon until approved
- Admins can approve/reject via UI or API
- Multi-platform: One user can have both Telegram and Slack linked

## 🐛 Troubleshooting

**Database connection failed:**
```bash
# Check if PostgreSQL is running
docker ps | grep postgres

# Restart PostgreSQL
docker-compose restart postgres
```

**Frontend can't reach API:**
- Check CORS settings in `main.py`
- Verify `VITE_API_URL` in frontend `.env`
- Check if backend is running on port 8000

**Migrations fail:**
```bash
# Reset database (⚠️ destroys data)
alembic downgrade base
alembic upgrade head
```

## 🎯 Future Enhancements

- OAuth2 login (Google/Microsoft)
- User-specific settings
- Role-based permissions
- Audit logs
- Email notifications
- User groups/teams
- API rate limiting per user

