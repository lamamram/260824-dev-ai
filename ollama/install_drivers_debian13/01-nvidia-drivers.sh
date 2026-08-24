#!/usr/bin/env bash
# Installation des drivers Nvidia propriétaires headless sur Debian 13
# Ref: https://docs.nvidia.com/datacenter/tesla/driver-installation-guide/debian.html
set -euo pipefail

REBOOT_FLAG="/var/run/nvidia-install-reboot-required"
KEYRING_PKG="cuda-keyring_1.1-1_all.deb"
KEYRING_URL="https://developer.download.nvidia.com/compute/cuda/repos/debian13/x86_64/${KEYRING_PKG}"

# ── idempotence : drivers déjà installés ? ─────────────────────────────────
if dpkg -l nvidia-driver-cuda &>/dev/null && dpkg -l nvidia-kernel-dkms &>/dev/null; then
    echo "[ok] Drivers Nvidia déjà installés — rien à faire."
    exit 0
fi

echo "[*] Installation des drivers Nvidia propriétaires headless..."

# ── élévation root ─────────────────────────────────────────────────────────
# Ce script doit être exécuté en tant que root (via su -)
if [[ $EUID -ne 0 ]]; then
    echo "[erreur] Ce script doit être exécuté en tant que root."
    echo "         Lancez : su - -c 'bash $(realpath "$0")'"
    exit 1
fi

# ── pré-requis ─────────────────────────────────────────────────────────────
apt-get install -y linux-headers-"$(uname -r)"

# activer le composant contrib s'il ne l'est pas déjà
if ! grep -qE '^[^#].*\bcontrib\b' /etc/apt/sources.list /etc/apt/sources.list.d/*.list 2>/dev/null; then
    sed -i 's/^\(deb .*\)\(main\)$/\1\2 contrib/' /etc/apt/sources.list
fi

# ── dépôt CUDA/Nvidia ──────────────────────────────────────────────────────
if ! dpkg -l cuda-keyring &>/dev/null; then
    TMP=$(mktemp -d)
    wget -qO "${TMP}/${KEYRING_PKG}" "${KEYRING_URL}"
    dpkg -i "${TMP}/${KEYRING_PKG}"
    rm -rf "${TMP}"
fi

apt-get update

# ── installation des drivers headless (compute-only) ──────────────────────
apt-get install -y nvidia-driver-cuda nvidia-kernel-dkms

# ── reboot requis ──────────────────────────────────────────────────────────
echo "[!] Installation terminée. Un redémarrage est nécessaire."
touch "${REBOOT_FLAG}"
echo "    Redémarrez la machine manuellement puis vérifiez avec : nvidia-smi"
exit 0
