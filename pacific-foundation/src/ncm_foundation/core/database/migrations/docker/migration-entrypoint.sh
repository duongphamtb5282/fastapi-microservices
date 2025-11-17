#!/bin/bash
# Migration entrypoint script for Docker

set -e

echo "Starting migration process..."

# Wait for database to be ready
echo "Waiting for database to be ready..."
python -c "
import asyncio
import asyncpg
import motor.motor_asyncio
from urllib.parse import urlparse
import os

async def wait_for_database():
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        print('DATABASE_URL not set')
        return
    
    parsed_url = urlparse(db_url)
    
    if parsed_url.scheme.startswith('postgresql'):
        for i in range(30):
            try:
                conn = await asyncpg.connect(db_url)
                await conn.close()
                print('PostgreSQL is ready!')
                return
            except:
                print(f'Waiting for PostgreSQL... ({i+1}/30)')
                await asyncio.sleep(2)
    elif parsed_url.scheme.startswith('mongodb'):
        for i in range(30):
            try:
                client = motor.motor_asyncio.AsyncIOMotorClient(db_url)
                await client.admin.command('ping')
                client.close()
                print('MongoDB is ready!')
                return
            except:
                print(f'Waiting for MongoDB... ({i+1}/30)')
                await asyncio.sleep(2)

asyncio.run(wait_for_database())
"

# Run migrations
echo "Running migrations..."
python -m migrations.runner "$@"

echo "Migration process completed!"
