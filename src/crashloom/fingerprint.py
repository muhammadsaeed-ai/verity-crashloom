import ast
import hashlib
import textwrap

class _ASTCanonicalizer(ast.NodeTransformer):
    def visit_Constant(self, node: ast.Constant) -> ast.AST:
        return ast.Name(id=f"CONST_{type(node.value).__name__}", ctx=ast.Load())

def extract_ast_statement_info(source_line: str) -> tuple[str, str]:
    cleaned = textwrap.dedent(source_line).strip()
    if not cleaned:
        return "Empty", "Empty"
    try:
        tree = ast.parse(cleaned)
        if tree.body:
            stmt = tree.body[0]
            return type(stmt).__name__, ast.dump(_ASTCanonicalizer().visit(stmt))
    except SyntaxError:
        pass
    return "UnparsedStatement", cleaned

def compute_crash_fingerprint(exception_type: str, module_name: str, qualname: str, ast_canonical_expr: str) -> str:
    payload = "|".join([exception_type, module_name, qualname, ast_canonical_expr])
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
