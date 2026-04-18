#!/usr/bin/env python3
"""
Local test for SafeDeck Lambda
Tests the CrewAI pipeline with MiniMax
"""
import json
import os
import sys

# Set MiniMax env
os.environ["OPENAI_API_BASE"] = "https://api.minimax.io/v1"
os.environ["OPENAI_API_KEY"] = "sk-cp-icuFT3Hv5b9L_vlFEqMwrgPeNIMYe4VZPkqNZvLkMsaO8V_TzE8x2Dxgv7iNcY7sZ5ppesGc0HCgUH6YrrnwQz5RRbpqnhZYCneDxOdFaVgEk5tMw1u0V9U"

def test_minimax_connection():
    """Test MiniMax API directly"""
    print("🔌 Testing MiniMax connection...")
    try:
        from openai import OpenAI
        client = OpenAI(
            api_key=os.environ["OPENAI_API_KEY"],
            base_url=os.environ["OPENAI_API_BASE"]
        )
        response = client.chat.completions.create(
            model="MiniMax-M2.7",
            messages=[{"role": "user", "content": "Say 'MiniMax is working!' in exactly 3 words."}]
        )
        print(f"✅ MiniMax response: {response.choices[0].message.content}")
        return True
    except Exception as e:
        print(f"❌ MiniMax error: {e}")
        return False

def test_lambda_handler():
    """Test the Lambda handler with a sample event"""
    print("\n📦 Testing Lambda handler...")
    
    # Sample event matching what the frontend sends
    sample_event = {
        "tenant_slug": "default",
        "company_name": "TestStartup",
        "pitch_deck_content": "dGVzdCBkZWNrIGNvbnRlbnQ=",  # "test deck content" in base64
        "email_body": None
    }
    
    # Import and run lambda
    sys.path.insert(0, ".")
    from Deployment.lambda_function import lambda_handler
    
    print(f"📤 Sending event: {json.dumps(sample_event, indent=2)}")
    result = lambda_handler(sample_event, None)
    print(f"📥 Lambda response: {json.dumps(result, indent=2)}")
    return result

if __name__ == "__main__":
    print("=" * 50)
    print("SafeDeck Lambda Local Test")
    print("=" * 50)
    
    # Test 1: MiniMax
    minimax_ok = test_minimax_connection()
    
    if minimax_ok:
        # Test 2: Lambda handler
        result = test_lambda_handler()
        print("\n" + "=" * 50)
        print("✅ TEST PASSED")
        print("=" * 50)
    else:
        print("\n❌ MiniMax connection failed — fix before testing Lambda")
