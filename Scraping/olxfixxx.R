# ==============================================================================
# WEB SCRAPING MOBIL BEKAS OLX - BOGOR BARAT KOTA (14 PEUBAH LENGKAP)
# Link URL: https://www.olx.co.id/bogor-barat-kota_g5001307/mobil-bekas_c198
# ==============================================================================

# Pastikan package berikut sudah terpasang:
# install.packages(c("httr", "jsonlite", "dplyr", "writexl"))

library(httr)
library(jsonlite)
library(dplyr)
library(writexl)

scrape_olx_bogor_barat <- function() {
  all_data <- list()
  
  # Location ID untuk Bogor Barat Kota = 5001307 (diambil dari g5001307 di URL)
  location_id <- "5001307"
  
  # Mode sorting untuk memastikan seluruh data terserap tanpa ada yang terlewat
  sort_options <- c("", "desc-creation", "asc-price", "desc-price")
  headers <- c(`User-Agent` = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
  
  cat("======================================================================\n")
  cat("===  MEMULAI SCRAPING MOBIL BEKAS OLX - BOGOR BARAT KOTA          ===\n")
  cat("======================================================================\n\n")
  
  for (sort_type in sort_options) {
    page <- 0
    sort_name <- ifelse(sort_type == "", "Relevansi", sort_type)
    cat(sprintf("\n[+] Mengambil Data Mode Sorting: '%s' ...\n", sort_name))
    
    while (TRUE) {
      # API Endpoint dengan parameter location=5001307 (Bogor Barat Kota)
      url <- paste0("https://www.olx.co.id/api/relevance/v2/search?category=198",
                    "&location=", location_id,
                    ifelse(sort_type == "", "", paste0("&sorting=", sort_type)),
                    "&page=", page)
      
      res <- GET(url, add_headers(.headers = headers))
      if (status_code(res) != 200) break
      
      json_text <- content(res, "text", encoding = "UTF-8")
      parsed <- fromJSON(json_text, simplifyVector = FALSE)
      items <- parsed$data
      
      # Jika data halaman habis, hentikan loop
      if (is.null(items) || length(items) == 0) {
        cat(sprintf("   Halaman %d kosong, pindah mode sorting/selesai.\n", page + 1))
        break
      }
      
      # Parsing 14 Peubah per unit mobil
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
        
        # 1. Parsing Atribut dari Object JSON 'parameters'
        if (!is.null(item$parameters)) {
          for (p in item$parameters) {
            fk <- tolower(ifelse(!is.null(p$formatted_key), p$formatted_key, ""))
            pk <- tolower(ifelse(!is.null(p$key), p$key, ""))
            val <- ifelse(!is.null(p$value_name), p$value_name, p$formatted_value)
            if (is.null(val) || val == "") next
            val <- as.character(val)
            
            if (fk == "merek" || pk == "p_make" || pk == "make") {
              merk_val <- val
            } else if (fk == "model" || pk == "p_model" || pk == "model") {
              model_val <- val
            } else if (fk == "tahun" || pk == "p_year" || pk == "year") {
              tahun_val <- val
            } else if (grepl("jarak|km|mileage", fk) || pk == "p_mileage") {
              km_val <- val
            } else if (grepl("bahan bakar|bensin|fuel", fk) || pk == "p_fuel") {
              bbm_val <- val
            } else if (grepl("transmisi", fk) || pk == "p_transmission") {
              transmisi_val <- val
            } else if (grepl("penjual|seller", fk) || pk == "p_seller_type") {
              penjual_val <- val
            } else if (grepl("kapasitas|mesin|cc", fk) || pk == "p_capacity") {
              cc_val <- val
            } else if (grepl("warna|color", fk) || pk == "p_color") {
              warna_val <- val
            } else if (grepl("bodi|body", fk) || pk == "p_body_type") {
              bodi_val <- val
            }
          }
        }
        
        # 2. Fallback Parsing dari Judul jika Merk/Model bernilai NULL
        if (!is.na(judul_str)) {
          words <- unlist(strsplit(trimws(judul_str), "\\s+"))
          if (is.na(merk_val)) merk_val <- words[1]
          if (is.na(model_val)) {
            model_val <- ifelse(length(words) >= 2, words[2], words[1])
          }
        }
        
        # 3. Ekstraksi Nama Bursa / Showroom / Toko Penjual
        bursa_val <- "Penjual Perorangan"
        if (!is.null(item$store$name) && item$store$name != "") {
          bursa_val <- as.character(item$store$name)
        } else if (!is.null(item$user$name) && item$user$name != "") {
          bursa_val <- as.character(item$user$name)
        }
        
        # 4. Ekstraksi Lokasi Detail (Kecamatan / Kota / Provinsi)
        prov <- ifelse(!is.null(item$locations_resolved$ADMIN_LEVEL_1_name), 
                       item$locations_resolved$ADMIN_LEVEL_1_name, "Jawa Barat")
        kota <- ifelse(!is.null(item$locations_resolved$ADMIN_LEVEL_3_name), 
                       item$locations_resolved$ADMIN_LEVEL_3_name, "Kota Bogor")
        kecamatan <- ifelse(!is.null(item$locations_resolved$ADMIN_LEVEL_4_name), 
                            item$locations_resolved$ADMIN_LEVEL_4_name, "Bogor Barat")
        
        # 5. Parsing Harga Display (Teks) & Numerik (Angka IDR)
        harga_str <- item$price$value$display
        if (is.null(harga_str)) harga_str <- item$price$value$raw
        harga_num <- ifelse(!is.null(harga_str), as.numeric(gsub("[^0-9]", "", harga_str)), NA_real_)
        
        data.frame(
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
          Tipe_Penjual     = ifelse(is.na(penjual_val), "Individu", penjual_val),
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
      cat(sprintf("   Halaman %2d selesai | Total Data Unik Bogor Barat: %d\n", page + 1, nrow(temp_df)))
      
      page <- page + 1
      Sys.sleep(0.4)
    }
  }
  
  final_df <- bind_rows(all_data) %>% distinct(URL_Detail, .keep_all = TRUE)
  return(final_df)
}

# ==============================================================================
# JALANKAN SCRAPING & SIMPAN KE FILE EXCEL
# ==============================================================================
df_bogor_barat <- scrape_olx_bogor_barat()

# Simpan Hasil ke Excel
write_xlsx(df_bogor_barat, "PSD_Scraping_OLX_BogorBarat.xlsx")

cat("\n======================================================================\n")
cat(sprintf("✅ SELESAI! Berhasil mengambil seluruh %d data mobil bekas area Bogor Barat.\n", nrow(df_bogor_barat)))
cat("   File tersimpan di: 'PSD_Scraping_OLX_BogorBarat.xlsx'\n")
cat("======================================================================\n")