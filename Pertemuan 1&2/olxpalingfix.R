# Install package pendukung jika belum ada:
# install.packages(c("httr", "jsonlite", "dplyr", "writexl"))

library(httr)
library(jsonlite)
library(dplyr)
library(writexl)

scrape_olx_full <- function(target_data = 1500) {
  all_data <- list()
  
  # Strategi Multi-Sorting untuk menembus limit API & menjangkau seluruh Indonesia
  sort_options <- c("", "desc-creation", "asc-price", "desc-price")
  headers <- c(`User-Agent` = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
  
  cat("=======================================================\n")
  cat("=== WEB SCRAPING MOBIL BEKAS OLX INDONESIA (14 PEUBAH) ===\n")
  cat("=======================================================\n\n")
  
  for (sort_type in sort_options) {
    page <- 0
    sort_label <- ifelse(sort_type == "", "Relevansi/Populer", sort_type)
    cat(sprintf("\n[+] Mengambil Data Mode Sorting: %s\n", sort_label))
    
    while (page < 25) {
      # Endpoint API OLX Kategori 198 (Mobil Bekas Seluruh Indonesia)
      url <- if (sort_type == "") {
        paste0("https://www.olx.co.id/api/relevance/v2/search?category=198&page=", page)
      } else {
        paste0("https://www.olx.co.id/api/relevance/v2/search?category=198&sorting=", sort_type, "&page=", page)
      }
      
      res <- GET(url, add_headers(.headers = headers))
      if (status_code(res) != 200) break
      
      json_text <- content(res, "text", encoding = "UTF-8")
      parsed <- fromJSON(json_text, simplifyVector = FALSE)
      items <- parsed$data
      
      if (is.null(items) || length(items) == 0) break
      
      # Parsing 14 atribut per unit mobil
      page_list <- lapply(items, function(item) {
        
        # Inisialisasi 14 variabel default (NA)
        merk            <- NA_character_
        model_mobil     <- NA_character_
        tahun           <- NA_character_
        jarak_tempuh    <- NA_character_
        bahan_bakar     <- NA_character_
        transmisi       <- NA_character_
        tipe_penjual    <- NA_character_
        bursa_mobil     <- NA_character_
        kapasitas_mesin <- NA_character_
        warna           <- NA_character_
        tipe_bodi       <- NA_character_
        
        # Ekstraksi atribut dinamis dari list 'parameters'
        if (!is.null(item$parameters)) {
          for (p in item$parameters) {
            key_identifier <- tolower(paste(p$key, p$formatted_key, p$id, collapse = " "))
            val <- ifelse(!is.null(p$value_name), p$value_name, p$formatted_value)
            if (is.null(val) || val == "") next
            val <- as.character(val)
            
            # Match 14 Peubah berdasarkan pola teks
            if (grepl("brand|merk|make", key_identifier)) {
              merk <- val
            } else if (grepl("model", key_identifier)) {
              model_mobil <- val
            } else if (grepl("year|tahun", key_identifier)) {
              tahun <- val
            } else if (grepl("mileage|jarak|km", key_identifier)) {
              jarak_tempuh <- val
            } else if (grepl("fuel|bahan_bakar|bensin", key_identifier)) {
              bahan_bakar <- val
            } else if (grepl("transmis", key_identifier)) {
              transmisi <- val
            } else if (grepl("seller|penjual", key_identifier)) {
              tipe_penjual <- val
            } else if (grepl("bursa|pasar_mobil|showroom", key_identifier)) {
              bursa_mobil <- val
            } else if (grepl("capacity|kapasitas|cc|engine", key_identifier)) {
              kapasitas_mesin <- val
            } else if (grepl("color|warna", key_identifier)) {
              warna <- val
            } else if (grepl("body|bodi", key_identifier)) {
              tipe_bodi <- val
            }
          }
        }
        
        # Jika Merk tidak ditemukan di parameter, ekstrak kata pertama dari Judul
        if (is.na(merk) && !is.null(item$title)) {
          merk <- strsplit(item$title, " ")[[1]][1]
        }
        
        # Lokasi (Provinsi & Kota/Kabupaten)
        prov <- ifelse(!is.null(item$locations_resolved$ADMIN_LEVEL_1_name), 
                       item$locations_resolved$ADMIN_LEVEL_1_name, NA_character_)
        kota <- ifelse(!is.null(item$locations_resolved$ADMIN_LEVEL_3_name), 
                       item$locations_resolved$ADMIN_LEVEL_3_name, prov)
        
        # Harga Display & Numerik
        harga_str <- item$price$value$display
        if (is.null(harga_str)) harga_str <- item$price$value$raw
        harga_num <- ifelse(!is.null(harga_str), as.numeric(gsub("[^0-9]", "", harga_str)), NA_real_)
        
        # Data Frame 14 Peubah
        data.frame(
          Kategori         = "Mobil Bekas",
          Provinsi         = prov,
          Kota_Kabupaten   = kota,
          Harga_Teks       = ifelse(is.null(harga_str), NA_character_, as.character(harga_str)),
          Harga_IDR        = harga_num,
          Merk             = merk,
          Model            = model_mobil,
          Tahun            = tahun,
          Jarak_Tempuh     = jarak_tempuh,
          Tipe_Bahan_Bakar = bahan_bakar,
          Transmisi        = transmisi,
          Tipe_Penjual     = tipe_penjual,
          Nama_Bursa_Mobil = bursa_mobil,
          Kapasitas_Mesin  = kapasitas_mesin,
          Warna            = warna,
          Tipe_Bodi        = tipe_bodi,
          URL_Detail       = ifelse(is.null(item$id), NA_character_, paste0("https://www.olx.co.id/item/", item$id)),
          stringsAsFactors = FALSE
        )
      })
      
      df_page <- bind_rows(page_list)
      all_data[[length(all_data) + 1]] <- df_page
      
      # Hitung total data unik sementara
      temp_df <- bind_rows(all_data) %>% distinct(URL_Detail, .keep_all = TRUE)
      cat(sprintf("Halaman %2d Selesai | Data Unik Terkumpul: %d / %d\n", page + 1, nrow(temp_df), target_data))
      
      if (nrow(temp_df) >= target_data) break
      
      page <- page + 1
      Sys.sleep(0.8) # Jeda waktu ramah server
    }
    
    temp_df <- bind_rows(all_data) %>% distinct(URL_Detail, .keep_all = TRUE)
    if (nrow(temp_df) >= target_data) break
  }
  
  # Gabung & Potong Sesuai Target Data Unik
  final_df <- bind_rows(all_data) %>%
    distinct(URL_Detail, .keep_all = TRUE) %>%
    head(target_data)
    
  return(final_df)
}

# =======================================================
# EXECUTE SCRAPING & SAVE TO EXCEL
# =======================================================

# Masukkan target jumlah data yang kamu mau (misal: 1200 data)
df_olx_lengkap <- scrape_olx_full(target_data = 1200)

# Cek Struktur Data Frame
glimpse(df_olx_lengkap)

# Simpan ke Excel
write_xlsx(df_olx_lengkap, "PSD_Scraping_OLX_14Peubah.xlsx")
cat("\n✅ BERHASIL! Data 14 peubah disimpan di file 'PSD_Scraping_OLX_14Peubah.xlsx'\n")