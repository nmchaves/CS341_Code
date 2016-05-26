
"""
    This file goes through all GO terms of interest and creates the positive and negative
    examples for running a prediction problem. A positive example is a gene that is known
    to be associated with the GO term, while a negative example is a randomly sampled gene
    from the set of genes that are not known to be associated with the GO term.

"""

from GO_Evidence_Codes import EvidenceCodes
from os import remove
import numpy as np
import pandas as pd
from sklearn.decomposition import PCA

import sys
# sys.path.insert(0, '../GO_prediction')
# import GO_utils
# import utils
# from utils import get_tissue_list

def get_tissue_list(tissue_fpath):
    tissue_file = open(tissue_fpath)
    for line in tissue_file:
        tissues = line.rstrip().split('\t')
        break
    return tissues

def get_tissues_to_cols(tissue_list):
    tissues_to_cols = {}
    for tissue in tissue_list:
        cols = []
        meta_fname = '../data/tissue_metadata/tissue_meta_' + tissue + '.txt'
        meta_file = open(meta_fname)
        for (i, line) in enumerate(meta_file):
            if i < 1:
                continue
            col = int(line.split('\t')[0])
            cols.append(col)
        tissues_to_cols[tissue] = cols
    return tissues_to_cols

def normalize_column(mtx_in):
    num_features = mtx_in.shape[1]
    for i in range(0, num_features):
        col = mtx_in[:, i]
        col = col - np.mean(col)
        std_dev = np.std(col)
        if std_dev > 0:
            col = col / std_dev
        gene_features[:, i] = col
    col = col_in - np.mean(col_in)
    std_dev = np.std(col)
    if std_dev > 0:
        col = col / std_dev
    return col

'''

*********************
        Main
*********************
'''
if __name__ == "__main__":

    gene2go_file_path = '../data/gene2go.txt' # If file doesn't exist, then run gene2go = download_ncbi_associations()
    # rpkm_file_path = '../../CS341_Data/transcript_rpkm_in_go_nonzero_exp.txt'
    # rpkm_file_path = '../data/small_example_data/GO-0000578_pos.txt'
    gene_count_file_path = '../data/supp_GO_term_gene_counts.txt'
    biomart_file_path = '../data/biomart_ensembl_to_entrez.txt'
    obo_file_path = '../data/go-basic.obo'

    # load tissue information
    tissues = get_tissue_list('../data/tissues.txt');
    tissues_to_cols = get_tissues_to_cols(tissues)

   
    num_features = 0
    for tissue in tissues_to_cols:
        num_features += len(tissues_to_cols[tissue])
    print 'Loaded '+str(num_features)+' features. Number of tissues:' + str(len(tissues))

    
    rpkm_file_path = '../data/small_example_data/small_transcript_rpkm_in_go_nonzero_exp.txt'
    n_header_lines = 1
    # count number of genes
    rpkm_file = open(rpkm_file_path)
    num_genes = 0
    for (i, line) in enumerate(rpkm_file):
        if i >= n_header_lines:
            num_genes += 1
    rpkm_file.close()
    print 'Reading:' + rpkm_file_path
    print 'Number of Genes: ' + str(num_genes)

    # read the full rpkm matrix
    full_mtx = np.empty((num_genes, num_features))  # each row will be the feature profile for a given gene
    gene_ids = ["ID"]*num_genes
    # file_name = '../../CS341_Data/experiment_inputs/' + term + '_neg_0.txt'
    print 'Reading:' + rpkm_file_path
    n_pcomp = 5
    rpkm_file = open(rpkm_file_path)
    for (i, line) in enumerate(rpkm_file):
        vals = line.rstrip().split('\t')
        if i < n_header_lines: # TODO: double-check the number of headers to ignore 
            first_fields =vals[0:3]
            continue
        idx = i - n_header_lines
        if (idx % 100 == 0):
            print '    ' + str(idx) + ' genes read'
        gene_ids[idx] = vals[0]
        exp_levels = vals[4:]
        # Convert expression levels to log(level+1)
        exp_levels = [np.log10(float(exp_level)+1.0) for exp_level in exp_levels]
        # full_mtx = np.append(full_mtx, [exp_levels], axis=0)
        full_mtx[idx,:] = exp_levels 
    rpkm_file.close()
    print 'Complete!'
    print 'Dimension of full input matrix: ' + str(full_mtx.shape)

    # perform pca for each tissue
    pca_tissues_to_cols = {}
    reduced_mtx = np.zeros([full_mtx.shape[0],n_pcomp*len(tissues)]);
    # reduced_cols= np.chararray(n_pcomp*len(tissues));
    reduced_cols= ["NULL"]*(n_pcomp*len(tissues));

    for idx, tissue in enumerate(tissues):
        print 'Reducing features for ' + tissue 
        pca_tissues_to_cols[tissue] = range(n_pcomp*idx, n_pcomp*(idx+1))
        tissue_mtx = full_mtx[:,tissues_to_cols[tissue]]
        assert(tissue_mtx.shape[1] >= n_pcomp)
        # NORMALIZATION
        tissue_mtx = normalize_columns(tissue_mtx)  


        pca = PCA(n_components=n_pcomp)
        reduced_tissue_mtx = pca.fit_transform(tissue_mtx)
        reduced_mtx[:,pca_tissues_to_cols[tissue]] = reduced_tissue_mtx
        for t_idx in pca_tissues_to_cols[tissue]:
            reduced_cols[t_idx] = tissue
    print '*Data matrix size: ', str(reduced_mtx.shape)
    # PANDA data frame
    # reduced_data = pd.DataFrame(data=reduced_mtx,index=gene_ids,columns=reduced_cols)
    first_row = first_fields + reduced_cols
    print first_row
    # print reduced_mtx
    # print reduced_cols

    # TODO: save reduced matrix to file as a dataframe to file
