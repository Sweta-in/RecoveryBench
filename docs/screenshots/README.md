# Screenshots

Add the following screenshots to this directory before pushing to GitHub:

- landing.png — Hero section of the frontend (dark background, headline, stats strip, pipeline trace mock)
- evaluation.png — A completed text analysis result showing the radar chart, risk gauge, and pipeline trace with values populated
- benchmark.png — The RecoveryBench-100 section showing the horizontal bar chart

To capture screenshots on Windows: Win+Shift+S (Snipping Tool)
Serve the frontend: python -m http.server 8080 in the frontend/ directory
API must be running: uvicorn api.main:app --port 8000
