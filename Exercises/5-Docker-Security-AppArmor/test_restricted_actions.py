"""Try restricted actions inside the container started by apply_apparmor.py."""
import docker

NAME = "flask-secure-sdk"

client = docker.from_env()
container = client.containers.get(NAME)

tests = [
    ("cat /etc/passwd", ["cat", "/etc/passwd"]),
    ("/bin/bash", ["/bin/bash", "-c", "echo bash executed"]),
]

for label, command in tests:
    result = container.exec_run(command)
    output = result.output.decode(errors="replace").strip().splitlines()
    verdict = "BLOCKED" if result.exit_code != 0 else "ALLOWED (not blocked)"
    print(f"[{label}] exit code: {result.exit_code} -> {verdict}")
    for line in output[:3]:
        print(f"    {line}")
    if len(output) > 3:
        print("    ...")
