# Snapshot

> **Watch Git Think.**

Snapshot is an educational version control system built from scratch to help users understand Git internals.

Instead of treating Git as a black box, Snapshot exposes the core data structures and workflows behind a version control system by implementing them from first principles.

The goal is not to replace Git, but to build an accurate mental model of how Git works under the hood.

---
## Motivation

Git is one of the most widely used developer tools, yet many users learn it by memorizing commands without understanding what happens internally.

Snapshot bridges this gap by implementing Git's core object model from scratch while intentionally keeping the implementation simple enough to inspect, explore, and understand.
---

## Features

### Object Storage

- Content-addressable object storage
- SHA-1 object identification
- Blob objects
- Tree objects

### Repository Management

- Repository initialization
- Staging area (Index)
- Working directory tracking
- Object serialization

### Commit System

- Snapshot-based commits
- Commit history traversal
- Parent commit relationships
- Immutable commit graph

### Branching

- Branch creation
- Branch switching
- Symbolic HEAD
- Detached HEAD
- Safe checkout

### Merge

- Fast-forward merge
- Three-way merge
- Merge commits with multiple parents
- Merge base discovery
- Merge conflict detection
- Conflict markers

### Testing

- Comprehensive unit test suite covering all implemented features

---


## Architecture

```
Working Directory
        │
        ▼
   Staging Area (Index)
        │
        ▼
      Blob Objects
        │
        ▼
      Tree Objects
        │
        ▼
     Commit Objects
        │
        ▼
 Branch References
        │
        ▼
       HEAD
```

Snapshot stores every object using content-addressable storage. Commits reference trees, trees reference blobs and subtrees, and branches simply point to commits. The complete repository history is maintained through commit metadata.

---

## Educational Philosophy

Snapshot focuses on understanding Git's core concepts rather than reproducing every production feature.

The implementation prioritizes:

- Conceptual accuracy
- Simplicity
- Inspectable data structures
- Clear repository state transitions

Whenever Snapshot intentionally simplifies production Git behaviour, the educational interface planned for future releases will explain the difference and the reasoning behind it.

---

## Intentional Simplifications

Snapshot currently does not implement:

- Remote repositories
- Networking
- Packfiles
- Delta compression
- Garbage collection
- Rebase
- Cherry-pick
- Hooks
- Tags
- Sparse checkout
- Worktrees

These omissions are intentional. They allow the project to focus on Git's object model and repository mechanics without introducing production optimizations that are not essential for understanding the underlying concepts.

---

## Project Structure
```
src/
└── snapshot/
    ├── blob.py
    ├── tree.py
    ├── commit.py
    ├── index.py
    ├── refs.py
    ├── checkout.py
    ├── merge.py
    ├── objects.py
    ├── repository.py
    └── cli.py

tests/
└── Unit tests for each core module
```


---

## Running the Project

Initialize a repository

```bash
snapshot init
```

Stage files

```bash
snapshot add .
```

Create a commit

```bash
snapshot commit -m "Initial commit"
```

Create a branch

```bash
snapshot branch feature
```

Switch branches

```bash
snapshot checkout feature
```

Merge branches

```bash
snapshot merge feature
```

#### These commands demonstrate the typical Snapshot workflow. Additional commands such as object inspection and history traversal are available through the CLI help.
---

## Running Tests

```bash
pytest -v
```

---

## Roadmap

### Engine

- [x] Content-addressable object storage
- [x] Blob objects
- [x] Tree objects
- [x] Commit objects
- [x] Branches
- [x] Checkout
- [x] Merge
- [x] Merge conflict detection

### Snapshot Studio

- [ ] Interactive terminal
- [ ] Commit graph visualization
- [ ] Object animations
- [ ] Repository status
- [ ] Object inspector
- [ ] Guided learning interface

---

## License

This project is intended for educational purposes.