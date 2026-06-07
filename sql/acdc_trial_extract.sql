SELECT
    o.observation_id,
    d.dataset_id,
    CAST(d.dataset_id AS TEXT) || ':' || CAST(o.subject AS TEXT) AS participant_id,
    o.subject AS subject_raw,
    CAST(NULLIF(TRIM(CAST(o.block AS TEXT)), '') AS INTEGER) AS block_raw,
    CAST(o.block AS TEXT) AS block_source_raw,
    o.trial AS trial_raw,
    o.within_id,
    d.study_id,
    p.publication_id,
    p.publication_code,
    t.task_id,
    t.task_name AS task_name_raw,
    CASE
        WHEN LOWER(t.task_name) LIKE '%stroop%' THEN 'Stroop'
        WHEN LOWER(t.task_name) LIKE '%flanker%' THEN 'Flanker'
        WHEN LOWER(t.task_name) LIKE '%simon%' THEN 'Simon'
        ELSE NULL
    END AS task_family,
    CASE
        WHEN LOWER(t.task_name) LIKE '%stroop%' THEN 'interference'
        WHEN LOWER(t.task_name) LIKE '%simon%' THEN 'interference'
        WHEN LOWER(t.task_name) LIKE '%flanker%' THEN 'conflict'
        ELSE NULL
    END AS control_cost_type,
    o.congruency AS congruency_raw,
    CASE LOWER(TRIM(CAST(o.congruency AS TEXT)))
        WHEN '1' THEN 'congruent'
        WHEN 'congruent' THEN 'congruent'
        WHEN '2' THEN 'incongruent'
        WHEN 'incongruent' THEN 'incongruent'
        WHEN '3' THEN 'neutral'
        WHEN 'neutral' THEN 'neutral'
        ELSE 'unknown'
    END AS congruency,
    o.accuracy AS accuracy_raw,
    CASE
        WHEN o.accuracy = 1 THEN 1
        WHEN o.accuracy = 0 THEN 0
        ELSE NULL
    END AS correct,
    o.rt AS rt_seconds_raw,
    CASE WHEN o.rt IS NULL THEN NULL ELSE o.rt * 1000.0 END AS rt_ms,
    d.time_limit AS time_limit_raw,
    'undocumented_in_acdc_schema' AS time_limit_unit,
    w.within_description,
    d.github AS source_url
FROM observation_table AS o
JOIN dataset_table AS d ON d.dataset_id = o.dataset_id
JOIN task_table AS t ON t.task_id = d.task_id
JOIN study_table AS s ON s.study_id = d.study_id
JOIN publication_table AS p ON p.publication_id = s.publication_id
LEFT JOIN within_table AS w
    ON w.within_id = o.within_id
    AND w.dataset_id = o.dataset_id
WHERE
    LOWER(t.task_name) LIKE '%stroop%'
    OR LOWER(t.task_name) LIKE '%flanker%'
    OR LOWER(t.task_name) LIKE '%simon%'
ORDER BY
    d.dataset_id,
    o.subject,
    o.block,
    o.trial,
    o.observation_id;
