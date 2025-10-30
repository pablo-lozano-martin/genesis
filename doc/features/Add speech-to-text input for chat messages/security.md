# Security Analysis

## Request Summary
Adding speech-to-text input functionality for chat messages, which involves:
- Recording audio in the browser
- Uploading audio files to the backend
- Sending audio to an external transcription service
- Inserting transcribed text into messages

## Relevant Files & Modules

### Files to Examine

#### Authentication & Authorization
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/infrastructure/security/auth_service.py` - JWT token generation, verification, password hashing
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/infrastructure/security/dependencies.py` - OAuth2 authentication dependencies, `CurrentUser` type
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/infrastructure/security/websocket_auth.py` - WebSocket JWT authentication from query params or headers
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/ports/auth_service.py` - Authentication service interface

#### API Routers & Endpoints
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/auth_router.py` - Registration, login, token refresh endpoints
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/conversation_router.py` - Conversation CRUD with ownership verification
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/message_router.py` - Message retrieval with conversation ownership checks
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/websocket_router.py` - WebSocket endpoints for chat and onboarding

#### Configuration & Settings
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/infrastructure/config/settings.py` - Environment configuration, CORS settings, token expiration
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/main.py` - Application entry point, middleware configuration

#### Domain Models
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/domain/user.py` - User model with field validation (min_length, max_length)
- `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/domain/conversation.py` - Conversation model with field validation

#### Dependencies & Requirements
- `/Users/pablolozano/Mac Projects August/genesis/backend/requirements.txt` - Python dependencies including security libraries
- `/Users/pablolozano/Mac Projects August/genesis/.env.example` - Environment variable template

### Key Functions & Classes

#### Authentication Functions
- `AuthService.hash_password()` - Bcrypt password hashing (12 rounds)
- `AuthService.verify_password()` - Password verification
- `AuthService.create_access_token()` - JWT token generation with expiration
- `AuthService.verify_token()` - JWT token validation
- `get_current_user()` in `dependencies.py` - Dependency for protected routes
- `get_user_from_websocket()` in `websocket_auth.py` - WebSocket authentication

#### Authorization Functions
- Conversation ownership verification in `conversation_router.py` (lines 99-104, 138-143, 179-185)
- Message access control in `message_router.py` (lines 38-53)

#### Validation Patterns
- Pydantic `Field()` with `min_length`, `max_length` constraints on User and Conversation models
- Query parameter validation with `Query()` and `ge`, `le` constraints
- Email validation with `EmailStr` type

## Current Security Overview

### Authentication

**JWT-Based Authentication**:
- Uses `python-jose[cryptography]` for JWT token operations
- Token algorithm: HS256 (HMAC with SHA-256)
- Token expiration: 30 minutes (configurable via `ACCESS_TOKEN_EXPIRE_MINUTES`)
- Secret key stored in environment variables (`SECRET_KEY`)
- Tokens include: `sub` (user_id), `exp` (expiration), `type` ("access")

**Password Security**:
- Bcrypt hashing with `passlib` and `bcrypt==4.0.1`
- Default bcrypt rounds: 12 (via `CryptContext`)
- Passwords require minimum 8 characters (validated in `UserCreate` model)

**OAuth2 Password Flow**:
- FastAPI's `OAuth2PasswordBearer` for token URL declaration
- Token sent via `Authorization: Bearer <token>` header
- WebSocket authentication supports both query parameter (`?token=`) and `Authorization` header

### Authorization

**User Isolation & Ownership Verification**:
- All conversation operations verify `conversation.user_id == current_user.id`
- 403 Forbidden returned when user attempts to access resources they don't own
- Authorization checks occur before any data retrieval or modification
- Two-database pattern: App DB verifies ownership before accessing LangGraph state

**Active User Enforcement**:
- `is_active` flag checked in `get_current_user()` dependency
- Inactive users receive 403 Forbidden on all protected endpoints
- WebSocket connections rejected for inactive users

### Data Protection

**Password Handling**:
- Plaintext passwords never stored or logged
- Hashed passwords stored in MongoDB using bcrypt
- Password field excluded from all API responses (only in `UserCreate`, not `UserResponse`)

**Token Security**:
- JWT tokens signed with secret key
- Token verification catches `JWTError` and returns None (logged as warning)
- Expired tokens rejected automatically by `jwt.decode()`

**Database Security**:
- MongoDB connection strings stored in environment variables
- Credentials never hardcoded in source code
- Separate databases for app data and LangGraph state

### Security Middleware

**CORS Configuration**:
- Configured in `main.py` (lines 160-166)
- Origins whitelist from environment (`CORS_ORIGINS`)
- Credentials allowed: `allow_credentials=True`
- All methods and headers allowed (may be overly permissive)

**No Rate Limiting**:
- No rate limiting library detected (e.g., slowapi, FastAPI-Limiter)
- No rate limiting decorators or middleware in codebase
- Potential vulnerability: API abuse, brute force attacks, DoS

**No Input Sanitization Middleware**:
- Relies on Pydantic validation only
- No explicit XSS prevention or content security policies
- No file upload handling currently exists

**No Request Size Limits**:
- No explicit maximum request body size configuration detected
- FastAPI default is 16 MB (may be sufficient but not explicitly configured)

## Impact Analysis

### Components Affected by Audio Upload Feature

**New API Endpoint Required**:
- New router for audio upload endpoint (e.g., `/api/audio/transcribe`)
- Must be protected with `CurrentUser` dependency
- Must validate conversation ownership before processing audio

**WebSocket Alternative**:
- Audio could be sent via WebSocket connection (already authenticated)
- Would require binary message handling or base64 encoding
- May hit WebSocket message size limits

**External Service Integration**:
- Transcription service (e.g., OpenAI Whisper, Google Speech-to-Text)
- Requires API key management in environment variables
- Network egress to third-party service (privacy implications)

**File Handling Layer**:
- New infrastructure for temporary file storage
- Audio file validation (MIME type, size, duration)
- File cleanup after transcription

**LLM Provider Layer**:
- No changes needed (transcription happens before message creation)
- Transcribed text flows through existing WebSocket message handling

## Security Recommendations

### Authentication Changes

**No Changes Needed**:
- Existing JWT authentication is sufficient for audio upload endpoint
- Use `CurrentUser` dependency to protect new upload endpoint
- Reuse WebSocket authentication if implementing audio streaming

**Recommendation**:
```python
# New audio router
@router.post("/api/audio/transcribe")
async def transcribe_audio(
    audio_file: UploadFile,
    conversation_id: str,
    current_user: CurrentUser  # Existing auth dependency
):
    # Verify conversation ownership
    # Process audio
    # Return transcription
```

### Authorization Changes

**Conversation Ownership Verification Required**:
- Audio upload must verify user owns the target conversation
- Follow existing pattern from `conversation_router.py`:
  ```python
  conversation = await conversation_repository.get_by_id(conversation_id)
  if not conversation or conversation.user_id != current_user.id:
      raise HTTPException(status_code=403, detail="Access denied")
  ```

**User Quota Enforcement (Recommended)**:
- Track audio transcription usage per user (prevents abuse)
- Store quota in User model or separate usage tracking collection
- Return 429 Too Many Requests when quota exceeded

### Data Protection Changes

**Audio File Encryption**:
- Audio files contain sensitive voice data (more personal than text)
- **Recommendation**: Encrypt audio files at rest if stored temporarily
- Use `cryptography` library (already in dependencies via `python-jose[cryptography]`)
- Example: AES-256 encryption with user-specific or ephemeral keys

**Secure Temporary Storage**:
- Audio files should NOT be stored in web-accessible directories
- Use OS temporary directory with secure permissions: `tempfile.mkdtemp()`
- Set file permissions to 600 (owner read/write only)
- Clean up files immediately after transcription (use context managers or `finally` blocks)

**API Key Protection**:
- Transcription service API keys must be stored in environment variables
- NEVER log API keys or include in error messages
- Use separate API keys for dev/staging/production environments

**Data Minimization**:
- Delete audio files immediately after successful transcription
- Do not store audio files or transcriptions longer than necessary
- Consider not logging audio file names or paths

### Security Controls Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                      Client Browser                          │
│  1. Record audio via MediaRecorder API                      │
│  2. Send audio file with JWT token                          │
└────────────────────┬────────────────────────────────────────┘
                     │
                     │ HTTPS (TLS 1.2+)
                     │ Authorization: Bearer <jwt_token>
                     │ Content-Type: multipart/form-data
                     │
┌────────────────────▼────────────────────────────────────────┐
│                  FastAPI Backend                             │
│                                                              │
│  3. Authentication Middleware                                │
│     - Verify JWT token (get_current_user)                   │
│     - Check user is_active status                           │
│                                                              │
│  4. Authorization Check                                      │
│     - Verify conversation ownership                         │
│     - Check user quota (if implemented)                     │
│                                                              │
│  5. Input Validation                                         │
│     - MIME type: audio/webm, audio/wav, audio/mp3          │
│     - File size: <= 25 MB (recommended)                     │
│     - Duration: <= 5 minutes (recommended)                  │
│     - Magic number verification (not just extension)        │
│                                                              │
│  6. Rate Limiting (RECOMMENDED)                             │
│     - Per-user: 10 requests/minute                         │
│     - Per-IP: 20 requests/minute                           │
│                                                              │
│  7. Secure File Handling                                    │
│     - Save to secure temp directory (tempfile)              │
│     - Encrypt at rest (AES-256)                             │
│     - Set file permissions: 600                             │
│     - Generate random filename (uuid4)                      │
│                                                              │
└────────────────────┬────────────────────────────────────────┘
                     │
                     │ HTTPS to external service
                     │ Authorization: API Key (from env)
                     │
┌────────────────────▼────────────────────────────────────────┐
│            Transcription Service                             │
│         (OpenAI Whisper / Google STT)                        │
│                                                              │
│  8. Send encrypted audio file                               │
│  9. Receive transcription response                          │
│                                                              │
└────────────────────┬────────────────────────────────────────┘
                     │
                     │ Return transcription text
                     │
┌────────────────────▼────────────────────────────────────────┐
│                  FastAPI Backend                             │
│                                                              │
│  10. Cleanup                                                 │
│      - Delete temp audio file (secure delete)               │
│      - Log transcription event (no content)                 │
│                                                              │
│  11. Return transcription to client                         │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Implementation Guidance

### Step 1: Audio File Validation Layer

Create new validation module: `/Users/pablolozano/Mac Projects August/genesis/backend/app/infrastructure/validation/audio_validator.py`

**Validation checks**:
1. **MIME Type**: `audio/webm`, `audio/wav`, `audio/mpeg`, `audio/mp4`
2. **File Size**: Maximum 25 MB (configurable)
3. **Magic Number**: Verify file header matches MIME type (prevents extension spoofing)
4. **Duration**: Maximum 5 minutes (prevents abuse)

**Security rationale**:
- MIME type validation prevents executable file uploads disguised as audio
- Size limits prevent DoS attacks and excessive storage usage
- Magic number verification prevents MIME type spoofing
- Duration limits prevent abuse of transcription API quota

**Recommended library**: `python-magic` for magic number verification

### Step 2: Secure Temporary File Handling

Create secure file handler: `/Users/pablolozano/Mac Projects August/genesis/backend/app/infrastructure/storage/temp_file_handler.py`

**Implementation pattern**:
```python
import tempfile
import os
from pathlib import Path
from uuid import uuid4
from contextlib import contextmanager

@contextmanager
def secure_temp_file(suffix: str = ".webm"):
    """
    Context manager for secure temporary file handling.
    - Creates file in OS temp directory
    - Sets secure permissions (600)
    - Generates random filename
    - Guarantees cleanup on exit
    """
    temp_dir = tempfile.gettempdir()
    filename = f"{uuid4().hex}{suffix}"
    filepath = Path(temp_dir) / filename

    try:
        # Create file with secure permissions (owner read/write only)
        filepath.touch(mode=0o600)
        yield filepath
    finally:
        # Secure delete: overwrite with random data before deletion
        if filepath.exists():
            filepath.write_bytes(os.urandom(filepath.stat().st_size))
            filepath.unlink()
```

**Security rationale**:
- OS temp directory has appropriate permissions
- Random filenames prevent path traversal attacks
- Permission 600 prevents other users from reading audio files
- Context manager guarantees cleanup even on exceptions
- Secure delete overwrites file content before deletion

### Step 3: Audio Upload API Endpoint

Create new router: `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/inbound/audio_router.py`

**Endpoint structure**:
```python
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status
from app.infrastructure.security.dependencies import CurrentUser
from app.infrastructure.validation.audio_validator import validate_audio_file
from app.infrastructure.storage.temp_file_handler import secure_temp_file

router = APIRouter(prefix="/api/audio", tags=["audio"])

@router.post("/transcribe")
async def transcribe_audio(
    audio_file: UploadFile = File(...),
    conversation_id: str = Form(...),
    current_user: CurrentUser
):
    """
    Transcribe audio file to text.

    Security controls:
    - JWT authentication required
    - Conversation ownership verified
    - Audio validation (MIME, size, duration)
    - Rate limiting (if implemented)
    - Secure temporary storage
    - Immediate file cleanup
    """
    # 1. Verify conversation ownership
    # 2. Validate audio file
    # 3. Save to secure temp file
    # 4. Send to transcription service
    # 5. Cleanup temp file
    # 6. Return transcription
```

**Security considerations**:
- Use `UploadFile` with `File()` dependency for streaming upload
- Verify `conversation_id` exists and belongs to `current_user`
- Return 403 Forbidden for unauthorized access
- Return 400 Bad Request for invalid audio files
- Return 413 Payload Too Large for oversized files
- Return 429 Too Many Requests if rate limited

### Step 4: Rate Limiting Implementation

**Recommended library**: `slowapi` (FastAPI-compatible rate limiting)

Add to `requirements.txt`:
```
slowapi>=0.1.8
```

Integrate in `main.py`:
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
```

Apply to audio endpoint:
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.post("/transcribe")
@limiter.limit("10/minute")  # Per-IP rate limit
async def transcribe_audio(...):
    # Implementation
```

**Rate limit recommendations**:
- **Per-IP**: 20 requests/minute (prevents automated abuse)
- **Per-user**: 10 requests/minute (prevents account abuse)
- **Global**: 100 requests/minute (protects infrastructure)

**Security rationale**:
- Prevents brute force attacks on conversation IDs
- Limits transcription API costs from malicious usage
- Prevents DoS attacks via excessive uploads
- Protects backend resources (CPU, memory, disk)

### Step 5: Transcription Service Integration

Create transcription adapter: `/Users/pablolozano/Mac Projects August/genesis/backend/app/adapters/outbound/transcription/transcription_service.py`

**Port interface**: `/Users/pablolozano/Mac Projects August/genesis/backend/app/core/ports/transcription_service.py`

**Security considerations**:
- API keys stored in environment variables (`TRANSCRIPTION_API_KEY`)
- Use HTTPS for all external API calls
- Set reasonable timeout (30 seconds) to prevent hanging requests
- Handle API errors gracefully (don't expose internal errors to client)
- Log API usage for audit trail (no audio content or transcriptions)

**Privacy consideration**: External transcription services receive audio data
- Disclose in privacy policy that audio is sent to third-party service
- Consider self-hosted Whisper for sensitive deployments
- Ensure transcription service GDPR/privacy compliance

### Step 6: Frontend File Size Enforcement

**Client-side validation** (defense in depth):
```typescript
// Validate before upload
const MAX_FILE_SIZE = 25 * 1024 * 1024; // 25 MB
const MAX_DURATION = 300; // 5 minutes

if (audioBlob.size > MAX_FILE_SIZE) {
  throw new Error("Audio file too large");
}

if (audioDuration > MAX_DURATION) {
  throw new Error("Audio recording too long");
}
```

**Security rationale**:
- Provides immediate feedback to user
- Reduces unnecessary network traffic
- Does NOT replace server-side validation (client can be bypassed)

## Risks and Considerations

### Security Risks

**1. File Upload Vulnerabilities**
- **Risk**: Malicious file uploads (executables, malware, zip bombs)
- **Mitigation**: Strict MIME type validation, magic number verification, size limits
- **Severity**: HIGH

**2. Privacy Concerns**
- **Risk**: Voice recordings are highly personal, contain PII
- **Mitigation**: Immediate deletion after transcription, encryption at rest, secure transmission
- **Severity**: HIGH (GDPR/privacy implications)

**3. API Abuse**
- **Risk**: Transcription API quota exhaustion, cost overruns
- **Mitigation**: Rate limiting, per-user quotas, monitoring
- **Severity**: MEDIUM

**4. DoS Attacks**
- **Risk**: Large file uploads consume disk space, CPU, memory
- **Mitigation**: File size limits, rate limiting, timeout configuration
- **Severity**: MEDIUM

**5. CORS Misconfiguration**
- **Risk**: Current CORS allows all methods/headers (`["*"]`)
- **Mitigation**: Restrict to necessary methods (GET, POST), specific headers
- **Severity**: LOW (but should be hardened)

**6. No HTTPS Enforcement**
- **Risk**: Audio files transmitted in plaintext over HTTP
- **Mitigation**: Enforce HTTPS in production (nginx/load balancer), HSTS headers
- **Severity**: HIGH (if not using HTTPS)

### Privacy Considerations

**Voice Biometrics**:
- Voice recordings can be used to identify individuals
- More sensitive than text-based chat
- Consider anonymization or voice transformation for test environments

**Third-Party Data Sharing**:
- Transcription services (OpenAI, Google) receive audio data
- Review service privacy policies and data retention
- Consider data processing agreements (DPAs) for GDPR compliance
- Self-hosted Whisper may be required for sensitive industries (healthcare, legal)

**Data Retention**:
- **Recommendation**: Do NOT store audio files
- Delete immediately after successful transcription
- Transcription text stored in LangGraph checkpoints (existing pattern)
- Consider transcription expiration policy (e.g., auto-delete after 90 days)

**User Consent**:
- Display clear notice before recording audio
- Obtain explicit consent for third-party transcription processing
- Provide opt-out for audio input (use text instead)

### Compliance Considerations

**GDPR (European Union)**:
- Voice recordings are personal data under GDPR Article 4
- Requires lawful basis for processing (consent, legitimate interest)
- Data subject rights: access, deletion, portability
- DPA required for third-party transcription services

**CCPA (California)**:
- Voice recordings are personal information
- Must disclose data collection, usage, and sharing
- Consumers have right to deletion and opt-out

**HIPAA (Healthcare)**:
- Voice recordings containing health information are PHI
- Requires Business Associate Agreement (BAA) with transcription service
- Self-hosted Whisper recommended for HIPAA compliance

**SOC 2 / ISO 27001**:
- Encryption in transit and at rest required
- Audit logging of all audio processing
- Access controls and authentication

## Testing Strategy

### Security Testing Checklist

**Authentication & Authorization Tests**:
- [ ] Reject unauthenticated requests (no JWT token)
- [ ] Reject expired JWT tokens
- [ ] Reject invalid JWT tokens (malformed, wrong signature)
- [ ] Reject access to conversations owned by other users
- [ ] Reject inactive user audio uploads

**Input Validation Tests**:
- [ ] Reject files larger than 25 MB
- [ ] Reject files with invalid MIME types (e.g., `application/octet-stream`)
- [ ] Reject files with mismatched MIME type and magic number
- [ ] Reject audio longer than 5 minutes
- [ ] Reject requests with missing `conversation_id`

**Rate Limiting Tests**:
- [ ] Enforce per-user rate limits (10/minute)
- [ ] Enforce per-IP rate limits (20/minute)
- [ ] Return 429 Too Many Requests when limit exceeded
- [ ] Rate limit resets after time window expires

**File Handling Tests**:
- [ ] Temporary files created with secure permissions (600)
- [ ] Temporary files deleted after successful transcription
- [ ] Temporary files deleted after transcription errors
- [ ] No audio files stored in web-accessible directories
- [ ] File paths sanitized to prevent directory traversal

**Privacy & Data Protection Tests**:
- [ ] Audio files not logged in application logs
- [ ] Audio file paths not exposed in error messages
- [ ] Transcription API keys not logged or exposed
- [ ] Audio files overwritten before deletion (secure delete)

**Integration Tests**:
- [ ] End-to-end audio upload and transcription flow
- [ ] Error handling for transcription service failures
- [ ] Error handling for network timeouts
- [ ] Conversation ownership verified before processing

### Penetration Testing Scenarios

**1. Path Traversal Attack**:
```
POST /api/audio/transcribe
Content-Disposition: filename="../../etc/passwd"
```
Expected: Filename sanitized, file saved to temp directory only

**2. MIME Type Spoofing**:
```
POST /api/audio/transcribe
Content-Type: audio/wav
(file is actually a .exe)
```
Expected: Magic number verification detects mismatch, request rejected

**3. Rate Limit Bypass**:
```
// Rapid-fire requests with different IP addresses (X-Forwarded-For header)
```
Expected: Rate limiting based on authenticated user, not just IP

**4. Conversation ID Enumeration**:
```
POST /api/audio/transcribe
conversation_id: "00000000-0000-0000-0000-000000000001"
```
Expected: 403 Forbidden if conversation doesn't belong to user, no information leakage

**5. Token Replay Attack**:
```
// Capture valid JWT token, replay after user logs out
```
Expected: Token expiration enforced, old tokens rejected

## Summary

### Current Security Posture
- **Strong authentication**: JWT with bcrypt password hashing
- **Good authorization**: Conversation ownership verification enforced
- **Basic validation**: Pydantic field validation on inputs
- **Weak rate limiting**: No rate limiting implemented
- **No file upload security**: No existing file handling infrastructure

### Critical Security Gaps for Audio Upload
1. **No rate limiting** (HIGH PRIORITY)
2. **No file upload validation** (HIGH PRIORITY)
3. **No temporary file cleanup strategy** (HIGH PRIORITY)
4. **CORS configuration overly permissive** (MEDIUM PRIORITY)
5. **No request size limits explicitly configured** (MEDIUM PRIORITY)

### Recommended Security Controls for Audio Upload
1. **File validation**: MIME type, magic number, size (25 MB), duration (5 min)
2. **Rate limiting**: 10 requests/minute per user, 20/minute per IP
3. **Secure temp storage**: OS temp directory, 600 permissions, random names
4. **Immediate cleanup**: Context managers, secure delete (overwrite before unlink)
5. **Encryption at rest**: AES-256 for temporary audio files
6. **API key management**: Environment variables, never logged
7. **Privacy controls**: Immediate deletion, no long-term storage, user consent

### Implementation Priority
1. **Phase 1 (MVP)**: Authentication, authorization, basic file validation, cleanup
2. **Phase 2 (Hardening)**: Rate limiting, magic number verification, duration limits
3. **Phase 3 (Enterprise)**: Encryption at rest, audit logging, GDPR compliance

Pablo, the existing authentication and authorization patterns in Genesis are solid and follow security best practices. The main security work for audio upload will be implementing file validation, rate limiting, and secure temporary file handling. I've provided detailed implementation guidance for each security layer in the "Implementation Guidance" section above.

The key files you'll need to examine are the authentication dependencies (`dependencies.py`, `auth_service.py`) and the conversation router (`conversation_router.py`) for the ownership verification pattern. All relevant file paths are absolute paths as you requested.
