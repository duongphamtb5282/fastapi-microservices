# Database Foundation

A comprehensive database foundation library providing multi-database support with SQLAlchemy and Pydantic integration.

## Features

- **Multi-Database Support**: PostgreSQL, MySQL, SQLite, MongoDB, and GraphDB (Neo4j)
- **Connection Pooling**: High-performance connection management
- **Entity Listeners**: Automatic audit field updates
- **Database Security**: Encryption, row-level security, and audit logging
- **Repository Pattern**: Clean abstraction for data access
- **Type Safety**: Full Pydantic and SQLAlchemy integration
- **Async Support**: Native async/await support throughout

## Quick Start

### 1. Installation

```bash
pip install ncm-foundation
```

### 2. Basic Usage

```python
from ncm_foundation.core.database import (
    DatabaseConfig, DatabaseType, SQLAlchemyProvider,
    DatabaseManager, SQLAlchemyRepository
)
from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.asyncio import AsyncSession

# Configure database
config = DatabaseConfig(
    db_type=DatabaseType.POSTGRESQL,
    host="localhost",
    port=5432,
    database="myapp",
    username="postgres",
    password="password"
)

# Create provider and manager
provider = SQLAlchemyProvider(config)
db_manager = DatabaseManager(provider)

# Connect to database
await db_manager.connect()

# Use database
async with db_manager.get_session() as session:
    # Your database operations here
    pass

# Disconnect
await db_manager.disconnect()
```

## Architecture

### Core Components

1. **Providers**: Database-specific implementations
2. **Models**: SQLAlchemy models with audit capabilities
3. **Schemas**: Pydantic schemas for validation
4. **Repositories**: Data access layer
5. **Security**: Encryption, RLS, and audit logging
6. **Pooling**: Connection pool management

### File Structure

```
database/
├── __init__.py                 # Main exports
├── config.py                  # Configuration classes
├── providers/                 # Database providers
│   ├── base.py               # Abstract provider
│   ├── sqlalchemy_provider.py # SQLAlchemy implementation
│   └── mongodb_provider.py    # MongoDB implementation
├── models/                    # SQLAlchemy models
│   ├── base.py               # Base model classes
│   └── listeners.py          # Entity listeners
├── schemas/                   # Pydantic schemas
│   └── base.py               # Base schema classes
├── repositories/              # Repository pattern
│   ├── base.py               # Abstract repository
│   ├── sqlalchemy_repo.py    # SQLAlchemy repository
│   └── mongodb_repo.py       # MongoDB repository
├── pooling/                   # Connection pooling
│   ├── base.py               # Abstract pool
│   ├── sqlalchemy_pool.py    # SQLAlchemy pool
│   └── mongodb_pool.py       # MongoDB pool
├── security/                  # Security features
│   ├── encryption.py         # Field encryption
│   ├── access_control.py     # Row-level security
│   └── audit_logging.py      # Security audit
├── session.py                 # Session management
├── engine.py                  # Engine configuration
├── utils.py                   # Database utilities
└── examples.py               # Usage examples
```

## Database Providers

### SQLAlchemy Provider

Supports PostgreSQL, MySQL, and SQLite with full ORM capabilities.

```python
from ncm_foundation.core.database import SQLAlchemyProvider, DatabaseConfig, DatabaseType

config = DatabaseConfig(
    db_type=DatabaseType.POSTGRESQL,
    host="localhost",
    port=5432,
    database="myapp",
    username="postgres",
    password="password",
    pool_size=10,
    max_overflow=20
)

provider = SQLAlchemyProvider(config)
await provider.connect()
```

### MongoDB Provider

Native MongoDB support with connection pooling.

```python
from ncm_foundation.core.database import MongoDBProvider, DatabaseConfig, DatabaseType

config = DatabaseConfig(
    db_type=DatabaseType.MONGODB,
    host="localhost",
    port=27017,
    database="myapp",
    username="",
    password=""
)

provider = MongoDBProvider(config)
await provider.connect()
```

## Models and Schemas

### SQLAlchemy Models

```python
from ncm_foundation.core.database.models import BaseModel, AuditMixin, SoftDeleteMixin
from sqlalchemy import Column, Integer, String, Boolean

class User(BaseModel, SoftDeleteMixin):
    __tablename__ = 'users'

    username = Column(String(100), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
```

### Pydantic Schemas

```python
from ncm_foundation.core.database.schemas import BaseSchema, AuditSchema
from pydantic import Field
from typing import Optional
from datetime import datetime

class UserSchema(AuditSchema):
    username: str = Field(..., description="Username")
    email: str = Field(..., description="Email address")
    is_active: bool = Field(default=True, description="Active status")
    last_login: Optional[datetime] = Field(None, description="Last login time")

class UserCreateSchema(BaseSchema):
    username: str
    email: str
    password: str
```

## Repository Pattern

### SQLAlchemy Repository

```python
from ncm_foundation.core.database import SQLAlchemyRepository
from sqlalchemy.ext.asyncio import AsyncSession

async def user_operations(session: AsyncSession):
    user_repo = SQLAlchemyRepository(User, session)

    # Create user
    user_data = {
        'username': 'john_doe',
        'email': 'john@example.com',
        'password_hash': 'hashed_password'
    }
    user = await user_repo.create(user_data)

    # Get user by ID
    user = await user_repo.get_by_id(1)

    # Update user
    updated_user = await user_repo.update(1, {'is_active': False})

    # List users with filtering
    users = await user_repo.list(
        filters={'is_active': True},
        limit=10,
        offset=0
    )

    # Search users
    search_results = await user_repo.search("john", fields=['username', 'email'])

    # Soft delete user
    await user_repo.delete(1)
```

### MongoDB Repository

```python
from ncm_foundation.core.database import MongoDBRepository
from motor.motor_asyncio import AsyncIOMotorDatabase

async def mongo_operations(database: AsyncIOMotorDatabase):
    user_repo = MongoDBRepository(User, database, 'users')

    # Create user
    user_data = {
        'username': 'jane_doe',
        'email': 'jane@example.com',
        'password_hash': 'hashed_password'
    }
    user = await user_repo.create(user_data)

    # Get user by ID
    user = await user_repo.get_by_id(user.id)

    # Update user
    updated_user = await user_repo.update(user.id, {'is_active': False})

    # List users
    users = await user_repo.list(limit=10, offset=0)

    # Search users
    search_results = await user_repo.search("jane", fields=['username', 'email'])

    # Delete user
    await user_repo.delete(user.id)
```

## Security Features

### Field Encryption

```python
from ncm_foundation.core.database.security import EncryptedString
from sqlalchemy import Column, String

class User(BaseModel):
    __tablename__ = 'users'

    username = Column(String(100), nullable=False)
    password_hash = Column(EncryptedString(255), nullable=False)  # Encrypted field
```

### Row-Level Security

```python
from ncm_foundation.core.database.security import RowLevelSecurity, SecurityLevel

# Setup user context
user_context = {
    'user_id': 'user123',
    'roles': ['user'],
    'organization_id': 1,
    'security_level': SecurityLevel.INTERNAL
}

rls = RowLevelSecurity(user_context)

# Apply RLS policies
rls.setup_rls_policies(session, 'users')

# Filter queries based on security
filtered_query = rls.apply_security_filters(query, User)
```

### Audit Logging

```python
from ncm_foundation.core.database.security import SecurityAuditLogger

# Setup audit logging
audit_logger = SecurityAuditLogger()

# Query audit logs
audit_logs = await audit_logger.query_audit_logs(
    session,
    table_name='users',
    user_id='user123',
    start_date=datetime(2024, 1, 1),
    end_date=datetime(2024, 12, 31)
)
```

## Connection Pooling

### Pool Configuration

```python
config = DatabaseConfig(
    db_type=DatabaseType.POSTGRESQL,
    host="localhost",
    port=5432,
    database="myapp",
    username="postgres",
    password="password",
    pool_size=10,           # Base pool size
    max_overflow=20,        # Additional connections
    pool_timeout=30,        # Connection timeout
    pool_recycle=3600,      # Connection recycle time
    pool_pre_ping=True      # Validate connections
)
```

### Pool Monitoring

```python
# Get pool statistics
if hasattr(provider, 'get_pool_stats'):
    pool_stats = await provider.get_pool_stats()
    print(f"Active connections: {pool_stats['active_connections']}")
    print(f"Idle connections: {pool_stats['idle_connections']}")
    print(f"Total checkouts: {pool_stats['checkouts']}")
```

## Entity Listeners

### Automatic Audit Fields

```python
from ncm_foundation.core.database.models import setup_all_listeners, audit_context

# Setup listeners
setup_all_listeners()

# Set current user for audit
audit_context.set_user("admin_user")

# All database operations will automatically update audit fields
user = await user_repo.create(user_data)
# created_by and created_at are automatically set

user = await user_repo.update(user.id, update_data)
# updated_by, updated_at, and version are automatically updated
```

## Advanced Features

### Bulk Operations

```python
# Bulk create
users_data = [
    {'username': 'user1', 'email': 'user1@example.com'},
    {'username': 'user2', 'email': 'user2@example.com'},
    {'username': 'user3', 'email': 'user3@example.com'}
]
users = await user_repo.bulk_create(users_data)

# Bulk update
updates = [
    {'id': 1, 'is_active': False},
    {'id': 2, 'is_active': True},
    {'id': 3, 'is_active': False}
]
updated_count = await user_repo.bulk_update(updates)

# Bulk delete
deleted_count = await user_repo.bulk_delete([1, 2, 3])
```

### Advanced Filtering

```python
# Complex filters
filters = {
    'is_active': True,
    'created_at': {
        'gte': datetime(2024, 1, 1),
        'lte': datetime(2024, 12, 31)
    },
    'username': {
        'ilike': '%admin%'
    }
}
users = await user_repo.list(filters=filters)

# Field-specific queries
user = await user_repo.get_by_field('email', 'admin@example.com')
users = await user_repo.list_by_field('is_active', True, limit=10)
```

### Search and Indexing

```python
# Full-text search
search_results = await user_repo.search(
    query="john doe",
    fields=['username', 'email', 'first_name', 'last_name'],
    limit=20
)

# MongoDB text index
from ncm_foundation.core.database.utils import MongoDBUtils

await MongoDBUtils.create_text_index(
    database,
    'users',
    ['username', 'email', 'first_name', 'last_name']
)
```

## Configuration

### Environment Variables

```bash
# Database configuration
DB_TYPE=postgresql
DB_HOST=localhost
DB_PORT=5432
DB_DATABASE=myapp
DB_USERNAME=postgres
DB_PASSWORD=password

# Pool configuration
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=3600

# Security configuration
DB_SECURITY_ENABLED=true
DB_RLS_ENABLED=true
DB_ENCRYPTION_KEY=your_encryption_key
```

### Settings Class

```python
from ncm_foundation.core.database import DatabaseSettings

# Load from environment
settings = DatabaseSettings()

# Or configure manually
settings = DatabaseSettings(
    db_type=DatabaseType.POSTGRESQL,
    host="localhost",
    port=5432,
    database="myapp",
    username="postgres",
    password="password",
    pool_size=10,
    security_enabled=True
)
```

## Error Handling

```python
from sqlalchemy.exc import IntegrityError
from motor.errors import DuplicateKeyError

try:
    user = await user_repo.create(user_data)
except IntegrityError as e:
    logger.error(f"Database integrity error: {e}")
    # Handle duplicate key, foreign key constraint, etc.
except DuplicateKeyError as e:
    logger.error(f"MongoDB duplicate key error: {e}")
    # Handle MongoDB duplicate key
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    # Handle other errors
```

## Performance Optimization

### Connection Pooling

- Configure appropriate pool sizes based on your workload
- Use connection recycling to prevent stale connections
- Monitor pool statistics for optimization

### Query Optimization

- Use appropriate indexes for your queries
- Implement pagination for large datasets
- Use bulk operations for multiple records
- Consider read replicas for read-heavy workloads

### Caching

```python
# Example with Redis caching
from ncm_foundation.core.cache import CacheManager

cache_manager = CacheManager(redis_url="redis://localhost:6379")

async def get_user_cached(user_id: int):
    cache_key = f"user:{user_id}"

    # Try cache first
    cached_user = await cache_manager.get(cache_key)
    if cached_user:
        return cached_user

    # Get from database
    user = await user_repo.get_by_id(user_id)
    if user:
        # Cache for 1 hour
        await cache_manager.set(cache_key, user.to_dict(), ttl=3600)

    return user
```

## Testing

### Unit Tests

```python
import pytest
from ncm_foundation.core.database import DatabaseConfig, DatabaseType, SQLAlchemyProvider

@pytest.fixture
async def test_db():
    config = DatabaseConfig(
        db_type=DatabaseType.SQLITE,
        database=":memory:"
    )
    provider = SQLAlchemyProvider(config)
    await provider.connect()
    yield provider
    await provider.disconnect()

@pytest.mark.asyncio
async def test_user_creation(test_db):
    # Test user creation
    pass
```

### Integration Tests

```python
@pytest.mark.integration
async def test_database_integration():
    # Test with real database
    pass
```

## Migration

See the migration documentation for detailed information on migrating from the old database implementation to this new foundation.

## Examples

Run the examples to see the database foundation in action:

```python
from ncm_foundation.core.database.examples import main
import asyncio

asyncio.run(main())
```

## Support

For questions, issues, or contributions, please refer to the main project documentation or create an issue in the repository.
