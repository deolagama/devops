
import docker

client = docker.from_env()

container = None

try:
    # Start container with the AppArmor security option
    container = client.containers.run(
        "flask-apparmor",
        security_opt=["apparmor=my-apparmor-profile"],
        detach=True
    )

    print(f"Container started: {container.short_id}")

    # Commands to test
    restricted_commands = [
        ["cat", "/etc/passwd"],
        ["/bin/bash", "-c", "echo 'Shell access successful'"],
        ["sh", "-c", "touch /restricted_test_file"]
    ]

    # Execute and inspect each command
    for command in restricted_commands:
        print(f"\nTesting command: {' '.join(command)}")

        result = container.exec_run(command)

        print(f"Exit code: {result.exit_code}")
        print(f"Output: {result.output.decode('utf-8', errors='replace')}")

        if result.exit_code == 0:
            print("Result: Command executed successfully")
        else:
            print("Result: Command was blocked or failed")

    # Inspect configured security options
    container_info = client.api.inspect_container(container.id)
    security_options = container_info["HostConfig"]["SecurityOpt"]

    print("\nConfigured security options:")
    print(security_options)

finally:
    # Stop and remove temporary container
    if container is not None:
        container.remove(force=True)
        print("\nTest container cleaned up.")
