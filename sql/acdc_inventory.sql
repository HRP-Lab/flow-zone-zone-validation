SELECT
    d.dataset_id,
    d.study_id,
    p.publication_id,
    p.publication_code,
    p.apa_reference,
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
    d.n_participants AS declared_participants,
    d.n_blocks AS declared_blocks,
    d.n_trials AS declared_trials,
    d.neutral_trials,
    d.time_limit,
    d.mean_dataset_rt,
    d.mean_dataset_acc,
    d.mean_age,
    d.percentage_female,
    d.n_members,
    d.number_within_conditions,
    d.group_description,
    d.data_excl,
    d.github AS source_url,
    COUNT(o.observation_id) AS observed_trials,
    COUNT(DISTINCT o.subject) AS observed_participants,
    COUNT(
        DISTINCT NULLIF(TRIM(CAST(o.block AS TEXT)), '')
    ) AS observed_blocks,
    SUM(CASE WHEN o.rt IS NOT NULL THEN 1 ELSE 0 END) AS rt_present,
    SUM(CASE WHEN o.accuracy IS NOT NULL THEN 1 ELSE 0 END) AS accuracy_present,
    SUM(
        CASE
            WHEN LOWER(TRIM(CAST(o.congruency AS TEXT))) IN ('1', 'congruent')
                THEN 1
            ELSE 0
        END
    ) AS congruent_trials,
    SUM(
        CASE
            WHEN LOWER(TRIM(CAST(o.congruency AS TEXT))) IN ('2', 'incongruent')
                THEN 1
            ELSE 0
        END
    ) AS incongruent_trials,
    SUM(
        CASE
            WHEN LOWER(TRIM(CAST(o.congruency AS TEXT))) IN ('3', 'neutral')
                THEN 1
            ELSE 0
        END
    ) AS neutral_observations,
    SUM(
        CASE
            WHEN o.congruency IS NULL
                OR LOWER(TRIM(CAST(o.congruency AS TEXT))) NOT IN (
                    '1',
                    'congruent',
                    '2',
                    'incongruent',
                    '3',
                    'neutral'
                )
                THEN 1
            ELSE 0
        END
    ) AS unknown_congruency_trials,
    CASE
        WHEN COUNT(o.observation_id) = 0 THEN NULL
        ELSE 1.0 - (
            CAST(SUM(CASE WHEN o.rt IS NOT NULL THEN 1 ELSE 0 END) AS REAL)
            / COUNT(o.observation_id)
        )
    END AS rt_missing_fraction,
    CASE
        WHEN COUNT(o.observation_id) = 0 THEN NULL
        ELSE 1.0 - (
            CAST(SUM(CASE WHEN o.accuracy IS NOT NULL THEN 1 ELSE 0 END) AS REAL)
            / COUNT(o.observation_id)
        )
    END AS accuracy_missing_fraction
FROM dataset_table AS d
JOIN task_table AS t ON t.task_id = d.task_id
JOIN study_table AS s ON s.study_id = d.study_id
JOIN publication_table AS p ON p.publication_id = s.publication_id
LEFT JOIN observation_table AS o ON o.dataset_id = d.dataset_id
GROUP BY
    d.dataset_id,
    d.study_id,
    p.publication_id,
    p.publication_code,
    p.apa_reference,
    t.task_id,
    t.task_name,
    d.n_participants,
    d.n_blocks,
    d.n_trials,
    d.neutral_trials,
    d.time_limit,
    d.mean_dataset_rt,
    d.mean_dataset_acc,
    d.mean_age,
    d.percentage_female,
    d.n_members,
    d.number_within_conditions,
    d.group_description,
    d.data_excl,
    d.github
ORDER BY t.task_name, d.dataset_id;
