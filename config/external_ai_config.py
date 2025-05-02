import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))

from openai import AzureOpenAI
def get_openai():
    client = AzureOpenAI(
    azure_endpoint=os.getenv("OPENAI_ENDPOINT"),
    api_key=os.getenv("OPENAI_API_KEY"),
    api_version="2024-12-01-preview"
    )
    return client

def get_prompt(document_type: str, file_content) -> str:
    """
    Returns a prompt to generate a PlantUML diagram of a given type.
    document_type: "use case diagram", "sequence diagram", etc.
    """
    return f"""Please help me generate this document type: {document_type}.
    If it is not a technical document, please respond with 0 only.

    From the below, the data inside are metadata extracted from a project. 
    The data includes information of the actual code. 
    You are given that the end of the data indicate the order of data that will appear. 
    From the relationship of the data, 
    please try to draw a {document_type} to illustrate the design of the project. 
    Please only send back the PlantUML syntax code without any explanation.
    Start of the metadata:
    {file_content}

    """
