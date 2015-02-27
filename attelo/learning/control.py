"""
Central interface to the learners
"""

from attelo.table import for_attachment, for_labelling
from attelo.util import Team

# pylint: disable=too-few-public-methods

# ---------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------


def learn_attach(dpack, learners):
    """
    Train attachment learner
    """
    attach_pack = for_attachment(dpack)
    return learners.attach.fit(attach_pack.data,
                               attach_pack.target)


def learn_relate(dpack, learners):
    """
    Train relation learner
    """
    relate_pack = for_labelling(dpack.attached_only())
    return learners.relate.fit(relate_pack.data,
                               relate_pack.target)


def learn(dpack, learners):
    """
    Train learners for each attelo task. Return the resulting
    models

    :type learners: Team(learner)

    :rtype Team(model)
    """
    return Team(attach=learn_attach(dpack, learners),
                relate=learn_relate(dpack, learners))


def can_predict_proba(model):
    """
    True if a model is capable of returning a probability for
    a given instance. The alternative would be for it to
    implement `decision_function` which associates
    """
    if model == 'oracle':
        return True
    else:
        func = getattr(model, "predict_proba", None)
        return callable(func)
