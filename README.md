Article Crawler
============

Article Crawler is a tool for crawling article from websites.
Supports Python 3.5 or newer.

 * Webpage: https://github.com/korhanyuzbas/python-articlecrawler

Features
--------

 * Crawling articles from HTML websites (PDF content still in progress).
 * Collecting article's images URLs.
 * Exporting article data into JSON or SQL (Only SQLite3 supported)


 ## Usage
 
Checkout the code:

	git clone https://github.com/korhanyuzbas/python-articlecrawler.git
	cd python-articlecrawler


**virtualenv**

	virtualenv -p python3 env
	source env/bin/activate
    pip install -r requirements.txt
    python main.py <URL> --export=sql
    

TODO
----

 * More SQL support.
 * Better documentation.
 * Performance improvements.
