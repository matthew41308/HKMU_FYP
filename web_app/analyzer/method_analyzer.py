import ast
import json
from typing import Dict, List, Set, Optional, Any
from dataclasses import dataclass, asdict

@dataclass
class MethodParameter:
    parameter_name: str
    parameter_type: str
    is_required: bool
    default_value: Optional[str]
    description: str = ""

@dataclass
class Method:
    method_name: str
    return_type: str
    visibility: str
    is_static: bool
    description: str
    parameters: List[MethodParameter]
    location: str  # This will store the class name if method is inside a class, or "global" if it's a standalone function

class MethodAnalyzer(ast.NodeVisitor):
    def __init__(self):
        self.methods = []
        self.current_class = None

    def _format_complex_type(self, node: ast.Subscript) -> str:
        if isinstance(node.value, ast.Name):
            base_type = node.value.id
            if isinstance(node.slice, ast.Name):
                param_type = node.slice.id
            elif isinstance(node.slice, ast.Constant):
                param_type = str(node.slice.value)
            else:
                param_type = 'Any'
            return f'{base_type}[{param_type}]'
        return 'Any'

    def get_return_type(self, node: ast.FunctionDef) -> str:
        # Check for return annotation
        if node.returns:
            if isinstance(node.returns, ast.Name):
                return node.returns.id
            elif isinstance(node.returns, ast.Constant):
                return str(node.returns.value)
            elif isinstance(node.returns, ast.Subscript):
                return self._format_complex_type(node.returns)
        
        # Try to infer return type from return statements
        return_types = set()
        for child in ast.walk(node):
            if isinstance(child, ast.Return) and child.value:
                if isinstance(child.value, ast.Name):
                    return_types.add(child.value.id)
                elif isinstance(child.value, ast.Constant):
                    return_types.add(type(child.value.value).__name__)
        
        if return_types:
            return ' | '.join(return_types)
        return 'Any'

    def get_visibility(self, node: ast.FunctionDef) -> str:
        if node.name.startswith('__'):
            return 'private'
        elif node.name.startswith('_'):
            return 'protected'
        return 'public'

    def is_static_method(self, node: ast.FunctionDef) -> bool:
        return any(isinstance(dec, ast.Name) and dec.id == 'staticmethod' 
                  for dec in node.decorator_list)

    def extract_parameters(self, node: ast.FunctionDef) -> List[MethodParameter]:
        parameters = []
        
        # Skip 'self' parameter for instance methods
        start_idx = 1 if (self.current_class and not self.is_static_method(node)) else 0
        
        for arg in node.args.args[start_idx:]:
            param_type = 'Any'
            if arg.annotation:
                if isinstance(arg.annotation, ast.Name):
                    param_type = arg.annotation.id
                elif isinstance(arg.annotation, ast.Subscript):
                    param_type = self._format_complex_type(arg.annotation)

            # Find default value
            default_value = None
            is_required = True
            arg_idx = node.args.args.index(arg)
            defaults_idx = arg_idx - (len(node.args.args) - len(node.args.defaults))
            if defaults_idx >= 0:
                default = node.args.defaults[defaults_idx]
                if isinstance(default, ast.Constant):
                    default_value = str(default.value)
                    is_required = False

            parameters.append(MethodParameter(
                parameter_name=arg.arg,
                parameter_type=param_type,
                is_required=is_required,
                default_value=default_value,
                description=""  # Could be extracted from docstring if available
            ))
        
        return parameters

    def visit_ClassDef(self, node: ast.ClassDef):
        self.current_class = node.name
        self.generic_visit(node)
        self.current_class = None

    def visit_FunctionDef(self, node: ast.FunctionDef):
        method = Method(
            method_name=node.name,
            return_type=self.get_return_type(node),
            visibility=self.get_visibility(node),
            is_static=self.is_static_method(node),
            description=ast.get_docstring(node) or "",
            parameters=self.extract_parameters(node),
            location=self.current_class or "global"
        )
        
        self.methods.append(method)
        self.generic_visit(node)

def method_analyzer(code: str) -> Dict:
    try:
        tree = ast.parse(code)
    except Exception as parse_err:
        print(f"Ignored parsing error in method analyzer: {parse_err}")
    
    analyzer = MethodAnalyzer()
    
    try:
        analyzer.visit(tree)
    except Exception as visitor_err:
        print(f"Ignored visitor error in method analyzer: {visitor_err}")
    
    return {'methods': [asdict(m) for m in analyzer.methods]}

def analyze_method(file_location: str):
    with open(file_location,"r") as f:
        sample_code=f.read()
        result = method_analyzer(sample_code)
        return result
    
if __name__ == "__main__":
    file_location ="project_sample/library_management_python/Controllers/UserManager.py"
    analyzed_method=analyze_method(file_location)
    print(analyzed_method)