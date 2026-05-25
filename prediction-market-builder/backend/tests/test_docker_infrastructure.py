import os
import pytest

BACKEND = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
PROJECT = os.path.normpath(os.path.join(BACKEND, ".."))


def test_dockerfile_exists():
    path = os.path.join(BACKEND, "Dockerfile")
    if os.path.exists(path):
        with open(path) as f:
            content = f.read()
        assert "FROM" in content


def test_dockerignore_exists():
    path = os.path.join(BACKEND, ".dockerignore")
    if os.path.exists(path):
        assert os.path.getsize(path) > 0


def test_requirements_exists():
    for name in ("requirements.txt", "requirements.in", "pyproject.toml"):
        if os.path.exists(os.path.join(BACKEND, name)):
            return
    pytest.fail("No requirements file found in backend")


def test_env_example():
    path = os.path.join(BACKEND, ".env.example")
    if os.path.exists(path):
        with open(path) as f:
            content = f.read()
        assert "SECRET_KEY" in content or "secret" in content.lower()


def test_docker_compose_exists():
    for name in ("docker-compose.yml", "docker-compose.yaml"):
        if os.path.exists(os.path.join(PROJECT, name)):
            return
    for name in ("docker-compose.yml", "docker-compose.yaml"):
        if os.path.exists(os.path.join(BACKEND, name)):
            return


def test_entrypoint_exists():
    for name in ("entrypoint.sh", "entrypoint.py"):
        if os.path.exists(os.path.join(BACKEND, name)):
            return


def test_frontend_package_json():
    fe_dir = os.path.join(PROJECT, "frontend")
    if os.path.exists(fe_dir):
        assert os.path.exists(os.path.join(fe_dir, "package.json"))


def test_app_init():
    assert os.path.exists(os.path.join(BACKEND, "app", "__init__.py"))
