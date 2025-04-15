import os
from enum import Enum
from dataclasses import dataclass, asdict
from typing import List


@dataclass
class Organization:
    organization_name: str
    organization_path: str
    organization_type: str

def dfs_collect_orgs(current_dir: str, root_path: str) -> List[dict]:
    """
    Recursively traverse the directory structure using DFS not BFS.
    A directory is considered a leaf organization (and thus output) only if it has no subdirectories.
    
    Args:
        current_dir (str): The directory to process.
        root_path (str): The original root directory (used to calculate relative paths).
        
    Returns:
        List[dict]: A list of organization dictionaries for leaf directories.
    """
    try:
        entries = os.listdir(current_dir)
    except Exception as err:
        print(f"Error accessing directory {current_dir}: {err}")
        return []
    
    # Filter subdirectories: ignore hidden directories and __pycache__
    sub_dirs = [
        entry for entry in entries 
        if os.path.isdir(os.path.join(current_dir, entry)) 
           and not entry.startswith('.') 
           and entry != '__pycache__'
    ]
    
    if not sub_dirs:
        # Leaf folder: no subdirectories.
        base_name = os.path.basename(current_dir)
        has_init = '__init__.py' in entries
        org_type = 'module' if has_init else 'package'
        relative_path = os.path.relpath(current_dir, root_path)
        organization = Organization(
            organization_name=base_name,
            organization_path=relative_path,
            organization_type=org_type
        )
        return [asdict(organization)]
    else:
        organizations = []
        for sub in sub_dirs:
            full_sub_path = os.path.join(current_dir, sub)
            organizations.extend(dfs_collect_orgs(full_sub_path, root_path))
        return organizations

def analyze_organization(root_path: str) -> dict:
    """
    Analyze organizational units using DFS traversal.
    
    This version only outputs the deepest directories (the leaf organizations)
    so that a parent organization is not duplicated if it contains subfolders.
    
    Args:
        root_path (str): Root directory path to start analysis.
    
    Returns:
        dict: Dictionary containing a list of organization information.
    """
    try:
        organizations = dfs_collect_orgs(root_path, root_path)
    except Exception as parse_err:
        print(f"Ignored parsing error in organization analyzer: {parse_err}")
    return {"organizations": organizations}

if __name__ == "__main__":
    # Example usage
    project_path = "project_sample/library_management_python/"
    result = analyze_organization(project_path)
    print(result)