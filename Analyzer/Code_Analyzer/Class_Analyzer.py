import ast
import os
import json
from typing import Dict, List, Set
from dataclasses import dataclass, asdict

@dataclass
class Component:
    component_name: str
    component_type: str
    description: str = ""
    attributes: List[str] = None
    methods: List[str] = None

@dataclass
class ComponentDependency:
    source_component: str  # Using component names instead of IDs for simplicity
    target_component: str
    dependency_type: str

class ClassAnalyzer(ast.NodeVisitor):
    def __init__(self):
        self.components = []
        self.dependencies = []
        self.current_class = None
        self.all_classes = set()

    def get_component_type(self, node: ast.ClassDef) -> str:
        # Determine component type based on class name and decorators
        name = node.name.lower()
        if any(d.id == 'service' for d in node.decorator_list if isinstance(d, ast.Name)):
            return 'service'
        elif 'controller' in name:
            return 'controller'
        elif 'repository' in name:
            return 'repository'
        elif 'interface' in name or any(isinstance(b, ast.Name) and b.id.startswith('Abstract') for b in node.bases):
            return 'interface'
        elif any(isinstance(b, ast.Name) and b.id == 'Utility' for b in node.bases):
            return 'utility'
        else:
            return 'class'
        
    def extract_attributes(self, node: ast.ClassDef) -> List[str]:
        attributes = []
        
        # Look for attributes in the class body
        for item in node.body:
            # Direct assignments in class body
            if isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name):
                        attributes.append(target.id)
            
            # Look for attributes in __init__ method
            elif isinstance(item, ast.FunctionDef) and item.name == '__init__':
                for stmt in item.body:
                    if isinstance(stmt, ast.Assign):
                        for target in stmt.targets:
                            # Check for self.attribute assignments
                            if isinstance(target, ast.Attribute) and \
                               isinstance(target.value, ast.Name) and \
                               target.value.id == 'self':
                                attributes.append(target.attr)
                    # Handle multiple assignments in one line
                    elif isinstance(stmt, ast.AnnAssign) and \
                         isinstance(stmt.target, ast.Attribute) and \
                         isinstance(stmt.target.value, ast.Name) and \
                         stmt.target.value.id == 'self':
                        attributes.append(stmt.target.attr)

        return list(set(attributes))  # Remove duplicates

    def visit_ClassDef(self, node: ast.ClassDef):
        # Extract methods
        methods = [item.name for item in node.body if isinstance(item, ast.FunctionDef)]
        
        # Create component
        component = Component(
            component_name=node.name,
            component_type=self.get_component_type(node),
            description=ast.get_docstring(node) or "",
            attributes=self.extract_attributes(node),
            methods=methods
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
                    dependency_type='extends' if component.component_type != 'interface' else 'implements'
                ))
        
        self.current_class = node.name
        self.generic_visit(node)
        self.current_class = None

    def visit_Call(self, node: ast.Call):
        if self.current_class and isinstance(node.func, ast.Name):
            called_class = node.func.id
            if called_class in self.all_classes and called_class != self.current_class:
                self.dependencies.append(ComponentDependency(
                    source_component=self.current_class,
                    target_component=called_class,
                    dependency_type='uses'
                ))
        self.generic_visit(node)

def analyze_code(code: str) -> Dict:
    tree = ast.parse(code)
    analyzer = ClassAnalyzer()
    analyzer.visit(tree)
    
    return {
        'components': [asdict(c) for c in analyzer.components],
        'dependencies': [asdict(d) for d in analyzer.dependencies]
    }

def main():
    # Example usage with more attribute cases
    sample_code = """
class BaseService:
    base_attribute = "base"  # Class-level attribute
    
    def __init__(self):
        self.name = "base"    # Instance attribute
        self._private = True  # Private attribute
    
    def base_method(self):
        pass

class UserInterface:
    def process_user(self):
        pass

@service
class UserService(BaseService, UserInterface):
    \"\"\"Handles user-related operations\"\"\"
    service_type = "user"  # Class-level attribute
    
    def __init__(self):
        super().__init__()
        self.users = []          # Instance attribute
        self.active = True       # Instance attribute
        self._cache = {}         # Private attribute
        
    def add_user(self, user):
        self.users.append(user)
        
    def process_user(self):
        self.base_method()

class UserController:
    def __init__(self):
        self.service = UserService()  # Instance attribute
        self.enabled: bool = True     # Typed attribute
    
    def handle_user(self):
        self.service.process_user()
    """
    
    result = analyze_code(sample_code)
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()