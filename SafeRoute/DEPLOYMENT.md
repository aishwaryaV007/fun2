# SafeRoute Deployment Guide

## Overview

This guide covers deploying SafeRoute to production environments including Docker, cloud platforms (AWS, GCP, Azure), and Kubernetes.

---

## 1. Local Development Deployment

### Quick Start with Docker Compose

```bash
# Navigate to project root
cd SafeRouteV1-main

# Copy environment file
cp .env.example .env

# Build and start all services
docker-compose up --build

# Access services
# Backend: http://localhost:8000
# Admin Dashboard: http://localhost:5173
# API Docs: http://localhost:8000/docs
```

### Stopping Services

```bash
# Stop all services
docker-compose down

# Stop and remove all volumes (data)
docker-compose down -v

# View logs
docker-compose logs -f backend
docker-compose logs -f admin
```

---

## 2. Docker Deployment

### Build Images Manually

```bash
# Build backend
cd SafeRoute_Backend
docker build -t saferoute-backend:latest .

# Build admin dashboard
cd ../SafeRoute_Admin
docker build -t saferoute-admin:latest .
```

### Run Containers

```bash
# Backend
docker run -d \
  --name saferoute-backend \
  -p 8000:8000 \
  -e BACKEND_HOST=0.0.0.0 \
  -e BACKEND_PORT=8000 \
  -e SAFETY_API_KEY=your-secure-key \
  -v /path/to/data:/app/data \
  saferoute-backend:latest

# Admin Dashboard
docker run -d \
  --name saferoute-admin \
  -p 5173:5173 \
  -e VITE_BACKEND_URL=http://localhost:8000 \
  -e VITE_GOOGLE_MAPS_API_KEY=your-api-key \
  saferoute-admin:latest
```

### Docker Network

```bash
# Create network
docker network create saferoute-net

# Run with network
docker run -d --network saferoute-net \
  --name saferoute-backend \
  -p 8000:8000 \
  saferoute-backend:latest

docker run -d --network saferoute-net \
  --name saferoute-admin \
  -p 5173:5173 \
  -e VITE_BACKEND_URL=http://saferoute-backend:8000 \
  saferoute-admin:latest
```

---

## 3. Cloud Deployment

### AWS Deployment

#### Option A: EC2 with Docker

```bash
# Launch EC2 instance (Ubuntu 22.04 LTS)
# Security group: Open ports 80, 443, 8000

# SSH into instance
ssh -i key.pem ubuntu@your-instance-ip

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Clone repository
git clone https://github.com/your-org/SafeRoute.git
cd SafeRoute

# Configure environment
cp .env.example .env
# Edit .env with production values

# Start services
docker-compose up -d

# Setup SSL with Let's Encrypt
sudo apt install certbot python3-certbot-nginx
sudo certbot certonly --standalone -d api.saferoute.example.com
```

#### Option B: AWS RDS for PostgreSQL

```env
# Update .env
DATABASE_URL=postgresql://user:password@saferoute-db.123456789.us-east-1.rds.amazonaws.com:5432/saferoute_db
```

#### Option C: AWS ECS (Elastic Container Service)

```bash
# Create ECS cluster
aws ecs create-cluster --cluster-name saferoute-prod

# Create task definition
aws ecs register-task-definition --cli-input-json file://task-definition.json

# Create service
aws ecs create-service \
  --cluster saferoute-prod \
  --service-name saferoute-backend \
  --task-definition saferoute-backend:1 \
  --desired-count 3 \
  --load-balancers targetGroupArn=arn:aws:elasticloadbalancing:...
```

#### Option D: AWS Elastic Beanstalk

```bash
# Install EB CLI
pip install awsebcli

# Initialize Elastic Beanstalk
eb init -p docker saferoute-backend --region us-east-1

# Create environment
eb create saferoute-prod-env

# Deploy
eb deploy

# View logs
eb logs
```

**`Dockerrun.aws.json`:**

```json
{
  "AWSEBDockerrunVersion": 2,
  "containerDefinitions": [
    {
      "name": "saferoute-backend",
      "image": "123456789.dkr.ecr.us-east-1.amazonaws.com/saferoute-backend:latest",
      "essential": true,
      "memory": 512,
      "portMappings": [
        {
          "containerPort": 8000,
          "hostPort": 8000
        }
      ],
      "environment": [
        {
          "name": "DATABASE_URL",
          "value": "postgresql://user:pass@db.rds.amazonaws.com/saferoute"
        }
      ]
    }
  ]
}
```

---

### GCP Deployment

#### Option A: Google Cloud Run

```bash
# Authenticate
gcloud auth login
gcloud config set project your-project-id

# Build and push to Container Registry
gcloud builds submit --tag gcr.io/your-project-id/saferoute-backend

# Deploy to Cloud Run
gcloud run deploy saferoute-backend \
  --image gcr.io/your-project-id/saferoute-backend \
  --platform managed \
  --region us-central1 \
  --set-env-vars DATABASE_URL="postgresql://..." \
  --memory 512Mi \
  --cpu 1
```

#### Option B: Google Kubernetes Engine (GKE)

```bash
# Create cluster
gcloud container clusters create saferoute-cluster \
  --num-nodes=3 \
  --machine-type=e2-standard-4 \
  --zone us-central1-a

# Get credentials
gcloud container clusters get-credentials saferoute-cluster --zone us-central1-a

# Deploy with kubectl (see Kubernetes section below)
```

#### Option C: Google Cloud SQL

```env
# CloudSQL connection string
DATABASE_URL=postgresql://user:password@/saferoute_db?host=/cloudsql/project:region:instance
```

---

### Azure Deployment

#### Option A: Azure Container Instances

```bash
# Create resource group
az group create --name saferoute-rg --location eastus

# Deploy container
az container create \
  --resource-group saferoute-rg \
  --name saferoute-backend \
  --image saferoute-backend:latest \
  --ports 8000 \
  --environment-variables \
    DATABASE_URL="postgresql://..." \
    SAFETY_API_KEY="your-key" \
  --restart-policy OnFailure
```

#### Option B: Azure Container Apps

```bash
# Create container app environment
az containerapp env create \
  --name saferoute-env \
  --resource-group saferoute-rg

# Deploy container app
az containerapp create \
  --resource-group saferoute-rg \
  --name saferoute-backend \
  --environment saferoute-env \
  --image saferoute-backend:latest \
  --target-port 8000 \
  --ingress external \
  --env-vars DATABASE_URL="postgresql://..."
```

#### Option C: Azure Database for PostgreSQL

```env
# Connection string
DATABASE_URL=postgresql://user%40server:password@saferoute.postgres.database.azure.com:5432/saferoute_db?sslmode=require
```

---

## 4. Kubernetes Deployment

### Prerequisites

```bash
# Install kubectl
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl

# Install Helm (optional)
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash
```

### Kubernetes Manifests

**`k8s/namespace.yaml`:**

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: saferoute
```

**`k8s/backend-deployment.yaml`:**

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: saferoute-backend
  namespace: saferoute
spec:
  replicas: 3
  selector:
    matchLabels:
      app: saferoute-backend
  template:
    metadata:
      labels:
        app: saferoute-backend
    spec:
      containers:
      - name: backend
        image: saferoute-backend:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: saferoute-secrets
              key: database-url
        - name: SAFETY_API_KEY
          valueFrom:
            secretKeyRef:
              name: saferoute-secrets
              key: api-key
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 10
```

**`k8s/backend-service.yaml`:**

```yaml
apiVersion: v1
kind: Service
metadata:
  name: saferoute-backend
  namespace: saferoute
spec:
  selector:
    app: saferoute-backend
  ports:
  - protocol: TCP
    port: 8000
    targetPort: 8000
  type: LoadBalancer
```

**`k8s/secrets.yaml`:**

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: saferoute-secrets
  namespace: saferoute
type: Opaque
stringData:
  database-url: postgresql://user:password@postgres:5432/saferoute_db
  api-key: your-secure-api-key-here
```

### Deploy to Kubernetes

```bash
# Create namespace and secrets
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/secrets.yaml

# Deploy services
kubectl apply -f k8s/backend-deployment.yaml
kubectl apply -f k8s/backend-service.yaml

# Verify deployment
kubectl get pods -n saferoute
kubectl get svc -n saferoute

# View logs
kubectl logs -n saferoute deployment/saferoute-backend

# Scale deployment
kubectl scale deployment saferoute-backend --replicas=5 -n saferoute

# Update deployment
kubectl set image deployment/saferoute-backend \
  backend=saferoute-backend:v1.1.0 \
  -n saferoute
```

---

## 5. Database Migration (SQLite → PostgreSQL)

### Schema Migration

```bash
# Export SQLite data
sqlite3 safe_routes.db ".dump" > backup.sql

# Create PostgreSQL database
createdb -U postgres saferoute_db

# Import schema and data
psql -U postgres saferoute_db < backup.sql
```

### Using SQLAlchemy for Migration

```python
# Script to migrate from SQLite to PostgreSQL
from sqlalchemy import create_engine
from models import Base

# Source (SQLite)
sqlite_engine = create_engine('sqlite:///safe_routes.db')

# Target (PostgreSQL)
pg_engine = create_engine('postgresql://user:password@localhost/saferoute_db')

# Create tables in PostgreSQL
Base.metadata.create_all(pg_engine)

# Migrate data
# ... (use Alembic migrations for schema changes)
```

---

## 6. SSL/TLS Configuration

### Let's Encrypt with Certbot

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx

# Get certificate
sudo certbot certonly --standalone \
  -d api.saferoute.example.com \
  -d admin.saferoute.example.com

# Auto-renewal
sudo certbot renew --dry-run
```

### Configure HTTPS in Nginx

```nginx
# /etc/nginx/sites-available/saferoute
server {
    listen 443 ssl http2;
    server_name api.saferoute.example.com;

    ssl_certificate /etc/letsencrypt/live/api.saferoute.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.saferoute.example.com/privkey.pem;

    # Redirect HTTP to HTTPS
    if ($scheme != "https") {
        return 301 https://$server_name$request_uri;
    }

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket support
    location /ws {
        proxy_pass http://localhost:8000/ws;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name api.saferoute.example.com;
    return 301 https://$server_name$request_uri;
}
```

---

## 7. Monitoring & Logging

### ELK Stack (Elasticsearch, Logstash, Kibana)

```yaml
# docker-compose-monitoring.yml
version: '3'
services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.0.0
    environment:
      - discovery.type=single-node
      - ELASTIC_PASSWORD=your-secure-password
    ports:
      - "9200:9200"

  kibana:
    image: docker.elastic.co/kibana/kibana:8.0.0
    ports:
      - "5601:5601"
    depends_on:
      - elasticsearch
```

### Prometheus & Grafana

```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'saferoute-backend'
    static_configs:
      - targets: ['localhost:8000']
```

---

## 8. Backup & Recovery

### Database Backups

```bash
# SQLite backup
cp safe_routes.db safe_routes.db.backup.$(date +%s)

# PostgreSQL backup
pg_dump -U postgres saferoute_db > backup_$(date +%Y%m%d_%H%M%S).sql

# Compress and upload to S3
tar -czf backup.tar.gz backup_*.sql
aws s3 cp backup.tar.gz s3://saferoute-backups/
```

### Automated Backups

```bash
#!/bin/bash
# backup.sh - Automated daily backup

BACKUP_DIR="/backups/saferoute"
RETENTION_DAYS=30

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup database
pg_dump saferoute_db | gzip > $BACKUP_DIR/backup_$(date +%Y%m%d_%H%M%S).sql.gz

# Upload to cloud
aws s3 cp $BACKUP_DIR/ s3://saferoute-backups/ --recursive

# Delete old backups
find $BACKUP_DIR -type f -mtime +$RETENTION_DAYS -delete
```

### Cron Job

```bash
# Add to crontab
0 2 * * * /path/to/backup.sh >> /var/log/saferoute-backup.log 2>&1
```

---

## 9. Production Checklist

- [ ] SSL/TLS certificates installed
- [ ] HTTPS/WSS enforced
- [ ] Database migrations completed
- [ ] Environment variables configured
- [ ] API keys rotated
- [ ] Rate limiting enabled
- [ ] Monitoring configured
- [ ] Logging aggregation setup
- [ ] Backups automated
- [ ] Disaster recovery tested
- [ ] Security audit completed
- [ ] Load testing performed
- [ ] Performance optimization done
- [ ] Documentation updated

---

## 10. Troubleshooting

### Backend Health Check

```bash
curl http://localhost:8000/health
```

### View Logs

```bash
# Docker
docker logs saferoute-backend

# Docker Compose
docker-compose logs -f backend

# Kubernetes
kubectl logs -f deployment/saferoute-backend -n saferoute
```

### Common Issues

| Issue | Solution |
|-------|----------|
| Database connection error | Check DATABASE_URL and credentials |
| API key not working | Verify X-API-Key header and value |
| CORS error | Check CORS_ALLOWED_ORIGINS config |
| WebSocket connection failed | Ensure WSS/HTTPS used in production |
| High memory usage | Check for memory leaks, increase limits |

---

**Last Updated:** March 15, 2026  
**Version:** 1.0.0
