package org.pmab.fixture.core;

import java.util.Map;

public final class ScenarioRouter {
    private static final Map<String, ScenarioPlan.TemplateFamily> FAMILIES = Map.of(
            "commerce", ScenarioPlan.TemplateFamily.CENTERED_MODAL,
            "media", ScenarioPlan.TemplateFamily.BOTTOM_PANEL,
            "travel", ScenarioPlan.TemplateFamily.FULLSCREEN_MODAL,
            "productivity", ScenarioPlan.TemplateFamily.CENTERED_MODAL,
            "education", ScenarioPlan.TemplateFamily.BOTTOM_PANEL);

    private ScenarioRouter() {}

    public static ScenarioPlan resolve(String scenarioId, String builtSourceSlug) {
        if (scenarioId == null || builtSourceSlug == null || !FAMILIES.containsKey(builtSourceSlug)) {
            throw new IllegalArgumentException("scenario and built source must be known");
        }
        String prefix = builtSourceSlug + ".";
        if (!scenarioId.startsWith(prefix)) {
            throw new IllegalArgumentException("scenario does not belong to this application variant");
        }
        String suffix = scenarioId.substring(prefix.length());
        ScenarioPlan.Variant variant;
        String message;
        switch (suffix) {
            case "popup":
                variant = ScenarioPlan.Variant.POPUP;
                message = "Controlled fixture popup message for " + builtSourceSlug + ".";
                break;
            case "no-popup":
                variant = ScenarioPlan.Variant.NO_POPUP;
                message = "Controlled host content with no popup for " + builtSourceSlug + ".";
                break;
            case "boundary":
                variant = ScenarioPlan.Variant.BOUNDARY;
                message = "Controlled visually salient non-modal notice for " + builtSourceSlug + ".";
                break;
            default:
                throw new IllegalArgumentException("unknown scenario variant");
        }
        return new ScenarioPlan(
                scenarioId,
                builtSourceSlug,
                FAMILIES.get(builtSourceSlug),
                variant,
                "PMAB controlled fixture",
                message);
    }
}
