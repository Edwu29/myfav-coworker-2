#!/usr/bin/env python3
"""
Local test script to process real SQS messages using the updated worker.
"""

import os
import sys
import json
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent / 'src'
sys.path.insert(0, str(src_path))

# Set environment variables
os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'
os.environ['DYNAMODB_TABLE_NAME'] = 'myfav-coworker-main'
os.environ['GOOGLE_API_KEY'] = 'test-key'  # Replace with real key if needed
os.environ['SIMULATION_BROWSER_TIMEOUT'] = '30000'
os.environ['SIMULATION_SCRIPT_TIMEOUT'] = '300000'
os.environ['SIMULATION_HEADLESS'] = 'true'
os.environ['AI_AGENT_TIMEOUT'] = '60'
os.environ['AI_AGENT_MAX_RETRIES'] = '3'
os.environ['SIMULATION_QUEUE_NAME'] = 'myfav-coworker-simulation-queue'
os.environ['SQS_QUEUE_URL'] = 'https://sqs.us-east-1.amazonaws.com/220843429308/myfav-coworker-simulation-queue'

def process_sqs_messages():
    """Process real SQS messages using the updated worker."""
    
    # Import after setting environment
    from worker import process_sqs_messages
    
    print("Processing real SQS messages...")
    print("=" * 60)
    
    try:
        result = process_sqs_messages()
        
        print("\n✅ Worker execution completed!")
        print(f"Status Code: {result.get('statusCode')}")
        print(f"Processed: {result.get('processed')} messages")
        
        if result.get('results'):
            for i, res in enumerate(result['results']):
                print(f"\nResult {i+1}:")
                print(json.dumps(res, indent=2))
        elif result.get('processed') == 0:
            print("\nNo messages found in SQS queue")
        
        return result
        
    except Exception as e:
        print(f"\n❌ Worker execution failed: {e}")
        import traceback
        traceback.print_exc()
        return {"error": str(e)}

if __name__ == "__main__":
    print("SQS Worker Test")
    print("=" * 60)
    
    # Check if Playwright is available
    try:
        import playwright
        print("✅ Playwright is available")
    except ImportError:
        print("⚠️  Playwright not found - installing...")
        os.system("pip install playwright")
        os.system("playwright install chromium")
    
    result = process_sqs_messages()
    
    print("\n" + "=" * 60)
    print("Test completed!")
    if result.get('error'):
        print(f"❌ Error: {result['error']}")
    else:
        print("✅ Success!")