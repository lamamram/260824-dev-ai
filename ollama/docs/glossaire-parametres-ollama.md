# Glossaire des paramètres avancés d'Ollama

Pour chaque paramètre : **définition**, **mesure et intervalle**, **quand l'utiliser**.

---

## 1. Transport / streaming

### Streamer la réponse de la conversation (`stream`)
- **Définition** : active l'envoi de la réponse au fur et à mesure de sa génération (token par token) au lieu d'attendre la réponse complète.
- **Mesure et intervalle** : booléen — `true` **DEFAUT** / `false`.
- **Quand l'utiliser** : `true` pour une UI conversationnelle (effet « machine à écrire », meilleure latence perçue). `false` pour un appel programmatique où tu veux le JSON complet d'un coup (scripts, parsing, batch).

### Taille des blocs delta du streaming
- **Définition** : taille des fragments (« deltas ») envoyés à chaque événement de stream. Ollama streame généralement token par token ; ce réglage est surtout côté client/proxy (regroupement de chunks SSE).
- **Mesure et intervalle** : nombre de tokens ou d'octets par chunk (≥ 1).
- **Quand l'utiliser** : augmenter la taille pour réduire le nombre d'événements réseau (moins d'overhead) ; la réduire pour un rendu plus fluide. À ajuster seulement si tu observes un surcoût réseau ou un rendu saccadé.

### Appel de fonction (`tools` / function calling)
- **Définition** : permet au modèle de renvoyer un appel structuré (nom de fonction + arguments JSON) que ton application exécute, plutôt que du texte libre.
- **Mesure et intervalle** : liste de définitions d'outils (schéma JSON). Nécessite un modèle entraîné pour les outils (ex. Llama 3.1+, Qwen, Mistral).
- **Quand l'utiliser** : pour connecter le LLM à des actions réelles (API, base de données, calculs, agents). Inutile pour de la pure génération de texte.

> fait de Ollama un **harnais** pour orchestrer des LLMs et des outils externes, en transformant la sortie du modèle en actions concrètes. 

### Balises de raisonnement (reasoning tags, ex. `<think>...</think>`)
- **Définition** : balises délimitant la chaîne de raisonnement interne d'un modèle « reasoning » (DeepSeek-R1, etc.), séparée de la réponse finale.
- **Mesure et intervalle** : balises textuelles ; selon le client on peut afficher ou masquer ce bloc.
- **Quand l'utiliser** : afficher pour le débogage/transparence ; masquer en production pour ne montrer que la réponse finale. Voir aussi `think` plus bas.

> utilisable avec des modèles de type "reasoning" dans ollama, huggingface, ...

---

## 2. Échantillonnage (sampling) — contrôle de la créativité

### `seed`
- **Définition** : graine du générateur aléatoire. Une même graine + mêmes paramètres ⇒ sortie reproductible.
- **Mesure et intervalle** : entier (ex. `0`, `42`). `0` ou non défini = aléatoire.
- **Quand l'utiliser** : pour des résultats déterministes et reproductibles (tests, évaluations, débogage, démonstrations). À combiner avec `temperature` basse.

### Séquence d'arrêt (`stop`)
- **Définition** : une ou plusieurs chaînes qui, dès qu'elles sont générées, stoppent la génération (la séquence elle-même n'est pas incluse).
- **Mesure et intervalle** : liste de chaînes (ex. `["\n\n", "User:", "```"]`).
- **Quand l'utiliser** : pour borner la sortie (empêcher le modèle de continuer un dialogue, couper après un bloc, formats structurés).

### `temperature`
- **Définition** : contrôle l'aléa / la « créativité ». Plus c'est haut, plus la distribution des tokens est aplatie (réponses variées) ; plus c'est bas, plus c'est déterministe.
- **Mesure et intervalle** : flottant, typiquement `0.0` à `2.0` (défaut Ollama ≈ `0.8`).
- **Quand l'utiliser** : `0.0–0.3` pour du factuel/code/extraction ; `0.7–1.0` pour de la conversation ; `1.0+` pour du brainstorming/créatif.

### Effort de raisonnement (`reasoning_effort`)
- **Définition** : budget de raisonnement alloué aux modèles « reasoning » (combien le modèle « réfléchit » avant de répondre).
- **Mesure et intervalle** : niveau qualitatif `low` / `medium` / `high` (selon le modèle/API).
- **Quand l'utiliser** : `high` pour des problèmes complexes (maths, logique, code difficile) au prix de la latence/coût ; `low` pour des tâches simples où la vitesse prime.

### `logit_bias`
- **Définition** : ajuste manuellement la probabilité de tokens spécifiques (favoriser ou bannir des tokens).
- **Mesure et intervalle** : table `{token_id: biais}`, biais typiquement `-100` (interdit) à `+100` (forcé).
- **Quand l'utiliser** : interdire des mots/jurons, forcer/éviter un vocabulaire précis, contraindre un format.

> notion de "logit": la valeur d'un token de sortie avant l'application de la softmax (probabilité). Un logit élevé = token favorisé ; un logit bas = token pénalisé.

### `max_tokens` (alias Ollama : `num_predict`)
- **Définition** : nombre maximal de tokens **générés** dans la réponse (`-1` = illimité, `-2` = remplir le contexte).
- **Mesure et intervalle** : entier (ex. `128`, `512`, `4096`).
- **Quand l'utiliser** : pour borner coût/latence et éviter des réponses interminables. À ne pas confondre avec `num_ctx` (taille de la fenêtre totale).

### `top_k`
- **Définition** : ne considère que les `k` tokens les plus probables à chaque étape (troncature du vocabulaire candidat).
- **Mesure et intervalle** : entier (défaut ≈ `40`). `1` = greedy ; valeurs élevées (`100+`) = plus de diversité.
- **Quand l'utiliser** : baisser pour des réponses plus sûres/conservatrices ; augmenter pour plus de créativité.

### `top_p` (nucleus sampling)
- **Définition** : ne considère que le plus petit ensemble de tokens dont la probabilité cumulée atteint `p`.
- **Mesure et intervalle** : flottant `0.0–1.0` (défaut ≈ `0.9`).
- **Quand l'utiliser** : alternative/complément à `top_k`. Baisser (`0.5`) pour du factuel ; `0.9–0.95` pour de la conversation naturelle. Conseil : ajuster `temperature` **ou** `top_p`, pas les deux à fond.

### `min_p`
- **Définition** : seuil de probabilité **relatif** au token le plus probable ; élimine les tokens trop improbables. Alternative plus robuste à `top_p`.
- **Mesure et intervalle** : flottant `0.0–1.0` (ex. `0.05`). `0` = désactivé.
- **Quand l'utiliser** : pour garder de la diversité tout en coupant la « traîne » de tokens absurdes, surtout à température élevée.

### `frequency_penalty`
- **Définition** : pénalise les tokens **proportionnellement** au nombre de fois où ils sont déjà apparus (réduit les répétitions de mots).
- **Mesure et intervalle** : flottant, typiquement `-2.0` à `2.0` (`0` = off).
- **Quand l'utiliser** : positif pour réduire les redondances dans de longs textes ; négatif (rare) pour renforcer un vocabulaire récurrent.

### `presence_penalty`
- **Définition** : pénalise un token dès qu'il est **déjà apparu au moins une fois** (encourage l'introduction de nouveaux sujets/mots), indépendamment de la fréquence.
- **Mesure et intervalle** : flottant `-2.0` à `2.0` (`0` = off).
- **Quand l'utiliser** : positif pour pousser le modèle à diversifier les thèmes ; utile en brainstorming.

---

## 3. Mirostat — contrôle dynamique de la perplexité

### `mirostat`
- **Définition** : active un échantillonnage qui régule en continu la « surprise » (perplexité) de la sortie, en alternative à `top_k`/`top_p`.
- **Mesure et intervalle** : `0` = désactivé, `1` = Mirostat v1, `2` = Mirostat v2.
- **Quand l'utiliser** : pour stabiliser la qualité sur de longues générations (éviter dérives répétitives ou incohérentes). Quand activé, il prend le pas sur `top_k`/`top_p`.

### `mirostat_eta`
- **Définition** : taux d'apprentissage de Mirostat (vitesse d'ajustement de l'algorithme aux retours).
- **Mesure et intervalle** : flottant (défaut `0.1`).
- **Quand l'utiliser** : baisser pour des ajustements lents/stables ; augmenter pour une réactivité plus rapide. À toucher seulement si `mirostat` ≠ 0.

### `mirostat_tau`
- **Définition** : perplexité cible — contrôle l'équilibre cohérence/diversité visé.
- **Mesure et intervalle** : flottant (défaut `5.0`).
- **Quand l'utiliser** : valeur basse = sortie plus cohérente/focalisée ; valeur haute = plus de diversité. Actif uniquement si `mirostat` ≠ 0.

---

## 4. Anti-répétition

### `repeat_last_n`
- **Définition** : taille de la fenêtre arrière (nombre de derniers tokens) examinée pour appliquer la pénalité de répétition.
- **Mesure et intervalle** : entier (défaut `64`). `0` = désactivé, `-1` = num_ctx.
- **Quand l'utiliser** : augmenter pour éviter les répétitions sur de longues réponses ; attention à ne pas trop élargir (peut nuire à la cohérence locale).

### `tfs_z` (tail-free sampling)
- **Définition** : réduit l'impact des tokens peu probables de la « queue » de distribution, de façon plus fine que `top_p`.
- **Mesure et intervalle** : flottant ; `1.0` = désactivé, valeurs `< 1.0` (ex. `0.9`) augmentent l'effet. *(Paramètre déprécié/retiré dans certaines versions récentes — vérifier la disponibilité.)*
- **Quand l'utiliser** : pour couper le bruit des tokens improbables tout en gardant de la diversité utile.

### `repeat_penalty`
- **Définition** : facteur multiplicatif pénalisant les tokens déjà vus (dans la fenêtre `repeat_last_n`) pour décourager les boucles/répétitions.
- **Mesure et intervalle** : flottant (défaut `1.1`). `1.0` = pas de pénalité ; `> 1.0` pénalise davantage.
- **Quand l'utiliser** : monter (`1.15–1.3`) si le modèle se répète/boucle ; éviter de trop monter (texte qui devient incohérent ou évite des mots nécessaires).

---

## 5. Mémoire & chargement du modèle

### `use_mmap`
- **Définition** : charge le modèle via *memory-mapping* (le fichier reste sur disque et est mappé en mémoire à la demande) au lieu de tout charger en RAM.
- **Mesure et intervalle** : booléen `true` / `false`.
- **Quand l'utiliser** : `true` (défaut) pour démarrage rapide et faible empreinte RAM, surtout sur gros modèles. `false` si tu as beaucoup de RAM et veux éviter les accès disque.

### `use_mlock`
- **Définition** : verrouille le modèle en RAM (`mlock`) pour empêcher le système de le swapper sur disque.
- **Mesure et intervalle** : booléen `true` / `false`.
- **Quand l'utiliser** : `true` pour garantir des performances stables (pas de swap) si la RAM est suffisante ; à éviter si la RAM est juste (risque de pression mémoire/OOM).

---

## 6. Paramètres spécifiques Ollama

### `think`
- **Définition** : active/désactive le mode « réflexion » des modèles reasoning et contrôle la sortie de la chaîne de pensée.
- **Mesure et intervalle** : booléen `true`/`false` (ou niveau selon le modèle). Le bloc de pensée est renvoyé séparément du `content`.
- **Quand l'utiliser** : `true` pour les tâches complexes nécessitant un raisonnement ; `false` pour des réponses directes/rapides. Voir « Balises de raisonnement ».

### `format`
- **Définition** : force le format de sortie. `json` impose un JSON valide ; on peut aussi passer un **schéma JSON** pour des sorties structurées.
- **Mesure et intervalle** : `"json"` ou un objet schéma JSON.
- **Quand l'utiliser** : dès que tu parses la sortie par programme (extraction de données, API, pipelines). Conseillé d'instruire aussi le modèle dans le prompt de répondre en JSON.

### `num_keep`
- **Définition** : nombre de tokens du début du contexte (prompt système) à **conserver** lorsque le contexte est tronqué pour faire de la place.
- **Mesure et intervalle** : entier (ex. `0`, `24`).
- **Quand l'utiliser** : augmenter pour préserver des instructions système importantes lors de longues conversations qui dépassent la fenêtre.

### `num_ctx`
- **Définition** : taille de la fenêtre de contexte (nombre total de tokens : prompt + historique + génération) que le modèle prend en compte.
- **Mesure et intervalle** : entier (défaut souvent `2048`/`4096` ; jusqu'à la limite du modèle, ex. `8192`, `32768`, `128000`).
- **Quand l'utiliser** : augmenter pour de longs documents/conversations (coûte plus de RAM/VRAM et de calcul) ; garder bas pour économiser les ressources.

### `num_batch`
- **Définition** : taille de lot (batch) pour le traitement des tokens du prompt (combien de tokens sont évalués en parallèle).
- **Mesure et intervalle** : entier (défaut `512`).
- **Quand l'utiliser** : augmenter pour accélérer le traitement de longs prompts si la VRAM/RAM le permet ; réduire si tu manques de mémoire.

### `num_thread`
- **Définition** : nombre de threads CPU utilisés pour l'inférence.
- **Mesure et intervalle** : entier (défaut = nb de cœurs physiques).
- **Quand l'utiliser** : régler manuellement en inférence CPU pour optimiser les perfs ; en général le mettre au nombre de cœurs **physiques** (pas logiques). Peu pertinent en full-GPU.

### `num_gpu`
- **Définition** : nombre de couches (layers) du modèle déchargées sur le GPU.
- **Mesure et intervalle** : entier. `0` = tout CPU ; valeur élevée (ex. `999`) = tout sur GPU si la VRAM suffit.
- **Quand l'utiliser** : augmenter pour la vitesse (max si le modèle tient en VRAM) ; baisser si la VRAM déborde (offload partiel CPU/GPU).

### `keep_alive`
- **Définition** : durée pendant laquelle le modèle reste chargé en mémoire après la dernière requête.
- **Mesure et intervalle** : durée (`5m`, `1h`, `0` = décharge immédiate, `-1` = reste chargé indéfiniment).
- **Quand l'utiliser** : valeur longue (ou `-1`) pour un serveur sollicité fréquemment (évite les rechargements coûteux) ; `0` pour libérer la mémoire aussitôt sur une machine partagée/limitée.

---

## Récapitulatif rapide

| Besoin | Paramètres à régler |
|---|---|
| Réponses déterministes/factuelles | `temperature↓`, `seed`, `top_p↓`, `top_k↓` |
| Plus de créativité | `temperature↑`, `top_p↑`, `min_p`, `presence_penalty↑` |
| Réduire les répétitions | `repeat_penalty↑`, `repeat_last_n↑`, `frequency_penalty↑` |
| Sorties structurées | `format`, `stop`, `logit_bias` |
| Longs contextes | `num_ctx↑`, `num_keep↑`, `num_batch↑` |
| Performance matérielle | `num_gpu`, `num_thread`, `use_mmap`, `use_mlock`, `keep_alive` |
| Stabilité longue génération | `mirostat`, `mirostat_tau`, `mirostat_eta` |
