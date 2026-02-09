# Database and Deployment Analysis - Summary

This directory contains comprehensive analysis documents for RAGFlow's database design and deployment architecture.

## Available Documents

### 1. Database and Deployment Analysis (Chinese)
**File:** `database-deployment-analysis.md` (26KB)
**Language:** Chinese
**Content:**
- Complete database model analysis
- Deployment architecture overview
- Docker configuration details
- Environment variables reference
- Deployment and operations guide
- Troubleshooting procedures

### 2. Database and Deployment Analysis (English)
**File:** `database-deployment-analysis-en.md` (20KB)
**Language:** English
**Content:**
- Executive summary
- Multi-database architecture design
- Entity-relationship diagrams (Mermaid)
- Service components detailed breakdown
- Configuration management guide
- Deployment step-by-step instructions
- Operations and monitoring guide
- Backup and recovery procedures
- Scaling strategies
- Troubleshooting procedures
- Security considerations
- Performance tuning guidelines

## Key Findings

### Database Architecture
- **Multi-database polyglot persistence** architecture
- **MySQL 8.0.39**: Primary database for user data, metadata, configurations
- **Elasticsearch/Infinity/OceanBase**: Document storage with vector embeddings
- **MinIO**: Object storage for files and documents
- **Redis**: Caching, sessions, distributed locks

### Core Data Models
- **30+ database tables** organized around:
  - User management (authentication, multi-tenancy)
  - Knowledge base management
  - Document processing
  - Dialog and conversation
  - LLM integration
  - Agent workflows

### Deployment Architecture
- **Docker Compose** multi-container setup
- **Microservices architecture** with:
  - RAGFlow API server (port 9380)
  - Admin server (port 9381)
  - MCP server (port 9382)
  - Nginx reverse proxy (ports 80/443)
- **Multiple document engine options**:
  - Elasticsearch (default)
  - Infinity
  - OceanBase
  - OpenSearch

### Key Features
- **Connection pooling** with automatic retry (max 900 connections)
- **Distributed locking** for concurrent operations
- **Automatic schema migrations** on startup
- **Multi-tenant isolation** with role-based access control
- **Advanced RAG features**:
  - GraphRAG integration
  - RAPTOR hierarchical summarization
  - Mind map generation

## System Requirements

### Minimum
- **RAM:** 16GB
- **Disk:** 50GB (SSD recommended)
- **CPU:** 4 cores
- **OS:** Ubuntu 24.04 / Linux with Docker

### Recommended (Production)
- **RAM:** 32GB+
- **Disk:** 100GB+ (SSD)
- **CPU:** 8+ cores
- **Network:** Stable internet for image pulls

## Quick Start

### 1. Clone Repository
```bash
git clone https://github.com/infiniflow/ragflow.git
cd ragflow/docker
```

### 2. Configure Environment
```bash
cp .env .env.backup
# Edit .env and change passwords!
nano .env
```

### 3. Start Services
```bash
docker compose -f docker-compose.yml up -d
```

### 4. Verify Deployment
```bash
docker compose ps
curl http://localhost:9380/health
```

## Security Considerations

### ⚠️ Critical Security Warnings

1. **Change all default passwords** before production deployment
2. **Enable SSL/TLS** for production (use Certbot)
3. **Configure firewall** to block internal ports
4. **Use environment variables** for API keys (never commit to git)
5. **Enable data encryption** at rest for MySQL and MinIO

### Passwords to Change
- `MYSQL_PASSWORD`
- `MINIO_PASSWORD`
- `REDIS_PASSWORD`
- `ELASTIC_PASSWORD`

## Troubleshooting

### Common Issues

1. **Container startup failures**
   - Check logs: `docker compose logs ragflow-cpu`
   - Verify port availability
   - Check disk space: `df -h`

2. **Database connection errors**
   - Wait for MySQL health check: `docker compose ps`
   - Restart MySQL: `docker compose restart mysql`

3. **Elasticsearch issues**
   - Increase memory limit: `MEM_LIMIT=16147459182`
   - Check cluster health: `curl http://localhost:1200/_cluster/health?pretty`

## Monitoring and Operations

### Health Checks
```bash
# All services
docker compose ps

# Specific service
curl http://localhost:9380/health
```

### Log Monitoring
```bash
# Real-time logs
docker compose logs -f ragflow-cpu

# Service-specific
docker compose logs -f mysql
docker compose logs -f es01
```

### Performance Monitoring
```bash
# Container resources
docker stats

# Database performance
docker compose exec mysql mysqladmin -uroot -p${MYSQL_PASSWORD} processlist

# Redis performance
docker compose exec redis redis-cli -a ${REDIS_PASSWORD} INFO
```

## Backup Strategy

### Automated Backup Script
```bash
#!/bin/bash
BACKUP_DIR="/backup/ragflow/$(date +%Y%m%d)"
mkdir -p ${BACKUP_DIR}

# MySQL
docker compose exec -T mysql mysqldump -uroot -p${MYSQL_PASSWORD} rag_flow \
  > ${BACKUP_DIR}/mysql_backup.sql

# MinIO
docker compose exec minio mc mirror /data ${BACKUP_DIR}/minio

# Compress
tar -czf ${BACKUP_DIR}.tar.gz ${BACKUP_DIR}
rm -rf ${BACKUP_DIR}

# Keep last 7 days
find /backup/ragflow -name "*.tar.gz" -mtime +7 -delete
```

## Scaling Strategies

### Horizontal Scaling
```bash
# Scale application containers
docker compose up -d --scale ragflow-cpu=3
```

### Vertical Scaling
```bash
# Increase memory limits
MEM_LIMIT=16147459182  # 16GB

# Increase MySQL connections
--max_connections=2000

# Increase Elasticsearch heap
ES_JAVA_OPTS=-Xms16g -Xmx16g
```

## Performance Tuning

### MySQL
```ini
[mysqld]
max_connections = 1000
innodb_buffer_pool_size = 4G
innodb_log_file_size = 512M
query_cache_size = 256M
```

### Elasticsearch
```yaml
ES_JAVA_OPTS=-Xms8g -Xmx8g
indices.memory.index_buffer_size=30%
thread_pool.search.size=20
```

### Redis
```bash
maxmemory 256mb
maxmemory-policy allkeys-lru
```

## Support Resources

- **Official Documentation:** https://ragflow.io/docs
- **GitHub Repository:** https://github.com/infiniflow/ragflow
- **Issue Tracker:** https://github.com/infiniflow/ragflow/issues
- **Community:** https://ragflow.io/community

## Document Metadata

**Version:** 1.0  
**Created:** 2025-02-09  
**Authors:** RAGFlow Analysis Team  
**License:** Apache License 2.0  

---

**Note:** For detailed technical analysis, please refer to the full documents listed above.
