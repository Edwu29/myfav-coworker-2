#!/bin/bash

# Setup script for AI agent SSM parameters
# This script creates the necessary SSM parameters for the AI agent functionality

set -e

REGION=${AWS_REGION:-us-east-1}
PARAMETER_PREFIX="/myfav-coworker"

echo "Setting up AI agent SSM parameters in region: $REGION"

# Check if AWS CLI is configured
if ! aws sts get-caller-identity > /dev/null 2>&1; then
    echo "Error: AWS CLI is not configured or credentials are invalid"
    exit 1
fi

# Function to create or update SSM parameter
create_or_update_parameter() {
    local param_name=$1
    local param_value=$2
    local param_type=${3:-String}
    local param_description=$4
    
    echo "Creating/updating parameter: $param_name"
    
    if aws ssm get-parameter --name "$param_name" --region "$REGION" > /dev/null 2>&1; then
        aws ssm put-parameter \
            --name "$param_name" \
            --value "$param_value" \
            --type "$param_type" \
            --description "$param_description" \
            --overwrite \
            --region "$REGION"
        echo "  ✓ Updated existing parameter"
    else
        aws ssm put-parameter \
            --name "$param_name" \
            --value "$param_value" \
            --type "$param_type" \
            --description "$param_description" \
            --region "$REGION"
        echo "  ✓ Created new parameter"
    fi
}

# Prompt for Google API Key if not provided
if [ -z "$GOOGLE_API_KEY" ]; then
    echo ""
    echo "Please enter your Google API Key for Gemini:"
    echo "(This will be stored securely in AWS SSM Parameter Store)"
    read -s GOOGLE_API_KEY
    echo ""
fi

if [ -z "$GOOGLE_API_KEY" ]; then
    echo "Error: Google API Key is required"
    exit 1
fi

# Create AI agent related parameters
create_or_update_parameter \
    "$PARAMETER_PREFIX/google-api-key" \
    "$GOOGLE_API_KEY" \
    "SecureString" \
    "Google API Key for Gemini AI agent functionality"

create_or_update_parameter \
    "$PARAMETER_PREFIX/ai-agent-model" \
    "gemini-2.5-pro" \
    "String" \
    "AI model to use for test plan generation"

create_or_update_parameter \
    "$PARAMETER_PREFIX/ai-agent-timeout" \
    "60" \
    "String" \
    "Timeout in seconds for AI agent requests"

create_or_update_parameter \
    "$PARAMETER_PREFIX/ai-agent-max-retries" \
    "3" \
    "String" \
    "Maximum number of retries for AI agent requests"

create_or_update_parameter \
    "$PARAMETER_PREFIX/ai-agent-temperature" \
    "0.3" \
    "String" \
    "Temperature setting for AI agent (0.0-1.0, lower = more deterministic)"

echo ""
echo "✅ AI agent SSM parameters setup complete!"
echo ""
echo "Parameters created/updated:"
echo "  - $PARAMETER_PREFIX/google-api-key (SecureString)"
echo "  - $PARAMETER_PREFIX/ai-agent-model"
echo "  - $PARAMETER_PREFIX/ai-agent-timeout"
echo "  - $PARAMETER_PREFIX/ai-agent-max-retries"
echo "  - $PARAMETER_PREFIX/ai-agent-temperature"
echo ""
echo "You can now deploy your application with:"
echo "  sam build && sam deploy --parameter-overrides GoogleApiKey=\$GOOGLE_API_KEY"
echo ""
echo "Or update the existing stack:"
echo "  sam deploy --parameter-overrides GoogleApiKey=\$GOOGLE_API_KEY"
