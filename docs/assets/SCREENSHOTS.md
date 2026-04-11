# Screenshot Capture Guide

Replace these placeholder files with actual screenshots from the running app at http://localhost:5173

## Required Screenshots

1. **dashboard-overview.png** (800px wide)
   - Full dashboard view showing multiple panels
   - Capture with at least risk feed, supplier grid, and agent log visible

2. **simulation-lab.png** (700px wide)
   - SimPanel with a completed simulation showing baseline vs mitigated results
   - Run any preset scenario first to get results

3. **scenario-comparison.png** (700px wide)
   - Run 2-3 different preset scenarios, click Compare, take screenshot of the modal
   - Should show radar chart, metrics table, and distribution overlays

4. **executive-summary.png** (700px wide)
   - Click "Generate Executive Brief" after a simulation completes
   - Should show the modal with sections and ROI card

5. **agent-pipeline.png** (700px wide)
   - Ask a complex question in chat to trigger multi-agent handoff
   - Capture the agent pipeline panel showing handoff flow

6. **demo-mode.gif** (700px wide)
   - Record a GIF of the demo mode playing through
   - Use a tool like Gifox, LICEcap, or macOS screen recording + ffmpeg
   - Keep it under 15 seconds, target < 5MB file size

## Quick Capture Commands (macOS)

```bash
# Screenshot of full browser window
screencapture -w docs/assets/dashboard-overview.png

# Or use Chrome DevTools: Cmd+Shift+P > "Capture screenshot"
# Set viewport to 1280x800 for consistent sizing
```
