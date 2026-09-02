library(httr)
library(jsonlite)
library(dplyr)
library(writexl)

scrape_olx_r <- function(pages = 2) {
  all_data <- list()
  headers <- c(`User-Agent` = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
  
  for (p in 0:(pages - 1)) {
    cat("Mengambil data halaman:", p + 1, "\n")
    url <- paste0("https://www.olx.co.id/api/relevance/v2/search?category=198&page=", p)
    
    res <- GET(url, add_headers(.headers = headers))
    
    if (status_code(res) == 200) {
      json_text <- content(res, "text", encoding = "UTF-8")
      parsed <- fromJSON(json_text)
      items <- parsed$data
      
      if (!is.null(items) && length(items) > 0) {
        df_page <- data.frame(
          Judul = items$title,
          Harga = items$price$value$display,
          Lokasi = items$locations_resolved$ADMIN_LEVEL_3_name,
          Link = paste0("https://www.olx.co.id/item/", items$id),
          stringsAsFactors = FALSE
        )
        all_data[[p + 1]] <- df_page
      }
    }
    Sys.sleep(1.5) # Jeda waktu
  }
  
  final_df <- bind_rows(all_data)
  return(final_df)
}

# Eksekusi fungsi
df_mobil <- scrape_olx_r(pages = 2)

# Simpan ke file Excel
write_xlsx(df_mobil, "PSD_Scraping_Mobil_Bekas.xlsx")
cat("✅ Data berhasil disimpan ke 'PSD_Scraping_Mobil_Bekas.xlsx'\n")