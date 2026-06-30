from __future__ import annotations

import logging
from pathlib import Path

from .crypto import sign_detached, sign_embedded_pdf
from .models import SigningJob, SigningResult
from .pdf_tools import stamp_pdf
from .verification import verify_file

LOG = logging.getLogger(__name__)


def run_signing_job(job: SigningJob) -> list[SigningResult]:
    results: list[SigningResult] = []
    job.stamp.normalize()
    for source in job.pdf_paths:
        output_dir = source.parent if job.save_next_to_source else job.output_dir
        stamped = unique_path(output_dir / f"{source.stem}-signed.pdf")
        LOG.info("Stamping PDF %s", source.name)
        stamp_pdf(source, stamped, job.certificate, job.stamp)
        signature_path: Path | None = None
        embedded = False
        if job.detached_only or job.create_detached_sig:
            signature_path = unique_path(stamped.with_suffix(".sig"))
            LOG.info("Creating detached signature for %s", stamped.name)
            sign_detached(stamped, signature_path, job.certificate)
        if not job.detached_only:
            embedded_target = unique_path(output_dir / f"{source.stem}-signed-embedded.pdf")
            LOG.info("Creating embedded signature for %s", stamped.name)
            sign_embedded_pdf(stamped, embedded_target, job.certificate)
            stamped = embedded_target
            embedded = True
        verified = None
        message = ""
        if job.verify_after_signing:
            target = signature_path or stamped
            report = verify_file(target)
            verified = report.status == "VALID"
            message = report.status_description
        results.append(SigningResult(source, stamped, signature_path, embedded, verified, message))
    return results


def unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    suffix = path.suffix
    stem = path.with_suffix("")
    for index in range(2, 10000):
        candidate = Path(f"{stem}-{index}{suffix}")
        if not candidate.exists():
            return candidate
    raise RuntimeError(f"Cannot create unique path for {path}")
