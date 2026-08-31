# ==============================================================================
# WEB SCRAPING OLX JABODETABEK - 2-LEVEL SLICING (NEMBUS CEILING 500 API)
# ==============================================================================

library(httr)
library(jsonlite)
library(dplyr)
library(readr)
library(writexl)

scrape_olx_jabodetabek_full_breakthrough <- function() {
  all_data <- list()
  
  # 1. Location IDs Resmi OLX Jabodetabek
  jabodetabek_locations <- list(
    "Jakarta D.K.I."    = "2000007",
    "Kota Bogor"        = "4000030",
    "Kab. Bogor"        = "4000029",
    "Kota Depok"        = "4000035",
    "Kota Tangerang"    = "4000009",
    "Kab. Tangerang"    = "4000008",
    "Tangerang Selatan" = "4000010",
    "Kota Bekasi"       = "4000032",
    "Kab. Bekasi"       = "4000031"
  )
  
  # 2. Daftar Merek Utama (Untuk memecah pencarian agar tidak ada bucket > 500 data)
  merek_list <- c(
    "toyota", "honda", "daihatsu", "suzuki", "mitsubishi", 
    "nissan", "hyundai", "wuling", "mazda", "bmw", 
    "mercedes-benz", "isuzu", "kia", "chevrolet", "ford", 
    "lexus", "mg", "dfsk", "chery", "subaru", "peugeot", ""
  )
  
  # 3. Rentang Harga Mikro
  price_slices <- list(
    c(min = 0, max = 70000000),
    c(min = 70000001, max = 120000000),
    c(min = 120000001, max = 170000000),
    c(min = 170000001, max = 230000000),
    c(min = 230000001, max = 320000000),
    c(min = 320000001, max = 500000000),
    c(min = 500000001, max = 10000000000)
  )
  
  headers <- c(`User-Agent` = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
  
  cat("==========================================================================\n")
  cat("===  SCRAPING 100% MOBIL BEKAS JABODETABEK (NEMBUS CEILING LIMIT API)  ===\n")
  cat("==========================================================================\n\n")
  
  for (loc_name in names(jabodetabek_locations)) {
    loc_id <- jabodetabek_locations[[loc_name]]
    cat(sprintf("\n[>>>] MENYERAP LOKASI: %s\n", toupper(loc_name)))
    
    for (merek_query in merek_list) {
      merek_label <- ifelse(merek_query == "", "MEREK LAINNYA", toupper(merek_query))
      
      for (slice in price_slices) {
        min_p <- slice["min"]
        max_p <- slice["max"]
        page <- 0
        
        while (page < 25) {
          # Construct API Query dengan Lokasi + Merek + Harga
          q_param <- ifelse(merek_query == "", "", paste0("&q=", URLencode(merek_query)))
          
          url <- paste0("https://www.olx.co.id/api/relevance/v2/search?category=198",
                        "&location=", loc_id,
                        q_param,
                        "&filter_price_from=", min_p,
                        "&filter_price_to=", max_p,
                        "&page=", page)
          
          res <- GET(url, add_headers(.headers = headers))
          if (status_code(res) != 200) break
          
          json_text <- content(res, "text", encoding = "UTF-8")
          parsed <- fromJSON(json_text, simplifyVector = FALSE)
          items <- parsed$data
          
          if (is.null(items) || length(items) == 0) break
          
          # Parsing 14 Peubah Lengkap
          page_list <- lapply(items, function(item) {
            judul_str       <- ifelse(is.null(item$title), NA_character_, as.character(item$title))
            merk_val        <- NA_character_
            model_val       <- NA_character_
            tahun_val       <- NA_character_
            km_val          <- NA_character_
            bbm_val         <- NA_character_
            transmisi_val   <- NA_character_
            penjual_val     <- NA_character_
            cc_val          <- NA_character_
            warna_val       <- NA_character_
            bodi_val        <- NA_character_
            
            if (!is.null(item$parameters)) {
              for (p in item$parameters) {
                fk <- tolower(ifelse(!is.null(p$formatted_key), p$formatted_key, ""))
                pk <- tolower(ifelse(!is.null(p$key), p$key, ""))
                val <- ifelse(!is.null(p$value_name), p$value_name, p$formatted_value)
                if (is.null(val) || val == "") next
                val <- as.character(val)
                
                if (fk == "merek" || pk == "p_make" || pk == "make") merk_val <- val
                else if (fk == "model" || pk == "p_model" || pk == "model") model_val <- val
                else if (fk == "tahun" || pk == "p_year" || pk == "year") tahun_val <- val
                else if (grepl("jarak|km|mileage", fk) || pk == "p_mileage") km_val <- val
                else if (grepl("bahan bakar|bensin|fuel", fk) || pk == "p_fuel") bbm_val <- val
                else if (grepl("transmisi", fk) || pk == "p_transmission") transmisi_val <- val
                else if (grepl("penjual|seller", fk) || pk == "p_seller_type") penjual_val <- val
                else if (grepl("kapasitas|mesin|cc", fk) || pk == "p_capacity") cc_val <- val
                else if (grepl("warna|color", fk) || pk == "p_color") warna_val <- val
                else if (grepl("bodi|body", fk) || pk == "p_body_type") bodi_val <- val
              }
            }
            
            if (!is.na(judul_str)) {
              words <- unlist(strsplit(trimws(judul_str), "\\s+"))
              if (is.na(merk_val)) merk_val <- words[1]
              if (is.na(model_val)) model_val <- ifelse(length(words) >= 2, words[2], words[1])
            }
            
            bursa_val <- "Penjual Perorangan"
            if (!is.null(item$store$name) && item$store$name != "") {
              bursa_val <- as.character(item$store$name)
            } else if (!is.null(item$user$name) && item$user$name != "") {
              bursa_val <- as.character(item$user$name)
            }
            
            prov <- ifelse(!is.null(item$locations_resolved$ADMIN_LEVEL_1_name), 
                           item$locations_resolved$ADMIN_LEVEL_1_name, NA_character_)
            kota <- ifelse(!is.null(item$locations_resolved$ADMIN_LEVEL_3_name), 
                           item$locations_resolved$ADMIN_LEVEL_3_name, loc_name)
            kecamatan <- ifelse(!is.null(item$locations_resolved$ADMIN_LEVEL_4_name), 
                                item$locations_resolved$ADMIN_LEVEL_4_name, kota)
            
            harga_str <- item$price$value$display
            if (is.null(harga_str)) harga_str <- item$price$value$raw
            harga_num <- ifelse(!is.null(harga_str), as.numeric(gsub("[^0-9]", "", harga_str)), NA_real_)
            
                data.frame(
              Judul            = judul_str, # <--- DITARUH DI PALING DEPAN
              Kategori         = "Mobil Bekas",
              Provinsi         = prov,
              Kota_Kabupaten   = kota,
              Kecamatan        = kecamatan,
              Harga_Teks       = ifelse(is.null(harga_str), NA_character_, as.character(harga_str)),
              Harga_IDR        = harga_num,
              Merk             = merk_val,
              Model            = model_val,
              Tahun            = tahun_val,
              Jarak_Tempuh     = km_val,
              Tipe_Bahan_Bakar = bbm_val,
              Transmisi        = transmisi_val,
              Tipe_Penjual     = ifelse(is.na(penjual_val), "Individu / Dealer", penjual_val),
              Nama_Bursa_Mobil = bursa_val,
              Kapasitas_Mesin  = cc_val,
              Warna            = warna_val,
              Tipe_Bodi        = bodi_val,
              URL_Detail       = ifelse(is.null(item$id), NA_character_, paste0("https://www.olx.co.id/item/", item$id)),
              stringsAsFactors = FALSE
            )
          })
          
          df_page <- bind_rows(page_list)
          all_data[[length(all_data) + 1]] <- df_page
          
          # Hitung Unik Terkumpul Secara Real-Time
          temp_count <- bind_rows(all_data) %>% distinct(URL_Detail, .keep_all = TRUE) %>% nrow()
          cat(sprintf("   -> %s [%s] | Page %2d | Unik Terkumpul: %d unit\n", 
                      loc_name, merek_label, page + 1, temp_count))
          
          page <- page + 1
          Sys.sleep(0.1) # Jeda waktu cepat
        }
      }
    }
  }
  
  # Deduplikasi Akhir Presisi Sesuai Web
  final_df <- bind_rows(all_data) %>% 
    distinct(URL_Detail, .keep_all = TRUE)
    
  return(final_df)
}

# ==============================================================================
# EKSEKUSI SCRAPING
# ==============================================================================
df_jabodetabek_real <- scrape_olx_jabodetabek_full_breakthrough()

# Simpan ke CSV & Excel
write_csv(df_jabodetabek_real, "PSD_OLX_JABODETABEK_FULL_REAL.csv")
write_xlsx(df_jabodetabek_real, "PSD_OLX_JABODETABEK_FULL_REAL.xlsx")

cat("\n==========================================================================\n")
cat(sprintf("✅ SELESAI TOTAL! Berhasil menguras %d unit data mobil unik dari Jabodetabek.\n", nrow(df_jabodetabek_real)))
cat("==========================================================================\n")