import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))
import openai
def get_openai():
    client = openai.AzureOpenAI(
    azure_endpoint="https://fyp2025.openai.azure.com",
    api_key="3kDNJlmeMVUQa1a88MWNOWnWQtb2Mdgt0J9EKKcNLubRhXngK3PiJQQJ99BBACYeBjFXJ3w3AAABACOGDCXh",
    api_version="2024-02-01"
)
    return client