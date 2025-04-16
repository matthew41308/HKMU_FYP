import ast
import os
import sys
import json
import pymysql
from typing import List
from dataclasses import dataclass, asdict
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))

@dataclass
class Component:
    component_name: str
    component_type: str    # "class", "non-class", or "mixed"
    description: str = ""
    attributes: List[str] = None
    methods: List[str] = None
    organization_name: str = ""
    organization_path: str = ""

@dataclass
class ComponentDependency:
    source_component: str
    target_component: str
    dependency_type: str
    organization_name: str = ""
    organization_path: str = ""

class ComponentAnalyzer(ast.NodeVisitor):
    """
    Analyzer for a Python component (file).
    
    It collects:
      - Global (module-level) functions.
      - Class definitions along with their methods.
      - Inheritance dependencies between classes.
      
    It also gathers organization information from the file's path.
    """
    def __init__(self, file_path: str):
        self.component_classes = []  # Each entry: { "name": str, "methods": List[str], "docstring": str }
        self.component_methods = []  # Global functions (module-level)
        self.dependencies = []       # Inheritance dependencies between classes
        self.organization_name = ""
        self.organization_path = ""
        self._set_organization_info(file_path)
        
    def _set_organization_info(self, file_path: str):
        abs_path = os.path.abspath(file_path)
        parent_dir = os.path.dirname(abs_path)
        self.organization_name = os.path.basename(parent_dir)
        try:
            current_path = parent_dir
            relative_parts = []
            while current_path:
                # If an __init__.py exists, consider this folder in the organization structure.
                if os.path.isfile(os.path.join(current_path, '__init__.py')):
                    relative_parts.append(os.path.basename(current_path))
                    current_path = os.path.dirname(current_path)
                else:
                    break
            self.organization_path = '/'.join(reversed(relative_parts))
        except Exception:
            self.organization_path = self.organization_name

    def visit_Module(self, node: ast.Module):
        # Check for global (module-level) functions.
        for stmt in node.body:
            if isinstance(stmt, ast.FunctionDef):
                self.component_methods.append(stmt.name)
            else:
                self.visit(stmt)
                
    def visit_ClassDef(self, node: ast.ClassDef):
        # Record class methods and docstring.
        methods = [item.name for item in node.body if isinstance(item, ast.FunctionDef)]
        self.component_classes.append({
            "name": node.name,
            "methods": methods,
            "docstring": ast.get_docstring(node) or ""
        })
        # Record inheritance dependencies (only when the base is a simple name).
        for base in node.bases:
            if isinstance(base, ast.Name):
                base_name = base.id
                self.dependencies.append({
                    "source_component": node.name,
                    "target_component": base_name,
                    "dependency_type": "extends",
                    "organization_name": self.organization_name,
                    "organization_path": self.organization_path
                })
        self.generic_visit(node)

def component_analyzer(code: str, file_path: str):
    """
    Analyze a Python file and returns a dictionary with the following keys:
       - "components": a list of one component, built from the file name and its analyzed content.
       - "dependencies": a list of inheritance dependencies (if any).
       - "file_location": the provided file path.
    
    The component is built in such a way that:
       - The name is the file name (without extension).
       - The type is "class" if only class definitions are found,
         "non-class" if only global functions are found,
         and "mixed" if both are present.
       - The "methods" field merges all class methods and global functions.
    """
    try:
        tree = ast.parse(code)
    except Exception as parse_err:
        print(f"Ignored parsing error in file {file_path}: {parse_err}")
        return {
            "components": [],
            "dependencies": [],
            "file_location": file_path
        }
    
    analyzer = ComponentAnalyzer(file_path)
    try:
        analyzer.visit(tree)
    except Exception as visitor_err:
        print(f"Ignored visitor error in file {file_path}: {visitor_err}")
    
    # Collect methods defined inside classes.
    class_methods = []
    for cls in analyzer.component_classes:
        class_methods.extend(cls["methods"])
    
    # Decide on the component type.
    if analyzer.component_classes and analyzer.component_methods:
        comp_type = "mixed"
    elif analyzer.component_classes:
        comp_type = "class"
    elif analyzer.component_methods:
        comp_type = "non-class"
    else:
        comp_type = "non-class"  # default if no definitions are found
    
    # Merge methods from classes and global functions. Remove possible duplicates.
    all_methods = list(dict.fromkeys(class_methods + analyzer.component_methods))
    
    # Use the file name (without extension) for the component name.
    component_name = os.path.splitext(os.path.basename(file_path))[0]
    
    component = Component(
        component_name=component_name,
        component_type=comp_type,
        description="",
        attributes=[],
        methods=all_methods,
        organization_name=analyzer.organization_name,
        organization_path=analyzer.organization_path
    )
    
    return {
        "components": [asdict(component)],
        "dependencies": analyzer.dependencies,
        "file_location": file_path
    }

def analyze_component(file_location: str):
    """
    Read a Python file and analyze it as a component, producing
    a result with keys "components", "dependencies", and "file_location".
    This function is designed not to impact your process_file logic.
    """
    with open(file_location, "r", encoding="utf-8") as f:
        code = f.read()
    result = component_analyzer(code, file_location)
    return result

# For testing purposes only. 
if __name__ == "__main__":
    file_location = "project_sample/library_management_python/Misc/functions.py"
    analysis_result = analyze_component(file_location)
    print(json.dumps(analysis_result, indent=2))