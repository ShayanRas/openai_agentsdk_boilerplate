#!/usr/bin/env python3
"""
Test script for the streaming endpoint of the MarketGuru 2.0 API.

Usage:
    python test_streaming_endpoint.py
"""

import requests
import json
import sys

def test_streaming_endpoint():
    """Test the /invoke_stream endpoint with different scenarios."""
    
    base_url = "http://localhost:8001"
    
    # Test cases
    test_cases = [
        {
            "name": "Simple tool test",
            "payload": {
                "user_input": "What is 5 + 3? Use the add tool.",
                "history_mode": "none"
            }
        },
        {
            "name": "Echo tool test",
            "payload": {
                "user_input": "Please echo 'Hello streaming world!' using the echo tool.",
                "history_mode": "none"
            }
        },
        {
            "name": "Server time test",
            "payload": {
                "user_input": "What time is it on the server? Use the get_server_time tool.",
                "history_mode": "none"
            }
        },
        {
            "name": "Multiple tools test",
            "payload": {
                "user_input": "First, tell me what 10 + 15 equals using the add tool. Then echo 'Calculation complete!' and finally tell me the server time.",
                "history_mode": "none"
            }
        }
    ]
    
    for test_case in test_cases:
        print(f"\n{'='*60}")
        print(f"Test: {test_case['name']}")
        print(f"Input: {test_case['payload']['user_input']}")
        print(f"{'='*60}")
        
        try:
            # Make streaming request
            response = requests.post(
                f"{base_url}/invoke_stream",
                json=test_case['payload'],
                stream=True,
                headers={"Accept": "text/event-stream"}
            )
            
            if response.status_code != 200:
                print(f"Error: HTTP {response.status_code}")
                print(response.text)
                continue
            
            print("Response:")
            full_response = ""
            
            # Process the stream
            for line in response.iter_lines():
                if line:
                    line = line.decode('utf-8')
                    if line.startswith('data: '):
                        try:
                            data = json.loads(line[6:])
                            
                            if data['type'] == 'metadata':
                                print(f"[Metadata] Thread ID: {data['thread_id']}, New: {data['new_thread_created']}")
                            
                            elif data['type'] == 'delta':
                                print(data['content'], end='', flush=True)
                                full_response += data['content']
                            
                            elif data['type'] == 'message_id':
                                print(f"\n[Message ID: {data['message_id']}]", end='', flush=True)
                            
                            elif data['type'] == 'done':
                                print(f"\n[Stream completed. Thread ID: {data['thread_id']}]")
                            
                            elif data['type'] == 'error':
                                print(f"\n[Error: {data['content']}]")
                            
                        except json.JSONDecodeError as e:
                            print(f"\n[JSON Error: {e}]")
            
            print(f"\n\nFull response: {full_response}")
            
        except requests.exceptions.RequestException as e:
            print(f"Request error: {e}")
        except KeyboardInterrupt:
            print("\nTest interrupted by user")
            break

def test_with_history():
    """Test the streaming endpoint with conversation history."""
    
    base_url = "http://localhost:8001"
    
    print("\n" + "="*60)
    print("Testing with conversation history (API mode)")
    print("="*60)
    
    # First message
    first_request = {
        "user_input": "Remember that my favorite number is 42. What is my favorite number plus 8?",
        "history_mode": "api"
    }
    
    print(f"First request: {first_request['user_input']}")
    
    response = requests.post(
        f"{base_url}/invoke_stream",
        json=first_request,
        stream=True
    )
    
    thread_id = None
    first_response = ""
    
    for line in response.iter_lines():
        if line:
            line = line.decode('utf-8')
            if line.startswith('data: '):
                data = json.loads(line[6:])
                
                if data['type'] == 'metadata':
                    thread_id = data['thread_id']
                    print(f"Thread ID: {thread_id}")
                
                elif data['type'] == 'delta':
                    print(data['content'], end='', flush=True)
                    first_response += data['content']
                
                elif data['type'] == 'done':
                    print("\n[First message complete]")
    
    if thread_id:
        # Second message using the same thread
        second_request = {
            "user_input": "What was my favorite number again? And what was the calculation result?",
            "history_mode": "api",
            "thread_id": thread_id
        }
        
        print(f"\n\nSecond request (same thread): {second_request['user_input']}")
        
        response = requests.post(
            f"{base_url}/invoke_stream",
            json=second_request,
            stream=True
        )
        
        second_response = ""
        
        for line in response.iter_lines():
            if line:
                line = line.decode('utf-8')
                if line.startswith('data: '):
                    data = json.loads(line[6:])
                    
                    if data['type'] == 'delta':
                        print(data['content'], end='', flush=True)
                        second_response += data['content']
                    
                    elif data['type'] == 'done':
                        print("\n[Second message complete]")

if __name__ == "__main__":
    print("MarketGuru 2.0 Streaming Endpoint Test")
    print("Make sure the API is running at http://localhost:8001")
    
    try:
        # Test basic connectivity
        response = requests.get("http://localhost:8001/docs")
        if response.status_code != 200:
            print("Warning: API might not be running properly")
    except:
        print("Error: Cannot connect to API. Make sure it's running with:")
        print("  docker-compose up")
        print("  or")
        print("  uvicorn api_main:app --host 0.0.0.0 --port 8001 --reload")
        sys.exit(1)
    
    # Run tests
    test_streaming_endpoint()
    test_with_history()
    
    print("\n\nAll tests completed!")