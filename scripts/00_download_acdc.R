#!/usr/bin/env Rscript

source("scripts/acdc_helpers.R")

flags <- parse_flags(commandArgs(trailingOnly = TRUE))
output_dir <- flag_value(flags, "output-dir", "data/raw/acdc")
tag <- flag_value(flags, "tag", NULL)
manifest_path <- flag_value(flags, "manifest", "reports/run_manifest.json")

dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)
existing_database <- file.path(output_dir, "acdc.db")
if (file.exists(existing_database)) {
  Sys.chmod(existing_database, mode = "0666")
}
message(
  "Downloading ACDC ",
  if (is.null(tag)) "latest release" else paste0("release ", tag),
  " into ", output_dir
)

database_path <- acdcquery::download_acdc(output_dir, tag = tag)
database_path <- normalizePath(database_path, winslash = "/", mustWork = TRUE)

verified <- acdcquery::check_acdc(database_path, tag = tag)
if (!isTRUE(verified)) {
  stop("Downloaded ACDC database failed release hash verification.", call. = FALSE)
}

release_url <- "https://api.github.com/repos/jstbcs/acdc-database/releases/latest"
if (!is.null(tag)) {
  release_url <- paste0(
    "https://api.github.com/repos/jstbcs/acdc-database/releases/tags/",
    utils::URLencode(tag, reserved = TRUE)
  )
}
response <- httr::GET(release_url)
httr::stop_for_status(response)
release <- jsonlite::fromJSON(
  httr::content(response, as = "text", encoding = "UTF-8")
)

manifest <- read_json_or_empty(manifest_path)
manifest$created_at_utc <- format(Sys.time(), tz = "UTC", usetz = TRUE)
manifest$acdc <- list(
  release_tag = release$tag_name,
  release_published_at = release$published_at,
  database_path = database_path,
  database_size_bytes = unname(file.info(database_path)$size),
  sha256 = digest::digest(file = database_path, algo = "sha256"),
  release_hash_verified = TRUE,
  acdcquery_version = as.character(utils::packageVersion("acdcquery")),
  r_version = R.version.string
)
write_json(manifest, manifest_path)

Sys.chmod(database_path, mode = "0444")
message("ACDC download verified: ", database_path)
