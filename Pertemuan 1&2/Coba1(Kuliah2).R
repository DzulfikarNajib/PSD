library(rvest)
url <- "https://www.carsome.id/beli-mobil-bekas"

card <- read_html(url) %>% html_elements('.mod-b-card__footer')
card %>%
 html_element('.mod-b-card__car-other') %>%
 html_elements('span') %>%
 html_text() %>%
 paste(collapse = ',')

sapply(card,
 function(card){
 card %>%
 html_element('.mod-b-card__car-other') %>%
 html_elements('span') %>%
 html_text() %>%
 paste(collapse = ',')
 })
