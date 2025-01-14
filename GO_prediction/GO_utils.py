
import numpy as np
import random
from sklearn import linear_model
from goatools.associations import read_ncbi_gene2go
from goatools.base import download_ncbi_associations
import math
from sklearn.metrics import roc_auc_score
from sklearn.metrics import mean_squared_error
from sklearn.svm import SVC
from goatools.go_search import GoSearch

#from goatools.base import download
#obo_fname = download_go_basic_obo()


class GOterm:
    def __init__(self, id):
        self.id = id
        self.descendants_ids = []
        self.genes = set()

    def add_descendants(self, srchhelp):
        self.descendants_ids = list(srchhelp.add_children_gos(gos=[self.id]))


def sort_go_terms(terms):
    """
    Sort a list of GOterm objects in decreasing order of #
    of genes
    :param terms: The list GOterm objects
    :return: The sorted list
    """
    return sorted(terms, key=lambda term: len(term.genes), reverse=True)


def map_entrez_to_ensembl(path):
    ent_to_ens = {}
    f = open(path)
    for line in f:
        vals = line.split('\t')
        ens_gene_id = vals[0]
        entrez_id = vals[2]
        ent_to_ens[entrez_id] = ens_gene_id

    f.close()
    return ent_to_ens


def get_go_terms_descendants(biomart_fpath, gene2go_fpath, gene_count_fpath, obo_fpath, ev_codes=None):

    entrez_to_ensembl = map_entrez_to_ensembl(biomart_fpath)

    # taxids=[9606] means select only human.
    if ev_codes:
        go_to_entrez_ids_human = read_ncbi_gene2go(gene2go_fpath, taxids=[9606], go2geneids=True, evidence_set=ev_codes)
    else:
        go_to_entrez_ids_human = read_ncbi_gene2go(gene2go_fpath, taxids=[9606], go2geneids=True)
    print("{N} GO terms associated with human NCBI Entrez GeneIDs".format(N=len(go_to_entrez_ids_human)))
    srchhelp = GoSearch(obo_fpath, go2items=go_to_entrez_ids_human)

    # Get the GO terms
    gene_cnt_file = open(gene_count_fpath)
    GO_terms = []
    atLine = 0
    skipLines = 2
    for line in gene_cnt_file:
        if atLine < skipLines:
            atLine += 1
            continue
        GO_id = line.split('\t')[0]
        term = GOterm(GO_id)
        term.add_descendants(srchhelp)

        for id in [GO_id] + term.descendants_ids:
            entrez_ids = go_to_entrez_ids_human[id]
            for ent_id in entrez_ids:
                if str(ent_id) in entrez_to_ensembl:
                    ens_id = entrez_to_ensembl[str(ent_id)]
                    term.genes.add(ens_id)
        GO_terms.append(term)

    return GO_terms


def get_go_terms(biomart_fpath, gene2go_fpath, gene_count_fpath, top=1):
    """

    :param biomart_fpath:
    :param gene2go_fpath:
    :param gene_count_fpath: Path to file containing number of genes for each
    GO term contained in the supplementary file
    :param top:
    :return:
    """

    entrez_to_ensembl = map_entrez_to_ensembl(biomart_fpath)

    # taxids=[9606] means select only human.
    go_to_entrez_ids_human = read_ncbi_gene2go(gene2go_fpath, taxids=[9606], go2geneids=True)
    print("{N} GO terms associated with human NCBI Entrez GeneIDs".format(N=len(go_to_entrez_ids_human)))

    # Get the |top| GO terms with the most gene annotations
    gene_cnt_file = open(gene_count_fpath)
    top_GO_ids = []
    atLine = 0
    skipLines = 1
    for line in gene_cnt_file:
        if atLine < skipLines:
            atLine += 1
            continue
        elif atLine > top:
            break
        atLine += 1
        GO_id = line.split('\t')[0]
        entrez_ids = go_to_entrez_ids_human[GO_id]
        #print '# of Entrez IDs associated with ', GO_id, ' = ', len(entrez_ids)
        ensembl_ids = []
        for ent_id in entrez_ids:
            if str(ent_id) in entrez_to_ensembl:
                ensembl_ids.append(entrez_to_ensembl[str(ent_id)])
        top_GO_ids.append((GO_id, ensembl_ids))
        #print '# of Ensembl IDs associated with ', GO_id, ' = ', len(ensembl_ids)

    return top_GO_ids



def get_ensembl_ids(go_process_id, biomart_fpath, ev_codes=None):

    entrez_to_ensembl = map_entrez_to_ensembl(biomart_fpath)

    gene2go = 'data/gene2go.txt' # If file doesn't exist, then replace this line with gene2go = download_ncbi_associations()

    # taxids=[9606] means select only human.
    go_to_entrez_ids_human = read_ncbi_gene2go(gene2go, taxids=[9606], go2geneids=True)
    print("{N} GO terms associated with human NCBI Entrez GeneIDs".format(N=len(go_to_entrez_ids_human)))

    entrez_ids = go_to_entrez_ids_human[go_process_id]
    print '# of Entrez IDs associated with ', go_process_id, ' = ', len(entrez_ids)
    ensembl_ids = []
    for ent_id in entrez_ids:
        if str(ent_id) in entrez_to_ensembl:
            ensembl_ids.append(entrez_to_ensembl[str(ent_id)])

    print '# of Ensembl IDs associated with ', go_process_id, ' = ', len(ensembl_ids)
    return ensembl_ids


def get_positive_examples(rpkm_path, ens_ids_dict, num_features):

    gene_features = np.empty((0, num_features))
    positive_example_rows = []
    gene_ids_ordered = []
    i = 0
    rpkm_file = open(rpkm_path)
    firstLine = True
    for line in rpkm_file:
        if firstLine:
            firstLine = False
            continue

        tab1_index = line.find('\t')
        tab2_index = line.find('\t', tab1_index+1)
        cur_ens_id = line[tab1_index+1:tab2_index]
        # Remove decimal from the ensembl ID
        if '.' in cur_ens_id:
            cur_ens_id = cur_ens_id[0:cur_ens_id.index('.')]

        if cur_ens_id in ens_ids_dict:
            # This is IF condition prevents using the same gene for multiple
            # features. TODO: better method for accounting for multiple transcripts
            # mapping to same gene.
            if cur_ens_id not in gene_ids_ordered:
                positive_example_rows.append(i)
                gene_ids_ordered.append(cur_ens_id)
                exp_levels_str = line.rstrip().split('\t')[4:]
                # TODO: function that takes map from columns to tissues or whatever and return vector of averages for each tissue
                exp_levels = [float(exp_level) for exp_level in exp_levels_str]
                gene_features = np.append(gene_features, [exp_levels], axis=0)
        i += 1
    rpkm_file.close()

    return gene_features, positive_example_rows, gene_ids_ordered, i


def get_negative_examples(rpkm_path, neg_ex_rows, num_features):

    gene_features_neg = np.empty((0, num_features))
    gene_ids_ordered_neg = []
    rpkm_file = open(rpkm_path)
    i = 0
    firstLine = True
    for line in rpkm_file:
        if firstLine:
            firstLine = False
            continue

        if i in neg_ex_rows:
            vals = line.rstrip().split('\t')
            cur_ens_id = vals[1]

            # Remove decimal from the ensembl ID
            if '.' in cur_ens_id:
                cur_ens_id = cur_ens_id[0:cur_ens_id.index('.')]
            gene_ids_ordered_neg.append(cur_ens_id)
            exp_levels_str = vals[4:]
            exp_levels = [float(exp_level) for exp_level in exp_levels_str]
            gene_features_neg = np.append(gene_features_neg, [exp_levels], axis=0)
        i += 1

    rpkm_file.close()
    return gene_features_neg, gene_ids_ordered_neg
