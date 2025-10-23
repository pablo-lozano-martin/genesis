# API Reference

Quick reference for Genesis API endpoints. Full interactive documentation available at `/docs` when running.

## Base URLs

- Development: `http://localhost:8000`
- Production: `https://your-domain.com`

## Authentication

Most endpoints require JWT authentication via `Authorization: Bearer <token>` header.

### Authentication Endpoints

#### Register User
`POST /api/auth/register`

Creates a new user account.

**Body**: `{ email, username, password, full_name }`
**Returns**: User object (201)
**Errors**: 400 (email/username exists), 422 (validation error)

#### Login
`POST /api/auth/token`

Get access token for authentication.

**Body** (form data): `username=<user>&password=<pass>`
**Headers**: `Content-Type: application/x-www-form-urlencoded`
**Returns**: `{ access_token, token_type }` (200)
**Errors**: 401 (invalid credentials)

#### Refresh Token
`POST /api/auth/refresh`

Get new access token using valid token.

**Headers**: `Authorization: Bearer <token>`
**Returns**: `{ access_token, token_type }` (200)
**Errors**: 401 (invalid/expired token)

#### Get Current User
`GET /api/auth/me`

Get authenticated user information.

**Headers**: `Authorization: Bearer <token>`
**Returns**: User object (200)
**Errors**: 401 (not authenticated)

### User Endpoints

#### Get User Profile
`GET /api/user/me`

Get current user's profile (same as `/api/auth/me`).

#### Update User Profile
`PATCH /api/user/me`

Update user profile information.

**Body** (all optional): `{ email, username, full_name }`
**Returns**: Updated user object (200)
**Errors**: 400 (email/username in use), 401 (not authenticated)

### Conversation Endpoints

#### List Conversations
`GET /api/conversations?skip=0&limit=100`

Get all conversations for authenticated user.

**Query Params**:
- `skip` (int, default: 0)
- `limit` (int, default: 100, max: 100)

**Returns**: Array of conversation objects (200)

#### Create Conversation
`POST /api/conversations`

Create a new conversation.

**Body** (optional): `{ title }`
**Returns**: Conversation object (201)

#### Get Conversation
`GET /api/conversations/{conversation_id}`

Get specific conversation by ID.

**Returns**: Conversation object (200)
**Errors**: 403 (access denied), 404 (not found)

#### Update Conversation
`PATCH /api/conversations/{conversation_id}`

Update conversation title.

**Body**: `{ title }`
**Returns**: Updated conversation object (200)

#### Delete Conversation
`DELETE /api/conversations/{conversation_id}`

Delete conversation and all messages.

**Returns**: 204 (no content)

### Message Endpoints

#### Get Conversation Messages
`GET /api/conversations/{conversation_id}/messages?skip=0&limit=100`

Get all messages in a conversation.

**Query Params**:
- `skip` (int, default: 0)
- `limit` (int, default: 100, max: 500)

**Returns**: Array of message objects (200)
**Errors**: 403 (access denied), 404 (conversation not found)

#### Create Message
`POST /api/conversations/{conversation_id}/messages`

Send a message and get AI assistant response.

**Body**:
```json
{
  "content": "Your message here",
  "metadata": {}  // optional
}
```

**Returns**: Message pair object (201)
```json
{
  "user_message": {
    "id": "507f1f77bcf86cd799439013",
    "conversation_id": "507f1f77bcf86cd799439012",
    "role": "user",
    "content": "Your message here",
    "created_at": "2025-01-15T10:30:00",
    "metadata": null
  },
  "assistant_message": {
    "id": "507f1f77bcf86cd799439014",
    "conversation_id": "507f1f77bcf86cd799439012",
    "role": "assistant",
    "content": "AI response...",
    "created_at": "2025-01-15T10:30:01",
    "metadata": null
  }
}
```

**Errors**:
- 401 (not authenticated)
- 403 (access denied - not conversation owner)
- 404 (conversation not found)
- 422 (validation error - empty content)
- 500 (LLM provider error)

### Health Check

#### Health Check
`GET /api/health`

Check if API is running.

**Returns**: `{ status: "healthy", app: "Genesis", version: "0.1.0" }` (200)

## HTTP Status Codes

- `200` OK - Success
- `201` Created - Resource created
- `204` No Content - Success, no body
- `400` Bad Request - Invalid data
- `401` Unauthorized - Auth required/failed
- `403` Forbidden - Access denied
- `404` Not Found - Resource not found
- `422` Unprocessable Entity - Validation error
- `500` Internal Server Error - Server error

## Error Response Format

All errors follow this format:
```json
{
  "detail": "Error message description"
}
```

## Notes

- Pagination supported on list endpoints via `skip` and `limit` params
- Results ordered by most recent first
- See `/docs` for interactive API documentation (Swagger UI)
- See `/redoc` for alternative documentation (ReDoc)
