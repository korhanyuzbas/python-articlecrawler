import argparse
import json
import os
import uuid

import justext
import requests
from bs4 import BeautifulSoup
from goose3 import Goose
from goose3.configuration import Configuration
from pdfminer.converter import PDFPageAggregator
from pdfminer.high_level import extract_text_to_fp
from pdfminer.layout import LAParams, LTTextBoxHorizontal
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfparser import PDFParser
from requests.adapters import HTTPAdapter
from sqlalchemy import exists
from urllib3 import Retry

from constants import BASE_DIR, REQUESTS_RETRY, REQUESTS_TIMEOUT
from db import Article
from exceptions import UnknownContentType


class ExportArticle(object):
    """
    Export article to SQL or JSON (yet)

    Usage example:
        ExportArticle(article=<ArticleCrawler object>, to='sql')
    """

    def __init__(self, article, to):
        """
        
        :param to: Extration type, only supports SQL and JSON
        :param article: ArticleCrawler object
        :return: None
        """

        # article must be an ArticleCrawler object
        assert isinstance(article, ArticleCrawler), "article must be an ArticleCrawler object"

        self.to = to
        self.article = article

        if not self.article.title and not self.article.content:
            return

        try:
            import sqlalchemy
        except ImportError:
            print("SqlAlchemy is not installed. Process will be extracted to JSON file")
            self.to = 'json'

        self.__extract_to_json() if self.to == 'json' else self.__extract_to_sql()

    def __extract_to_sql(self):
        """
        Creates article table if not exists
        If url already exists in database, it will check if html content (raw_content) has changed
        Otherwise it will create new article

        Database sets for SQLite3.
        #TODO: hardcoded to SQLite3, get parameter from user
        """

        # Bad practice for importing
        # But it's creating tables on import
        # TODO: create table when __extract_to_sql() function called
        from db import sql_session as sql

        is_exists = sql.query(exists().where(Article.url == self.article.url)).scalar()
        if is_exists:
            # TODO: redundant query count. is_exists should be combined with article variable. affects database performance.
            article = sql.query(Article).filter_by(url=self.article.url).first()
            if article.raw_content != self.article.raw_content:
                article.raw_content = self.article.raw_content
                article.content = self.article.content
                article.title = self.article.title
                article.meta_keywords = self.article.meta_keywords
                article.meta_description = self.article.meta_description
                article.images = json.dumps(self.article.images)
                sql.commit()
        else:
            article = Article(title=self.article.title,
                              content=self.article.content,
                              url=self.article.url,
                              raw_content=self.article.raw_content,
                              meta_description=self.article.meta_description,
                              meta_keywords=self.article.meta_keywords,
                              images=json.dumps(self.article.images))
            sql.add(article)
            sql.commit()

    def __extract_to_json(self):
        """
        Extracting data to JSON
        """
        json_data = {}
        article_json_file = os.path.join(BASE_DIR, 'article.json')
        if os.path.exists(article_json_file):
            with open(article_json_file, 'r') as f:
                try:
                    json_data = json.load(f)
                except json.decoder.JSONDecodeError:
                    # It will delete JSON file in anyway
                    pass

            # delete json file so it can create it with edited version
            os.remove(article_json_file)
        else:
            json_data[self.article.url] = {}

        # TODO: Can cause performance issues
        # must find another way to do it
        if url not in json_data:
            json_data[self.article.url] = {}

        json_data[self.article.url] = {'title': self.article.title,
                                       'content': self.article.content,
                                       'raw_content': self.article.raw_content,
                                       'url': self.article.url,
                                       'meta_keywords': self.article.meta_keywords,
                                       'meta_description': self.article.meta_description,
                                       'images': self.article.images}

        # create json file
        with open(article_json_file, 'w') as f:
            json.dump(json_data, f, indent=4)


class ArticleCrawler(object):
    """
        Getting article details
        It doesn't require to call any function in this class
        Usage example:
            article = ArticleCrawler(url='some link')

            Example attributes:
                article.title = 'Example Title'
                article.content = 'Example Content'
                article.raw_content = returns full html body without parsing
                article.url = returns url for export to SQL or JSON
                article.images = returns list of images URLs
    """

    def __init__(self, url):
        """
        Constructor of ArticleCrawler

        :param url: URL to fetch
        :return: None
        """
        self.url = url
        self.title = ''
        self.content = ''
        self.raw_content = ''
        self.images = []
        self.meta_description = ''
        self.meta_keywords = ''
        self.response = self.__get_response()

        if not self.response:
            return

        try:
            self.__get_content_type()
        except UnknownContentType:
            print()

        self.is_html = False
        self.is_pdf = False

    def __get_content_type(self):
        response = self.response
        content_type = response.headers['Content-Type']

        # known content types
        # unknown content types will be added to json file
        if 'text/html' in content_type:
            self.is_html = True
            self.get_article_details()
        elif content_type == 'application/pdf':
            self.is_pdf = True
            print("PDF rendering is still in progress")
            # self.get_pdf_details()
        else:
            # if content type is not a expected type, it will write it to json file for

            # create textures folder if not exists
            path = os.path.join(BASE_DIR, 'textures')
            if not os.path.exists(path):
                os.makedirs(path)

            json_data = {}

            # read json file first if exists
            unknown_content_types_file = os.path.join(path, 'unknown-content-types.json')
            if os.path.exists(unknown_content_types_file):
                with open(unknown_content_types_file, 'r') as f:
                    try:
                        json_data = json.load(f)
                    except json.decoder.JSONDecodeError:
                        # It will delete JSON file in anyway
                        pass

                # delete json file so it can create it with edited version
                os.remove(unknown_content_types_file)
            else:
                json_data['content_types'] = []

            # for broken JSON files, there must be content_types key in dict
            if 'content_types' not in json_data:
                json_data['content_types'] = []

            json_data['content_types'].append(content_type)

            # create json file
            with open(unknown_content_types_file, 'w') as f:
                json.dump(json_data, f, indent=4)

            raise UnknownContentType

    def __get_response(self):
        with requests.Session() as s:
            retry = Retry(total=REQUESTS_RETRY, backoff_factor=0.3, status_forcelist=[500, 503])
            adapter = HTTPAdapter(max_retries=retry)
            s.mount('https://', adapter=adapter)
            s.mount('http://', adapter=adapter)
            try:
                return s.get(self.url, timeout=REQUESTS_TIMEOUT)
            except (requests.exceptions.ReadTimeout, requests.exceptions.ConnectionError):
                # TODO: Do something in case of connectionerror and/or readtimeout
                return
            except (requests.exceptions.MissingSchema):
                print("Invalid URL, Please make sure to add http:// or https:// to URL")

    def __process_goose(self):
        goose_config = Configuration()
        goose_config.browser_user_agent = 'Mozilla 5.0'
        goose_config.enable_image_fetching = True
        g = Goose(config=goose_config)
        try:
            article = g.extract(self.url)

            if article.top_image.src:
                self.images = self.get_all_images_from_example_src(article.top_image.src)

        except (requests.exceptions.ConnectionError, requests.exceptions.ReadTimeout):
            return None
        return article

    def get_all_images_from_example_src(self, src):
        """
        Goose library returns only one relevant image in article
        In case of having multiple relevant images in article, this will collect them all if have similar attributes

        :param src: Relevant image's URL
        :return: images list
        """
        soup = BeautifulSoup(self.response.text, 'html.parser')
        image_element = soup.find_all('img', {'src': src})[0]

        image_attrs = image_element.attrs

        # class attribute may use in other irrelevant image
        image_attrs.pop('class', None)

        # alt and id attributes are unique in most cases.
        image_attrs.pop('alt', None)
        image_attrs.pop('id', None)

        all_images = []

        for key, value in image_attrs.items():
            all_data = soup.find_all('img', {key: value})
            for i in all_data:
                all_images.append(i.get('src'))

        # article's top_image will appear in list twice, thus it will convert it to set and convert it back to list again
        all_images = list(set(all_images))

        return all_images

    def get_article_details(self):
        goose_object = self.__process_goose()

        title = None
        content = None
        if goose_object:
            title = goose_object.title
            # Removing newlines and tabs in article content
            content = goose_object.cleaned_text.replace('\n', '').replace('\t', '') if goose_object.cleaned_text else None

        # If Goose can not found title or content, will try jusText to get article
        if not title or not content:
            content_language = None
            for key, value in self.response.headers.items():
                if "language" in key.lower():
                    content_language = value

            # Goose would have found content language in meta
            if not content_language:
                content_language = goose_object.meta_lang

            # If not content language has found, English will be default language
            # TODO: take parameter from user for default language
            if not content_language:
                parapraphs = justext.justext(self.response.content, justext.get_stoplist(language='English'))
            else:
                path = os.path.join(BASE_DIR, 'textures')
                if not os.path.exists(path):
                    os.makedirs(path)

                # read json file first if exists

                language_codes_json = os.path.join(path, 'language_codes.json')
                stoplist_language = "English"

                if os.path.exists(language_codes_json):
                    with open(language_codes_json, 'r') as f:
                        language_data = json.load(f)

                    for key, value in language_data.items():
                        if key == content_language:
                            stoplist_language = value

                parapraphs = justext.justext(self.response.content, justext.get_stoplist(language=stoplist_language))

            # Goose would have found title in article
            if not title:
                try:
                    title = [parapraph.text for parapraph in parapraphs if
                             not parapraph.is_boilerplate and parapraph.is_heading and parapraph.class_type == 'good'][0]
                except IndexError:
                    pass

            # Goose would have found content in article
            if not content:
                content = " ".join([parapraph.text for parapraph in parapraphs if
                                    not parapraph.is_boilerplate and not parapraph.is_heading and parapraph.class_type == 'good'])

        self.title = title
        self.content = content
        self.raw_content = self.response.text
        self.meta_description = goose_object.meta_description
        self.meta_keywords = goose_object.meta_keywords

    # not using currently.
    def get_pdf_details(self):
        # save pdf to local
        # it gives random name to pdf, it will delete it after processing
        random_string = str(uuid.uuid4())[0:10]
        file_path = os.path.join(BASE_DIR, 'pdf_files', "{}.pdf".format(random_string))
        html_file_path = os.path.join(BASE_DIR, 'pdf_files', "{}.html".format(random_string))
        with open(file_path, 'wb') as f:
            f.write(self.response.content)

        text = ""

        # Usage Type 1:
        # Rendering pdf as text. Best way to get PDF content, but got problems with jusText, not getting article as expected
        with open(file_path, 'rb') as f:
            parser = PDFParser(f)
            document = PDFDocument(parser)
            manager = PDFResourceManager()
            laparams = LAParams()
            device = PDFPageAggregator(manager, laparams=laparams)
            interpreter = PDFPageInterpreter(manager, device)
            for page in PDFPage.get_pages(f):
                interpreter.process_page(page)
            layout = device.get_result()
            for element in layout:
                if isinstance(element, (LTTextBoxHorizontal)):
                    # alterin element get as html element, so jusText library can find relative texts
                    text += "<p>{}</p>".format(element.get_text())
            # End of usage type 1

            # Usage Type 2:
            # Rendering pdf as html. Not a great way to get PDF content. Font sizes, html elements etc. not rendering as expected.
            # If fixed, would work with jusText as expected.
            with open(html_file_path, 'wb') as outf:
                extract_text_to_fp(f, outf, output_type='html')
        with open(html_file_path, 'rb') as f:
            text = " ".join([x.decode().replace('\n', '') for x in f.readlines()])

        # End of usage type 2

        if document.info:
            self.title = document.info[0].get('Title', None)
            if self.title:
                self.title = self.title.decode()

        # jusText raises exception if text variable is empty
        if text:
            parapraphs = justext.justext(text, justext.get_stoplist(language='English'))

            content = " ".join([parapraph.text for parapraph in parapraphs if
                                not parapraph.is_boilerplate and not parapraph.is_heading and parapraph.class_type == 'good'])

            self.content = content
            self.raw_content = content

        # Remove reduntant files.
        os.unlink(file_path)
        os.unlink(html_file_path)


if __name__ == '__main__':
    argparser = argparse.ArgumentParser(description='Article crawler')
    argparser.add_argument('url', help='Enter URL to fetch',
                           default='https://www.theguardian.com/politics/2018/aug/19/brexit-tory-mps-warn-of-entryism-threat-from-leave-eu-supporters')
    argparser.add_argument('--export', help='Article export option. Choices are: sql, json. Default argument: sql', default='sql')

    parser = argparser.parse_args()

    url = parser.url
    export_option = parser.export

    article = ArticleCrawler(url=url)
    ExportArticle(article=article, to=export_option)
