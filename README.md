SlotSwapper - Complete Implementation Guide
Project Overview
SlotSwapper is a peer-to-peer time-slot scheduling application that enables users to exchange calendar events with other users. The core innovation is the atomic swap mechanism that ensures both users' calendars are updated simultaneously, preventing conflicts or partial states.

Architecture Overview
<img width="2400" height="1600" alt="slotswapper_architecture" src="https://github.com/user-attachments/assets/a2bce2c5-f89f-4591-9c3f-2571f135c04c" />
Tech Stack
Frontend: React 18 + Vite, Context API for state management, Socket.io for real-time notifications

Backend: Node.js/Express, JWT authentication, Socket.io server

Database: PostgreSQL (with SQLite fallback for local development)

Real-time: WebSockets via Socket.io

Testing: Jest + Supertest

Containerization: Docker + Docker Compose

System Architecture
text
┌─────────────────────────────────────────────────────────────┐
│                      React Frontend                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ Auth Pages   │  │  Dashboard   │  │  Marketplace     │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │        Context API State Management                  │  │
│  │  (auth, events, swapRequests, currentUser)          │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
              ↓ HTTP (REST API) ↓
              ↕ WebSocket (Socket.io) ↕
┌─────────────────────────────────────────────────────────────┐
│                   Express.js Backend                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ Auth Routes  │  │ Event Routes │  │ Swap Routes      │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │        JWT Verification Middleware                   │  │
│  │     Socket.io Connection Handler                     │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
              ↓ SQL Queries with Transactions ↓
┌─────────────────────────────────────────────────────────────┐
│                    PostgreSQL Database                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ users        │  │ events       │  │ swapRequests     │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────────────┘
Database Schema
Users Table

sql
CREATE TABLE users (
  id SERIAL PRIMARY KEY,
  email VARCHAR(255) UNIQUE NOT NULL,
  username VARCHAR(255) NOT NULL,
  passwordHash VARCHAR(255) NOT NULL,
  createdAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
Events Table
sql
CREATE TABLE events (
  id SERIAL PRIMARY KEY,
  userId INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  title VARCHAR(255) NOT NULL,
  startTime TIMESTAMP NOT NULL,
  endTime TIMESTAMP NOT NULL,
  status VARCHAR(50) DEFAULT 'BUSY' 
    CHECK (status IN ('BUSY', 'SWAPPABLE', 'SWAP_PENDING')),
  createdAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updatedAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_events_userId ON events(userId);
CREATE INDEX idx_events_status ON events(status);
SwapRequests Table
sql
CREATE TABLE swapRequests (
  id SERIAL PRIMARY KEY,
  requesterId INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  requesteeId INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  requesterSlotId INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
  requesteeSlotId INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
  status VARCHAR(50) DEFAULT 'PENDING' 
    CHECK (status IN ('PENDING', 'ACCEPTED', 'REJECTED')),
  createdAt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  respondedAt TIMESTAMP,
  UNIQUE(requesterSlotId, requesteeSlotId)
);

CREATE INDEX idx_swapRequests_requesterId ON swapRequests(requesterId);
CREATE INDEX idx_swapRequests_requesteeId ON swapRequests(requesteeId);
Core Features & Implementation
1. Authentication System
JWT Token Structure:

Access Token: 15-minute expiration, contains userId and email

Refresh Token: 7-day expiration, stored securely

Header: Authorization: Bearer <access_token>

Flow:

text
1. User signs up → password hashed with bcrypt (10 rounds)
2. User logs in → verify password → generate JWT pair
3. Protected requests → extract token from header → verify signature
4. Token expired → use refresh token to get new access token
Security Best Practices:

Tokens use RS256 (RSA) algorithm in production, HS256 (HMAC) in dev

Short-lived access tokens minimize breach impact

Refresh tokens have longer TTL but can be revoked

No sensitive data in token payload (user_id only)

Always use HTTPS in production (for token transmission)

2. Swap Logic (Critical Transaction)
State Diagram:

text
BUSY ──[Make Swappable]──> SWAPPABLE ──[Create Swap Request]──> SWAP_PENDING
                                                                      │
                                         ┌────────────────────────────┼────────────────────────┐
                                         │                            │                        │
                                    [Accept]                    [Reject]                  [Cancel]
                                         │                            │                        │
                                    BUSY (owner changed)       SWAPPABLE                SWAPPABLE
Atomic Swap Transaction (PostgreSQL):

sql
BEGIN TRANSACTION;
  -- Verify both slots exist and are SWAPPABLE
  SELECT * FROM events WHERE id = $1 AND status = 'SWAPPABLE';
  SELECT * FROM events WHERE id = $2 AND status = 'SWAPPABLE';
  
  -- Swap ownership: exchange userId between two events
  UPDATE events SET userId = user_b_id WHERE id = slot_a_id;
  UPDATE events SET userId = user_a_id WHERE id = slot_b_id;
  
  -- Mark both slots as BUSY (no longer swappable)
  UPDATE events SET status = 'BUSY' WHERE id IN ($1, $2);
  
  -- Mark swap request as ACCEPTED
  UPDATE swapRequests SET status = 'ACCEPTED', respondedAt = NOW() WHERE id = $3;
  
COMMIT; -- All succeed or all rollback (ACID guarantee)
Key Properties:

Atomicity: All operations succeed or none do (no half-completed swaps)

Consistency: Database constraints enforced (FKs, unique indexes)

Isolation: Transaction isolated from concurrent requests

Durability: Once committed, changes persist despite system failures

3. Real-time Notifications with WebSockets
Socket.io Events:

Client → Server:

connect - User connects after login

disconnect - User logs out or connection lost

subscribe - User subscribes to swap notifications

Server → Client:

swap-request-received - New swap request arrived

swap-accepted - Your swap request was accepted

swap-rejected - Your swap request was rejected

event-updated - Your event was modified by swap

Implementation:

javascript
// Server: Notify specific user
io.to(requesteeSocketId).emit('swap-request-received', {
  id: swapRequest.id,
  requesterName: requester.username,
  requesterSlot: {...},
  offeredSlot: {...},
});

// Client: Listen for real-time updates
socket.on('swap-request-received', (data) => {
  // Update incoming requests list
  // Show notification toast
  // Update state without page refresh
});
4. API Endpoints
Authentication Endpoints
POST /api/auth/signup

json
Request:
{
  "email": "user@example.com",
  "username": "john_doe",
  "password": "securePassword123"
}

Response (201):
{
  "message": "User created successfully",
  "userId": 1
}

Error (409):
{ "error": "Email already exists" }
POST /api/auth/login

json
Request:
{
  "email": "user@example.com",
  "password": "securePassword123"
}

Response (200):
{
  "accessToken": "eyJhbGc...",
  "refreshToken": "eyJhbGc...",
  "user": {
    "id": 1,
    "email": "user@example.com",
    "username": "john_doe"
  }
}

Error (401):
{ "error": "Invalid credentials" }
Event Endpoints
POST /api/events (Protected)

json
Request:
{
  "title": "Team Meeting",
  "startTime": "2025-11-05T10:00:00Z",
  "endTime": "2025-11-05T11:00:00Z"
}

Response (201):
{
  "id": 5,
  "userId": 1,
  "title": "Team Meeting",
  "startTime": "2025-11-05T10:00:00Z",
  "endTime": "2025-11-05T11:00:00Z",
  "status": "BUSY"
}
GET /api/events (Protected)

text
Response (200):
[
  {
    "id": 5,
    "title": "Team Meeting",
    "startTime": "2025-11-05T10:00:00Z",
    "endTime": "2025-11-05T11:00:00Z",
    "status": "BUSY"
  },
  ...
]
PUT /api/events/:id (Protected)

json
Request:
{
  "title": "Team Standup",
  "status": "SWAPPABLE"
}

Response (200):
{ ...updated event }
Swap Endpoints
GET /api/swappable-slots (Protected)

text
Response (200):
[
  {
    "id": 5,
    "userId": 2,
    "username": "jane_doe",
    "title": "Focus Block",
    "startTime": "2025-11-05T14:00:00Z",
    "endTime": "2025-11-05T15:00:00Z",
    "status": "SWAPPABLE"
  },
  ...
]
POST /api/swap-request (Protected)

json
Request:
{
  "mySlotId": 5,
  "theirSlotId": 8
}

Response (201):
{
  "id": 12,
  "requesterId": 1,
  "requesteeId": 2,
  "requesterSlotId": 5,
  "requesteeSlotId": 8,
  "status": "PENDING"
}

Error (400):
{ "error": "One or both slots are not SWAPPABLE" }
POST /api/swap-response/:requestId (Protected)

json
Request:
{
  "accept": true
}

Response (200):
{
  "message": "Swap accepted",
  "swapRequest": { ...updated with ACCEPTED status }
}

On Accept: Events swapped, both set to BUSY
On Reject: Events reverted to SWAPPABLE
Frontend Implementation
State Management Structure
javascript
// AuthContext
{
  currentUser: {
    id: 1,
    email: "user@example.com",
    username: "john_doe"
  },
  accessToken: "eyJhbGc...",
  refreshToken: "eyJhbGc...",
  isAuthenticated: true,
  loading: false,
  error: null
}

// EventsContext
{
  userEvents: [
    {
      id: 5,
      title: "Team Meeting",
      startTime: "2025-11-05T10:00:00Z",
      endTime: "2025-11-05T11:00:00Z",
      status: "SWAPPABLE"
    }
  ],
  swappableSlots: [
    {
      id: 8,
      userId: 2,
      username: "jane_doe",
      title: "Focus Block",
      startTime: "2025-11-05T14:00:00Z",
      endTime: "2025-11-05T15:00:00Z",
      status: "SWAPPABLE"
    }
  ],
  loading: false,
  error: null
}

// SwapRequestsContext
{
  incomingRequests: [
    {
      id: 12,
      requesterName: "bob",
      requesterSlot: {...},
      requesteeSlot: {...},
      status: "PENDING"
    }
  ],
  outgoingRequests: [
    {
      id: 11,
      requesteeName: "alice",
      requesterSlot: {...},
      requesteeSlot: {...},
      status: "PENDING"
    }
  ],
  loading: false,
  error: null
}
Component Hierarchy
text
App
├── AuthPages (Login/Signup)
│   ├── LoginForm
│   ├── SignUpForm
│   └── FormValidator
├── MainLayout (Protected)
│   ├── Navigation
│   ├── Routes
│   │   ├── Dashboard
│   │   │   ├── EventList
│   │   │   │   ├── EventCard
│   │   │   │   └── EventForm (Modal)
│   │   │   └── CreateEventButton
│   │   ├── Marketplace
│   │   │   ├── SlotList
│   │   │   │   ├── SlotCard
│   │   │   │   └── SwapModal
│   │   │   └── Filters
│   │   └── NotificationCenter
│   │       ├── IncomingRequests
│   │       │   └── RequestCard (with Accept/Reject)
│   │       └── OutgoingRequests
│   │           └── RequestCard (with Cancel)
│   └── Toast/Notification
└── Providers
    ├── AuthProvider
    ├── EventsProvider
    └── SwapRequestsProvider
Custom Hooks
useAuth() - Handle authentication state and actions

javascript
const { login, signup, logout, currentUser, accessToken } = useAuth();
useEvents() - Handle event CRUD operations

javascript
const { createEvent, updateEvent, deleteEvent, userEvents, swappableSlots, loading } = useEvents();
useSwaps() - Handle swap request operations

javascript
const { createSwapRequest, acceptSwap, rejectSwap, incomingRequests, outgoingRequests } = useSwaps();
useWebSocket() - Handle Socket.io connection and events

javascript
const { isConnected, subscribeToNotifications } = useWebSocket();
Backend Implementation
Middleware Stack
javascript
// Error handling middleware (bottom)
app.use((err, req, res, next) => {
  console.error(err);
  res.status(err.status || 500).json({ 
    error: err.message || "Internal server error" 
  });
});

// Authentication middleware (verify JWT on protected routes)
function verifyToken(req, res, next) {
  const token = req.headers.authorization?.split(" ");
  if (!token) return res.status(401).json({ error: "No token" });
  try {
    req.user = jwt.verify(token, process.env.JWT_SECRET);
    next();
  } catch (err) {
    res.status(401).json({ error: "Invalid token" });
  }
}

// CORS middleware
app.use(cors({
  origin: process.env.FRONTEND_URL,
  credentials: true
}));

// Rate limiting on auth endpoints (bonus feature)
const authLimiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 5, // 5 login attempts
  message: "Too many login attempts, try again later"
});
Request Validation
javascript
// Example: Sign up validation
const signupValidation = [
  body('email').isEmail().normalizeEmail(),
  body('username').isLength({ min: 3, max: 30 }),
  body('password').isLength({ min: 8 }).matches(/[A-Z]/).matches(/[0-9]/)
];

router.post('/signup', signupValidation, (req, res) => {
  const errors = validationResult(req);
  if (!errors.isEmpty()) {
    return res.status(400).json({ errors: errors.array() });
  }
  // Process signup...
});
Swap Logic Implementation
javascript
async function acceptSwap(swapRequestId) {
  const client = await pool.connect();
  try {
    await client.query('BEGIN');
    
    // Fetch swap request details
    const swapResult = await client.query(
      'SELECT * FROM swapRequests WHERE id = $1',
      [swapRequestId]
    );
    const { requesterSlotId, requesteeSlotId, requesterId, requesteeId } = swapResult.rows;
    
    // Verify both slots are SWAPPABLE
    const slotCheck = await client.query(
      'SELECT * FROM events WHERE id = ANY($1) AND status = $2',
      [[requesterSlotId, requesteeSlotId], 'SWAPPABLE']
    );
    
    if (slotCheck.rowCount !== 2) {
      throw new Error('One or both slots are no longer swappable');
    }
    
    // Atomic swap: exchange userId
    await client.query(
      'UPDATE events SET userId = $1 WHERE id = $2',
      [requesteeId, requesterSlotId]
    );
    
    await client.query(
      'UPDATE events SET userId = $1 WHERE id = $2',
      [requesterId, requesteeSlotId]
    );
    
    // Set both slots to BUSY
    await client.query(
      'UPDATE events SET status = $1 WHERE id = ANY($2)',
      ['BUSY', [requesterSlotId, requesteeSlotId]]
    );
    
    // Mark swap as ACCEPTED
    await client.query(
      'UPDATE swapRequests SET status = $1, respondedAt = NOW() WHERE id = $2',
      ['ACCEPTED', swapRequestId]
    );
    
    await client.query('COMMIT');
    
    // Emit WebSocket events to both users
    io.to(userSockets[requesterId]).emit('swap-accepted', {...});
    io.to(userSockets[requesteeId]).emit('swap-accepted', {...});
    
  } catch (error) {
    await client.query('ROLLBACK');
    throw error;
  } finally {
    client.release();
  }
}
Testing Strategy
Unit Tests (Jest)
javascript
// __tests__/auth.test.js
describe('Authentication', () => {
  test('should hash password correctly', () => {
    const hashedPassword = hashPassword('myPassword123');
    expect(hashedPassword).not.toBe('myPassword123');
    expect(comparePassword('myPassword123', hashedPassword)).toBe(true);
  });
  
  test('should generate valid JWT', () => {
    const token = generateJWT({ userId: 1, email: 'test@example.com' });
    const decoded = jwt.verify(token, process.env.JWT_SECRET);
    expect(decoded.userId).toBe(1);
  });
});

// __tests__/swap.test.js
describe('Swap Logic', () => {
  test('should accept swap and exchange slot ownership', async () => {
    // Setup: Create two users and two events
    const user1 = await createUser({ email: 'user1@test.com' });
    const user2 = await createUser({ email: 'user2@test.com' });
    const event1 = await createEvent({ userId: user1.id, status: 'SWAPPABLE' });
    const event2 = await createEvent({ userId: user2.id, status: 'SWAPPABLE' });
    const swapRequest = await createSwapRequest({
      requesterId: user1.id,
      requesteeId: user2.id,
      requesterSlotId: event1.id,
      requesteeSlotId: event2.id
    });
    
    // Execute: Accept swap
    await acceptSwap(swapRequest.id);
    
    // Assert
    const updatedEvent1 = await getEvent(event1.id);
    const updatedEvent2 = await getEvent(event2.id);
    expect(updatedEvent1.userId).toBe(user2.id);
    expect(updatedEvent2.userId).toBe(user1.id);
    expect(updatedEvent1.status).toBe('BUSY');
    expect(updatedEvent2.status).toBe('BUSY');
  });
});
Integration Tests (Supertest)
javascript
// __tests__/api.test.js
describe('API Endpoints', () => {
  test('POST /api/auth/signup - should create new user', async () => {
    const res = await request(app)
      .post('/api/auth/signup')
      .send({
        email: 'newuser@test.com',
        username: 'newuser',
        password: 'Password123'
      });
    
    expect(res.statusCode).toBe(201);
    expect(res.body).toHaveProperty('userId');
  });
  
  test('POST /api/swap-request - should create swap request', async () => {
    // Login as user1, get auth token
    const loginRes = await request(app)
      .post('/api/auth/login')
      .send({ email: 'user1@test.com', password: 'pass123' });
    
    const token = loginRes.body.accessToken;
    
    // Create swap request with auth
    const res = await request(app)
      .post('/api/swap-request')
      .set('Authorization', `Bearer ${token}`)
      .send({
        mySlotId: 5,
        theirSlotId: 8
      });
    
    expect(res.statusCode).toBe(201);
    expect(res.body.status).toBe('PENDING');
  });
});
Deployment
Docker Setup
Dockerfile (Backend):

text
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
EXPOSE 3000
CMD ["node", "server.js"]
Dockerfile (Frontend):

text
FROM node:18-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
docker-compose.yml:

text
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: slotswapper
      POSTGRES_PASSWORD: dev_password
      POSTGRES_DB: slotswapper
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  backend:
    build: ./backend
    ports:
      - "3000:3000"
    environment:
      DATABASE_URL: postgresql://slotswapper:dev_password@postgres:5432/slotswapper
      JWT_SECRET: your_jwt_secret_key
      FRONTEND_URL: http://localhost:5173
    depends_on:
      - postgres
    volumes:
      - ./backend:/app
      - /app/node_modules

  frontend:
    build: ./frontend
    ports:
      - "80:80"
    depends_on:
      - backend

volumes:
  postgres_data:
Run locally:

bash
docker-compose up --build
# Frontend: http://localhost
# Backend: http://localhost:3000
# Database: localhost:5432
Production Deployment
Recommended platforms:

Frontend: Vercel, Netlify (static hosting with CI/CD)

Backend: Render, Railway, AWS EC2 (Node.js hosting)

Database: AWS RDS, Heroku PostgreSQL, Digital Ocean Managed Databases

Real-time: Use managed Socket.io services or Redis adapter for scaling

Production Checklist:

 HTTPS enabled (SSL certificates via Let's Encrypt)

 Environment variables secured (.env not committed)

 Database backups automated

 Rate limiting on all auth endpoints

 CORS configured properly (only allow frontend domain)

 Tokens stored in HttpOnly cookies (not localStorage)

 Input validation and XSS protection

 SQL injection prevention (parameterized queries)

 CSRF tokens for state-changing operations

 Logging and monitoring setup (e.g., DataDog, New Relic)

 Error tracking (e.g., Sentry)

 Load balancing for multiple backend instances

 Redis for session management and caching

Common Issues & Solutions
Issue: WebSocket connection fails
Solution: Ensure Socket.io is correctly configured on both frontend and backend. Use transports: ['websocket', 'polling'] fallback in production.

Issue: Swap transaction deadlock
Solution: Always acquire locks in the same order (by ID) to prevent circular waits. Use transaction isolation level SERIALIZABLE for critical operations.

Issue: Tokens not persisting after page refresh
Solution: Store refresh token in HttpOnly cookie (automatic with credentials: include). Implement token refresh logic on app startup.

Issue: Real-time notifications not arriving
Solution: Verify user-to-socket ID mapping is maintained. Check Socket.io rooms and authentication on connection event.

Issue: CORS errors in production
Solution: Configure CORS with exact frontend URL, enable credentials: true, ensure preflight requests are handled.

Future Enhancements
Recurring Events - Support recurring event patterns (daily, weekly, monthly)

Conflict Detection - Prevent overlapping time slots

Event Categories - Tag events (work, personal, etc.)

Timezone Support - Handle users in different timezones

Calendar Integration - Sync with Google Calendar, Outlook

Analytics - Track swap success rates, popular time slots

Ratings & Reviews - Users rate swap partners

Undo/History - Track swap history and allow undoing swaps

Mobile App - React Native version with offline support

Advanced Matching - AI-powered recommendations for compatible swaps

Security Considerations
Input Validation: All user inputs validated server-side and client-side

XSS Protection: HTML entities escaped, no innerHTML with user data

CSRF Protection: Tokens for state-changing operations

SQL Injection: Parameterized queries with prepared statements

Rate Limiting: Prevent brute force attacks on auth endpoints

JWT Security: Short expiration times, secure signing algorithm

Password Security: Min 8 chars, uppercase + numbers required, hashed with bcrypt

HTTPS Mandatory: All communication encrypted in transit

Secure Cookies: HttpOnly, Secure, SameSite flags set

Performance Optimization
Database Indexing: Indexes on userId, status, timestamps for fast queries

Connection Pooling: Reuse database connections to reduce overhead

Caching: Cache swappable slots for 1 minute to reduce DB hits

Pagination: Limit query results to 50 events per page

WebSocket Optimization: Use rooms for targeted broadcasts instead of all clients

Frontend Code Splitting: Lazy load components based on routes

Compression: gzip compression on all responses

Monitoring & Logging
javascript
// Example: Structured logging
logger.info('Swap accepted', {
  swapRequestId: 12,
  requesterId: 1,
  requesteeId: 2,
  timestamp: new Date().toISOString(),
  duration: executionTime
});

logger.error('Swap failed', {
  swapRequestId: 12,
  error: err.message,
  stack: err.stack
});
Conclusion
SlotSwapper demonstrates a complete full-stack application with complex requirements:

Atomic transactions for financial-grade reliability

Real-time WebSocket communication

JWT-based authentication and authorization

Comprehensive state management

Production-ready error handling and validation

Containerization and deployment strategies

The architecture is scalable, secure, and maintainable, serving as a foundation for similar peer-to-peer exchange platforms.
