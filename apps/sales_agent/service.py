import os


def get_queue_stats(cases):
    """Compute summary stats for queue view."""
    total = len(cases)
    pending = sum(1 for c in cases if c["status"] == "Pending")
    in_progress = sum(1 for c in cases if c["status"] == "In Progress")
    completed = sum(1 for c in cases if c["status"] == "Completed")
    referred = sum(1 for c in cases if c["status"] == "Referred to Risk")
    return {
        "total": total,
        "pending": pending,
        "in_progress": in_progress,
        "completed": completed,
        "referred": referred,
    }


def get_doc_files(app_no, static_folder):
    """Look up local image files for an application in the static folder."""
    doc_dir = os.path.join(static_folder, "docs", app_no)
    doc_files = {}
    doc_types = ["pan", "aadhaar", "bank_statement", "proposal"]
    image_exts = (".jpg", ".jpeg", ".png", ".pdf", ".webp")

    if os.path.isdir(doc_dir):
        for fname in os.listdir(doc_dir):
            name_lower = fname.lower()
            for doc_type in doc_types:
                if (
                    name_lower.startswith(doc_type)
                    and os.path.splitext(name_lower)[1] in image_exts
                ):
                    doc_files[doc_type] = f"/static/docs/{app_no}/{fname}"
                    break
    return doc_files


def get_all_statuses_map(cases):
    """Return {app_no: status} map for bulk queue refresh."""
    return {
        c["app_no"]: {
            "status": c["status"],
            "uw_status": c["uw_status"],
            "updated_at": c["updated_at"],
        }
        for c in cases
    }
