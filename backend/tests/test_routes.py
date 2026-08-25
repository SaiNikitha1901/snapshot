def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_command_endpoint_round_trip(client):
    resp = client.post("/api/command", json={"input": "init"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["repository_status"]["initialized"] is True
    assert body["animation"]["command"] == "init"
    assert body["learn"]["cards"][0]["trigger"] == "repository_initialized"


def test_repo_status_and_graph_endpoints_reflect_command_state(client):
    client.post("/api/command", json={"input": "init"})
    client.post("/api/command", json={"input": "echo hi > a.txt"})
    client.post("/api/command", json={"input": "add a.txt"})
    commit_resp = client.post("/api/command", json={"input": 'commit -m "c1"'})
    commit_oid = commit_resp.json()["terminal"]["stdout_lines"][0]

    status = client.get("/api/repo/status").json()
    assert status["current_commit_oid"] == commit_oid

    graph = client.get("/api/repo/graph").json()
    assert len(graph["commits"]) == 1
    assert graph["commits"][0]["oid"] == commit_oid

    head = client.get("/api/repo/head").json()
    assert head["kind"] == "head"
    assert head["commit_oid"] == commit_oid


def test_repo_reflog_endpoint_reflects_head_movements(client):
    client.post("/api/command", json={"input": "init"})
    client.post("/api/command", json={"input": "echo hi > a.txt"})
    client.post("/api/command", json={"input": "add a.txt"})
    commit_resp = client.post("/api/command", json={"input": 'commit -m "c1"'})
    commit_oid = commit_resp.json()["terminal"]["stdout_lines"][0]

    reflog = client.get("/api/repo/reflog").json()
    assert len(reflog["entries"]) == 1
    entry = reflog["entries"][0]
    assert entry["new_oid"] == commit_oid
    assert entry["short_new_oid"] == commit_oid[:7]
    assert entry["old_oid"] is None
    assert entry["is_reachable"] is True
    assert entry["message"] == "commit (initial): c1"


def test_repo_head_404_before_init(client):
    resp = client.get("/api/repo/head")
    assert resp.status_code == 404


def test_get_object_by_oid(client):
    client.post("/api/command", json={"input": "init"})
    client.post("/api/command", json={"input": "echo hi > a.txt"})
    add_resp = client.post("/api/command", json={"input": "add a.txt"})
    blob_oid = add_resp.json()["focused_object"]["oid"]

    obj = client.get(f"/api/objects/{blob_oid}").json()
    assert obj["kind"] == "blob"
    assert obj["content"] == "hi\n"


def test_get_object_404_for_unknown_oid(client):
    client.post("/api/command", json={"input": "init"})
    resp = client.get(f"/api/objects/{'0' * 40}")
    assert resp.status_code == 404


def test_get_object_graph_for_a_commit(client):
    client.post("/api/command", json={"input": "init"})
    client.post("/api/command", json={"input": "echo hi > a.txt"})
    client.post("/api/command", json={"input": "add a.txt"})
    commit_resp = client.post("/api/command", json={"input": 'commit -m "c1"'})
    commit_oid = commit_resp.json()["terminal"]["stdout_lines"][0]

    graph = client.get(f"/api/objects/{commit_oid}/graph").json()

    assert graph["root_oid"] == commit_oid
    kinds = sorted(n["kind"] for n in graph["nodes"])
    assert kinds == ["blob", "commit", "tree"]
    assert len(graph["edges"]) == 2


def test_get_object_graph_404_for_unknown_oid(client):
    client.post("/api/command", json={"input": "init"})
    resp = client.get(f"/api/objects/{'0' * 40}/graph")
    assert resp.status_code == 404


def test_files_read_and_write_round_trip(client):
    client.post("/api/command", json={"input": "init"})

    empty = client.get("/api/files/read", params={"path": "notes.md"}).json()
    assert empty == {"path": "notes.md", "content": "", "exists": False}

    write_resp = client.post("/api/files/write", json={"path": "notes.md", "content": "hello world\n"})
    assert write_resp.status_code == 200
    body = write_resp.json()
    assert body["command"]["name"] == "edit"
    assert "notes.md" in body["repository_status"]["untracked_paths"]

    read_back = client.get("/api/files/read", params={"path": "notes.md"}).json()
    assert read_back == {"path": "notes.md", "content": "hello world\n", "exists": True}


def test_files_write_is_sandboxed(client):
    client.post("/api/command", json={"input": "init"})
    resp = client.post("/api/files/write", json={"path": "../escape.txt", "content": "x"})
    assert resp.status_code == 400


def test_learn_generate_falls_back_without_api_key(client):
    resp = client.post(
        "/api/learn/generate",
        json={"context": {"trigger": "repository_initialized", "command_name": "init"}},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["source"] == "template"
    assert body["card"]["trigger"] == "repository_initialized"


def test_unknown_command_does_not_500(client):
    resp = client.post("/api/command", json={"input": "definitely-not-a-real-command"})
    assert resp.status_code == 200
    assert resp.json()["terminal"]["exit_code"] == 127
