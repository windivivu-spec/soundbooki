# Optional online listening — implementation boundary

The user wants listening across devices and will decide pricing later. No fee, billing provider, account system, storage service or upload destination has been activated.

## Working now

The app exports a scoped static web package: `index.html`, `player.css`, `player.js`, `book.js`, `book.json`, `audio.m4a`. Audio already contains the selected background track/gain. Text is inserted with textContent, HTML titles are escaped, and the JavaScript data file escapes `<` and Unicode line separators. The player supports start-by-segment, browser audio controls, rate selection, download and local browser position. It needs no third-party assets or API. The same package was tested at localhost; this is not a public deployment.

A user with their own hosting can upload the package as a folder. The host must serve audio byte ranges (HTTP 206 / Accept-Ranges) for reliable browser seeking/resume; a plain development server that ignores Range is insufficient on the tested WebKit browser. `tests/range_server.py` is a loopback-only QA server, not a production service. This by itself has no authentication: a publicly hosted folder makes its text/audio available to anyone who can access that URL. The app does not silently host, upload or share anything.

## Next integrated service

Proposed user flow: select a completed book/scope → review exported audio/text and account destination → upload → private library on phone/web → signed streaming URL → listen/resume on another device. This is an optional network feature; local OCR/TTS remains offline.

Provider-independent endpoints to implement after selecting an account/storage platform:

- POST `/books/uploads`: reserve upload, bind authenticated owner, MIME/size/checksum constraints, return short-lived upload URL.
- POST `/books/{id}/complete`: verify uploaded bytes and finalize manifest; idempotent, no public bucket.
- GET `/books`: owner-scoped library.
- GET `/books/{id}/playback`: authorize owner and return short-lived stream URLs with HTTP Range support.
- PUT `/books/{id}/position`: save segment/time/version per authenticated user; latest update resolves cross-device resume.
- DELETE `/books/{id}`: remove the user's stored media and metadata with a recoverable removal policy where available.

A production service also needs real auth, per-owner isolation, quotas, durable uploads, signed URL renewal, deletion, access tests and a reachable HTTPS player. Billing/paid entitlement checks can be added later; a UI badge is not payment enforcement. None of these endpoints are represented as implemented in the current app.

No storage API credentials are placed in desktop JavaScript, source files, exported ZIPs or logs. Do not reuse unrelated WindiStudio projects or keys for this service without explicit scope. Do not make a public upload merely to demonstrate the button.
