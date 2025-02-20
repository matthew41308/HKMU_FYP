import ast
import json
from typing import Dict, List, Optional, Any
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
    method_name: Optional[str] = None     # Method name if applicable
    line_number: int = None               # Added line number
    declaration_type: str = "variable"    # To distinguish different types of declarations

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
    line_number: int  # Added line number
    source_method: Optional[str] = None
    target_method: Optional[str] = None
    source_component: Optional[str] = None
    target_component: Optional[str] = None

class VariableAnalyzer(ast.NodeVisitor):
    def __init__(self):
        self.variables = []  # All variable declarations
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
        # Check only the final part of a compound name (after the last dot)
        final_name = name.split('.')[-1]
        if final_name.startswith('__'):
            return Visibility.PRIVATE
        elif final_name.startswith('_'):
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

    def get_full_name(self, node: ast.AST) -> str:
        """
        Recursively build the full name for an attribute chain.
        For example, for `self.something.anotherthing` it returns
        "self.something.anotherthing".
        """
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return self.get_full_name(node.value) + '.' + node.attr
        return ''

    def visit_ClassDef(self, node: ast.ClassDef):
        self.current_class = node.name
        self.enter_scope(Scope.CLASS)
        
        # Handle class-level variable declarations.
        for item in node.body:
            if isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name):
                        var_name = target.id
                        self.variables.append(Variable(
                            variable_name=var_name,
                            variable_type=self.infer_type(item.value),
                            scope=Scope.CLASS,
                            is_constant=var_name.isupper(),
                            is_static=True,
                            visibility=self.get_visibility(var_name),
                            component_name=self.current_class,
                            line_number=item.lineno,
                            declaration_type="class_attribute"
                        ))
                        self.usages.append(VariableUsage(
                            variable_name=var_name,
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
        # Handle parameters (skip "self").
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
            if isinstance(target, (ast.Name, ast.Attribute)):
                var_name = self.get_full_name(target)
                # Check if the final part of the variable name is uppercase for constants
                is_constant = var_name.split('.')[-1].isupper()
                self.variables.append(Variable(
                    variable_name=var_name,
                    variable_type=self.infer_type(node.value),
                    scope=self.current_scope,
                    is_constant=is_constant,
                    component_name=self.current_class,
                    method_name=self.current_method,
                    line_number=node.lineno,
                    declaration_type="assignment"
                ))
                self.usages.append(VariableUsage(
                    variable_name=var_name,
                    usage_type=UsageType.WRITE,
                    line_number=node.lineno,
                    component_name=self.current_class,
                    method_name=self.current_method
                ))
                
                # If the right-hand side is also a Name or an Attribute,
                # register the flow—from the source variable to the target.
                if isinstance(node.value, (ast.Name, ast.Attribute)):
                    source_var = self.get_full_name(node.value)
                    self.flows.append(VariableFlow(
                        source_variable=source_var,
                        target_variable=var_name,
                        flow_type=FlowType.ASSIGNMENT,
                        line_number=node.lineno,
                        source_method=self.current_method,
                        target_method=self.current_method,
                        source_component=self.current_class,
                        target_component=self.current_class
                    ))
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute):
        # Only record a usage for the outermost attribute in a chain.
        if not (hasattr(node, 'parent') and isinstance(node.parent, ast.Attribute)):
            if isinstance(node.ctx, ast.Load):
                full_name = self.get_full_name(node)
                self.usages.append(VariableUsage(
                    variable_name=full_name,
                    usage_type=UsageType.READ,
                    line_number=node.lineno,
                    component_name=self.current_class,
                    method_name=self.current_method
                ))
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name):
        # If this Name node is part of an attribute chain, skip it since
        # the outer Attribute already registers the complete variable.
        if hasattr(node, 'parent') and isinstance(node.parent, ast.Attribute):
            return
        if isinstance(node.ctx, ast.Load):
            self.usages.append(VariableUsage(
                variable_name=node.id,
                usage_type=UsageType.READ,
                line_number=node.lineno,
                component_name=self.current_class,
                method_name=self.current_method
            ))

    def visit_Return(self, node: ast.Return):
        if isinstance(node.value, (ast.Name, ast.Attribute)):
            var_name = (
                node.value.id if isinstance(node.value, ast.Name)
                else self.get_full_name(node.value)
            )
            self.usages.append(VariableUsage(
                variable_name=var_name,
                usage_type=UsageType.RETURN,
                line_number=node.lineno,
                component_name=self.current_class,
                method_name=self.current_method
            ))

    def generic_visit(self, node: ast.AST):
        # Set parent pointers so that in visit_Name and visit_Attribute we know the chain.
        for child in ast.iter_child_nodes(node):
            child.parent = node
            self.visit(child)

def variable_analyzer(code: str) -> Dict:
    tree = ast.parse(code)
    analyzer = VariableAnalyzer()
    analyzer.visit(tree)
    
    return {
        'variables': [asdict(v) for v in analyzer.variables],
        'usages': [asdict(u) for u in analyzer.usages],
        'flows': [asdict(f) for f in analyzer.flows]
    }

def analyze_variable(file_location: str):
    with open(file_location, "r") as f:
        sample_code = f.read()
        result = variable_analyzer(sample_code)
        return result
    
if __name__ == "__main__":
    file_location = "project_sample/library_management_python/Controllers/UserManager.py"
    analyzed_variable = analyze_variable(file_location)
    print(analyzed_variable)

    variables=analyzed_variable["variables"]
    print(len(variables))
