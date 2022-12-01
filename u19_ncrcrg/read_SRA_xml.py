#!/usr/bin/env python

import argparse
import xml.etree.ElementTree as et 
import os
import glob
from xml.dom import minidom
from collections import defaultdict
import yaml

from yaml.representer import Representer
yaml.add_representer(defaultdict, Representer.represent_dict)


import json
def get_metadata_from_xml_file(input_file, transcriptome, chemistry, cr11, read1_length, read2_length, module, module_version, module_script):
    return 0  # TODO: process from file instead of string


def get_10x_metadata_from_xml(input_string, transcriptome, chemistry, cr11, read1_length, read2_length, expect_cells):
    """
    Transforms the metadata XML file into a dictionary that can be dumped into 1 or more properly 
    formatted JSON files.
    
    input_file: string
    transcriptome: string
    chemistry: string
    cr11: string
    module: string
    module_version: string
    module_script: string
    """
    my_expt_set_metadata = []

    xmldoc = minidom.parseString(input_string)
    expt_packages = xmldoc.getElementsByTagName('EXPERIMENT_PACKAGE')
    for expt_package in expt_packages:
        my_expt_metadata = defaultdict(list)
        
        organization_metadata = expt_package.getElementsByTagName('Organization')
        for metadata in organization_metadata:
            try:
                my_expt_metadata['organization'].append(metadata.getElementsByTagName('Name')[0].firstChild.data)
            except KeyError:
                pass
            try:
                my_expt_metadata['email'].append(metadata.getElementsByTagName('Contact')[0].attributes['email'].value)
            except KeyError:
                pass
        my_expt_metadata['organization'] = ','.join(my_expt_metadata['organization'])
        my_expt_metadata['email'] = ','.join(my_expt_metadata['email'])

        expt_metadata = expt_package.getElementsByTagName('EXPERIMENT')
        for metadata in expt_metadata:
            title = metadata.getElementsByTagName('TITLE')[0].firstChild.data
            my_expt_metadata['experiment_nickname'].append(metadata.attributes['accession'].value)
            my_expt_metadata['experiment_summary'].append(title)
        my_expt_metadata['experiment_nickname'] = ','.join(my_expt_metadata['experiment_nickname'])
        my_expt_metadata['experiment_summary'] = ','.join(my_expt_metadata['experiment_summary'])

        design_metadata = expt_package.getElementsByTagName('DESIGN')
        for metadata in design_metadata:
            try:
                design = metadata.getElementsByTagName('DESIGN_DESCRIPTION')[0].firstChild.data
            except AttributeError:
                design = ''
            my_expt_metadata['experiment_design'].append(design)
        my_expt_metadata['experiment_design'] = ','.join(my_expt_metadata['experiment_design'])
        
        study_metadata = expt_package.getElementsByTagName('STUDY')[0]
        my_expt_metadata['study_title'] = study_metadata.getElementsByTagName('STUDY_TITLE')[0].firstChild.nodeValue
        my_expt_metadata['study_abstract'] = study_metadata.getElementsByTagName('STUDY_ABSTRACT')[0].firstChild.nodeValue
        my_expt_metadata['experiment_summary'] = my_expt_metadata['experiment_summary'] + "\n[ABSTRACT]: " + my_expt_metadata['study_abstract']
        external_ids = study_metadata.getElementsByTagName('EXTERNAL_ID')
        for external_id in external_ids:
            for attr in external_id.attributes.keys():
                ddb = external_id.attributes[attr].value
                did = external_id.firstChild.data
                my_expt_metadata['database'].append({ddb:did})
        study_links = study_metadata.getElementsByTagName('STUDY_LINKS')
        
        for link in study_links:
            sdb = link.getElementsByTagName('XREF_LINK')[0].childNodes[0].firstChild.data
            sid = link.getElementsByTagName('XREF_LINK')[0].childNodes[1].firstChild.data
            my_expt_metadata['reference'].append({sdb:sid})
            
        run_set = expt_package.getElementsByTagName('RUN_SET')

        run_accession_list = []
        for run in run_set:

            run_metadata = run.getElementsByTagName('RUN')
            for metadata in run_metadata:
                my_run_metadata = defaultdict(dict)
                accession = metadata.attributes['accession'].value
                run_accession_list.append(accession)
                try:
                    print('processing run {}'.format(accession))
                    my_run_metadata['library_nickname'] = metadata.attributes['accession'].value
                except KeyError:
                    my_run_metadata['library_nickname'] = ''
                try:
                    my_run_metadata['library_prep'] = ""
                except KeyError:
                    my_run_metadata['library_prep'] = ""
                try:
                    my_run_metadata['sample_id'] = metadata.attributes['accession'].value
                except KeyError:
                    my_run_metadata['sample_id'] = ""
                try:
                    my_run_metadata['original_assembly'] = metadata.attributes['assembly'].value
                except KeyError:
                    my_run_metadata['original_assembly'] = ""

                file_metadata = metadata.getElementsByTagName('SRAFile')
                for fmetadata in file_metadata:
                    # print("FILE METADATA: {}".format(metadata))
                    try:
                        filename = fmetadata.attributes['filename'].value
                        url = fmetadata.attributes['url'].value
                        if filename.endswith('.bam') or filename.endswith('.bam.1'):
                            my_run_metadata['bam_file_url'] = fmetadata.attributes['url'].value
                            print(my_run_metadata['library_nickname'], my_run_metadata['bam_file_url'])
                    except KeyError:
                        print("{} does not have a file associated with it.".format(fmetadata))
                instrument_metadata = expt_package.getElementsByTagName('PLATFORM')
                for imetadata in instrument_metadata:
                    try:
                        instrument = imetadata.getElementsByTagName('INSTRUMENT_MODEL')[0].firstChild.data
                    except AttributeError:
                        instrument = ''
                    my_run_metadata['instrument_model'] = instrument
                    my_run_metadata['read1_length'] = int(read1_length)
                    my_run_metadata['read2_length'] = int(read2_length)
                    my_run_metadata['expect_cells'] = int(expect_cells)
                    my_run_metadata['chemistry'] = chemistry
                    my_run_metadata['transcriptome'] = {
                        'class': 'Directory',
                        'path': transcriptome
                    }

                    # cr11_as_yaml_bool = 'false' if cr11 is False else 'true'

                    my_run_metadata['cr11'] = cr11

                # This actually belong on the top level per-expt, but we apply characteristics to each file.
                taxonomy_metadata = expt_package.getElementsByTagName('SAMPLE_NAME')
                for tmetadata in taxonomy_metadata:
                    scientific_name = tmetadata.getElementsByTagName('SCIENTIFIC_NAME')[0].firstChild.data
                    my_expt_metadata['organism'] = scientific_name

                sample_set = expt_package.getElementsByTagName('SAMPLE')
                for sample in sample_set:
                    sample_metadata = sample.getElementsByTagName('SAMPLE_ATTRIBUTES')
                    characteristics_list = []
                    for smetadata in sample_metadata:
                        attributes = smetadata.getElementsByTagName('SAMPLE_ATTRIBUTE')
                        my_sample_metadata = defaultdict()
                        for attribute in attributes:
                            characteristics_tag = {
                                'name': attribute.getElementsByTagName('TAG')[0].firstChild.data,
                                'value': attribute.getElementsByTagName('VALUE')[0].firstChild.data
                            }
                            characteristics_list.append(characteristics_tag)
                    my_run_metadata['characteristics'] = characteristics_list
                if 'bam_file_url' not in my_run_metadata.keys():
                    print('missing key', my_run_metadata.keys())
                    # WE NEED THIS URL TO DOWNLOAD AND PROCESS
                    print("{} is missing 10X bam file url.".format(my_expt_metadata['experiment_nickname']))
                else:
                    my_expt_metadata['samples'].append(my_run_metadata)

        my_expt_set_metadata.append(my_expt_metadata)
    return my_expt_set_metadata


def get_rnaseq_metadata_from_xml(input_string, genome_index, start0base, end, b_adapters, chrom_sizes):
    """
    Transforms the metadata XML file into a dictionary that can be dumped into 1 or more properly
    formatted JSON files.

    input_string: string
        XML of metadata in string format
    genome_index: string
        relative path to genome index
    start0base: string
        Assuming the UMIs are embedded in the read header, where does the UMI start (0-based half-open)?
    end: string
        Assuming the UMIs are embedded in the read header, where does the UMI end (0-based half-open)?
    b_adapters: string
        relative path to the adapter fasta file.
    chrom_sizes: string
        relative path to the chrom_sizes file (tabbed file containing chrom\tlength)
    """
    my_expt_set_metadata = []

    xmldoc = minidom.parseString(input_string)
    expt_packages = xmldoc.getElementsByTagName('EXPERIMENT_PACKAGE')
    for expt_package in expt_packages:
        my_expt_metadata = defaultdict(list)

        ### USER INPUT ###
        my_expt_metadata['speciesGenomeDir'] = {
            'class': 'Directory',
            'path': genome_index
        }
        if start0base is not None:
            my_expt_metadata['start0base'] = int(start0base)
        if end is not None:
            my_expt_metadata['end'] = int(end)
        my_expt_metadata['b_adapters'] = {
            'class': 'File',
            'path': b_adapters
        }
        my_expt_metadata['speciesChromSizes'] = {
            'class': 'File',
            'path': chrom_sizes
        }

        ### EXPERIMENTAL METADATA. Describe experiment-level details. Broken up into 1) organization, 2) experiment 3) design 4) study ###
        organization_metadata = expt_package.getElementsByTagName('Organization')
        for metadata in organization_metadata:
            try:
                my_expt_metadata['organization'].append(metadata.getElementsByTagName('Name')[0].firstChild.data)
            except IndexError:
                pass
            try:
                print(metadata.getElementsByTagName('Contact'))
                my_expt_metadata['email'].append(metadata.getElementsByTagName('Contact')[0].attributes['email'].value)
            except IndexError:
                pass
        try:
            my_expt_metadata['organization'] = ','.join(my_expt_metadata['organization'])
        except KeyError:
            pass
        try:
            my_expt_metadata['email'] = ','.join(my_expt_metadata['email'])
        except KeyError:
            pass
        expt_metadata = expt_package.getElementsByTagName('EXPERIMENT')
        for metadata in expt_metadata:
            title = metadata.getElementsByTagName('TITLE')[0].firstChild.data
            my_expt_metadata['experiment_nickname'].append(metadata.attributes['accession'].value)
            my_expt_metadata['experiment_summary'].append(title)
        my_expt_metadata['experiment_nickname'] = ','.join(my_expt_metadata['experiment_nickname'])
        my_expt_metadata['experiment_summary'] = ','.join(my_expt_metadata['experiment_summary'])

        design_metadata = expt_package.getElementsByTagName('DESIGN')[0]
        my_expt_metadata['library_layout'] = \
        design_metadata.getElementsByTagName('LIBRARY_DESCRIPTOR')[0].getElementsByTagName('LIBRARY_LAYOUT')[
            0].firstChild.tagName
        my_expt_metadata['library_source'] = \
        design_metadata.getElementsByTagName('LIBRARY_DESCRIPTOR')[0].getElementsByTagName('LIBRARY_SOURCE')[
            0].firstChild.nodeValue
        my_expt_metadata['library_description'] = \
        design_metadata.getElementsByTagName('LIBRARY_DESCRIPTOR')[0].getElementsByTagName('LIBRARY_SELECTION')[
            0].firstChild.nodeValue

        study_metadata = expt_package.getElementsByTagName('STUDY')[0]
        my_expt_metadata['study_title'] = study_metadata.getElementsByTagName('STUDY_TITLE')[0].firstChild.nodeValue
        my_expt_metadata['study_abstract'] = study_metadata.getElementsByTagName('STUDY_ABSTRACT')[
            0].firstChild.nodeValue
        my_expt_metadata['experiment_summary'] = my_expt_metadata['experiment_summary'] + "\n[ABSTRACT]: " + \
                                                 my_expt_metadata['study_abstract']
        external_ids = study_metadata.getElementsByTagName('EXTERNAL_ID')
        for external_id in external_ids:
            for attr in external_id.attributes.keys():
                ddb = external_id.attributes[attr].value
                did = external_id.firstChild.data
                my_expt_metadata['database'].append({ddb: did})
        study_links = study_metadata.getElementsByTagName('STUDY_LINKS')

        for link in study_links:
            sdb = link.getElementsByTagName('XREF_LINK')[0].childNodes[0].firstChild.data
            sid = link.getElementsByTagName('XREF_LINK')[0].childNodes[1].firstChild.data
            my_expt_metadata['reference'].append({sdb: sid})

        ### RUN METADATA. Describe each individual sequencing run. ###
        run_set = expt_package.getElementsByTagName('RUN_SET')
        for run in run_set:
            my_run_metadata = defaultdict(dict)

            run_metadata = run.getElementsByTagName('RUN')
            for metadata in run_metadata:
                try:
                    my_run_metadata['library_nickname'] = metadata.attributes['accession'].value
                except KeyError:
                    my_run_metadata['library_nickname'] = ''
                try:
                    my_run_metadata['library_prep'] = ""
                except KeyError:
                    my_run_metadata['library_prep'] = ""
                try:
                    my_run_metadata['sample_id'] = metadata.attributes['accession'].value
                except KeyError:
                    my_run_metadata['sample_id'] = ""
                try:
                    my_run_metadata['original_assembly'] = metadata.attributes['assembly'].value
                except KeyError:
                    my_run_metadata['original_assembly'] = ""

            ### Comment out for now. Supposedly NCBI will move to AWS and will eventually have s3 links available. ###
            # file_metadata = run.getElementsByTagName('SRAFile')
            # for metadata in file_metadata:
            #     if 'url' in metadata.attributes:
            #         print(metadata.attributes['url'].value)
            # filename = metadata.attributes['filename'].value
            # url = metadata.attributes['url'].value
            # print(url)

            instrument_metadata = expt_package.getElementsByTagName('PLATFORM')
            for metadata in instrument_metadata:
                try:
                    instrument = metadata.getElementsByTagName('INSTRUMENT_MODEL')[0].firstChild.nodeValue
                except AttributeError:
                    instrument = ''
                my_run_metadata['instrument_model'] = instrument

            # This actually belong on the top level per-expt, but we apply characteristics to each file.
            taxonomy_metadata = expt_package.getElementsByTagName('SAMPLE_NAME')
            for metadata in taxonomy_metadata:
                scientific_name = metadata.getElementsByTagName('SCIENTIFIC_NAME')[0].firstChild.data
                my_expt_metadata['organism'] = scientific_name

            sample_set = expt_package.getElementsByTagName('SAMPLE')
            for sample in sample_set:
                sample_metadata = sample.getElementsByTagName('SAMPLE_ATTRIBUTES')
                characteristics_list = []
                for metadata in sample_metadata:
                    attributes = metadata.getElementsByTagName('SAMPLE_ATTRIBUTE')
                    my_sample_metadata = defaultdict()
                    for attribute in attributes:
                        characteristics_tag = {
                            'name': attribute.getElementsByTagName('TAG')[0].firstChild.data,
                            'value': attribute.getElementsByTagName('VALUE')[0].firstChild.data
                        }
                        characteristics_list.append(characteristics_tag)
            my_run_metadata['characteristics'] = characteristics_list
            my_expt_metadata['samples'].append(my_run_metadata)

        my_expt_set_metadata.append(my_expt_metadata)
    return my_expt_set_metadata


def main():
    """
    This script contains a set of functions that parse XML files downloaded from the sequence read archive (SRA).
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input_file",
        required=True,
        type=str
    )
    parser.add_argument(
        "--output_dir",
        required=True,
        type=str,
    )
    parser.add_argument(
        "--transcriptome",
        required=True,
        type=str,
    )
    parser.add_argument(
        "--module",
        required=True,
        type=str
    )
    parser.add_argument(
        "--module_version",
        required=True,
        type=str,
    )
    parser.add_argument(
        "--module_script",
        required=True,
        type=str,
    )
    parser.add_argument(
        "--chemistry",
        required=False,
        type=str,
        default='auto'
    )
    parser.add_argument(
        "--cr11",
        required=False,
        action='store_true',
        default=False
    )


    # Process args
    args = parser.parse_args()

    input_file = args.input_file
    output_dir = args.output_dir
    transcriptome = args.transcriptome
    cr11 = args.cr11
    chemistry = args.chemistry
    module = args.module
    module_version = args.module_version
    module_script = args.module_script
    # TODO: update cmdline main func, but unused for now.
    metadata = get_metadata_from_xml_file(
        input_string=input_file,
        transcriptome=transcriptome,
        chemistry=chemistry,
        cr11=cr11,
        module=module,
        module_version=module_version,
        module_script=module_script
    )
    
    for expt in metadata:
        with open(os.path.join(output_dir, '{}.json'.format(expt['experiment_nickname'])), 'w') as o:
            json.dump(dict(expt), o, indent=2)
            
if __name__ == "__main__":
    main()
