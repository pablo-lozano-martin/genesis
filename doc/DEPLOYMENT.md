# Genesis Deployment Guide

This guide covers deploying Genesis in both development and production environments.

## Prerequisites

- Docker and Docker Compose installed
- An LLM provider API key (OpenAI, Anthropic, Google, or Ollama)
- Git

## Development Deployment

Development deployment includes hot-reload for both frontend and backend.

### 1. Clone and Setup

```bash
git clone <repository-url>
cd genesis
```

### 2. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` and set required variables:

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

### 3. Start Services

```bash
docker-compose up
```

This starts:
- **Backend**: http://localhost:8000
- **Frontend**: http://localhost:5173
- **MongoDB**: localhost:27017
- **API Docs**: http://localhost:8000/docs

### 4. Create First User

Navigate to http://localhost:5173 and register a new account.

### 5. Development Workflow

**Backend changes**: Automatically reload (uvicorn --reload)
**Frontend changes**: Automatically reload (Vite HMR)

```bash
# View logs
docker-compose logs -f

# Run tests
docker-compose exec backend pytest

# Access backend shell
docker-compose exec backend bash

# Access frontend shell
docker-compose exec frontend sh
```

## Production Deployment

Production deployment uses optimized Docker images with security hardening.

### 1. Production Environment Setup

Create a production `.env` file:

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

### 2. Build and Deploy

```bash
# Build images
docker-compose -f docker-compose.prod.yml build

# Start services in detached mode
docker-compose -f docker-compose.prod.yml up -d

# Check status
docker-compose -f docker-compose.prod.yml ps

# View logs
docker-compose -f docker-compose.prod.yml logs -f
```

### 3. Health Checks

Services include health checks:

```bash
# Backend health
curl http://localhost:8000/api/health

# Check container health
docker-compose -f docker-compose.prod.yml ps
```

### 4. Stopping Services

```bash
# Stop services
docker-compose -f docker-compose.prod.yml down

# Stop and remove volumes (WARNING: Deletes database)
docker-compose -f docker-compose.prod.yml down -v
```

## Cloud Deployment

### AWS Deployment (Example)

#### Using EC2

1. **Launch EC2 Instance**
   - Ubuntu 22.04 LTS
   - t2.medium or larger
   - Security groups: Allow ports 80, 443, 22

2. **Install Docker**

```bash
sudo apt update
sudo apt install -y docker.io docker-compose
sudo usermod -aG docker $USER
```

3. **Clone and Deploy**

```bash
git clone <repository-url>
cd genesis
cp .env.example .env
# Edit .env with production values
docker-compose -f docker-compose.prod.yml up -d
```

4. **Setup Nginx Reverse Proxy** (Optional but recommended)

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:80;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /ws {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "Upgrade";
    }
}
```

5. **Setup SSL with Let's Encrypt**

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

### Using Docker Swarm

For multi-node deployment:

```bash
# Initialize swarm
docker swarm init

# Deploy stack
docker stack deploy -c docker-compose.prod.yml genesis

# Check services
docker stack services genesis

# View logs
docker service logs genesis_backend
```

### Using Kubernetes

Example Kubernetes manifests (create separate files):

**backend-deployment.yaml**:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: genesis-backend
spec:
  replicas: 3
  selector:
    matchLabels:
      app: genesis-backend
  template:
    metadata:
      labels:
        app: genesis-backend
    spec:
      containers:
      - name: backend
        image: genesis-backend:latest
        ports:
        - containerPort: 8000
        env:
        - name: MONGODB_URL
          value: "mongodb://mongodb:27017"
        - name: SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: genesis-secrets
              key: secret-key
```

Deploy:
```bash
kubectl apply -f backend-deployment.yaml
kubectl apply -f frontend-deployment.yaml
kubectl apply -f mongodb-statefulset.yaml
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

Add to crontab:
```bash
0 2 * * * /path/to/backup-script.sh
```

**backup-script.sh**:
```bash
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups/genesis_$DATE"

docker-compose exec -T mongodb mongodump --out /data/backup
docker cp genesis_mongodb_1:/data/backup $BACKUP_DIR

# Optional: Upload to S3
# aws s3 cp $BACKUP_DIR s3://your-bucket/backups/
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

### Application Metrics

Consider adding:
- **Prometheus**: Metrics collection
- **Grafana**: Metrics visualization
- **Sentry**: Error tracking
- **ELK Stack**: Log aggregation

## Scaling

### Horizontal Scaling

Scale backend instances:

```bash
# Scale to 3 backend instances
docker-compose -f docker-compose.prod.yml up -d --scale backend=3

# Add load balancer (nginx)
# Configure round-robin to backend instances
```

### Vertical Scaling

Update resource limits in `docker-compose.prod.yml`:

```yaml
deploy:
  resources:
    limits:
      cpus: '4'
      memory: 4G
    reservations:
      cpus: '2'
      memory: 2G
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

## Performance Tuning

### Backend

- Increase worker count: `--workers 4` in uvicorn command
- Enable HTTP/2 with reverse proxy
- Use connection pooling for MongoDB
- Cache frequently accessed data

### Frontend

- Enable CDN for static assets
- Implement service workers for offline support
- Optimize bundle size with code splitting
- Use image optimization

### Database

- Create indexes for frequently queried fields
- Regular database maintenance
- Monitor slow queries
- Consider read replicas for scaling

## Maintenance

### Update Application

```bash
# Pull latest changes
git pull

# Rebuild images
docker-compose -f docker-compose.prod.yml build

# Restart with zero downtime (if using multiple instances)
docker-compose -f docker-compose.prod.yml up -d --no-deps --build backend
```

### Database Migrations

Currently, database schema is managed by Beanie. For migrations:

1. Update domain models
2. Update Beanie documents
3. Restart services
4. Beanie handles schema updates automatically

For complex migrations, consider migration tools like Alembic.

## Support

For issues and questions:
- Check logs: `docker-compose logs`
- Review documentation: `doc/` directory
- Open an issue on GitHub

## Conclusion

This deployment guide covers common deployment scenarios. Adjust configurations based on your specific requirements and infrastructure.

For production deployments, always:
- Use strong secrets
- Enable HTTPS
- Set up monitoring
- Implement backups
- Follow security best practices
