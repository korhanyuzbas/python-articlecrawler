Article Crawler
============

Article Crawler is a tool for crawling article from websites.

 * Webpage: https://github.com/pdfminer/

Features
--------

 * Crawling articles from HTML websites (PDF content still in progress).
 * Collecting article's images URLs.
 * Exporting article data into JSON or SQL (Only SQLite3 supported)


 ## Usage
 
Checkout the code:

	git clone https://github.com/misja/python-boilerpipe.git
	cd python-boilerpipe


**virtualenv**

	virtualenv -p python3 env
	source env/bin/activate
    pip install -r requirements.txt
	python setup.py install
	
**command line**

    python main.py <URL> --export=sql
Command Line Tools
------------------

PDFMiner comes with two handy tools:
pdf2txt.py and dumppdf.py.

**pdf2txt.py**

pdf2txt.py extracts text contents from a PDF file.
It extracts all the text that are to be rendered programmatically,
i.e. text represented as ASCII or Unicode strings.
It cannot recognize text drawn as images that would require optical character recognition.
It also extracts the corresponding locations, font names, font sizes, writing
direction (horizontal or vertical) for each text portion.
You need to provide a password for protected PDF documents when its access is restricted.
You cannot extract any text from a PDF document which does not have extraction permission.

(For details, refer to /docs/index.html.)

**dumppdf.py**

dumppdf.py dumps the internal contents of a PDF file in pseudo-XML format.
This program is primarily for debugging purposes,
but it's also possible to extract some meaningful contents (e.g. images).

(For details, refer to /docs/index.html.)


TODO
----

 * More SQL support.
 * Better documentation.
 * Performance improvements.
