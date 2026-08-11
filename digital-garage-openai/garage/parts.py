from urllib.parse import quote_plus
def shopping_links(query):
 q=quote_plus(query); return {'amazon_search':f'https://www.amazon.com/s?k={q}','ebay_search':f'https://www.ebay.com/sch/i.html?_nkw={q}','google_search':f'https://www.google.com/search?q={q}'}
def compare_part(stock,candidate): return {'stock':stock,'candidate':candidate,'fitment_gate':'Verify year/model/engine/transmission and manufacturer fitment evidence before purchase/install.','performance_questions':['Calibration requirement?','NVH change?','Emissions legality?','Service-life trade-off?','Supporting modification required?']}
