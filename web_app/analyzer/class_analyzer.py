import ast
import os
import sys
import json
import pymysql
from typing import List
from dataclasses import dataclass, asdict
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../")))
from config.dbConfig import db_connect,db,cursor,isDBconnected

# ✅ 匯入 MySQL 設定
from config.dbConfig import db_connect

@dataclass
class Component:
    component_name: str
    component_type: str
    description: str = ""
    attributes: List[str] = None
    methods: List[str] = None
    organization_name: str = ""  # Added field for organization name
    organization_path: str = ""  # Added field for organization path

@dataclass
class ComponentDependency:
    source_component: str
    target_component: str
    dependency_type: str
    organization_name: str = ""  # Added field for organization name
    organization_path: str = ""  # Added field for organization path


class ClassAnalyzer(ast.NodeVisitor):
    def __init__(self, file_path: str):  # Modified to accept file_path
        self.components = []
        self.dependencies = []
        self.current_class = None
        self.all_classes = set()
        self.external_dependencies = set()
        
        # Get organization information
        self.organization_name = ""
        self.organization_path = ""
        self._set_organization_info(file_path)

    def _set_organization_info(self, file_path: str):
        """
        Set organization information based on file path
        Args:
            file_path: Path to the file being analyzed
        """
        # Get absolute path
        abs_path = os.path.abspath(file_path)
        
        # Get parent directory as organization
        parent_dir = os.path.dirname(abs_path)
        self.organization_name = os.path.basename(parent_dir)
        
        # Get relative path from project root (assuming file_path includes project structure)
        try:
            # Find the path relative to the first parent that has __init__.py
            current_path = parent_dir
            relative_parts = []
            
            while current_path:
                if os.path.isfile(os.path.join(current_path, '__init__.py')):
                    relative_parts.append(os.path.basename(current_path))
                    current_path = os.path.dirname(current_path)
                else:
                    break
            
            self.organization_path = '/'.join(reversed(relative_parts))
        except Exception:
            self.organization_path = self.organization_name

    def visit_ClassDef(self, node: ast.ClassDef):
        """ Record class attributes and methods with organization info """
        methods = [item.name for item in node.body if isinstance(item, ast.FunctionDef)]
        component = Component(
            component_name=node.name,
            component_type="class",
            description=ast.get_docstring(node) or "",
            attributes=[],
            methods=methods,
            organization_name=self.organization_name,  # Add organization name
            organization_path=self.organization_path   # Add organization path
        )
        self.components.append(component)
        self.all_classes.add(node.name)

        # Handle inheritance
        for base in node.bases:
            if isinstance(base, ast.Name):
                base_name = base.id
                self.dependencies.append(ComponentDependency(
                    source_component=node.name,
                    target_component=base_name,
                    dependency_type='extends'
                ))

        self.current_class = node.name
        self.generic_visit(node)
        self.current_class = None

def class_analyzer(code: str, file_path: str):  # Modified to accept file_path
    """ Parse code and return components & dependencies with organization info """
    tree = ast.parse(code)
    analyzer = ClassAnalyzer(file_path)  # Pass file_path to analyzer
    analyzer.visit(tree)

    return {
        'components': [asdict(c) for c in analyzer.components],
        'dependencies': [asdict(d) for d in analyzer.dependencies]
    }

def analyze_class(file_location: str):
    with open(file_location, "r") as f:
        sample_code = f.read()
        result = class_analyzer(sample_code, file_location)  # Pass file_location
        return result


if __name__ == "__main__":
    file_location = "project_sample/library_management_python/Controllers/UserManager.py"  # 測試用
    print(analyze_class(file_location))
