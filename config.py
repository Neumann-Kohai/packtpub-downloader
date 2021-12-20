# -*- coding: utf-8 -*-

'''
    This file contain all url endpoint 
'''

# instead of variables should i change variables to a one big json of urls ? 

# this is base url where i do the requests
BASE_URL = "https://services.packtpub.com/"

# this is base url for static content
BASE_STATIC_URL = "https://static.packt-cdn.com/"

# webreader base url
BASE_WEBREADER_URL = "https://subscription.packtpub.com"

BASE_SHOP_URL = "https://www.packtpub.com/product"

# URL to request jwt token, params by post are user and pass, return jwt token
AUTH_ENDPOINT = "auth-v1/users/tokens"

# URL to get all your books, two params that i change are offset and limit, method GET
PRODUCTS_ENDPOINT = "entitlements-v1/users/me/products?sort={order}&offset={offset}&limit={limit}" #&search=Query

# URL(BASE_STATIC) to get book information from id 
URL_SUMMARY_ENDPOINT = "products/{book_id}/summary"

# URL(BASE_STATIC) to get author information from id 
URL_AUTHOR_ENDPOINT = "authors/{id}"

# URL to get types , param is  book id, method GET
URL_BOOK_TYPES_ENDPOINT = "products-v1/products/{book_id}/types"

# URL to get url file to download, params are book id and format of the file (can be pdf, epub, etc..), method GET
URL_BOOK_ENDPOINT = "products-v1/products/{book_id}/files/{format}"

# URL to get the toc of a book
URL_TOC_ENDPOINT = "products/{book_id}/toc"

# URL to get the reviews of a book
URL_REVIEWS_ENDPOINT = "feefo-v1/rating/{book_id}"


# Toggle lookups for additional information to use in the readme
ENABLE_TOC = True
ENABLE_REVIEWS = False
ENABLE_AUTHOR_LOOKUP = False