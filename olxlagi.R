library(httr)
library(jsonlite)
library(dplyr)
library(writexl)

scrape_olx_mobil <- function(target_data = 1000) {
  all_data <- list()
  total_terambil <- 0
  page <- 0
  headers <- c(`User-Agent` = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
  
  cat("=== Memulai Web Scraping OLX Mobil Bekas ===\n")
  
  while (total_terambil < target_data) {
    url <- paste0("https://www.olx.co.id/api/relevance/v2/search?category=198&page=", page)
    res <- GET(url, add_headers(.headers = headers))
    
    if (status_code(res) != 200) break
    
    json_text <- content(res, "text", encoding = "UTF-8")
    parsed <- fromJSON(json_text, simplifyVector = FALSE)
    items <- parsed$data
    
    if (length(items) == 0) break
    
    page_list <- lapply(items, function(item) {
      # Pemetaan key atribut (Tahun, Transmisi, Mileage)
      params_map <- list()
      if (!is.null(item$parameters)) {
        for (p in item$parameters) {
          if (!is.null(p$key) && !is.null(p$value_name)) {
            params_map[[p$key]] <- p$value_name
          }
        }
      }
      
      # Parsing Harga Display & Konversi ke Angka Numerik
      harga_str <- item$price$value$display
      if (is.null(harga_str)) harga_str <- item$price$value$raw
      harga_num <- ifelse(!is.null(harga_str), as.numeric(gsub("[^0-9]", "", harga_str)), NA_real_)
      
      # Parsing Lokasi
      lokasi_val <- item$locations_resolved$ADMIN_LEVEL_3_name
      if (is.null(lokasi_val)) lokasi_val <- item$locations_resolved$ADMIN_LEVEL_1_name
      
      data.frame(
        Judul        = ifelse(is.null(item$title), NA_character_, as.character(item$title)),
        Harga_Teks   = ifelse(is.null(harga_str), NA_character_, as.character(harga_str)),
        Harga_IDR    = harga_num,
        Tahun        = ifelse(is.null(params_map[["year"]]), NA_character_, as.character(params_map[["year"]])),
        Jarak_Tempuh = ifelse(is.null(params_map[["mileage"]]), NA_character_, as.character(params_map[["mileage"]])),
        Transmisi    = ifelse(is.null(params_map[["transmission"]]), NA_character_, as.character(params_map[["transmission"]])),
        Lokasi       = ifelse(is.null(lokasi_val), NA_character_, as.character(lokasi_val)),
        URL_Detail   = ifelse(is.null(item$id), NA_character_, paste0("https://www.olx.co.id/item/", item$id)),
        stringsAsFactors = FALSE
      )
    })
    
    df_page <- bind_rows(page_list)
    all_data[[length(all_data) + 1]] <- df_page
    
    total_terambil <- total_terambil + nrow(df_page)
    cat(sprintf("Halaman %2d selesai | Total Data: %d / %d\n", page + 1, total_terambil, target_data))
    
    page <- page + 1
    Sys.sleep(1.2)
  }
  
  final_df <- bind_rows(all_data) %>% head(target_data)
  return(final_df)
}

# Jalankan & Simpan
df_mobil_bekas <- scrape_olx_mobil(target_data = 1000)
write_xlsx(df_mobil_bekas, "PSD_Scraping_OLX_1000lagi.xlsx")
cat("✅ Scraping selesai! Data tersimpan di 'PSD_Scraping_OLX_1000lagi.xlsx'\n")