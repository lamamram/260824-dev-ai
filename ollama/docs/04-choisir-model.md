# critères pour choisir un modèle

> vocabulaire du développement assisté avec LLM <br>
> Référence: [dépôt github de Matt Pocock](https://github.com/mattpocock/dictionary-of-ai-coding)

---

## :compass: Premier repère : la mémoire disponible

Choisir un modèle, c'est faire tenir **3 choses dans une enveloppe mémoire** (RAM ou VRAM) :

1. les **poids** du modèle (fixes, dépendent du nombre de paramètres et de la quantization) ;
2. le **cache KV** (grandit avec la fenêtre de contexte **et** le nombre d'utilisateurs simultanés) ;
3. l'**overhead** du moteur (activations, buffers, fragmentation) — compter ~1 à 2 Go.

> <span style="color: gold;font-size:12px"><strong><ins>Règle d'or :</ins></strong></span> <br>
> <span style="color: gold;font-size:16px"><strong>AVAILABLE_MEMORY ≥ WEIGHTS_SIZE + KV_CACHE_SIZE + overhead</strong></span>

## :compass: 4 axes de décision

| Axe | Question | Impacte surtout… |
|---|---|---|
| **Pool de ressources** | Combien de RAM / VRAM ? | la taille (B) et la quantization possibles |
| **Hébergeur / moteur** | Ollama, llama.cpp, vLLM, ExLlamaV2 ? | CPU vs GPU, batching, formats de poids |
| **Mono / multi-utilisateur** | 1 personne ou N requêtes concurrentes ? | le **batching** et donc le cache KV total |
| **Capacités** | Multimodal ? Reasoning ? | la famille de modèle et le budget de tokens |

---

## :triangular_ruler: 1. Du nombre de paramètres à la taille/mémoire des poids

### :mag_right: Paramètres / poids

- Un **paramètre** = un **poids** = un nombre réel appris pendant l'entraînement (coefficient d'une matrice du réseau).
- La « taille » d'un modèle s'exprime en **milliards de paramètres** : `7B`, `13B`, `70B`, `405B`…
- Les octets par paramètre dépendent de la **quantization**.

> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span style="color: gold;font-size:16px"><strong>WEIGHTS_SIZE = NB_PARAMS * BYTES_PER_PARAM</strong></span> <br> 

### :mag_right: Quantization (précision des poids)

Réduire la précision = diviser la mémoire au prix d'une légère perte de qualité.

| Précision | Bits / param | Octets / param | 7B ≈ | 70B ≈ | Qualité |
|---|---|---|---|---|---|
| FP16 / BF16 (natif) | 16 | 2,0 | ~14 Go | ~140 Go | référence |
| Q8 / INT8 | 8 | ~1,0 | ~7 Go | ~70 Go | quasi identique |
| <span style="color: gold;font-size:12px">**Q5_K_M**</span> | ~5,5 | ~0,69 | **~5 Go** | **~48 Go** | **très bon (pour développer)** |
| <span style="color: gold;font-size:12px">**Q4_K_M**</span> | ~4,5 | ~0,56 | **~4 Go** | **~40 Go** | **bon (minimum)** |
| Q3_K | ~3,4 | ~0,43 | ~3 Go | ~30 Go | dégradation visible |
| Q2_K | ~2,6 | ~0,33 | ~2,5 Go | ~26 Go | à éviter sauf contrainte forte |

> **Raccourci mental :** en **Q4**, la taille des poids en Go ≈ **moitié du nombre de paramètres en B** <br> 
> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;7B → ~4 Go <br>
> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;70B → ~40 Go <br>
> En **FP16** → **2 × le nombre de B**.

### :mag_right: Formats selon le moteur

- **GGUF** : format quantisé de **llama.cpp / Ollama** (Q4_K_M, Q5_K_M…). Tourne CPU **et** GPU, et permet l'**offload** partiel CPU↔GPU.
- **EXL2** : format de **ExLlamaV2**, quantization à bits variables (ex. 4.0, 4.65, 6.0 bpw), **GPU only**, très rapide en mono-GPU.
- **safetensors FP16/AWQ/GPTQ** : formats consommés par **vLLM** (GPU), AWQ/GPTQ = quantization 4 bits orientée serveur.

---

## :triangular_ruler: 2. structure d'une conversation : système + historique + documents

* un agent conversationnel (comme opencode) stocke 
  - les **requêtes d'un utilisateur**
  - les **réponses du model**,
  - des messages intriductifs (système)
  - et des appels et réponses d'**outils déterministes**
> <span style="color: gold;font-size:16px"><strong>PROMPT = système + historique + documents + réponses en cours</strong></span>

exemple de prompt en json avec rôles :

```json
{
  "messages": [
    {"role": "system", "content": "Tu es un assistant utile."},
    {"role": "user", "content": "Bonjour, peux-tu m'aider à coder ?"},
    {"role": "assistant", "content": "Bien sûr ! Que veux-tu coder ?"},
    {"role": "user", "content": "Je veux un script Python pour trier une liste."}
    {"role": "tool", "Bash(write)": "python -c 'import ...'", "content": "Résultats de recherche sur le tri de listes en Python."}
    //...
  ]
}

```

---

## :triangular_ruler: 3. Fenêtre de contexte et cache KV

### :mag_right: Fenêtre de contexte (`context window`, `num_ctx`)

- Nombre **maximal de tokens** que le modèle « voit » à la fois <br>
  **prompt (système + historique + documents) **+** réponse en cours.**
- Plus elle est grande, plus on peut injecter de contexte (**RAG**, longs documents) — **mais** le cache KV grossit avec elle :arrow_upper_right:  .

### :mag_right: Le cache KV : pourquoi il coûte de la mémoire

À chaque token déjà généré, le modèle mémorise des vecteurs **K** (clé) et **V** (valeur) **par couche**, pour ne pas recalculer tout l'historique à chaque nouveau token. C'est le **cache KV**, et il vit **en plus** des poids.


> <span style="color: gold;font-size:16px"><strong>KV_CACHE_SIZE ≈ 2 (K et V) * nb_layers * n_kv_heads * head_dim * num_ctx</strong></span>&nbsp;<span style="color: aquamarine;font-size:16px"><strong>* batch * byte_precision</strong></span><br>
> &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;--------------------------dépend du modèle------------------------------|-------------dépend de l'utilisateur----------

- `2` : on stocke K **et** V.
- `n_kv_heads × head_dim` : c'est la dimension « cachée » réservée à l'attention (réduite par la **GQA**, voir plus bas).
- `num_ctx` : longueur de contexte → **linéaire**.
- `batch` : nombre de séquences simultanées → **linéaire** (clé du multi-utilisateur).
- `bytes_precision` : FP16 = 2 octets ; le **KV cache quantisé** (Q8/Q4) le divise par 2 à 4.

> <ins>**quantifier le cache KV != quantifier les poids**</ins> : par défaut le cache KV est en FP16 <br>
> c'est à nous de le quantiser si le moteur le permet (Q8, Q4, vLLM fp8). <br>
> <span style="color: gold;font-size:16px"><strong>OLLAMA_KV_CACHE_TYPE=FP16 | Q8 | Q4</strong></span>

> <ins>**Ordre de grandeur (Llama-3 8B, FP16) :**</ins> ~**0,12–0,5 Go par 1000 tokens** de contexte et par séquence. Sur un 70B, c'est plusieurs fois plus. Un contexte de 32k tokens peut coûter **plus de VRAM que les poids eux-mêmes**.

---

## :busts_in_silhouette: 4. Mono vs multi-utilisateur : le batching

### Mono-utilisateur
- 1 requête à la fois. On optimise la **latence** et la mémoire d'**une** séquence.
- Ollama, llama.cpp, ExLlamaV2 sont parfaits ici (poste de travail, démo, agent perso).
- **cache KV total = 1 batch × (KV d'une séquence)**.

### Multi-utilisateur
- N requêtes concurrentes. On optimise le **débit** (tokens/s cumulés).
- Le **batching** = traiter plusieurs séquences **dans le même passage GPU**
- **Conséquence mémoire :** le cache KV est **multiplié par le nombre de séquences actives**.

> En multi-utilisateur, ce n'est généralement **pas** la taille du modèle qui sature la VRAM, mais le **cache KV cumulé**. <br>
> Dimensionner d'abord <span style="color:gold;font-size:16px">**nb_users × num_ctx**</span>

| | Mono-utilisateur | Multi-utilisateur |
|---|---|---|
| Objectif | latence | débit (req/s, tokens/s) |
| Moteur typique | Ollama, llama.cpp, ExLlamaV2 | **vLLM**, TGI, SGLang |
| Mémoire dominée par | les poids | le **cache KV × N** |
| Technique clé | offload, quantization | **continuous batching + PagedAttention** |

---

## :electric_plug: 5. Les hébergeurs / moteurs d'inférence

| Moteur | Cible matériel | Formats | Batching multi-user | Multi-GPU | Points forts | Quand l'utiliser |
|---|---|---|---|---|---|---|
| **Ollama** | CPU **et** GPU, **RAM unifiée** (Apple Silicon) | GGUF | basique (parallélisme limité) | offload simple | installation triviale, API REST, gère le pull des modèles | poste perso, démo, mono-utilisateur, prototypage (**c'est la pile de ce dépôt**) |
| **llama.cpp** | CPU **et** GPU, RAM unifiée, offload CPU↔GPU fin | GGUF | léger (`--parallel`) | pipeline (split par couches) | tourne **partout**, quantization KV, contrôle bas niveau | matériel modeste, edge, CPU-only, offload partiel |
| **vLLM** | **GPU** (NVIDIA surtout) | safetensors FP16, AWQ, GPTQ, fp8 | **excellent** (continuous batching + PagedAttention) | **tensor + pipeline parallelism** | débit serveur maximal, OpenAI-compatible | **production multi-utilisateur**, API à fort trafic |
| **ExLlamaV2** | **GPU only** | EXL2 (bpw variable) | limité | tensor parallelism (récent) | le plus **rapide en mono-GPU** quantisé, faible empreinte | un seul GPU grand public, latence minimale, mono-utilisateur |

### CPU (RAM) vs GPU (VRAM) vs RAM unifiée
- **CPU / RAM** : lent (peu de bande passante mémoire) mais grande capacité et peu cher. Viable pour petits modèles ou usage non temps-réel (llama.cpp, Ollama).
- **GPU / VRAM** : rapide (forte bande passante) mais capacité limitée et coûteuse. Indispensable au temps réel et au multi-utilisateur.
- **RAM unifiée** (Apple Silicon, certains APU) : CPU et GPU partagent **un seul pool** mémoire à bonne bande passante → un Mac 64 Go peut charger un modèle qu'aucun GPU grand public ne tiendrait. Très bien servi par Ollama / llama.cpp (Metal).

---

## :brain: 6. Multimodal et reasoning

### Multimodal
- Modèle qui ingère **plusieurs modalités** : texte **+ image** (voire audio/vidéo). Ex. : **LLaVA**, **Llama 3.2 Vision**, **Qwen2-VL**, **Gemma 3**.
- Coûts : un **encodeur de vision** s'ajoute aux poids, et **chaque image consomme beaucoup de tokens** de contexte (donc du cache KV). Prévoir de la marge mémoire.
- Support inégal selon le moteur : Ollama et vLLM gèrent plusieurs modèles vision ; vérifier la compatibilité **modèle × moteur** avant de choisir.

### Reasoning
- Modèles entraînés à **« réfléchir » avant de répondre** (chaîne de raisonnement, souvent entre balises `<think>…</think>`). Ex. : **DeepSeek-R1**, **QwQ**, modèles « -reasoning ».
- Ils génèrent **beaucoup plus de tokens** (le raisonnement intermédiaire) → **plus de latence, plus de cache KV, contexte plus grand requis**.
- Voir `reasoning_effort` et les *reasoning tags* dans le [glossaire des paramètres](./glossaire-parametres-ollama.md).
- **Quand l'utiliser :** maths, logique, code difficile, planification. **Inutile (et coûteux)** pour de l'extraction, de la reformulation ou du chat simple → préférer un modèle « instruct » classique.

---

## :package: 7. Plusieurs CPU / GPU et réseau : les parallélismes

Quand un modèle **ne tient pas** sur un seul accélérateur, ou qu'on veut **plus de débit**, on distribue le calcul. Quatre stratégies, souvent combinées.

### Tensor parallelism (parallélisme de tenseurs)
- **Quoi :** on découpe **chaque matrice** d'une couche en tranches réparties sur plusieurs GPU ; chaque GPU calcule un morceau de la **même** couche, puis on agrège.
- **Coût :** échanges **à chaque couche** → exige un **interconnect très rapide** (NVLink / PCIe), donc **intra-nœud** (même machine).
- **Usage :** faire tenir un gros modèle (70B+) sur plusieurs GPU d'une même machine **et** accélérer. vLLM : `--tensor-parallel-size N`.

### Pipeline parallelism (parallélisme de pipeline)
- **Quoi :** on découpe le modèle **par blocs de couches** (étages). GPU 0 = couches 1–20, GPU 1 = couches 21–40… La séquence traverse les étages comme une chaîne de montage.
- **Coût :** peu de communication (seulement entre étages) → **tolère le réseau**, donc **multi-nœuds** possible. Mais « bulle » de pipeline (étages parfois inactifs).
- **Usage :** modèle trop gros pour un nœud, ou interconnect lent / cluster réseau. vLLM : `--pipeline-parallel-size N` ; llama.cpp répartit aussi par couches.

### Model parallelism (parallélisme de modèle)
- **Quoi :** terme **générique** = « le modèle est trop gros pour une mémoire, on le **partitionne** ». Tensor parallelism et pipeline parallelism en sont les **deux variantes** concrètes.
- **Usage :** dès que `poids + KV > VRAM d'un GPU`.

### Data parallelism (parallélisme de données)
- **Quoi :** on **réplique le modèle entier** sur chaque GPU/machine et on **répartit les requêtes** (le batch) entre les répliques.
- **Condition :** le modèle doit **tenir en entier** sur un seul accélérateur.
- **Usage :** **monter en débit** en multi-utilisateur (scaling horizontal) — N répliques derrière un load-balancer. C'est de la **scalabilité**, pas une solution au « modèle trop gros ».

| Stratégie | Résout… | Découpe | Communication | Réseau / nœuds |
|---|---|---|---|---|
| **Tensor** | modèle trop gros + vitesse | les matrices d'une couche | énorme (chaque couche) | intra-nœud (NVLink) |
| **Pipeline** | modèle trop gros | par blocs de couches | faible (entre étages) | multi-nœuds OK |
| **Model** | modèle trop gros (terme générique) | tensor et/ou pipeline | — | — |
| **Data** | débit / nb d'utilisateurs | aucune (réplique) | nulle entre répliques | multi-nœuds OK |

> **Combinaison typique en production :** *tensor parallelism* intra-nœud (entre les GPU NVLink d'une machine) **+** *pipeline parallelism* inter-nœuds (entre machines via le réseau) **+** *data parallelism* pour répliquer l'ensemble et absorber le trafic.

---

## :checkered_flag: 8. Arbre de décision rapide

```
1. Combien de VRAM/RAM as-tu ?
   ├─ Pas de GPU / RAM unifiée Mac ........ Ollama ou llama.cpp (GGUF), modèle ≤ ce que tient la RAM
   ├─ 1 GPU grand public (8–24 Go) ........ Q4_K_M (GGUF) ou EXL2 ; mono-utilisateur
   └─ Plusieurs GPU / serveur ............. vLLM (tensor/pipeline parallelism)

2. Combien d'utilisateurs simultanés ?
   ├─ 1 (perso, démo, agent) ............. Ollama / llama.cpp / ExLlamaV2, optimiser la latence
   └─ N (API, équipe, prod) .............. vLLM (continuous batching) ; dimensionner KV = N × num_ctx

3. Quel besoin de contexte ?
   ├─ Court (chat, Q/R) .................. num_ctx 4k–8k
   └─ Long (RAG, gros docs) ............. num_ctx 32k+ → prévoir la VRAM du KV, GQA + KV quantisé

4. Capacités spéciales ?
   ├─ Images ............................ modèle multimodal (LLaVA, Llama 3.2 Vision, Qwen2-VL) + marge mémoire
   └─ Raisonnement complexe ............. modèle reasoning (DeepSeek-R1, QwQ) + contexte large
   (sinon : modèle "instruct" classique, plus léger et plus rapide)
```

### Choisir une « gamme » de taille selon la VRAM (quantization Q4_K_M, mono-utilisateur)

| VRAM / RAM dispo | Gamme réaliste | Exemples | Remarque |
|---|---|---|---|
| ≤ 8 Go | **3B–8B** Q4 | Llama 3.x 8B, Qwen2.5 7B, Phi | contexte modéré (≤ 8k) |
| 12–16 Go | **8B–14B** Q4/Q5 | Qwen2.5 14B, Gemma 2 9B | RAG possible, surveiller le KV |
| 24 Go | **14B–32B** Q4 | Qwen2.5 32B, Gemma 3 27B | sweet spot grand public |
| 48 Go | **32B–70B** Q4 | Llama 3.x 70B Q4 | confort, contexte large |
| 2× 80 Go (serveur) | **70B FP16 / 100B+** | multi-GPU + parallélisme | production multi-utilisateur |

> Pour le **multi-utilisateur**, prendre une gamme **en dessous** de ce que la VRAM permet en mono : la mémoire libérée part dans le **cache KV × nb d'utilisateurs**.

---

## :pushpin: Mémo des formules

```
Poids (Go)        ≈ nb_paramètres(B) × octets_par_param
                     FP16 = 2  | Q8 ≈ 1  | Q4_K_M ≈ 0,56

KV par séquence   ≈ 2 × n_couches × n_kv_heads × head_dim × num_ctx × octets_précision

VRAM mono         ≈ poids + KV(1 séquence) + overhead(~1–2 Go)
VRAM multi        ≈ poids + KV(1 séquence) × nb_users + overhead

Raccourci Q4 : Go_poids ≈ B / 2   (7B→4 Go, 70B→40 Go)
Raccourci FP16 : Go_poids ≈ B × 2 (7B→14 Go, 70B→140 Go)
```

> Voir aussi le [glossaire des paramètres Ollama](./glossaire-parametres-ollama.md) pour `num_ctx`, `reasoning_effort`, quantization du cache KV et function calling.
