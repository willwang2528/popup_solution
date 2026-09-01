package org.pmab.fixture.core;

public final class ScenarioPlan {
    public enum TemplateFamily {
        CENTERED_MODAL,
        BOTTOM_PANEL,
        FULLSCREEN_MODAL
    }

    public enum Variant {
        POPUP,
        NO_POPUP,
        BOUNDARY
    }

    private final String scenarioId;
    private final String sourceSlug;
    private final TemplateFamily templateFamily;
    private final Variant variant;
    private final String title;
    private final String message;

    ScenarioPlan(
            String scenarioId,
            String sourceSlug,
            TemplateFamily templateFamily,
            Variant variant,
            String title,
            String message) {
        this.scenarioId = scenarioId;
        this.sourceSlug = sourceSlug;
        this.templateFamily = templateFamily;
        this.variant = variant;
        this.title = title;
        this.message = message;
    }

    public String scenarioId() {
        return scenarioId;
    }

    public String sourceSlug() {
        return sourceSlug;
    }

    public TemplateFamily templateFamily() {
        return templateFamily;
    }

    public Variant variant() {
        return variant;
    }

    public String title() {
        return title;
    }

    public String message() {
        return message;
    }

    public boolean automaticAction() {
        return false;
    }

    public boolean emitsGold() {
        return false;
    }
}
