package org.pmab.collector.core;

public final class TimingEvidence {
    private final long treeBeforeStartUptimeMs;
    private final long treeBeforeEndUptimeMs;
    private final long screenshotRequestUptimeMs;
    private final long screenshotResultUptimeMs;
    private final long screenshotCallbackUptimeMs;
    private final long treeAfterStartUptimeMs;
    private final long treeAfterEndUptimeMs;
    private final String beforeTreeHash;
    private final String afterTreeHash;
    private final long eventSequenceBefore;
    private final long eventSequenceAfter;
    private final String focusTokenBefore;
    private final String focusTokenAfter;

    public TimingEvidence(
            long treeBeforeStartUptimeMs,
            long treeBeforeEndUptimeMs,
            long screenshotRequestUptimeMs,
            long screenshotResultUptimeMs,
            long screenshotCallbackUptimeMs,
            long treeAfterStartUptimeMs,
            long treeAfterEndUptimeMs,
            String beforeTreeHash,
            String afterTreeHash,
            long eventSequenceBefore,
            long eventSequenceAfter,
            String focusTokenBefore,
            String focusTokenAfter) {
        this.treeBeforeStartUptimeMs = treeBeforeStartUptimeMs;
        this.treeBeforeEndUptimeMs = treeBeforeEndUptimeMs;
        this.screenshotRequestUptimeMs = screenshotRequestUptimeMs;
        this.screenshotResultUptimeMs = screenshotResultUptimeMs;
        this.screenshotCallbackUptimeMs = screenshotCallbackUptimeMs;
        this.treeAfterStartUptimeMs = treeAfterStartUptimeMs;
        this.treeAfterEndUptimeMs = treeAfterEndUptimeMs;
        this.beforeTreeHash = beforeTreeHash;
        this.afterTreeHash = afterTreeHash;
        this.eventSequenceBefore = eventSequenceBefore;
        this.eventSequenceAfter = eventSequenceAfter;
        this.focusTokenBefore = focusTokenBefore;
        this.focusTokenAfter = focusTokenAfter;
    }

    public long treeBeforeStartUptimeMs() { return treeBeforeStartUptimeMs; }
    public long treeBeforeEndUptimeMs() { return treeBeforeEndUptimeMs; }
    public long screenshotRequestUptimeMs() { return screenshotRequestUptimeMs; }
    public long screenshotResultUptimeMs() { return screenshotResultUptimeMs; }
    public long screenshotCallbackUptimeMs() { return screenshotCallbackUptimeMs; }
    public long treeAfterStartUptimeMs() { return treeAfterStartUptimeMs; }
    public long treeAfterEndUptimeMs() { return treeAfterEndUptimeMs; }
    public String beforeTreeHash() { return beforeTreeHash; }
    public String afterTreeHash() { return afterTreeHash; }
    public long eventSequenceBefore() { return eventSequenceBefore; }
    public long eventSequenceAfter() { return eventSequenceAfter; }
    public String focusTokenBefore() { return focusTokenBefore; }
    public String focusTokenAfter() { return focusTokenAfter; }

}
