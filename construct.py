import ast
import json
import subprocess
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class CodeNode:
    """A single addressable unit in the codebase (module, class, function)."""
    node_id: str                  # Unique: "owlapy/utils.py::get_dnf"
    kind: str                     # "module" | "class" | "function" | "async_function"
    name: str
    qualified_name: str           # "owlapy.utils.get_dnf"
    file_path: str                # Repo-relative, e.g. "owlapy/utils.py"
    start_line: int
    end_line: int
    commit_hash: str
    github_url: str               # Permalink with line anchor
    code: str                     # Full source text of this node
    docstring: Optional[str]
    decorators: list[str]         # e.g. ["@staticmethod", "@property"]
    parent_id: Optional[str]      # Enclosing class node_id (None for top-level)
    bases: list[str]              # Superclass names (for classes)
    return_annotation: Optional[str]
    arg_annotations: dict[str, str]


@dataclass
class CodeEdge:
    """A directed relationship between two nodes."""
    source_id: str
    target_id: str                # May be unresolved (external) string
    kind: str                     # "contains" | "inherits" | "calls" | "imports"
    metadata: dict = field(default_factory=dict)


@dataclass
class CodeGraph:
    """
    The complete structured representation of a repository.

    Internally this is an adjacency structure:
      nodes : dict[node_id -> CodeNode]
      edges : list[CodeEdge]

    That is sufficient to serialise to JSON, feed into NetworkX,
    or load into a graph DB such as Neo4j.
    """
    repo_name: str
    commit_hash: str
    nodes: dict[str, CodeNode] = field(default_factory=dict)
    edges: list[CodeEdge] = field(default_factory=list)

    # ---- helpers --------------------------------------------------------

    def add_node(self, node: CodeNode) -> None:
        self.nodes[node.node_id] = node

    def add_edge(self, edge: CodeEdge) -> None:
        self.edges.append(edge)

    def children_of(self, node_id: str) -> list[CodeNode]:
        return [
            self.nodes[e.target_id]
            for e in self.edges
            if e.source_id == node_id and e.kind == "contains"
            and e.target_id in self.nodes
        ]

    def to_dict(self) -> dict:
        return {
            "repo_name": self.repo_name,
            "commit_hash": self.commit_hash,
            "nodes": {k: asdict(v) for k, v in self.nodes.items()},
            "edges": [asdict(e) for e in self.edges],
        }

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")
        print(f"Graph saved → {path}  ({len(self.nodes)} nodes, {len(self.edges)} edges)")

    @classmethod
    def load(cls, path: Path) -> "CodeGraph":
        raw = json.loads(path.read_text(encoding="utf-8"))
        g = cls(repo_name=raw["repo_name"], commit_hash=raw["commit_hash"])
        for k, v in raw["nodes"].items():
            g.nodes[k] = CodeNode(**v)
        for e in raw["edges"]:
            g.edges.append(CodeEdge(**e))
        return g


# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------

GITHUB_BASE = "https://github.com/dice-group/owlapy"

def get_git_commit(repo_path: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_path, capture_output=True, text=True, check=True,
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Warning: could not read git HEAD — using 'main'.")
        return "main"


def make_github_url(rel_path: str, commit: str, start: int, end: int) -> str:
    return f"{GITHUB_BASE}/blob/{commit}/{rel_path}#L{start}-L{end}"


# ---------------------------------------------------------------------------
# AST visitor — builds nodes and intra-file edges
# ---------------------------------------------------------------------------

class GraphVisitor(ast.NodeVisitor):
    """
    Single-pass AST walk over one Python file.

    Produces:
      - One CodeNode  per module / class / function
      - "contains"   edges  (class → method, module → top-level def)
      - "inherits"   edges  (class → base class, by name)
      - "calls"      edges  (function → called names, best-effort)
    """

    def __init__(
        self,
        rel_path: str,
        source_lines: list[str],
        commit_hash: str,
        graph: CodeGraph,
    ):
        self.rel_path = rel_path
        self.source_lines = source_lines
        self.commit = commit_hash
        self.graph = graph

        # Stack of (node_id, qualified_prefix) for the current scope
        self._scope: list[tuple[str, str]] = []

        # Module-level node is created up front
        module_qname = rel_path.replace("/", ".").removesuffix(".py")
        module_id = f"{rel_path}::__module__"
        module_node = CodeNode(
            node_id=module_id,
            kind="module",
            name=module_qname.split(".")[-1],
            qualified_name=module_qname,
            file_path=rel_path,
            start_line=1,
            end_line=len(source_lines),
            commit_hash=commit_hash,
            github_url=make_github_url(rel_path, commit_hash, 1, len(source_lines)),
            code="",          # Too large; keep empty; full source is in repo
            docstring=None,
            decorators=[],
            parent_id=None,
            bases=[],
            return_annotation=None,
            arg_annotations={},
        )
        self.graph.add_node(module_node)
        self._scope.append((module_id, module_qname))

    # ---- scope helpers --------------------------------------------------

    def _current_parent_id(self) -> str:
        return self._scope[-1][0]

    def _current_qprefix(self) -> str:
        return self._scope[-1][1]

    def _node_id(self, name: str) -> str:
        return f"{self.rel_path}::{self._current_qprefix()}.{name}"

    def _qualified(self, name: str) -> str:
        return f"{self._current_qprefix()}.{name}"

    # ---- shared recorder ------------------------------------------------

    def _record(self, node: ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef, kind: str) -> str:
        start = node.lineno
        end = getattr(node, "end_lineno", start)
        code_snippet = "".join(self.source_lines[start - 1 : end]).strip()
        docstring = ast.get_docstring(node)

        decorators = [ast.unparse(d) for d in node.decorator_list]

        # Return annotation (functions only)
        ret_ann = None
        arg_anns: dict[str, str] = {}
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.returns:
                ret_ann = ast.unparse(node.returns)
            for arg in node.args.args + node.args.posonlyargs + node.args.kwonlyargs:
                if arg.annotation:
                    arg_anns[arg.arg] = ast.unparse(arg.annotation)

        # Base classes (classes only)
        bases: list[str] = []
        if isinstance(node, ast.ClassDef):
            bases = [ast.unparse(b) for b in node.bases]

        node_id = self._node_id(node.name)
        qname = self._qualified(node.name)
        parent_id = self._current_parent_id()

        code_node = CodeNode(
            node_id=node_id,
            kind=kind,
            name=node.name,
            qualified_name=qname,
            file_path=self.rel_path,
            start_line=start,
            end_line=end,
            commit_hash=self.commit,
            github_url=make_github_url(self.rel_path, self.commit, start, end),
            code=code_snippet,
            docstring=docstring,
            decorators=decorators,
            parent_id=parent_id,
            bases=bases,
            return_annotation=ret_ann,
            arg_annotations=arg_anns,
        )
        self.graph.add_node(code_node)

        # "contains" edge  parent → this node
        self.graph.add_edge(CodeEdge(
            source_id=parent_id,
            target_id=node_id,
            kind="contains",
        ))

        # "inherits" edges  (resolved later by CodeGraph.resolve_cross_file_edges)
        for base in bases:
            self.graph.add_edge(CodeEdge(
                source_id=node_id,
                target_id=base,          # unresolved name; resolved in post-pass
                kind="inherits",
                metadata={"unresolved": True},
            ))

        return node_id

    # ---- visitors -------------------------------------------------------

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        node_id = self._record(node, "class")
        self._scope.append((node_id, self._qualified(node.name)))
        self.generic_visit(node)
        self._scope.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        node_id = self._record(node, "function")
        # Walk body only for calls — do NOT recurse into nested defs
        # (inner functions would add noise; revisit if needed)
        self._collect_calls(node, node_id)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        node_id = self._record(node, "async_function")
        self._collect_calls(node, node_id)

    # ---- call-edge extraction -------------------------------------------

    def _collect_calls(
        self,
        func_node: ast.FunctionDef | ast.AsyncFunctionDef,
        caller_id: str,
    ) -> None:
        """Add 'calls' edges for every Name/Attribute call inside the function body."""
        for child in ast.walk(func_node):
            if not isinstance(child, ast.Call):
                continue
            callee_name = self._callee_name(child.func)
            if callee_name:
                self.graph.add_edge(CodeEdge(
                    source_id=caller_id,
                    target_id=callee_name,   # unresolved; post-pass can resolve
                    kind="calls",
                    metadata={"unresolved": True},
                ))

    @staticmethod
    def _callee_name(func_node: ast.expr) -> Optional[str]:
        if isinstance(func_node, ast.Name):
            return func_node.id
        if isinstance(func_node, ast.Attribute):
            return func_node.attr     # short name; full resolution needs type info
        return None


# ---------------------------------------------------------------------------
# Import-edge extraction (module level)
# ---------------------------------------------------------------------------

def extract_import_edges(
    tree: ast.Module,
    source_module_id: str,
    graph: CodeGraph,
) -> None:
    """Add 'imports' edges from the module node to imported names."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                graph.add_edge(CodeEdge(
                    source_id=source_module_id,
                    target_id=alias.name,
                    kind="imports",
                ))
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for alias in node.names:
                graph.add_edge(CodeEdge(
                    source_id=source_module_id,
                    target_id=f"{module}.{alias.name}",
                    kind="imports",
                ))


# ---------------------------------------------------------------------------
# Cross-file resolution pass
# ---------------------------------------------------------------------------

def resolve_edges(graph: CodeGraph) -> None:
    """
    Best-effort: replace unresolved string targets with actual node_ids.

    Strategy: build a lookup from (short name) and (qualified name)
    to node_id, then patch edges whose target matches.
    """
    # name → list of node_ids  (a name may exist in multiple files)
    by_name: dict[str, list[str]] = {}
    by_qname: dict[str, str] = {}

    for nid, node in graph.nodes.items():
        by_name.setdefault(node.name, []).append(nid)
        by_qname[node.qualified_name] = nid

    resolved = 0
    for edge in graph.edges:
        if not edge.metadata.get("unresolved"):
            continue
        target = edge.target_id
        if target in by_qname:
            edge.target_id = by_qname[target]
            edge.metadata["unresolved"] = False
            resolved += 1
        elif target in by_name and len(by_name[target]) == 1:
            edge.target_id = by_name[target][0]
            edge.metadata["unresolved"] = False
            resolved += 1

    ambiguous = sum(1 for e in graph.edges if e.metadata.get("unresolved"))
    print(f"  Edge resolution: {resolved} resolved, {ambiguous} still unresolved (ambiguous or external)")


# ---------------------------------------------------------------------------
# Top-level builder
# ---------------------------------------------------------------------------

SKIP_DIRS = {".git", ".tox", "venv", ".venv", "env", "__pycache__", "build", "dist", "node_modules"}
SKIP_DIR_PREFIXES = ("test",)


def should_skip(path: Path, repo_root: Path) -> bool:
    parts = path.relative_to(repo_root).parts
    for part in parts:
        if part in SKIP_DIRS:
            return True
        if any(part.lower().startswith(p) for p in SKIP_DIR_PREFIXES):
            return True
    return False


def build_code_graph(repo_dir: str, repo_name: str = "owlapy") -> CodeGraph:
    """
    Entry point.  Walk every .py file in *repo_dir* and return a populated CodeGraph.
    """
    repo_path = Path(repo_dir).resolve()
    commit = get_git_commit(repo_path)
    graph = CodeGraph(repo_name=repo_name, commit_hash=commit)

    py_files = [p for p in repo_path.rglob("*.py") if not should_skip(p, repo_path)]
    print(f"Parsing {len(py_files)} Python files from {repo_path.name}  (commit {commit[:8]})")

    parse_errors = 0
    for file_path in sorted(py_files):
        try:
            source = file_path.read_text(encoding="utf-8")
            source_lines = source.splitlines(keepends=True)
            tree = ast.parse(source, filename=str(file_path))
            rel_path = file_path.relative_to(repo_path).as_posix()

            visitor = GraphVisitor(rel_path, source_lines, commit, graph)
            visitor.visit(tree)

            # Import edges at module level
            module_id = f"{rel_path}::__module__"
            extract_import_edges(tree, module_id, graph)

        except SyntaxError as exc:
            print(f"  SyntaxError in {file_path.name}: {exc}")
            parse_errors += 1
        except Exception as exc:
            print(f"  Error in {file_path.name}: {exc}")
            parse_errors += 1

    print(f"  Parse errors: {parse_errors}")
    print(f"  Raw graph: {len(graph.nodes)} nodes, {len(graph.edges)} edges")

    resolve_edges(graph)
    return graph


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Build a code graph for owlapy.")
    parser.add_argument("repo_dir", help="Path to local owlapy clone")
    parser.add_argument("--out", default="owlapy_graph.json", help="Output JSON path")
    args = parser.parse_args()

    graph = build_code_graph(args.repo_dir)

    out_path = Path(args.out)
    graph.save(out_path)

    # Spot-check: print the first 3 function nodes
    funcs = [n for n in graph.nodes.values() if n.kind == "function"][:3]
    for f in funcs:
        print(f"\n--- {f.qualified_name} ---")
        print(f"  URL:        {f.github_url}")
        print(f"  Docstring:  {(f.docstring or '')[:80]}")
        print(f"  Returns:    {f.return_annotation}")
        outgoing = [e for e in graph.edges if e.source_id == f.node_id]
        print(f"  Edges out:  {[(e.kind, e.target_id[:40]) for e in outgoing[:4]]}")