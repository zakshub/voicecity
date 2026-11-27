# Open Decisions

| Decision | Current position | Evidence required |
|---|---|---|
| Speech model | Not selected | Urdu quality, license, hardware, offline behavior |
| Frontend framework | Not locked | UX needs and maintenance cost |
| Metadata storage | SQLite candidate | Profile and history requirements |
| Audio formats | WAV first | Reliable local codecs |
| MP3 export | Later option | Encoder and license review |
| Commercial release | Not decided | User intent and dependency licenses |
| Project license | Not selected | Ownership and distribution decision |
| Packaging | Not selected | Linux target and dependency footprint |
| GPU runtime | Not selected | Actual laptop GPU and model requirements |
| Remote inference | Disabled by default | Explicit decision and privacy review |

## Known constraints
- Initial voice sample is approximately two minutes and available as WAV.
- Do not request another upload unless a real technical blocker requires it.
- Do not assume the phone is suitable for model training or inference.
- Inspect the target Linux laptop before model selection.
- No paid API is part of the default plan.
