# infra-cli-py

CLI em **Python** para gerar boilerplates (Kubernetes, Terraform) a partir de **qualquer diretório**.

## Instalação (local)
```bash
pip install -e .
# ou
python -m pip install .
```

## Uso
```bash
# configurar repositório com /templates
infra use-repo --repo git@github.com:sua-org/boilerplates-infra.git --ref main

# listar templates
infra templates --type k8s

# gerar artefato
infra new --type k8s --template app-basic --name api-x --outdir ./scaffold --vars '{"image":"nginx:latest","port":8080}'
```

### Estrutura esperada do repositório de templates
```
templates/
  k8s/
    app-basic/
      deployment.yaml.j2
      service.yaml.j2
      template.json   # opcional (perguntas/defaults)
  terraform/
    aws-app/
      main.tf.j2
      variables.tf.j2
      outputs.tf.j2
      template.json
```
Arquivos com extensão `.j2` são renderizados via **Jinja2** e gravados **sem** a extensão.
Demais arquivos são copiados como estão. `template.json` (se presente) não é copiado.

### template.json (opcional)
```json
{
  "defaults": { "namespace": "default", "port": 8080 },
  "questions": [
    { "type": "input", "name": "image", "message": "Imagem:", "default": "nginx:latest" },
    { "type": "number", "name": "port", "message": "Porta:", "default": 8080 },
    { "type": "password", "name": "token", "message": "Token:" }
  ]
}
```
