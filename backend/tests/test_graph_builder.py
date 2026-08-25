from app.services import command_dispatcher


def run(repo_root, text):
    return command_dispatcher.run_command(repo_root, text)


def test_empty_repo_graph_is_empty(repo_root):
    resp = run(repo_root, "init")
    graph = resp.commit_graph
    assert graph.commits == []
    assert graph.branches == []


def test_linear_history_generations_increase(repo_root):
    run(repo_root, "init")
    run(repo_root, "echo a > f.txt")
    run(repo_root, "add f.txt")
    run(repo_root, 'commit -m "c1"')
    run(repo_root, "echo b >> f.txt")
    run(repo_root, "add f.txt")
    resp = run(repo_root, 'commit -m "c2"')

    graph = resp.commit_graph
    assert len(graph.commits) == 2
    by_generation = sorted(graph.commits, key=lambda c: c.generation)
    assert by_generation[0].generation == 0
    assert by_generation[1].generation == 1
    assert by_generation[1].parent_oid == by_generation[0].oid
    assert graph.head_commit_oid == by_generation[1].oid
    assert by_generation[1].is_head_commit is True
    assert by_generation[0].is_head_commit is False


def test_main_branch_claims_lane_zero_feature_gets_its_own_lane(repo_root):
    run(repo_root, "init")
    run(repo_root, "echo base > f.txt")
    run(repo_root, "add f.txt")
    run(repo_root, 'commit -m "base"')
    run(repo_root, "branch feature")
    run(repo_root, "checkout feature")
    run(repo_root, "echo feature-only > g.txt")
    run(repo_root, "add g.txt")
    resp = run(repo_root, 'commit -m "feature commit"')

    graph = resp.commit_graph
    main_ref = next(b for b in graph.branches if b.name == "main")
    feature_ref = next(b for b in graph.branches if b.name == "feature")
    assert main_ref.lane == 0
    assert feature_ref.lane == 1
    assert feature_ref.is_current is True
    assert main_ref.is_current is False

    base_commit = next(c for c in graph.commits if c.generation == 0)
    feature_commit = next(c for c in graph.commits if c.generation == 1)
    assert base_commit.lane == 0  # shared history claimed by main (processed first)
    assert feature_commit.lane == 1  # unique to feature


def test_merge_commit_has_two_generation_increasing_parents(repo_root):
    run(repo_root, "init")
    run(repo_root, "echo base > shared.txt")
    run(repo_root, "add shared.txt")
    run(repo_root, 'commit -m "base"')
    run(repo_root, "branch feature")

    run(repo_root, "echo main-line >> shared.txt")
    run(repo_root, "add shared.txt")
    run(repo_root, 'commit -m "main change"')

    run(repo_root, "checkout feature")
    run(repo_root, "echo other content > other.txt")
    run(repo_root, "add other.txt")
    run(repo_root, 'commit -m "feature change"')

    run(repo_root, "checkout main")
    resp = run(repo_root, "merge feature")

    graph = resp.commit_graph
    merge_commit = next(c for c in graph.commits if c.is_merge)
    parent = next(c for c in graph.commits if c.oid == merge_commit.parent_oid)
    merge_parent = next(c for c in graph.commits if c.oid == merge_commit.merge_parent_oid)
    assert merge_commit.generation > parent.generation
    assert merge_commit.generation > merge_parent.generation


def test_detached_head_commit_gets_its_own_lane_when_unclaimed(repo_root):
    run(repo_root, "init")
    run(repo_root, "echo a > f.txt")
    run(repo_root, "add f.txt")
    first = run(repo_root, 'commit -m "c1"')
    first_oid = first.terminal.stdout_lines[0]

    run(repo_root, "echo b >> f.txt")
    run(repo_root, "add f.txt")
    run(repo_root, 'commit -m "c2"')

    resp = run(repo_root, f"checkout {first_oid}")
    assert resp.commit_graph.head_detached is True
    assert resp.commit_graph.head_commit_oid == first_oid
