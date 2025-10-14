import json
import os
import sys
import typer
from rich import print
from typing import Optional
from .generator import (
    set_templates_dir,
    list_templates,
    load_template_schema,
    generate_from_template,
    use_template_repo,
    data_dir_path,
)

app = typer.Typer(help="CLI Python para gerar boilerplates (Kubernetes/Terraform).")

@app.command("use-repo")
def use_repo(
    repo: str = typer.Option(..., "--repo", help="URL Git (SSH/HTTPS) contendo /templates"),
    ref: str = typer.Option("main", "--ref", help="branch/tag/commit")
):
    tpl_dir = use_template_repo(repo, ref)
    print(f"✔️ Templates disponíveis em: [bold]{tpl_dir}[/]")
    # salvar config padrão
    cfg_path = data_dir_path() / "config.json"
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    cfg_path.write_text(json.dumps({"defaultRepo": repo, "ref": ref}, indent=2), encoding="utf-8")
    print(f"🧭 Config salvo em: [dim]{cfg_path}[/]")

@app.command("templates")
def templates(
    type: str = typer.Option(..., "--type", help="k8s|terraform"),
    templates: Optional[str] = typer.Option(None, "--templates", help="Override do diretório de templates"),
):
    if templates:
        set_templates_dir(templates)
    items = list_templates(type)
    if not items:
        print("⚠️ Nenhum template encontrado. Rode [bold]infra use-repo[/] ou defina --templates.")
        raise typer.Exit(1)
    print(f"Templates de {type}:")
    for t in items:
        print(f" - {t}")

@app.command("new")
def new(
    type: str = typer.Option(..., "--type", help="k8s|terraform"),
    template: Optional[str] = typer.Option(None, "--template", help="nome do template"),
    name: Optional[str] = typer.Option(None, "--name", help="nome do serviço/projeto"),
    outdir: str = typer.Option("./out", "--outdir", help="diretório de saída"),
    vars: Optional[str] = typer.Option(None, "--vars", help="JSON com variáveis"),
    templates: Optional[str] = typer.Option(None, "--templates", help="Override do diretório de templates")
):
    if templates:
        set_templates_dir(templates)

    items = list_templates(type)
    if not items:
        print("⚠️ Nenhum template encontrado. Rode [bold]infra use-repo[/] ou defina --templates.")
        raise typer.Exit(1)

    if not template:
        print("Escolha um template com --template. Disponíveis:")
        for t in items: print(f" - {t}")
        raise typer.Exit(2)

    schema = load_template_schema(type, template)
    answers = {}
    if schema and schema.get("questions"):
        # prompts simples com Typer (Click) - sem dependência extra
        for q in schema["questions"]:
            qtype = q.get("type", "input")
            qname = q["name"]
            msg = q.get("message", qname)
            default = q.get("default")
            if qtype == "password":
                value = typer.prompt(msg, default=default, hide_input=True)
            else:
                value = typer.prompt(msg, default=default)
            answers[qname] = value

    if vars:
        try:
            answers.update(json.loads(vars))
        except Exception as e:
            print(f"[red]✖ JSON inválido em --vars:[/] {e}")
            raise typer.Exit(3)

    if name:
        answers["name"] = name
    if "name" not in answers:
        answers["name"] = typer.prompt("Nome do serviço/projeto")

    generate_from_template(type=type, template=template, variables=answers, outdir=outdir)
    print(f"✔️ Gerado com sucesso em: [bold]{os.path.join(outdir, type, answers['name'])}[/]")
