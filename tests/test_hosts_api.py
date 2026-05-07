from fastapi.testclient import TestClient

from app.main import app


def _create_profile(client: TestClient, name: str = "support-default") -> dict:
    response = client.post(
        "/api/ssh-profiles",
        json={"name": name, "username": "support", "auth_type": "agent", "sudo_mode": "none"},
    )
    assert response.status_code == 200
    return response.json()


def _create_host(client: TestClient, name: str = "app01", profile_id: int | None = None) -> dict:
    payload = {"name": name, "hostname": f"{name}.example.local", "tags": ["nginx", "prod"]}
    if profile_id is not None:
        payload["ssh_profile_id"] = profile_id
    response = client.post("/api/hosts", json=payload)
    assert response.status_code == 200
    return response.json()


def test_create_list_get_patch_delete_host():
    with TestClient(app) as client:
        profile = _create_profile(client, "host-crud-profile")
        host = _create_host(client, "host-crud-app01", profile["id"])

        list_response = client.get("/api/hosts")
        assert list_response.status_code == 200
        assert any(item["id"] == host["id"] for item in list_response.json()["items"])

        detail_response = client.get(f"/api/hosts/{host['id']}")
        assert detail_response.status_code == 200
        assert detail_response.json()["hostname"] == "host-crud-app01.example.local"

        patch_response = client.patch(f"/api/hosts/{host['id']}", json={"notes": "frontend reverse proxy", "tags": ["prod"]})
        assert patch_response.status_code == 200
        assert patch_response.json()["notes"] == "frontend reverse proxy"
        assert patch_response.json()["tags"] == ["prod"]

        delete_response = client.delete(f"/api/hosts/{host['id']}")
        assert delete_response.status_code == 200
        assert delete_response.json() == {"status": "deleted", "id": host["id"]}


def test_invalid_hostname_rejected():
    with TestClient(app) as client:
        response = client.post("/api/hosts", json={"name": "bad", "hostname": "app01;whoami"})
    assert response.status_code == 422


def test_invalid_port_rejected():
    with TestClient(app) as client:
        response = client.post("/api/hosts", json={"name": "bad-port", "hostname": "app01", "port": 70000})
    assert response.status_code == 422


def test_host_secret_extra_fields_rejected():
    with TestClient(app) as client:
        for field in ["password", "private_key", "token"]:
            response = client.post("/api/hosts", json={"name": "bad-secret", "hostname": "app01", field: "secret"})
            assert response.status_code == 422


def test_create_list_patch_delete_ssh_profile():
    with TestClient(app) as client:
        profile = _create_profile(client, "profile-crud")

        list_response = client.get("/api/ssh-profiles")
        assert list_response.status_code == 200
        assert any(item["id"] == profile["id"] for item in list_response.json()["items"])

        detail_response = client.get(f"/api/ssh-profiles/{profile['id']}")
        assert detail_response.status_code == 200
        assert detail_response.json()["auth_type"] == "agent"

        patch_response = client.patch(f"/api/ssh-profiles/{profile['id']}", json={"sudo_mode": "prompt"})
        assert patch_response.status_code == 200
        assert patch_response.json()["sudo_mode"] == "prompt"

        delete_response = client.delete(f"/api/ssh-profiles/{profile['id']}")
        assert delete_response.status_code == 200
        assert delete_response.json() == {"status": "deleted", "id": profile["id"]}


def test_invalid_auth_type_rejected():
    with TestClient(app) as client:
        response = client.post("/api/ssh-profiles", json={"name": "bad-auth", "username": "support", "auth_type": "oauth"})
    assert response.status_code == 422


def test_invalid_sudo_mode_rejected():
    with TestClient(app) as client:
        response = client.post(
            "/api/ssh-profiles",
            json={"name": "bad-sudo", "username": "support", "auth_type": "agent", "sudo_mode": "root"},
        )
    assert response.status_code == 422


def test_ssh_profile_secret_extra_field_rejected():
    with TestClient(app) as client:
        response = client.post(
            "/api/ssh-profiles",
            json={"name": "bad-secret", "username": "support", "auth_type": "agent", "password": "secret"},
        )
    assert response.status_code == 422


def test_delete_referenced_ssh_profile_returns_409():
    with TestClient(app) as client:
        profile = _create_profile(client, "referenced-profile")
        host = _create_host(client, "referenced-host", profile["id"])

        delete_response = client.delete(f"/api/ssh-profiles/{profile['id']}")
        assert delete_response.status_code == 409

        client.delete(f"/api/hosts/{host['id']}")


def test_safe_ssh_profile_refs_accepted():
    safe_refs = ["support-default", "ssh-agent", "keys/support-default", "vault-ref/support-default"]
    with TestClient(app) as client:
        for index, ref in enumerate(safe_refs):
            response = client.post(
                "/api/ssh-profiles",
                json={
                    "name": f"safe-ref-{index}",
                    "username": "support",
                    "auth_type": "key",
                    "key_ref": ref,
                    "password_ref": ref,
                    "sudo_mode": "none",
                },
            )
            assert response.status_code == 200
            assert response.json()["key_ref"] == ref
            assert response.json()["password_ref"] == ref


def test_pem_like_key_ref_rejected():
    with TestClient(app) as client:
        response = client.post(
            "/api/ssh-profiles",
            json={
                "name": "pem-ref",
                "username": "support",
                "auth_type": "key",
                "key_ref": "-----BEGIN OPENSSH PRIVATE KEY-----",
                "sudo_mode": "none",
            },
        )
    assert response.status_code == 422


def test_token_like_password_ref_rejected():
    token_like = "actualSecretWithVeryLongBlob" * 4
    with TestClient(app) as client:
        response = client.post(
            "/api/ssh-profiles",
            json={
                "name": "secret-ref",
                "username": "support",
                "auth_type": "password",
                "password_ref": token_like,
                "sudo_mode": "none",
            },
        )
    assert response.status_code == 422
