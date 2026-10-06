# Exercise 5 – Docker Security with AppArmor and Python

## Objective

Containerize a Flask application, write an AppArmor profile that restricts file access and binary execution, apply the profile to the container using the Docker CLI and the Docker SDK for Python, and test whether the restrictions are enforced.

## Environment

| Item              | Value                                              |
|-------------------|----------------------------------------------------|
| OS                | macOS (Darwin 12.7.6)                              |
| Shell             | VS Code integrated terminal (bash)                 |
| Container Runtime | Docker Desktop for Mac                             |
| Language          | Python 3.8 (container image `python:3.8-slim`), Flask |
| Tools             | Docker CLI, Docker SDK for Python (`pip3 install docker`) |

> **Important:** AppArmor is a Linux kernel feature. macOS has no AppArmor, and the Linux VM that Docker Desktop runs containers in does not enable it either. The profile can therefore be built, attached to the container and recorded by Docker, but it **cannot be enforced** on a Mac. See [Observations and Limitations](#6-observations-and-limitations) and the optional Multipass section for a way to see real enforcement.

## Project Structure

```
05-Docker-Security-AppArmor/
├── README.md
├── app.py
├── Dockerfile
├── my-apparmor-profile
├── apply_apparmor.py
├── test_restricted_actions.py
├── requirements.txt
└── images/
    ├── 01-project-files.png
    ├── 02-apparmor-not-available.png
    ├── 03-build-image.png
    ├── 04-run-container.png
    └── 05-sdk-apply-and-test.png
```

---

## 1. Project Files

The exercise folder contains the application, the Dockerfile, the AppArmor profile, and the two Python scripts:

```bash
ls -la
```

- `app.py` – Flask app returning a greeting on port 5000
- `Dockerfile` – builds the image from `python:3.8-slim`
- `my-apparmor-profile` – the AppArmor profile
- `apply_apparmor.py` – starts the container with the profile using the Docker SDK
- `test_restricted_actions.py` – tries restricted actions inside the container
- `requirements.txt` – the Docker SDK for Python (`docker`)

![Project Files](images/01-project-files.png)

---

## 2. AppArmor Profile

The profile `my-apparmor-profile`:

- allows IPv4 TCP networking and the `net_bind_service` capability for Flask on port 5000
- denies the `sys_admin` capability
- allows Python and its libraries to run, and read/write access to `/app`
- denies access to `/etc/passwd`, `/etc/shadow`, writes to `/etc`, and all access to `/var`
- denies execution of binaries in `/bin`, `/usr/bin` and `/sbin`

The profile in the lab sheet was adjusted in two ways:

- The profile is named `my-apparmor-profile` (instead of `/usr/bin/python3`) so that Docker can find it with `--security-opt apparmor=my-apparmor-profile`.
- Rules allowing Python's own files were added, and the `/etc` rule was narrowed, so the container can still start.

---

## 3. Load the Profile and Build the Image

On Linux the profile would be loaded with:

```bash
sudo cp my-apparmor-profile /etc/apparmor.d/my-apparmor-profile
sudo apparmor_parser -r /etc/apparmor.d/my-apparmor-profile
sudo aa-status | grep my-apparmor-profile
```

On macOS these tools do not exist, and Docker Desktop's VM does not list AppArmor among its security options:

```bash
apparmor_parser -r my-apparmor-profile
aa-status
docker info --format '{{.SecurityOptions}}'
```

![AppArmor Not Available on macOS](images/02-apparmor-not-available.png)

`docker info` lists only `seccomp` and `cgroupns` – there is no `name=apparmor`. The profile file is still part of the project and is used by the next steps.

Build the image (Docker Desktop must be running):

```bash
docker build -t flask-apparmor .
docker images flask-apparmor
```

The image `flask-apparmor` is built from `python:3.8-slim` with Flask installed. The final build steps copy `app.py`, expose port 5000 and set the container command to `python app.py`.

![Build Image](images/03-build-image.png)

---

## 4. Run the Container with the Profile

```bash
docker run -d --name flask-secure --security-opt apparmor=my-apparmor-profile -p 5001:5000 flask-apparmor
sleep 3
curl -s localhost:5001
docker inspect flask-secure --format '{{.AppArmorProfile}}'
docker ps
```

> **Why port 5001?** On macOS Monterey and later, the **AirPlay Receiver** service already listens on port 5000, so `-p 5000:5000` fails or answers with `403 Forbidden`. The container still listens on 5000 internally; only the host port is different. (Alternatively turn off *System Settings → General → AirDrop & Handoff → AirPlay Receiver*.)

The container starts and the application responds with:

```
Hello, this is a secure Flask application running inside a Docker container!
```

`docker inspect` reports the profile `my-apparmor-profile`.

![Run Secure Flask Container](images/04-run-container.png)

---

## 5. Apply the Profile and Test Restrictions with the Docker SDK

Install the Docker SDK for Python and run the two scripts:

```bash
pip3 install -r requirements.txt
python3 apply_apparmor.py
python3 test_restricted_actions.py
```

`apply_apparmor.py` starts a second container (`flask-secure-sdk`, host port 5002) with `security_opt=["apparmor=my-apparmor-profile"]` and prints the applied option. `test_restricted_actions.py` then tries two restricted actions inside that container:

| Action            | Expected | Observed (Docker Desktop on macOS)   |
|-------------------|----------|--------------------------------------|
| `cat /etc/passwd` | Blocked  | Succeeded, user entries were printed |
| `/bin/bash`       | Blocked  | Exit code 0                          |

![SDK Apply and Test Restrictions](images/05-sdk-apply-and-test.png)

> If `docker.from_env()` fails with *Error while fetching server API version*, Docker Desktop is not exposing the default socket. Either enable *Settings → Advanced → Allow the default Docker socket to be used*, or run `export DOCKER_HOST=unix://$HOME/.docker/run/docker.sock` before the scripts.

---

## 6. Observations and Limitations

The profile was attached to the container (visible in `docker inspect`), but the restricted actions were **not blocked** on this Mac.

`docker info --format '{{.SecurityOptions}}'` listed only `seccomp` and `cgroupns` and not `apparmor`. Containers on Docker Desktop for Mac run inside a lightweight Linux VM whose kernel does not have AppArmor enabled, so the profile was recorded in the container settings but not enforced. In addition, `apparmor_parser` is not available on macOS, so the profile could not be loaded into any kernel.

To see the restrictions enforced, the same files should be run on a native Linux host or a Linux VM (for example Ubuntu on Multipass or VirtualBox), where Docker reports `name=apparmor` and `cat /etc/passwd` and `/bin/bash` fail with "Permission denied" (exit code 126).

### Optional: see enforcement with Multipass (Ubuntu VM on the Mac)

These commands are not part of the screenshots above; run them if you want to demonstrate real enforcement.

```bash
brew install --cask multipass
multipass launch 22.04 --name apparmor-lab --cpus 2 --memory 2G --disk 10G
multipass transfer -r . apparmor-lab:/home/ubuntu/lab
multipass shell apparmor-lab
```

Inside the VM:

```bash
sudo apt update && sudo apt install -y docker.io apparmor-utils python3-pip
sudo usermod -aG docker ubuntu && newgrp docker
pip3 install docker

cd ~/lab
sudo cp my-apparmor-profile /etc/apparmor.d/my-apparmor-profile
sudo apparmor_parser -r /etc/apparmor.d/my-apparmor-profile
sudo aa-status | grep my-apparmor-profile
docker info --format '{{.SecurityOptions}}'     # should now include name=apparmor

docker build -t flask-apparmor .
python3 apply_apparmor.py
python3 test_restricted_actions.py              # both actions should now be BLOCKED
```

---

## 7. Answers to the Questions

**What is the purpose of using AppArmor with Docker containers?**
AppArmor enforces security policies that confine an application to a limited set of files, network access and capabilities, adding a layer of protection beyond container isolation.

**How do AppArmor profiles help secure a Docker container?**
A profile defines what the containerized process may read, write, execute and which capabilities it may use, so a compromised application cannot freely affect the container or the host.

**Why is it important to restrict access to sensitive directories such as `/etc/` and `/var/`?**
They hold system configuration, user information and logs. Restricting them prevents the container from reading or modifying files that could be used to escalate an attack.

**What other capabilities can you restrict using AppArmor profiles?**
Network access and socket types, specific Linux capabilities (such as `sys_admin`), file read/write/execute permissions, mounting, signals and ptrace.

**How can you verify if an AppArmor profile is successfully applied to a Docker container?**
Check `docker inspect` (`HostConfig.SecurityOpt` and `AppArmorProfile`) and `aa-status`. To confirm it is actually enforced, also check that `docker info` lists `name=apparmor` and that restricted actions inside the container fail.

---

## 8. Commands Used

```bash
ls -la

apparmor_parser -r my-apparmor-profile
aa-status
docker info --format '{{.SecurityOptions}}'

docker build -t flask-apparmor .
docker images flask-apparmor

docker run -d --name flask-secure --security-opt apparmor=my-apparmor-profile -p 5001:5000 flask-apparmor
sleep 3
curl -s localhost:5001
docker inspect flask-secure --format '{{.AppArmorProfile}}'
docker ps

pip3 install -r requirements.txt
python3 apply_apparmor.py
python3 test_restricted_actions.py
```

### Cleanup

```bash
docker rm -f flask-secure flask-secure-sdk
docker rmi flask-apparmor
```

---

## 9. Result

The Flask application was containerized, an AppArmor profile was written, and the container was run with the profile using both the Docker CLI and the Docker SDK for Python. On macOS with Docker Desktop, AppArmor is not available, so the profile was recorded but not enforced and the test actions were not blocked. The profile and test scripts are ready to be re-run on a Linux host with AppArmor support to demonstrate enforcement.
