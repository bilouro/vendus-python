"""MkDocs hook: publish a second copy of the generated sitemap under a different
filename.

Google Search Console can get stuck on a sitemap URL it once failed to fetch.
Publishing an identical, always-fresh copy under a new name gives a clean URL to
submit, without waiting for GSC to retry the original. The ``<loc>`` entries are
unchanged, so the alias stays valid for the same property.
"""

from __future__ import annotations

import os
import shutil
from typing import Any

ALIAS = "sitemap-vendus.xml"


def on_post_build(config: Any, **kwargs: Any) -> None:
    src = os.path.join(config["site_dir"], "sitemap.xml")
    if os.path.exists(src):
        shutil.copyfile(src, os.path.join(config["site_dir"], ALIAS))
