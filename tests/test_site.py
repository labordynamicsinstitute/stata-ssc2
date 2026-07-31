"""Checks on the Jekyll site configuration and, when it has been built,
on the links in the generated HTML.

The site is deployed to GitHub *project* Pages at
https://labordynamicsinstitute.github.io/stata-ssc2/, i.e. under a path
prefix rather than at the host root. Jekyll only emits that prefix when
`baseurl` is set; without it every `{{ site.baseurl }}`-derived link --
including the theme's stylesheets -- points at the host root and 404s,
which renders the site completely unstyled.

Standard library only, matching the rest of this repository's Python.
The built-output checks are skipped when site/_site is absent, so the
module still passes on a clean checkout (site/_site is gitignored);
tools/serve_site.sh builds it.
"""

import re
import unittest
from pathlib import Path
from urllib.parse import urlparse

REPO = Path(__file__).resolve().parent.parent
CONFIG = REPO / "site" / "_config.yml"
BUILT = REPO / "site" / "_site"

# Where GitHub publishes this repository's Pages site, and the path
# prefix that follows from it.
DEPLOY_URL = "https://labordynamicsinstitute.github.io/stata-ssc2"
BASEURL = "/stata-ssc2"

# Top-level `key: value` in _config.yml, ignoring nested/list entries.
_TOP_LEVEL = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*):[ \t]*(.*?)[ \t]*$")

# href="..." / src="..." in the generated HTML.
_LINK = re.compile(r'(?:href|src)="([^"]*)"')


def read_config():
    """Return the top-level scalar keys of _config.yml as a dict of strings."""
    values = {}
    for line in CONFIG.read_text(encoding="utf-8").splitlines():
        match = _TOP_LEVEL.match(line)
        if match:
            values[match.group(1)] = match.group(2).strip().strip('"').strip("'")
    return values


class BaseUrlConfigTest(unittest.TestCase):
    def setUp(self):
        self.config = read_config()

    def test_url_is_the_origin_only(self):
        """`url` is the origin; the path prefix belongs in `baseurl`."""
        self.assertIn("url", self.config, "_config.yml must set url")
        self.assertEqual(
            urlparse(self.config["url"]).path.rstrip("/"),
            "",
            "url must carry no path -- Jekyll takes the path prefix from "
            "baseurl, and a path smuggled into url is silently ignored when "
            "building asset links",
        )

    def test_baseurl_is_the_project_pages_prefix(self):
        self.assertEqual(
            self.config.get("baseurl", ""),
            BASEURL,
            "baseurl must be %r, otherwise Jekyll emits root-absolute asset "
            "links that 404 on GitHub project Pages" % BASEURL,
        )

    def test_url_and_baseurl_reconstruct_the_deployment_url(self):
        self.assertEqual(
            self.config["url"].rstrip("/") + self.config.get("baseurl", ""),
            DEPLOY_URL,
            "url + baseurl must equal the address the site is published at",
        )


class BuiltLinkTest(unittest.TestCase):
    """Every root-absolute link in the built HTML must carry the prefix."""

    def setUp(self):
        if not BUILT.is_dir():
            self.skipTest("site/_site not built; run tools/serve_site.sh build")
        self.pages = sorted(BUILT.rglob("*.html"))
        if not self.pages:
            self.skipTest("site/_site contains no HTML")
        self.baseurl = read_config().get("baseurl", "")

    def test_root_absolute_links_are_prefixed(self):
        offenders = []
        for page in self.pages:
            for link in _LINK.findall(page.read_text(encoding="utf-8")):
                # Only site-root-absolute links can lose the prefix;
                # protocol-relative (//), fragment, and relative links cannot.
                if not link.startswith("/") or link.startswith("//"):
                    continue
                if link == self.baseurl or link.startswith(self.baseurl + "/"):
                    continue
                offenders.append("%s: %s" % (page.relative_to(BUILT), link))
        self.assertEqual(
            [],
            offenders,
            "links missing the %r prefix will 404 on GitHub project Pages:\n%s"
            % (self.baseurl, "\n".join(offenders)),
        )

    def test_theme_stylesheet_is_linked_and_present(self):
        """The symptom that started this: the theme CSS must resolve on disk."""
        index = BUILT / "index.html"
        self.assertTrue(index.is_file(), "site/_site/index.html not built")
        html = index.read_text(encoding="utf-8")
        sheets = [
            link
            for link in _LINK.findall(html)
            if link.startswith("/") and link.endswith(".css")
        ]
        self.assertTrue(sheets, "index.html links no stylesheet")
        for sheet in sheets:
            relative = sheet[len(self.baseurl) :].lstrip("/")
            self.assertTrue(
                (BUILT / relative).is_file(),
                "index.html links %s but %s was not generated" % (sheet, relative),
            )


if __name__ == "__main__":
    unittest.main()
