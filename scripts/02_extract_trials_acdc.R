#!/usr/bin/env Rscript

source("scripts/acdc_helpers.R")

flags <- parse_flags(commandArgs(trailingOnly = TRUE))
database_path <- flag_value(flags, "database", "data/raw/acdc/acdc.db")
csv_output <- flag_value(
  flags,
  "csv-output",
  "data/interim/acdc_trial_extract.csv.gz"
)
parquet_output <- flag_value(
  flags,
  "parquet-output",
  "data/interim/acdc_trial_extract.parquet"
)
chunk_size <- as.integer(flag_value(flags, "chunk-size", "100000"))
sql_path <- flag_value(flags, "sql", "sql/acdc_trial_extract.sql")
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

if (file.exists(csv_output)) {
  file.remove(csv_output)
}
if (file.exists(parquet_output)) {
  file.remove(parquet_output)
}
ensure_parent(csv_output)

result <- DBI::dbSendQuery(conn, read_sql(sql_path))
on.exit(DBI::dbClearResult(result), add = TRUE)
rows_written <- 0
datasets_seen <- integer()
first_chunk <- TRUE
csv_connection <- gzfile(csv_output, open = "wb", compression = 6)
connection_open <- TRUE
on.exit(
  if (connection_open) close(csv_connection),
  add = TRUE
)
repeat {
  trials <- DBI::dbFetch(result, n = chunk_size)
  if (nrow(trials) == 0) {
    break
  }
  if (any(is.na(trials$task_family))) {
    stop("Target extract contains unmapped task families.", call. = FALSE)
  }
  trials$mapping_issue <- ifelse(
    is.na(trials$block_raw),
    "missing_block_value",
    ifelse(
      trials$congruency == "unknown",
      "unknown_congruency_code",
      ifelse(
        is.na(trials$correct) & !is.na(trials$accuracy_raw),
        "unknown_accuracy_code",
        NA_character_
      )
    )
  )
  utils::write.table(
    trials,
    file = csv_connection,
    sep = ",",
    row.names = FALSE,
    col.names = first_chunk,
    quote = TRUE,
    na = "",
    qmethod = "double"
  )
  first_chunk <- FALSE
  rows_written <- rows_written + nrow(trials)
  datasets_seen <- union(datasets_seen, trials$dataset_id)
  message("Extracted ", format(rows_written, big.mark = ","), " trial rows...")
}
close(csv_connection)
connection_open <- FALSE

if (rows_written == 0) {
  stop(
    "No Stroop, Flanker, or Simon observations matched documented task names.",
    call. = FALSE
  )
}

ensure_parent(parquet_output)
if (!requireNamespace("arrow", quietly = TRUE)) {
  stop(
    "Package 'arrow' is required to write the Parquet trial extract.",
    call. = FALSE
  )
}
arrow_table <- arrow::read_csv_arrow(csv_output)
arrow::write_parquet(arrow_table, parquet_output)
rm(arrow_table)
gc()

message(
  "Wrote ", format(rows_written, big.mark = ","), " trial rows across ",
  length(datasets_seen), " datasets."
)
