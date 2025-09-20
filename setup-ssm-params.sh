#!/bin/bash

echo "🔐 Setting up AWS SSM Parameters for MyFav Coworker..."

# Check if AWS CLI is configured
if ! aws sts get-caller-identity &>/dev/null; then
    echo "❌ AWS CLI not configured. Please run 'aws configure' first."
    exit 1
fi

echo "📝 You'll need to provide your GitHub OAuth App credentials."
echo "   Create a GitHub OAuth App at: https://github.com/settings/developers"
echo ""

# Prompt for GitHub Client ID
read -p "Enter your GitHub Client ID: " GITHUB_CLIENT_ID
if [ -z "$GITHUB_CLIENT_ID" ]; then
    echo "❌ GitHub Client ID is required"
    exit 1
fi

# Prompt for GitHub Client Secret
read -s -p "Enter your GitHub Client Secret: " GITHUB_CLIENT_SECRET
echo ""
if [ -z "$GITHUB_CLIENT_SECRET" ]; then
    echo "❌ GitHub Client Secret is required"
    exit 1
fi

echo ""
echo "🔑 Creating SSM parameters..."

# Create GitHub Client ID parameter
aws ssm put-parameter \
    --name "/myfav-coworker/github-client-id" \
    --value "$GITHUB_CLIENT_ID" \
    --type "String" \
    --description "GitHub OAuth App Client ID" \
    --overwrite

if [ $? -eq 0 ]; then
    echo "✅ GitHub Client ID parameter created"
else
    echo "❌ Failed to create GitHub Client ID parameter"
    exit 1
fi

# Create GitHub Client Secret parameter
aws ssm put-parameter \
    --name "/myfav-coworker/github-client-secret" \
    --value "$GITHUB_CLIENT_SECRET" \
    --type "SecureString" \
    --description "GitHub OAuth App Client Secret" \
    --overwrite

if [ $? -eq 0 ]; then
    echo "✅ GitHub Client Secret parameter created"
else
    echo "❌ Failed to create GitHub Client Secret parameter"
    exit 1
fi

# Generate and create GitHub token encryption key
ENCRYPTION_KEY=$(openssl rand -base64 32)
aws ssm put-parameter \
    --name "/myfav-coworker/github-token-encryption-key" \
    --value "$ENCRYPTION_KEY" \
    --type "SecureString" \
    --description "Encryption key for GitHub tokens" \
    --overwrite

if [ $? -eq 0 ]; then
    echo "✅ GitHub token encryption key parameter created"
else
    echo "❌ Failed to create GitHub token encryption key parameter"
    exit 1
fi

# Generate and create JWT secret key
JWT_SECRET=$(openssl rand -base64 32)
aws ssm put-parameter \
    --name "/myfav-coworker/jwt-secret-key" \
    --value "$JWT_SECRET" \
    --type "SecureString" \
    --description "JWT secret key for token signing" \
    --overwrite

if [ $? -eq 0 ]; then
    echo "✅ JWT secret key parameter created"
else
    echo "❌ Failed to create JWT secret key parameter"
    exit 1
fi

echo ""
echo "🎉 All SSM parameters created successfully!"
echo ""
echo "📋 Next steps:"
echo "   1. Update your GitHub OAuth App callback URL to match your deployed API"
echo "   2. Re-run deployment: ./deploy.sh"
echo "   3. The callback URL will be: https://YOUR_API_ID.execute-api.us-east-1.amazonaws.com/Prod/auth/github/callback"
