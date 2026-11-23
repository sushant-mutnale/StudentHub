import os
import shutil
import socket
import subprocess
import tempfile
import time

_CONTAINER = "studenthub-mongo-rs"
_PORT = 27018


def _uri(port):
    return f"mongodb://127.0.0.1:{port}/?directConnection=true"


def _port_open(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.2)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def _run(args, timeout=180):
    return subprocess.run(args, capture_output=True, text=True, timeout=timeout)


def _accepting_connections(uri, deadline):
    from pymongo import MongoClient

    client = MongoClient(uri, serverSelectionTimeoutMS=1000, connectTimeoutMS=1000)
    while time.time() < deadline:
        try:
            client.admin.command("ping")
            return client
        except Exception:
            time.sleep(0.5)
    client.close()
    return None


def _initiate_replica_set(client, port, deadline):
    last_error = None
    while time.time() < deadline:
        try:
            client.admin.command(
                "replSetInitiate",
                {"_id": "rs0", "members": [{"_id": 0, "host": f"127.0.0.1:{port}"}]},
            )
            return None
        except Exception as exc:
            if "already initialized" in str(exc):
                return None
            last_error = exc
            time.sleep(0.5)
    return last_error


def _await_primary(client, deadline):
    while time.time() < deadline:
        try:
            if client.admin.command("hello").get("isWritablePrimary"):
                return True
        except Exception:
            pass
        time.sleep(0.5)
    return False


def _start_local_mongod(port, uri, deadline):
    mongod = shutil.which("mongod")
    if not mongod:
        return None
    dbpath = tempfile.mkdtemp(prefix="interview-engine-rs-")
    subprocess.Popen(
        [mongod, "--replSet", "rs0", "--dbpath", dbpath, "--port", str(port),
         "--bind_ip", "127.0.0.1"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return _accepting_connections(uri, deadline)


def _start_docker_container(port):
    if not shutil.which("docker"):
        raise RuntimeError("docker not found")
    inspect = _run(["docker", "inspect", _CONTAINER], timeout=60)
    if inspect.returncode == 0:
        running = _run(
            ["docker", "inspect", "-f", "{{.State.Running}}", _CONTAINER], timeout=60
        ).stdout.strip()
        if running != "true":
            started = _run(["docker", "start", _CONTAINER], timeout=120)
            if started.returncode != 0:
                raise RuntimeError(f"docker start failed: {started.stderr.strip()}")
    else:
        created = _run(
            ["docker", "run", "-d", "--name", _CONTAINER, "-p", f"{port}:{port}",
             "mongo:7", "--replSet", "rs0", "--bind_ip_all", "--port", str(port)],
            timeout=300,
        )
        if created.returncode != 0:
            raise RuntimeError(f"docker run failed: {created.stderr.strip()}")
    return _uri(port)


def start_replica_set(port=_PORT):
    configured = os.environ.get("MONGODB_REPLICA_URI")
    if configured:
        return configured
    uri = _uri(port)
    deadline = time.time() + 120

    if _port_open(port):
        client = _accepting_connections(uri, time.time() + 10)
        if client is None:
            raise RuntimeError(f"a server is listening on {port} but does not speak MongoDB")
    else:
        client = _start_local_mongod(port, uri, deadline)
        if client is None:
            uri = _start_docker_container(port)
            client = _accepting_connections(uri, deadline)
        if client is None:
            raise RuntimeError("replica set did not accept connections")

    try:
        error = _initiate_replica_set(client, port, deadline)
        if error is not None:
            raise RuntimeError(f"replSetInitiate failed: {error}")
        if not _await_primary(client, deadline):
            raise RuntimeError("replica set did not elect a primary")
    finally:
        client.close()
    return uri
