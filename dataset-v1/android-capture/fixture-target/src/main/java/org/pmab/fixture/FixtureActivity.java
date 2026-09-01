package org.pmab.fixture;

import android.app.Activity;
import android.app.AlertDialog;
import android.app.Dialog;
import android.graphics.Color;
import android.graphics.drawable.ColorDrawable;
import android.os.Bundle;
import android.view.Gravity;
import android.view.ViewGroup;
import android.view.Window;
import android.widget.Button;
import android.widget.FrameLayout;
import android.widget.LinearLayout;
import android.widget.TextView;
import org.pmab.fixture.core.ScenarioPlan;
import org.pmab.fixture.core.ScenarioRouter;

public final class FixtureActivity extends Activity {
    private static final int SPACE_SMALL_DP = 12;
    private static final int SPACE_LARGE_DP = 24;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        String scenarioId = getIntent().getStringExtra("scenario_id");
        ScenarioPlan plan;
        try {
            plan = ScenarioRouter.resolve(scenarioId, BuildConfig.SOURCE_SLUG);
        } catch (IllegalArgumentException error) {
            renderInvalidScenario(error.getMessage());
            return;
        }

        FrameLayout root = renderHost(plan);
        setContentView(root);
        if (plan.variant() == ScenarioPlan.Variant.POPUP) {
            showPopup(plan);
        } else if (plan.variant() == ScenarioPlan.Variant.BOUNDARY) {
            renderBoundary(root, plan);
        }
    }

    private FrameLayout renderHost(ScenarioPlan plan) {
        FrameLayout root = new FrameLayout(this);
        root.setId(R.id.fixture_root);
        root.setBackgroundColor(Color.rgb(245, 247, 250));

        LinearLayout content = verticalPanel();
        content.setPadding(dp(SPACE_LARGE_DP), dp(SPACE_LARGE_DP), dp(SPACE_LARGE_DP), dp(SPACE_LARGE_DP));
        TextView title = textView("Controlled fixture host: " + plan.sourceSlug(), 24f, Color.BLACK);
        title.setId(R.id.fixture_host_title);
        TextView body = textView(
                plan.variant() == ScenarioPlan.Variant.NO_POPUP
                        ? plan.message()
                        : "Stable host task content remains behind the observation target.",
                18f,
                Color.DKGRAY);
        body.setId(R.id.fixture_host_body);
        content.addView(title, matchWrap());
        content.addView(body, matchWrapWithTopMargin(SPACE_SMALL_DP));
        root.addView(content, new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT,
                Gravity.TOP));
        return root;
    }

    private void renderBoundary(FrameLayout root, ScenarioPlan plan) {
        LinearLayout panel = verticalPanel();
        panel.setId(R.id.fixture_boundary_panel);
        panel.setBackgroundColor(Color.rgb(255, 244, 194));
        panel.setPadding(dp(SPACE_LARGE_DP), dp(SPACE_LARGE_DP), dp(SPACE_LARGE_DP), dp(SPACE_LARGE_DP));
        panel.setClickable(false);
        panel.setFocusable(false);
        TextView message = textView(plan.message(), 19f, Color.BLACK);
        message.setId(R.id.fixture_boundary_message);
        panel.addView(message, matchWrap());

        FrameLayout.LayoutParams layout = new FrameLayout.LayoutParams(
                plan.templateFamily() == ScenarioPlan.TemplateFamily.FULLSCREEN_MODAL
                        ? ViewGroup.LayoutParams.MATCH_PARENT
                        : dp(340),
                plan.templateFamily() == ScenarioPlan.TemplateFamily.FULLSCREEN_MODAL
                        ? ViewGroup.LayoutParams.MATCH_PARENT
                        : ViewGroup.LayoutParams.WRAP_CONTENT,
                boundaryGravity(plan.templateFamily()));
        int margin = dp(SPACE_LARGE_DP);
        layout.setMargins(margin, margin, margin, margin);
        root.addView(panel, layout);
    }

    private void showPopup(ScenarioPlan plan) {
        if (plan.templateFamily() == ScenarioPlan.TemplateFamily.CENTERED_MODAL) {
            new AlertDialog.Builder(this)
                    .setTitle(plan.title())
                    .setMessage(plan.message())
                    .setCancelable(false)
                    .setPositiveButton(R.string.fixture_close, (dialog, which) -> dialog.dismiss())
                    .show();
            return;
        }

        Dialog dialog = new Dialog(this);
        dialog.setTitle(plan.title());
        dialog.setCancelable(false);
        dialog.setContentView(customPopupContent(dialog, plan));
        dialog.show();
        Window window = dialog.getWindow();
        if (window == null) {
            return;
        }
        window.setBackgroundDrawable(new ColorDrawable(Color.WHITE));
        if (plan.templateFamily() == ScenarioPlan.TemplateFamily.BOTTOM_PANEL) {
            window.setGravity(Gravity.BOTTOM);
            window.setLayout(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.WRAP_CONTENT);
        } else {
            window.setGravity(Gravity.CENTER);
            window.setLayout(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT);
        }
    }

    private LinearLayout customPopupContent(Dialog dialog, ScenarioPlan plan) {
        LinearLayout panel = verticalPanel();
        panel.setId(R.id.fixture_popup_panel);
        panel.setPadding(dp(SPACE_LARGE_DP), dp(SPACE_LARGE_DP), dp(SPACE_LARGE_DP), dp(SPACE_LARGE_DP));
        TextView message = textView(plan.message(), 20f, Color.BLACK);
        message.setId(R.id.fixture_popup_message);
        Button close = new Button(this);
        close.setId(R.id.fixture_popup_close);
        close.setText(R.string.fixture_close);
        close.setOnClickListener(view -> dialog.dismiss());
        panel.addView(message, matchWrap());
        panel.addView(close, matchWrapWithTopMargin(SPACE_LARGE_DP));
        return panel;
    }

    private void renderInvalidScenario(String reason) {
        TextView error = textView("Fixture scenario rejected: " + reason, 18f, Color.RED);
        error.setPadding(dp(SPACE_LARGE_DP), dp(SPACE_LARGE_DP), dp(SPACE_LARGE_DP), dp(SPACE_LARGE_DP));
        setContentView(error);
    }

    private LinearLayout verticalPanel() {
        LinearLayout panel = new LinearLayout(this);
        panel.setOrientation(LinearLayout.VERTICAL);
        return panel;
    }

    private TextView textView(String text, float sizeSp, int color) {
        TextView view = new TextView(this);
        view.setText(text);
        view.setTextSize(sizeSp);
        view.setTextColor(color);
        return view;
    }

    private LinearLayout.LayoutParams matchWrap() {
        return new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT);
    }

    private LinearLayout.LayoutParams matchWrapWithTopMargin(int marginDp) {
        LinearLayout.LayoutParams params = matchWrap();
        params.topMargin = dp(marginDp);
        return params;
    }

    private int boundaryGravity(ScenarioPlan.TemplateFamily family) {
        switch (family) {
            case BOTTOM_PANEL:
                return Gravity.BOTTOM | Gravity.CENTER_HORIZONTAL;
            case FULLSCREEN_MODAL:
                return Gravity.FILL;
            case CENTERED_MODAL:
            default:
                return Gravity.CENTER;
        }
    }

    private int dp(int value) {
        return Math.round(value * getResources().getDisplayMetrics().density);
    }
}
