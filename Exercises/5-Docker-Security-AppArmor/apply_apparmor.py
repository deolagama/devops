"""Start the flask-apparmor image with the AppArmor profile using the Docker SDK for Python."""
import docker

IMAGE = "flask-apparmor"
NAME = "flask-secure-sdk"
PROFILE = "my-apparmor-profile"
HOST_PORT = 5002  # 5000 is used by macOS AirPlay Receiver, 5001 by the CLI container

client = docker.from_env()

# Remove a container left over from a previous run
try:
    client.containers.get(NAME).remove(force=True)
except docker.errors.NotFound:
    pass

container = client.containers.run(
    IMAGE,
    name=NAME,
    detach=True,
    security_opt=[f"apparmor={PROFILE}"],
    ports={"5000/tcp": HOST_PORT},
)
container.reload()

print(f"Container {container.name} started with security_opt: {container.attrs['HostConfig']['SecurityOpt']}")
print(f"AppArmor profile reported by Docker: {container.attrs['AppArmorProfile']}")
