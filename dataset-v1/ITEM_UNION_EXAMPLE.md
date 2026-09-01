# Item 字段并集示例

> 这是仅由公开 schema 产物生成的视图：该 item 是 `synthetic_schema_fixture`，不是经验数据，也不是 gold 数据。

## Fixture 披露

| 属性 | 值 |
|---|---|
| Item ID | `fixture.android.popup-message.positive.0001` |
| 记录类型 | `synthetic_schema_fixture` |
| 证据级别 | `synthetic_schema_fixture` |
| 是否为经验数据 | **否** |
| 是否为 gold 数据 | **否** |
| 动作策略 | `no_action` |
| 动作尝试次数 | 0 |

## 来源字段并集

| 来源类别 | 原子 source field 数 |
|---|---:|
| `literature_14` | 90 |
| `our_method` | 165 |
| **并集总计** | **255** |

## 机器审计完整性

这里的 presence 表示：每个 source-field 记录在公开 catalog 与 crosswalk 中恰好出现一次，并且至少具有一个 canonical pointer；它不表示该 v1 item 的每个 nullable 值都已被观测。

Provenance 完整性表示：对应来源类别要求的 source metadata 已齐备；它不构成经验验证。

| 来源类别 | Catalog presence | Crosswalk presence | 非空 canonical mapping | Provenance 完整 |
|---|---:|---:|---:|---:|
| `literature_14` | 90 | 90 | 90 | 90 |
| `our_method` | 165 | 165 | 165 | 165 |
| **并集总计** | **255** | **255** | **255** | **255** |

| Item 形状检查 | 完整 |
|---|---:|
| Template/fixture 顶层 containers | 16/16 |

## 此单个 item 的 canonical containers

`action_attempts`, `annotations`, `assistive_technology`, `candidates`, `capability_profile`, `decision`, `environment`, `feedback`, `identity`, `message_judgment`, `observability`, `observations`, `provenance`, `quality`, `scenario`, `verification`

## 完整 source field 清单

下表直接由通过校验的公开 crosswalk 生成；只列字段元数据，不列任何 item 值。

| 序号 | Namespace | Source field path | Canonical pointer(s) | Provenance 摘要 |
|---:|---|---|---|---|
| 1 | `literature_14` | `action.action_semantics` | `/decision/selection/action_semantics_pred`<br>`/action_attempts/*/action_semantics`<br>`/candidates/*/ground_truth/action_semantics_gt` | papers=abandon_all_hope_2024,cookieverse_bannerclick,freely_given_consent_2022,ssldetecter_2019,tcf_aaid_2026,the_ok_is_not_enough_2023; evidence=mixed |
| 2 | `literature_14` | `verification.action_trace` | `/action_attempts` | papers=hotmobile_ad_policy_2018; evidence=reported |
| 3 | `literature_14` | `discovery.structured.actionability` | `/candidates/*/features`<br>`/candidates/*/scores/actionability_score` | papers=vlm_fuzz_2026; evidence=reported |
| 4 | `literature_14` | `context.activity` | `/observations/*/owner_context/activity_or_page`<br>`/observations/*/structured_representation/android_raw/activity` | papers=ssldetecter_2019; evidence=inferred_from_local_source |
| 5 | `literature_14` | `context.app_or_package` | `/environment/app_or_package` | papers=popsweeper_2024,tcf_aaid_2026; evidence=reported |
| 6 | `literature_14` | `discovery.structured.bounds` | `/candidates/*/normalized/bounds_normalized` | papers=poker_sneaky_popups,vlm_fuzz_2026; evidence=reported |
| 7 | `literature_14` | `discovery.visual.candidate_bbox` | `/candidates/*/visual_raw/candidate_bbox` | papers=poker_sneaky_popups,popsweeper_2024,whispertest_2025; evidence=reported |
| 8 | `literature_14` | `action.candidate_label` | `/candidates/*/normalized/name_or_text` | papers=dynamic_ios_privacy_2021; evidence=inferred_from_local_source |
| 9 | `literature_14` | `action.center` | `/candidates/*/visual_raw/center`<br>`/candidates/*/ios_raw/center` | papers=ios_applications_testing_2018; evidence=inferred_from_local_source |
| 10 | `literature_14` | `discovery.structured.checkable` | `/candidates/*/normalized/checkable` | papers=abandon_all_hope_2024,tcf_aaid_2026; evidence=mixed |
| 11 | `literature_14` | `discovery.structured.checked_or_toggle` | `/candidates/*/normalized/checked_or_toggle` | papers=abandon_all_hope_2024,tcf_aaid_2026,whispertest_2025; evidence=mixed |
| 12 | `literature_14` | `discovery.structured.clickable` | `/candidates/*/normalized/clickable` | papers=poker_sneaky_popups; evidence=reported |
| 13 | `literature_14` | `discovery.visual.cluster_id` | `/observations/*/literature_signals/cluster_id` | papers=freely_given_consent_2022; evidence=reported |
| 14 | `literature_14` | `context.cmp_id` | `/observations/*/literature_signals/cmp_id`<br>`/observations/*/structured_representation/dom_raw/cmp_id` | papers=cookieverse_bannerclick,tcf_aaid_2026; evidence=reported |
| 15 | `literature_14` | `discovery.visual.color_emphasis` | `/candidates/*/visual_raw/color_emphasis` | papers=the_ok_is_not_enough_2023; evidence=reported |
| 16 | `literature_14` | `action.command_delivered` | `/action_attempts/*/command_delivered` | papers=whispertest_2025; evidence=reported |
| 17 | `literature_14` | `action.confidence` | `/decision/selection/confidence`<br>`/action_attempts/*/confidence` | papers=poker_sneaky_popups,tcf_aaid_2026; evidence=reported |
| 18 | `literature_14` | `context.window_or_page_context` | `/observations/*/owner_context/window_or_context` | papers=cookieverse_bannerclick; evidence=reported |
| 19 | `literature_14` | `context.dataset` | `/provenance/source_dataset` | papers=popsweeper_2024; evidence=reported |
| 20 | `literature_14` | `verification.destination_state` | `/observations/*/literature_signals/destination_state` | papers=hotmobile_ad_policy_2018; evidence=reported |
| 21 | `literature_14` | `context.device_context` | `/environment/device_state` | papers=dios_2014,whispertest_2025; evidence=reported |
| 22 | `literature_14` | `context.device_profile` | `/environment/device_model`<br>`/environment/screen_size_px` | papers=cookieverse_bannerclick; evidence=reported |
| 23 | `literature_14` | `discovery.structured.dom_raw` | `/observations/*/structured_representation/dom_raw`<br>`/candidates/*/dom_raw` | papers=cookieverse_bannerclick; evidence=reported |
| 24 | `literature_14` | `discovery.structured.element_type` | `/candidates/*/ios_raw/element_type`<br>`/candidates/*/normalized/role_or_class` | papers=dynamic_ios_privacy_2021; evidence=inferred_from_local_source |
| 25 | `literature_14` | `verification.evidence_uris` | `/provenance/episode_evidence_uris`<br>`/verification/dismissal/evidence_uris` | papers=cookieverse_bannerclick; evidence=reported |
| 26 | `literature_14` | `action.execution_channel` | `/decision/selection/execution_channel_pred`<br>`/action_attempts/*/execution_channel` | papers=cookieverse_bannerclick; evidence=reported |
| 27 | `literature_14` | `discovery.structured.exposure_status` | `/scenario/exposure_status_gt`<br>`/candidates/*/ground_truth/exposure_status_gt` | papers=dios_2014; evidence=reported |
| 28 | `literature_14` | `context.foreground_owner` | `/environment/foreground_owner`<br>`/observations/*/owner_context/foreground_owner` | papers=vlm_fuzz_2026; evidence=reported |
| 29 | `literature_14` | `discovery.structured.frame` | `/candidates/*/ios_raw/frame` | papers=ios_applications_testing_2018; evidence=inferred_from_local_source |
| 30 | `literature_14` | `discovery.visual.frame_gate_score` | `/observations/*/visual_representation/histogram_similarity` | papers=popsweeper_2024; evidence=reported |
| 31 | `literature_14` | `context.frame_id` | `/observations/*/visual_representation/frame_id` | papers=popsweeper_2024; evidence=reported |
| 32 | `literature_14` | `discovery.structured.geometry` | `/candidates/*/normalized/bounds_normalized`<br>`/candidates/*/normalized/z_or_layer` | papers=cookieverse_bannerclick,hotmobile_ad_policy_2018,ssldetecter_2019; evidence=mixed |
| 33 | `literature_14` | `discovery.structured.hierarchy` | `/candidates/*/normalized/hierarchy_path`<br>`/candidates/*/normalized/parent_id`<br>`/candidates/*/normalized/children_ids` | papers=cookieverse_bannerclick,dios_2014,hotmobile_ad_policy_2018,ssldetecter_2019,vlm_fuzz_2026; evidence=mixed |
| 34 | `literature_14` | `action.label_first_token` | `/candidates/*/ios_raw/label_first_token` | papers=dynamic_ios_privacy_2021; evidence=inferred_from_local_source |
| 35 | `literature_14` | `context.locale` | `/environment/locale` | papers=cookieverse_bannerclick; evidence=reported |
| 36 | `literature_14` | `context.method_id` | `/decision/method_id` | papers=abandon_all_hope_2024,dios_2014,freely_given_consent_2022,the_ok_is_not_enough_2023; evidence=mixed |
| 37 | `literature_14` | `discovery.structured.name_or_text` | `/candidates/*/normalized/name_or_text` | papers=abandon_all_hope_2024,cookieverse_bannerclick,dios_2014,freely_given_consent_2022,poker_sneaky_popups,ssldetecter_2019,tcf_aaid_2026,the_ok_is_not_enough_2023,vlm_fuzz_2026,whispertest_2025; evidence=mixed |
| 38 | `literature_14` | `verification.network_state` | `/observations/*/literature_signals/network_state` | papers=freely_given_consent_2022; evidence=reported |
| 39 | `literature_14` | `discovery.visual.normalized_tokens` | `/observations/*/literature_signals/normalized_tokens`<br>`/candidates/*/features/normalized_tokens` | papers=freely_given_consent_2022; evidence=reported |
| 40 | `literature_14` | `discovery.visual.ocr_text` | `/observations/*/visual_representation/ocr_items`<br>`/candidates/*/visual_raw/ocr_text` | papers=freely_given_consent_2022,poker_sneaky_popups,whispertest_2025; evidence=reported |
| 41 | `literature_14` | `discovery.visual.overlay_ratio` | `/observations/*/popup/overlay_ratio`<br>`/observations/*/visual_representation/shadow_mask_ratio` | papers=poker_sneaky_popups; evidence=reported |
| 42 | `literature_14` | `discovery.structured.owner` | `/candidates/*/normalized/owner` | papers=dios_2014,hotmobile_ad_policy_2018,poker_sneaky_popups,vlm_fuzz_2026; evidence=reported |
| 43 | `literature_14` | `verification.owner_after` | `/verification/technical_context_recovery/owner_after` | papers=hotmobile_ad_policy_2018; evidence=reported |
| 44 | `literature_14` | `verification.owner_context` | `/verification/technical_context_recovery/owner_context_restored` | papers=vlm_fuzz_2026; evidence=reported |
| 45 | `literature_14` | `context.page_context` | `/observations/*/owner_context/activity_or_page`<br>`/observations/*/owner_context/origin_or_frame` | papers=cookieverse_bannerclick; evidence=reported |
| 46 | `literature_14` | `verification.persisted_business_choice` | `/verification/persistence/business_choice_persisted`<br>`/observations/*/literature_signals/persistent_business_choice` | papers=tcf_aaid_2026; evidence=reported |
| 47 | `literature_14` | `verification.persisted_dialog_state` | `/verification/persistence/popup_absent_after_relaunch`<br>`/observations/*/literature_signals/dialog_present_after_relaunch` | papers=abandon_all_hope_2024; evidence=ppt_only_candidate |
| 48 | `literature_14` | `context.phase` | `/observations/*/phase` | papers=abandon_all_hope_2024,freely_given_consent_2022,the_ok_is_not_enough_2023; evidence=mixed |
| 49 | `literature_14` | `context.platform` | `/environment/platform` | papers=abandon_all_hope_2024,cookieverse_bannerclick,dios_2014,dynamic_ios_privacy_2021,freely_given_consent_2022,hotmobile_ad_policy_2018,ios_applications_testing_2018,poker_sneaky_popups,popsweeper_2024,ssldetecter_2019,tcf_aaid_2026,the_ok_is_not_enough_2023,vlm_fuzz_2026,whispertest_2025; evidence=mixed |
| 50 | `literature_14` | `action.policy_trace` | `/decision/rationale_trace`<br>`/decision/policy` | papers=dios_2014; evidence=reported |
| 51 | `literature_14` | `discovery.visual.popup_bbox` | `/observations/*/visual_representation/popup_bbox_pred`<br>`/observations/*/popup/bbox_gt` | papers=poker_sneaky_popups; evidence=reported |
| 52 | `literature_14` | `discovery.structured.popup_kind` | `/observations/*/popup/kind_gt`<br>`/scenario/popup_kind_gt` | papers=hotmobile_ad_policy_2018; evidence=reported |
| 53 | `literature_14` | `verification.popup_present_after` | `/verification/dismissal/semantic_popup_gone`<br>`/verification/persistence/popup_absent_after_relaunch` | papers=hotmobile_ad_policy_2018; evidence=reported |
| 54 | `literature_14` | `discovery.visual.popup_present_gt` | `/observations/*/popup/present_gt` | papers=popsweeper_2024; evidence=reported |
| 55 | `literature_14` | `discovery.visual.popup_score` | `/observations/*/visual_representation/popup_detector_confidence` | papers=popsweeper_2024; evidence=reported |
| 56 | `literature_14` | `action.protocol_event` | `/observations/*/owner_context/protocol_event` | papers=dios_2014; evidence=reported |
| 57 | `literature_14` | `action.rationale_trace` | `/decision/rationale_trace`<br>`/action_attempts/*/rationale_trace` | papers=tcf_aaid_2026,vlm_fuzz_2026,whispertest_2025; evidence=reported |
| 58 | `literature_14` | `discovery.structured.raw_element` | `/candidates/*/raw_ref` | papers=ios_applications_testing_2018; evidence=inferred_from_local_source |
| 59 | `literature_14` | `context.recording_id` | `/observations/*/visual_representation/recording_id` | papers=popsweeper_2024; evidence=reported |
| 60 | `literature_14` | `verification.replay_path` | `/observations/*/structured_representation/replay_path` | papers=poker_sneaky_popups; evidence=reported |
| 61 | `literature_14` | `discovery.structured.role_name_id_bundle` | `/candidates/*/normalized/role_or_class`<br>`/candidates/*/normalized/name_or_text`<br>`/candidates/*/normalized/stable_id`<br>`/candidates/*/normalized/owner` | papers=hotmobile_ad_policy_2018; evidence=reported |
| 62 | `literature_14` | `discovery.structured.role_or_class` | `/candidates/*/normalized/role_or_class` | papers=cookieverse_bannerclick,ssldetecter_2019,tcf_aaid_2026,vlm_fuzz_2026,whispertest_2025; evidence=mixed |
| 63 | `literature_14` | `discovery.visual.screenshot_uri` | `/observations/*/artifacts/screenshot` | papers=cookieverse_bannerclick,freely_given_consent_2022,poker_sneaky_popups,popsweeper_2024,tcf_aaid_2026,the_ok_is_not_enough_2023,vlm_fuzz_2026,whispertest_2025; evidence=reported |
| 64 | `literature_14` | `discovery.visual.size_emphasis` | `/candidates/*/visual_raw/size_emphasis` | papers=the_ok_is_not_enough_2023; evidence=reported |
| 65 | `literature_14` | `discovery.structured.source_channel` | `/candidates/*/source_channel` | papers=abandon_all_hope_2024; evidence=ppt_only_candidate |
| 66 | `literature_14` | `verification.state_signature` | `/observations/*/structured_representation/state_signature` | papers=poker_sneaky_popups; evidence=reported |
| 67 | `literature_14` | `verification.state_transition` | `/observations/*/literature_signals/state_transition` | papers=hotmobile_ad_policy_2018; evidence=reported |
| 68 | `literature_14` | `action.step_index` | `/action_attempts/*/attempt_index` | papers=dynamic_ios_privacy_2021; evidence=inferred_from_local_source |
| 69 | `literature_14` | `action.supported_actions` | `/candidates/*/normalized/supported_actions` | papers=cookieverse_bannerclick,tcf_aaid_2026; evidence=reported |
| 70 | `literature_14` | `action.tap_coordinate` | `/action_attempts/*/coordinate`<br>`/candidates/*/visual_raw/tap_coordinate` | papers=ios_applications_testing_2018,popsweeper_2024; evidence=mixed |
| 71 | `literature_14` | `action.target_candidate` | `/decision/selection/target_candidate_id_pred`<br>`/action_attempts/*/target_candidate_id` | papers=poker_sneaky_popups,tcf_aaid_2026; evidence=reported |
| 72 | `literature_14` | `action.target_label` | `/candidates/*/normalized/name_or_text` | papers=dios_2014; evidence=reported |
| 73 | `literature_14` | `discovery.structured.text_rule_match` | `/candidates/*/features/text_rule_match`<br>`/observations/*/literature_signals/text_rule_match` | papers=freely_given_consent_2022,the_ok_is_not_enough_2023; evidence=reported |
| 74 | `literature_14` | `discovery.visual.tfidf_vector` | `/observations/*/literature_signals/tfidf_vector_uri` | papers=freely_given_consent_2022; evidence=reported |
| 75 | `literature_14` | `context.timestamp` | `/observations/*/timestamp` | papers=popsweeper_2024; evidence=reported |
| 76 | `literature_14` | `verification.transition_graph` | `/observations/*/structured_representation/transition_graph_uri` | papers=poker_sneaky_popups; evidence=reported |
| 77 | `literature_14` | `verification.transition_path` | `/observations/*/structured_representation/replay_path` | papers=hotmobile_ad_policy_2018; evidence=reported |
| 78 | `literature_14` | `verification.transition_stack` | `/observations/*/structured_representation/transition_stack` | papers=vlm_fuzz_2026; evidence=reported |
| 79 | `literature_14` | `verification.transition_trace` | `/action_attempts`<br>`/observations/*/literature_signals/state_transition` | papers=poker_sneaky_popups,vlm_fuzz_2026; evidence=reported |
| 80 | `literature_14` | `context.traversal_state` | `/observations/*/structured_representation/traversal_state` | papers=ssldetecter_2019; evidence=inferred_from_local_source |
| 81 | `literature_14` | `verification.tree_diff` | `/observations/*/structured_representation/tree_diff_from_previous`<br>`/observations/*/structured_representation/host_tree_diff` | papers=vlm_fuzz_2026; evidence=reported |
| 82 | `literature_14` | `action.trigger_action` | `/scenario/trigger_action` | papers=poker_sneaky_popups; evidence=reported |
| 83 | `literature_14` | `context.trigger_context` | `/scenario/trigger_action`<br>`/observations/*/owner_context` | papers=hotmobile_ad_policy_2018; evidence=reported |
| 84 | `literature_14` | `discovery.visual.valid_close_target_gt` | `/candidates/*/ground_truth/is_valid_exit_target_gt` | papers=popsweeper_2024; evidence=reported |
| 85 | `literature_14` | `context.viewport` | `/environment/viewport_px`<br>`/observations/*/structured_representation/dom_raw/viewport_px` | papers=cookieverse_bannerclick; evidence=reported |
| 86 | `literature_14` | `discovery.structured.visible` | `/candidates/*/normalized/visible` | papers=cookieverse_bannerclick; evidence=reported |
| 87 | `literature_14` | `action.visual_mark_id` | `/candidates/*/visual_raw/visual_mark_id` | papers=vlm_fuzz_2026; evidence=reported |
| 88 | `literature_14` | `verification.visual_transition_proxy` | `/observations/*/visual_representation/screen_change_proxy`<br>`/verification/weak_proxies/screen_changed` | papers=whispertest_2025; evidence=reported |
| 89 | `literature_14` | `verification.weak_state_similarity` | `/observations/*/structured_representation/state_similarity`<br>`/verification/weak_proxies/interface_similarity` | papers=ssldetecter_2019; evidence=inferred_from_local_source |
| 90 | `literature_14` | `context.window_or_context` | `/environment/window_or_context`<br>`/observations/*/owner_context/window_or_context` | papers=ssldetecter_2019,vlm_fuzz_2026; evidence=mixed |
| 91 | `our_method` | `episode.episode_id` | `/identity/item_id` | label_source=collector; missing=reject_record; stage=episode_setup |
| 92 | `our_method` | `episode.scenario_id` | `/scenario/scenario_id` | label_source=experiment_designer; missing=reject_record; stage=episode_setup |
| 93 | `our_method` | `episode.method_id` | `/decision/method_id` | label_source=experiment_runner; missing=reject_record; stage=episode_setup |
| 94 | `our_method` | `episode.seed` | `/identity/randomization_seed` | label_source=experiment_runner; missing=reject_record; stage=episode_setup |
| 95 | `our_method` | `task_context.target_population` | `/scenario/target_population` | label_source=experiment_designer; missing=reject_record; stage=scenario_definition |
| 96 | `our_method` | `task_context.task_goal` | `/scenario/task_goal` | label_source=experiment_designer; missing=reject_record; stage=scenario_definition |
| 97 | `our_method` | `task_context.blocked_step` | `/scenario/blocked_step` | label_source=experiment_designer; missing=reject_record; stage=scenario_definition |
| 98 | `our_method` | `task_context.trigger_action` | `/scenario/trigger_action` | label_source=fixture_log_or_human_annotation; missing=unknown_only_with_provenance; stage=scenario_definition |
| 99 | `our_method` | `task_context.blocked_target_gt` | `/scenario/blocked_target_gt` | label_source=human_annotation_or_fixture_oracle; missing=unknown_only_with_annotation_reason; stage=scenario_definition |
| 100 | `our_method` | `task_context.task_postcondition_gt` | `/scenario/task_postcondition_gt` | label_source=experiment_designer_or_fixture_oracle; missing=reject_record; stage=scenario_definition |
| 101 | `our_method` | `task_context.scope_label` | `/scenario/scope_label` | label_source=human_annotation_with_policy; missing=unknown_requires_adjudication_before_evaluation; stage=scenario_definition |
| 102 | `our_method` | `task_context.popup_kind` | `/scenario/popup_kind_gt` | label_source=human_annotation; missing=unknown; stage=scenario_definition |
| 103 | `our_method` | `task_context.owner_type_gt` | `/scenario/popup_owner_type_gt` | label_source=fixture_or_reference_trace_or_adjudicated_annotation; missing=unknown_not_inferred_from_appearance; stage=scenario_definition |
| 104 | `our_method` | `task_context.action_topology` | `/scenario/action_topology_gt` | label_source=human_annotation_or_fixture; missing=unknown; stage=scenario_definition |
| 105 | `our_method` | `task_context.allowed_action_set_gt` | `/scenario/allowed_action_set_gt` | label_source=policy_review_and_human_annotation; missing=empty_array_means_no_safe_autonomous_action; stage=scenario_definition |
| 106 | `our_method` | `task_context.abstain_allowed_gt` | `/scenario/abstain_allowed_gt` | label_source=policy_review; missing=reject_record; stage=scenario_definition |
| 107 | `our_method` | `task_context.fixture_or_real_app` | `/identity/record_kind` | label_source=dataset_curator; missing=reject_record; stage=scenario_definition |
| 108 | `our_method` | `task_context.popup_expected_gt` | `/scenario/popup_expected_gt` | label_source=fixture_or_adjudicated_annotation; missing=unknown_requires_adjudication; stage=scenario_definition |
| 109 | `our_method` | `platform_context.platform` | `/environment/platform` | label_source=device_adapter; missing=reject_record; stage=episode_setup |
| 110 | `our_method` | `platform_context.os_version` | `/environment/os_version` | label_source=device_adapter; missing=tool_failure; stage=episode_setup |
| 111 | `our_method` | `platform_context.oem_or_device` | `/environment/device_model` | label_source=device_adapter; missing=tool_failure; stage=episode_setup |
| 112 | `our_method` | `platform_context.app_or_package` | `/environment/app_or_package` | label_source=device_adapter; missing=unknown_if_system_owner_else_tool_failure; stage=episode_setup |
| 113 | `our_method` | `platform_context.app_version` | `/environment/app_version` | label_source=device_adapter; missing=unknown_with_reason; stage=episode_setup |
| 114 | `our_method` | `platform_context.ui_framework` | `/environment/ui_framework` | label_source=fixture_metadata_or_human_annotation; missing=unknown; stage=episode_setup |
| 115 | `our_method` | `platform_context.locale` | `/environment/locale` | label_source=device_adapter; missing=tool_failure; stage=episode_setup |
| 116 | `our_method` | `platform_context.theme` | `/environment/theme` | label_source=device_adapter_or_experiment_runner; missing=unknown_with_reason; stage=episode_setup |
| 117 | `our_method` | `platform_context.orientation` | `/environment/orientation` | label_source=device_adapter; missing=tool_failure; stage=episode_setup |
| 118 | `our_method` | `platform_context.font_scale` | `/environment/font_scale` | label_source=device_adapter; missing=not_observable_with_reason; stage=episode_setup |
| 119 | `our_method` | `platform_context.assistive_technology` | `/assistive_technology/name` | label_source=device_adapter_and_run_config; missing=reject_record; stage=episode_setup |
| 120 | `our_method` | `platform_context.assistive_technology_config` | `/assistive_technology` | label_source=run_config_and_device_adapter; missing=not_collected_or_not_observable_with_reason; stage=episode_setup |
| 121 | `our_method` | `platform_context.driver_and_adapter_version` | `/environment/driver_and_adapter_version` | label_source=collector; missing=reject_record; stage=episode_setup |
| 122 | `our_method` | `platform_context.snapshot_state_id` | `/environment/reset_snapshot_id` | label_source=experiment_runner; missing=unknown_only_for_nonresettable_real_app; stage=episode_setup |
| 123 | `our_method` | `episode.started_at` | `/identity/started_at` | label_source=collector_clock; missing=tool_failure; stage=episode_setup |
| 124 | `our_method` | `episode.ended_at` | `/identity/ended_at` | label_source=collector_clock; missing=tool_failure_marks_episode_incomplete; stage=verification_summary |
| 125 | `our_method` | `platform_context.screen_reader_focus_order_uri` | `/observations/*/screen_reader_state/focus_order_uri` | label_source=verified_at_adapter_or_target_user_session; missing=not_observable_or_pending_capability_probe_or_not_collected; stage=observation_collection |
| 126 | `our_method` | `platform_context.screen_reader_utterance_trace_uri` | `/observations/*/screen_reader_state/utterance_trace_uri` | label_source=verified_at_adapter_or_target_user_session; missing=not_observable_or_pending_capability_probe_or_not_collected; stage=observation_collection |
| 127 | `our_method` | `capability_profile.structured_read_status` | `/capability_profile/structured_read_status` | label_source=target_device_capability_probe; missing=pending_capability_probe; stage=capability_probe |
| 128 | `our_method` | `capability_profile.action_execution_status` | `/capability_profile/action_execution_status` | label_source=target_device_capability_probe; missing=pending_capability_probe; stage=capability_probe |
| 129 | `our_method` | `capability_profile.screen_reader_focus_observability` | `/capability_profile/screen_reader_focus_observability` | label_source=target_device_at_probe; missing=pending_capability_probe; stage=capability_probe |
| 130 | `our_method` | `capability_profile.utterance_observability` | `/capability_profile/utterance_observability` | label_source=target_device_at_probe; missing=pending_capability_probe; stage=capability_probe |
| 131 | `our_method` | `capability_profile.technical_closed_loop_status` | `/capability_profile/technical_closed_loop_status` | label_source=derived_from_target_device_probe; missing=pending_capability_probe; stage=capability_probe |
| 132 | `our_method` | `capability_profile.accessible_closed_loop_status` | `/capability_profile/accessible_closed_loop_status` | label_source=derived_from_target_device_at_probe; missing=pending_capability_probe; stage=capability_probe |
| 133 | `our_method` | `capability_profile.evidence_refs` | `/capability_profile/evidence_refs` | label_source=collector; missing=empty_array_requires_all_capability_statuses_pending_capability_probe; stage=capability_probe |
| 134 | `our_method` | `observations[].observation_id` | `/observations/*/observation_id` | label_source=collector; missing=reject_observation; stage=observation_collection |
| 135 | `our_method` | `observations[].phase` | `/observations/*/phase` | label_source=experiment_runner; missing=reject_observation; stage=observation_collection |
| 136 | `our_method` | `observations[].timestamp` | `/observations/*/timestamp` | label_source=collector_clock; missing=tool_failure; stage=observation_collection |
| 137 | `our_method` | `observations[].foreground_owner` | `/observations/*/owner_context/foreground_owner` | label_source=platform_adapter; missing=not_observable_or_tool_failure_with_reason; stage=observation_collection |
| 138 | `our_method` | `observations[].window_or_context` | `/observations/*/owner_context/window_or_context` | label_source=platform_adapter; missing=not_observable_or_tool_failure_with_reason; stage=observation_collection |
| 139 | `our_method` | `observations[].protocol_event` | `/observations/*/owner_context/protocol_event` | label_source=protocol_adapter; missing=not_applicable_or_not_observable; stage=observation_collection |
| 140 | `our_method` | `observations[].tree_uri` | `/observations/*/artifacts/accessibility_tree` | label_source=platform_adapter; missing=not_observable_or_tool_failure_with_reason; stage=observation_collection |
| 141 | `our_method` | `observations[].screenshot_uri` | `/observations/*/artifacts/screenshot` | label_source=screen_capture_adapter; missing=tool_failure; stage=observation_collection |
| 142 | `our_method` | `observations[].tree_screenshot_sync_status` | `/observations/*/synchronization/tree_screenshot_sync_status` | label_source=derived_from_timestamps_and_ui_fingerprint; missing=tool_failure; stage=observation_collection |
| 143 | `our_method` | `observations[].ui_fingerprint` | `/observations/*/synchronization/ui_fingerprint` | label_source=collector; missing=not_collected; stage=observation_collection |
| 144 | `our_method` | `observations[].popup_present_gt` | `/observations/*/popup/present_gt` | label_source=fixture_or_adjudicated_human_annotation; missing=unknown_requires_adjudication; stage=annotation |
| 145 | `our_method` | `observations[].popup_present_pred` | `/observations/*/popup/present_pred` | label_source=method_prediction; missing=tool_failure; stage=popup_detection |
| 146 | `our_method` | `observations[].popup_bbox_gt` | `/observations/*/popup/bbox_gt` | label_source=fixture_or_adjudicated_human_annotation; missing=not_applicable_or_not_observable; stage=annotation |
| 147 | `our_method` | `observations[].popup_roi_pred` | `/observations/*/visual_representation/popup_roi` | label_source=method_prediction; missing=tool_failure; stage=visual_completion |
| 148 | `our_method` | `candidates[].candidate_id` | `/candidates/*/candidate_id` | label_source=normalizer; missing=reject_candidate; stage=normalization |
| 149 | `our_method` | `candidates[].observation_id` | `/candidates/*/observation_id` | label_source=normalizer; missing=reject_candidate; stage=normalization |
| 150 | `our_method` | `candidates[].source_channel` | `/candidates/*/source_channel` | label_source=normalizer; missing=reject_candidate; stage=normalization |
| 151 | `our_method` | `candidates[].owner` | `/candidates/*/normalized/owner` | label_source=source_channel_or_human_annotation; missing=unknown_with_field_provenance; stage=normalization |
| 152 | `our_method` | `candidates[].window_or_context` | `/candidates/*/normalized/window_or_context` | label_source=source_channel_or_human_annotation; missing=unknown_with_field_provenance; stage=normalization |
| 153 | `our_method` | `candidates[].role_or_class` | `/candidates/*/normalized/role_or_class` | label_source=source_channel_or_visual_model; missing=unknown_with_field_presence_mask; stage=normalization |
| 154 | `our_method` | `candidates[].name_or_text` | `/candidates/*/normalized/name_or_text` | label_source=source_channel_or_ocr_or_visual_model; missing=unknown_with_field_presence_mask; stage=normalization |
| 155 | `our_method` | `candidates[].value_or_hint` | `/candidates/*/normalized/value_or_hint` | label_source=source_channel_or_visual_model; missing=not_applicable_or_unknown_with_field_presence_mask; stage=normalization |
| 156 | `our_method` | `candidates[].stable_id` | `/candidates/*/normalized/stable_id` | label_source=source_channel; missing=not_observable_with_field_presence_mask; stage=normalization |
| 157 | `our_method` | `candidates[].supported_actions` | `/candidates/*/normalized/supported_actions` | label_source=source_channel_or_capability_inference; missing=empty_array_means_no_verified_supported_action; stage=normalization |
| 158 | `our_method` | `candidates[].state` | `/candidates/*/normalized/enabled`<br>`/candidates/*/normalized/clickable`<br>`/candidates/*/normalized/hittable`<br>`/candidates/*/normalized/visible`<br>`/candidates/*/normalized/focusable`<br>`/candidates/*/normalized/checkable`<br>`/candidates/*/normalized/checked_or_toggle`<br>`/candidates/*/normalized/selected` | label_source=source_channel_or_visual_model; missing=each_member_uses_not_observable_or_not_applicable_in_field_presence_mask; stage=normalization |
| 159 | `our_method` | `candidates[].bounds_normalized` | `/candidates/*/normalized/bounds_normalized` | label_source=source_channel_or_visual_model; missing=not_observable_with_field_presence_mask; stage=normalization |
| 160 | `our_method` | `candidates[].hierarchy_path` | `/candidates/*/normalized/hierarchy_path` | label_source=structured_source; missing=not_applicable_for_visual_only_or_not_observable; stage=normalization |
| 161 | `our_method` | `candidates[].field_presence_mask` | `/candidates/*/presence` | label_source=normalizer; missing=reject_candidate; stage=normalization |
| 162 | `our_method` | `candidates[].field_provenance` | `/candidates/*/field_provenance` | label_source=normalizer; missing=reject_candidate; stage=normalization |
| 163 | `our_method` | `candidates[].raw_ref` | `/candidates/*/raw_ref` | label_source=normalizer; missing=tool_failure; stage=normalization |
| 164 | `our_method` | `candidates[].android_raw` | `/candidates/*/android_raw` | label_source=android_adapter; missing=not_applicable_or_tool_failure; stage=raw_capture |
| 165 | `our_method` | `candidates[].ios_raw` | `/candidates/*/ios_raw` | label_source=verified_target_ios_adapter; missing=pending_capability_probe_or_not_applicable_or_tool_failure; stage=raw_capture |
| 166 | `our_method` | `candidates[].dom_raw` | `/candidates/*/dom_raw` | label_source=dom_adapter; missing=not_applicable_or_tool_failure; stage=raw_capture |
| 167 | `our_method` | `candidates[].visual_raw` | `/candidates/*/visual_raw` | label_source=ocr_detector_or_frozen_vlm; missing=not_applicable_or_tool_failure; stage=visual_completion |
| 168 | `our_method` | `candidates[].matched_cross_channel_candidate_ids` | `/candidates/*/matched_cross_channel_candidate_ids` | label_source=matcher; missing=empty_array_means_unmatched; stage=cross_channel_matching |
| 169 | `our_method` | `candidates[].action_semantics_gt` | `/candidates/*/ground_truth/action_semantics_gt` | label_source=adjudicated_human_annotation_or_fixture_oracle; missing=unknown_requires_adjudication; stage=annotation |
| 170 | `our_method` | `candidates[].is_valid_close_target_gt` | `/candidates/*/ground_truth/is_valid_exit_target_gt` | label_source=adjudicated_human_annotation_or_fixture_oracle; missing=unknown_requires_adjudication; stage=annotation |
| 171 | `our_method` | `candidates[].exposure_status_gt` | `/candidates/*/ground_truth/exposure_status_gt` | label_source=adjudicated_annotation_with_evidence_rule; missing=unknown; stage=annotation |
| 172 | `our_method` | `candidates[].actionability_features` | `/candidates/*/features` | label_source=scorer_input_pipeline; missing=missing_component_must_be_explicit_and_masked; stage=gate_scoring |
| 173 | `our_method` | `candidates[].actionability_score_pre_visual` | `/candidates/*/scores/actionability_score_pre_visual` | label_source=trained_scorer; missing=not_applicable_or_tool_failure; stage=gate_pre_visual |
| 174 | `our_method` | `candidates[].actionability_score_post_visual` | `/candidates/*/scores/actionability_score_post_visual` | label_source=trained_scorer; missing=not_applicable_or_tool_failure; stage=gate_post_visual |
| 175 | `our_method` | `gate.top1_candidate_id_pre_visual` | `/decision/gate/top1_candidate_id` | label_source=trained_scorer; missing=not_applicable_if_no_candidate; stage=gate_pre_visual |
| 176 | `our_method` | `gate.top1_score_pre_visual` | `/decision/gate/top1_score` | label_source=trained_scorer; missing=not_applicable_if_no_candidate; stage=gate_pre_visual |
| 177 | `our_method` | `gate.top2_score_pre_visual` | `/decision/gate/top2_score` | label_source=trained_scorer; missing=not_applicable_if_fewer_than_two_candidates; stage=gate_pre_visual |
| 178 | `our_method` | `gate.score_threshold_tau` | `/decision/gate/threshold_tau` | label_source=frozen_calibration_config; missing=reject_episode; stage=gate_pre_visual |
| 179 | `our_method` | `gate.margin_pre_visual` | `/decision/gate/margin` | label_source=derived_deterministically; missing=not_applicable_if_fewer_than_two_candidates; stage=gate_pre_visual |
| 180 | `our_method` | `gate.margin_threshold_delta` | `/decision/gate/margin_delta` | label_source=frozen_calibration_config; missing=reject_episode; stage=gate_pre_visual |
| 181 | `our_method` | `gate.owner_context_known_and_consistent` | `/decision/gate/owner_consistent` | label_source=derived_from_platform_context_and_candidate; missing=false_when_unknown_with_gap_reason_owner_mismatch; stage=gate_pre_visual |
| 182 | `our_method` | `gate.action_supported_and_executable` | `/decision/gate/action_executable` | label_source=derived_from_candidate_and_capability_profile; missing=false_when_unverified; stage=gate_pre_visual |
| 183 | `our_method` | `gate.action_in_low_risk_policy` | `/decision/gate/low_risk_policy_satisfied` | label_source=policy_engine; missing=false_when_unknown; stage=gate_pre_visual |
| 184 | `our_method` | `gate.capture_fresh_and_synchronized` | `/decision/gate/capture_fresh_and_synchronized` | label_source=derived_from_sync_status; missing=false_on_tool_failure_or_unknown; stage=gate_pre_visual |
| 185 | `our_method` | `gate.structured_sufficient` | `/decision/gate/structured_sufficient` | label_source=derived_deterministically_from_gate_contract; missing=false_on_any_unresolved_condition; stage=gate_pre_visual |
| 186 | `our_method` | `gate.gap_reasons` | `/decision/gate/gap_reasons` | label_source=gate; missing=empty_array_only_when_structured_sufficient=true; stage=gate_pre_visual |
| 187 | `our_method` | `gate.visual_fallback_triggered` | `/decision/gate/visual_fallback_triggered`<br>`/decision/visual_fallback/used` | label_source=gate; missing=false_only_with_gate_trace; stage=visual_completion |
| 188 | `our_method` | `gate.final_candidate_id` | `/decision/gate/final_candidate_id`<br>`/decision/selection/target_candidate_id_pred` | label_source=trained_scorer_and_policy; missing=not_applicable_if_abstained; stage=gate_post_visual |
| 189 | `our_method` | `gate.final_score` | `/decision/gate/final_score` | label_source=trained_scorer; missing=not_applicable_if_abstained; stage=gate_post_visual |
| 190 | `our_method` | `gate.final_state` | `/decision/gate/final_state` | label_source=gate_and_policy_engine; missing=reject_episode; stage=gate_post_visual |
| 191 | `our_method` | `gate.scorer_version` | `/decision/gate/scorer_version` | label_source=model_registry; missing=reject_episode; stage=gate_scoring |
| 192 | `our_method` | `gate.calibration_version` | `/decision/gate/calibration_version` | label_source=model_registry; missing=reject_episode; stage=gate_scoring |
| 193 | `our_method` | `decision.allowed_action_policy_version` | `/decision/policy/allowed_action_policy_version` | label_source=policy_registry; missing=reject_episode; stage=policy_decision |
| 194 | `our_method` | `decision.action_semantics_pred` | `/decision/selection/action_semantics_pred` | label_source=method_prediction; missing=not_applicable_if_abstained; stage=policy_decision |
| 195 | `our_method` | `decision.target_candidate_id_pred` | `/decision/selection/target_candidate_id_pred` | label_source=method_prediction; missing=not_applicable_if_abstained; stage=policy_decision |
| 196 | `our_method` | `decision.execution_channel` | `/decision/selection/execution_channel_pred` | label_source=policy_engine; missing=not_applicable_if_abstained; stage=policy_decision |
| 197 | `our_method` | `decision.confidence` | `/decision/selection/confidence` | label_source=method_prediction; missing=tool_failure; stage=policy_decision |
| 198 | `our_method` | `decision.abstain` | `/decision/abstention/abstained` | label_source=policy_engine; missing=true_on_unresolved_safety_or_observability; stage=policy_decision |
| 199 | `our_method` | `decision.abstain_reasons` | `/decision/abstention/reason` | label_source=gate_and_policy_engine; missing=empty_array_invalid_when_abstain=true; stage=policy_decision |
| 200 | `our_method` | `decision.rationale_trace` | `/decision/rationale_trace` | label_source=method_runtime; missing=tool_failure; stage=policy_decision |
| 201 | `our_method` | `action_attempts[].attempt_id` | `/action_attempts/*/attempt_id` | label_source=executor; missing=not_applicable_if_abstained; stage=execution |
| 202 | `our_method` | `action_attempts[].attempt_index` | `/action_attempts/*/attempt_index` | label_source=executor; missing=reject_attempt; stage=execution |
| 203 | `our_method` | `action_attempts[].observation_id` | `/action_attempts/*/observation_before_id` | label_source=executor; missing=reject_attempt; stage=execution |
| 204 | `our_method` | `action_attempts[].action_semantics_pred` | `/action_attempts/*/action_semantics` | label_source=method_prediction; missing=reject_attempt; stage=execution |
| 205 | `our_method` | `action_attempts[].target_candidate_id_pred` | `/action_attempts/*/target_candidate_id` | label_source=method_prediction; missing=not_applicable_only_for_protocol_action_without_candidate; stage=execution |
| 206 | `our_method` | `action_attempts[].execution_channel` | `/action_attempts/*/execution_channel` | label_source=policy_engine_and_executor; missing=reject_attempt; stage=execution |
| 207 | `our_method` | `action_attempts[].confidence` | `/action_attempts/*/confidence` | label_source=method_prediction; missing=tool_failure; stage=execution |
| 208 | `our_method` | `action_attempts[].rationale_trace` | `/action_attempts/*/rationale_trace` | label_source=method_runtime; missing=tool_failure; stage=execution |
| 209 | `our_method` | `action_attempts[].locator_or_coordinate` | `/action_attempts/*/selector_or_locator`<br>`/action_attempts/*/coordinate` | label_source=executor; missing=not_applicable_only_for_protocol_callback_else_tool_failure; stage=execution |
| 210 | `our_method` | `action_attempts[].command_delivered` | `/action_attempts/*/command_delivered` | label_source=executor; missing=tool_failure; stage=execution |
| 211 | `our_method` | `action_attempts[].execution_error` | `/action_attempts/*/execution_error` | label_source=executor; missing=not_applicable_when_no_error; stage=execution |
| 212 | `our_method` | `action_attempts[].latency_ms` | `/action_attempts/*/latency_ms` | label_source=monotonic_clock; missing=tool_failure; stage=execution |
| 213 | `our_method` | `safety.sensitive_context_flags` | `/verification/safety/sensitive_context_flags` | label_source=policy_engine_and_adjudicated_ground_truth; missing=unknown_semantics; stage=safety_screening |
| 214 | `our_method` | `safety.safe_exit_exists_gt` | `/verification/safety/safe_exit_exists_gt` | label_source=policy_review_and_fixture_or_adjudicated_annotation; missing=unknown_requires_abstain; stage=annotation |
| 215 | `our_method` | `safety.policy_violation` | `/verification/safety/policy_violation` | label_source=derived_from_attempts_and_policy; missing=unknown_requires_adjudication; stage=safety_outcome |
| 216 | `our_method` | `safety.false_intervention` | `/verification/safety/false_intervention` | label_source=derived_from_popup_ground_truth_and_attempts; missing=unknown_requires_adjudication; stage=safety_outcome |
| 217 | `our_method` | `safety.harmful_action` | `/verification/safety/harmful_action` | label_source=adjudicated_outcome; missing=unknown_requires_adjudication; stage=safety_outcome |
| 218 | `our_method` | `safety.side_effect_detected` | `/verification/safety/side_effect_detected` | label_source=fixture_oracle_or_post_action_annotation; missing=unknown_with_evidence_status; stage=safety_outcome |
| 219 | `our_method` | `safety.cross_app_jump` | `/verification/safety/cross_app_jump` | label_source=owner_context_trace; missing=unknown_if_owner_not_observable; stage=safety_outcome |
| 220 | `our_method` | `safety.retry_budget` | `/verification/safety/retry_budget` | label_source=frozen_policy_config; missing=reject_episode; stage=policy_decision |
| 221 | `our_method` | `safety.retry_count` | `/verification/safety/retry_count` | label_source=derived_from_action_attempts; missing=zero_when_no_retry; stage=execution |
| 222 | `our_method` | `safety.retry_exhausted` | `/verification/safety/retry_exhausted` | label_source=derived_from_action_attempts_and_retry_budget; missing=false_when_no_retry; stage=safety_outcome |
| 223 | `our_method` | `outcome.visual_popup_gone` | `/verification/dismissal/visual_popup_gone` | label_source=visual_diff_or_adjudicated_annotation; missing=not_observable_or_tool_failure; stage=verification_D |
| 224 | `our_method` | `outcome.semantic_popup_gone` | `/verification/dismissal/semantic_popup_gone` | label_source=platform_or_protocol_observation; missing=not_observable_or_tool_failure; stage=verification_D |
| 225 | `our_method` | `outcome.D_dismissal` | `/verification/dismissal/D` | label_source=derived_deterministically; missing=false_for_success_claim_if_either_conjunct_unobserved; stage=verification_D |
| 226 | `our_method` | `outcome.owner_context_restored` | `/verification/technical_context_recovery/owner_context_restored` | label_source=platform_adapter_and_reference_context; missing=not_observable_or_tool_failure_blocks_success_claim; stage=verification_C_tech |
| 227 | `our_method` | `outcome.blocked_target_operable` | `/verification/technical_context_recovery/blocked_target_operable` | label_source=safe_nonmutating_probe_or_fixture_oracle; missing=not_observable_or_tool_failure_blocks_success_claim; stage=verification_C_tech |
| 228 | `our_method` | `outcome.C_tech` | `/verification/technical_context_recovery/C_tech` | label_source=derived_deterministically; missing=false_for_success_claim_if_any_conjunct_unobserved; stage=verification_C_tech |
| 229 | `our_method` | `outcome.screen_reader_focus_before` | `/verification/accessible_context_recovery/focus_before` | label_source=verified_at_adapter_or_target_user_session; missing=not_observable_or_pending_capability_probe; stage=verification_C_a11y |
| 230 | `our_method` | `outcome.screen_reader_focus_after` | `/verification/accessible_context_recovery/focus_after` | label_source=verified_at_adapter_or_target_user_session; missing=not_observable_or_pending_capability_probe; stage=verification_C_a11y |
| 231 | `our_method` | `outcome.focus_restored_to_blocked_target_or_successor` | `/verification/accessible_context_recovery/focus_restored_to_blocked_target_or_successor` | label_source=derived_from_verified_focus_trace_or_target_user_validation; missing=not_observable_or_pending_capability_probe; stage=verification_C_a11y |
| 232 | `our_method` | `outcome.utterance_before` | `/verification/accessible_context_recovery/utterance_before` | label_source=verified_at_adapter_or_target_user_session; missing=not_observable_or_pending_capability_probe; stage=verification_C_a11y |
| 233 | `our_method` | `outcome.utterance_after` | `/verification/accessible_context_recovery/utterance_after` | label_source=verified_at_adapter_or_target_user_session; missing=not_observable_or_pending_capability_probe; stage=verification_C_a11y |
| 234 | `our_method` | `outcome.spoken_context_consistent` | `/verification/accessible_context_recovery/spoken_context_consistent` | label_source=adjudicated_trace_or_target_user_validation; missing=not_observable_or_pending_capability_probe; stage=verification_C_a11y |
| 235 | `our_method` | `outcome.C_a11y` | `/verification/accessible_context_recovery/C_a11y` | label_source=derived_from_C_tech_focus_and_observable_utterance; missing=not_observable; never substitute C_tech; stage=verification_C_a11y |
| 236 | `our_method` | `outcome.task_postcondition_satisfied` | `/verification/task/task_postcondition_satisfied` | label_source=fixture_oracle_or_adjudicated_business_state; missing=not_observable_or_tool_failure_blocks_success_claim; stage=verification_T |
| 237 | `our_method` | `outcome.T_task_postcondition` | `/verification/task/T` | label_source=derived_deterministically; missing=false_for_success_claim_if_unobserved; stage=verification_T |
| 238 | `our_method` | `outcome.verified_technical_task_recovery` | `/verification/metrics/VTR_tech` | label_source=derived_as_D_and_C_tech_and_T; missing=false_for_success_claim_if_any_conjunct_unobserved; stage=verification_summary |
| 239 | `our_method` | `outcome.accessible_verified_task_recovery` | `/verification/metrics/A_VTR` | label_source=derived_as_D_and_C_a11y_and_T; missing=not_observable; never infer from VTR-tech; stage=verification_summary |
| 240 | `our_method` | `outcome.extra_screen_reader_navigation_steps` | `/verification/metrics/extra_navigation_steps_after_dismissal` | label_source=at_trace_or_target_user_session; missing=not_observable_or_not_collected; stage=verification_C_a11y |
| 241 | `our_method` | `outcome.target_user_validation` | `/verification/accessible_context_recovery/target_user_validation` | label_source=consented_target_user_session; missing=not_collected_means_no_user_experience_claim; stage=user_evaluation |
| 242 | `our_method` | `outcome.abstained` | `/decision/abstention/abstained` | label_source=derived_from_decision_and_attempts; missing=tool_failure; stage=verification_summary |
| 243 | `our_method` | `outcome.handoff_reason` | `/decision/abstention/reason` | label_source=policy_engine_and_feedback_adapter; missing=not_applicable_when_no_handoff; stage=feedback_handoff |
| 244 | `our_method` | `feedback.status` | `/feedback/status` | label_source=feedback_adapter; missing=tool_failure; stage=feedback_handoff |
| 245 | `our_method` | `feedback.message` | `/feedback/message` | label_source=feedback_adapter; missing=not_delivered_with_reason; stage=feedback_handoff |
| 246 | `our_method` | `feedback.handoff_options` | `/feedback/handoff_options` | label_source=policy_engine_and_feedback_adapter; missing=empty_array_requires_explicit_no_available_handoff_reason; stage=feedback_handoff |
| 247 | `our_method` | `feedback.delivered` | `/feedback/delivered` | label_source=verified_feedback_adapter; missing=not_observable_or_tool_failure; stage=feedback_handoff |
| 248 | `our_method` | `observability.field_status` | `/observability/field_status` | label_source=collector_and_capability_profile; missing=reject_record; stage=provenance_and_quality |
| 249 | `our_method` | `observability.measurement_channel` | `/observability/measurement_channel` | label_source=collector; missing=unknown_with_field_status; stage=provenance_and_quality |
| 250 | `our_method` | `provenance.source_artifact_refs` | `/provenance/source_artifacts` | label_source=collector; missing=empty_array_invalid; stage=provenance_and_quality |
| 251 | `our_method` | `provenance.raw_capture_hashes` | `/provenance/raw_capture_hashes` | label_source=collector; missing=tool_failure; stage=provenance_and_quality |
| 252 | `our_method` | `provenance.collector_and_model_versions` | `/provenance/collector_and_model_versions` | label_source=runtime_registry; missing=reject_record; stage=provenance_and_quality |
| 253 | `our_method` | `provenance.annotation_records` | `/annotations`<br>`/provenance/annotation_record_ids` | label_source=annotation_system; missing=empty_array_only_for_fully_automatic_non_ground_truth_fields; stage=annotation |
| 254 | `our_method` | `provenance.episode_evidence_uris` | `/provenance/episode_evidence_uris` | label_source=collector_and_verifier; missing=empty_array_blocks_verified_success_claim; stage=verification_summary |
| 255 | `our_method` | `provenance.evidence_level` | `/provenance/evidence_level` | label_source=derived_from_evidence_and_capability_profile; missing=unverified; stage=provenance_and_quality |

## 进阶 Recovery 兼容字段

这些字段仅为 schema 兼容性保留，不属于 v1 成功定义。

| 字段 | Canonical pointer | 存储值 | v1 状态 |
|---|---|---|---|
| `D` | `/verification/dismissal/D` | `null` | `not_applicable` |
| `C_tech` | `/verification/technical_context_recovery/C_tech` | `null` | `not_applicable` |
| `C_a11y` | `/verification/accessible_context_recovery/C_a11y` | `null` | `not_applicable` |
| `T` | `/verification/task/T` | `null` | `not_applicable` |
| `VTR_tech` | `/verification/metrics/VTR_tech` | `null` | `not_applicable` |
| `A_VTR` | `/verification/metrics/A_VTR` | `null` | `not_applicable` |

## 公开输入与机器校验

输入：`schema/field_catalog.json`、`schema/source_to_item_crosswalk.json`、`data/item.template.json` 与 `data/items.schema-fixture.jsonl`。

```bash
../../.venv/bin/python3 scripts/build_item_union_example.py --check
```
