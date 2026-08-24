#!/usr/bin/env bash
# Installation de Docker Engine sur Ubuntu2404 via apt-get
# Ref: https://docs.docker.com/engine/install/ubuntu/
set -euo pipefail

TARGET_USER="dmin_stagiaire"

# ── élévation root ─────────────────────────────────────────────────────────
if [[ $EUID -ne 0 ]]; then
    echo "[erreur] Ce script doit être exécuté en tant que root."
    echo "         Lancez : su - -c 'bash $(realpath "$0")'"
    exit 1
fi

# ── idempotence : Docker déjà installé ? ───────────────────────────────────
if command -v docker &>/dev/null && docker version &>/dev/null; then
    echo "[ok] Docker déjà installé ($(docker version --format '{{.Server.Version}}')) — rien à faire."
    # s'assurer que l'utilisateur est dans le groupe docker
    if ! id -nG "${TARGET_USER}" | grep -qw docker; then
        usermod -aG docker "${TARGET_USER}"
        echo "[ok] ${TARGET_USER} ajouté au groupe docker."
    fi
    exit 0
fi

echo "[*] Installation de Docker Engine..."

# ── suppression des éventuels paquets conflictuels ────────────────────────
CONFLICT_PKGS="docker.io docker-compose docker-doc podman-docker containerd runc"
for pkg in ${CONFLICT_PKGS}; do
    if dpkg -l "${pkg}" &>/dev/null; then
        apt-get remove -y "${pkg}"
    fi
done

# ── dépendances ───────────────────────────────────────────────────────────
apt-get update
apt-get install -y ca-certificates curl

# ── clé GPG Docker ────────────────────────────────────────────────────────
install -m 0755 -d /etc/apt/keyrings
if [[ ! -f /etc/apt/keyrings/docker.asc ]]; then
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
        -o /etc/apt/keyrings/docker.asc
    chmod a+r /etc/apt/keyrings/docker.asc
fi

# ── dépôt Docker ──────────────────────────────────────────────────────────
if [[ ! -f /etc/apt/sources.list.d/docker.sources ]]; then
    CODENAME=$(. /etc/os-release && echo "${VERSION_CODENAME}")
    ARCH=$(dpkg --print-architecture)
    cat > /etc/apt/sources.list.d/docker.sources <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: ${CODENAME}
Components: stable
Architectures: ${ARCH}
Signed-By: /etc/apt/keyrings/docker.asc
EOF
fi

apt-get update

# ── installation ──────────────────────────────────────────────────────────
apt-get install -y \
    docker-ce \
    docker-ce-cli \
    containerd.io \
    docker-buildx-plugin \
    docker-compose-plugin

# ── post-install : groupe docker ──────────────────────────────────────────
if id "${TARGET_USER}" &>/dev/null; then
    usermod -aG docker "${TARGET_USER}"
    echo "[ok] ${TARGET_USER} ajouté au groupe docker."
fi

# ── vérification ──────────────────────────────────────────────────────────
systemctl enable --now docker
docker version

echo "[ok] Docker installé avec succès. Reconnectez-vous pour que les droits groupe soient actifs."
exit 0
