import ast
import json
from typing import Dict, List, Set, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum

class Scope(str, Enum):
    GLOBAL = 'global'
    CLASS = 'class'
    METHOD = 'method'
    BLOCK = 'block'

class Visibility(str, Enum):
    PUBLIC = 'public'
    PRIVATE = 'private'
    PROTECTED = 'protected'
    INTERNAL = 'internal'

class UsageType(str, Enum):
    READ = 'read'
    WRITE = 'write'
    PARAMETER = 'parameter'
    RETURN = 'return'
    DECLARATION = 'declaration'

class FlowType(str, Enum):
    ASSIGNMENT = 'assignment'
    PARAMETER_PASSING = 'parameter_passing'
    RETURN_VALUE = 'return_value'
    REFERENCE = 'reference'

@dataclass
class Variable:
    variable_name: str
    variable_type: str
    scope: Scope
    is_constant: bool = False
    is_static: bool = False
    visibility: Optional[Visibility] = None
    description: str = ""
    component_name: Optional[str] = None  # Class name if applicable
    method_name: Optional[str] = None    # Method name if applicable
    line_number: int = None              # Added line number
    declaration_type: str = "variable"    # Added to distinguish different types of declarations

@dataclass
class VariableUsage:
    variable_name: str
    usage_type: UsageType
    line_number: int
    component_name: Optional[str] = None
    method_name: Optional[str] = None

@dataclass
class VariableFlow:
    source_variable: str
    target_variable: str
    flow_type: FlowType
    line_number: int                    # Added line number
    source_method: Optional[str] = None
    target_method: Optional[str] = None
    source_component: Optional[str] = None
    target_component: Optional[str] = None

class VariableAnalyzer(ast.NodeVisitor):
    def __init__(self):
        self.variables = []  # Keeping as list to track all declarations
        self.usages = []
        self.flows = []
        self.current_class = None
        self.current_method = None
        self.current_scope = Scope.GLOBAL
        self.scope_stack = []

    def enter_scope(self, scope: Scope):
        self.scope_stack.append(self.current_scope)
        self.current_scope = scope

    def exit_scope(self):
        self.current_scope = self.scope_stack.pop()

    def get_visibility(self, name: str) -> Visibility:
        if name.startswith('__'):
            return Visibility.PRIVATE
        elif name.startswith('_'):
            return Visibility.PROTECTED
        return Visibility.PUBLIC

    def infer_type(self, node: ast.AST) -> str:
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Constant):
            return type(node.value).__name__
        elif isinstance(node, ast.List):
            return 'List'
        elif isinstance(node, ast.Dict):
            return 'Dict'
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                return node.func.id
        return 'Any'

    def visit_ClassDef(self, node: ast.ClassDef):
        self.current_class = node.name
        self.enter_scope(Scope.CLASS)
        
        # Handle class variables
        for item in node.body:
            if isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name):
                        self.variables.append(Variable(
                            variable_name=target.id,
                            variable_type=self.infer_type(item.value),
                            scope=Scope.CLASS,
                            is_constant=target.id.isupper(),
                            is_static=True,
                            visibility=self.get_visibility(target.id),
                            component_name=self.current_class,
                            line_number=item.lineno,
                            declaration_type="class_attribute"
                        ))

                        self.usages.append(VariableUsage(
                            variable_name=target.id,
                            usage_type=UsageType.DECLARATION,
                            line_number=item.lineno,
                            component_name=self.current_class
                        ))

        self.generic_visit(node)
        self.current_class = None
        self.exit_scope()

    def visit_FunctionDef(self, node: ast.FunctionDef):
        self.current_method = node.name
        self.enter_scope(Scope.METHOD)

        # Handle parameters
        for arg in node.args.args:
            if arg.arg == 'self':
                continue
                
            var_type = 'Any'
            if arg.annotation:
                if isinstance(arg.annotation, ast.Name):
                    var_type = arg.annotation.id
                elif isinstance(arg.annotation, ast.Constant):
                    var_type = str(arg.annotation.value)

            self.variables.append(Variable(
                variable_name=arg.arg,
                variable_type=var_type,
                scope=Scope.METHOD,
                component_name=self.current_class,
                method_name=self.current_method,
                line_number=node.lineno,
                declaration_type="parameter"
            ))

            self.usages.append(VariableUsage(
                variable_name=arg.arg,
                usage_type=UsageType.PARAMETER,
                line_number=node.lineno,
                component_name=self.current_class,
                method_name=self.current_method
            ))

        self.generic_visit(node)
        self.current_method = None
        self.exit_scope()

    def visit_Assign(self, node: ast.Assign):
        for target in node.targets:
            if isinstance(target, ast.Name):
                self.variables.append(Variable(
                    variable_name=target.id,
                    variable_type=self.infer_type(node.value),
                    scope=self.current_scope,
                    is_constant=target.id.isupper(),
                    component_name=self.current_class,
                    method_name=self.current_method,
                    line_number=node.lineno,
                    declaration_type="assignment"
                ))

                self.usages.append(VariableUsage(
                    variable_name=target.id,
                    usage_type=UsageType.WRITE,
                    line_number=node.lineno,
                    component_name=self.current_class,
                    method_name=self.current_method
                ))

                if isinstance(node.value, ast.Name):
                    self.flows.append(VariableFlow(
                        source_variable=node.value.id,
                        target_variable=target.id,
                        flow_type=FlowType.ASSIGNMENT,
                        line_number=node.lineno,
                        source_method=self.current_method,
                        target_method=self.current_method,
                        source_component=self.current_class,
                        target_component=self.current_class
                    ))

        self.generic_visit(node)

    def visit_Name(self, node: ast.Name):
        if isinstance(node.ctx, ast.Load):
            self.usages.append(VariableUsage(
                variable_name=node.id,
                usage_type=UsageType.READ,
                line_number=node.lineno,
                component_name=self.current_class,
                method_name=self.current_method
            ))

    def visit_Return(self, node: ast.Return):
        if isinstance(node.value, ast.Name):
            self.usages.append(VariableUsage(
                variable_name=node.value.id,
                usage_type=UsageType.RETURN,
                line_number=node.lineno,
                component_name=self.current_class,
                method_name=self.current_method
            ))

def analyze_variables(code: str) -> Dict:
    tree = ast.parse(code)
    analyzer = VariableAnalyzer()
    analyzer.visit(tree)
    
    return {
        'variables': [asdict(v) for v in analyzer.variables],
        'usages': [asdict(u) for u in analyzer.usages],
        'flows': [asdict(f) for f in analyzer.flows]
    }

def main():
    # Example usage
    sample_code = """
from typing import List, Dict, Optional

GLOBAL_CONSTANT = 42

class UserService:
    DEFAULT_LIMIT = 100
    
    def __init__(self):
        self._users = []
        self.__private_var = None
        self.DEFAULT_LIMIT = 200  # Reassigning class variable
    
    def add_user(self, user_data: Dict, validate: bool = True) -> bool:
        temp_data = user_data.copy()
        DEFAULT_LIMIT = 50  # Local variable with same name
        result = self._validate(temp_data) if validate else True
        if result:
            self._users.append(temp_data)
        return result
    
    def _validate(self, data: Dict) -> bool:
        valid = True
        min_age = 18
        if data.get('age', 0) < min_age:
            valid = False
        return valid

def process_data(input_data: List[Dict]) -> Optional[Dict]:
    processed = input_data.copy()
    result = {'status': 'success', 'data': processed}
    return result
    """
    
    result = analyze_variables(sample_code)
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()