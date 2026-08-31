# ==============================================================================
# SCRIPT UJI COBA 300 DATA (JUDUL DI KOLOM PERTAMA + CEK 15 PEUBAH)
# ==============================================================================

library(httr)
library(jsonlite)
library(dplyr)
library(writexl)

scrape_olx_test_300 <- function(target_data = 300) {
  all_data <- list()
  
  # Location DKI Jakarta & Bogor untuk Cek Cepat
  test_locations <- list("Jakarta D.K.I." = "2000007", "Kota Bogor" = "4000030")
  headers <- c(`User-Agent` = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
  
  cat("==================================================================\n")
  cat("=== MEMULAI SCRAPING UJI COBA 300 DATA (JUDUL KOLOM PERTAMA) ===\n")
  cat("==================================================================\n\n")
  
  for (loc_name in names(test_locations)) {
    loc_id <- test_locations[[loc_name]]
    page <- 0
    
    while (page < 25) {
      url <- paste0("https://www.olx.co.id/api/relevance/v2/search?category=198&location=", loc_id, "&page=", page)
      res <- GET(url, add_headers(.headers = headers))
      if (status_code(res) != 200) break
      
      json_text <- content(res, "text", encoding = "UTF-8")
      parsed <- fromJSON(json_text, simplifyVector = FALSE)
      items <- parsed$data
      
      if (is.null(items) || length(items) == 0) break
      
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
        
        # Ekstraksi Atribut JSON
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
        
        # Fallback Merk & Model dari Judul jika Kosong
        if (!is.na(judul_str)) {
          words <- unlist(strsplit(trimws(judul_str), "\\s+"))
          if (is.na(merk_val)) merk_val <- words[1]
          if (is.na(model_val)) model_val <- ifelse(length(words) >= 2, words[2], words[1])
        }
        
        # Ekstraksi Nama Bursa / Toko Penjual
        bursa_val <- "Penjual Perorangan"
        if (!is.null(item$store$name) && item$store$name != "") {
          bursa_val <- as.character(item$store$name)
        } else if (!is.null(item$user$name) && item$user$name != "") {
          bursa_val <- as.character(item$user$name)
        }
        
        # Lokasi
        prov <- ifelse(!is.null(item$locations_resolved$ADMIN_LEVEL_1_name), 
                       item$locations_resolved$ADMIN_LEVEL_1_name, NA_character_)
        kota <- ifelse(!is.null(item$locations_resolved$ADMIN_LEVEL_3_name), 
                       item$locations_resolved$ADMIN_LEVEL_3_name, loc_name)
        kecamatan <- ifelse(!is.null(item$locations_resolved$ADMIN_LEVEL_4_name), 
                            item$locations_resolved$ADMIN_LEVEL_4_name, kota)
        
        # Harga
        harga_str <- item$price$value$display
        if (is.null(harga_str)) harga_str <- item$price$value$raw
        harga_num <- ifelse(!is.null(harga_str), as.numeric(gsub("[^0-9]", "", harga_str)), NA_real_)
        
        # Data Frame dengan JUDUL di KOLOM PERTAMA
        data.frame(
          Judul            = judul_str,        # <-- DITARUH DI DEPAN
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
      
      temp_df <- bind_rows(all_data) %>% distinct(URL_Detail, .keep_all = TRUE)
      cat(sprintf("   -> Halaman %2d Selesai | Total Data Unik: %d / %d\n", page + 1, nrow(temp_df), target_data))
      
      if (nrow(temp_df) >= target_data) break
      page <- page + 1
      Sys.sleep(0.1)
    }
    
    temp_df <- bind_rows(all_data) %>% distinct(URL_Detail, .keep_all = TRUE)
    if (nrow(temp_df) >= target_data) break
  }
  
  final_df <- bind_rows(all_data) %>% distinct(URL_Detail, .keep_all = TRUE) %>% head(target_data)
  return(final_df)
}

# ==============================================================================
# EKSEKUSI CEK 300 DATA
# ==============================================================================
df_test_300 <- scrape_olx_test_300(target_data = 300)

# Simpan ke File Excel untuk dicek manual
write_xlsx(df_test_300, "PSD_TEST_300_DATA.xlsx")

cat("\n==================================================================\n")
cat("✅ UJI COBA SELESAI! Silakan buka file 'PSD_TEST_300_DATA.xlsx'\n")
cat("==================================================================\n")