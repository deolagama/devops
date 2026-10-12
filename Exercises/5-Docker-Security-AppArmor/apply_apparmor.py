import docker

client = docker.from_env()

client.images.build(path=".", tag="flask-apparmor")

container = client.containers.run(
    "flask-apparmor",
    security_opt=["apparmor=my-apparmor-profile"],
    detach=True
)

print(f"Container started: {container.short_id}")

container_info = client.api.inspect_container(container.id)
apparmor_profile = container_info['HostConfig']['SecurityOpt']

print(f"AppArmor profile applied: {apparmor_profile}")

container.stop()
container.remove()