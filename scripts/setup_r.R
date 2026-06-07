#!/usr/bin/env Rscript

bootstrap_library <- normalizePath(
  "renv/bootstrap-library",
  winslash = "/",
  mustWork = FALSE
)
dir.create(bootstrap_library, recursive = TRUE, showWarnings = FALSE)
.libPaths(c(bootstrap_library, .libPaths()))

if (!requireNamespace("renv", quietly = TRUE)) {
  install.packages(
    "renv",
    lib = bootstrap_library,
    repos = "https://cloud.r-project.org"
  )
}

if (!file.exists("renv.lock")) {
  renv::init(bare = TRUE, restart = FALSE)
}

packages <- c(
  "acdcquery",
  "arrow",
  "DBI",
  "digest",
  "httr",
  "jsonlite",
  "readr",
  "RSQLite"
)
renv::install(packages)
renv::snapshot(packages = c("renv", packages), prompt = FALSE)

message("R environment installed and snapshotted to renv.lock.")
