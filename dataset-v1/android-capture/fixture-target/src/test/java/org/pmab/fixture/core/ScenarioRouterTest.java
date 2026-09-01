package org.pmab.fixture.core;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertThrows;

import java.util.LinkedHashMap;
import java.util.Map;
import org.junit.Test;

public final class ScenarioRouterTest {
    @Test
    public void everyFlavorResolvesAllThreeObservationStrata() {
        // Break caught: one built application ID cannot render its complete capture matrix.
        Map<String, ScenarioPlan.TemplateFamily> sources = new LinkedHashMap<>();
        sources.put("commerce", ScenarioPlan.TemplateFamily.CENTERED_MODAL);
        sources.put("media", ScenarioPlan.TemplateFamily.BOTTOM_PANEL);
        sources.put("travel", ScenarioPlan.TemplateFamily.FULLSCREEN_MODAL);
        sources.put("productivity", ScenarioPlan.TemplateFamily.CENTERED_MODAL);
        sources.put("education", ScenarioPlan.TemplateFamily.BOTTOM_PANEL);

        for (Map.Entry<String, ScenarioPlan.TemplateFamily> source : sources.entrySet()) {
            assertPlan(source.getKey(), "popup", ScenarioPlan.Variant.POPUP, source.getValue());
            assertPlan(source.getKey(), "no-popup", ScenarioPlan.Variant.NO_POPUP, source.getValue());
            assertPlan(source.getKey(), "boundary", ScenarioPlan.Variant.BOUNDARY, source.getValue());
        }
    }

    @Test
    public void aFlavorCannotRenderAnotherPackageScenario() {
        // Break caught: scenario routing contaminates source/app-group provenance.
        assertThrows(
                IllegalArgumentException.class,
                () -> ScenarioRouter.resolve("media.popup", "commerce"));
    }

    private static void assertPlan(
            String source,
            String suffix,
            ScenarioPlan.Variant variant,
            ScenarioPlan.TemplateFamily family) {
        ScenarioPlan plan = ScenarioRouter.resolve(source + "." + suffix, source);
        assertEquals(source + "." + suffix, plan.scenarioId());
        assertEquals(source, plan.sourceSlug());
        assertEquals(variant, plan.variant());
        assertEquals(family, plan.templateFamily());
        assertFalse(plan.automaticAction());
        assertFalse(plan.emitsGold());
    }
}
