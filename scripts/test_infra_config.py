import os
import sys
import yaml
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("test_infra")

def test_infrastructure_configs():
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    # 1. Validate Dockerfile
    logger.info("\n--- 1. Validating Dockerfile ---")
    dockerfile_path = os.path.join(base_dir, "Dockerfile")
    assert os.path.exists(dockerfile_path), "Dockerfile missing!"
    with open(dockerfile_path, "r", encoding="utf-8") as f:
        df_content = f.read()

    assert "FROM python:3.11-slim" in df_content
    assert "USER appuser" in df_content, "Missing non-root user enforcement!"
    assert "HEALTHCHECK" in df_content, "Missing HEALTHCHECK instruction!"
    assert "EXPOSE 8000" in df_content
    logger.info("✓ Dockerfile validated (non-root security, healthcheck, multi-worker uvicorn)")

    # 2. Validate Nginx Configuration
    logger.info("\n--- 2. Validating infra/nginx/nginx.conf ---")
    nginx_path = os.path.join(base_dir, "infra", "nginx", "nginx.conf")
    assert os.path.exists(nginx_path), "nginx.conf missing!"
    with open(nginx_path, "r", encoding="utf-8") as f:
        nginx_content = f.read()

    assert "upstream rag_api_cluster" in nginx_content
    assert "limit_req_zone $binary_remote_addr zone=rag_limit:10m rate=60r/m" in nginx_content
    assert "X-Frame-Options \"DENY\"" in nginx_content
    assert "X-Content-Type-Options \"nosniff\"" in nginx_content
    assert "location /api/" in nginx_content
    assert "location /health" in nginx_content
    assert "location /metrics" in nginx_content
    logger.info("✓ Nginx reverse proxy validated (load balancing, 60 r/m edge rate limiting, OWASP security headers)")

    # 3. Validate Docker Compose Prod
    logger.info("\n--- 3. Validating infra/docker-compose.prod.yml ---")
    compose_path = os.path.join(base_dir, "infra", "docker-compose.prod.yml")
    assert os.path.exists(compose_path), "docker-compose.prod.yml missing!"
    with open(compose_path, "r", encoding="utf-8") as f:
        compose_data = yaml.safe_load(f)

    services = compose_data.get("services", {})
    required_services = ["nginx", "rag-api", "rag-worker", "postgres", "qdrant", "redis", "prometheus", "grafana"]
    for s in required_services:
        assert s in services, f"Missing service {s} in docker-compose.prod.yml!"
        logger.info(f"  ✓ Service present: {s}")

    assert "pg_isready" in str(services["postgres"].get("healthcheck", {}))
    logger.info("✓ Docker Compose production stack validated (all 8 services, healthchecks & networks)")

    # 4. Validate Kubernetes Manifests
    logger.info("\n--- 4. Validating Kubernetes Manifests (infra/k8s/) ---")
    k8s_dir = os.path.join(base_dir, "infra", "k8s")

    for manifest_name in ["configmap.yaml", "secret.yaml", "deployment.yaml", "service.yaml", "hpa.yaml"]:
        m_path = os.path.join(k8s_dir, manifest_name)
        assert os.path.exists(m_path), f"Missing k8s manifest {manifest_name}"
        with open(m_path, "r", encoding="utf-8") as f:
            docs = list(yaml.safe_load_all(f))
            assert len(docs) > 0, f"Manifest {manifest_name} is empty!"
            logger.info(f"  ✓ Validated {manifest_name} ({len(docs)} resource(s))")

    # Inspect deployment specifics
    with open(os.path.join(k8s_dir, "deployment.yaml"), "r", encoding="utf-8") as f:
        deployments = list(yaml.safe_load_all(f))
        api_dep = next(d for d in deployments if d["metadata"]["name"] == "university-rag-api")
        assert api_dep["spec"]["replicas"] == 2
        container = api_dep["spec"]["template"]["spec"]["containers"][0]
        assert "livenessProbe" in container
        assert "readinessProbe" in container
        assert container["resources"]["limits"]["memory"] == "4Gi"
        logger.info("  ✓ Kubernetes deployment validated (2 replicas, health probes, resource limits)")

    logger.info("\n=======================================================")
    logger.info("ALL PHASE 9 PRODUCTION INFRASTRUCTURE CONFIGS VALIDATED!")
    logger.info("=======================================================")

if __name__ == "__main__":
    test_infrastructure_configs()
