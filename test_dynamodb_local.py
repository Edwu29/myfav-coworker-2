#!/usr/bin/env python3
"""
Test script to validate DynamoDB operations locally using DynamoDB Local.
"""

import boto3
import sys
import os
from datetime import datetime, timezone
from botocore.exceptions import ClientError

# Add src to path for imports
sys.path.append('src')
from models.user import User, GitHubUserProfile
from services.user_service import UserService
from utils.encryption import create_token_encryptor

def setup_local_dynamodb():
    """Set up DynamoDB Local connection and create table."""
    # Configure for local DynamoDB
    dynamodb = boto3.resource(
        'dynamodb',
        endpoint_url='http://localhost:8000',
        region_name='us-east-1',
        aws_access_key_id='dummy',
        aws_secret_access_key='dummy'
    )
    
    table_name = 'myfav-coworker-main-local'
    
    # Check if table exists
    try:
        table = dynamodb.Table(table_name)
        table.load()
        print(f"✅ Table '{table_name}' already exists")
        return table
    except ClientError:
        pass
    
    # Create table
    print(f"📦 Creating table '{table_name}'...")
    table = dynamodb.create_table(
        TableName=table_name,
        KeySchema=[
            {'AttributeName': 'PK', 'KeyType': 'HASH'},
            {'AttributeName': 'SK', 'KeyType': 'RANGE'}
        ],
        AttributeDefinitions=[
            {'AttributeName': 'PK', 'AttributeType': 'S'},
            {'AttributeName': 'SK', 'AttributeType': 'S'}
        ],
        BillingMode='PAY_PER_REQUEST'
    )
    
    # Wait for table to be created
    table.wait_until_exists()
    print(f"✅ Table '{table_name}' created successfully")
    return table

def test_user_operations():
    """Test user CRUD operations."""
    print("\n🧪 Testing User Operations")
    print("=" * 40)
    
    # Set environment for local testing
    os.environ['DYNAMODB_TABLE_NAME'] = 'myfav-coworker-main-local'
    os.environ['AWS_ENDPOINT_URL'] = 'http://localhost:8000'
    os.environ['GITHUB_TOKEN_ENCRYPTION_KEY'] = 'test-key-32-chars-long-for-fernet'
    
    # Create user service with local endpoint
    user_service = UserService()
    user_service.dynamodb = boto3.resource(
        'dynamodb',
        endpoint_url='http://localhost:8000',
        region_name='us-east-1',
        aws_access_key_id='dummy',
        aws_secret_access_key='dummy'
    )
    user_service.table = user_service.dynamodb.Table('myfav-coworker-main-local')
    
    # Test data
    github_profile = GitHubUserProfile(
        id=12345,
        login="testuser",
        name="Test User",
        email="test@example.com",
        avatar_url="https://github.com/avatar/testuser"
    )
    
    github_token = "gho_test_token_12345"
    
    print("1. Testing user creation...")
    try:
        user = user_service.create_user(github_profile, github_token)
        print(f"✅ User created: {user.user_id}")
        print(f"   GitHub ID: {user.github_id}")
        print(f"   Username: {user.github_username}")
        print(f"   Created: {user.created_at}")
    except Exception as e:
        print(f"❌ User creation failed: {e}")
        return
    
    print("\n2. Testing user retrieval...")
    try:
        retrieved_user = user_service.get_user_by_github_id(str(github_profile.id))
        if retrieved_user:
            print(f"✅ User retrieved: {retrieved_user.github_username}")
            print(f"   User ID: {retrieved_user.user_id}")
        else:
            print("❌ User not found")
    except Exception as e:
        print(f"❌ User retrieval failed: {e}")
    
    print("\n3. Testing user update...")
    try:
        user.last_login_at = datetime.now(timezone.utc)
        updated_user = user_service.update_user(user)
        print(f"✅ User updated: {updated_user.last_login_at}")
    except Exception as e:
        print(f"❌ User update failed: {e}")
    
    print("\n4. Testing token decryption...")
    try:
        decrypted_token = user_service.get_decrypted_github_token(user.github_id)
        if decrypted_token == github_token:
            print("✅ Token encryption/decryption working")
        else:
            print("❌ Token mismatch")
    except Exception as e:
        print(f"❌ Token decryption failed: {e}")

def test_table_structure():
    """Test table structure and queries."""
    print("\n🔍 Testing Table Structure")
    print("=" * 40)
    
    dynamodb = boto3.resource(
        'dynamodb',
        endpoint_url='http://localhost:8000',
        region_name='us-east-1',
        aws_access_key_id='dummy',
        aws_secret_access_key='dummy'
    )
    
    table = dynamodb.Table('myfav-coworker-main-local')
    
    # Scan table to see all items
    try:
        response = table.scan()
        items = response.get('Items', [])
        print(f"✅ Table scan successful: {len(items)} items found")
        
        for item in items:
            print(f"   PK: {item.get('PK')}, SK: {item.get('SK')}")
            if 'github_username' in item:
                print(f"      User: {item['github_username']}")
    except Exception as e:
        print(f"❌ Table scan failed: {e}")

def main():
    """Main test function."""
    print("🚀 DynamoDB Local Validation")
    print("=" * 50)
    
    # Check if DynamoDB Local is running
    try:
        dynamodb = boto3.client(
            'dynamodb',
            endpoint_url='http://localhost:8000',
            region_name='us-east-1',
            aws_access_key_id='dummy',
            aws_secret_access_key='dummy'
        )
        dynamodb.list_tables()
        print("✅ DynamoDB Local is running on port 8000")
    except Exception as e:
        print(f"❌ DynamoDB Local not accessible: {e}")
        print("💡 Make sure to run: docker run -d -p 8000:8000 amazon/dynamodb-local")
        return
    
    # Setup table
    table = setup_local_dynamodb()
    
    # Run tests
    test_user_operations()
    test_table_structure()
    
    print("\n" + "=" * 50)
    print("🎉 DynamoDB Local Validation Complete!")

if __name__ == "__main__":
    main()
