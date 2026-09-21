"""Recursos compartilhados pelas rotas HTML."""

from pathlib import Path

from fastapi.templating import Jinja2Templates


TEMPLATES_DIR = Path(__file__).resolve().parents[1] / "templates"
templates = Jinja2Templates(directory=TEMPLATES_DIR)
