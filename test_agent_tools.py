"""Test if Kitchen Agent tools are being called"""
import sys
sys.path.insert(0, 'Agents')

from Agents.KitchenAgent import kitchen_agent

if kitchen_agent:
    print("✓ Kitchen Agent loaded")
    print(f"  Tools: {kitchen_agent.tools if hasattr(kitchen_agent, 'tools') else 'N/A'}")
    
    # Simple test
    prompt = "Query the orders table for pending orders using the execute_database_query tool"
    print(f"\n🔬 Testing with prompt: {prompt}\n")
    
    response = kitchen_agent.run(prompt)
    print(f"\n📤 Response: {response}\n")
else:
    print("❌ Kitchen Agent not available")
