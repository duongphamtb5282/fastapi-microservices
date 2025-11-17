# NCM Auth Service

Authentication and authorization service for the NCM (Natural Capital Monitoring) platform. Provides user management, authentication, and authorization capabilities.

## Features

- 👤 **User Management**: Create, read, update, delete users
- 🔐 **Authentication**: JWT-based authentication
- 🛡️ **Authorization**: Role-based access control
- 🔒 **Security**: Password hashing, input validation
- 📊 **Health Checks**: Service health monitoring
- 🔍 **Logging**: Structured logging with correlation IDs

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   API Gateway   │───▶│  Auth Service   │───▶│   Database      │
│                 │    │                 │    │   (PostgreSQL)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌─────────────────┐
                       │   Redis Cache   │
                       └─────────────────┘
```

## Installation

### Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Redis 7+

### Local Development

```bash
# Clone repository
git clone https://github.com/your-org/ncm-auth-service.git
cd ncm-auth-service

# Install dependencies
pip install -e .

# Install foundation and contracts
pip install git+https://github.com/your-org/ncm-foundation.git@v0.1.0
pip install git+https://github.com/your-org/ncm-contracts.git@v0.1.0
```

### Docker

```bash
# Build image
docker build -t ncm-auth-service .

# Run container
docker run -p 8001:8000 \
  -e DATABASE_URL=postgresql://user:pass@host:5432/db \
  -e REDIS_URL=redis://host:6379 \
  ncm-auth-service
```

## Configuration

### Environment Variables

| Variable             | Description              | Default                  | Required |
| -------------------- | ------------------------ | ------------------------ | -------- |
| `DATABASE_URL`       | Database connection URL  | -                        | ✅       |
| `REDIS_URL`          | Redis connection URL     | `redis://localhost:6379` | ✅       |
| `SECRET_KEY`         | Application secret key   | -                        | ✅       |
| `JWT_SECRET`         | JWT signing secret       | -                        | ✅       |
| `JWT_ALGORITHM`      | JWT algorithm            | `HS256`                  | ❌       |
| `JWT_EXPIRE_MINUTES` | JWT expiration (minutes) | `1440`                   | ❌       |
| `LOG_LEVEL`          | Logging level            | `INFO`                   | ❌       |
| `LOG_FORMAT`         | Log format               | `json`                   | ❌       |

### Example .env

```bash
# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/ncm_auth

# Cache
REDIS_URL=redis://localhost:6379

# Security
SECRET_KEY=your-super-secret-key-here
JWT_SECRET=your-jwt-secret-key-here

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
```

## API Endpoints

### Health Check

```http
GET /health
```

**Response:**

```json
{
  "status": "healthy",
  "services": {
    "database": {
      "status": "healthy",
      "service": "database"
    },
    "cache": {
      "status": "healthy",
      "service": "cache"
    }
  }
}
```

### User Management

#### Create User

```http
POST /api/v1/users/
Content-Type: application/json

{
  "email": "john@example.com",
  "password": "securepassword",
  "first_name": "John",
  "last_name": "Doe",
  "organization_id": 1,
  "role": "user"
}
```

**Response:**

```json
{
  "id": 1,
  "email": "john@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "organization_id": 1,
  "role": "user",
  "status": "active",
  "is_active": true,
  "is_superuser": false,
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

#### Get User

```http
GET /api/v1/users/{user_id}
```

**Response:**

```json
{
  "id": 1,
  "email": "john@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "organization_id": 1,
  "role": "user",
  "status": "active",
  "is_active": true,
  "is_superuser": false,
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z"
}
```

#### Update User

```http
PUT /api/v1/users/{user_id}
Content-Type: application/json

{
  "first_name": "Johnny",
  "last_name": "Smith"
}
```

#### List Users

```http
GET /api/v1/users/
```

**Response:**

```json
[
  {
    "id": 1,
    "email": "john@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "organization_id": 1,
    "role": "user",
    "status": "active",
    "is_active": true,
    "is_superuser": false,
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
  }
]
```

### Authentication

#### Login

```http
POST /api/v1/users/login
Content-Type: application/json

{
  "email": "john@example.com",
  "password": "securepassword"
}
```

**Response:**

```json
{
  "user": {
    "id": 1,
    "email": "john@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "organization_id": 1,
    "role": "user",
    "status": "active",
    "is_active": true,
    "is_superuser": false,
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:00:00Z"
  },
  "token": {
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
    "token_type": "bearer",
    "expires_in": 3600
  }
}
```

## Data Models

### User Model

```python
class User:
    id: int
    email: str
    hashed_password: str
    first_name: Optional[str]
    last_name: Optional[str]
    organization_id: Optional[int]
    role: UserRole  # admin, user, viewer, superuser
    status: UserStatus  # active, inactive, pending, suspended
    is_active: bool
    is_superuser: bool
    created_at: datetime
    updated_at: datetime
```

### User Roles

- `admin`: Full administrative access
- `user`: Standard user access
- `viewer`: Read-only access
- `superuser`: System administrator access

### User Status

- `active`: User is active and can log in
- `inactive`: User is inactive and cannot log in
- `pending`: User registration pending approval
- `suspended`: User is suspended

## Security

### Password Security

- Passwords are hashed using SHA-256 (in production, use bcrypt)
- Minimum password length: 8 characters
- Passwords are never stored in plain text

### JWT Tokens

- Tokens are signed using HS256 algorithm
- Default expiration: 24 hours
- Tokens include user ID and email
- Secret key should be strong and unique

### Input Validation

- All inputs are validated using Pydantic schemas
- Email addresses are validated for proper format
- SQL injection protection through SQLAlchemy ORM

## Error Handling

### HTTP Status Codes

- `200 OK`: Successful operation
- `201 Created`: Resource created successfully
- `400 Bad Request`: Invalid request data
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Resource not found
- `422 Unprocessable Entity`: Validation error
- `500 Internal Server Error`: Server error

### Error Response Format

```json
{
  "detail": "Error message",
  "status_code": 400,
  "timestamp": "2024-01-01T00:00:00Z"
}
```

## Logging

### Log Format

```json
{
  "timestamp": "2024-01-01T00:00:00Z",
  "level": "INFO",
  "logger": "auth_service",
  "message": "User created successfully",
  "correlation_id": "req-123-456",
  "user_id": 1,
  "action": "create_user"
}
```

### Log Levels

- `DEBUG`: Detailed information for debugging
- `INFO`: General information about operations
- `WARNING`: Warning messages for potential issues
- `ERROR`: Error messages for failed operations
- `CRITICAL`: Critical errors that require immediate attention

## Database Schema

### Users Table

```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    organization_id INTEGER,
    role VARCHAR(20) DEFAULT 'user',
    status VARCHAR(20) DEFAULT 'active',
    is_active BOOLEAN DEFAULT TRUE,
    is_superuser BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_organization_id ON users(organization_id);
```

## Development

### Running Locally

```bash
# Start database and Redis
docker-compose up -d postgres redis

# Run migrations
alembic upgrade head

# Start service
uvicorn src.auth_service.main:app --host 0.0.0.0 --port 8001 --reload
```

### Running Tests

```bash
# Install test dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run with coverage
pytest --cov=src/auth_service --cov-report=html
```

### Code Quality

```bash
# Format code
black src/

# Sort imports
isort src/

# Type checking
mypy src/

# Linting
pylint src/
```

## Deployment

### Docker Deployment

```bash
# Build image
docker build -t ncm-auth-service:latest .

# Run container
docker run -d \
  --name auth-service \
  -p 8001:8000 \
  -e DATABASE_URL=postgresql://user:pass@host:5432/db \
  -e REDIS_URL=redis://host:6379 \
  -e SECRET_KEY=your-secret-key \
  -e JWT_SECRET=your-jwt-secret \
  ncm-auth-service:latest
```

### Docker Compose

```yaml
version: "3.8"
services:
  auth-service:
    build: ./ncm-auth-service
    ports:
      - "8001:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@postgres:5432/ncm_auth
      - REDIS_URL=redis://redis:6379
      - SECRET_KEY=your-secret-key
      - JWT_SECRET=your-jwt-secret
    depends_on:
      - postgres
      - redis
```

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: auth-service
spec:
  replicas: 3
  selector:
    matchLabels:
      app: auth-service
  template:
    metadata:
      labels:
        app: auth-service
    spec:
      containers:
        - name: auth-service
          image: ncm-auth-service:latest
          ports:
            - containerPort: 8000
          env:
            - name: DATABASE_URL
              valueFrom:
                secretKeyRef:
                  name: auth-secrets
                  key: database-url
            - name: REDIS_URL
              valueFrom:
                secretKeyRef:
                  name: auth-secrets
                  key: redis-url
```

## Monitoring

### Health Checks

The service provides comprehensive health checks:

- **Database Health**: Checks database connectivity
- **Cache Health**: Checks Redis connectivity
- **Overall Health**: Aggregated health status

### Metrics

- Request count and duration
- Error rates by endpoint
- Database connection pool status
- Cache hit/miss ratios

### Logging

- Structured JSON logging
- Correlation ID tracking
- Request/response logging
- Error tracking with stack traces

## Troubleshooting

### Common Issues

1. **Database Connection Failed**

   - Check DATABASE_URL environment variable
   - Verify database is running and accessible
   - Check network connectivity

2. **Redis Connection Failed**

   - Check REDIS_URL environment variable
   - Verify Redis is running and accessible
   - Check Redis authentication if configured

3. **JWT Token Invalid**

   - Verify JWT_SECRET is set correctly
   - Check token expiration
   - Ensure token format is correct

4. **User Creation Failed**
   - Check email uniqueness constraint
   - Verify password meets requirements
   - Check database permissions

### Debug Mode

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG

# Start service
uvicorn src.auth_service.main:app --host 0.0.0.0 --port 8001 --reload
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Update documentation
6. Submit a pull request

## License

MIT License - see LICENSE file for details.
