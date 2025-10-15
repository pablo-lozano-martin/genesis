# Genesis API Documentation

Complete API reference for the Genesis chatbot application.

## Base URL

- **Development**: `http://localhost:8000`
- **Production**: `https://your-domain.com`

## Interactive Documentation

When running the application, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Authentication

Most endpoints require authentication via JWT tokens.

### Getting a Token

1. Register a user (see `/api/auth/register`)
2. Login to get a token (see `/api/auth/token`)
3. Include token in requests: `Authorization: Bearer <token>`

---

## Authentication Endpoints

### Register User

Create a new user account.

**Endpoint**: `POST /api/auth/register`

**Request Body**:
```json
{
  "email": "user@example.com",
  "username": "johndoe",
  "password": "securepassword123",
  "full_name": "John Doe"
}
```

**Response** (201 Created):
```json
{
  "id": "507f1f77bcf86cd799439011",
  "email": "user@example.com",
  "username": "johndoe",
  "full_name": "John Doe",
  "is_active": true,
  "created_at": "2025-01-15T10:30:00"
}
```

**Errors**:
- `400`: Email or username already exists
- `422`: Validation error (invalid email, short password, etc.)

---

### Login

Get an access token for authentication.

**Endpoint**: `POST /api/auth/token`

**Request Body** (form data):
```
username=johndoe
password=securepassword123
```

**Headers**:
```
Content-Type: application/x-www-form-urlencoded
```

**Response** (200 OK):
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Errors**:
- `401`: Invalid credentials

---

### Refresh Token

Get a new access token using a valid token.

**Endpoint**: `POST /api/auth/refresh`

**Headers**:
```
Authorization: Bearer <your-token>
```

**Response** (200 OK):
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Errors**:
- `401`: Invalid or expired token

---

### Get Current User

Get information about the authenticated user.

**Endpoint**: `GET /api/auth/me`

**Headers**:
```
Authorization: Bearer <your-token>
```

**Response** (200 OK):
```json
{
  "id": "507f1f77bcf86cd799439011",
  "email": "user@example.com",
  "username": "johndoe",
  "full_name": "John Doe",
  "is_active": true,
  "created_at": "2025-01-15T10:30:00"
}
```

**Errors**:
- `401`: Not authenticated

---

## User Endpoints

### Get User Profile

Get the current user's profile (same as `/api/auth/me`).

**Endpoint**: `GET /api/user/me`

**Headers**:
```
Authorization: Bearer <your-token>
```

**Response**: Same as `/api/auth/me`

---

### Update User Profile

Update the current user's profile information.

**Endpoint**: `PATCH /api/user/me`

**Headers**:
```
Authorization: Bearer <your-token>
```

**Request Body**:
```json
{
  "email": "newemail@example.com",
  "username": "newusername",
  "full_name": "New Name"
}
```

All fields are optional.

**Response** (200 OK):
```json
{
  "id": "507f1f77bcf86cd799439011",
  "email": "newemail@example.com",
  "username": "newusername",
  "full_name": "New Name",
  "is_active": true,
  "created_at": "2025-01-15T10:30:00"
}
```

**Errors**:
- `400`: Email or username already in use
- `401`: Not authenticated

---

## Conversation Endpoints

### List Conversations

Get all conversations for the authenticated user.

**Endpoint**: `GET /api/conversations`

**Headers**:
```
Authorization: Bearer <your-token>
```

**Query Parameters**:
- `skip` (int, default: 0): Number of conversations to skip
- `limit` (int, default: 100, max: 100): Maximum conversations to return

**Response** (200 OK):
```json
[
  {
    "id": "507f1f77bcf86cd799439012",
    "user_id": "507f1f77bcf86cd799439011",
    "title": "Python Decorators Discussion",
    "created_at": "2025-01-15T10:30:00",
    "updated_at": "2025-01-15T11:45:00",
    "message_count": 8
  },
  {
    "id": "507f1f77bcf86cd799439013",
    "user_id": "507f1f77bcf86cd799439011",
    "title": "FastAPI Best Practices",
    "created_at": "2025-01-14T09:00:00",
    "updated_at": "2025-01-14T09:30:00",
    "message_count": 4
  }
]
```

**Errors**:
- `401`: Not authenticated

---

### Create Conversation

Create a new conversation.

**Endpoint**: `POST /api/conversations`

**Headers**:
```
Authorization: Bearer <your-token>
```

**Request Body**:
```json
{
  "title": "New Conversation"
}
```

`title` is optional, defaults to "New Conversation".

**Response** (201 Created):
```json
{
  "id": "507f1f77bcf86cd799439014",
  "user_id": "507f1f77bcf86cd799439011",
  "title": "New Conversation",
  "created_at": "2025-01-15T12:00:00",
  "updated_at": "2025-01-15T12:00:00",
  "message_count": 0
}
```

**Errors**:
- `401`: Not authenticated

---

### Get Conversation

Get a specific conversation by ID.

**Endpoint**: `GET /api/conversations/{conversation_id}`

**Headers**:
```
Authorization: Bearer <your-token>
```

**Response** (200 OK):
```json
{
  "id": "507f1f77bcf86cd799439012",
  "user_id": "507f1f77bcf86cd799439011",
  "title": "Python Decorators Discussion",
  "created_at": "2025-01-15T10:30:00",
  "updated_at": "2025-01-15T11:45:00",
  "message_count": 8
}
```

**Errors**:
- `401`: Not authenticated
- `403`: Access denied (conversation belongs to another user)
- `404`: Conversation not found

---

### Update Conversation

Update a conversation's title.

**Endpoint**: `PATCH /api/conversations/{conversation_id}`

**Headers**:
```
Authorization: Bearer <your-token>
```

**Request Body**:
```json
{
  "title": "Updated Title"
}
```

**Response** (200 OK):
```json
{
  "id": "507f1f77bcf86cd799439012",
  "user_id": "507f1f77bcf86cd799439011",
  "title": "Updated Title",
  "created_at": "2025-01-15T10:30:00",
  "updated_at": "2025-01-15T12:30:00",
  "message_count": 8
}
```

**Errors**:
- `401`: Not authenticated
- `403`: Access denied
- `404`: Conversation not found

---

### Delete Conversation

Delete a conversation and all its messages.

**Endpoint**: `DELETE /api/conversations/{conversation_id}`

**Headers**:
```
Authorization: Bearer <your-token>
```

**Response** (204 No Content)

**Errors**:
- `401`: Not authenticated
- `403`: Access denied
- `404`: Conversation not found

---

## Message Endpoints

### Get Conversation Messages

Get all messages in a conversation.

**Endpoint**: `GET /api/conversations/{conversation_id}/messages`

**Headers**:
```
Authorization: Bearer <your-token>
```

**Query Parameters**:
- `skip` (int, default: 0): Number of messages to skip
- `limit` (int, default: 100, max: 500): Maximum messages to return

**Response** (200 OK):
```json
[
  {
    "id": "507f1f77bcf86cd799439015",
    "conversation_id": "507f1f77bcf86cd799439012",
    "role": "user",
    "content": "What are Python decorators?",
    "created_at": "2025-01-15T10:30:00",
    "metadata": null
  },
  {
    "id": "507f1f77bcf86cd799439016",
    "conversation_id": "507f1f77bcf86cd799439012",
    "role": "assistant",
    "content": "Python decorators are functions that modify the behavior of other functions...",
    "created_at": "2025-01-15T10:30:15",
    "metadata": null
  }
]
```

**Errors**:
- `401`: Not authenticated
- `403`: Access denied
- `404`: Conversation not found

---

## WebSocket Endpoint

### Real-time Chat

Stream messages to and from the AI assistant in real-time.

**Endpoint**: `WS /ws/chat`

**Authentication**:

Include token as query parameter or header:
- Query: `ws://localhost:8000/ws/chat?token=<your-token>`
- Header: `Authorization: Bearer <your-token>`

### Client → Server Messages

**Send Message**:
```json
{
  "type": "message",
  "conversation_id": "507f1f77bcf86cd799439012",
  "content": "What are Python decorators?"
}
```

**Ping** (keep-alive):
```json
{
  "type": "ping"
}
```

### Server → Client Messages

**Streaming Token**:
```json
{
  "type": "token",
  "content": "Python "
}
```

Multiple token messages are sent as the AI generates the response.

**Completion**:
```json
{
  "type": "complete",
  "message_id": "507f1f77bcf86cd799439017",
  "conversation_id": "507f1f77bcf86cd799439012"
}
```

**Error**:
```json
{
  "type": "error",
  "message": "Failed to generate response",
  "code": "LLM_ERROR"
}
```

**Pong**:
```json
{
  "type": "pong"
}
```

**Error Codes**:
- `ACCESS_DENIED`: User doesn't own the conversation
- `INVALID_FORMAT`: Invalid message format
- `LLM_ERROR`: LLM generation failed
- `INTERNAL_ERROR`: Server error

---

## Health Check

### Health Check

Check if the API is running.

**Endpoint**: `GET /api/health`

**Response** (200 OK):
```json
{
  "status": "healthy",
  "app": "Genesis",
  "version": "0.1.0"
}
```

---

## Error Responses

All error responses follow this format:

```json
{
  "detail": "Error message description"
}
```

### HTTP Status Codes

- `200 OK`: Success
- `201 Created`: Resource created successfully
- `204 No Content`: Success with no response body
- `400 Bad Request`: Invalid request data
- `401 Unauthorized`: Authentication required or failed
- `403 Forbidden`: Authenticated but access denied
- `404 Not Found`: Resource not found
- `422 Unprocessable Entity`: Validation error
- `500 Internal Server Error`: Server error

---

## Rate Limiting

Currently, no rate limiting is implemented. For production deployments, consider adding:
- Rate limiting middleware
- Per-user request limits
- API usage tracking

---

## Pagination

List endpoints support pagination via `skip` and `limit` parameters:

```
GET /api/conversations?skip=0&limit=20
```

- Results are ordered by most recent first
- Default limit: 100
- Maximum limit: Varies by endpoint

---

## Examples

### Complete Authentication Flow

```bash
# 1. Register
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","username":"user","password":"pass123","full_name":"User"}'

# 2. Login
curl -X POST http://localhost:8000/api/auth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=user&password=pass123"

# 3. Use token
TOKEN="<token-from-login>"
curl http://localhost:8000/api/user/me \
  -H "Authorization: Bearer $TOKEN"
```

### Create and Use Conversation

```bash
TOKEN="<your-token>"

# Create conversation
CONV_ID=$(curl -X POST http://localhost:8000/api/conversations \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"Test Chat"}' | jq -r '.id')

# Get messages
curl http://localhost:8000/api/conversations/$CONV_ID/messages \
  -H "Authorization: Bearer $TOKEN"
```

### WebSocket Chat (JavaScript)

```javascript
const token = "<your-token>";
const ws = new WebSocket(`ws://localhost:8000/ws/chat?token=${token}`);

ws.onopen = () => {
  ws.send(JSON.stringify({
    type: "message",
    conversation_id: "<conversation-id>",
    content: "Hello!"
  }));
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);

  if (data.type === "token") {
    console.log("Token:", data.content);
  } else if (data.type === "complete") {
    console.log("Complete:", data.message_id);
  }
};
```

---

## Support

For issues or questions:
- Check logs: `docker-compose logs backend`
- Review API docs: http://localhost:8000/docs
- Open an issue on GitHub
