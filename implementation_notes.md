# Technical Report: Dual-Workflow Architecture Strategy

**Date:** December 28, 2025  
**Source Reference:** Voice Note Analysis ("Notes Implémentations.m4a")  
**Status:** Strategic Pivot / Scope Definition

## 1. Executive Summary

Following the analysis of recent implementation tests, the project strategy is evolving from a single linear pipeline to a **Dual-Workflow Architecture**.

Testing revealed a critical divergence in model performance based on input length:

- **Long files (~10s)** caused the LLM to hallucinate (generating ~68 syllables against a target of 28), losing rhythmic coherence.
- **Short files (~2s)** resulted in high-precision generation (7 syllables generated for 7 targeted).

To address this and maximize user utility, the application will support two distinct interaction models: **"Batch Automation"** for structural work and **"Creative Assist"** for iterative songwriting.

## 2. Workflow Definitions

### Workflow A: The "Batch Automation" Pipeline

**Target Use Case:** Processing long audio files (Full songs, whole verses, choruses).  
**Goal:** Rapidly convert a large "yaourt" (gibberish) draft into a structured textual baseline.

**Input:** Long audio file upload.

**System Behavior (Backend Enforced):**
- The system must not feed the entire audio to the LLM at once.
- **Auto-Segmentation:** The backend must algorithmically slice the long file into short, digestible "bars" (approx. 2-4 seconds) before processing. This mimics the success conditions of the "Short file" test.
- **Serialization:** The system processes these chunks in sequence (or parallel batches) to construct a complete lyric sheet.

**User Experience:** "Set it and forget it." The user uploads, waits, and receives a full draft to edit later.

### Workflow B: The "Co-Pilot" (Interactive Tool)

**Target Use Case:** Iterative composition on short clips (1 or 2 bars, a verse max), loop-based writing, or real-time "mumble" input.  
**Goal:** Provide creative options and inspiration rather than a single "correct" answer.

**Input:**
- Microphone input (Artist mumbles a flow in real-time).
- Selection of a specific region on the timeline.

**System Behavior:**
- **Low Latency:** Optimized for speed.
- **Multi-Candidate Display:** The system generates a batch (e.g., 5 variations) and presents all of them to the user.
- **Imperfect is Acceptable:** As noted in the testing feedback, even "imperfect" candidates can serve as creative blocking tools.

**User Experience:** The tool acts as an instrument. The user loops a bar, sees 5 options, selects the best fit (or parts of it), and moves to the next bar.

## 3. Technical Implications & Requirements

### Backend Logic Update (core_pipeline.py)

The current pipeline is designed to filter and return a single "winner". This must be refactored to support the Dual Workflow:

**API Response Structure:**
- The API must return the full array of candidates (the Batch) alongside their metadata (Groove Score, Syllable Count).
- The frontend will decide whether to auto-select the best one (Workflow A) or display the list (Workflow B).

**Strict Segmentation (Solving the "Hallucination" Issue):**
- To fix the issue where 10s of audio generated double the syllable count, the AudioEngine must implement a **Max Block Duration** constraint.
- **Requirement:** Any input > 4 seconds must be forced-split into smaller Blocks before reaching the PromptEngine.

### Frontend Mode Switching

The UI must accommodate two states:

**Project View (Workflow A):**
- Focus on the full timeline.
- Visualizing the waveform structure.
- Global "Regenerate" actions.

**Live/Loop View (Workflow B):**
- Focus on a single segment.
- **Candidate List UI:** A new component to display the 5 generated options from the LLM.
- **Microphone Integration:** Controls for capturing short audio bursts (future implementation).

## 4. Conclusion

By adopting this dual approach, we solve the technical limitation of the LLM (drift on long contexts) by enforcing segmentation in Workflow A, while unlocking a higher-value product feature (creative assistance) in Workflow B.

The "failure" of the long-audio test has effectively defined the architecture requirements for the full automation pipeline: **Long audio must be treated as a sequence of short audios.**
