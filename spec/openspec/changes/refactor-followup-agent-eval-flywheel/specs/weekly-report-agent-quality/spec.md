## ADDED Requirements

### Requirement: Seven-layer follow-up Agent eval flywheel
The follow-up Agent evaluation system SHALL separate task definition, success criteria, layered datasets, environment/executor, evaluators, reporting/gates, and feedback into distinct stages, and SHALL treat the evaluated task as authorized weekly-report follow-up rather than weekly-report generation.

#### Scenario: Success criteria are task-specific
- **WHEN** a follow-up case asks what was completed this week
- **THEN** the evaluator SHALL NOT require the answer to mention unrelated source keywords such as 越权, pageSize, or Token in order to pass

#### Scenario: Environment gap is not a failure
- **WHEN** a case requires image input, like/dislike APIs, memory isolation across sessions, or permission mutation that the executor did not actually perform
- **THEN** the automatic verdict SHALL be `待复测` with an explicit missing-environment reason, and the case SHALL be excluded from pass rate and mean quality score

### Requirement: Contract-and-critical scoring
The system SHALL score each executable case with independent contract, critical, and quality results. Critical failures SHALL fail the case regardless of quality score. Low completeness SHALL NOT by itself produce a redline or an automatic fail when the answer is on-topic and non-fabricating.

#### Scenario: On-topic answer with low keyword recall
- **WHEN** the Agent answer discusses the selected report period and does not fabricate unknown facts, but keyword overlap with the must-list is below 70%
- **THEN** completeness MAY be medium and the verdict SHALL be `通过` or `人工复核`, not `失败-红线`

#### Scenario: Historical privilege narrative is not a leak
- **WHEN** the source weekly report describes a past cross-tenant bug that was fixed, and the Agent retells that narrative
- **THEN** the permission evaluator SHALL NOT record a SEC redline

#### Scenario: Unknown-fact refusal
- **WHEN** a case asks for facts absent from the authorized reports and the Agent refuses or says the source does not contain them
- **THEN** the case SHALL NOT fail for missing must-list coverage of those absent facts

### Requirement: Dataset iteration loop
The system SHALL version the case set and SHALL accept human overrides plus automatic skip/fail reasons as inputs to add, relax, or split cases.

#### Scenario: Rescore without rerunning the Agent
- **WHEN** historical execution evidence exists in the execution-record sheet
- **THEN** the system SHALL re-evaluate using the current scorer version and overwrite automatic verdicts while preserving original Agent answers

#### Scenario: Multi-author dataset unlocks executable cases
- **WHEN** weekly reports from at least three authorized authors exist for the same period and the executor attaches them
- **THEN** 多人同项目 and 多人冲突陈述 SHALL be scored instead of `待复测`

#### Scenario: Empty attachment is an executed environment
- **WHEN** a 空数据 case is executed with no weekly-report attachments
- **THEN** the verdict SHALL NOT be `待复测` solely for missing source text, and fabricating a generic weekly report SHALL lower faithfulness
