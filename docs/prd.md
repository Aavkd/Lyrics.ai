# 📄 Document de Spécifications Techniques : Projet "Flow-to-Lyrics" (v2.1)

**Scope** : MVP (Anglais uniquement)  
**Objectif** : Transformer un flux vocal informel ("yaourt") en paroles de rap/chanson cohérentes, avec une précision rythmique stricte et une validation humaine.

---

## 1. 🔄 Le Pipeline de Traitement (Workflow "Human-in-the-Loop")

Ce pipeline privilégie la précision rythmique sur la vitesse pure, en combinant la puissance des LLM avec une validation logique rigide (Neuro-Symbolic AI).

### Étape 1 : Nettoyage & Isolation (Audio Pre-processing)
*   **Input** : Fichier audio brut (WAV/MP3).
*   **Technologie** : Demucs v4 (Hybrid Transformer).
*   **Processus** :
    *   Séparation des sources (Vocals vs Instrumental).
    *   Normalisation du stem vocal.
    *   Conversion en Mono 16kHz (format optimal pour l'analyse spectrale).
*   **Output** : `vocal_stem.wav`.

### Étape 2 : Extraction Structurelle & Validation UX (Le "Safety Check")
C'est ici que se joue la qualité finale. On ne fait pas confiance aveuglément à l'algo.

*   **Analyse Automatique** :
    *   *Détection d'Onsets* : Librosa (Spectral Flux) pour repérer les débuts de syllabes.
    *   *Détection d'Intensité* : Repérage des pics d'amplitude pour deviner les accents toniques (Stress).
*   **🛑 Interface "Human-in-the-loop" (Frontend)** :
    *   *Visuel* : Waveform interactive (via Wavesurfer.js + Region Plugin). Chaque région = 1 syllabe.
    *   *Feature "Tap-to-Rhythm"* : Si la détection automatique échoue (trop de bruit), l'utilisateur peut réécouter le son et appuyer sur une touche (Espace) en rythme pour redéfinir les marqueurs de syllabes manuellement.
    *   *Actions* : Merge (fusionner), Split (couper), Delete.
*   **Output** : Une "Grid" validée de segments temporels.

### Étape 3 : Le JSON Pivot (Enrichi pour l'Anglais)
Structure de données envoyée au backend de génération.

```json
{
  "meta": {
    "tempo": 90,
    "genre": "Trap",
    "theme": "Overcoming obstacles",
    "language": "en-US"
  },
  "blocks": [
    {
      "id": 1,
      "rhyme_scheme": "A",
      "syllable_target": 8, 
      "segments": [
        { 
          "time_start": 0.0, 
          "duration": 0.2, 
          "is_stressed": true,  // Important pour l'anglais (Strong beat)
          "pitch_contour": "high" // Pour suggérer une voyelle ouverte
        },
        // ... suite des segments
      ]
    }
  ]
}
```

### Étape 4 : Génération & Validation Phonétique (Moteur Hybride)
Remplacement de la boucle itérative simple par une génération parallèle + filtrage.

*   **Stratégie** : "Generate Many, Filter Best"
    *   Au lieu de demander 1 ligne et de la corriger, on demande au LLM de générer 5 variantes d'une même ligne en parallèle.
*   **Le Prompt (System Prompt)** :
    *   Injection de contraintes structurelles : *"Write a line of exactly 8 syllables. Stress pattern should roughly match: DA-da-DA-da..."*
*   **Le Validateur (Python - The "Gatekeeper")** :
    *   *Technologie* : `g2p_en` (Grapheme-to-Phoneme) ou CMU Dict.
    *   *Logique* : Convertir le texte en phonèmes (ex: "Fire" -> F AY1 ER0). Compter les noyaux vocaliques pour obtenir le vrai compte syllabique auditif, et non orthographique.
*   **Scoring** :
    *   *Score Syllabique (0 ou 1)* : Le compte est-il exact ?
    *   *Score de Stress (0.0 - 1.0)* : Les mots accentués tombent-ils sur les segments `is_stressed` ?
*   **Sélection** : On garde la meilleure variante. Si aucune ne matche, on relance un batch avec un prompt d'erreur spécifique.

### Étape 5 : Alignement & Rendu
*   **Technologie** : CTC-Segmentation (si possible) ou alignement linéaire simple basé sur les timestamps validés à l'étape 2.
*   **Output** : Texte affiché mot par mot sur l'interface, synchronisé avec l'audio original.

---

## 2. 🛠️ Stack Technique (Mise à Jour)

### Backend (Python)
*   **Core** : FastAPI (Async, Websockets).
*   **Audio Processing** : Torchaudio, Librosa, Demucs.
*   **NLP / Phonétique (Anglais)** :
    *   `g2p_en` : Pour la conversion texte -> phonèmes (très précis pour l'anglais).
    *   `nltk` (CMU Dict) : Base de données lexicale.
*   **LLM Integration** :
    *   Instructor ou Outlines : Pour forcer une sortie JSON valide (Structured Generation).
    *   *Modèles* : Groq (Llama-3-70b) pour la vitesse (Drafting) ou GPT-4o (si complexité sémantique élevée).

### Frontend (Next.js / React)
*   **Audio UI** : Wavesurfer.js (v7) + Plugins (Regions, Timeline).
*   **State Management** : Zustand (pour gérer l'état complexe de l'éditeur audio).
*   **Communication** : Server-Sent Events (SSE) pour voir les lignes apparaître en temps réel.

---

## 3. 🚦 Analyse des Risques (Mise à jour v2.1)

| Risque Critique | Solution Technique |
| :--- | :--- |
| **Syllabation Anglaise** (Ex: "Every" = 2 syllabes, pas 3) | Utilisation de G2P (Phonèmes). Ne jamais utiliser de compteurs basés sur l'orthographe (pyphen) pour le rap. On compte les sons, pas les lettres. |
| **Latence** (L'utilisateur attend trop) | Génération Parallèle (Batching). Générer 5 candidats en un appel API est aussi rapide qu'en générer 1. Le filtrage Python est instantané (ms). |
| **Erreur de segmentation** (Le "Yaourt" est illisible) | Feature "Tap-to-Rhythm". Permettre à l'utilisateur de taper le rythme au clavier pour corriger l'IA instantanément. |
| **Flow "Robotique"** | Détection d'accents (Stress). Mapper les temps forts de l'audio aux syllabes accentuées du texte via CMU Dict (1 = Primary Stress). |

---

## 4. 📅 Roadmap Révisée (Focus MVP Anglais)

### Phase 0 : Le "Blind Test" (Semaines 1-2) - Priorité Absolue
*   **Objectif** : Valider le moteur de génération sans interface graphique.
*   **Action** : Script Python qui prend une liste `[8, 10, 8, 10]` syllabes.
*   **Test** : Génération via LLM -> Validation via `g2p_en`.
*   **KPI** : Atteindre >90% de lignes valides rythmiquement.

### Phase 1 : L'Outil de Segmentation (Semaines 3-4)
*   Développement du Frontend Wavesurfer.js.
*   Implémentation de Demucs (Backend).
*   Feature "Tap-to-Rhythm" fonctionnelle.
*   Pas encore de génération de texte, juste Audio -> Blocs JSON.

### Phase 2 : Intégration End-to-End (Semaines 5-6)
*   Connexion du moteur Phase 0 avec l'interface Phase 1.
*   Streaming des réponses.
*   Export initial.