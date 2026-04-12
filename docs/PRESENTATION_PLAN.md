# Supply Chain War Room — Presentation Plan

> Master plan for screenshots, demo video, and portfolio presentation.

---

## 1. Screenshots to Capture

Capture at **1280x800 viewport** in Chrome DevTools for consistency. Dark theme should be active (it's the default).

### Shot List

| # | Name | File | What to show | How to trigger |
|---|------|------|-------------|----------------|
| 1 | **Dashboard Overview** | `dashboard-overview.png` | Full war room — map, risk feed, suppliers, agent panel, orders, demand, sim panel all visible | Just load the app with seeded data. Scroll to show Row 1 + Row 2. |
| 2 | **Risk Feed + Alert Rules** | `risk-alert-rules.png` | Risk feed with active events (red/amber glows) alongside the Alert Rules panel showing rules with fire counts | Load app — seed data has active risks and rules with trigger history. |
| 3 | **Agent Pipeline** | `agent-pipeline.png` | Multi-agent handoff flow with orchestrator delegating to specialists, timing visible | In Chat, ask: _"Assess the risk from the typhoon and recommend what we should do"_ — this triggers risk_monitor then strategy. Switch to Pipeline tab. |
| 4 | **Agent Memory** | `agent-memory.png` | Memory tab showing learned patterns with effectiveness bar, expanded card showing situation/action/lesson | Click the Memory tab. Expand the "Suez Canal" or "Shenzhen factory fire" card. |
| 5 | **Agent Decision Audit** | `agent-decisions.png` | Agent Log with expanded decision showing full reasoning, parameters table, impact metrics, approve/reject buttons | Click Agent Log tab. Expand the "Proposed rerouting 4 orders via Ho Chi Minh City" decision (it has status=proposed). |
| 6 | **Chat Interface** | `chat-interface.png` | Conversational AI with a multi-turn exchange showing agent analysis | Ask: _"What are the top risks right now?"_ then follow up with _"What should we do about the highest one?"_ |
| 7 | **Simulation Results** | `simulation-lab.png` | Completed simulation with baseline vs mitigated distributions, statistical summary | Run any preset scenario from the Scenario Builder, or use Chat: _"Simulate a Suez Canal closure"_ |
| 8 | **Scenario Comparison** | `scenario-comparison.png` | 2-3 scenarios compared side-by-side with radar chart + distribution overlays | Run 2+ presets, then click Compare in SimPanel. |
| 9 | **Executive Summary** | `executive-summary.png` | The executive brief modal with sections and ROI card | After a simulation completes, click "Generate Executive Brief". |
| 10 | **Demo Mode Active** | `demo-mode.png` | Demo mode in progress — progress bar at top, highlighted panel, overlay narration visible | Click "Demo" button, capture mid-flow (around step 3-4). |
| 11 | **Create Alert Rule** | `create-alert-rule.png` | The inline rule creation form open with fields filled in | Click "+ New Rule" in Alert Rules panel. Fill in: "Supplier reliability below 0.6", metric=supplier_reliability, operator=<, threshold=0.6. |

### GIF

| # | Name | File | Duration | What to capture |
|---|------|------|----------|-----------------|
| 1 | **Demo Mode** | `demo-mode.gif` | 15-20s | Demo mode auto-playing: disruption trigger -> risk feed lights up -> agents deliberate -> simulation runs -> mitigation proposed |

**Recording tool**: Gifox, LICEcap, or `screencapture` + ffmpeg. Target < 8MB.

```bash
# macOS screen recording to GIF via ffmpeg
# 1. Record with QuickTime (File > New Screen Recording, select window)
# 2. Convert:
ffmpeg -i demo-recording.mov -vf "fps=12,scale=800:-1:flags=lanczos" -loop 0 docs/assets/demo-mode.gif
```

---

## 2. Demo Video Plan

**Format**: 2:00-2:30 narrated walkthrough
**Resolution**: 1920x1080
**Voice**: AI text-to-speech (ElevenLabs, OpenAI TTS, or similar)
**Background music**: Optional subtle ambient/tech track (low volume)

### Script

```
[0:00 - 0:10] INTRO
─────────────────────────────────────────────
VISUAL: App loads. Dashboard overview fades in — dark theme, glowing panels,
        world map with trade routes.
VOICE:  "This is the Supply Chain War Room — a multi-agent AI system
        that monitors global supply chains, detects risks in real time,
        and recommends mitigations before disruptions cascade."

[0:10 - 0:25] LIVE RISK MONITORING
─────────────────────────────────────────────
VISUAL: Hover over risk feed showing active events. Red glow on critical
        events. Pan to alert rules panel.
VOICE:  "The risk feed ingests live data from news and weather APIs.
        Users define custom alert rules — like flagging any supplier
        whose reliability drops below a threshold. When a rule fires,
        it automatically triggers agent analysis."

[0:25 - 0:50] AGENT CONVERSATION
─────────────────────────────────────────────
VISUAL: Switch to Chat tab. Type: "Assess the typhoon risk and recommend
        a plan." Show the typing indicator, then the agent response
        streaming in. Switch to Pipeline tab showing handoff flow:
        orchestrator -> risk_monitor -> strategy.
VOICE:  "Five specialized AI agents collaborate through natural language.
        The orchestrator routes my question to the risk monitor, which
        assesses the threat, then hands off to the strategy agent for
        a mitigation plan. Every handoff is visible in the pipeline view."

[0:50 - 1:10] AGENT DECISIONS + MEMORY
─────────────────────────────────────────────
VISUAL: Switch to Agent Log. Expand a proposed decision showing reasoning,
        parameters, cost impact. Show the approve/reject buttons.
        Switch to Memory tab. Expand a learned pattern.
VOICE:  "Every decision is logged with full reasoning, confidence scores,
        and cost impact. Humans approve or reject before execution.
        The memory system stores lessons learned — so agents reference
        what worked last time a similar disruption happened."

[1:10 - 1:30] MONTE CARLO SIMULATION
─────────────────────────────────────────────
VISUAL: Click a preset scenario in the Scenario Builder. Simulation runs,
        results appear with distribution charts. Click "Generate Executive
        Brief" — show the modal.
VOICE:  "The simulation engine runs ten thousand Monte Carlo iterations
        using real NumPy computation — not LLM-generated numbers.
        After any simulation, a boardroom-ready executive brief is
        generated with disruption analysis, statistical results,
        and ROI calculations."

[1:30 - 1:50] SCENARIO COMPARISON
─────────────────────────────────────────────
VISUAL: Show 2-3 completed simulations. Click Compare. Show the radar
        chart and overlapping distribution curves side by side.
VOICE:  "Run multiple scenarios and compare them side-by-side.
        Radar charts show risk profiles, while overlapping distributions
        reveal where outcomes diverge — helping leadership choose
        between contingency plans with data, not gut feeling."

[1:50 - 2:10] DEMO MODE + CLOSE
─────────────────────────────────────────────
VISUAL: Click "Demo" button. Speed through the auto-play: disruption
        triggers, panels highlight, agents respond, simulation runs.
        End on the full dashboard with all panels populated.
VOICE:  "Demo mode runs the entire workflow end-to-end with one click —
        from disruption trigger through agent deliberation to mitigation
        proposal. Built with Python, FastAPI, React, and the Claude Agent
        SDK. The full source is on GitHub."

[2:10 - 2:15] END CARD
─────────────────────────────────────────────
VISUAL: Fade to dark screen with:
        - "Supply Chain War Room"
        - GitHub URL
        - "Built with Claude Agent SDK"
        - Your name / contact
VOICE:  (silence, just the end card)
```

### Video Production Steps

1. **Record screen** (QuickTime or OBS at 1920x1080, 30fps)
   - Do 2-3 takes. The script above maps to natural mouse movements.
   - Use a browser window sized to 1280x800 centered on a 1920x1080 canvas (black letterbox bars).
   - Disable system notifications before recording.

2. **Generate voiceover**
   - Copy each `VOICE:` block into your TTS tool.
   - Recommended voice: male/female professional, moderate pace, neutral accent.
   - ElevenLabs: "Adam" or "Rachel" voices work well for tech demos.
   - OpenAI TTS: `alloy` or `onyx` voice.
   - Export as WAV/MP3 per section.

3. **Edit** (CapCut, DaVinci Resolve, iMovie, or even ffmpeg)
   - Layer screen recording + voiceover.
   - Add subtle transitions (0.3s crossfade) between sections.
   - Optional: add section title cards between segments (dark background, white text).
   - Optional: subtle background music at -20dB.

4. **Export**
   - MP4, H.264, 1920x1080, 30fps.
   - Target file size: < 50MB for easy sharing.
   - Upload to YouTube (unlisted) or Loom for embeddable link.

### TTS Prompt Template

For each section, feed this to your TTS API:

```
Generate a professional, clear narration for a software demo video.
Tone: confident but conversational, like a senior engineer showing
their work to a CTO. Not salesy. Moderate pace — about 150 words
per minute. Slight pauses between sentences.

Text to narrate:
"[paste VOICE section here]"
```

---

## 3. README Updates After Capture

Once screenshots and video are captured, update these README sections:

1. **Screenshots section** — Replace placeholder `<img>` tags (they already point to the right paths)
2. **Add video embed** — Add after the Screenshots section:
   ```markdown
   ## Video Walkthrough

   <p align="center">
     <a href="YOUR_YOUTUBE_OR_LOOM_URL">
       <img src="docs/assets/video-thumbnail.png" alt="Demo Video" width="600" />
     </a>
     <br />
     <em>2-minute walkthrough: risk detection, agent collaboration, Monte Carlo simulation, and executive briefing</em>
   </p>
   ```
3. **Update badge count** and any feature descriptions that have changed since Tier 4

---

## 4. Capture Sequence (Recommended Order)

Run the app with seeded data, then capture in this order to build state progressively:

```
1. Load app fresh                -> capture #1 (Dashboard Overview)
2. Look at Row 2                 -> capture #2 (Risk + Alert Rules)
3. Open Memory tab               -> capture #4 (Agent Memory)
4. Open Agent Log tab, expand    -> capture #5 (Agent Decision Audit)
5. Switch to Chat, ask question  -> capture #6 (Chat Interface)
6. Wait for response, Pipeline   -> capture #3 (Agent Pipeline)
7. Run simulation preset         -> capture #7 (Simulation Results)
8. Run 2nd preset, Compare       -> capture #8 (Scenario Comparison)
9. Generate Executive Brief      -> capture #9 (Executive Summary)
10. Click "+ New Rule"            -> capture #11 (Create Alert Rule)
11. Click Demo button             -> capture #10 (Demo Mode Active)
12. Record Demo Mode GIF          -> GIF #1
13. Record full video             -> Video
```

---

## 5. File Checklist

After capture, these files should exist:

```
docs/assets/
├── war-room-banner.svg          (exists)
├── SCREENSHOTS.md               (exists — capture guide)
├── dashboard-overview.png       (capture)
├── risk-alert-rules.png         (capture)
├── agent-pipeline.png           (capture)
├── agent-memory.png             (capture)
├── agent-decisions.png          (capture)
├── chat-interface.png           (capture)
├── simulation-lab.png           (capture)
├── scenario-comparison.png      (capture)
├── executive-summary.png        (capture)
├── demo-mode.png                (capture)
├── create-alert-rule.png        (capture)
├── demo-mode.gif                (record + convert)
└── video-thumbnail.png          (extract from video frame)
```
