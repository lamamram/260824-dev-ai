Dans PowerShell administrateur :

```powershell
wsl --install -d Ubuntu-24.04
wsl --update
wsl --set-default-version 2
```

Redémarrez si demandé, créez votre utilisateur Ubuntu, puis vérifiez :

```powershell
wsl -l -v
```

Dans Docker Desktop :

- Activez `Use the WSL 2 based engine`.
- Dans `Resources > WSL Integration`, activez `Ubuntu-24.04`.
- Si vous avez une NVIDIA, installez le pilote NVIDIA Windows compatible WSL, puis vérifiez dans Ubuntu :

```bash
nvidia-smi
docker run --rm --gpus all nvidia/cuda:12.6.3-base-ubuntu24.04 nvidia-smi
```

Ne réinstallez pas de pilote NVIDIA Linux dans Ubuntu WSL.

**Dimensionnement WSL**

Un modèle 27B est exigeant. Le besoin dépend fortement de la quantification, du contexte et du GPU.

| Ressource | Minimum réaliste | Recommandé |
|---|---:|---:|
| RAM machine | 32 Go | 64 Go |
| RAM WSL | 24 Go | 40-48 Go |
| VRAM GPU | 16 Go en quantifié | 24 Go ou plus |
| Stockage libre WSL | 60 Go | 120 Go |
| CPU attribués | 6 | 8-12 |
| Swap WSL | 8 Go | 12-16 Go |

Un 27B en $Q4$ occupe typiquement environ 16-20 Go auxquels s’ajoutent le cache de contexte et l’overhead. Avec seulement 16 Go de RAM totale ou une GPU de 8 Go, cela peut fonctionner partiellement en CPU, mais les performances seront médiocres.

Créez `%UserProfile%\.wslconfig` :

```ini
[wsl2]
memory=48GB
processors=10
swap=12GB
localhostForwarding=true
defaultVhdSize=60000000000
```

Adaptez ces valeurs à votre machine : ne donnez pas toute la RAM à WSL, Windows doit rester confortable. Appliquez ensuite :

```powershell
wsl --shutdown
# ou pour supprimer
# wsl --unregister Ubuntu-24.04
```

** WSL dans VSCODE **

* ajouter l'**extension WSL de microsoft**
* chercher `ctr + shift + P` : connect to WSL
* trouver le dossier windows à partir de `/mnt/c/...`

* OU application WSL et dedans `code`

**Ollama en conteneur**

Dans Ubuntu :

```bash
mkdir -p ~/ai/ollama
cd ~/ai/ollama
```

Créez `compose.yaml` :

```yaml
services:
  ollama:
    image: ollama/ollama:latest
    container_name: ollama
    restart: unless-stopped
    ports:
      - "127.0.0.1:11434:11434"
    volumes:
      - ollama:/root/.ollama
    gpus: all

volumes:
  ollama:
```

Démarrez et vérifiez :

```bash
docker compose up -d
docker compose logs -f ollama
```

Puis téléchargez le modèle :

```bash
docker exec -it ollama ollama pull qwen3.5:27b
```

Vérifiez d’abord le tag exact proposé par la bibliothèque Ollama : `qwen3.5:27b` est à adapter si le nom officiel est différent. Test :

```bash
docker exec -it ollama ollama run qwen3.5:27b
```

Le port est volontairement lié à `127.0.0.1` : Ollama reste accessible localement, y compris depuis Windows sur `http://localhost:11434`, sans être exposé au réseau local.

**OpenCode avec sandbox Docker**

Le principe sain est :

- OpenCode tourne dans Ubuntu WSL.
- Son sandbox utilise le daemon Docker Desktop déjà intégré à WSL.
- Les projets restent dans le système Linux, par exemple `~/code/mon-projet`, pas sous `/mnt/c/...`, pour éviter les lenteurs et les problèmes de permissions.
- Le sandbox reçoit seulement le dossier du projet et les secrets strictement nécessaires.
- Le conteneur OpenCode accède à Ollama via `http://ollama:11434` s’il est sur le même réseau Compose, ou via `http://host.docker.internal:11434` selon son mode de lancement.

Pour un environnement durable, mettez Ollama et le sandbox OpenCode dans un même fichier Compose et un même réseau Docker. Cela évite d’exposer Ollama et permet à OpenCode d’utiliser directement le nom DNS `ollama`.

Docker Desktop est préférable ici. Installez Docker Engine directement dans WSL seulement si vous voulez une machine Linux autonome sans interface Docker Desktop, acceptez la maintenance manuelle et n’avez pas besoin de l’intégration Windows/GPU simplifiée.