import logging
from itertools import chain

from django.conf import settings

from treeherder.model.models import (BugJobMap,
                                     ClassifiedFailure,
                                     FailureClassification,
                                     JobNote,
                                     TextLogSummaryLine)

logger = logging.getLogger(__name__)


def insert_autoclassify_job_note(self, job, user=None):
    if not settings.AUTOCLASSIFY_JOBS:
        return

    # Only insert bugs for verified failures since these are automatically
    # mirrored to ES and the mirroring can't be undone
    classified_failures = ClassifiedFailure.objects.filter(
        best_for_lines__job_guid=job.guid,
        best_for_lines__best_is_verified=True)

    text_log_summary_lines = TextLogSummaryLine.objects.filter(
        summary__job_guid=job.guid, verified=True).exclude(
            bug_number=None)

    bug_numbers = {item.bug_number
                   for item in chain(classified_failures,
                                     text_log_summary_lines)
                   if item.bug_number}

    for bug_number in bug_numbers:
        BugJobMap.objects.get_or_create(job=job,
                                        bug_id=bug_number,
                                        defaults={
                                            'user': user
                                        })

    # if user is not specified, then this is an autoclassified job note
    # and we should mark it as such
    if user is None:
        classification = FailureClassification.objects.get(
            name="autoclassified intermittent")
        logger.info("Autoclassifier adding job note")
    else:
        classification = FailureClassification.objects.get(name="intermittent")

    JobNote.objects.create(job=job,
                           failure_classification=classification,
                           user=user,
                           text="")
