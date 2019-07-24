import definitions

from bs4 import BeautifulSoup

from main.model.article import Article

from main.retrievers import affiliation, authors, date, email,\
    keywords, location, entities, language, jdst

PATH_TO_ARTICLES = definitions.ROOT_DIR + '/dataset/articles/'
PATH_TO_ARTICLES_ENTITIES = definitions.ROOT_DIR + '/dataset/articles_entities/'


def load_article(pmid):
    """Given the PMID, creates and returns an article full of all its retrievable informations."""

    # Opening the file and reading the content
    file = open(PATH_TO_ARTICLES+str(pmid)+'.xml', 'r')
    article_content = file.read()
    file.close()

    # Converting raw string into an object
    soup = BeautifulSoup(article_content, 'xml')

    # Retrieving basic infos
    aff = affiliation.find_affiliation(soup)
    lan = language.find_language(soup)
    auts = authors.find_authors(soup)
    dat = date.find_date(soup)
    mail = email.find_email(soup)
    keys = keywords.find_keywords(soup)
    country = location.find_country(soup)
    city = location.find_city(soup)
    ents = entities.find_entities(pmid, dir_path=PATH_TO_ARTICLES_ENTITIES)

    # Retrieving JDS and STS infos
    jds, sts, text = "", "", ""

    if soup.ArticleTitle is not None:
        if soup.ArticleTitle.string is not None:
            text = soup.ArticleTitle.string
    if soup.AbstractText is not None:
        if soup.AbstractText.string is not None:
            text = text + soup.AbstractText.string

    if len(text) == 0:
        jds = list()
        sts = list()
    else:
        jdst_retriever = jdst.JDSTRetriever()
        jds = jdst_retriever.get_jds(text)
        sts = jdst_retriever.get_sts(text)

    return Article(PMID=pmid, authors=auts, language=lan, e_mail=mail, date=dat, affiliation=aff,
                   country=country, city=city, key_words=keys, entities=ents, sts=sts, jds=jds)
