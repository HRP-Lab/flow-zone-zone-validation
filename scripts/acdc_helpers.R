parse_flags <- function(args) {
  values <- list()
  index <- 1
  while (index <= length(args)) {
    key <- args[[index]]
    if (!startsWith(key, "--")) {
      stop("Unexpected positional argument: ", key, call. = FALSE)
    }
    key <- sub("^--", "", key)
    if (index == length(args) || startsWith(args[[index + 1]], "--")) {
      values[[key]] <- TRUE
      index <- index + 1
    } else {
      values[[key]] <- args[[index + 1]]
      index <- index + 2
    }
  }
  values
}

flag_value <- function(flags, name, default = NULL) {
  value <- flags[[name]]
  if (is.null(value)) default else value
}

ensure_parent <- function(path) {
  dir.create(dirname(path), recursive = TRUE, showWarnings = FALSE)
}

read_schema_contract <- function(path = "config/acdc_schema.json") {
  jsonlite::fromJSON(path, simplifyVector = TRUE)
}

validate_acdc_schema <- function(conn, contract) {
  issues <- character()
  available_tables <- DBI::dbListTables(conn)
  for (table_name in names(contract)) {
    if (!table_name %in% available_tables) {
      issues <- c(issues, paste0("Missing table: ", table_name))
      next
    }
    available_columns <- DBI::dbListFields(conn, table_name)
    missing_columns <- setdiff(contract[[table_name]], available_columns)
    if (length(missing_columns) > 0) {
      issues <- c(
        issues,
        paste0(
          "Table ", table_name, " is missing columns: ",
          paste(missing_columns, collapse = ", ")
        )
      )
    }
  }
  issues
}

write_schema_discrepancy <- function(
    issues,
    output = "reports/acdc_schema_discrepancy.md",
    database_path = NULL) {
  ensure_parent(output)
  lines <- c(
    "# ACDC Schema Discrepancy",
    "",
    paste0("- Checked at: `", format(Sys.time(), tz = "UTC", usetz = TRUE), "`"),
    if (!is.null(database_path)) paste0("- Database: `", database_path, "`") else NULL,
    "",
    "The pipeline stopped because the live schema did not match the versioned contract.",
    "No field mappings were inferred.",
    "",
    "## Issues",
    "",
    paste0("- ", issues)
  )
  writeLines(lines, output, useBytes = TRUE)
}

connect_validated_acdc <- function(
    database_path,
    schema_path = "config/acdc_schema.json",
    discrepancy_path = "reports/acdc_schema_discrepancy.md") {
  conn <- acdcquery::connect_to_db(database_path)
  contract <- read_schema_contract(schema_path)
  issues <- validate_acdc_schema(conn, contract)
  if (length(issues) > 0) {
    write_schema_discrepancy(issues, discrepancy_path, database_path)
    DBI::dbDisconnect(conn)
    stop(
      "ACDC schema mismatch. See ", discrepancy_path,
      ". No mappings were inferred.",
      call. = FALSE
    )
  }
  conn
}

read_sql <- function(path) {
  paste(readLines(path, warn = FALSE, encoding = "UTF-8"), collapse = "\n")
}

write_json <- function(value, path) {
  ensure_parent(path)
  jsonlite::write_json(
    value,
    path,
    pretty = TRUE,
    auto_unbox = TRUE,
    null = "null",
    na = "null"
  )
}

read_json_or_empty <- function(path) {
  if (!file.exists(path)) {
    return(list())
  }
  jsonlite::read_json(path, simplifyVector = FALSE)
}
