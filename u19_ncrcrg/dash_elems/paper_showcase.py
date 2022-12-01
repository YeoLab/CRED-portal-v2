from collections import defaultdict, OrderedDict
from operator import getitem

import dash_bootstrap_components as dbc
import requests
from django_plotly_dash import DjangoDash
from .navbars import navbar_authenticated, navbar_home
from .helpers import *
from .. import settings
import pandas as pd
from xml.dom import minidom
import xmltodict
import re
import yaml

# from ..util import get_omero_objects

logger = logging.getLogger(__name__)

paper_app = DjangoDash('PaperShowcaseApp', external_stylesheets=[settings.BOOTSTRAP_THEME])
STATESDICT = defaultdict(list)


def get_base_url_other_repositories(repo_name):
    """
    Returns the base URL for a given repository name (as labeled in the google spreadsheet)
    """
    repos = {
        "SRA": "https://www.ncbi.nlm.nih.gov/sra/?term=",
        "NDEX": "https://www.ndexbio.org/viewer/networks/",
        "SYNAPSE": "https://www.synapse.org/#!Synapse:"
    }
    try:
        return repos[repo_name.upper()]
    except KeyError:
        logger.error(f"{repo_name.upper()} does not exist in repo dictionary")
        return ""


def read_sheet(tsv='NCRCRG-CN-iSearch_-_Publications-export_2022-06-28-19-52-25.tsv'):
    """
    NCRCRG-CN-iSearch_-_Publications-export_2022-06-28-19-52-25.tsv
    Reads in a publication metadata sheet from somewhere.
    TODO: pull in from google sheets directly
    """
    df = pd.read_csv(tsv, sep='\t', dtype={'OMERO accession': 'str'})
    df.fillna("", inplace=True)
    return df


def paper_showcase_page(cred_user):
    if cred_user.is_authenticated:
        nav = navbar_authenticated(cred_user)
    else:
        nav = navbar_home()
    paper_app.layout = html.Div([
        nav,
        dbc.Container([
            html.H1("Featured Publications", id="featuredPublications"),
        ], className="container"),
    ])

    return paper_app


def get_publications():
    df = read_sheet()
    try:
        with open('tmp.yaml') as f:
            y = yaml.load(f, Loader=yaml.FullLoader)
        records = defaultdict(dict, **y)
        logger.debug("Successfully loaded from cache")
    except Exception as e:
        logger.debug(e)
        records = defaultdict(dict)
    all_records = df.to_dict(orient='records')

    for r in all_records:
        cleaned_doi = clean_doi(r['DOI'])  # forms do NOT like non-alphanumeric characters!

        if cleaned_doi in records.keys():
            logger.debug(f"record {cleaned_doi} exists, do not re-parse.")
            pass
        else:
            records[cleaned_doi]['other_accessions'] = defaultdict(dict)
            logger.debug(f"record {cleaned_doi} does not exist, parse.", records.keys())
            authors = r['Authors'].split(';')
            author_string = '; '.join(authors[:2]) + ' et. al.' if len(authors) > 2 else '; '.join(authors[:2])
            other_accessions = r['Other accessions'].split(',') if r['Other accessions'] != "" else []
            for other_accession in other_accessions:
                try:
                    other_repo, accession = other_accession.split('::')
                    records[cleaned_doi]['other_accessions'][f"{other_repo} ({accession})"] = get_base_url_other_repositories(other_repo) + accession
                except ValueError as e:
                    logger.error(e, other_accession)
            records[cleaned_doi]['title'] = r['Title']
            records[cleaned_doi]['full_authors'] = r['Authors']
            records[cleaned_doi]['authors'] = author_string
            records[cleaned_doi]['abstract'] = r['Abstract']
            records[cleaned_doi]['total_citations'] = r['Total Citations']
            records[cleaned_doi]['pub_year'] = r['Pub Year']
            records[cleaned_doi]['mesh_keywords'] = r['MeSH Keywords'].split(';')
            records[cleaned_doi]['doi_link'] = f"https://doi.org/{r['DOI']}"
            records[cleaned_doi]['pmid_link'] = f"https://pubmed.ncbi.nlm.nih.gov/{r['PMID']}"
            records[cleaned_doi]['geo_accessions'] = []
            records[cleaned_doi]['pride_accessions'] = []
            records[cleaned_doi]['omero_accessions'] = []
            if r['GEO accession'] != "":
                for accession in r['GEO accession'].split(','):
                    logger.debug(f"parsing publication (GEO) {accession}")
                    records[cleaned_doi]['geo_accessions'] += get_srr_from_geo_accession(accession)  # GEO -> SRR
            if r['PRIDE accession'] != "":
                for accession in r['PRIDE accession'].split(','):
                    logger.info(f"parsing publication (PRIDE) {accession}")
                    records[cleaned_doi]['pride_accessions'] += get_files_from_pride_accession(accession)
            if r['OMERO accession'] != "":
                for accession in str(r['OMERO accession']).split(','):
                    logger.info(f"parsing publication (OMERO) {accession}")
                    records[cleaned_doi]['omero_accessions'] += get_omero_images(str(accession))

    with open('tmp.yaml', 'w') as o:
        yaml.dump(records, o, default_flow_style=False)

    sorted_records = OrderedDict(sorted(records.items(), key=lambda x: getitem(x[1], 'pub_year'), reverse=True))
    return sorted_records


def get_omero_images(omero_id):
    """
    Queries OMERO for images associated with a given ID.
    :params omero_id: str used to query OMERO referred to accession.
    :return omero_image: list of image tuples containing the image name and path to the image.
    """
    logger.info("Start get_omero_images")
    omero_name, omero_id = str(omero_id).split('::')
    # omero_image = get_omero_objects(omero_id)
    # return omero_image
    return [(omero_id, omero_name)]


def esearch(term, db='gds'):
    """
    Queries NCBI using the esearch utility. GEO ('gds') database is used as default for search term.
    """
    logger.debug(f"Start esearch GDS ({term})")
    url = f'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db={db}&term={term}&retmax=5000&usehistory=y'
    response = urllib.request.urlopen(url)
    return response.read()


def get_esummary(esearch_string, db='gds'):
    """
    Parses a http response in XML format to obtain the webenv and querykey tokens.
    Uses NCBI eutils to transform these tokens into web summaries of GEO (db='gds') datasets.
    """
    logger.debug("Start esummary GDS")
    xmldoc = minidom.parseString(esearch_string)
    try:
        webenv = xmldoc.getElementsByTagName('WebEnv')[0].firstChild.data
        querykey = xmldoc.getElementsByTagName('QueryKey')[0].firstChild.data
        host = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi'
        params = f'?db={db}&version=2.0&query_key={querykey}&WebEnv={webenv}'
        url = host + params
        response = urllib.request.urlopen(url)
        return response.read()
    except IndexError as e:
        logger.debug(f"Unparsable publication string ({e}, search={esearch_string}")
        return ""


def parse_geo_esummary(input_string):
    """
    Parses an XML-formatted GEO metadata string and returns series, sample, and platform metadata.
    Importantly, this function uses the GEO metadata to pull out the SRA accession ID.
    """
    logger.debug("Parsing esummary GDS")
    try:
        o = xmltodict.parse(input_string)
    except Exception as e:
        logger.debug(f"Could not parse xml to dict: {input_string}")
        return [], [], []
    series_metadata = defaultdict()  # should only be one series per xml string
    sample_metadata = []  # one or more samples
    platform_metadata = []  # one or more associated platforms
    try:
        for document_summary in o['eSummaryResult']['DocumentSummarySet']['DocumentSummary']:
            acc = document_summary['Accession']
            title = document_summary['title']
            description = document_summary['summary']
            if acc.startswith('GSE'):  # Series
                series_metadata = {'accession': acc, 'title': title, 'description': description}
            elif acc.startswith('GSM'):  # Sample
                sra = ""
                try:
                    if document_summary['ExtRelations']['ExtRelation']['RelationType'] == 'SRA':
                        sra = document_summary['ExtRelations']['ExtRelation']['TargetObject']
                except KeyError:
                    logger.error(f"Error parsing GEO Summary. No known SRA or malformed entry {acc}.")
                    raise
                except TypeError:
                    logger.error(f"Error parsing GEO Summary {acc}. Make sure the GEO accession ID is not a superSeries.")
                    raise
                metadata = {'accession': acc, 'title': title, 'description': description, 'SRA': sra}
                sample_metadata.append(metadata)
            elif acc.startswith('GPL'):  # Platform
                platform_metadata.append({'accession': acc, 'title': title, 'description': description})
    except KeyError as e:
        logger.error(e, input_string)
    return series_metadata, sample_metadata, platform_metadata


def efetch(srx, db='sra'):
    logger.debug(f"Starting efetch SRA {srx}")
    host = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/'
    url = host + f'efetch.fcgi?db={db}&id={srx}'
    try:
        response = urllib.request.urlopen(url)
    except urllib.error.HTTPError as e:
        logger.error(e)
        response = urllib.request.urlopen(url, timeout=1)
    return response.read()


def parse_srx(input_string):
    """
    Takes an input string from an API call to eutils, returns a list of tuples [SRR accession, label]
    """
    logger.debug("Parsing SRA")
    try:
        o = xmltodict.parse(input_string)
    except TypeError as e:
        logger.error(f"Having trouble parsing SRX input string (starts with: {input_string[:200]}...).")
        raise
    accession_metadata = []
    for _, experiment in o['EXPERIMENT_PACKAGE_SET'].items():
        try:
            label = experiment['EXPERIMENT']['TITLE']
            for key, run in experiment['RUN_SET'].items():
                if key == 'RUN':
                    try:  # one RUN per RUN_SET
                        srr = run['IDENTIFIERS']['PRIMARY_ID']
                        label2 = label + f' (SRR: {srr})'
                        accession_metadata.append((srr, label2))
                    except TypeError:  # multiple RUNS per RUN_SET
                        for r in run:
                            srr = r['IDENTIFIERS']['PRIMARY_ID']
                            label2 = label + f' (SRR: {srr})'
                            accession_metadata.append((srr, label2))
        except KeyError:
            logger.error(f"Dictionary does not have the requisite keys {o}")

    return sorted(accession_metadata)


def get_srr_from_geo_accession(geo_term):
    """
    Converts GEO accession codes into a list of SRA accessions.
    Returns a list of tuples [(SRR_accession1, label1), (SRR_accession2, label2), etc.]
    """
    logger.debug(f"parsing {geo_term}")
    esummary = get_esummary(esearch(geo_term, db='gds'), db='gds')
    try:
        series_metadata, sample_metadata, platform_metadata = parse_geo_esummary(esummary)
    except TypeError as e:
        logger.error(f"Problem parsing GEO term {geo_term}: {e}")
        return []
    accessions = []
    for sample in sample_metadata:  # one for each GSM id

        try:
            fetched = efetch(srx=sample['SRA'])
            accessions += parse_srx(fetched)
        except IndexError as e:
            logger.error(f"Error in get_srr_from_geo_accession({geo_term}) {e}")
            pass
    return accessions


def get_files_from_pride_accession(pride_accession):
    files = []
    response = requests.get(
        f'https://www.ebi.ac.uk/pride/ws/archive/v2/projects/{pride_accession}/files',
        headers={'Accept': 'application/json'}
    )
    responsej = response.json()
    for file_object in responsej['_embedded']['files']:
        for f in file_object['publicFileLocations']:
            if f['name'] == 'FTP Protocol':
                files.append((f['value'], os.path.basename(f['value'])))

    return files


def clean_doi(doi):
    """
    Turns DOI accession IDs into something parseable by django forms.
    Forms do not work well with '.' or '/', so to be safe, we'll
    transform non-alphanumeric characters into underscores.
    (eg. 10.1038/s41593-019-0393-4 -> 10_1038_s41593_019_0393_4
    """
    return re.sub(r"[^a-zA-Z0-9]", '_', doi)


publications = get_publications()