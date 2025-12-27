📄 Technical Roadmap: The Core "Flow-to-Lyrics" Pipeline
Goal: Validate the central promise—transforming "yaourt" (gibberish) into rhythmically accurate lyrics—by building a functional, headless (no UI) backend pipeline.

Scope:

Input: Raw Audio File (Mumbled vocal flow).

Output: Generated text lyrics perfectly synchronized to the input rhythm.

Excluded: Frontend, Demucs (Source Separation), Streaming, User Editing.

🏗️ Architecture of the Core Pipeline
The pipeline consists of four distinct stages that must be implemented sequentially.

Extrait de code

graph LR
    Audio(Raw Audio) --> Step1[1. Analysis DSP]
    Step1 --> JSON[Pivot JSON]
    JSON --> Step2[2. Prompt Engine]
    Step2 --> Step3[3. LLM Generation]
    Step3 --> Step4[4. The Gatekeeper]
    Step4 --> Result(Valid Lyrics)
    Step4 -.->|Fail| Step3
🛠️ Step 1: Enhanced Audio Analysis (The "Ear")
Objective: Extract not just when a syllable happens, but how it sounds (Stress & Duration). The current implementation detects onsets but misses the "vibe" (accentuation) needed for natural flow.

1.1 Implement Stress Detection (Amplitude)
Current Status: ✅ Completed (RMS Amplitude vs Local Average)

Implementation Requirement:

Analyze the RMS amplitude of each detected segment.

Calculate the local average amplitude of the phrase.

Mark a segment as is_stressed: true if its peak amplitude exceeds a threshold (e.g., >1.2x the local average).

Why: This tells the AI to put "strong" words (verbs, nouns) on these beats.

1.2 Implement Sustained Note Detection
Current Status: ✅ Completed (Duration Threshold > 0.4s)

Implementation Requirement:

Measure the duration of each segment.

If duration > 0.4s (configurable), flag it in the Pivot JSON (e.g., sustain: true).

Why: Forces the AI to choose words with open vowels (like "fly", "go", "day") rather than short, clipped words (like "cat", "stop").

1.3 Refine Pitch Contour (Optional for MVP, but recommended)
Current Status: Not implemented.

Implementation Requirement:

Use librosa.pyin to detect fundamental frequency (f0).

Classify segments as rise, fall, or flat.

Why: Helps match lyric intonation to melody (e.g., a rising pitch suggests a question).

📝 Step 2: The Structured Prompt (The "Translator")
Objective: Translate the audio constraints into a language the LLM understands strictly.

2.1 JSON-to-Prompt Converter
Task: Create a function that reads the Pivot JSON and constructs a "Skeleton" prompt.

Template Logic:

Context: "You are a rapper writing lyrics to a specific flow."

Constraints: "The line must have exactly [X] syllables."

Stress Map: "The stress pattern is: [0, 1, 0, 1, 1] (0=weak, 1=strong). Match this rhythm."

Vowel Constraints: "Syllable 4 is held long. Use an open vowel."

2.2 Few-Shot Examples
Task: Hardcode 3-5 perfect examples of Input JSON -> Output Lyric in the system prompt to "teach" the model the format.

🧠 Step 3: The Generation Engine (The "Brain")
Objective: Generate high-volume candidates to ensure at least one fits the strict constraints.

3.1 Connect Real LLM
Current Status: Using Mock Generator.

Implementation Requirement:

Integrate Groq (Llama-3-70b) or OpenAI (GPT-4o-mini).

Set temperature low (0.3 - 0.5) for adherence to structure.

3.2 Parallel Batching ("Generate Many")
Strategy: Do not ask for 1 line. Ask for 10 lines in parallel (or one batch request asking for a JSON list of 10 variations).

Why: Probability. If the model has a 30% chance of nailing the rhythm, generating 10 candidates gives a ~97% chance of success.

🛡️ Step 4: The Gatekeeper (Validation Logic)
Objective: ruthlessly filter out any candidate that doesn't strictly match the audio data. This is the "Neuro-Symbolic" part of the AI.

4.1 Phonetic Syllable Counting (Existing)
Current Status: Implemented using g2p_en.

Refinement: Ensure it handles edge cases (like abbreviations or numbers) by expanding them to text first.

4.2 Stress Matching (The "Groove Check")
Current Status: Not implemented.

Implementation Requirement:

Convert generated text to phonemes with stress markers (e.g., "PO-wer" -> P OW1 ER0).

Compare the text stress array [1, 0] with the audio stress array [true, false].

Scoring: Calculate a "Groove Score" (0.0 to 1.0). If Score < 0.8, discard the line.

🏃 Execution Plan: core_pipeline.py
Create a single script core_pipeline.py that orchestrates these steps without any web server.

Load Audio: librosa.load("input.wav")

Analyze: Run AudioEngine -> Get PivotJSON.

Construct Prompt: Format PivotJSON -> String Prompt.

Generate: Call LLM API -> Get List[CandidateStrings].

Filter: Run SyllableValidator on each candidate.

Output: Print the winning lyric + synchronization stats.

Success Metric
The pipeline is "Complete" when you can feed it a distinct mumbled phrase (e.g., “Da-DA-da-da”) and it returns a sentence with exactly that rhythm (e.g., “I ran to the store”) 9 times out of 10.