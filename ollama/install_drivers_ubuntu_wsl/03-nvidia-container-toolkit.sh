#!/usr/bin/env bash
# Installation et configuration du NVIDIA Container Toolkit sur Debian 13 (Docker normal)
# Ref: https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html
set -euo pipefail

KEYRING="/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg"
SOURCES_LIST="/etc/apt/sources.list.d/nvidia-container-toolkit.list"

# ── élévation root ─────────────────────────────────────────────────────────
if [[ $EUID -ne 0 ]]; then
    echo "[erreur] Ce script doit être exécuté en tant que root."
    echo "         Lancez : su - -c 'bash $(realpath "$0")'"
    exit 1
fi

# ── idempotence : toolkit déjà installé et configuré ? ────────────────────
if dpkg -l nvidia-container-toolkit &>/dev/null; then
    if docker info 2>/dev/null | grep -q "nvidia"; then
        echo "[ok] NVIDIA Container Toolkit déjà installé et Docker déjà configuré — rien à faire."
        exit 0
    fi
    echo "[*] Toolkit installé mais Docker non configuré — configuration en cours..."
    nvidia-ctk runtime configure --runtime=docker
    systemctl restart docker
    echo "[ok] Docker configuré avec le runtime Nvidia."
    exit 0
fi

echo "[*] Installation du NVIDIA Container Toolkit..."

# ── dépendances ───────────────────────────────────────────────────────────
apt-get update
apt-get install -y --no-install-recommends ca-certificates curl gnupg2

# ── clé GPG ───────────────────────────────────────────────────────────────
if [[ ! -f "${KEYRING}" ]]; then
    curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey \
        | gpg --dearmor -o "${KEYRING}"
fi

# ── dépôt apt ─────────────────────────────────────────────────────────────
if [[ ! -f "${SOURCES_LIST}" ]]; then
    curl -sL https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list \
        | sed "s#deb https://#deb [signed-by=${KEYRING}] https://#g" \
        | tee "${SOURCES_LIST}"
fi

apt-get update

# ── installation ──────────────────────────────────────────────────────────
apt-get install -y nvidia-container-toolkit

# ── configuration du runtime Docker ──────────────────────────────────────
nvidia-ctk runtime configure --runtime=docker
systemctl restart docker

# ── vérification ──────────────────────────────────────────────────────────
echo "[*] Vérification du runtime Nvidia dans Docker..."
docker info | grep -i nvidia || echo "[warn] Runtime Nvidia non visible dans docker info — vérifier manuellement."

echo "[ok] NVIDIA Container Toolkit installé et Docker configuré."
echo "     Testez avec : docker run --rm --gpus all nvidia/cuda:12.0.0-base-ubuntu20.04 nvidia-smi"
exit 0

## REM on protected environment wsl:
# curl -k + dépôt nvidia .list "deb [trusted=yes]"
# on ubuntu: add "default-runtime": "nvidia" dans /etc/docker/daemon.json
# + reboot of the VM
# else:
# /sbin/ldconfig.real: Can't link /usr/lib/wsl/lib/libnvoptix_loader.so.1 to libnvoptix.so.1
# /sbin/ldconfig.real: /usr/lib/wsl/lib/libcuda.so.1 is not a symbolic link
# 