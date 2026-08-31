#!/usr/bin/env python3
"""Build an auditable source-field to canonical-item crosswalk.

This is a deterministic schema build helper. It does not create or alter any
empirical popup episode.
"""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
LITERATURE = ROOT / "work" / "literature_field_union.json"
OURS = ROOT / "work" / "our_method_fields.json"
OUTPUT = ROOT / "schema" / "source_to_item_crosswalk.json"


LITERATURE_MAP = {
    "action.action_semantics": ["/decision/selection/action_semantics_pred", "/action_attempts/*/action_semantics", "/candidates/*/ground_truth/action_semantics_gt"],
    "verification.action_trace": ["/action_attempts"],
    "discovery.structured.actionability": ["/candidates/*/features", "/candidates/*/scores/actionability_score"],
    "context.activity": ["/observations/*/owner_context/activity_or_page", "/observations/*/structured_representation/android_raw/activity"],
    "context.app_or_package": ["/environment/app_or_package"],
    "discovery.structured.bounds": ["/candidates/*/normalized/bounds_normalized"],
    "discovery.visual.candidate_bbox": ["/candidates/*/visual_raw/candidate_bbox"],
    "action.candidate_label": ["/candidates/*/normalized/name_or_text"],
    "action.center": ["/candidates/*/visual_raw/center", "/candidates/*/ios_raw/center"],
    "discovery.structured.checkable": ["/candidates/*/normalized/checkable"],
    "discovery.structured.checked_or_toggle": ["/candidates/*/normalized/checked_or_toggle"],
    "discovery.structured.clickable": ["/candidates/*/normalized/clickable"],
    "discovery.visual.cluster_id": ["/observations/*/literature_signals/cluster_id"],
    "context.cmp_id": ["/observations/*/literature_signals/cmp_id", "/observations/*/structured_representation/dom_raw/cmp_id"],
    "discovery.visual.color_emphasis": ["/candidates/*/visual_raw/color_emphasis"],
    "action.command_delivered": ["/action_attempts/*/command_delivered"],
    "action.confidence": ["/decision/selection/confidence", "/action_attempts/*/confidence"],
    "context.window_or_page_context": ["/observations/*/owner_context/window_or_context"],
    "context.dataset": ["/provenance/source_dataset"],
    "verification.destination_state": ["/observations/*/literature_signals/destination_state"],
    "context.device_context": ["/environment/device_state"],
    "context.device_profile": ["/environment/device_model", "/environment/screen_size_px"],
    "discovery.structured.dom_raw": ["/observations/*/structured_representation/dom_raw", "/candidates/*/dom_raw"],
    "discovery.structured.element_type": ["/candidates/*/ios_raw/element_type", "/candidates/*/normalized/role_or_class"],
    "verification.evidence_uris": ["/provenance/episode_evidence_uris", "/verification/dismissal/evidence_uris"],
    "action.execution_channel": ["/decision/selection/execution_channel_pred", "/action_attempts/*/execution_channel"],
    "discovery.structured.exposure_status": ["/scenario/exposure_status_gt", "/candidates/*/ground_truth/exposure_status_gt"],
    "context.foreground_owner": ["/environment/foreground_owner", "/observations/*/owner_context/foreground_owner"],
    "discovery.structured.frame": ["/candidates/*/ios_raw/frame"],
    "discovery.visual.frame_gate_score": ["/observations/*/visual_representation/histogram_similarity"],
    "context.frame_id": ["/observations/*/visual_representation/frame_id"],
    "discovery.structured.geometry": ["/candidates/*/normalized/bounds_normalized", "/candidates/*/normalized/z_or_layer"],
    "discovery.structured.hierarchy": ["/candidates/*/normalized/hierarchy_path", "/candidates/*/normalized/parent_id", "/candidates/*/normalized/children_ids"],
    "action.label_first_token": ["/candidates/*/ios_raw/label_first_token"],
    "context.locale": ["/environment/locale"],
    "context.method_id": ["/decision/method_id"],
    "discovery.structured.name_or_text": ["/candidates/*/normalized/name_or_text"],
    "verification.network_state": ["/observations/*/literature_signals/network_state"],
    "discovery.visual.normalized_tokens": ["/observations/*/literature_signals/normalized_tokens", "/candidates/*/features/normalized_tokens"],
    "discovery.visual.ocr_text": ["/observations/*/visual_representation/ocr_items", "/candidates/*/visual_raw/ocr_text"],
    "discovery.visual.overlay_ratio": ["/observations/*/popup/overlay_ratio", "/observations/*/visual_representation/shadow_mask_ratio"],
    "discovery.structured.owner": ["/candidates/*/normalized/owner"],
    "verification.owner_after": ["/verification/technical_context_recovery/owner_after"],
    "verification.owner_context": ["/verification/technical_context_recovery/owner_context_restored"],
    "context.page_context": ["/observations/*/owner_context/activity_or_page", "/observations/*/owner_context/origin_or_frame"],
    "verification.persisted_business_choice": ["/verification/persistence/business_choice_persisted", "/observations/*/literature_signals/persistent_business_choice"],
    "verification.persisted_dialog_state": ["/verification/persistence/popup_absent_after_relaunch", "/observations/*/literature_signals/dialog_present_after_relaunch"],
    "context.phase": ["/observations/*/phase"],
    "context.platform": ["/environment/platform"],
    "action.policy_trace": ["/decision/rationale_trace", "/decision/policy"],
    "discovery.visual.popup_bbox": ["/observations/*/visual_representation/popup_bbox_pred", "/observations/*/popup/bbox_gt"],
    "discovery.structured.popup_kind": ["/observations/*/popup/kind_gt", "/scenario/popup_kind_gt"],
    "verification.popup_present_after": ["/verification/dismissal/semantic_popup_gone", "/verification/persistence/popup_absent_after_relaunch"],
    "discovery.visual.popup_present_gt": ["/observations/*/popup/present_gt"],
    "discovery.visual.popup_score": ["/observations/*/visual_representation/popup_detector_confidence"],
    "action.protocol_event": ["/observations/*/owner_context/protocol_event"],
    "action.rationale_trace": ["/decision/rationale_trace", "/action_attempts/*/rationale_trace"],
    "discovery.structured.raw_element": ["/candidates/*/raw_ref"],
    "context.recording_id": ["/observations/*/visual_representation/recording_id"],
    "verification.replay_path": ["/observations/*/structured_representation/replay_path"],
    "discovery.structured.role_name_id_bundle": ["/candidates/*/normalized/role_or_class", "/candidates/*/normalized/name_or_text", "/candidates/*/normalized/stable_id", "/candidates/*/normalized/owner"],
    "discovery.structured.role_or_class": ["/candidates/*/normalized/role_or_class"],
    "discovery.visual.screenshot_uri": ["/observations/*/artifacts/screenshot"],
    "discovery.visual.size_emphasis": ["/candidates/*/visual_raw/size_emphasis"],
    "discovery.structured.source_channel": ["/candidates/*/source_channel"],
    "verification.state_signature": ["/observations/*/structured_representation/state_signature"],
    "verification.state_transition": ["/observations/*/literature_signals/state_transition"],
    "action.step_index": ["/action_attempts/*/attempt_index"],
    "action.supported_actions": ["/candidates/*/normalized/supported_actions"],
    "action.tap_coordinate": ["/action_attempts/*/coordinate", "/candidates/*/visual_raw/tap_coordinate"],
    "action.target_candidate": ["/decision/selection/target_candidate_id_pred", "/action_attempts/*/target_candidate_id"],
    "action.target_label": ["/candidates/*/normalized/name_or_text"],
    "discovery.structured.text_rule_match": ["/candidates/*/features/text_rule_match", "/observations/*/literature_signals/text_rule_match"],
    "discovery.visual.tfidf_vector": ["/observations/*/literature_signals/tfidf_vector_uri"],
    "context.timestamp": ["/observations/*/timestamp"],
    "verification.transition_graph": ["/observations/*/structured_representation/transition_graph_uri"],
    "verification.transition_path": ["/observations/*/structured_representation/replay_path"],
    "verification.transition_stack": ["/observations/*/structured_representation/transition_stack"],
    "verification.transition_trace": ["/action_attempts", "/observations/*/literature_signals/state_transition"],
    "context.traversal_state": ["/observations/*/structured_representation/traversal_state"],
    "verification.tree_diff": ["/observations/*/structured_representation/tree_diff_from_previous", "/observations/*/structured_representation/host_tree_diff"],
    "action.trigger_action": ["/scenario/trigger_action"],
    "context.trigger_context": ["/scenario/trigger_action", "/observations/*/owner_context"],
    "discovery.visual.valid_close_target_gt": ["/candidates/*/ground_truth/is_valid_exit_target_gt"],
    "context.viewport": ["/environment/viewport_px", "/observations/*/structured_representation/dom_raw/viewport_px"],
    "discovery.structured.visible": ["/candidates/*/normalized/visible"],
    "action.visual_mark_id": ["/candidates/*/visual_raw/visual_mark_id"],
    "verification.visual_transition_proxy": ["/observations/*/visual_representation/screen_change_proxy", "/verification/weak_proxies/screen_changed"],
    "verification.weak_state_similarity": ["/observations/*/structured_representation/state_similarity", "/verification/weak_proxies/interface_similarity"],
    "context.window_or_context": ["/environment/window_or_context", "/observations/*/owner_context/window_or_context"]
}


OUR_PREFIX_MAP = {
    "episode": {
        "episode_id": ["/identity/item_id"],
        "scenario_id": ["/scenario/scenario_id"],
        "method_id": ["/decision/method_id"],
        "seed": ["/identity/randomization_seed"],
        "started_at": ["/identity/started_at"],
        "ended_at": ["/identity/ended_at"]
    },
    "task_context": {
        "target_population": ["/scenario/target_population"],
        "task_goal": ["/scenario/task_goal"],
        "blocked_step": ["/scenario/blocked_step"],
        "trigger_action": ["/scenario/trigger_action"],
        "blocked_target_gt": ["/scenario/blocked_target_gt"],
        "task_postcondition_gt": ["/scenario/task_postcondition_gt"],
        "scope_label": ["/scenario/scope_label"],
        "popup_kind": ["/scenario/popup_kind_gt"],
        "owner_type_gt": ["/scenario/popup_owner_type_gt"],
        "action_topology": ["/scenario/action_topology_gt"],
        "allowed_action_set_gt": ["/scenario/allowed_action_set_gt"],
        "abstain_allowed_gt": ["/scenario/abstain_allowed_gt"],
        "fixture_or_real_app": ["/identity/record_kind"],
        "popup_expected_gt": ["/scenario/popup_expected_gt"]
    },
    "platform_context": {
        "platform": ["/environment/platform"],
        "os_version": ["/environment/os_version"],
        "oem_or_device": ["/environment/device_model"],
        "app_or_package": ["/environment/app_or_package"],
        "app_version": ["/environment/app_version"],
        "ui_framework": ["/environment/ui_framework"],
        "locale": ["/environment/locale"],
        "theme": ["/environment/theme"],
        "orientation": ["/environment/orientation"],
        "font_scale": ["/environment/font_scale"],
        "assistive_technology": ["/assistive_technology/name"],
        "assistive_technology_config": ["/assistive_technology"],
        "driver_and_adapter_version": ["/environment/driver_and_adapter_version"],
        "snapshot_state_id": ["/environment/reset_snapshot_id"],
        "screen_reader_focus_order_uri": ["/observations/*/screen_reader_state/focus_order_uri"],
        "screen_reader_utterance_trace_uri": ["/observations/*/screen_reader_state/utterance_trace_uri"]
    },
    "capability_profile": {
        "structured_read_status": ["/capability_profile/structured_read_status"],
        "action_execution_status": ["/capability_profile/action_execution_status"],
        "screen_reader_focus_observability": ["/capability_profile/screen_reader_focus_observability"],
        "utterance_observability": ["/capability_profile/utterance_observability"],
        "technical_closed_loop_status": ["/capability_profile/technical_closed_loop_status"],
        "accessible_closed_loop_status": ["/capability_profile/accessible_closed_loop_status"],
        "evidence_refs": ["/capability_profile/evidence_refs"]
    },
    "feedback": {
        "status": ["/feedback/status"],
        "message": ["/feedback/message"],
        "handoff_options": ["/feedback/handoff_options"],
        "delivered": ["/feedback/delivered"]
    },
    "observability": {
        "field_status": ["/observability/field_status"],
        "measurement_channel": ["/observability/measurement_channel"]
    },
    "provenance": {
        "source_artifact_refs": ["/provenance/source_artifacts"],
        "raw_capture_hashes": ["/provenance/raw_capture_hashes"],
        "collector_and_model_versions": ["/provenance/collector_and_model_versions"],
        "annotation_records": ["/annotations", "/provenance/annotation_record_ids"],
        "episode_evidence_uris": ["/provenance/episode_evidence_uris"],
        "evidence_level": ["/provenance/evidence_level"]
    }
}


OBSERVATION_MAP = {
    "observation_id": ["/observations/*/observation_id"],
    "phase": ["/observations/*/phase"],
    "timestamp": ["/observations/*/timestamp"],
    "foreground_owner": ["/observations/*/owner_context/foreground_owner"],
    "window_or_context": ["/observations/*/owner_context/window_or_context"],
    "protocol_event": ["/observations/*/owner_context/protocol_event"],
    "tree_uri": ["/observations/*/artifacts/accessibility_tree"],
    "screenshot_uri": ["/observations/*/artifacts/screenshot"],
    "tree_screenshot_sync_status": ["/observations/*/synchronization/tree_screenshot_sync_status"],
    "ui_fingerprint": ["/observations/*/synchronization/ui_fingerprint"],
    "popup_present_gt": ["/observations/*/popup/present_gt"],
    "popup_present_pred": ["/observations/*/popup/present_pred"],
    "popup_bbox_gt": ["/observations/*/popup/bbox_gt"],
    "popup_roi_pred": ["/observations/*/visual_representation/popup_roi"]
}


CANDIDATE_MAP = {
    "candidate_id": ["/candidates/*/candidate_id"],
    "observation_id": ["/candidates/*/observation_id"],
    "source_channel": ["/candidates/*/source_channel"],
    "owner": ["/candidates/*/normalized/owner"],
    "window_or_context": ["/candidates/*/normalized/window_or_context"],
    "role_or_class": ["/candidates/*/normalized/role_or_class"],
    "name_or_text": ["/candidates/*/normalized/name_or_text"],
    "value_or_hint": ["/candidates/*/normalized/value_or_hint"],
    "stable_id": ["/candidates/*/normalized/stable_id"],
    "supported_actions": ["/candidates/*/normalized/supported_actions"],
    "state": ["/candidates/*/normalized/enabled", "/candidates/*/normalized/clickable", "/candidates/*/normalized/hittable", "/candidates/*/normalized/visible", "/candidates/*/normalized/focusable", "/candidates/*/normalized/checkable", "/candidates/*/normalized/checked_or_toggle", "/candidates/*/normalized/selected"],
    "bounds_normalized": ["/candidates/*/normalized/bounds_normalized"],
    "hierarchy_path": ["/candidates/*/normalized/hierarchy_path"],
    "field_presence_mask": ["/candidates/*/presence"],
    "field_provenance": ["/candidates/*/field_provenance"],
    "raw_ref": ["/candidates/*/raw_ref"],
    "android_raw": ["/candidates/*/android_raw"],
    "ios_raw": ["/candidates/*/ios_raw"],
    "dom_raw": ["/candidates/*/dom_raw"],
    "visual_raw": ["/candidates/*/visual_raw"],
    "matched_cross_channel_candidate_ids": ["/candidates/*/matched_cross_channel_candidate_ids"],
    "action_semantics_gt": ["/candidates/*/ground_truth/action_semantics_gt"],
    "is_valid_close_target_gt": ["/candidates/*/ground_truth/is_valid_exit_target_gt"],
    "exposure_status_gt": ["/candidates/*/ground_truth/exposure_status_gt"],
    "actionability_features": ["/candidates/*/features"],
    "actionability_score_pre_visual": ["/candidates/*/scores/actionability_score_pre_visual"],
    "actionability_score_post_visual": ["/candidates/*/scores/actionability_score_post_visual"]
}


GATE_MAP = {
    "top1_candidate_id_pre_visual": ["/decision/gate/top1_candidate_id"],
    "top1_score_pre_visual": ["/decision/gate/top1_score"],
    "top2_score_pre_visual": ["/decision/gate/top2_score"],
    "score_threshold_tau": ["/decision/gate/threshold_tau"],
    "margin_pre_visual": ["/decision/gate/margin"],
    "margin_threshold_delta": ["/decision/gate/margin_delta"],
    "owner_context_known_and_consistent": ["/decision/gate/owner_consistent"],
    "action_supported_and_executable": ["/decision/gate/action_executable"],
    "action_in_low_risk_policy": ["/decision/gate/low_risk_policy_satisfied"],
    "capture_fresh_and_synchronized": ["/decision/gate/capture_fresh_and_synchronized"],
    "structured_sufficient": ["/decision/gate/structured_sufficient"],
    "gap_reasons": ["/decision/gate/gap_reasons"],
    "visual_fallback_triggered": ["/decision/gate/visual_fallback_triggered", "/decision/visual_fallback/used"],
    "final_candidate_id": ["/decision/gate/final_candidate_id", "/decision/selection/target_candidate_id_pred"],
    "final_score": ["/decision/gate/final_score"],
    "final_state": ["/decision/gate/final_state"],
    "scorer_version": ["/decision/gate/scorer_version"],
    "calibration_version": ["/decision/gate/calibration_version"]
}


DECISION_MAP = {
    "allowed_action_policy_version": ["/decision/policy/allowed_action_policy_version"],
    "action_semantics_pred": ["/decision/selection/action_semantics_pred"],
    "target_candidate_id_pred": ["/decision/selection/target_candidate_id_pred"],
    "execution_channel": ["/decision/selection/execution_channel_pred"],
    "confidence": ["/decision/selection/confidence"],
    "abstain": ["/decision/abstention/abstained"],
    "abstain_reasons": ["/decision/abstention/reason"],
    "rationale_trace": ["/decision/rationale_trace"]
}


ATTEMPT_MAP = {
    "attempt_id": ["/action_attempts/*/attempt_id"],
    "attempt_index": ["/action_attempts/*/attempt_index"],
    "observation_id": ["/action_attempts/*/observation_before_id"],
    "action_semantics_pred": ["/action_attempts/*/action_semantics"],
    "target_candidate_id_pred": ["/action_attempts/*/target_candidate_id"],
    "execution_channel": ["/action_attempts/*/execution_channel"],
    "confidence": ["/action_attempts/*/confidence"],
    "rationale_trace": ["/action_attempts/*/rationale_trace"],
    "locator_or_coordinate": ["/action_attempts/*/selector_or_locator", "/action_attempts/*/coordinate"],
    "command_delivered": ["/action_attempts/*/command_delivered"],
    "execution_error": ["/action_attempts/*/execution_error"],
    "latency_ms": ["/action_attempts/*/latency_ms"]
}


SAFETY_MAP = {
    "sensitive_context_flags": ["/verification/safety/sensitive_context_flags"],
    "safe_exit_exists_gt": ["/verification/safety/safe_exit_exists_gt"],
    "policy_violation": ["/verification/safety/policy_violation"],
    "false_intervention": ["/verification/safety/false_intervention"],
    "harmful_action": ["/verification/safety/harmful_action"],
    "side_effect_detected": ["/verification/safety/side_effect_detected"],
    "cross_app_jump": ["/verification/safety/cross_app_jump"],
    "retry_budget": ["/verification/safety/retry_budget"],
    "retry_count": ["/verification/safety/retry_count"],
    "retry_exhausted": ["/verification/safety/retry_exhausted"]
}


OUTCOME_MAP = {
    "visual_popup_gone": ["/verification/dismissal/visual_popup_gone"],
    "semantic_popup_gone": ["/verification/dismissal/semantic_popup_gone"],
    "D_dismissal": ["/verification/dismissal/D"],
    "owner_context_restored": ["/verification/technical_context_recovery/owner_context_restored"],
    "blocked_target_operable": ["/verification/technical_context_recovery/blocked_target_operable"],
    "C_tech": ["/verification/technical_context_recovery/C_tech"],
    "screen_reader_focus_before": ["/verification/accessible_context_recovery/focus_before"],
    "screen_reader_focus_after": ["/verification/accessible_context_recovery/focus_after"],
    "focus_restored_to_blocked_target_or_successor": ["/verification/accessible_context_recovery/focus_restored_to_blocked_target_or_successor"],
    "utterance_before": ["/verification/accessible_context_recovery/utterance_before"],
    "utterance_after": ["/verification/accessible_context_recovery/utterance_after"],
    "spoken_context_consistent": ["/verification/accessible_context_recovery/spoken_context_consistent"],
    "C_a11y": ["/verification/accessible_context_recovery/C_a11y"],
    "task_postcondition_satisfied": ["/verification/task/task_postcondition_satisfied"],
    "T_task_postcondition": ["/verification/task/T"],
    "verified_technical_task_recovery": ["/verification/metrics/VTR_tech"],
    "accessible_verified_task_recovery": ["/verification/metrics/A_VTR"],
    "extra_screen_reader_navigation_steps": ["/verification/metrics/extra_navigation_steps_after_dismissal"],
    "target_user_validation": ["/verification/accessible_context_recovery/target_user_validation"],
    "abstained": ["/decision/abstention/abstained"],
    "handoff_reason": ["/decision/abstention/reason"]
}


def route_ours(path: str) -> list[str]:
    if path.startswith("observations[]."):
        return OBSERVATION_MAP.get(path.split(".", 1)[1], [])
    if path.startswith("candidates[]."):
        return CANDIDATE_MAP.get(path.split(".", 1)[1], [])
    if path.startswith("gate."):
        return GATE_MAP.get(path.split(".", 1)[1], [])
    if path.startswith("decision."):
        return DECISION_MAP.get(path.split(".", 1)[1], [])
    if path.startswith("action_attempts[]."):
        return ATTEMPT_MAP.get(path.split(".", 1)[1], [])
    if path.startswith("safety."):
        return SAFETY_MAP.get(path.split(".", 1)[1], [])
    if path.startswith("outcome."):
        return OUTCOME_MAP.get(path.split(".", 1)[1], [])
    prefix, _, suffix = path.partition(".")
    return OUR_PREFIX_MAP.get(prefix, {}).get(suffix, [])


def load(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def main() -> None:
    literature = load(LITERATURE)
    ours = load(OURS)
    entries = []
    unmapped = []

    for field in literature["fields"]:
        source_path = field["field_path"]
        targets = LITERATURE_MAP.get(source_path, [])
        if not targets:
            unmapped.append(f"literature:{source_path}")
        entries.append({
            "source_namespace": "literature_14",
            "source_field_path": source_path,
            "canonical_item_pointers": targets,
            "mapping_kind": "semantic_union",
            "source_metadata": field
        })

    for field in ours["fields"]:
        source_path = field["field_path"]
        targets = route_ours(source_path)
        if not targets:
            unmapped.append(f"our_method:{source_path}")
        entries.append({
            "source_namespace": "our_method",
            "source_field_path": source_path,
            "canonical_item_pointers": targets,
            "mapping_kind": "semantic_union",
            "source_metadata": field
        })

    if unmapped:
        raise SystemExit("Unmapped source fields:\n" + "\n".join(unmapped))

    output = {
        "schema_version": "1.1.0-provisional",
        "item_schema": "item.schema.json",
        "source_counts": {
            "literature_14": len(literature["fields"]),
            "our_method": len(ours["fields"]),
            "total": len(entries)
        },
        "mapping_policy": "Semantic duplicates map to the same canonical pointer; platform raw data remains alongside normalized values. A source field may map to multiple canonical pointers when the episode separates prediction, ground truth, execution, or verification.",
        "entries": entries
    }
    OUTPUT.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(entries)} mappings to {OUTPUT}")


if __name__ == "__main__":
    main()
