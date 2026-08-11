import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

key = os.getenv('OPENAI_API_KEY') or os.getenv('MESH_API_KEY')
base_url = os.getenv('OPENAI_BASE_URL', 'https://api.groq.com/openai/v1')
model = os.getenv('LLM_MODEL', 'llama-3.1-8b-instant')

print(f"Using Key: {key[:10] if key else 'NONE'}...")
print(f"Using Base URL: {base_url}")
print(f"Using Model: {model}")

try:
    print("\nConnecting to Groq endpoint...")
    
    llm = ChatOpenAI(
        model=model,
        api_key=key,
        base_url=base_url
    )
    
    response = llm.invoke("Say 'Groq Connection Successful!'")
    print(f"\n✅ SUCCESS: {response.content}")
    
except Exception as e:
    print(f"\n❌ FATAL ERROR: {str(e)}")