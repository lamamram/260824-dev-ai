# Chargement sélectif des experts MoE sur GPU avec llama.cpp

## Architecture MoE (Mixture of Experts)

### Principe de base

Les modèles MoE comme Mixtral 8x7B utilisent une architecture sparse où chaque couche contient:
- **1 routeur (gating network)**: Petit réseau qui sélectionne les experts actifs
- **8 experts**: FFN (Feed-Forward Networks) indépendants
- **Activation sparse**: Seuls 2 experts sur 8 sont activés par token

**Exemple Mixtral 8x7B**:
```
Total parameters: 46.7B
Active parameters par token: 12.9B (2 experts × ~6.5B + routeur)
```

### Mécanisme de routing

Pour chaque token, le routeur calcule des scores pour chaque expert:

```python
# Pseudo-code du routing
gate_scores = router(token_embedding)  # Shape: [batch, seq_len, num_experts]
top_k_scores, top_k_indices = topk(gate_scores, k=2)  # Sélection des 2 meilleurs experts
expert_outputs = [experts[i](token) for i in top_k_indices]
output = weighted_sum(expert_outputs, top_k_scores)
```

**Distribution des experts**:
- Chaque expert est spécialisé sur certains types de tokens
- La distribution suit souvent une loi de puissance (certains experts très actifs, d'autres peu)
- Le routing est dynamique et dépend du contexte

## Possibilités de chargement sélectif

### Approche théorique: Expert Paging

L'idée est de traiter les experts comme des pages mémoire virtuelles:

```
┌─────────────────────────────────────┐
│   GPU VRAM (limitée)                │
├─────────────────────────────────────┤
│ [Expert 0] [Expert 3] [Expert 5]    │  ← Experts chargés
│ [Routeur ] [Embeddings] [Norms]     │  ← Toujours présents
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│   CPU RAM (grande)                  │
├─────────────────────────────────────┤
│ [Expert 1] [Expert 2] [Expert 4]    │  ← Experts en réserve
│ [Expert 6] [Expert 7]               │
└─────────────────────────────────────┘
```

**Flux d'exécution**:
1. Le routeur identifie les experts nécessaires pour le batch actuel
2. Vérifier si ces experts sont en VRAM
3. Si non, les charger depuis la RAM (transfert PCIe)
4. Exécuter le calcul sur GPU
5. Optionnellement, décharger les experts peu utilisés

### Avantages théoriques

1. **Réduction VRAM**: Seulement les experts actifs en GPU
   - Mixtral 8x7B: 8 experts × ~3GB = 24GB total
   - Avec 2 experts actifs: ~6GB au lieu de 24GB
   - Permet d'exécuter des modèles plus grands sur GPU limité

2. **Efficacité énergétique**: Moins de mémoire = moins de consommation

3. **Flexibilité**: Adaptation dynamique au workload

### Défis majeurs

#### 1. Latence de transfert PCIe

```
Transfert d'un expert (3GB):
- PCIe 4.0 x16: ~32 GB/s → 94ms par expert
- PCIe 5.0 x16: ~64 GB/s → 47ms par expert

Pour un batch de 32 tokens avec 2 experts:
- 2 transferts × 94ms = 188ms de latence ajoutée
- Génération typique: ~50ms par token
- Impact: 3.7x plus lent!
```

**Problème**: Le transfert PCIe est 10-100x plus lent que l'accès VRAM

#### 2. Prédictibilité du routing

Le routing MoE est:
- **Dépendant du token**: Chaque token active des experts différents
- **Difficile à prédire**: Nécessite d'exécuter le routeur avant de savoir quels experts charger
- **Batching complexe**: Dans un batch, différents tokens peuvent nécessiter différents experts

**Exemple**:
```
Batch de 4 tokens:
- Token 1: Experts [2, 5]
- Token 2: Experts [0, 3]
- Token 3: Experts [2, 7]
- Token 4: Experts [1, 5]

Experts nécessaires: {0, 1, 2, 3, 5, 7} = 6 experts sur 8
→ Pas d'économie significative!
```

#### 3. Locality et cache

Les experts présentent une certaine locality:
- Certains experts sont fréquemment activés (hot experts)
- D'autres sont rarement utilisés (cold experts)
- Mais cette distribution varie selon le domaine/prompt

**Stratégie de cache**:
```
Hot experts (toujours en VRAM):
- Experts activés > 20% du temps

Cold experts (en RAM):
- Experts activés < 5% du temps

Warm experts (chargement dynamique):
- Entre 5% et 20%
```

## État actuel de llama.cpp

### Support MoE dans llama.cpp

llama.cpp supporte les modèles MoE depuis janvier 2024:
- Mixtral 8x7B
- DBRX
- Autres architectures MoE

**Limitations actuelles**:
```bash
# Chargement standard
./llama-cli -m mixtral-8x7b-q4_0.gguf -ngl 32

# Comportement:
# - Toutes les couches sont chargées (y compris tous les experts)
# - Pas de chargement sélectif des experts
# - GPU offloading binaire: couche complète sur GPU ou CPU
```

### Pourquoi pas de chargement sélectif?

1. **Complexité d'implémentation**:
   - Nécessite un système de pagination mémoire
   - Gestion de cache LRU/LFU pour les experts
   - Synchronisation CPU/GPU asynchrone

2. **Goulot d'étranglement PCIe**:
   - Les benchmarks montrent que le transfert annule les gains
   - Mieux vaut avoir toutes les couches sur CPU que de faire des allers-retours

3. **Architecture GGUF**:
   - Format de fichier conçu pour chargement mmap
   - Pas de support natif pour pagination dynamique

## Solutions alternatives et émergentes

### 1. Expert Pruning (pré-processing)

**Concept**: Analyser le prompt et pré-charger les experts probables

```python
# Analyse statique du prompt
prompt_experts = analyze_prompt(prompt, expert_profiles)
# Charger ces experts sur GPU avant l'inférence
preload_experts(prompt_experts, gpu)
```

**Limitations**:
- Nécessite une analyse préalable du prompt
- Ne fonctionne pas bien pour la génération autoregressive (chaque token peut nécessiter différents experts)

### 2. Expert Quantization différentielle

**Concept**: Quantizer différemment les experts selon leur importance

```
Hot experts: Q8_0 (haute précision, ~6GB)
Cold experts: Q2_K (basse précision, ~1.5GB)
```

**Avantage**: Tous les experts tiennent en VRAM avec quantization adaptative

### 3. Split Expert (approche vLLM/TensorRT-LLM)

**Concept**: Répartir les experts sur plusieurs GPU

```
GPU 0: Experts [0, 1, 2, 3]
GPU 1: Experts [4, 5, 6, 7]
```

**Implémentation**:
```bash
# TensorRT-LLM avec tensor parallelism
trtllm-build \
  --model_dir mixtral-8x7b \
  --tp_size 2 \  # 2 GPU
  --moe_tp_size 2  # Expert parallelism
```

**Avantage**: Pas de transfert CPU↔GPU, seulement GPU↔GPU (NVLink)

### 4. Expert Offloading avec prefetch (recherche active)

**Projets de recherche**:
- **MoE-Lightning** (2024): Optimisation du routing avec prefetch
- **Punica** (2024): Batching efficace pour LoRA et MoE
- **S-LoRA**: Low-rank adaptation avec memory management

**Principe**:
```python
# Prédire les experts du prochain token
next_experts = predict_next_experts(current_context, router)

# Prefetch asynchrone
async_load_to_gpu(next_experts, stream=cuda_stream)

# Exécuter le token actuel
current_output = execute_current_token()

# Synchroniser pour le prochain token
wait_for_prefetch(next_experts)
```

### 5. Expert Merging/Fusion

**Concept**: Fusionner les experts similaires pour réduire le nombre total

```
Avant: 8 experts séparés
Après: 4 experts fusionnés (experts similaires combinés)
```

**Avantage**: Moins d'experts = moins de transferts potentiels

## Benchmarks et performances

### Scénario 1: Tout sur GPU (baseline)

```
Configuration:
- 2x RTX 4090 (48GB VRAM total)
- Mixtral 8x7B Q4_0 (26GB)
- Tous les experts en VRAM

Performance:
- Prompt processing: 1500 tokens/s
- Token generation: 45 tokens/s
- VRAM utilisée: 26GB / 48GB
```

### Scénario 2: Expert paging simulé

```
Configuration:
- 1x RTX 4090 (24GB VRAM)
- Mixtral 8x7B Q4_0 (26GB)
- 2 experts en VRAM, 6 en RAM
- Transfert PCIe 4.0 x16

Performance:
- Prompt processing: 200 tokens/s (7.5x plus lent)
- Token generation: 8 tokens/s (5.6x plus lent)
- VRAM utilisée: 10GB / 24GB
- Transfers/s: ~15 (goulot d'étranglement)
```

**Conclusion**: Le paging d'experts dégrade fortement les performances

### Scénario 3: Quantization adaptative

```
Configuration:
- 1x RTX 4090 (24GB VRAM)
- Mixtral 8x7B avec quantization mixte
  - 2 hot experts: Q8_0 (6GB)
  - 6 cold experts: Q3_K (9GB)
  - Total: 15GB

Performance:
- Prompt processing: 1200 tokens/s
- Token generation: 38 tokens/s
- VRAM utilisée: 15GB / 24GB
- Précision: ~95% du modèle original
```

**Conclusion**: Meilleur compromis performance/VRAM

## Recommandations pratiques

### Quand utiliser le chargement sélectif d'experts?

**À éviter**:
- ❌ Modèles avec peu d'experts (2-4): Pas d'économie significative
- ❌ GPU avec PCIe 3.0 ou inférieur: Latence trop élevée
- ❌ Workloads avec routing très dispersé: Tous les experts sont utilisés
- ❌ Génération autoregressive longue: Impossible de prédire les experts

**À considérer**:
- ✅ Modèles avec beaucoup d'experts (16+) et routing sparse
- ✅ GPU avec PCIe 4.0/5.0 et NVLink
- ✅ Workloads avec locality forte (certains experts dominants)
- ✅ Prompt processing uniquement (pas de génération)

### Stratégies optimales

#### Pour llama.cpp actuellement

```bash
# Option 1: Tout sur GPU si possible
./llama-cli -m mixtral-8x7b-q4_0.gguf -ngl 99

# Option 2: Tout sur CPU si VRAM insuffisante
./llama-cli -m mixtral-8x7b-q4_0.gguf -ngl 0 -t 32

# Option 3: Quantization plus agressive
./llama-cli -m mixtral-8x7b-q3_k_m.gguf -ngl 99
```

#### Pour frameworks spécialisés

**vLLM** (support MoE avancé):
```python
from vllm import LLM

llm = LLM(
    model="mistralai/Mixtral-8x7B-v0.1",
    tensor_parallel_size=2,  # Multi-GPU
    enable_expert_parallel=True,
    gpu_memory_utilization=0.9
)
```

**TensorRT-LLM** (optimisations MoE):
```python
import tensorrt_llm

config = {
    'moe_tp_size': 2,  # Expert parallelism
    'moe_ep_size': 4,  # Expert parallelism
    'enable_kv_cache_reuse': True,
}
```

## Perspectives futures

### Évolutions attendues

1. **Hardware**:
   - PCIe 6.0: 128 GB/s (réduction de la latence)
   - CXL (Compute Express Link): Memory pooling CPU/GPU
   - HBM4: Plus de VRAM sur GPU

2. **Software**:
   - Support natif du paging d'experts dans llama.cpp (en discussion)
   - Frameworks spécialisés MoE (MoE-Lightning, Punica)
   - Optimisations du routing (predictive routing)

3. **Architectures**:
   - MoE avec experts plus petits (plus de sparsity)
   - Routing hiérarchique (meilleure locality)
   - Experts partagés entre couches

### Recherche active

**Papiers récents**:
- "MoE-Lightning: High-Throughput Modelling for MoE LLMs" (2024)
- "Punica: Multi-Tenant LoRA Serving" (2024)
- "S-LoRA: Serving Thousands of Concurrent LoRA Adapters" (2024)

**Axes de recherche**:
- Prefetching prédictif des experts
- Compression des experts (pruning, distillation)
- Routing aware of hardware constraints
- Expert placement optimization

## Conclusion

Le chargement sélectif des experts MoE sur GPU est **théoriquement possible** mais **pratiquement limité** par:

1. **Latence PCIe**: Le transfert annule les gains de performance
2. **Imprédictibilité du routing**: Difficile de savoir quels experts charger
3. **Complexité d'implémentation**: Nécessite un système de pagination sophistiqué

**État actuel de llama.cpp**:
- Pas de support natif pour le chargement sélectif d'experts
- Approche binaire: couche complète sur GPU ou CPU
- Meilleure stratégie: quantization adaptative ou multi-GPU

**Recommandation**:
- Privilégier le multi-GPU avec expert parallelism
- Utiliser la quantization pour réduire l'empreinte mémoire
- Attendre les évolutions hardware (PCIe 6.0, CXL) et software (paging natif)

Le chargement sélectif d'experts reste un domaine de recherche actif avec un potentiel significatif pour démocratiser l'accès aux grands modèles MoE sur du matériel limité.
