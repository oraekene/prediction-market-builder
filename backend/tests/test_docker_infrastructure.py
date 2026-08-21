import os
import pytest

BACKEND = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
PROJECT = os.path.normpath(os.path.join(BACKEND, ".."))
INFRA = os.path.join(PROJECT, "infrastructure")


def test_dockerfile_exists():
    path = os.path.join(BACKEND, "Dockerfile")
    assert os.path.exists(path), "backend/Dockerfile is required"
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


def test_env_example_exists():
    path = os.path.join(PROJECT, ".env.example")
    assert os.path.exists(path), ".env.example is required at repo root"
    with open(path) as f:
        content = f.read()
    assert "SECRET_KEY" in content
    assert "ENCRYPTION_KEY" in content
    assert "POSTGRES_PASSWORD" in content


def test_docker_compose_exists():
    for name in ("docker-compose.yml", "docker-compose.yaml"):
        path = os.path.join(INFRA, name)
        if os.path.exists(path):
            with open(path) as f:
                content = f.read()
            assert "backend" in content
            assert "frontend" in content
            return
    pytest.fail("docker-compose.yml not found in infrastructure/")


def test_frontend_package_json():
    fe_dir = os.path.join(PROJECT, "frontend")
    assert os.path.exists(fe_dir)
    assert os.path.exists(os.path.join(fe_dir, "package.json"))


def test_frontend_dockerfile_exists():
    path = os.path.join(PROJECT, "frontend", "Dockerfile")
    assert os.path.exists(path)
    with open(path) as f:
        content = f.read()
    assert "nginx" in content  # production two-stage build


def test_app_init():
    assert os.path.exists(os.path.join(BACKEND, "app", "__init__.py"))
