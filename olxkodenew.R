library(jsonlite)
library(httr2)
library(dplyr)
library(purrr)
library(stringr)

# --- 1. Helper Function: Ekstraksi Parameter Spesifik dari API ---
get_param <- function(params, key_name) {
  if (is.null(params) || length(params) == 0) return(NA_character_)
  for (p in params) {
    if (isTRUE(p$key == key_name)) {
      val <- ifelse(!is.null(p$value_name), p$value_name, p$value)
      return(as.character(val))
    }
  }
  return(NA_character_)
}

# --- 2. Helper Function: Parsing Mileage ke Angka ---
parse_mileage <- function(x) {
  if (is.na(x) || x == "") return(NA_real_)
  x_clean <- str_replace_all(x, "\\.", "")
  nums <- as.numeric(unlist(str_extract_all(x_clean, "\\d+")))
  if (length(nums) >= 2) return(mean(nums[1:2]))
  if (length(nums) == 1) return(nums[1])
  return(NA_real_)
}

# --- 3. Fungsi Scrape per Halaman dengan Filter Rentang Harga ---
scrape_olx_chunk <- function(page_num, min_p, max_p) {
  # Endpoint API dengan filter min_price & max_price
  api_url <- paste0(
    "https://www.olx.co.id/api/relevance/v1/search?",
    "category=198&",
    "facet_limit=100&",
    "location=2000007&", # ID DKI Jakarta
    "location_facet=2000007&",
    "filter_price_between=", min_p, "%3A", max_p, "&",
    "page=", page_num
  )
  
  tryCatch({
    resp <- request(api_url) %>%
      req_headers(
        `User-Agent` = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        `Accept` = "application/json, text/plain, */*",
        `Accept-Language` = "id-ID,id;q=0.9,en-US;q=0.8",
        `Referer` = "https://www.olx.co.id/jakarta-dki_g2000007/mobil-bekas_c198",
        `Origin` = "https://www.olx.co.id"
      ) %>%
      req_error(is_error = function(resp) FALSE) %>%
      req_perform()
    
    if (resp_status(resp) != 200) return(NULL)
    
    json_data <- resp %>% resp_body_json()
    items <- json_data$data
    
    if (is.null(items) || length(items) == 0) return(NULL)
    
    parsed_data <- map_df(items, function(x) {
      params <- x$parameters
      
      # Ambil nilai parameter dinamis
      year_raw     <- get_param(params, "year")
      mileage_raw  <- get_param(params, "mileage")
      trans_raw    <- get_param(params, "transmission")
      fuel_raw     <- get_param(params, "fuel")
      
      tibble(
        id            = as.character(x$id),
        title         = as.character(x$title),
        price         = ifelse(!is.null(x$price$value$raw), x$price$value$raw, NA_real_),
        year_raw      = year_raw,
        mileage_raw   = mileage_raw,
        transmission  = trans_raw,
        fuel_type     = fuel_raw,
        location_city = ifelse(!is.null(x$locations_resolved$ADMIN_LEVEL_2), x$locations_resolved$ADMIN_LEVEL_2, NA_character_),
        location_sub  = ifelse(!is.null(x$locations_resolved$ADMIN_LEVEL_3), x$locations_resolved$ADMIN_LEVEL_3, NA_character_),
        is_badged     = ifelse(!is.null(x$badge$badge_type), x$badge$badge_type, "Standard"),
        created_at    = ifelse(!is.null(x$created_at), x$created_at, NA_character_)
      )
    })
    
    return(parsed_data)
  }, error = function(e) return(NULL))
}

# --- 4. Loop Chunking Rentang Harga (Trik Menjebol Limit 1000 OLX) ---
# Membagi pencarian ke 15 segmen harga dari Rp 0 s/d Rp 2 Miliar+
price_brackets <- c(
  0, 
  50000000, 
  75000000, 
  100000000, 
  125000000, 
  150000000, 
  175000000, 
  200000000, 
  250000000, 
  300000000, 
  400000000, 
  500000000, 
  750000000, 
  1000000000, 
  2000000000
)

all_chunks_data <- list()

for (b in 1:(length(price_brackets) - 1)) {
  min_p <- format(price_brackets[b], scientific = FALSE)
  max_p <- format(price_brackets[b+1], scientific = FALSE)
  
  message(paste0("=== Scraping Rentang Harga: Rp ", min_p, " - Rp ", max_p, " ==="))
  
  # Scrape maksimal 40 halaman per chunk
  for (page in 0:39) {
    df_page <- scrape_olx_chunk(page, min_p, max_p)
    
    if (is.null(df_page) || nrow(df_page) == 0) break
    
    all_chunks_data[[length(all_chunks_data) + 1]] <- df_page
    Sys.sleep(runif(1, 0.3, 0.8)) # Fast delay
  }
}

# Gabungkan seluruh chunk data mentah
raw_43k_df <- bind_rows(all_chunks_data)

# --- 5. Clean & Robust Feature Extraction (Mencegah Data Terbuang) ---
clean_43k_df <- raw_43k_df %>%
  # Hapus duplikat iklan akibat overlap rentang harga
  distinct(id, .keep_all = TRUE) %>%
  mutate(
    # Parsing Tahun (Utamakan dari parameter, fallback ke regex dari Judul)
    year = as.numeric(year_raw),
    year = ifelse(is.na(year), as.numeric(str_extract(title, "\\b(19|20)\\d{2}\\b")), year),
    
    # Hitung Usia Mobil
    car_age = 2026 - year,
    
    # Ekstrak Brand & Model
    brand = str_extract(title, "^\\S+"),
    
    # Parsing Kilometer
    mileage_clean = map_dbl(mileage_raw, parse_mileage)
  ) %>%
  # Filter hanya baris yang benar-benar invalid
  filter(!is.na(price), !is.na(year))

# Cek Total Data yang Berhasil Didapat
message(paste("TOTAL DATA MOBIL JAKARTA KEAMBIL:", nrow(clean_43k_df)))

# Export Data Utama
write.csv(clean_43k_df, "data_mobil_bekas_jakarta_43k_FULL.csv", row.names = FALSE)