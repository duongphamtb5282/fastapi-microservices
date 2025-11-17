# NCM Sample Project

A comprehensive sample project demonstrating the NCM Foundation Library with database operations, caching, logging, and authentication.

## 🚀 Features

### **Database Operations**

- **PostgreSQL Integration**: Full CRUD operations with connection pooling
- **Database Migrations**: Alembic-based migration system
- **Entity Management**: Users, Roles, and User-Role relationships
- **Audit Logging**: Automatic change tracking and versioning

### **Advanced Caching**

- **Multi-Level Cache**: L1 (memory) + L2 (Redis) with automatic fallback
- **Cache Strategies**: Write-through, write-behind, write-around, cache-aside
- **Cache Management**: Pattern-based clearing, TTL management
- **Cache Statistics**: Performance monitoring and metrics

### **Structured Logging**

- **Correlation ID Tracking**: Request tracing across operations
- **Structured Logging**: JSON format with context information
- **Log Rotation**: Automatic log file rotation and cleanup
- **Data Masking**: Sensitive data protection

### **Authentication & Authorization**

- **JWT Authentication**: Secure token-based authentication
- **Role-Based Access Control**: User roles and permissions
- **OpenAM Integration**: Enterprise SSO support
- **Password Security**: Bcrypt password hashing

## 📋 Prerequisites

- **Docker & Docker Compose**: For running infrastructure services
- **Python 3.11+**: For running the application
- **Poetry**: For dependency management

## 🛠️ Quick Start

### 1. Start Infrastructure Services

```bash
# Start all services (PostgreSQL, Redis, Kafka, OpenAM)
docker-compose up -d

# Check service status
docker-compose ps
```

### 2. Setup Application

```bash
# Install dependencies
poetry install

# Run setup script
python scripts/setup.py
```

### 3. Start Application

```bash
# Start the application
poetry run python -m uvicorn ncm_sample.api:app --reload

# Or using Docker
docker-compose up ncm-sample
```

### 4. Test the API

```bash
# Run API tests
python scripts/test_api.py

# Or test manually
curl http://localhost:8000/health
```

## 🗄️ Database Schema

### **Users Table**

```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    password_hash VARCHAR(255) NOT NULL,
    phone VARCHAR(20),
    avatar_url VARCHAR(500),
    last_login TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    created_by VARCHAR(100),
    updated_by VARCHAR(100),
    version INTEGER DEFAULT 1
);
```

### **Roles Table**

```sql
CREATE TABLE roles (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    permissions TEXT, -- JSON string
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    created_by VARCHAR(100),
    updated_by VARCHAR(100),
    version INTEGER DEFAULT 1
);
```

### **User Roles Table**

```sql
CREATE TABLE user_roles (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    role_id INTEGER REFERENCES roles(id),
    assigned_at TIMESTAMP DEFAULT NOW(),
    assigned_by VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    created_by VARCHAR(100),
    updated_by VARCHAR(100),
    version INTEGER DEFAULT 1
);
```

## 🔧 API Endpoints

### **Health & Monitoring**

- `GET /health` - Health check with service status
- `GET /cache/stats` - Cache statistics and performance
- `POST /cache/clear` - Clear all cache
- `POST /cache/clear/{pattern}` - Clear cache by pattern

### **Authentication**

- `POST /auth/login` - User login with JWT token

### **User Management**

- `POST /users/` - Create new user
- `GET /users/{user_id}` - Get user by ID
- `GET /users/` - List users with pagination
- `PUT /users/{user_id}` - Update user
- `DELETE /users/{user_id}` - Delete user

### **Role Management**

- `POST /roles/` - Create new role
- `GET /roles/{role_id}` - Get role by ID
- `GET /roles/` - List roles with pagination

### **User-Role Management**

- `POST /users/{user_id}/roles/` - Assign role to user
- `GET /users/{user_id}/roles/` - Get user roles

## 🧪 Testing Scenarios

### **Database Testing**

```bash
# Test database connection
curl http://localhost:8000/health

# Create a user
curl -X POST http://localhost:8000/users/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "email": "test@example.com",
    "username": "testuser",
    "first_name": "Test",
    "last_name": "User",
    "password": "password123"
  }'
```

### **Caching Testing**

```bash
# Get cache statistics
curl http://localhost:8000/cache/stats

# Clear cache
curl -X POST http://localhost:8000/cache/clear

# Clear cache by pattern
curl -X POST http://localhost:8000/cache/clear/users:*
```

### **Logging Testing**

```bash
# Check logs (structured JSON format)
tail -f logs/app.log

# Test correlation ID tracking
curl -H "X-Correlation-ID: test-123" http://localhost:8000/health
```

## 🔐 Authentication Flow

### 1. **User Registration**

```bash
# Create user
curl -X POST http://localhost:8000/users/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "username": "user",
    "first_name": "John",
    "last_name": "Doe",
    "password": "password123"
  }'
```

### 2. **User Login**

```bash
# Login and get token
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "user@example.com",
    "password": "password123"
  }'
```

### 3. **Authenticated Requests**

```bash
# Use token for authenticated requests
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/users/
```

## 📊 Monitoring & Metrics

### **Health Check Response**

```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T00:00:00Z",
  "services": {
    "database": true,
    "cache": true,
    "logging": true
  },
  "version": "0.1.0"
}
```

### **Cache Statistics**

```json
{
  "running": true,
  "strategy": {
    "strategy": "write_through",
    "write_queue_size": 0
  },
  "reloader": {
    "running": true,
    "total_tasks": 0,
    "enabled_tasks": 0,
    "total_reloads": 0,
    "total_errors": 0,
    "success_rate": 0,
    "background_tasks": 0,
    "reload_interval": 300
  },
  "cache": {
    "hits": 10,
    "misses": 5,
    "sets": 8,
    "deletes": 2,
    "hit_rate": 0.6667,
    "total_requests": 15
  }
}
```

## 🐳 Docker Services

### **PostgreSQL**

- **Port**: 5432
- **Database**: test
- **User**: auth_user
- **Password**: auth_password

### **Redis**

- **Port**: 6379
- **No authentication required**

### **Kafka**

- **Port**: 9092
- **Auto-create topics**: Enabled

### **OpenAM**

- **Port**: 8080
- **Admin User**: amAdmin
- **Admin Password**: password

## 🔧 Configuration

### **Environment Variables**

```bash
# Database
DATABASE_URL=postgresql://auth_user:auth_password@localhost:5432/test

# Redis
REDIS_URL=redis://localhost:6379

# Kafka
KAFKA_BOOTSTRAP_SERVERS=localhost:9092

# OpenAM
OPENAM_URL=http://localhost:8080/openam

# Security
SECRET_KEY=your-secret-key
JWT_SECRET=your-jwt-secret

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
```

## 📝 Development

### **Running Tests**

```bash
# Run API tests
python scripts/test_api.py

# Run unit tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=ncm_sample
```

### **Database Migrations**

```bash
# Create new migration
alembic revision --autogenerate -m "description"

# Run migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

### **Code Quality**

```bash
# Format code
poetry run black src/

# Sort imports
poetry run isort src/

# Type checking
poetry run mypy src/

# Linting
poetry run ruff check src/
```

## 🚀 Production Deployment

### **Docker Deployment**

```bash
# Build image
docker build -t ncm-sample .

# Run container
docker run -p 8000:8000 ncm-sample
```

### **Environment Setup**

```bash
# Copy environment file
cp env.example .env

# Edit configuration
nano .env

# Start services
docker-compose -f docker-compose.prod.yml up -d
```

## 📚 Documentation

- **API Documentation**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI Schema**: http://localhost:8000/openapi.json

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details.

## 🆘 Support

- **Issues**: [GitHub Issues](https://github.com/ncm/sample/issues)
- **Documentation**: [Project Wiki](https://github.com/ncm/sample/wiki)
- **Email**: Contact the development team
