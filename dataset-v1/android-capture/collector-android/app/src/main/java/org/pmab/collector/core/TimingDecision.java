package org.pmab.collector.core;

public final class TimingDecision {
    private final boolean accepted;
    private final String reason;

    public TimingDecision(boolean accepted, String reason) {
        this.accepted = accepted;
        this.reason = reason;
    }

    public boolean accepted() { return accepted; }
    public String reason() { return reason; }
}
