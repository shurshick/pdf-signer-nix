from __future__ import annotations

import logging
import tempfile
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
        final_pdf = unique_path(output_dir / f"{source.stem}-signed.pdf")
        signature_path: Path | None = None
        embedded = job.signature_mode == "embedded"

        if job.signature_mode == "detached":
            LOG.info("Stamping PDF %s to final detached target", source.name)
            stamp_pdf(source, final_pdf, job.certificate, job.stamp)
            signature_path = unique_path(final_pdf.with_suffix(".sig"))
            LOG.info("Creating detached signature for %s", final_pdf.name)
            sign_detached(final_pdf, signature_path, job.certificate)
        else:
            with tempfile.TemporaryDirectory(prefix="pdf-signer-nix-stamp-") as temp_dir:
                stamped_temp = Path(temp_dir) / f"{source.stem}-stamped.pdf"
                LOG.info("Stamping PDF %s to temporary file for embedded signing", source.name)
                stamp_pdf(source, stamped_temp, job.certificate, job.stamp)
                LOG.info("Creating embedded signature for %s", stamped_temp.name)
                sign_embedded_pdf(stamped_temp, final_pdf, job.certificate, reason=job.stamp.reason)

        verified = None
        message = ""
        if job.verify_after_signing:
            target = signature_path or final_pdf
            report = verify_file(target)
            verified = report.status == "VALID"
            message = report.status_description
        results.append(SigningResult(source, final_pdf, signature_path, embedded, verified, message))
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
