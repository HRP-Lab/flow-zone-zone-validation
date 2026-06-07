#!/usr/bin/env Rscript

args <- commandArgs(trailingOnly = TRUE)
input_dir <- if (length(args) >= 1) args[[1]] else "data/raw/acdc"
output_file <- if (length(args) >= 2) {
  args[[2]]
} else {
  "data/interim/acdc_inventory.csv"
}

if (!dir.exists(input_dir)) {
  stop("Input directory does not exist: ", input_dir, call. = FALSE)
}

files <- fs::dir_ls(input_dir, recurse = TRUE, type = "file", all = TRUE)
info <- fs::file_info(files)
inventory <- data.frame(
  path = fs::path_rel(files, start = input_dir),
  extension = tolower(fs::path_ext(files)),
  size_bytes = as.numeric(info$size),
  modified_at = format(info$modification_time, tz = "UTC", usetz = TRUE),
  stringsAsFactors = FALSE
)

dir.create(dirname(output_file), recursive = TRUE, showWarnings = FALSE)
readr::write_csv(inventory, output_file)
message("Wrote ", nrow(inventory), " inventory rows to ", output_file)
