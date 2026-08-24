# Utilisation CPU et GPU avec llama.cpp pour l'inférence LLM

## Vue d'ensemble

llama.cpp est une bibliothèque d'inférence LLM qui supporte l'exécution hybride sur CPU et GPU. Elle permet d'exploiter simultanément les deux types de processeurs pour optimiser les performances selon le matériel disponible.

## Architecture de calcul

### Calcul sur CPU

Le CPU traite les opérations de manière séquentielle avec un nombre limité de cœurs (généralement 4-64 cœurs). llama.cpp utilise:

- **SIMD (Single Instruction Multiple Data)**: Instructions vectorielles (AVX2, AVX-512, NEON) pour traiter plusieurs données simultanément
- **Multi-threading**: Répartition des calculs sur plusieurs cœurs CPU via OpenMP ou pthreads
- **Quantization**: Modèles compressés (Q4_0, Q4_1, Q5_0, Q5_1, Q8_0) réduisant l'utilisation mémoire et accélérant les calculs

**Avantages CPU**:
- Disponibilité universelle (pas de matériel spécialisé requis)
- Mémoire système généralement plus importante que la VRAM
- Coût inférieur pour les configurations de base

**Limitations CPU**:
- Performances inférieures pour les modèles de grande taille
- Latence plus élevée pour le traitement de tokens
- Goulots d'étranglement mémoire pour les modèles non quantizés

### Calcul sur GPU

Le GPU excelle dans le traitement parallèle massif avec des milliers de cœurs. llama.cpp supporte plusieurs backends GPU:

#### CUDA (NVIDIA)
- Support des architectures Kepler à Blackwell
- Utilisation de cuBLAS pour les opérations matricielles
- Mémoire VRAM dédiée (généralement 4-80 GB selon la carte)
- Support multi-GPU via répartition des couches

#### Metal (Apple Silicon)
- Optimisé pour les puces M1/M2/M3/M4
- Utilisation de l'unified memory (CPU et GPU partagent la même mémoire)
- Accès direct via Metal Performance Shaders
- Pas de copie mémoire CPU↔GPU nécessaire

#### ROCm (AMD)
- Support des architectures RDNA et CDNA
- Alternative open-source à CUDA
- Performance variable selon les modèles de cartes

#### Vulkan
- Support multi-plateforme (Windows, Linux, Android)
- Fonctionne avec la plupart des GPU modernes
- Performance généralement inférieure à CUDA/Metal mais bonne portabilité

#### OpenCL
- Support très large (AMD, Intel, ARM)
- Performance variable selon les implémentations
- Alternative quand CUDA/Metal ne sont pas disponibles

**Avantages GPU**:
- Vitesse d'inférence 10-100x supérieure au CPU pour les modèles de taille moyenne à grande
- Parallélisation massive des opérations matricielles
- Meilleure efficacité énergétique par token généré

**Limitations GPU**:
- Mémoire VRAM limitée (contrainte majeure pour les grands modèles)
- Coût élevé pour les cartes haut de gamme
- Consommation électrique importante

## Mécanisme de partitionnement CPU/GPU (GPU Offloading)

### Concept

llama.cpp permet de répartir les couches du modèle entre CPU et GPU. Cette approche hybride est cruciale quand:
- Le modèle complet ne tient pas en VRAM
- Vous souhaitez optimiser le compromis performance/coût
- Vous avez plusieurs GPU avec des capacités différentes

### Fonctionnement technique

Un modèle transformer est composé de N couches identiques. llama.cpp permet de spécifier combien de couches sont déchargées sur le GPU:

```bash
# Exemple: décharger 20 couches sur le GPU
./llama-cli -m model.gguf -ngl 20
```

**Processus d'exécution**:
1. **Chargement**: Le modèle est chargé en mémoire RAM
2. **Répartition**: Les N premières couches sont copiées en VRAM
3. **Inférence**: 
   - Les couches sur GPU s'exécutent en parallèle sur la VRAM
   - Les couches restantes s'exécutent sur CPU en RAM
   - Les données transitent entre CPU et GPU via PCIe/NVLink
4. **Génération**: Le token de sortie est produit après passage par toutes les couches

### Optimisation du partitionnement

**Facteurs à considérer**:

1. **Capacité VRAM**: 
   - Mesurer la VRAM disponible: `nvidia-smi` (NVIDIA) ou `system_profiler SPDisplaysDataType` (Mac)
   - Calculer l'empreinte mémoire du modèle: `taille modèle × quantization`
   - Exemple: Llama 3 70B en Q4_0 ≈ 40GB

2. **Bande passante PCIe**:
   - Le transfert CPU↔GPU est limité par PCIe (typiquement 16-64 GB/s)
   - Réduire le nombre de transferts améliore les performances
   - Placer autant de couches que possible sur le GPU

3. **Profil de travail**:
   - Prompt processing (prefill): bénéficie du GPU (calcul parallèle)
   - Token generation (decode): moins sensible au GPU (calcul séquentiel)
   - Ajuster le partitionnement selon l'usage dominant

## Paramètres de configuration

### Options de ligne de commande

```bash
# Nombre de couches sur GPU
-ngl, --n-gpu-layers N    # Décharger N couches sur le GPU

# Sélection du GPU (multi-GPU)
-main-gpu ID              # GPU principal pour le calcul
--tensor-split SPLIT      # Répartition entre GPU (ex: "0.5,0.5" pour 50/50)

# Threads CPU
-t, --threads N           # Nombre de threads CPU (défaut: nombre de cœurs physiques)
--threads-batch N         # Threads pour le traitement par batch

# Mémoire
--memory-f32              # Utiliser float32 au lieu de float16 (plus précis, plus lent)
--no-mmap                 # Désactiver le mapping mémoire (plus lent mais plus stable)

# Batch size
-b, --batch-size N        # Taille de batch pour le prompt processing
-ub, --ubatch-size N      # Taille de batch pour le traitement physique
```

### Variables d'environnement

```bash
# CUDA
CUDA_VISIBLE_DEVICES=0,1  # Sélectionner les GPU visibles
CUDA_DEVICE_ORDER=PCI_BUS_ID  # Ordre des devices

# Metal (Apple)
GGML_METAL_USE_ASYNC=1    # Exécution asynchrone
GGML_METAL_DEVICE=0       # Sélection du device

# ROCm
HSA_OVERRIDE_GFX_VERSION=10.3.0  # Forcer la version GFX
```

## Exemples pratiques

### Configuration 1: GPU unique avec modèle complet en VRAM

```bash
# RTX 4090 (24GB VRAM) avec Llama 3 8B Q4_0 (≈5GB)
./llama-cli \
  -m llama-3-8b-q4_0.gguf \
  -ngl 99 \  # Toutes les couches sur GPU
  -t 8 \
  -c 4096
```

**Performance attendue**: 50-100 tokens/s

### Configuration 2: GPU unique avec modèle partiellement en VRAM

```bash
# RTX 3080 (10GB VRAM) avec Llama 3 70B Q4_0 (≈40GB)
./llama-cli \
  -m llama-3-70b-q4_0.gguf \
  -ngl 20 \  # 20 couches sur GPU, reste sur CPU
  -t 16 \
  -c 2048
```

**Performance attendue**: 5-10 tokens/s (goulot d'étranglement PCIe)

### Configuration 3: Multi-GPU

```bash
# 2x RTX 4090 avec Llama 3 70B Q4_0
./llama-cli \
  -m llama-3-70b-q4_0.gguf \
  -ngl 99 \  # Toutes les couches sur GPU
  --tensor-split 0.5,0.5 \  # Répartition égale
  -t 16 \
  -c 4096
```

**Performance attendue**: 30-50 tokens/s

### Configuration 4: Apple Silicon (unified memory)

```bash
# M2 Max (96GB unified memory) avec Llama 3 70B Q4_0
./llama-cli \
  -m llama-3-70b-q4_0.gguf \
  -ngl 99 \  # Toutes les couches sur GPU (pas de copie mémoire)
  -t 8 \
  -c 8192
```

**Performance attendue**: 20-40 tokens/s (excellent grâce à l'unified memory)

### Configuration 5: CPU uniquement

```bash
# Pas de GPU disponible
./llama-cli \
  -m llama-3-8b-q4_0.gguf \
  -ngl 0 \  # Aucune couche sur GPU
  -t 16 \
  -c 4096
```

**Performance attendue**: 5-15 tokens/s

## Monitoring et diagnostic

### Outils de monitoring

```bash
# Surveillance GPU NVIDIA
watch -n 1 nvidia-smi

# Utilisation mémoire GPU détaillée
nvidia-smi dmon -s mu

# Monitoring CPU
htop

# Performance llama.cpp
# Utiliser l'option --verbose pour voir les timings par couche
```

### Indicateurs de performance

- **t/s (tokens par seconde)**: Métrique principale de vitesse
- **P/t (prompt processing)**: Vitesse de traitement du prompt initial
- **T/t (token generation)**: Vitesse de génération token par token
- **VRAM usage**: Mémoire GPU utilisée
- **RAM usage**: Mémoire système utilisée

## Optimisations avancées

### Flash Attention

```bash
# Activer Flash Attention (réduit l'utilisation mémoire pour les longs contextes)
./llama-cli -m model.gguf -fa
```

### KV Cache quantization

```bash
# Quantizer le cache KV pour réduire l'utilisation mémoire
./llama-cli -m model.gguf -ctk q8_0 -ctv q8_0
```

### Mmap et mlock

```bash
# Utiliser mmap pour charger le modèle (plus rapide)
./llama-cli -m model.gguf --mmap

# Verrouiller le modèle en mémoire (évite le swapping)
./llama-cli -m model.gguf --mlock
```

## Compromis et recommandations

### Quand utiliser CPU uniquement
- Modèles petits (< 7B paramètres)
- Pas de GPU disponible
- Contraintes budgétaires
- Usage occasionnel

### Quand utiliser GPU uniquement
- Modèle complet tient en VRAM
- Besoin de performances maximales
- Traitement de prompts longs
- Génération de tokens rapide requise

### Quand utiliser CPU+GPU hybride
- Modèle trop grand pour tenir entièrement en VRAM
- Budget GPU limité
- Compromis acceptable entre performance et coût
- Usage mixte (prompt processing + génération)

### Règles générales

1. **Maximiser les couches GPU**: Plus de couches sur GPU = meilleures performances
2. **Éviter le goulot PCIe**: Si possible, charger le modèle complet sur GPU
3. **Adapter la quantization**: Q4_0 pour la vitesse, Q8_0 pour la précision
4. **Ajuster les threads CPU**: Généralement nombre de cœurs physiques (pas logiques)
5. **Surveiller la VRAM**: Laisser 1-2GB libres pour le système et le cache

## Conclusion

llama.cpp offre une flexibilité remarquable pour l'inférence LLM en permettant l'utilisation combinée de CPU et GPU. Le mécanisme de GPU offloading permet d'adapter l'exécution au matériel disponible, optimisant ainsi les performances tout en respectant les contraintes mémoire.

Le choix de la configuration dépend de:
- La taille du modèle et sa quantization
- La capacité VRAM disponible
- Le budget matériel
- Les exigences de performance

L'approche hybride CPU+GPU est particulièrement utile pour exécuter des modèles de grande taille sur du matériel grand public, démocratisant ainsi l'accès aux LLM puissants.
