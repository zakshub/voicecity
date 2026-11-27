# Speech Model Evaluation Plan

## Objective
Select a model that runs locally on the target Linux laptop and produces acceptable Pakistani Urdu, English, and mixed Urdu-English speech from the user's own reference recording.

No model is selected in this foundation commit.

## Gate A: Licensing
Verify code and weight licenses separately. Confirm personal use, modification, redistribution, commercial rights, attribution, share-alike, non-commercial restrictions, and acceptable-use conditions. Unclear terms are a blocker. A permissive wrapper license does not change the weights license.

## Gate B: Language quality
Use a fixed test set containing:
- Urdu in Urdu script.
- Pakistani names and place names.
- English words embedded in Urdu sentences.
- English sentences.
- Mixed Urdu-English code-switching.
- Numbers, dates, currency, abbreviations, and punctuation.

Evaluate pronunciation, intelligibility, naturalness, rhythm, accent, stability, and similarity to the reference voice. A language in a model's language list is not sufficient evidence.

## Gate C: Reference audio
Verify minimum and recommended duration, accepted formats, sample rates, channel requirements, transcript requirements, speaker embedding or fine-tuning needs, and suitability of the existing approximately two-minute WAV.

Do not request a longer recording until a candidate demonstrates that the current sample is insufficient.

## Gate D: Hardware
Measure model size, disk footprint, peak RAM and VRAM, CPU-only performance, GPU support, time to first audio, real-time factor, and repeated-generation stability.

## Gate E: Offline and privacy
Confirm inference works without internet after model download. Inspect telemetry and external network calls. Identify remote account or license server requirements. Ensure source audio is not unexpectedly transmitted.

## Candidate comparison template
| Criterion | Candidate A | Candidate B | Candidate C |
|---|---|---|---|
| Official source | Pending | Pending | Pending |
| Code license | Pending | Pending | Pending |
| Weight license | Pending | Pending | Pending |
| Commercial use | Pending | Pending | Pending |
| Urdu evidence | Pending | Pending | Pending |
| Pakistani Urdu listening score | Pending | Pending | Pending |
| English quality | Pending | Pending | Pending |
| Code-switching | Pending | Pending | Pending |
| Reference audio minimum | Pending | Pending | Pending |
| CPU and RAM | Pending | Pending | Pending |
| GPU and VRAM | Pending | Pending | Pending |
| Offline inference | Pending | Pending | Pending |
| Model size | Pending | Pending | Pending |
| Decision | Not evaluated | Not evaluated | Not evaluated |

## Listening review
Use identical text prompts and reference audio for each candidate. Score intelligibility, pronunciation, naturalness, voice similarity, and code-switching from 1 to 5. Record specific failures. Do not average away a critical Urdu pronunciation failure.

## Selection rule
Approve only when license terms are acceptable, Urdu and English pass listening review, the existing reference recording is supported or its limitation is documented, hardware is sufficient, and local/offline behavior is understood.

If no candidate passes, report that honestly and propose the smallest next experiment.
