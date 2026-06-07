#!/usr/bin/env Rscript

args <- commandArgs(trailingOnly = TRUE)
url <- if (length(args) >= 1) args[[1]] else Sys.getenv("ACDC_DOWNLOAD_URL")
output_dir <- if (length(args) >= 2) args[[2]] else "data/raw/acdc"

if (!nzchar(url)) {
  stop(
    "Provide a download URL as the first argument or set ACDC_DOWNLOAD_URL.",
    call. = FALSE
  )
}

dir.create(output_dir, recursive = TRUE, showWarnings = FALSE)
url_path <- sub("[?#].*$", "", url)
filename <- basename(url_path)
if (!nzchar(filename) || filename == "/") {
  filename <- "acdc_download"
}
destination <- file.path(output_dir, filename)

message("Downloading ACDC data to ", destination)
utils::download.file(url, destination, mode = "wb", quiet = FALSE)

if (grepl("\\.zip$", destination, ignore.case = TRUE)) {
  message("Extracting archive into ", output_dir)
  utils::unzip(destination, exdir = output_dir)
}

message("Download complete.")
