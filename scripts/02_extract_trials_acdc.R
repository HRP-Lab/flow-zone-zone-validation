#!/usr/bin/env Rscript

args <- commandArgs(trailingOnly = TRUE)
input_dir <- if (length(args) >= 1) args[[1]] else "data/raw/acdc"
output_file <- if (length(args) >= 2) {
  args[[2]]
} else {
  "data/interim/acdc_trials.csv"
}
file_pattern <- if (length(args) >= 3) args[[3]] else "trial.*\\.csv$"

files <- fs::dir_ls(
  input_dir,
  recurse = TRUE,
  type = "file",
  regexp = file_pattern
)
if (length(files) == 0) {
  stop(
    "No files matched '", file_pattern,
    "'. Inspect data/interim/acdc_inventory.csv and adjust the pattern.",
    call. = FALSE
  )
}

read_trials <- function(path) {
  data <- readr::read_csv(path, show_col_types = FALSE, progress = FALSE)
  data$source_file <- fs::path_rel(path, start = input_dir)
  data
}

trials <- dplyr::bind_rows(lapply(files, read_trials))

# Tighten this check after confirming the source release's field names.
required_columns <- character()
missing_columns <- setdiff(required_columns, names(trials))
if (length(missing_columns) > 0) {
  stop(
    "Missing required columns: ", paste(missing_columns, collapse = ", "),
    call. = FALSE
  )
}

dir.create(dirname(output_file), recursive = TRUE, showWarnings = FALSE)
readr::write_csv(trials, output_file)
message("Wrote ", nrow(trials), " trials from ", length(files), " files.")
