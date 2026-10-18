# Skill: Build and Run Docker Images

Build, run, and troubleshoot Glances Docker images locally.

## Instructions

### Build images
```bash
make docker                    # Build all images (Alpine + Ubuntu, full + minimal)
make docker-alpine-full        # Alpine full image
make docker-alpine-minimal     # Alpine minimal image
make docker-ubuntu-full        # Ubuntu full image
make docker-ubuntu-minimal     # Ubuntu minimal image
```

Requires Docker Buildx (`apt install docker-buildx` on Ubuntu).

### Run containers
```bash
make run-docker-alpine-full    # Run Alpine full in console mode
make run-docker-ubuntu-full    # Run Ubuntu full in console mode
```

Default run options: `--rm --pid host --network host` with Docker/Podman socket mounts.

### Security scan
```bash
make trivy-docker              # Run Trivy on all local images
```

### Dockerfiles
Located in `docker-files/`:
- `alpine.Dockerfile` — multi-stage: `minimal` and `full` targets
- `ubuntu.Dockerfile` — multi-stage: `minimal` and `full` targets

### Key considerations
- Prefer `SYS_PTRACE` capability over `privileged: true`
- Mount Docker socket read-only: `-v /var/run/docker.sock:/var/run/docker.sock:ro`
- For Kubernetes: use DaemonSet (one pod per node) for system monitoring
- The images run Glances v5 (`python -m glances ${GLANCES_OPT}`); in server mode (`-w`) bind to `0.0.0.0` (`bind_address` in `docker-compose/glances.conf`, or `-B 0.0.0.0`), v5 defaults to loopback
- CI builds Docker images on `develop` (the `dev` image) and on tags only (see `.github/workflows/build_docker.yml`); a pre-release tag (`v5.0.0b1`, `rc`) never moves `latest`

### Troubleshooting
- **Socket permission errors**: Ensure the user is in the `docker` group or use Podman
- **Multi-arch builds**: CI uses QEMU for cross-platform (ARM64) — local builds are native only by default
- **Build timeouts**: Multi-arch builds can take 20-40 min; CI timeout is 60 min
