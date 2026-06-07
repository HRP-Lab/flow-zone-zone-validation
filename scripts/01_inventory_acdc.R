#!/usr/bin/env Rscript

source("scripts/acdc_helpers.R")

flags <- parse_flags(commandArgs(trailingOnly = TRUE))
database_path <- flag_value(flags, "database", "data/raw/acdc/acdc.db")
output_file <- flag_value(
  flags,
  "output",
  "data/interim/acdc_task_inventory.csv"
)
sql_path <- flag_value(flags, "sql", "sql/acdc_inventory.sql")
discrepancy_path <- flag_value(
  flags,
  "discrepancy-report",
  "reports/acdc_schema_discrepancy.md"
)

conn <- connect_validated_acdc(
  database_path,
  discrepancy_path = discrepancy_path
)
on.exit(DBI::dbDisconnect(conn), add = TRUE)

inventory <- DBI::dbGetQuery(conn, read_sql(sql_path))
inventory$suitable_target_task <- !is.na(inventory$task_family)
inventory$suitable_dynamics <- (
  inventory$suitable_target_task
  & inventory$observed_trials >= 80
  & inventory$rt_present > 0
  & inventory$accuracy_present > 0
)
inventory$suitable_control_cost <- (
  inventory$suitable_target_task
  & inventory$congruent_trials > 0
  & inventory$incongruent_trials > 0
)
inventory$suitable_post_error_slowing <- (
  inventory$suitable_target_task
  & inventory$accuracy_present > 0
  & inventory$observed_trials >= 80
)

ensure_parent(output_file)
readr::write_csv(inventory, output_file, na = "")

unmatched <- unique(inventory$task_name_raw[is.na(inventory$task_family)])
unmatched_path <- file.path(dirname(output_file), "acdc_unmatched_tasks.csv")
readr::write_csv(
  data.frame(task_name_raw = sort(unmatched)),
  unmatched_path,
  na = ""
)

message("Wrote ", nrow(inventory), " dataset inventory rows to ", output_file)
message("Wrote unmatched task names to ", unmatched_path)
