import base64
import json
import os
import re
import ssl
import urllib.request
from collections import OrderedDict

import pymongo
import requests
from django.utils.datetime_safe import datetime
from django.core.validators import RegexValidator

from django.conf import settings

from u19_ncrcrg.accounts.views import get_admin_client, get_globus_https_server, get_https_token
from u19_ncrcrg.read_SRA_xml import get_10x_metadata_from_xml

alphanumeric_plus = RegexValidator(r'^[0-9a-zA-Z-\.]*$', 'Only alphanumeric characters, dots and dashes are allowed.')


def connect_mongodb(database, user, password):
    client = pymongo.MongoClient(
        "mongodb+srv://{}:{}@cluster0-hcum8.mongodb.net/test?retryWrites=true".
            format(urllib.parse.quote_plus(user),
                   urllib.parse.quote_plus(password)),
        ssl=True,
        ssl_cert_reqs=ssl.CERT_NONE
    )
    return client[database]


db = connect_mongodb(database='u19', user=bytes(os.environ.get("MONGODB_USER"), 'utf-8'),
                     password=bytes(os.environ.get("MONGODB_PASSWORD"), 'utf-8'))


def valid_pipelines():
    """
    :return: dictionary containing tool.id - tool Object as key - value pairs
    """
    pipelines = {
        'Azimuth043Job': Azimuth043Job,
        'CellrangerCount302Job': CellrangerCount302Job,
        'CellrangerAggr302Job': CellrangerAggr302Job,
        'CellrangerFromSRX302Job': CellrangerFromSRX302Job,
        'CellrangerCount600Job': CellrangerCount600Job,
        'Chipseq215Job': Chipseq215Job,
        'Comppassde872c0Job': Comppassde872c0Job,
        'Dropseqtools113Job': Dropseqtools113Job,
        'Fragpipe180Job': Fragpipe180Job,
        'GEKO': Geko,
        'Genoppib9ae5caJob': Genoppib9ae5caJob,
        'Maxquant1634Job': Maxquant1634Job,
        'Maxquant161043Job': Maxquant161043Job,
        'Mrhg060Job': Mrhg060Job,
        'RnaseqJob': RnaseqJob,
        'Saintexpress363Job': Saintexpress363Job,
        'ScArches035': ScArches035,
        'Seurat403': Seurat403,
        'Toppcell20200612Job': Toppcell20200612Job,
        'Star252bJob': Star252bJob,
        'Star274aJob': Star274aJob,
        'ProteomicsEssentials': ProteomicsEssentials,
        'ImagingEssentials': ImagingEssentials,
        'EphysEssentials': EphysEssentials,
        'Patchseqtools': Patchseqtools,
    }
    return pipelines


def mergedict(dict1, dict2):
    """
    Special function that merges two dictionaries together, without overriding keys.
    Items (values) for each dict MUST be an array, and dict1 items are prioritized over dict2. For example:

    dict1 = {'text': ['a', 'b', 'c'], 'integer_inputs': [1, 2, 3]}
    dict2 = {'text': ['c', 'd', 'e', 'f'], 'dropdown': ['opt1', 'opt2']}

    merged = {'text': ['a', 'b', 'c', 'c', 'd', 'e', 'f'], 'integer_inputs': [1, 2, 3], 'dropdown': ['opt1', 'opt2']}
    """
    # res = OrderedDict({**dict1, **dict2})
    merged = OrderedDict()

    for key in dict1.keys():
        for key2 in dict1[key]:
            try:
                merged[key].append(key2)
            except KeyError:
                merged[key] = []
                merged[key].append(key2)
    for key in dict2.keys():
        for key2 in dict2[key]:
            try:
                merged[key].append(key2)
            except KeyError:
                merged[key] = []
                merged[key].append(key2)

    return merged


class ExternalTool:
    def __init__(self, user):
        try:
            self.user = user.username
            self.contact_email = user.email
        except AttributeError:  # TODO: remove once we have accounts set up.
            self.user = 'public'
            self.contact_email = 'ncrcrg.u19@gmail.com'
        self.pi_name = 'Gene Yeo'
        self.module = ''
        self.module_version = ''
        self.module_script = ''
        self.modality = ''
        self.id = ''
        self.name = ''

    def get_container(self, base_url):
        return ""

    def get_workflow(self):
        return ""


class Job:
    def __init__(self, user):
        try:
            self.user = user.username
            self.contact_email = user.email
        except AttributeError:  # TODO: remove once we have accounts set up.
            self.user = 'public'
            self.contact_email = 'ncrcrg.u19@gmail.com'
        self.pi_name = 'Gene Yeo'
        self.module = ''
        self.module_version = ''
        self.module_script = ''
        self.modality = ''
        self.id = ''
        self.name = ''

    def get_default_options(self):
        """
        Returns form options that apply to every Job.
        Hidden options need not to be filled out, but they do need to exist
        within the form.
        """
        return OrderedDict({
            'hidden': [
                ('Module', 'module', self.module),
                ('Module version', 'module_version', self.module_version),
                ('Module script', 'module_script', self.module_script),
                ('Module ID', 'tool_id', self.id),
            ],
            'text_inputs': [
                ('Job name', 'experiment_nickname', None, [alphanumeric_plus]),
                ('Project', 'project', 'default-project', [alphanumeric_plus]),
            ],

            'date_inputs': [
                ('Processing date', 'start_date', None),
            ],
            'textarea_inputs': [
                ('Job summary', 'experiment_summary', None),
            ],
            'dropdown_inputs': [
                (
                    'Organism',
                    'organism',
                    [
                        ('human', 'human'),
                        ('mouse', 'mouse')
                    ]
                )
            ],
        })

    def generate_default_job_submission_document(self):
        """
        Populates the following fields that do not require user input:
        - module
        - module_version
        - module_script
        - user
        - investigator
        - contact_email
        - modality
        - processing_date
        - shared
        """
        timestamp = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
        expt_dict = dict()
        expt_dict['module'] = self.module
        expt_dict['module_version'] = self.module_version
        expt_dict['module_script'] = self.module_script
        expt_dict['tool_id'] = self.id
        expt_dict['user'] = self.user
        expt_dict['investigator'] = self.user
        expt_dict['contact_email'] = self.contact_email
        expt_dict['modality'] = self.modality
        expt_dict['processing_date'] = timestamp
        expt_dict['cred-portal-shared'] = False
        return expt_dict


class FasterqdumpJob(Job):
    def __init__(self, user):
        """
        All of the tool-specific metadata
        :param post_data:
        :param user:
        """
        super().__init__(user)
        self.module = 'sratools'
        self.module_version = '2.11.0'
        self.module_script = 'wf_fasterq-dump'
        self.modality = 'genomics'
        self.id = 'Fasterqdump2110'  # cannot have . or { in name
        self.name = 'Fasterqdump'

    def get_container(self, base_url):
        return base_url

    def get_workflow(self):
        return ""

    def get_publication(self):
        return ""

    def get_description(self):
        return """
        Fasterq dump
        """

    def get_form_options(self, json_payload=None):
        """
        Returns the dictionary containing the inputs required for this tool.
        First, it needs to provide the default form options for an empty form.
        If json_payload is passed, this means that the form options must
        include data from a previous job (user is re-submitting a job from
        the job-status page). We will need to pre-pend this data as new
        defaults prior to populating the form.

        Keys MUST be one of the following (to match standard types):
            file_inputs,
            text_inputs,
            date_inputs,
            textarea_inputs,
            integer_inputs,
            dropdown_inputs


        :return final_form: json
            dictionary that populates default form options.
            @see forms.DynamicForm.__init__
        """
        default_options = self.get_default_options()  # options for every tool

        tool_options = OrderedDict({})

    def generate_job_submission_document(self, srr):
        """
        All of the job-specific metadata (params).
        First, we must populate the submission document (JSON file) with default fields. These fields
        @see generate_default_job_submission_document() are hidden fields that are important for the
        chosen pipeline to run, but do not require user input, hence they are not part of post_data.

        :param post_data: QueryDict
        :return:
        """
        default_expt_dict = self.generate_default_job_submission_document()

        job_expt_dict = {
            'aggr_nickname': srr + '-' + default_expt_dict['processing_date'],
            'project': 'SRA-downloads',
            'accession': srr,
            'split_files': False,
        }

        return OrderedDict({**default_expt_dict, **job_expt_dict})


class DownloaderJob(Job):
    def __init__(self, user):
        """
        All of the tool-specific metadata
        :param post_data:
        :param user:
        """
        super().__init__(user)
        self.module = 'sratools'
        self.module_version = '1'
        self.module_script = 'downloader'
        self.modality = 'genomics'
        self.id = 'DownloaderJob'  # cannot have . or { in name
        self.name = 'DownloaderJob'

    def get_container(self, base_url):
        return base_url

    def get_workflow(self):
        return ""

    def get_publication(self):
        return ""

    def get_description(self):
        return """
        Download files with wget.
        """

    def get_form_options(self, json_payload=None):
        """
        Returns the dictionary containing the inputs required for this tool.
        First, it needs to provide the default form options for an empty form.
        If json_payload is passed, this means that the form options must
        include data from a previous job (user is re-submitting a job from
        the job-status page). We will need to pre-pend this data as new
        defaults prior to populating the form.

        Keys MUST be one of the following (to match standard types):
            file_inputs,
            text_inputs,
            date_inputs,
            textarea_inputs,
            integer_inputs,
            dropdown_inputs


        :return final_form: json
            dictionary that populates default form options.
            @see forms.DynamicForm.__init__
        """
        default_options = self.get_default_options()  # options for every tool

        tool_options = OrderedDict({})

    def generate_job_submission_document(self, url):
        """
        All of the job-specific metadata (params).
        First, we must populate the submission document (JSON file) with default fields. These fields
        @see generate_default_job_submission_document() are hidden fields that are important for the
        chosen pipeline to run, but do not require user input, hence they are not part of post_data.

        :param post_data: QueryDict
        :return:
        """
        default_expt_dict = self.generate_default_job_submission_document()
        label = re.sub(r"[^a-zA-Z0-9]", '_', os.path.basename(url))
        job_expt_dict = {
            'aggr_nickname': label + '-' + default_expt_dict['processing_date'],
            'project': 'Downloads',
            'url': url,
        }

        return OrderedDict({**default_expt_dict, **job_expt_dict})


class OmeroDownloaderJob(Job):
    def __init__(self, user):
        """
        All of the tool-specific metadata
        :param post_data:
        :param user:
        """
        super().__init__(user)
        self.module = 'omeropy'
        self.module_version = '5.12.1'
        self.module_script = 'omeropy-downloader'
        self.modality = 'genomics'
        self.id = 'OmeroDownloaderJob'  # cannot have . or { in name
        self.name = 'OmeroDownloaderJob'

    def get_container(self, base_url):
        return base_url

    def get_workflow(self):
        return ""

    def get_publication(self):
        return ""

    def get_description(self):
        return """
        Download files with wget.
        """

    def get_form_options(self, json_payload=None):
        """
        Returns the dictionary containing the inputs required for this tool.
        First, it needs to provide the default form options for an empty form.
        If json_payload is passed, this means that the form options must
        include data from a previous job (user is re-submitting a job from
        the job-status page). We will need to pre-pend this data as new
        defaults prior to populating the form.

        Keys MUST be one of the following (to match standard types):
            file_inputs,
            text_inputs,
            date_inputs,
            textarea_inputs,
            integer_inputs,
            dropdown_inputs


        :return final_form: json
            dictionary that populates default form options.
            @see forms.DynamicForm.__init__
        """
        default_options = self.get_default_options()  # options for every tool

        tool_options = OrderedDict({})

    def generate_job_submission_document(self, project_id):
        """
        All of the job-specific metadata (params).
        First, we must populate the submission document (JSON file) with default fields. These fields
        @see generate_default_job_submission_document() are hidden fields that are important for the
        chosen pipeline to run, but do not require user input, hence they are not part of post_data.

        :param post_data: QueryDict
        :return:
        """
        default_expt_dict = self.generate_default_job_submission_document()
        label = re.sub(r"[^a-zA-Z0-9]", '_', os.path.basename(project_id))
        job_expt_dict = {
            'aggr_nickname': 'OMERO_' + label + '-' + default_expt_dict['processing_date'],
            'project': 'Downloads',
            'project_id': project_id,
        }

        return OrderedDict({**default_expt_dict, **job_expt_dict})


class DropseqtoolsJob(Job):
    def __init__(self, user):
        """
        All of the tool-specific metadata
        :param post_data:
        :param user:
        """
        super().__init__(user)
        self.module = 'dropseqtools'
        self.module_version = '1.13'
        self.module_script = 'dropseqtools-1.13-runner'
        self.modality = 'genomics'
        self.id = 'Dropseqtools113Job'  # cannot have . or { in name
        self.name = 'Dropseqtools'

    def get_container(self, base_url):
        return base_url

    def get_workflow(self):
        return "https://github.com/broadinstitute/Drop-seq"

    def get_publication(self):
        return "https://www.sciencedirect.com/science/article/pii/S0092867415005498"

    def get_description(self):
        return """
        Java tools for analyzing Drop-seq data.
        """

    def get_form_options(self, json_payload=None):
        """
        Returns the dictionary containing the inputs required for this tool.
        First, it needs to provide the default form options for an empty form.
        If json_payload is passed, this means that the form options must
        include data from a previous job (user is re-submitting a job from
        the job-status page). We will need to pre-pend this data as new
        defaults prior to populating the form.

        Keys MUST be one of the following (to match standard types):
            file_inputs,
            text_inputs,
            date_inputs,
            textarea_inputs,
            integer_inputs,
            dropdown_inputs


        :return final_form: json
            dictionary that populates default form options.
            @see forms.DynamicForm.__init__
        """
        default_options = self.get_default_options()  # options for every tool

        tool_options = OrderedDict({

            'dropdown_inputs': [
                (
                    'Reference dataset',
                    'reference_prefix',
                    [
                        ('hg19_ERCC_GSM1629193', 'hg19_ERCC_GSM1629193'),
                    ]
                )
            ],
            'file_inputs': [
                ('Read 1', 'read1', (".fastq.gz", ".fq.gz")),
                ('Read 2', 'read2', (".fastq.gz", ".fq.gz"))
            ],
            'text_inputs': [
                ('Sample ID', 'sample_id', None),
            ],
            'integer_inputs': [
                ('Read 1 Length', 'read1_length', 25),
                ('Read 2 Length', 'read2_length', 50),
                ('Core barcodes', 'core_barcodes', 2000),
                ('Expected barcodes', 'expected_barcodes', 2000)
            ]
        })
        return mergedict(default_options, tool_options)

    def generate_job_submission_document(self, post_data):
        """
        All of the job-specific metadata (params).
        First, we must populate the submission document (JSON file) with default fields. These fields
        @see generate_default_job_submission_document() are hidden fields that are important for the
        chosen pipeline to run, but do not require user input, hence they are not part of post_data.

        :param post_data: QueryDict
        :return:
        """
        default_expt_dict = self.generate_default_job_submission_document()

        job_expt_dict = {
            'project': post_data['project'],
            'experiment_nickname': post_data['experiment_nickname'],
            'aggr_nickname': post_data['experiment_nickname'] + '-' + default_expt_dict['processing_date'],
            'experiment_start_date': post_data['start_date'],
            'experiment_summary': post_data['experiment_summary'],
            'organism': post_data['organism'],

            'samples': [
                {
                    "sample_id": post_data['sample_id'],
                    "expt_id": post_data['sample_id'],
                    "read1": {
                        "path": post_data['read1'],
                        "class": "File"
                    },
                    "read1_length": int(post_data['read1_length']),
                    "read2": {
                        "path": post_data['read2'],
                        "class": "File"
                    },
                    "read2_length": int(post_data['read2_length']),
                    "core_barcodes": int(post_data['core_barcodes']),
                    "expected_barcodes": int(post_data['expected_barcodes']),
                    "species_genome_dir": {
                        "path": post_data['reference_prefix'] + "_star/",
                        "class": "Directory"
                    },
                    "species_reference_fasta": {
                        "path": post_data['reference_prefix'] + ".fasta",
                        "class": "File"
                    },
                    "species_reference_refFlat": {
                        "path": post_data['reference_prefix'] + ".refFlat",
                        "class": "File"
                    },
                    "characteristics": [],
                }
            ]
        }

        return OrderedDict({**default_expt_dict, **job_expt_dict})


class Dropseqtools113Job(DropseqtoolsJob):
    def __init__(self, user):
        """
        All of the tool-specific metadata
        :param post_data:
        :param user:
        """
        super().__init__(user)
        self.module = 'dropseqtools'
        self.module_version = '1.13'
        self.module_script = 'dropseqtools-1.13-runner'
        self.modality = 'genomics'
        self.id = 'Dropseqtools113Job'  # cannot have . or { in name
        self.name = 'Dropseqtools 1.13'

    def get_container(self, base_url):
        return os.path.join(base_url, "tools", "")


class CellrangerCountJob(Job):
    def __init__(self, user):
        """
        All of the tool-specific metadata
        :param post_data:
        :param user:
        """
        super().__init__(user)
        self.module = 'cellranger'
        self.module_version = '3.0.2'
        self.module_script = 'cellranger-3.0.2-runner'
        self.modality = 'genomics'
        self.id = 'CellrangerCount302Job'  # cannot have . or { in name
        self.name = 'Cellranger Count'

    def get_container(self, base_url):
        return base_url

    def get_workflow(self):
        return "https://support.10xgenomics.com/single-cell-gene-expression/software/pipelines/latest/using/count"

    def get_publication(self):
        return "https://doi.org/doi:10.1038/ncomms14049"

    def get_description(self):
        return """
        takes FASTQ files from cellranger mkfastq and performs alignment, filtering, barcode counting, and UMI counting.
        """

    def get_form_options(self, json_payload=None):
        """
        Returns the dictionary containing the inputs required for this tool.
        First, it needs to provide the default form options for an empty form.
        If json_payload is passed, this means that the form options must
        include data from a previous job (user is re-submitting a job from
        the job-status page). We will need to pre-pend this data as new
        defaults prior to populating the form.

        Keys MUST be one of the following (to match standard types):
            file_inputs,
            text_inputs,
            date_inputs,
            textarea_inputs,
            integer_inputs,
            dropdown_inputs


        :return final_form: json
            dictionary that populates default form options.
            @see forms.DynamicForm.__init__
        """
        default_options = self.get_default_options()  # options for every tool

        tool_options = OrderedDict({
            'dropdown_inputs': [
                (
                    'Reference dataset',
                    'transcriptome',
                    [
                        ('refdata-cellranger-hg19-3.0.0', 'refdata-cellranger-hg19-3.0.0'),
                        ('refdata-cellranger-hg19-1.2.0', 'refdata-cellranger-hg19-1.2.0'),
                        ('refdata-cellranger-mm10-3.0.0', 'refdata-cellranger-mm10-3.0.0'),
                        ('refdata-cellranger-mm10-1.2.0', 'refdata-cellranger-mm10-1.2.0'),
                        ('refdata-cellranger-hg19-and-mm10-3.0.0', 'refdata-cellranger-hg19-and-mm10-3.0.0'),
                    ]
                ),
                (
                    'Chemistry',
                    'chemistry',
                    [
                        ('auto', 'auto'),
                        ('SC3Pv1', 'SC3Pv1'),
                        ('SC3Pv2', 'SC3Pv2'),
                        ('SC3Pv3', 'SC3Pv3'),
                        ('SC5P-PE', 'SC5P-PE'),
                        ('SC5P-R2', 'SC5P-R2'),
                    ]
                )
            ],
            'file_inputs': [
                ('FASTQ Directory', 'fastq_dir', "/"),
            ],
            'text_inputs': [
                ('Sample ID', 'sample_id', None),
            ],
            'integer_inputs': [
                ('Read 1 Length', 'read1_length', 26),
                ('Read 2 Length', 'read2_length', 98),
                ('Expected cells', 'expect_cells', 3000),
            ]
        })
        return mergedict(default_options, tool_options)

    def generate_job_submission_document(self, post_data):
        """
        All of the job-specific metadata (params).
        First, we must populate the submission document (JSON file) with default fields. These fields
        @see generate_default_job_submission_document() are hidden fields that are important for the
        chosen pipeline to run, but do not require user input, hence they are not part of post_data.

        :param post_data: QueryDict
        :return:
        """
        default_expt_dict = self.generate_default_job_submission_document()
        sample_dict = {
            "chemistry": post_data['chemistry'],
            "library_nickname": post_data['experiment_nickname'],
            "library_prep": post_data['chemistry'],
            "read1_length": int(post_data['read1_length']),
            "read2_length": int(post_data['read2_length']),
            "characteristics": [],
            "expect_cells": int(post_data['expect_cells']),
            "fastq_dir": {
                "path": post_data['fastq_dir'],
                "class": "Directory"
            },
        }
        if 'sample_id' in post_data.keys():
            sample_dict['sample_id'] = post_data['sample_id']

        job_expt_dict = {
            'project': post_data['project'],
            'experiment_nickname': post_data['experiment_nickname'],
            'aggr_nickname': post_data['experiment_nickname'] + '-' + default_expt_dict['processing_date'],
            'experiment_start_date': post_data['start_date'],
            'experiment_summary': post_data['experiment_summary'],
            'organism': post_data['organism'],
            'transcriptome': {
                "class": "Directory",
                "path": post_data['transcriptome']
            },
            'samples': [sample_dict]
        }

        return OrderedDict({**default_expt_dict, **job_expt_dict})


class CellrangerCount302Job(CellrangerCountJob):
    def __init__(self, user):
        """
        All of the tool-specific metadata
        :param post_data:
        :param user:
        """
        super().__init__(user)
        self.module = 'cellranger'
        self.module_version = '3.0.2'
        self.module_script = 'cellranger-3.0.2-runner'
        self.modality = 'genomics'
        self.id = 'CellrangerCount302Job'  # cannot have . or { in name
        self.name = 'Cellranger Count 3.0.2'

    def get_container(self, base_url):
        return os.path.join(base_url, "tools", "cellranger-3.0.2.img")


class CellrangerCount600Job(CellrangerCountJob):
    def __init__(self, user):
        """
        All of the tool-specific metadata
        :param post_data:
        :param user:
        """
        super().__init__(user)
        self.module = 'cellranger'
        self.module_version = '6.0.0'
        self.module_script = 'cellranger-6.0.0-runner'
        self.modality = 'genomics'
        self.id = 'CellrangerCount600Job'  # cannot have . or { in name
        self.name = 'Cellranger Count 6.0.0'

    def get_container(self, base_url):
        return os.path.join(base_url, "tools", "cellranger-6.0.0.img")


class RnaseqJob(Job):
    def __init__(self, user):
        """
        All of the tool-specific metadata
        :param post_data:
        :param user:
        """
        super().__init__(user)
        self.module = 'rnaseq'
        self.module_version = '53d8c96'
        self.module_script = 'rnaseq-53d8c96-runner'
        self.modality = 'genomics'
        self.id = 'RnaseqJob'  # cannot have . or { in name
        self.name = 'RNASeq Pipeline from ENCODE DCC'

    def get_container(self, base_url):
        return base_url

    def get_workflow(self):
        return "https://github.com/ENCODE-DCC/rna-seq-pipeline"

    def get_publication(self):
        return ""

    def get_description(self):
        return """
        This is the ENCODE-DCC RNA-sequencing pipeline. The scope of the pipeline is to align reads, generate signal 
        tracks, and quantify genes and isoforms.
        """

    def get_form_options(self, json_payload=None):
        """
        Returns the dictionary containing the inputs required for this tool.
        First, it needs to provide the default form options for an empty form.
        If json_payload is passed, this means that the form options must
        include data from a previous job (user is re-submitting a job from
        the job-status page). We will need to pre-pend this data as new
        defaults prior to populating the form.

        Keys MUST be one of the following (to match standard types):
            file_inputs,
            text_inputs,
            date_inputs,
            textarea_inputs,
            integer_inputs,
            dropdown_inputs


        :return final_form: json
            dictionary that populates default form options.
            @see forms.DynamicForm.__init__
        """
        default_options = self.get_default_options()  # options for every tool

        tool_options = OrderedDict({
            'dropdown_inputs': [
                (
                    'Kallisto index',
                    'rna.kallisto_index',
                    [
                        ('ENCFF471EAM.idx', 'ENCFF471EAM.idx (GRCh38 v29 ENCODE)'),
                    ]
                ),
                (
                    'STAR index',
                    'rna.align_index',
                    [
                        ('ENCFF598IDH.tar.gz', 'ENCFF598IDH.tar.gz'),
                    ]
                ),
                (
                    'RSEM index',
                    'rna.rsem_index',
                    [
                        ('ENCFF285DRD.tar.gz', 'ENCFF285DRD.tar.gz'),
                    ]
                ),
                (
                    'ID to Gene file',
                    'rna.rna_qc_tr_id_to_gene_type_tsv',
                    [
                        ('gencodeV24pri-tRNAs-ERCC-phiX.transcript_id_to_genes.tsv',
                         'gencodeV24pri-tRNAs-ERCC-phiX.transcript_id_to_genes.tsv'),
                    ]
                ),
                (
                    'Chrom sizes',
                    'rna.chrom_sizes',
                    [
                        ('GRCh38_EBV.chrom.sizes.tsv', 'GRCh38_EBV.chrom.sizes.tsv'),
                    ]
                ),
                (
                    'Endedness',
                    'rna.endedness',
                    [
                        ('single', 'single'),
                        ('paired', 'paired'),
                    ]
                ),
                (
                    'Strandedness',
                    'rna.strandedness',
                    [
                        ('stranded', 'stranded'),
                        ('unstranded', 'unstranded'),
                    ]
                ),
                (
                    'Strandedness direction',
                    'rna.strandedness_direction',
                    [
                        ('reverse', 'reverse'),
                        ('forward', 'forward'),
                        ('unstranded', 'unstranded'),
                    ]
                )
            ],
            'multi_file_inputs': [
                ('Read 1', 'rna.fastqs_R1', None),
                ('Read 2', 'rna.fastqs_R2', None),
            ],
            'text_inputs': [
                ('Label', 'rna.bamroot', None),
            ],
        })
        return mergedict(default_options, tool_options)

    def generate_job_submission_document(self, post_data):
        """
        All of the job-specific metadata (params).
        First, we must populate the submission document (JSON file) with default fields. These fields
        @see generate_default_job_submission_document() are hidden fields that are important for the
        chosen pipeline to run, but do not require user input, hence they are not part of post_data.

        :param post_data: QueryDict
        :return:
        """
        default_expt_dict = self.generate_default_job_submission_document()
        job_expt_dict = {
            'project': post_data['project'],
            'experiment_nickname': post_data['experiment_nickname'],
            'aggr_nickname': post_data['experiment_nickname'] + '-' + default_expt_dict['processing_date'],
            'experiment_start_date': post_data['start_date'],
            'experiment_summary': post_data['experiment_summary'],
            'organism': post_data['organism'],
            "rna.bamroot": post_data['rna.bamroot'],
            "rna.chrom_sizes": post_data['rna.chrom_sizes'],
            "rna.endedness": post_data['rna.endedness'],
            "rna.fastqs_R1": [[r1] for r1 in post_data.getlist('rna.fastqs_R1')],
            "rna.fastqs_R2": [[r2] for r2 in post_data.getlist('rna.fastqs_R2')],
            "rna.align_index": post_data['rna.align_index'],
            "rna.kallisto_index": post_data['rna.kallisto_index'],
            "rna.rsem_index": post_data['rna.rsem_index'],
            "rna.rna_qc_tr_id_to_gene_type_tsv": post_data['rna.rna_qc_tr_id_to_gene_type_tsv'],
            "rna.strandedness_direction": post_data['rna.strandedness_direction'],
            "rna.strandedness": post_data['rna.strandedness'],
            "rna.rsem_ncpus": 8,
            "rna.rsem_ramGB": 30,
            "rna.align_ncpus": 8,
            "rna.align_ramGB": 40,
            "rna.bam_to_signals_ncpus": 2,
            "rna.bam_to_signals_ramGB": 16,
            "rna.kallisto_ramGB": 30,
            "rna.kallisto_number_of_threads": 8
        }

        return OrderedDict({**default_expt_dict, **job_expt_dict})


class ChipseqJob(Job):
    def __init__(self, user):
        """
        All of the tool-specific metadata
        :param post_data:
        :param user:
        """
        super().__init__(user)
        self.module = 'chipseq'
        self.module_version = '2.1.5'
        self.module_script = 'chipseq-2.1.5-runner'
        self.modality = 'genomics'
        self.id = 'ChipseqJob'  # cannot have . or { in name
        self.name = 'CHIPseq Pipeline from ENCODE DCC'

    def get_container(self, base_url):
        return ""

    def get_workflow(self):
        return "https://github.com/ENCODE-DCC/chip-seq-pipeline2"

    def get_publication(self):
        return ""

    def get_description(self):
        return """
        ENCODE Transcription Factor and Histone ChIP-Seq processing pipeline.
        """

    def get_form_options(self, json_payload=None):
        """
        Returns the dictionary containing the inputs required for this tool.
        First, it needs to provide the default form options for an empty form.
        If json_payload is passed, this means that the form options must
        include data from a previous job (user is re-submitting a job from
        the job-status page). We will need to pre-pend this data as new
        defaults prior to populating the form.

        Keys MUST be one of the following (to match standard types):
            file_inputs,
            text_inputs,
            date_inputs,
            textarea_inputs,
            integer_inputs,
            dropdown_inputs


        :return final_form: json
            dictionary that populates default form options.
            @see forms.DynamicForm.__init__
        """
        default_options = self.get_default_options()  # options for every tool

        tool_options = OrderedDict({
            'dropdown_inputs': [
                (
                    'Genome TSV',
                    'chip.genome_tsv',
                    [
                        ('hg38_chr19_chrM.tsv', 'hg38_chr19_chrM.tsv'),
                    ]
                ),
                (
                    'Pipeline type',
                    'chip.pipeline_type',
                    [
                        ('tf', 'tf'),
                        ('histone', 'histone'),
                        ('control', 'control'),
                    ]
                ),
                (
                    'Endedness',
                    'endedness',
                    [
                        ('single', 'single'),
                        ('paired', 'paired'),
                    ]
                ),
            ],
            'file_inputs': [
                ('Sample Rep 1, Read 1', 'chip.fastqs_rep1_R1', None),
                ('Sample Rep 2, Read 2', 'chip.fastqs_rep2_R1', None),
                ('Control Rep 1, Read 1', 'chip.ctl_fastqs_rep1_R1', None),
                ('Control Rep 2, Read 2', 'chip.ctl_fastqs_rep2_R1', None),
            ],
        })
        return mergedict(default_options, tool_options)

    def generate_job_submission_document(self, post_data):
        """
        All of the job-specific metadata (params).
        First, we must populate the submission document (JSON file) with default fields. These fields
        @see generate_default_job_submission_document() are hidden fields that are important for the
        chosen pipeline to run, but do not require user input, hence they are not part of post_data.

        :param post_data: QueryDict
        :return:
        """
        default_expt_dict = self.generate_default_job_submission_document()
        job_expt_dict = {
            'project': post_data['project'],
            'experiment_nickname': post_data['experiment_nickname'],
            'aggr_nickname': post_data['experiment_nickname'] + '-' + default_expt_dict['processing_date'],
            'experiment_start_date': post_data['start_date'],
            'experiment_summary': post_data['experiment_summary'],
            'organism': post_data['organism'],
            "chip.title": post_data['experiment_nickname'],
            "chip.description": post_data['experiment_summary'],
            "chip.genome_tsv": post_data['chip.genome_tsv'],
            "chip.pipeline_type": post_data['chip.pipeline_type'],
            "chip.paired_end": True if post_data['endedness'] == 'paired' else False,
            "chip.fastqs_rep1_R1": [r1 for r1 in post_data.getlist('chip.fastqs_rep1_R1')],
            "chip.fastqs_rep2_R1": [r1 for r1 in post_data.getlist('chip.fastqs_rep2_R1')],
            "chip.ctl_fastqs_rep1_R1": [r1 for r1 in post_data.getlist('chip.ctl_fastqs_rep1_R1')],
            "chip.ctl_fastqs_rep2_R1": [r1 for r1 in post_data.getlist('chip.ctl_fastqs_rep2_R1')],
        }

        return OrderedDict({**default_expt_dict, **job_expt_dict})


class Chipseq215Job(ChipseqJob):
    def __init__(self, user):
        """
        All of the tool-specific metadata
        :param post_data:
        :param user:
        """
        super().__init__(user)
        self.module = 'chipseq'
        self.module_version = '2.1.5'
        self.module_script = 'chipseq-2.1.5-runner'
        self.modality = 'genomics'
        self.id = 'Chipseq215Job'  # cannot have . or { in name
        self.name = 'CHIPseq Pipeline from ENCODE DCC'


class MrhgJob(Job):
    def __init__(self, user):
        """
        All of the tool-specific metadata
        :param post_data:
        :param user:
        """
        super().__init__(user)
        self.module = 'mrhg'
        self.module_version = '0.1.0'
        self.module_script = 'mrhg-0.1.0-runner'
        self.modality = 'ephys'
        self.id = 'MEAMapper 0.1.0'  # cannot have . or { in name
        self.name = 'Machine readable heatmap generator'

    def get_container(self, base_url):
        return os.path.join(base_url, "tools", "")

    def get_workflow(self):
        return ""

    def get_publication(self):
        return ""

    def get_description(self):
        return """
        Machine Readable Heatmap Generator
        """

    def get_form_options(self, json_payload=None):
        """
        Returns the dictionary containing the inputs required for this tool.
        First, it needs to provide the default form options for an empty form.
        If json_payload is passed, this means that the form options must
        include data from a previous job (user is re-submitting a job from
        the job-status page). We will need to pre-pend this data as new
        defaults prior to populating the form.

        Keys MUST be one of the following (to match standard types):
            file_inputs,
            text_inputs,
            date_inputs,
            textarea_inputs,
            integer_inputs,
            dropdown_inputs


        :return final_form: json
            dictionary that populates default form options.
            @see forms.DynamicForm.__init__
        """
        default_options = self.get_default_options()  # options for every tool

        tool_options = OrderedDict({

            'file_inputs': [
                ('Directory', 'rootBase', "/"),
            ],
        })
        return mergedict(default_options, tool_options)

    def generate_job_submission_document(self, post_data):
        """
        All of the job-specific metadata (params).
        First, we must populate the submission document (JSON file) with default fields. These fields
        @see generate_default_job_submission_document() are hidden fields that are important for the
        chosen pipeline to run, but do not require user input, hence they are not part of post_data.

        :param post_data: QueryDict
        :return:
        """
        default_expt_dict = self.generate_default_job_submission_document()

        job_expt_dict = {
            'project': post_data['project'],
            'experiment_nickname': post_data['experiment_nickname'],
            'aggr_nickname': post_data['experiment_nickname'] + '-' + default_expt_dict['processing_date'],
            'experiment_start_date': post_data['start_date'],
            'experiment_summary': post_data['experiment_summary'],
            'organism': post_data['organism'],
            'rootBase': '{}'.format(post_data['rootBase']),
            'rootDir': {
                'class': "Directory",
                'path': os.path.join(
                    settings.USS_ROOT,
                    '{}/work_dir/{}'.format(
                        self.user,
                        post_data['rootBase']
                    )
                )
            }
        }
        return OrderedDict({**default_expt_dict, **job_expt_dict})


class Mrhg010Job(MrhgJob):
    def __init__(self, user):
        """
        All of the tool-specific metadata
        :param post_data:
        :param user:
        """
        super().__init__(user)
        self.module = 'mrhg'
        self.module_version = '0.1.0'
        self.module_script = 'mrhg-0.1.0-runner'
        self.modality = 'ephys'
        self.id = 'Mrhg010Job'  # cannot have . or { in name
        self.name = 'Machine readable heatmap generator 0.1.0'

    def get_container(self, base_url):
        return ""


class Mrhg050Job(MrhgJob):
    def __init__(self, user):
        """
        All of the tool-specific metadata
        :param post_data:
        :param user:
        """
        super().__init__(user)
        self.module = 'mrhg'
        self.module_version = '0.5.0'
        self.module_script = 'meamapper-0.5.0-runner'
        self.modality = 'ephys'
        self.id = 'Mrhg050Job'  # cannot have . or { in name
        self.name = 'Machine readable heatmap generator 0.5.0'

    def get_container(self, base_url):
        return ""


class Mrhg060Job(MrhgJob):
    def __init__(self, user):
        """
        All of the tool-specific metadata
        :param post_data:
        :param user:
        """
        super().__init__(user)
        self.module = 'mrhg'
        self.module_version = '0.6.0'
        self.module_script = 'mrhg-0.6.0-runner'
        self.modality = 'ephys'
        self.id = 'Mrhg060Job'  # cannot have . or { in name
        self.name = 'Machine readable heatmap generator 0.6.0'

    def get_container(self, base_url):
        return ""


class GenoppiJob(Job):
    def __init__(self, user):
        """
        All of the tool-specific metadata
        :param post_data:
        :param user:
        """
        super().__init__(user)
        self.module = 'genoppi'
        self.module_version = 'b9ae5ca'
        self.module_script = 'genoppi-b9ae5ca-runner'
        self.modality = 'ephys'
        self.id = 'Genoppi b9ae5ca'  # cannot have . or { in name
        self.name = 'Genoppi'

    def get_container(self, base_url):
        return os.path.join(base_url, "tools", "genoppi_wrapper.sif")

    def get_workflow(self):
        return "https://github.com/lagelab/Genoppi"

    def get_publication(self):
        return "https://doi.org/10.1038/s41467-021-22648-5"

    def get_description(self):
        return """
        Genoppi is an open-source software for performing quality control and analyzing quantitative proteomic data. 
        """

    def get_form_options(self, json_payload=None):
        """
        Returns the dictionary containing the inputs required for this tool.
        First, it needs to provide the default form options for an empty form.
        If json_payload is passed, this means that the form options must
        include data from a previous job (user is re-submitting a job from
        the job-status page). We will need to pre-pend this data as new
        defaults prior to populating the form.

        Keys MUST be one of the following (to match standard types):
            file_inputs,
            text_inputs,
            date_inputs,
            textarea_inputs,
            integer_inputs,
            dropdown_inputs


        :return final_form: json
            dictionary that populates default form options.
            @see forms.DynamicForm.__init__
        """
        default_options = self.get_default_options()  # options for every tool

        tool_options = OrderedDict()
        return mergedict(default_options, tool_options)

    def generate_job_submission_document(self, post_data):
        """
        All of the job-specific metadata (params).
        First, we must populate the submission document (JSON file) with default fields. These fields
        @see generate_default_job_submission_document() are hidden fields that are important for the
        chosen pipeline to run, but do not require user input, hence they are not part of post_data.

        :param post_data: QueryDict
        :return:
        """
        default_expt_dict = self.generate_default_job_submission_document()
        job_expt_dict = {
            'project': post_data['project'],
            'experiment_nickname': post_data['experiment_nickname'],
            'aggr_nickname': post_data['experiment_nickname'] + '-' + default_expt_dict['processing_date'],
            'experiment_start_date': post_data['start_date'],
            'experiment_summary': post_data['experiment_summary'],
            'organism': post_data['organism'],
            'rootBase': "genoppi-{}".format(default_expt_dict['processing_date']),
            'rootDir': {
                'class': "Directory",
                'path': os.path.join(
                    settings.USS_ROOT,
                    '{}/work_dir/genoppi-{}'.format(
                        self.user,
                        default_expt_dict['processing_date']
                    )
                )
            }
        }
        return OrderedDict({**default_expt_dict, **job_expt_dict})


class Genoppib9ae5caJob(GenoppiJob):
    def __init__(self, user):
        """
        All of the tool-specific metadata
        :param post_data:
        :param user:
        """
        super().__init__(user)
        self.module = 'genoppi'
        self.module_version = 'b9ae5ca'
        self.module_script = 'genoppi-b9ae5ca-runner'
        self.modality = 'ephys'
        self.id = 'Genoppib9ae5caJob'  # cannot have . or { in name. This should match the pipeline[key]
        self.name = 'Genoppi b9ae5ca'

    def get_container(self, base_url):
        return os.path.join(base_url, "tools", "genoppi_wrapper.sif")


class CellrangerAggrJob(Job):
    def __init__(self, user):
        """
        All of the tool-specific metadata
        :param post_data:
        :param user:
        """
        super().__init__(user)
        self.module = 'cellranger'
        self.module_version = '3.0.2'
        self.module_script = 'cellranger-3.0.2-aggr-runner'
        self.modality = 'genomics'
        self.id = 'CellrangerAggr302Job'  # cannot have . or { in name
        self.name = 'Cellranger Aggr'

    def get_container(self, base_url):
        return "container URL"

    def get_workflow(self):
        return "https://support.10xgenomics.com/single-cell-gene-expression/software/pipelines/latest/using/aggregate"

    def get_publication(self):
        return "https://doi.org/doi:10.1038/ncomms14049"

    def get_description(self):
        return """
        The aggr pipeline aggregates the outputs for multiple samples generated via multiple runs of 
        cellranger count and performs analysis on the combined data. The aggr pipeline also aggregates the outputs for 
        multiple samples generated via single or multiple runs of cellranger multi.
        """

    def get_form_options(self, json_payload=None):
        """
        Returns the dictionary containing the inputs required for this tool.
        First, it needs to provide the default form options for an empty form.
        If json_payload is passed, this means that the form options must
        include data from a previous job (user is re-submitting a job from
        the job-status page). We will need to pre-pend this data as new
        defaults prior to populating the form.

        Keys MUST be one of the following (to match standard types):
            file_inputs,
            text_inputs,
            date_inputs,
            textarea_inputs,
            integer_inputs,
            dropdown_inputs


        :return final_form: json
            dictionary that populates default form options.
            @see forms.DynamicForm.__init__
        """
        default_options = self.get_default_options()  # options for every tool

        tool_options = OrderedDict({
            'dropdown_inputs': [
                (
                    'Normalization mode',
                    'normalize',
                    [
                        ('mapped', 'mapped'),
                        ('raw', 'raw'),
                        ('none', 'none'),
                    ]
                ),
            ],
            'multi_file_inputs': [
                ('Cellranger count output directory', 'h5_basedirs', "/"),
            ],
        })
        not_even_final_form = mergedict(default_options, tool_options)

        if json_payload is not None:  # TODO: refactor, this is really cumbersome.
            json_payload = json.loads(json_payload)

            norm_method = json_payload['normalize']
            not_even_final_form['dropdown_inputs'][1][2].insert(0, tuple(
                [norm_method, norm_method]))  # [0] index reserved for generic species choice
            # basedirs = []
            # for basedir in json_payload['h5_basedirs']:
            #     basedirs.append(basedir['path'])
            # not_even_final_form['multi_file_inputs'] = [
            #     ('Cellranger count output directory', 'h5_basedirs', basedirs)
            # ]('Job summary', 'experiment_summary', None),
            not_even_final_form['text_inputs'][0] = 'Job name', 'experiment_nickname', json_payload[
                'experiment_nickname'],
            not_even_final_form['text_inputs'][1] = 'Project', 'project', json_payload[
                'project'],
            not_even_final_form['textarea_inputs'][0] = 'Job summary', 'experiment_summary', json_payload[
                'experiment_summary'],
            final_form = not_even_final_form
            # print("Success! final form = {}".format(final_form))

        else:
            final_form = not_even_final_form

        return final_form

    def generate_job_submission_document(self, post_data):
        """
        All of the job-specific metadata (params).
        First, we must populate the submission document (JSON file) with default fields. These fields
        @see generate_default_job_submission_document() are hidden fields that are important for the
        chosen pipeline to run, but do not require user input, hence they are not part of post_data.

        :param post_data: QueryDict
        :return:
        """
        default_expt_dict = self.generate_default_job_submission_document()
        samples = []
        for h5_basedir in post_data.getlist('h5_basedirs'):
            samples.append(
                {
                    'class': 'Directory',
                    'path': h5_basedir
                }
            )
        job_expt_dict = {
            'project': post_data['project'],
            'experiment_nickname': post_data['experiment_nickname'],
            'aggr_nickname': post_data['experiment_nickname'] + '-' + default_expt_dict['processing_date'],
            'experiment_start_date': post_data['start_date'],
            'experiment_summary': post_data['experiment_summary'],
            'organism': post_data['organism'],
            'normalize': post_data['normalize'],
            'h5_basedirs': samples
        }

        return OrderedDict({**default_expt_dict, **job_expt_dict})


class CellrangerAggr302Job(CellrangerAggrJob):
    def __init__(self, user):
        """
        All of the tool-specific metadata
        :param post_data:
        :param user:
        """
        super().__init__(user)
        self.module = 'cellranger'
        self.module_version = '3.0.2'
        self.module_script = 'cellranger-3.0.2-aggr-runner'
        self.modality = 'genomics'
        self.id = 'CellrangerAggr302Job'  # cannot have . or { in name. PascalCase.
        self.name = 'Cellranger Aggr 3.0.2'

    def get_container(self, base_url):
        return os.path.join(base_url, "tools", "cellranger-3.0.2.img")


class CellrangerFromSRXJob(Job):
    def __init__(self, user):
        """
        All of the tool-specific metadata
        :param post_data:
        :param user:
        """
        super().__init__(user)
        self.module = 'cellranger'
        self.module_version = '3.0.2'
        self.module_script = 'cellranger-3.0.2-bam-runner'
        self.modality = 'genomics'
        self.id = 'CellrangerFromSRXJob'  # cannot have . or { in name
        self.name = 'Cellranger from BAM file URL'

    def get_container(self, base_url):
        return os.path.join(base_url, "tools", "cellranger-3.0.2.img")

    def get_workflow(self):
        return "https://support.10xgenomics.com/single-cell-gene-expression/software/pipelines/latest/using/count"

    def get_description(self):
        return """
        This workflow runs cellranger count using a URL that points to a BAM file
        """

    def get_publication(self):
        return "https://doi.org/doi:10.1038/ncomms14049"

    def get_form_options(self, json_payload=None):
        """
        Returns the dictionary containing the inputs required for this tool.
        First, it needs to provide the default form options for an empty form.
        If json_payload is passed, this means that the form options must
        include data from a previous job (user is re-submitting a job from
        the job-status page). We will need to pre-pend this data as new
        defaults prior to populating the form.

        Keys MUST be one of the following (to match standard types):
            file_inputs,
            text_inputs,
            date_inputs,
            textarea_inputs,
            integer_inputs,
            dropdown_inputs


        :return final_form: json
            dictionary that populates default form options.
            @see forms.DynamicForm.__init__
        """
        default_options = self.get_default_options()  # options for every tool

        tool_options = OrderedDict({
            'dropdown_inputs': [
                (
                    'Reference dataset',
                    'transcriptome',
                    [
                        ('refdata-cellranger-hg19-3.0.0', 'refdata-cellranger-hg19-3.0.0'),
                        ('refdata-cellranger-hg19-1.2.0', 'refdata-cellranger-hg19-1.2.0'),
                        ('refdata-cellranger-mm10-3.0.0', 'refdata-cellranger-mm10-3.0.0'),
                        ('refdata-cellranger-mm10-1.2.0', 'refdata-cellranger-mm10-1.2.0'),
                        ('refdata-cellranger-hg19-and-mm10-3.0.0', 'refdata-cellranger-hg19-and-mm10-3.0.0'),
                    ]
                ),
                (
                    'Chemistry',
                    'chemistry',
                    [
                        ('auto', 'auto'),
                        ('SC3Pv1', 'SC3Pv1'),
                        ('SC3Pv2', 'SC3Pv2'),
                        ('SC3Pv3', 'SC3Pv3'),
                        ('SC5P-PE', 'SC5P-PE'),
                        ('SC5P-R2', 'SC5P-R2'),
                    ]
                ),
                (
                    'cr11',
                    'cr11',
                    [('true', 'true'), ('false', 'false')],
                )
            ],
            'text_inputs': [
                ('SRX accession', 'srx', None)
            ],
            'integer_inputs': [
                ('Read 1 Length', 'read1_length', 26),
                ('Read 2 Length', 'read2_length', 98),
                ('Expected cells', 'expect_cells', 3000),
            ]
        })
        return mergedict(default_options, tool_options)

    def generate_job_submission_document(self, post_data):
        """
        All of the job-specific metadata (params).
        First, we must populate the submission document (JSON file) with default fields. These fields
        @see generate_default_job_submission_document() are hidden fields that are important for the
        chosen pipeline to run, but do not require user input, hence they are not part of post_data.

        :param post_data: QueryDict
        :return:
        """
        host = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/'
        url = host + f'efetch.fcgi?db=sra&id={post_data["srx"]}'
        response = urllib.request.urlopen(url)
        default_expt_dict = self.generate_default_job_submission_document()
        cr11 = True if post_data['cr11'] == 'true' else False
        metadata_set = get_10x_metadata_from_xml(
            input_string=response.read(),
            transcriptome=post_data['transcriptome'],
            chemistry=post_data['chemistry'],
            cr11=cr11,
            read1_length=post_data['read1_length'],
            read2_length=post_data['read2_length'],
            expect_cells=post_data['expect_cells']
        )

        job_expt_dicts = []

        for metadata in metadata_set:
            job_expt_dict = {
                'project': post_data['project'],
                'experiment_nickname': post_data['experiment_nickname'],
                'aggr_nickname': post_data['experiment_nickname'] + '-' + default_expt_dict['processing_date'],
                'experiment_start_date': post_data['start_date'],
                'experiment_summary': post_data['experiment_summary'],
                'organism': post_data['organism'],
                'transcriptome': {
                    "class": "Directory",
                    "path": post_data['transcriptome']
                },
            }
            job_expt_dicts.append(
                OrderedDict({**default_expt_dict, **metadata, **job_expt_dict})
            )

        return job_expt_dicts


class CellrangerFromSRX302Job(CellrangerFromSRXJob):
    def __init__(self, user):
        """
        All of the tool-specific metadata
        :param post_data:
        :param user:
        """
        super().__init__(user)
        self.module = 'cellranger'
        self.module_version = '3.0.2'
        self.module_script = 'cellranger-3.0.2-bam-runner'
        self.modality = 'genomics'
        self.id = 'CellrangerFromSRX302Job'  # cannot have . or { in name
        self.name = 'Cellranger Count 3.0.2 from (SRX accession)'

    def get_container(self, base_url):
        return os.path.join(base_url, "tools", "cellranger-3.0.2.img")


class ToppcellJob(Job):
    def __init__(self, user):
        """
        All of the tool-specific metadata
        :param post_data:
        :param user:
        """
        super().__init__(user)
        self.module = 'toppcell'
        self.module_version = '20200612'
        self.module_script = 'toppcell-20200612-runner'
        self.modality = 'genomics'
        self.id = 'ToppcellJob'  # cannot have . or { in name
        self.name = 'Toppcell'

    def get_container(self, base_url):
        return "container URL"

    def get_workflow(self):
        return "https://scienceblog.cincinnatichildrens.org/single-cell-web-portal-covid-19-immune-host-responses/"

    def get_description(self):
        return """
        ToppCell: A Hierarchical Modular Single Cell Gene Expression Analysis System 
        """

    def get_publication(self):
        return "https://www.cell.com/iscience/fulltext/S2589-0042(21)01083-X"

    def get_form_options(self, json_payload=None):
        """
        Returns the dictionary containing the inputs required for this tool.
        First, it needs to provide the default form options for an empty form.
        If json_payload is passed, this means that the form options must
        include data from a previous job (user is re-submitting a job from
        the job-status page). We will need to pre-pend this data as new
        defaults prior to populating the form.

        Keys MUST be one of the following (to match standard types):
            file_inputs,
            text_inputs,
            date_inputs,
            textarea_inputs,
            integer_inputs,
            dropdown_inputs


        :return final_form: json
            dictionary that populates default form options.
            @see forms.DynamicForm.__init__
        """
        default_options = self.get_default_options()  # options for every tool

        tool_options = OrderedDict({

            'dropdown_inputs': [
                (
                    'Matrix directory',
                    'matrix_dir',
                    [
                        ('filtered_feature_bc_matrix', 'filtered_feature_bc_matrix'),
                        ('raw_feature_bc_matrix', 'raw_feature_bc_matrix'),
                    ]
                ),
                (
                    'Clevel',
                    'clevel',
                    [('cell_type', 'cell_type')]
                ),
                (
                    'Transpose',
                    'transpose',
                    [('true', 'true')],
                ),
                (
                    'Factor',
                    'factor',
                    [('graphclust', 'graphclust')]
                ),
                (
                    'Cellranger version',
                    'cellranger_version',
                    [('3.0.2', '3.0.2')]
                )
            ],
            'file_inputs': [
                ('Cellranger output directory', 'outs', ("outs/")),
            ],
            'text_inputs': [
                ('Shred title', 'shred_title', 'Title'),
                ('Display name', 'display_name', 'Project'),
                ('Dataset title', 'dataset_title', 'Title'),
                ('Output directory', 'shred_output_directory', 'output')
            ],
            'textarea_inputs': [
                ('Dataset description', 'dataset_description', f'Toppcell ({self.module_script})')
            ],
            'integer_inputs': [
                ('ngenes', 'ngenes', 200),
                ('port', 'port', 0)
            ]
        })
        return mergedict(default_options, tool_options)

    def generate_job_submission_document(self, post_data):
        """
        All of the job-specific metadata (params).
        First, we must populate the submission document (JSON file) with default fields. These fields
        @see generate_default_job_submission_document() are hidden fields that are important for the
        chosen pipeline to run, but do not require user input, hence they are not part of post_data.

        :param post_data: QueryDict
        :return:
        """
        default_expt_dict = self.generate_default_job_submission_document()

        job_expt_dict = {
            'project': post_data['project'],
            'experiment_nickname': post_data['experiment_nickname'],
            'aggr_nickname': post_data['experiment_nickname'] + '-' + default_expt_dict['processing_date'],
            'experiment_start_date': post_data['start_date'],
            'experiment_summary': post_data['experiment_summary'],
            'organism': post_data['organism'],
            'species': post_data['organism'],
        }
        for field in [
            'matrix_dir', 'ngenes', 'clevel', 'display_name',
            'shred_title', 'dataset_description', 'dataset_title', 'factor', 'project',
            'cellranger_version', 'shred_output_directory'
        ]:
            job_expt_dict[field] = post_data[field]
        for field in [
            'ngenes', 'port'
        ]:
            job_expt_dict[field] = int(post_data[field])
        job_expt_dict['outs'] = {'class': 'Directory', 'path': post_data['outs']}
        transpose = True if post_data['transpose'] == 'true' else False
        job_expt_dict['transpose'] = transpose
        return OrderedDict({**default_expt_dict, **job_expt_dict})


class Toppcell20200612Job(ToppcellJob):
    def __init__(self, user):
        """
        All of the tool-specific metadata
        :param post_data:
        :param user:
        """
        super().__init__(user)
        self.module = 'toppcell'
        self.module_version = '20200612'
        self.module_script = 'toppcell-20200612-runner'
        self.modality = 'genomics'
        self.id = 'Toppcell20200612Job'  # cannot have . or { in name
        self.name = 'Toppcell version 20200612'

    def get_container(self, base_url):
        return os.path.join(base_url, "tools", "ebardes_toppcell-2020-06-12-4d067c2e60c6.simg")


class MaxquantJob(Job):
    def __init__(self, user):
        """
        All of the tool-specific metadata
        :param post_data:
        :param user:
        """
        super().__init__(user)
        self.module = 'maxquant'
        self.module_version = '1.6.3.4'
        self.module_script = 'maxquant-1.6.3.4-runner'
        self.modality = 'proteomics'
        self.id = 'MaxquantJob'  # cannot have . or { in name
        self.name = 'Maxquant'

    def get_container(self, base_url):
        return "container URL"

    def get_workflow(self):
        return "https://www.maxquant.org/"

    def get_publication(self):
        return "https://experiments.springernature.com/articles/10.1038/nprot.2016.136"

    def get_description(self):
        return """
        MaxQuant is a quantitative proteomics software package designed for analyzing large mass-spectrometric data sets. 
        It is specifically aimed at high-resolution MS data. 
        """

    def get_form_options(self, json_payload=None):
        """
        Returns the dictionary containing the inputs required for this tool.
        First, it needs to provide the default form options for an empty form.
        If json_payload is passed, this means that the form options must
        include data from a previous job (user is re-submitting a job from
        the job-status page). We will need to pre-pend this data as new
        defaults prior to populating the form.

        Keys MUST be one of the following (to match standard types):
            file_inputs,
            text_inputs,
            date_inputs,
            textarea_inputs,
            integer_inputs,
            dropdown_inputs


        :return final_form: json
            dictionary that populates default form options.
            @see forms.DynamicForm.__init__
        """
        default_options = self.get_default_options()  # options for every tool

        tool_options = OrderedDict({

            'dropdown_inputs': [
                (
                    'Reference file',
                    'fasta_file',
                    [
                        ('UP000005640_9606.fasta', 'UP000005640_9606.fasta'),
                        ('uniprot-proteome_UP000005640.fasta', 'uniprot-proteome_UP000005640.fasta'),
                    ]
                )
            ],
            'file_inputs': [
                ('Raw files', 'raw_file_directory', ("/")),
            ],
            'text_inputs': [
                ('Identifier parser rule', 'identifier_parse_rule', '>.*\|(.*)\|'),
            ],
            'integer_inputs': [
                ('num_threads', 'num_threads', 8),
            ]
        })
        return mergedict(default_options, tool_options)

    def generate_job_submission_document(self, post_data):
        """
        All of the job-specific metadata (params).
        First, we must populate the submission document (JSON file) with default fields. These fields
        @see generate_default_job_submission_document() are hidden fields that are important for the
        chosen pipeline to run, but do not require user input, hence they are not part of post_data.

        :param post_data: QueryDict
        :return:
        """
        default_expt_dict = self.generate_default_job_submission_document()

        job_expt_dict = {
            'project': post_data['project'],
            'experiment_nickname': post_data['experiment_nickname'],
            'aggr_nickname': post_data['experiment_nickname'] + '-' + default_expt_dict['processing_date'],
            'experiment_start_date': post_data['start_date'],
            'experiment_summary': post_data['experiment_summary'],
            'organism': post_data['organism'],
            'species': post_data['organism'],
        }
        for field in [
            'identifier_parse_rule'
        ]:
            job_expt_dict[field] = post_data[field]
        for field in [
            'num_threads'
        ]:
            job_expt_dict[field] = int(post_data[field])
        job_expt_dict['fasta_file'] = {'class': 'File', 'path': post_data['fasta_file']}
        job_expt_dict['raw_file_directory'] = {'class': 'Directory', 'path': post_data['raw_file_directory']}

        return OrderedDict({**default_expt_dict, **job_expt_dict})


class Maxquant1634Job(MaxquantJob):
    def __init__(self, user):
        """
        All of the tool-specific metadata
        :param post_data:
        :param user:
        """
        super().__init__(user)
        self.module = 'maxquant'
        self.module_version = '1.6.3.4'
        self.module_script = 'maxquant-1.6.3.4-runner'
        self.modality = 'proteomics'
        self.id = 'Maxquant1634Job'  # cannot have . or { in name
        self.name = 'Maxquant 1.6.3.4'

    def get_container(self, base_url):
        return os.path.join(base_url, "tools", "maxquant-1.6.3.4.img")


class Maxquant161043Job(MaxquantJob):
    def __init__(self, user):
        """
        All of the tool-specific metadata
        :param post_data:
        :param user:
        """
        super().__init__(user)
        self.module = 'maxquant'
        self.module_version = '1.6.10.43'
        self.module_script = 'maxquant-1.6.10.43-runner'
        self.modality = 'proteomics'
        self.id = 'Maxquant161043Job'  # cannot have . or { in name
        self.name = 'Maxquant 1.6.10.43'

    def get_container(self, base_url):
        return os.path.join(base_url, "tools", "maxquant-1.6.10.43.img")


class SaintexpressJob(Job):
    def __init__(self, user):
        """
        All of the tool-specific metadata
        :param post_data:
        :param user:
        """
        super().__init__(user)
        self.module = 'saintexpress'
        self.module_version = '3.6.3'
        self.module_script = 'saintexpress-3.6.3-runner'
        self.modality = 'proteomics'
        self.id = 'SaintexpressJob'  # cannot have . or { in name
        self.name = 'SAINTExpress'

    def get_container(self, base_url):
        return "container URL"

    def get_workflow(self):
        return "http://saint-apms.sourceforge.net/"

    def get_publication(self):
        return "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC4102138/"

    def get_description(self):
        return """
        Significance Analysis of INTeractome (SAINT) consists of a series of software tools for assigning confidence 
        scores to protein-protein interactions based on quantitative proteomics data in AP-MS experiments.
        """

    def get_form_options(self, json_payload=None):
        """
        Returns the dictionary containing the inputs required for this tool.
        First, it needs to provide the default form options for an empty form.
        If json_payload is passed, this means that the form options must
        include data from a previous job (user is re-submitting a job from
        the job-status page). We will need to pre-pend this data as new
        defaults prior to populating the form.

        Keys MUST be one of the following (to match standard types):
            file_inputs,
            text_inputs,
            date_inputs,
            textarea_inputs,
            integer_inputs,
            dropdown_inputs


        :return final_form: json
            dictionary that populates default form options.
            @see forms.DynamicForm.__init__
        """
        default_options = self.get_default_options()  # options for every tool

        tool_options = OrderedDict({

            'file_inputs': [
                ('Interactions File', 'interactions', (".txt")),
                ('Preys File', 'preys', (".txt")),
                ('Baits File', 'baits', (".txt"))
            ],
            'integer_inputs': [
                ('ncounts', 'ncounts', 100),
                ('ncontrols', 'ncontrols', 100),
            ],
            'float_inputs': [
                ('Frequency', 'frequency', 0.5),
            ]
        })
        return mergedict(default_options, tool_options)

    def generate_job_submission_document(self, post_data):
        """
        All of the job-specific metadata (params).
        First, we must populate the submission document (JSON file) with default fields. These fields
        @see generate_default_job_submission_document() are hidden fields that are important for the
        chosen pipeline to run, but do not require user input, hence they are not part of post_data.

        :param post_data: QueryDict
        :return:
        """
        default_expt_dict = self.generate_default_job_submission_document()

        job_expt_dict = {
            'project': post_data['project'],
            'experiment_nickname': post_data['experiment_nickname'],
            'aggr_nickname': post_data['experiment_nickname'] + '-' + default_expt_dict['processing_date'],
            'experiment_start_date': post_data['start_date'],
            'experiment_summary': post_data['experiment_summary'],
            'organism': post_data['organism'],
            'species': post_data['organism'],
        }
        for field in [
            'frequency'
        ]:
            job_expt_dict[field] = float(post_data[field])
        for field in [
            'ncounts', 'ncontrols'
        ]:
            job_expt_dict[field] = int(post_data[field])
        job_expt_dict['interactions'] = {'class': 'File', 'path': post_data['interactions']}
        job_expt_dict['baits'] = {'class': 'File', 'path': post_data['baits']}
        job_expt_dict['preys'] = {'class': 'File', 'path': post_data['preys']}
        return OrderedDict({**default_expt_dict, **job_expt_dict})


class Saintexpress363Job(SaintexpressJob):
    def __init__(self, user):
        """
        All of the tool-specific metadata
        :param post_data:
        :param user:
        """
        super().__init__(user)
        self.module = 'saintexpress'
        self.module_version = '3.6.3'
        self.module_script = 'saintexpress-3.6.3-runner'
        self.modality = 'proteomics'
        self.id = 'Saintexpress363Job'  # cannot have . or { in name
        self.name = 'SAINTExpress 3.6.3'

    def get_container(self, base_url):
        return os.path.join(base_url, "tools", "saintexpress-3.6.3.img")


class ComppassJob(Job):
    def __init__(self, user):
        """
        All of the tool-specific metadata
        :param post_data:
        :param user:
        """
        super().__init__(user)
        self.module = 'comppass'
        self.module_version = 'de872c0'
        self.module_script = 'comppass-de872c0-runner'
        self.modality = 'proteomics'
        self.id = 'ComppassJob'  # cannot have . or { in name
        self.name = 'compPASS'

    def get_container(self, base_url):
        return "container URL"

    def get_workflow(self):
        return ""

    def get_publication(self):
        return ""

    def get_description(self):
        return """
        CompPASS is an acronym for Comparative Proteomic Analysis Software Suite and as the name implies, it 
        relies on an unbiased comparative approach for identifying high-confidence candidate interacting proteins 
        (HCIPs for short) from the hundreds of proteins typically identified in IP-MS/MS experiments.
        """

    def get_form_options(self, json_payload=None):
        """
        Returns the dictionary containing the inputs required for this tool.
        First, it needs to provide the default form options for an empty form.
        If json_payload is passed, this means that the form options must
        include data from a previous job (user is re-submitting a job from
        the job-status page). We will need to pre-pend this data as new
        defaults prior to populating the form.

        Keys MUST be one of the following (to match standard types):
            file_inputs,
            text_inputs,
            date_inputs,
            textarea_inputs,
            integer_inputs,
            dropdown_inputs


        :return final_form: json
            dictionary that populates default form options.
            @see forms.DynamicForm.__init__
        """
        default_options = self.get_default_options()  # options for every tool

        tool_options = OrderedDict({

            'file_inputs': [
                ('Interactions File', 'interactions_file', (".txt")),
            ],
        })
        return mergedict(default_options, tool_options)

    def generate_job_submission_document(self, post_data):
        """
        All of the job-specific metadata (params).
        First, we must populate the submission document (JSON file) with default fields. These fields
        @see generate_default_job_submission_document() are hidden fields that are important for the
        chosen pipeline to run, but do not require user input, hence they are not part of post_data.

        :param post_data: QueryDict
        :return:
        """
        default_expt_dict = self.generate_default_job_submission_document()

        job_expt_dict = {
            'project': post_data['project'],
            'experiment_nickname': post_data['experiment_nickname'],
            'aggr_nickname': post_data['experiment_nickname'] + '-' + default_expt_dict['processing_date'],
            'experiment_start_date': post_data['start_date'],
            'experiment_summary': post_data['experiment_summary'],
            'organism': post_data['organism'],
            'species': post_data['organism'],
            'interactions_file': {'class': 'File', 'path': post_data['interactions_file']}
        }
        return OrderedDict({**default_expt_dict, **job_expt_dict})


class Comppassde872c0Job(ComppassJob):
    def __init__(self, user):
        """
        All of the tool-specific metadata
        :param post_data:
        :param user:
        """
        super().__init__(user)
        self.module = 'comppass'
        self.module_version = 'de872c0'
        self.module_script = 'comppass-de872c0-runner'
        self.modality = 'proteomics'
        self.id = 'ComppassJob'  # cannot have . or { in name
        self.name = 'compPASS de872c0'

    def get_container(self, base_url):
        return os.path.join(base_url, "tools", "comppass-de872c0.img")


class AzimuthJob(Job):
    def __init__(self, user):
        """
        All of the tool-specific metadata
        :param post_data:
        :param user:
        """
        super().__init__(user)
        self.module = 'azimuth'
        self.module_version = '0.4.3'
        self.module_script = 'azimuth-0.4.3-runner'
        self.modality = 'genomics'
        self.id = 'Azimuth 0.4.3'  # cannot have . or { in name
        self.name = 'Azimuth'

    def get_container(self, base_url):
        return os.path.join(base_url, "tools", "azimuth_0.4.3.sif")

    def get_workflow(self):
        return "https://azimuth.hubmapconsortium.org/"

    def get_publication(self):
        return "https://www.cell.com/cell/fulltext/S0092-8674(21)00583-3"

    def get_description(self):
        return """
        Azimuth is a Shiny app demonstrating a query-reference mapping algorithm for single-cell data.
        """

    def get_form_options(self, json_payload=None):
        """
        Returns the dictionary containing the inputs required for this tool.
        First, it needs to provide the default form options for an empty form.
        If json_payload is passed, this means that the form options must
        include data from a previous job (user is re-submitting a job from
        the job-status page). We will need to pre-pend this data as new
        defaults prior to populating the form.

        Keys MUST be one of the following (to match standard types):
            file_inputs,
            text_inputs,
            date_inputs,
            textarea_inputs,
            integer_inputs,
            dropdown_inputs


        :return final_form: json
            dictionary that populates default form options.
            @see forms.DynamicForm.__init__
        """
        default_options = self.get_default_options()  # options for every tool

        tool_options = OrderedDict({

            'dropdown_inputs': [
                (
                    'Reference',
                    'reference_dir',
                    [
                        ('human_bmmc-1.0.0', 'human_bmmc-1.0.0'),
                        ('human_fetal_development-1.0.0', 'human_fetal_development-1.0.0'),
                        ('human_motor_cortex-1.0.0', 'human_motor_cortex-1.0.0'),
                        ('human_pbmc-1.0.0', 'human_pbmc-1.0.0'),
                        ('lung-1.0.0', 'lung-1.0.0'),
                    ]
                )
            ],
        })
        return mergedict(default_options, tool_options)

    def generate_job_submission_document(self, post_data):
        """
        All of the job-specific metadata (params).
        First, we must populate the submission document (JSON file) with default fields. These fields
        @see generate_default_job_submission_document() are hidden fields that are important for the
        chosen pipeline to run, but do not require user input, hence they are not part of post_data.

        :param post_data: QueryDict
        :return:
        """
        default_expt_dict = self.generate_default_job_submission_document()
        job_expt_dict = {
            'project': post_data['project'],
            'experiment_nickname': post_data['experiment_nickname'],
            'aggr_nickname': post_data['experiment_nickname'] + '-' + default_expt_dict['processing_date'],
            'experiment_start_date': post_data['start_date'],
            'experiment_summary': post_data['experiment_summary'],
            'organism': post_data['organism'],
            'reference_dir': {
                'class': "Directory",
                'path': '/projects/ps-yeolab4/NCRCRG/refs/azimuth/{}/'.format(
                    post_data['reference_dir']
                )
            }
        }
        return OrderedDict({**default_expt_dict, **job_expt_dict})


class Azimuth043Job(AzimuthJob):
    def __init__(self, user):
        """
        All of the tool-specific metadata
        :param post_data:
        :param user:
        """
        super().__init__(user)
        self.module = 'azimuth'
        self.module_version = '0.4.3'
        self.module_script = 'azimuth-0.4.3-runner'
        self.modality = 'genomics'
        self.id = 'Azimuth043Job'  # cannot have . or { in name
        self.name = 'Azimuth 0.4.3'

    def get_container(self, base_url):
        return os.path.join(base_url, "tools", "azimuth_0.4.3.sif")


class Geko(ExternalTool):
    def __init__(self, user):
        """
        All of the tool-specific metadata
        :param post_data:
        :param user:
        """
        super().__init__(user)
        self.modality = 'genomics'
        self.id = 'GEKO'  # cannot have . or { in name
        self.name = 'GEKO'

    def get_description(self):
        return """
        Gene Expression in Cortical Organoids (GEKO) allows the concomitant examination of gene trajectories in hCS 
        and in BrainSpan.
        """

    def get_workflow(self):
        return "https://labs.dgsom.ucla.edu/geschwind/files/view/html/GECO.html"

    def get_publication(self):
        return "https://doi.org/10.1038/s41593-021-00802-y"


class ScArches035(ExternalTool):
    def __init__(self, user):
        """
        All of the tool-specific metadata
        :param post_data:
        :param user:
        """
        super().__init__(user)
        self.modality = 'genomics'
        self.id = 'scArches035'  # cannot have . or { in name
        self.name = 'scArches 0.3.5'

    def get_description(self):
        return """
        scArches is a package to integrate newly produced single-cell datasets into integrated reference atlases. Our 
        method can facilitate large collaborative projects with decentralized training and integration of multiple 
        datasets by different groups.
        """

    def get_container(self, base_url):
        return os.path.join(base_url, "tools", "scarches_0.3.5.sif")

    def get_publication(self):
        return "https://www.nature.com/articles/s41587-021-01001-7"

    def get_workflow(self):
        return "https://github.com/theislab/scarches"


class Seurat403(ExternalTool):
    def __init__(self, user):
        """
        All of the tool-specific metadata
        :param post_data:
        :param user:
        """
        super().__init__(user)
        self.modality = 'genomics'
        self.id = 'Seurat403'  # cannot have . or { in name
        self.name = 'Seurat 4.0.3 '

    def get_description(self):
        return """
        Seurat is an R package designed for QC, analysis, and exploration of single-cell RNA-seq data. Seurat aims to 
        enable users to identify and interpret sources of heterogeneity from single-cell transcriptomic measurements, 
        and to integrate diverse types of single-cell data.
        """

    def get_container(self, base_url):
        return os.path.join(base_url, "tools", "seurat_4.0.3.sif")

    def get_workflow(self):
        return "https://satijalab.org/seurat/"

    def get_publication(self):
        return "https://doi.org/10.1016/j.cell.2021.04.048"


class ProteomicsEssentials(ExternalTool):
    def __init__(self, user):
        """
        All of the tool-specific metadata
        :param post_data:
        :param user:
        """
        super().__init__(user)
        self.modality = 'proteomics'
        self.id = 'ProteomicsEssentials'  # cannot have . or { in name
        self.name = 'ProteomicsEssentials'

    def get_description(self):
        return """
        Contains a selection of essential software packages for analyzing proteomics-type data. Please see the 
        External link (Dockerfile) for full details of the contents of this image.
        """

    def get_container(self, base_url):
        return os.path.join(base_url, "tools", "proteomics-essentials_1.0.0.sif")

    def get_publication(self):
        return ""

    def get_workflow(self):
        return "https://github.com/YeoLab/containers/tree/main/images/proteomics-essentials/1.0.0"


class EphysEssentials(ExternalTool):
    def __init__(self, user):
        """
        All of the tool-specific metadata
        :param post_data:
        :param user:
        """
        super().__init__(user)
        self.modality = 'ephys'
        self.id = 'EphysEssentials'  # cannot have . or { in name
        self.name = 'EphysEssentials'

    def get_description(self):
        return """
        Contains a selection of essential software packages for analyzing electrophysiology-type data. Please see the 
        External link (Dockerfile) for full details of the contents of this image.
        """

    def get_container(self, base_url):
        return os.path.join(base_url, "tools", "ephys-essentials_1.0.0.sif")

    def get_publication(self):
        return ""

    def get_workflow(self):
        return "https://github.com/YeoLab/containers/tree/main/images/ephys-essentials/1.0.0"


class ImagingEssentials(ExternalTool):
    def __init__(self, user):
        """
        All of the tool-specific metadata
        :param post_data:
        :param user:
        """
        super().__init__(user)
        self.modality = 'imaging'
        self.id = 'ImagingEssentials'  # cannot have . or { in name
        self.name = 'ImagingEssentials'

    def get_description(self):
        return """
        Contains a selection of essential software packages for analyzing imaging-type data. Please see the 
        External link (Dockerfile) for full details of the contents of this image.
        """

    def get_container(self, base_url):
        return os.path.join(base_url, "tools", "imaging-essentials_1.0.0.sif")

    def get_publication(self):
        return ""

    def get_workflow(self):
        return "https://github.com/YeoLab/containers/tree/main/images/imaging-essentials/1.0.0"


class Patchseqtools(ExternalTool):
    def __init__(self, user):
        """
        All of the tool-specific metadata
        :param post_data:
        :param user:
        """
        super().__init__(user)
        self.modality = 'ephys'
        self.id = 'Patchseqtools'  # cannot have . or { in name
        self.name = 'Patchseqtools'

    def get_description(self):
        return """
        Contains a selection of essential software packages for analyzing patch-seq-type data. Please see the 
        External link (Dockerfile) for full details of the contents of this image.
        """

    def get_container(self, base_url):
        return os.path.join(base_url, "tools", "patchseqtools_be5018c.sif")

    def get_publication(self):
        return ""

    def get_workflow(self):
        return "https://github.com/YeoLab/containers/tree/main/images/patchseqtools/be5018c"


class StarJob(Job):
    def __init__(self, user):
        """
        All of the tool-specific metadata
        :param post_data:
        :param user:
        """
        super().__init__(user)
        self.module = 'star'
        self.module_version = '2.7.6a'
        self.module_script = 'star-2.7.6a-runner'
        self.modality = 'genomics'
        self.id = 'StarJob'  # cannot have . or { in name
        self.name = 'STAR'

    def get_container(self, base_url):
        return os.path.join(base_url, "tools", "star_2.7.6a.sif")

    def get_workflow(self):
        return ""

    def get_publication(self):
        return "https://www.ncbi.nlm.nih.gov/pubmed/23104886"

    def get_description(self):
        return """
        RNA-seq aligner
        """

    def get_workflow(self):
        return "https://github.com/alexdobin/STAR"

    def get_form_options(self, json_payload=None):
        """
        Returns the dictionary containing the inputs required for this tool.
        First, it needs to provide the default form options for an empty form.
        If json_payload is passed, this means that the form options must
        include data from a previous job (user is re-submitting a job from
        the job-status page). We will need to pre-pend this data as new
        defaults prior to populating the form.

        Keys MUST be one of the following (to match standard types):
            file_inputs,
            text_inputs,
            date_inputs,
            textarea_inputs,
            integer_inputs,
            dropdown_inputs


        :return final_form: json
            dictionary that populates default form options.
            @see forms.DynamicForm.__init__
        """
        default_options = self.get_default_options()  # options for every tool

        tool_options = OrderedDict({

            'dropdown_inputs': [

                ('outFilterType', 'outFilterType', [('Normal', 'BySJout'), ]),
                ('readFilesCommand', 'readFilesCommand', [
                    ('zcat', 'zcat'),
                    ('None', 'None'),
                    ('gunzip -c', 'gunzip -c'),
                    ('bunzip2 -c', 'bunzip2 -c'),
                ]),
            ],
            'text_inputs': [
                ('outFileNamePrefix', 'outFileNamePrefix', 'STAR')
            ],
            'file_inputs': [
                (
                    'readFilesIn (read1)',
                    'readFilesIn_r1',
                    ('.fastq.gz', '.fq.gz', '.fq', '.fastq')
                ),
                (
                    'readFilesIn (read2)',
                    'readFilesIn_r2',
                    ('.fastq.gz', '.fq.gz', '.fq', '.fastq'),
                    'None'
                ),
                (
                    'genomeDir',
                    'genomeDir',
                    '/',
                    [
                        'star_2_7_gencode29_sjdb',
                        'star_2_7_gencode19_sjdb',
                    ]
                ),
            ],
            'integer_inputs': [
                ('outFilterMultimapNmax', 'outFilterMultimapNmax', 20),
                ('alignSJoverhangMin', 'alignSJoverhangMin', 8),
                ('alignSJDBoverhangMin', 'alignSJDBoverhangMin', 1),
                ('outFilterMismatchNmax', 'outFilterMismatchNmax', 999),
                ('alignIntronMin', 'alignIntronMin', 20),
                ('alignIntronMax', 'alignIntronMax', 1000000),
                ('alignMatesGapMax', 'alignMatesGapMax', 1000000),
            ],
            'float_inputs': [
                ('outFilterMismatchNoverReadLmax', 'outFilterMismatchNoverReadLmax', 0.04),
            ],
        })
        return mergedict(default_options, tool_options)

    def generate_job_submission_document(self, post_data):
        """
        All of the job-specific metadata (params).
        First, we must populate the submission document (JSON file) with default fields. These fields
        @see generate_default_job_submission_document() are hidden fields that are important for the
        chosen pipeline to run, but do not require user input, hence they are not part of post_data.

        :param post_data: QueryDict
        :return:
        """
        default_expt_dict = self.generate_default_job_submission_document()

        job_expt_dict = {
            'project': post_data['project'],
            'experiment_nickname': post_data['experiment_nickname'],
            'aggr_nickname': post_data['experiment_nickname'] + '-' + default_expt_dict['processing_date'],
            'experiment_start_date': post_data['start_date'],
            'experiment_summary': post_data['experiment_summary'],
            'organism': post_data['organism'],
            'species': post_data['organism'],
        }
        for field in [
            'outFilterType', 'outFileNamePrefix'
        ]:
            job_expt_dict[field] = post_data[field]
        for field in [
            'outFilterMismatchNoverReadLmax'
        ]:
            job_expt_dict[field] = float(post_data[field])
        for field in [
            'outFilterMultimapNmax', 'alignSJoverhangMin', 'alignSJDBoverhangMin',
            'outFilterMismatchNmax', 'alignIntronMin', 'alignIntronMax', 'alignMatesGapMax'
        ]:
            job_expt_dict[field] = int(post_data[field])
        job_expt_dict['genomeDir'] = {'class': 'Directory', 'path': post_data['genomeDir']}
        job_expt_dict['readFilesIn'] = []
        job_expt_dict['readFilesIn'].append({'class': 'File', 'path': post_data['readFilesIn_r1']})
        if post_data['readFilesIn_r2'] != 'None':
            job_expt_dict['readFilesIn'].append({'class': 'File', 'path': post_data['readFilesIn_r2']})
        if post_data['readFilesCommand'] != 'None':
            job_expt_dict['readFilesCommand'] = post_data['readFilesCommand']
        return OrderedDict({**default_expt_dict, **job_expt_dict})


class Star252bJob(StarJob):
    def __init__(self, user):
        """
        All of the tool-specific metadata
        :param post_data:
        :param user:
        """
        super().__init__(user)
        self.module = 'star'
        self.module_version = '2.5.2b'
        self.module_script = 'star-2.5.2b-runner'
        self.modality = 'genomics'
        self.id = 'Star252bJob'  # cannot have . or { in name
        self.name = 'STAR 2.5.2b'

    def get_container(self, base_url):
        return os.path.join(base_url, "tools", "star_2.5.2b.sif")

    def get_form_options(self, json_payload=None):
        """
        Returns the dictionary containing the inputs required for this tool.
        First, it needs to provide the default form options for an empty form.
        If json_payload is passed, this means that the form options must
        include data from a previous job (user is re-submitting a job from
        the job-status page). We will need to pre-pend this data as new
        defaults prior to populating the form.

        Keys MUST be one of the following (to match standard types):
            file_inputs,
            text_inputs,
            date_inputs,
            textarea_inputs,
            integer_inputs,
            dropdown_inputs


        :return final_form: json
            dictionary that populates default form options.
            @see forms.DynamicForm.__init__
        """
        default_options = self.get_default_options()  # options for every tool

        tool_options = OrderedDict({

            'dropdown_inputs': [

                ('outFilterType', 'outFilterType', [('Normal', 'BySJout'), ]),
                ('readFilesCommand', 'readFilesCommand', [
                    ('zcat', 'zcat'),
                    ('None', 'None'),
                    ('gunzip -c', 'gunzip -c'),
                    ('bunzip2 -c', 'bunzip2 -c'),
                ]),
            ],
            'text_inputs': [
                ('outFileNamePrefix', 'outFileNamePrefix', 'STAR')
            ],
            'file_inputs': [
                (
                    'readFilesIn (read1)',
                    'readFilesIn_r1',
                    ('.fastq.gz', '.fq.gz', '.fq', '.fastq')
                ),
                (
                    'readFilesIn (read2)',
                    'readFilesIn_r2',
                    ('.fastq.gz', '.fq.gz', '.fq', '.fastq'),
                    'None'
                ),
                (
                    'genomeDir',
                    'genomeDir',
                    '/',
                    [
                        'refdata-cellranger-hg19-3.0.0/star/',
                        'refdata-cellranger-GRCh38-3.0.0/star/',
                    ]
                ),
            ],
            'integer_inputs': [
                ('outFilterMultimapNmax', 'outFilterMultimapNmax', 20),
                ('alignSJoverhangMin', 'alignSJoverhangMin', 8),
                ('alignSJDBoverhangMin', 'alignSJDBoverhangMin', 1),
                ('outFilterMismatchNmax', 'outFilterMismatchNmax', 999),
                ('alignIntronMin', 'alignIntronMin', 20),
                ('alignIntronMax', 'alignIntronMax', 1000000),
                ('alignMatesGapMax', 'alignMatesGapMax', 1000000),
            ],
            'float_inputs': [
                ('outFilterMismatchNoverReadLmax', 'outFilterMismatchNoverReadLmax', 0.04),
            ],
        })
        return mergedict(default_options, tool_options)


class Star274aJob(StarJob):
    def __init__(self, user):
        """
        All of the tool-specific metadata
        :param post_data:
        :param user:
        """
        super().__init__(user)
        self.module = 'star'
        self.module_version = '2.7.4a'
        self.module_script = 'star-2.7.4a-runner'
        self.modality = 'genomics'
        self.id = 'Star274aJob'  # cannot have . or { in name
        self.name = 'STAR 2.7.4a'

    def get_container(self, base_url):
        return os.path.join(base_url, "tools", "star_2.7.4a.sif")


class FragpipeJob(Job):
    def __init__(self, user):
        """
        All of the tool-specific metadata
        :param post_data:
        :param user:
        """
        super().__init__(user)
        self.module = 'fragpipe'
        self.module_version = '18.0'
        self.module_script = 'fragpipe-18.0-runner'
        self.modality = 'proteomics'
        self.id = 'FragpipeJob'  # cannot have . or { in name
        self.name = 'Fragpipe'

    def get_container(self, base_url):
        return base_url

    def get_workflow(self):
        return ""

    def get_publication(self):
        return ""

    def get_description(self):
        return """
        
        """

    def get_form_options(self, json_payload=None):
        """
        Returns the dictionary containing the inputs required for this tool.
        First, it needs to provide the default form options for an empty form.
        If json_payload is passed, this means that the form options must
        include data from a previous job (user is re-submitting a job from
        the job-status page). We will need to pre-pend this data as new
        defaults prior to populating the form.

        Keys MUST be one of the following (to match standard types):
            file_inputs,
            text_inputs,
            date_inputs,
            textarea_inputs,
            integer_inputs,
            dropdown_inputs


        :return final_form: json
            dictionary that populates default form options.
            @see forms.DynamicForm.__init__
        """
        default_options = self.get_default_options()  # options for every tool

        tool_options = OrderedDict({
            'multi_file_inputs': [
                ('Raw files directories', 'rawfiles', "/"),
            ],
            'file_inputs': [
                ('Workflow', 'workflow', ".workflow"),
                # ('Workflow', 'workflow', ".workflow", [
                #     'fragpipe_workflows/Default.workflow',
                #     'fragpipe_workflows/common-mass-offsets.workflow'
                # ]),
                ('Manifest', 'manifest', None),
                (
                    'Database',
                    'database',
                    ".fasta",
                    [
                        'uniprot-proteome_UP000005640.fasta',
                        '202011_uniprot_reviewed_mus_musculus.fasta',
                        'UP000005640_9606.fasta',
                    ]
                ),
            ],
        })
        return mergedict(default_options, tool_options)

    def generate_job_submission_document(self, post_data):
        """
        All of the job-specific metadata (params).
        First, we must populate the submission document (JSON file) with default fields. These fields
        @see generate_default_job_submission_document() are hidden fields that are important for the
        chosen pipeline to run, but do not require user input, hence they are not part of post_data.

        :param post_data: QueryDict
        :return:
        """
        default_expt_dict = self.generate_default_job_submission_document()
        post_data_raw_files = post_data.getlist('rawfiles')
        endpoint_id = settings.GLOBUS_USS_EP_ID
        https_server = get_globus_https_server(endpoint_id)
        # open file to stream out
        manifest_transfer_url = f'{https_server}/{self.user}/{post_data["manifest"]}'
        workflow_transfer_url = f'{https_server}/{self.user}/{post_data["workflow"]}'
        new_workflow_transfer_url = f'{https_server}/{self.user}/{post_data["workflow"]}_{post_data["experiment_nickname"]}'

        https_token = get_https_token(endpoint_id)
        header = {"Authorization": f"Bearer {https_token}"}
        manifest_response = requests.get(manifest_transfer_url, headers=header, allow_redirects=False)
        workflow_response = requests.get(workflow_transfer_url, headers=header, allow_redirects=False)

        manifest = manifest_response.content.decode("utf-8")
        workflow = workflow_response.content.decode("utf-8")

        manifest_files = []
        manifest_filetypes = []

        # modify workflow DB path based on form choice. Must hardcode this path, otherwise Fragpipe can't find it!
        root_dir = post_data['database'].split('/')[0]
        if root_dir == 'results' or root_dir == 'raw_files':
            base_dir = self.user
        else:
            base_dir = 'refs'
        database_file = os.path.join(f"/projects/ps-yeolab5/cred/{base_dir}/", post_data['database'])  # TODO: refactor refdata
        amended_workflow = []
        for line in workflow.split('\n'):
            if not line.startswith('database.db-path'):
                amended_workflow.append(line.rstrip())
        amended_workflow.append("database.db-path={}".format(database_file))
        # write new data to file
        bvalue = base64.b64encode(bytes('\n'.join(amended_workflow), 'utf-8'))
        decoded = base64.b64decode(bvalue)
        response = requests.put(new_workflow_transfer_url, data=decoded, headers=header, allow_redirects=False)

        for line in manifest.split('\n'):
            file_name, _, _, file_type = line.rstrip().split('\t')  # TODO: validate? manifest must have 4 fields
            for post_data_raw_file in post_data_raw_files:
                if os.path.basename(file_name.rstrip('/')) == os.path.basename(post_data_raw_file.rstrip('/')):  # only use files that are included in manifest
                    manifest_files.append({'class': 'Directory', 'path': post_data_raw_file})
                    manifest_filetypes.append(file_type)

        job_expt_dict = {
            'project': post_data['project'],
            'experiment_nickname': post_data['experiment_nickname'],
            'aggr_nickname': post_data['experiment_nickname'] + '-' + default_expt_dict['processing_date'],
            'experiment_start_date': post_data['start_date'],
            'experiment_summary': post_data['experiment_summary'],
            'organism': post_data['organism'],
            'rawfiles_type': manifest_filetypes,
            'rawfiles': manifest_files,
            'workflow': {'class': 'File', 'path': f'{post_data["workflow"]}_{post_data["experiment_nickname"]}'}
        }
        return OrderedDict({**default_expt_dict, **job_expt_dict})


class Fragpipe180Job(FragpipeJob):
    def __init__(self, user):
        """
        All of the tool-specific metadata
        :param post_data:
        :param user:
        """
        super().__init__(user)
        self.module = 'fragpipe'
        self.module_version = '18.0'
        self.module_script = 'fragpipe-18.0-runner'
        self.modality = 'proteomics'
        self.id = 'Fragpipe180Job'  # cannot have . or { in name
        self.name = 'Fragpipe 18.0'
