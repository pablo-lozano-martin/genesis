# Deployment Guide

## Development Deployment

### Setup

1. **Clone and configure**
```bash
cd genesis
cp .env.example .env
```

2. **Edit `.env` and set required variables**
```env
# Required: Set a secret key (generate with: openssl rand -hex 32)
SECRET_KEY=your-generated-secret-key-here

# Required: Choose LLM provider
LLM_PROVIDER=openai

# Required: Add API key for chosen provider
OPENAI_API_KEY=sk-your-key-here
# OR
ANTHROPIC_API_KEY=sk-ant-your-key-here
# OR
GOOGLE_API_KEY=your-key-here
```

3. **Start services**
```bash
docker-compose up
```

This starts:
- **Backend**: http://localhost:8000
- **Frontend**: http://localhost:5173
- **MongoDB**: localhost:27017
- **API Docs**: http://localhost:8000/docs

### Development Workflow

**Backend changes**: Automatically reload (uvicorn --reload)
**Frontend changes**: Automatically reload (Vite HMR)

```bash
# View logs
docker-compose logs -f

# Run tests
docker-compose exec backend pytest

# Access shells
docker-compose exec backend bash
docker-compose exec frontend sh
```

## Production Deployment

### Environment Setup

Create production `.env` file:

```env
# Application
APP_NAME=Genesis
DEBUG=false
LOG_LEVEL=WARNING

# Security (CRITICAL: Generate secure random keys)
SECRET_KEY=<generate-with-openssl-rand-hex-32>
ACCESS_TOKEN_EXPIRE_MINUTES=30

# CORS (update with your production domain)
CORS_ORIGINS=https://your-domain.com

# LLM Provider
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-your-production-key-here
OPENAI_MODEL=gpt-4-turbo-preview

# Database
MONGODB_URL=mongodb://mongodb:27017
MONGODB_DB_NAME=genesis

# MongoDB Authentication (recommended for production)
MONGO_ROOT_USERNAME=admin
MONGO_ROOT_PASSWORD=<generate-secure-password>

# Frontend
API_URL=https://your-api-domain.com
```

### Build and Deploy

```bash
# Build images
docker-compose -f docker-compose.prod.yml build

# Start services
docker-compose -f docker-compose.prod.yml up -d

# Check status
docker-compose -f docker-compose.prod.yml ps

# View logs
docker-compose -f docker-compose.prod.yml logs -f
```

### Health Checks

```bash
# Backend health
curl http://localhost:8000/api/health

# Check container health
docker-compose -f docker-compose.prod.yml ps
```

### Stopping Services

```bash
# Stop services
docker-compose -f docker-compose.prod.yml down

# Stop and remove volumes (WARNING: Deletes database)
docker-compose -f docker-compose.prod.yml down -v
```

## Database Backup

### MongoDB Backup

```bash
# Create backup
docker-compose exec mongodb mongodump --out /data/backup

# Copy backup to host
docker cp <container-id>:/data/backup ./backup

# Restore backup
docker-compose exec mongodb mongorestore /data/backup
```

### Automated Backups

Create `backup-script.sh`:
```bash
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups/genesis_$DATE"

docker-compose exec -T mongodb mongodump --out /data/backup
docker cp genesis_mongodb_1:/data/backup $BACKUP_DIR
```

Add to crontab:
```bash
0 2 * * * /path/to/backup-script.sh
```

## Monitoring

### Logs
```bash
# Real-time logs
docker-compose -f docker-compose.prod.yml logs -f

# Specific service
docker-compose -f docker-compose.prod.yml logs -f backend

# Last 100 lines
docker-compose -f docker-compose.prod.yml logs --tail=100 backend
```

### Container Stats
```bash
# Resource usage
docker stats

# Specific containers
docker stats genesis_backend_1 genesis_frontend_1
```

## Security Checklist

- [ ] Change default SECRET_KEY
- [ ] Use strong MongoDB passwords
- [ ] Enable MongoDB authentication
- [ ] Configure CORS for production domain only
- [ ] Use HTTPS/TLS in production
- [ ] Keep Docker images updated
- [ ] Regular security audits
- [ ] Implement rate limiting
- [ ] Enable firewall rules
- [ ] Regular backups
- [ ] Monitor logs for suspicious activity

## Troubleshooting

### Backend won't start
```bash
# Check logs
docker-compose logs backend

# Common issues:
# 1. MongoDB not ready - wait and retry
# 2. Missing API keys - check .env
# 3. Port already in use - check with: lsof -i :8000
```

### Frontend can't connect to backend
```bash
# Check VITE_API_URL in .env
# Ensure CORS_ORIGINS includes frontend URL
# Check backend logs for CORS errors
```

### Database connection failed
```bash
# Check MongoDB is running
docker-compose ps mongodb

# Check MongoDB logs
docker-compose logs mongodb

# Verify MONGODB_URL in .env
```

### WebSocket connection failed
```bash
# Ensure WebSocket endpoint is accessible
# Check nginx WebSocket proxy configuration
# Verify authentication token is valid
```

## Maintenance

### Update Application
```bash
# Pull latest changes
git pull

# Rebuild images
docker-compose -f docker-compose.prod.yml build

# Restart services
docker-compose -f docker-compose.prod.yml up -d --no-deps --build backend
```

### Database Migrations

Database schema is managed by Beanie:
1. Update domain models
2. Update Beanie documents
3. Restart services
4. Beanie handles schema updates automatically

For complex migrations, consider using migration tools.
