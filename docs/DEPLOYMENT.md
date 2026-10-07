# IntelliStock Deployment Guide

---

## Local Development

See main `README.md` for quick start.

---

## Docker Compose (Recommended for Testing)

Starts complete stack with all services.

```bash
docker-compose up -d
```

Verify all services:
```bash
docker-compose ps
docker-compose logs -f
```

Stop:
```bash
docker-compose down
```

Full cleanup (removes data):
```bash
docker-compose down -v
```

---

## Production Deployment

### Requirements

- Docker & Docker Compose on host
- PostgreSQL managed service or container
- Redis managed service or container
- SSL/TLS certificates
- Environment variables (.env file)

### Step 1: Prepare Environment

**Create `.env` with production values:**

```env
# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
DEBUG=false

# Database (use managed PostgreSQL in prod)
DATABASE_URL=postgresql://prod_user:SECURE_PASSWORD@prod-postgres.example.com:5432/intellistock
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=40

# Cache (use managed Redis in prod)
REDIS_URL=redis://prod-redis.example.com:6379/0

# Security
SECRET_KEY=<generate_with_openssl_rand_hex>
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# CORS
CORS_ORIGINS=https://yourdomain.com,https://app.yourdomain.com

# Logging
LOG_LEVEL=WARNING
SENTRY_DSN=<optional_error_tracking>

# LLM (Phase 7+)
LLM_PROVIDER=openai
OPENAI_API_KEY=sk-<your_key>
OPENAI_MODEL=gpt-4

# Frontend
FRONTEND_URL=https://yourdomain.com
VITE_API_URL=https://api.yourdomain.com/api/v1
VITE_WS_URL=wss://api.yourdomain.com/ws
```

### Step 2: Build Docker Images

```bash
docker-compose build --no-cache
```

### Step 3: Run Migrations

```bash
docker-compose run backend alembic upgrade head
```

### Step 4: Start Services

```bash
docker-compose up -d
```

### Step 5: Verify Deployment

```bash
# Health check
curl https://api.yourdomain.com/health

# API docs
curl https://api.yourdomain.com/docs

# Test endpoint
curl https://api.yourdomain.com/api/v1/zones
```

---

## Reverse Proxy Configuration (Nginx)

```nginx
upstream backend {
    server backend:8000;
}

upstream frontend {
    server frontend:3000;
}

server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;
    
    ssl_certificate /etc/ssl/certs/yourdomain.crt;
    ssl_certificate_key /etc/ssl/private/yourdomain.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    
    # API reverse proxy
    location / {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com;
    
    ssl_certificate /etc/ssl/certs/yourdomain.crt;
    ssl_certificate_key /etc/ssl/private/yourdomain.key;
    
    # Frontend reverse proxy
    location / {
        proxy_pass http://frontend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name yourdomain.com api.yourdomain.com;
    return 301 https://$server_name$request_uri;
}
```

---

## Database Migrations

### Create Migration

```bash
docker-compose run backend alembic revision --autogenerate -m "Add column X to table Y"
```

### Apply Migration

```bash
docker-compose run backend alembic upgrade head
```

### Rollback

```bash
docker-compose run backend alembic downgrade -1
```

---

## Monitoring & Maintenance

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f frontend
```

### Database Backup

```bash
# Backup
docker-compose exec postgres pg_dump -U postgres intellistock > backup.sql

# Restore
docker-compose exec -T postgres psql -U postgres intellistock < backup.sql
```

### Redis Dump

```bash
# View
docker-compose exec redis redis-cli KEYS \*

# Backup
docker-compose exec redis redis-cli BGSAVE
docker cp <container_id>:/data/dump.rdb ./redis_backup.rdb
```

---

## Scaling

### Horizontal Scaling (Multiple Backends)

Use a load balancer (Nginx, HAProxy) in front of multiple backend instances:

```yaml
# docker-compose.yml (scaled)
version: '3.8'
services:
  backend-1:
    image: intellistock-backend
    ports:
      - "8001:8000"
  backend-2:
    image: intellistock-backend
    ports:
      - "8002:8000"
  backend-3:
    image: intellistock-backend
    ports:
      - "8003:8000"
  
  nginx:
    image: nginx:latest
    ports:
      - "8000:8000"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
```

---

## Security Checklist

- [ ] Set strong `SECRET_KEY` (min 32 chars)
- [ ] Use HTTPS with valid SSL certificates
- [ ] Enable CORS only for your domain
- [ ] Use managed database (not exposed to internet)
- [ ] Use managed Redis (password protected)
- [ ] Enable audit logging
- [ ] Set up rate limiting
- [ ] Enable CSRF protection on frontend
- [ ] Rotate API keys regularly
- [ ] Use secrets manager (.env not in git)
- [ ] Enable database encryption at rest
- [ ] Set up monitoring/alerting (Sentry, Datadog)
- [ ] Regular security updates to dependencies
- [ ] Backup database daily
- [ ] Test disaster recovery quarterly

---

## Rollback Procedure

1. **Stop current deployment:**
   ```bash
   docker-compose down
   ```

2. **Revert to previous version:**
   ```bash
   git checkout <previous_tag>
   docker-compose build
   docker-compose up -d
   ```

3. **Rollback database (if needed):**
   ```bash
   docker-compose run backend alembic downgrade -1
   ```

---

## Performance Tuning

### Database Connections

```env
DB_POOL_SIZE=20  # Increase if 100+ concurrent users
DB_MAX_OVERFLOW=40
```

### Redis Memory

```
maxmemory 2gb
maxmemory-policy allkeys-lru
```

### Nginx Caching

```nginx
proxy_cache_path /var/cache/nginx levels=1:2 keys_zone=api_cache:10m;

location /api/v1/dashboard/metrics {
    proxy_cache api_cache;
    proxy_cache_valid 200 1m;
}
```

---

## Troubleshooting Deployment

### Containers won't start

```bash
docker-compose logs backend
docker-compose logs postgres
```

### Database connection failed

```bash
docker-compose exec postgres psql -U postgres
# Check if database exists
\l
```

### WebSocket connection drops

- Check firewall allows WebSocket upgrades
- Verify proxy sets `Upgrade` and `Connection` headers
- Check backend logs for connection errors

### High memory usage

```bash
docker stats  # Monitor container memory
```

---

## Cloud Deployment Examples

### AWS (ECS + RDS + ElastiCache)

1. Build and push image to ECR
2. Create RDS PostgreSQL instance
3. Create ElastiCache Redis cluster
4. Create ECS task definition pointing to RDS/Redis
5. Create ECS service
6. Use Application Load Balancer for traffic

### GCP (Cloud Run + Cloud SQL + Memorystore)

1. Build and push image to Artifact Registry
2. Create Cloud SQL PostgreSQL instance
3. Create Memorystore Redis instance
4. Deploy to Cloud Run with environment variables
5. Use Cloud Load Balancing

### Azure (App Service + SQL Database + Cache for Redis)

1. Push image to Azure Container Registry
2. Create Azure SQL Database
3. Create Azure Cache for Redis
4. Deploy to App Service
5. Use Application Gateway for load balancing

---

## Support

For deployment issues:
- Check logs: `docker-compose logs`
- Review `.env` configuration
- Verify database/Redis connectivity
- Check firewall rules
- See main README for local development reference

