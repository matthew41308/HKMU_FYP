import os
from enum import Enum
from dataclasses import dataclass, asdict
from typing import List

class OrganizationType(Enum):
    MODULE = "module"      # has __init__.py
    PACKAGE = "package"    # no __init__.py

@dataclass
class Organization:
    organization_name: str
    organization_path: str
    organization_type: OrganizationType

def analyze_organization(root_path: str) -> dict:
    """
    Analyze all organizational units (modules and packages)
    Args:
        root_path: Root directory path to start analysis
    Returns:
        dict: Dictionary containing organization information
    """
    organizations = []

    for dirpath, dirnames, filenames in os.walk(root_path):
        # Skip hidden directories and __pycache__
        dirnames[:] = [d for d in dirnames if not d.startswith('.') and d != '__pycache__']
        
        for dirname in dirnames:
            full_path = os.path.join(dirpath, dirname)
            has_init = '__init__.py' in os.listdir(full_path)
            relative_path = os.path.relpath(full_path, root_path)
            
            # Determine organization type
            organization_type = OrganizationType.MODULE if has_init else OrganizationType.PACKAGE
            
            organization = Organization(
                organization_name=dirname,
                organization_path=relative_path,
                organization_type=organization_type
            )
            organizations.append(asdict(organization))

    return {'organizations': organizations}

if __name__ == "__main__":
    # Example usage
    project_path = "project_sample/library_management_python/"
    result = analyze_organization(project_path)
    print(result)