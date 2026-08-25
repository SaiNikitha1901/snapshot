import pytest

from app.services import command_dispatcher, object_graph_builder


def run(repo_root, text):
    return command_dispatcher.run_command(repo_root, text)


def _snapshot_dir(repo_root):
    return repo_root / ".snapshot"


def _objects_dir(repo_root):
    return repo_root / ".snapshot" / "objects"


def test_single_file_commit_produces_commit_tree_blob(repo_root):
    run(repo_root, "init")
    run(repo_root, "echo hello > a.txt")
    run(repo_root, "add a.txt")
    commit_resp = run(repo_root, 'commit -m "c1"')
    commit_oid = commit_resp.terminal.stdout_lines[0]

    graph = object_graph_builder.build_object_graph(_snapshot_dir(repo_root), _objects_dir(repo_root), commit_oid)

    assert graph.root_oid == commit_oid
    kinds = sorted(n.kind for n in graph.nodes)
    assert kinds == ["blob", "commit", "tree"]
    assert len(graph.edges) == 2

    commit_node = next(n for n in graph.nodes if n.kind == "commit")
    tree_node = next(n for n in graph.nodes if n.kind == "tree")
    blob_node = next(n for n in graph.nodes if n.kind == "blob")
    assert commit_node.depth == 0
    assert tree_node.depth == 1
    assert blob_node.depth == 2
    assert commit_node.is_head_commit is True
    assert blob_node.label == "6 bytes"  # "hello\n"

    tree_to_blob_edge = next(e for e in graph.edges if e.source == tree_node.oid)
    assert tree_to_blob_edge.target == blob_node.oid
    assert tree_to_blob_edge.label == "a.txt"

    commit_to_tree_edge = next(e for e in graph.edges if e.source == commit_node.oid)
    assert commit_to_tree_edge.target == tree_node.oid
    assert commit_to_tree_edge.label == "tree"


def test_nested_directory_adds_a_depth_level(repo_root):
    run(repo_root, "init")
    run(repo_root, "mkdir src")
    run(repo_root, "echo nested > src/util.py")
    run(repo_root, "add src/util.py")
    commit_resp = run(repo_root, 'commit -m "c1"')
    commit_oid = commit_resp.terminal.stdout_lines[0]

    graph = object_graph_builder.build_object_graph(_snapshot_dir(repo_root), _objects_dir(repo_root), commit_oid)

    kinds = sorted(n.kind for n in graph.nodes)
    assert kinds == ["blob", "commit", "tree", "tree"]
    depths = sorted(n.depth for n in graph.nodes)
    assert depths == [0, 1, 2, 3]


def test_identical_content_deduplicates_to_one_blob_node(repo_root):
    run(repo_root, "init")
    run(repo_root, "echo same-content > a.txt")
    run(repo_root, "echo same-content > b.txt")
    run(repo_root, "add a.txt")
    run(repo_root, "add b.txt")
    commit_resp = run(repo_root, 'commit -m "dedup"')
    commit_oid = commit_resp.terminal.stdout_lines[0]

    graph = object_graph_builder.build_object_graph(_snapshot_dir(repo_root), _objects_dir(repo_root), commit_oid)

    blob_nodes = [n for n in graph.nodes if n.kind == "blob"]
    assert len(blob_nodes) == 1  # content-addressed: identical content is ONE object

    blob_oid = blob_nodes[0].oid
    incoming = [e for e in graph.edges if e.target == blob_oid]
    assert len(incoming) == 2
    assert sorted(e.label for e in incoming) == ["a.txt", "b.txt"]

    # exactly one commit + one tree + one (shared) blob
    assert len(graph.nodes) == 3


def test_unknown_root_oid_raises_file_not_found(repo_root):
    run(repo_root, "init")

    with pytest.raises(FileNotFoundError):
        object_graph_builder.build_object_graph(_snapshot_dir(repo_root), _objects_dir(repo_root), "0" * 40)


def test_tree_as_root_is_supported(repo_root):
    run(repo_root, "init")
    run(repo_root, "echo hello > a.txt")
    run(repo_root, "add a.txt")
    commit_resp = run(repo_root, 'commit -m "c1"')
    commit_detail = commit_resp.focused_object
    tree_oid = commit_detail.tree_oid

    graph = object_graph_builder.build_object_graph(_snapshot_dir(repo_root), _objects_dir(repo_root), tree_oid)

    assert graph.root_oid == tree_oid
    kinds = sorted(n.kind for n in graph.nodes)
    assert kinds == ["blob", "tree"]
    root_node = next(n for n in graph.nodes if n.oid == tree_oid)
    assert root_node.depth == 0
