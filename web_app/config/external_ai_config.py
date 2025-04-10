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
    # 定義不合法的文件類型
    invalid_types = ['business', 'marketing', 'non-technical']

    # 檢查是否是 "Others" 或不合法的類型
    if document_type.lower() in invalid_types:
        return "0"  # AI 回應 0，表示這不是有效的技術文檔

    # 生成常規的 prompt
    return f"""Please help me generate this document type: {document_type}.
If it is not a technical document for project management, please respond with 0 only.

From the given file, the data inside are metadata extracted from a project, 
the data includes information of the actual code. From the relationship of the data, 
please try to draw a {document_type} to illustrate the design of the project. 
The graph should be in the format of PlantUML with an older version. 
Please only send back the PlantUML code without any explanation.
"""
