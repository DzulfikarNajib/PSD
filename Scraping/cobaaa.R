library(httr)
library(jsonlite)
library(dplyr)
library(writexl)
library(stringr)

scrape_olx_jakarta_full <- function(target_data = 43000) {
  all_data <- list()
  headers <- c(`User-Agent` = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
  
  price_brackets <- c(
    0, 30000000, 50000000, 75000000, 100000000, 125000000, 150000000, 
    175000000, 200000000, 250000000, 300000000, 400000000, 500000000, 
    750000000, 1000000000, 1500000000, 2000000000, 5000000000
  )
  
  sort_options <- c("", "desc-creation", "asc-price", "desc-price")
  
  cat("=======================================================\n")
  cat("=== SCRAPING FULL DATASET MOBIL BEKAS DKI JAKARTA ===\n")
  cat("=======================================================\n\n")
  
  for (b in 1:(length(price_brackets) - 1)) {
    min_p <- format(price_brackets[b], scientific = FALSE)
    max_p <- format(price_brackets[b+1], scientific = FALSE)
    
    cat(sprintf("\n--- Memproses Rentang Harga: Rp %s s/d Rp %s ---\n", min_p, max_p))
    
    for (sort_type in sort_options) {
      page <- 0
      
      while (page < 25) {

        url <- paste0(
          "https://www.olx.co.id/api/relevance/v2/search?",
          "category=198&",
          "location=2000007&",
          "location_facet=2000007&",
          "filter_price_between=", min_p, "%3A", max_p,
          if (sort_type != "") paste0("&sorting=", sort_type) else "",
          "&page=", page
        )
        
        res <- GET(url, add_headers(.headers = headers))
        if (status_code(res) != 200) break
        
        json_text <- content(res, "text", encoding = "UTF-8")
        parsed <- fromJSON(json_text, simplifyVector = FALSE)
        items <- parsed$data
        
        if (is.null(items) || length(items) == 0) break
        
        page_list <- lapply(items, function(item) {
          judul_str <- ifelse(is.null(item$title), NA_character_, as.character(item$title))
          
          merk            <- NA_character_
          model_mobil     <- NA_character_
          tahun           <- NA_character_
          jarak_tempuh    <- NA_character_
          bahan_bakar     <- NA_character_
          transmisi       <- NA_character_
          tipe_penjual    <- NA_character_
          kapasitas_mesin <- NA_character_
          warna           <- NA_character_
          tipe_bodi       <- NA_character_
          
          if (!is.null(item$parameters)) {
            for (p in item$parameters) {
              key_str <- tolower(paste(p$key, p$formatted_key, p$key_name, p$id, collapse = " "))
              val <- if (!is.null(p$value_name)) p$value_name else p$formatted_value
              if (is.null(val) || val == "") next
              val <- as.character(val)
              
              if (grepl("brand|merk|make", key_str)) merk <- val
              else if (grepl("model", key_str) && !grepl("brand|merk", key_str)) model_mobil <- val
              else if (grepl("year|tahun", key_str)) tahun <- val
              else if (grepl("mileage|jarak|km", key_str)) jarak_tempuh <- val
              else if (grepl("fuel|bahan_bakar|bensin", key_str)) bahan_bakar <- val
              else if (grepl("transmis", key_str)) transmisi <- val
              else if (grepl("seller|penjual", key_str)) tipe_penjual <- val
              else if (grepl("capacity|kapasitas|cc|engine", key_str)) kapasitas_mesin <- val
              else if (grepl("color|warna", key_str)) warna <- val
              else if (grepl("body|bodi", key_str)) tipe_bodi <- val
            }
          }
          
          if (!is.na(judul_str)) {
            words <- unlist(strsplit(trimws(judul_str), "\\s+"))
            if (is.na(merk)) merk <- words[1]
            if (is.na(model_mobil)) model_mobil <- ifelse(length(words) >= 2, words[2], words[1])
            if (is.na(tahun)) tahun <- str_extract(judul_str, "\\b(19|20)\\d{2}\\b")
            
            if (is.na(transmisi)) {
              if (grepl("AT|Automatic|Matic|CVT", judul_str, ignore.case = TRUE)) transmisi <- "Automatic"
              else if (grepl("MT|Manual", judul_str, ignore.case = TRUE)) transmisi <- "Manual"
            }
          }
          
          bursa_mobil <- "Penjual Perorangan"
          if (!is.null(item$store$name) && item$store$name != "") {
            bursa_mobil <- as.character(item$store$name)
          } else if (!is.null(item$user$name) && item$user$name != "") {
            bursa_mobil <- as.character(item$user$name)
          }
          
          prov <- ifelse(!is.null(item$locations_resolved$ADMIN_LEVEL_1_name), 
                         item$locations_resolved$ADMIN_LEVEL_1_name, "Jakarta D.K.I.")
          kota <- ifelse(!is.null(item$locations_resolved$ADMIN_LEVEL_2_name), 
                         item$locations_resolved$ADMIN_LEVEL_2_name, 
                         ifelse(!is.null(item$locations_resolved$ADMIN_LEVEL_3_name),
                                item$locations_resolved$ADMIN_LEVEL_3_name, prov))
          kecamatan <- ifelse(!is.null(item$locations_resolved$ADMIN_LEVEL_3_name),
                              item$locations_resolved$ADMIN_LEVEL_3_name, NA_character_)
          
          harga_str <- item$price$value$display
          if (is.null(harga_str)) harga_str <- item$price$value$raw
          harga_num <- ifelse(!is.null(harga_str), as.numeric(gsub("[^0-9]", "", as.character(harga_str))), NA_real_)
          
          data.frame(
            Judul            = judul_str,
            Kategori         = "Mobil Bekas",
            Provinsi         = prov,
            Kota_Kabupaten   = kota,
            Kecamatan        = kecamatan,
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
            Tipe_Bodi        = tipe_bodi, # Fixed variable bug (tipe_bodi)
            URL_Detail       = ifelse(is.null(item$id), NA_character_, paste0("https://www.olx.co.id/item/", item$id)),
            stringsAsFactors = FALSE
          )
        })
        
        df_page <- bind_rows(page_list)
        all_data[[length(all_data) + 1]] <- df_page
        
        temp_df <- bind_rows(all_data) %>% distinct(URL_Detail, .keep_all = TRUE)
        cat(sprintf("Proses... | Total Data Unik Terkumpul: %d / %d\r", nrow(temp_df), target_data))
        
        if (nrow(temp_df) >= target_data) break
        page <- page + 1
        Sys.sleep(0.2)
      }
      
      temp_df <- bind_rows(all_data) %>% distinct(URL_Detail, .keep_all = TRUE)
      if (nrow(temp_df) >= target_data) break
    }
    
    temp_df <- bind_rows(all_data) %>% distinct(URL_Detail, .keep_all = TRUE)
    if (nrow(temp_df) >= target_data) break
  }
  
  final_df <- bind_rows(all_data) %>% distinct(URL_Detail, .keep_all = TRUE)
  return(final_df)
}

df_jakarta_full <- scrape_olx_jakarta_full(target_data = 43000)

write_xlsx(df_jakarta_full, "PSD_DATA_MOBIL_JAKARTA_FULL.xlsx")