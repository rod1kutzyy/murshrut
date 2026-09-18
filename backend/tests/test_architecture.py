import ast
from importlib.util import resolve_name
from pathlib import Path

APP = Path(__file__).resolve().parents[1] / 'app'


def imported_modules(path):
    package = '.'.join(('app', *path.relative_to(APP).parts[:-1]))
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Import):
            yield from (alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            name = '.' * node.level + (node.module or '')
            yield resolve_name(name, package) if node.level else name


def test_layer_dependencies():
    for path in APP.rglob('*.py'):
        layer = path.relative_to(APP).parts[0]
        forbidden = ()
        if layer == 'service':
            forbidden = ('app.transport', 'app.repository', 'app.bootstrap', 'app.main', 'app.config',
                         'fastapi', 'sqlalchemy', 'httpx', 'jwt', 'pydantic', 'pydantic_settings')
        elif layer == 'repository':
            forbidden = ('app.transport', 'app.bootstrap', 'app.main', 'fastapi')
        elif layer == 'transport':
            forbidden = ('app.repository', 'app.bootstrap', 'app.main', 'sqlalchemy')
        for name in imported_modules(path):
            assert not any(name == prefix or name.startswith(prefix + '.') for prefix in forbidden), (path, name)


def test_commits_are_owned_by_unit_of_work():
    for path in (APP / 'repository').glob('*.py'):
        if path.name == 'unit_of_work.py':
            continue
        for node in ast.walk(ast.parse(path.read_text())):
            assert not (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                        and node.func.attr in {'commit', 'rollback'}), path


def test_legacy_modules_are_removed():
    assert not any((APP / name).exists() for name in ('models.py', 'db.py', 'schemas.py', 'services'))
