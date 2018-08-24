import unittest

from main import ArticleCrawler


class ArticleCrawlerTest(unittest.TestCase):
    def test_article(self):
        article = ArticleCrawler(url='https://www.theguardian.com/politics/2018/aug/19/brexit-tory-mps-warn-of-entryism-threat-from-leave-eu-supporters')
        self.assertIsInstance(article.title, str)


def create_test_suite():
    test_suite = unittest.TestSuite()
    test_suite.addTest(ArticleCrawlerTest())
    return test_suite

if __name__ == '__main__':
    suite = create_test_suite()
    runner = unittest.TextTestRunner()
    runner.run(suite)