#!/bin/bash

echo "🚀 Deploying MyFav Coworker API..."

# Build the application
echo "📦 Building SAM application..."
sam build

if [ $? -ne 0 ]; then
    echo "❌ Build failed!"
    exit 1
fi

# Deploy with guided setup
echo "🌩️  Deploying to AWS..."
sam deploy --guided

echo "✅ Deployment complete!"
echo "📋 Next steps:"
echo "   1. Set up GitHub OAuth app with the callback URL from deployment output"
echo "   2. Add SSM parameters for GitHub credentials"
echo "   3. Test the deployed endpoints"
