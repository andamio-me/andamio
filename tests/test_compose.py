"""La plantilla del compose de una app (ansible/templates/app-compose.yaml.j2): varias apps en un
repo tienen cada una su imagen, y una con path: comparte el host de otra en esa ruta."""
from __future__ import annotations

import json
from pathlib import Path

import jinja2
import yaml

TEMPLATE = Path(__file__).resolve().parent.parent / "ansible/templates/app-compose.yaml.j2"
BASE = {"name": "web", "repo": "Yo/Proyecto", "host": "web", "port": 3000, "access": "public",
        "resources": {"mem": "256m", "cpus": 0.5, "pids": 200}}


def render(**app) -> dict:
    env = jinja2.Environment(keep_trailing_newline=True, trim_blocks=True, lstrip_blocks=True)
    env.filters["to_json"] = json.dumps
    out = env.from_string(TEMPLATE.read_text()).render(app={**BASE, **app}, andamio_github_owner="yo", andamio_registry="ghcr.io")
    return yaml.safe_load(out)


def labels(c: dict) -> list[str]:
    return c["services"]["app"]["labels"]


def test_one_app_per_repo_keeps_its_image_and_rule():
    c = render()
    assert c["services"]["app"]["image"].startswith("ghcr.io/yo/proyecto:")
    assert "traefik.http.routers.web.rule=Host(`web.${DOMAIN}`)" in labels(c)


def test_an_app_in_a_folder_has_its_own_image():
    c = render(name="web-api", dir="backend")
    assert c["services"]["app"]["image"].startswith("ghcr.io/yo/web-api:")


def test_a_path_shares_the_host_under_its_own_router():
    c = render(name="web-api", dir="backend", path="/api")
    assert "traefik.http.routers.web-api.rule=Host(`web.${DOMAIN}`) && PathPrefix(`/api`)" in labels(c)
    apex = render(name="web-api", dir="backend", path="/api", host="@")
    assert "traefik.http.routers.web-api.rule=(Host(`${DOMAIN}`) || Host(`www.${DOMAIN}`)) && PathPrefix(`/api`)" in labels(apex)
    own = render(name="web-api", dir="backend", path="/api", domains=["a.com", "b.com"])
    assert "traefik.http.routers.web-api-own.rule=(Host(`a.com`) || Host(`b.com`)) && PathPrefix(`/api`)" in labels(own)


def test_apex_without_path_keeps_the_same_rule_text():
    """Sin path, el texto de la regla no cambia: un cambio recrearía el contenedor."""
    c = render(host="@", domains=["a.com"])
    assert "traefik.http.routers.web.rule=Host(`${DOMAIN}`) || Host(`www.${DOMAIN}`)" in labels(c)
    assert "traefik.http.routers.web-own.rule=Host(`a.com`)" in labels(c)
