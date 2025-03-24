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

def get_prompt(document_type: str) -> str:
    """
    Returns a prompt to generate a PlantUML diagram of a given type.
    document_type: "use case diagram", "sequence diagram", etc.
    """
    return f"""From the given file, the data inside are metadata extracted from a project, 
the data includes information of the actual code. From the relationship of the data, 
please try to draw a {document_type} to illustrate the design of the project. 
The graph should be in the format of PlantUML with an older version. 
Please only send back the PlantUML code without any explanation.
"""
