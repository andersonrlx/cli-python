import json
import os
import re
import shutil
from pathlib import Path
from typing import Dict, List, Optional

from git import Repo, GitCommandError
from jinja2 import Environment, FileSystemLoader, StrictUndefined, TemplateError

def data_dir_path() -> Path:
    xdg = os.environ.get("XDG_DATA_HOME")
    return Path(xdg) / "infra-cli" if xdg else Path.home() / ".infra-cli"

DATA_DIR = data_dir_path()
TPL_DIR = DATA_DIR / "templates"

def set_templates_dir(dirpath: str):
    global TPL_DIR
    TPL_DIR = Path(dirpath).expanduser().resolve()

def get_templates_dir() -> Path:
    return TPL_DIR

def _sanitize_repo(url: str) -> str:
    return re.sub(r"[^\w.-]+", "_", url)

def use_template_repo(repo_url: str, ref: str = "main") -> Path:
    repos_dir = DATA_DIR / "repos"
    dest = repos_dir / _sanitize_repo(repo_url) / ref
    dest.mkdir(parents=True, exist_ok=True)
    try:
        if (dest / ".git").exists():
            repo = Repo(dest)
            repo.git.fetch("--all")
            repo.git.checkout(ref)
            repo.git.pull("origin", ref)
        else:
            Repo.clone_from(repo_url, dest, branch=ref, single_branch=True)
    except GitCommandError as e:
        raise RuntimeError(f"Falha ao preparar repositório de templates ({repo_url} @ {ref}): {e}")

    candidate = dest / "templates"
    if not candidate.exists():
        raise RuntimeError(f"Diretório 'templates' não encontrado no repositório ({repo_url} @ {ref}).")

    TPL_DIR.mkdir(parents=True, exist_ok=True)
    # copia preservando estrutura
    if TPL_DIR.exists():
        shutil.rmtree(TPL_DIR)
    shutil.copytree(candidate, TPL_DIR)
    return TPL_DIR

def list_templates(tpl_type: str) -> List[str]:
    base = TPL_DIR / tpl_type
    if not base.exists():
        return []
    return [p.name for p in base.iterdir() if p.is_dir()]

def load_template_schema(tpl_type: str, template: str) -> Optional[Dict]:
    schema_path = TPL_DIR / tpl_type / template / "template.json"
    if schema_path.exists():
        try:
            return json.loads(schema_path.read_text(encoding="utf-8"))
        except Exception as e:
            raise RuntimeError(f"template.json inválido em {tpl_type}/{template}: {e}")
    return None

def _walk(dirpath: Path) -> List[Path]:
    files = []
    for root, _, filenames in os.walk(dirpath):
        r = Path(root)
        for fn in filenames:
            files.append(r / fn)
    return files

def generate_from_template(*, type: str, template: str, variables: Dict, outdir: str):
    if "name" not in variables:
        raise RuntimeError('Variáveis devem incluir "name".')
    src = TPL_DIR / type / template
    if not src.exists():
        raise RuntimeError(f"Template não encontrado: {type}/{template} em {TPL_DIR}")

    target_base = Path(outdir).expanduser().resolve()
    target = target_base / type / variables["name"]
    target.mkdir(parents=True, exist_ok=True)

    env = Environment(
        loader=FileSystemLoader(str(src)),
        undefined=StrictUndefined,
        keep_trailing_newline=True,
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
    )

    for f in _walk(src):
        rel = f.relative_to(src)
        if rel.name == "template.json":
            continue
        out_path = (target / rel).with_suffix("") if rel.suffix == ".j2" else (target / rel)
        out_path.parent.mkdir(parents=True, exist_ok=True)

        if rel.suffix == ".j2":
            try:
                tpl = env.get_template(str(rel))
                rendered = tpl.render(**variables, env=os.environ)
            except TemplateError as e:
                raise RuntimeError(f"Erro ao renderizar {rel}: {e}")
            out_path.write_text(rendered, encoding="utf-8")
        else:
            shutil.copy2(f, out_path)
