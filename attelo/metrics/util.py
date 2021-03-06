"""
Temporary place for utilities related to classification metrics.

This currently contains code to rebuild constituency trees from
dependency trees in attelo parlance and enumerate constituency tree
spans for evaluation.

Another motivation of this module is to contain and confine educe
imports.
"""

from __future__ import print_function

from collections import defaultdict
import itertools

from educe.annotation import Span as EduceSpan
from educe.rst_dt.annotation import (EDU as EduceEDU,
                                     RSTTree,
                                     SimpleRSTTree)
from educe.rst_dt.dep2con import (deptree_to_simple_rst_tree,
                                  DummyNuclearityClassifier,
                                  InsideOutAttachmentRanker)
from educe.rst_dt.deptree import (RstDepTree,
                                  RstDtException)

from attelo.table import UNKNOWN


def get_oracle_ctrees(dep_edges, att_edus,
                      nuc_strategy="unamb_else_most_frequent",
                      rank_strategy="closest-intra-rl-inter-rl",
                      prioritize_same_unit=True,
                      strict=False):
    """Build the oracle constituency tree(s) for a dependency tree.

    Parameters
    ----------
    dep_edges: dict(string, [(string, string, string)])
        Edges for each document, indexed by doc name
        Cf. type of return value from
        irit-rst-dt/ctree.py:load_attelo_output_file()
    att_edus: cf return type of attelo.io.load_edus
        EDUs as they are known to attelo
    strict: boolean, True by default
        If True, any link from ROOT to an EDU that is neither 'ROOT' nor
        UNRELATED raises an exception, otherwise a warning is issued.

    Returns
    -------
    ctrees: list of RstTree
        There can be several e.g. for leaky sentences.
    """
    # rebuild educe EDUs from their attelo description
    # and group them by doc_name
    educe_edus = defaultdict(list)
    edu2sent_idx = defaultdict(dict)
    gid2num = dict()
    for att_edu in att_edus:
        # doc name
        doc_name = att_edu.grouping
        # EDU info
        # skip ROOT (automatically added by RstDepTree.__init__)
        if att_edu.id == 'ROOT':
            continue
        edu_num = int(att_edu.id.rsplit('_', 1)[1])
        edu_span = EduceSpan(att_edu.start, att_edu.end)
        edu_text = att_edu.text
        educe_edus[doc_name].append(EduceEDU(edu_num, edu_span, edu_text))
        # map global id of EDU to num of EDU inside doc
        gid2num[att_edu.id] = edu_num
        # map EDU to sentence
        try:
            sent_idx = int(att_edu.subgrouping.split('_sent')[1])
        except IndexError:
            # this EDU could not be attached to any sentence (ex: missing
            # text in the PTB), so a default subgrouping identifier was used ;
            # we aim for consistency with educe and map these to "None"
            sent_idx = None
        edu2sent_idx[doc_name][edu_num] = sent_idx
    # check that our info covers only one document
    assert len(educe_edus) == 1
    # then restrict to this document
    doc_name = educe_edus.keys()[0]
    educe_edus = educe_edus[doc_name]
    edu2sent_idx = edu2sent_idx[doc_name]
    # sort EDUs by num
    educe_edus = list(sorted(educe_edus, key=lambda e: e.num))
    # rebuild educe-style edu2sent ; prepend 0 for the fake root
    edu2sent = [0] + [edu2sent_idx[e.num] for e in educe_edus]
    # classifiers for nuclearity and ranking
    # FIXME declare, fit and predict upstream...
    # nuclearity
    nuc_classifier = DummyNuclearityClassifier(strategy=nuc_strategy)
    nuc_classifier.fit([], [])  # empty X and y for dummy fit
    # ranking classifier
    rank_classifier = InsideOutAttachmentRanker(
        strategy=rank_strategy,
        prioritize_same_unit=prioritize_same_unit)

    # rebuild RstDepTrees
    dtree = RstDepTree(educe_edus)
    for src_id, tgt_id, lbl in dep_edges:
        if src_id == 'ROOT':
            if lbl not in ['ROOT', UNKNOWN]:
                err_msg = 'weird root label: {} {} {}'.format(
                    src_id, tgt_id, lbl)
                if strict:
                    raise ValueError(err_msg)
                else:
                    print('W: {}, using ROOT instead'.format(err_msg))
            dtree.set_root(gid2num[tgt_id])
        else:
            dtree.add_dependency(gid2num[src_id], gid2num[tgt_id], lbl)
    # add nuclearity: heuristic baseline
    dtree.nucs = nuc_classifier.predict([dtree])[0]
    # add rank: some strategies require a mapping from EDU to sentence
    # EXPERIMENTAL attach array of sentence index for each EDU in tree
    dtree.sent_idx = edu2sent
    # end EXPERIMENTAL
    dtree.ranks = rank_classifier.predict([dtree])[0]
    # end NEW

    # create pred ctree
    try:
        bin_srtrees = deptree_to_simple_rst_tree(dtree, allow_forest=True)
        if False:  # EXPERIMENTAL
            # currently False to run on output that already has
            # labels embedding nuclearity
            bin_srtrees = [SimpleRSTTree.incorporate_nuclearity_into_label(
                bin_srtree) for bin_srtree in bin_srtrees]
        bin_rtrees = [SimpleRSTTree.to_binary_rst_tree(bin_srtree)
                      for bin_srtree in bin_srtrees]
    except RstDtException as rst_e:
        print(rst_e)
        if False:
            print('\n'.join('{}: {}'.format(edu.text_span(), edu)
                            for edu in educe_edus[doc_name]))
        raise
    ctrees = bin_rtrees

    return ctrees


def get_spans(ctree):
    """Get the spans of a constituency tree, except for the root node.

    This corresponds to the spans used in the PARSEVAL metric modified
    for discourse, as described in (Marcu 2000) and implemented in
    Joty's evaluation scripts.

    Each span is descried by a triplet (edu_span, nuclearity, relation).
    """
    tnodes = [subtree.label()  # was: educe.internalutil.treenode(subtree)
              for root_child in ctree if isinstance(root_child, RSTTree)
              for subtree in root_child.subtrees()]
    spans = [(tn.edu_span, tn.nuclearity, tn.rel)
             for tn in tnodes]
    return spans


def oracle_ctree_spans(dep_edges, att_edus):
    """Get the spans of the oracle ctree for a given dtree.

    Parameters
    ----------
    dep_edges : dict(string, [(string, string, string)])
        Edges for each document, indexed by doc name (cf. return type of
        return value from
        irit-rst-dt/ctree.py:load_attelo_output_file()).
    att_edus: list of attelo EDUs
        List of attelo EDUs (cf. return type of attelo.io.load_edus).

    Returns
    -------
    spans: list of ((int, int), string, string)
        List of spans, described as (edu_span, nuclearity, relation)
    """
    # a single dependency tree with several real roots corresponds
    # to a forest of constituency trees
    oracle_ctrees = get_oracle_ctrees(dep_edges, att_edus)
    oracle_spans = list(itertools.chain.from_iterable(
        [get_spans(oracle_ctree) for oracle_ctree in oracle_ctrees]))
    return oracle_spans
