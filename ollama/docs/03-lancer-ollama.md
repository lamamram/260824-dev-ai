# lancement local de Ollama

## :mag_right: petite introduction à Ollama

* **GPT**: Generative Pre-trained **Transformer**
  + algorithme général de deep learning communément utilisé par les LLMs

* **LLM**: Large Language Model
  + modèle de langage basé sur l'architecture Transformer
  + entraîné sur un grand corpus de texte pour générer du texte cohérent et contextuellement pertinent

* **chatGPT**: client (chat) + llm créé par *OPENAI*

* **LLama** = LLM de *Meta*

* OLLama = *Open* LLama =  un portail public hébergeant des modèles open-source et/ou gratuit à installer

## :mag_right: Schéma de la pile de services

![](./images/ollama-schema.png)

## :mag_right: paramètrer un modèle avec ollama

* [ici](./glossaire-parametres-ollama.md)


## crash course de Docker


Docker est une plateforme permettant de créer, déployer et exécuter des applications dans des conteneurs. Un conteneur est une unité standardisée qui contient tout le nécessaire pour exécuter une application : code, runtime, bibliothèques et dépendances.

### installation de Docker sur wsl sous Windows

* [ici](./config_wsl.md)


* **<ins>ex lancement d'un postgresql</ins>**


```bash
# -d: détaché (en arrière-plan)
# -e: variable d'environnement pour configurer
# -p: port mapping entre l'hôte et le conteneur
# --name: nom du conteneur
# --restart unless-stopped: redémarrage automatique sauf si le conteneur est arrêté manuellement
# -v: volume pour persister les données du conteneur sur l'hôte quand le conteneur est supprimé
# postgres:15-trixie: image officielle de PostgreSQL version 15 avec la variante "trixie"
docker run \
       -d \
       --name postgres \
       --restart unless-stopped \
       -e POSTGRES_PASSWORD=roottoor \
       -p 5432:5432 \
       -v pgdata:/var/lib/postgresql/data \
       postgres:15-trixie
```

* **<ins>lancement "oneshot" d'un conteneur client</ins>**


```bash
# --rm: supprime le conteneur après exécution
# -it: mode interactif avec terminal (ajout du flux d'entrée et sortie)
# `psql ...` : commande custom pour utiliser des éléments contenus dans l'image
# 172.17.0.2: adresse IP du conteneur PostgreSQL (à adapter selon votre configuration)
# le réseau 172.17.0.0/16 est le réseau bridge par défaut de Docker sur lequel les conteneurs sont connectés par défaut (voir docker inspect <ctn> et docker network ls)
docker run \
       --name client \
       --rm \
       -it postgres:15-trixie psql -h 172.17.0.2 -U postgres --password
```

* arrêt ou suppression d'un conteneur

```bash
docker stop <nom_du_conteneur>
docker rm <nom_du_conteneur>
docker rm -f <nom_du_conteneur> # force stop + remove
```

* **<ins>se donner un prompt de shell dans le conteneur serveur</ins>**

```bash
# -it: mode interactif avec terminal (ajout du flux d'entrée et sortie)
# bash: shell à exécuter dans le conteneur
docker exec -it postgres bash
```

* **<ins>introspection & logs</ins>**

```bash
# inspecter les détails d'un conteneur
docker inspect <nom_du_conteneur>
docker image inspect <nom_de_l_image>
docker network inspect <nom_du_reseau>
docker volume inspect <nom_du_volume>
```

```bash
docker logs <nom_du_conteneur>
```

* **<ins>travailler des documents yaml pour configurer une pile de conteneurs</ins>**

- [ici](../ollama_stack/compose.yml)


## :mag_right: ajuster la fenêtre de contexte d'un modèle avec ollama

> rappel des formules et du vocabulaire (`num_ctx`, cache KV, VRAM) : [choisir un modèle §3](./04-choisir-model.md#️-3-fenêtre-de-contexte-et-cache-kv) et [glossaire des paramètres](./glossaire-parametres-ollama.md#num_ctx).

### :compass: le problème

* par défaut, Ollama limite la fenêtre de contexte à **2048 tokens** (`num_ctx`), quelle que soit la capacité réelle du modèle.
* un modèle comme `llama3.2:3b` (`ollama show llama3.2:3b`) annonce une fenêtre native de **131072 tokens (128k)** — mais l'utiliser en entier coûte du **cache KV**, donc de la **VRAM**, pas seulement des tokens en plus.

### :triangular_ruler: ce que la VRAM permet réellement (ex. GPU local — Quadro P3200, 6 Go)

```
KV_par_token ≈ 2 (K/V) × n_layers × n_kv_heads × head_dim × octets_précision

llama3.2:3b (28 couches, 8 têtes KV, head_dim 128, cache FP16) :
KV_par_token ≈ 2 × 28 × 8 × 128 × 2 ≈ 112 Kio/token

num_ctx = 32k  → KV ≈ 3,5 Go   | poids Q4_K_M ≈ 2 Go → total ≈ 6,5 Go  :warning: à la limite
num_ctx = 128k → KV ≈ 14 Go    | poids Q4_K_M ≈ 2 Go → total ≈ 16 Go   :x: ne tient pas
```

> avec 6 Go de VRAM, **128k n'est pas atteignable en FP16**, même pour un petit modèle 3B : il faut réduire `num_ctx` et/ou quantiser le cache KV.

### :gear: 3 façons de régler `num_ctx`

1. **valeur par défaut du serveur** (variable d'environnement, s'applique à tout modèle qui ne précise rien) — dans [compose.yml](../ollama_stack/compose.yml), service `ollama-gpu-nvidia` :

```yaml
environment:
  - OLLAMA_CONTEXT_LENGTH=32768   # défaut serveur (au lieu de 2048)
  - OLLAMA_FLASH_ATTENTION=1      # requis pour quantiser le cache KV
  - OLLAMA_KV_CACHE_TYPE=q8_0     # divise la taille du cache KV par ~2 (q4_0 par ~4)
```

```bash
docker compose --profile gpu-nvidia up -d --force-recreate ollama-gpu-nvidia
```

2. **par requête / session**, en dépassant le défaut si la VRAM suit :

```bash
docker compose exec ollama-gpu-nvidia ollama run llama3.2:3b
>>> /set parameter num_ctx 65536
```

```bash
curl http://localhost:11434/api/generate -d '{
  "model": "llama3.2:3b",
  "prompt": "...",
  "options": { "num_ctx": 32768 }
}'
```

3. **par modèle**, en figeant la valeur dans un `Modelfile` dérivé :

```Modelfile
FROM llama3.2:3b
PARAMETER num_ctx 32768
```

```bash
docker compose exec ollama-gpu-nvidia   create llama3.2-longctx -f /path/Modelfile
```

* dans **Open WebUI** : *Workspace → Modèles → paramètres avancés → Context Length* règle le même `num_ctx` via l'API.
* vérifier le contexte réellement chargé : `ollama ps` (colonne `CONTEXT`) une fois le modèle chargé.

### :white_check_mark: recommandation pour un GPU 6 Go avec `llama3.2:3b`

| usage | `num_ctx` | `OLLAMA_KV_CACHE_TYPE` | commentaire |
|---|---|---|---|
| chat courant | 8k–16k | `f16` (défaut) | confortable, aucune perte de qualité |
| longs documents / RAG | 32k | `q8_0` | nécessite `OLLAMA_FLASH_ATTENTION=1` |
| 128k (max du modèle) | 128k | `q4_0` | tient tout juste, offload CPU partiel probable → forte baisse de vitesse, à réserver aux cas où la longueur prime sur la latence |

