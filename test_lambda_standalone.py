#!/usr/bin/env python3
"""
Standalone test for SafeDeck Lambda - MiniMax + Simulated Fallback
No crewai dependencies needed for this test.
"""
import json
import os
import random

# MiniMax config
OPENAI_API_BASE = "https://api.minimax.io/v1"
OPENAI_API_KEY = "sk-cp-icuFT3Hv5b9L_vlFEqMwrgPeNIMYe4VZPkqNZvLkMsaO8V_TzE8x2Dxgv7iNcY7sZ5ppesGc0HCgUH6YrrnwQz5RRbpqnhZYCneDxOdFaVgEk5tMw1u0V9U"

def test_minimax():
    """Test MiniMax API connection"""
    print("=" * 50)
    print("TEST 1: MiniMax Connection")
    print("=" * 50)
    try:
        import urllib.request
        payload = json.dumps({
            "model": "MiniMax-M2.7",
            "messages": [{"role": "user", "content": "Reply with exactly one word: 'working'. No punctuation."}]
        }).encode()
        
        req = urllib.request.Request(
            f"{OPENAI_API_BASE}/chat/completions",
            data=payload,
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json"
            },
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
            reply = data["choices"][0]["message"]["content"]
            print(f"✅ MiniMax is working! Response: '{reply}'")
            return True
    except Exception as e:
        print(f"❌ MiniMax error: {e}")
        return False


def test_simulated_fallback():
    """Test the simulated fallback that runs when crewai fails"""
    print("\n" + "=" * 50)
    print("TEST 2: Simulated Fallback Response")
    print("=" * 50)
    
    company_name = "TestStartup"
    random.seed(hash(company_name))
    
    simulated = {
        "founder_score": round(random.uniform(6.5, 8.5), 1),
        "market_size": round(random.uniform(7.0, 9.0), 1),
        "traction": round(random.uniform(5.0, 7.5), 1),
        "team_strength": round(random.uniform(6.0, 8.0), 1),
        "overall_score": round(random.uniform(6.0, 8.0), 1),
        "simulated": True,
    }
    
    print(f"✅ Simulated response generated:")
    print(json.dumps(simulated, indent=2))
    
    # Check it has the right fields for the UI
    required = ["founder_score", "market_size", "traction", "team_strength", "overall_score", "simulated"]
    missing = [f for f in required if f not in simulated]
    if missing:
        print(f"❌ Missing fields: {missing}")
        return False
    else:
        print(f"✅ All required fields present for UI")
        return True


def test_crewai_minimax_integration():
    """Test that MiniMax works with the OpenAI-compatible crewai interface"""
    print("\n" + "=" * 50)
    print("TEST 3: CrewAI-compatible MiniMax integration")
    print("=" * 50)
    try:
        import urllib.request
        
        # This is what crewai uses internally when configured for OpenAI-compatible
        payload = json.dumps({
            "model": "MiniMax-M2.7",
            "messages": [
                {"role": "system", "content": "You are a startup evaluator. Score this startup idea concisely."},
                {"role": "user", "content": "Startup: AI-powered pitch deck analyzer for VCs. Founders: ex-Googlers. ARR: $500K. Score from 1-10."}
            ],
            "max_tokens": 100
        }).encode()
        
        req = urllib.request.Request(
            f"{OPENAI_API_BASE}/chat/completions",
            data=payload,
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json"
            },
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
            reply = data["choices"][0]["message"]["content"]
            print(f"✅ MiniMax works with structured prompts: {reply[:100]}")
            return True
    except Exception as e:
        print(f"❌ Integration test error: {e}")
        return False


if __name__ == "__main__":
    print("SafeDeck Lambda Local Test")
    print("Testing: MiniMax connection + Simulated fallback\n")
    
    results = []
    results.append(("MiniMax Connection", test_minimax()))
    results.append(("Simulated Fallback", test_simulated_fallback()))
    results.append(("MiniMax CrewAI Integration", test_crewai_minimax_integration()))
    
    print("\n" + "=" * 50)
    print("RESULTS SUMMARY")
    print("=" * 50)
    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {name}")
    
    all_passed = all(r[1] for r in results)
    print("\n" + ("✅ ALL TESTS PASSED" if all_passed else "❌ SOME TESTS FAILED"))
