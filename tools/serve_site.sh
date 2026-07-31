#!/usr/bin/env bash
#
# Local Jekyll harness for the ssc2 site, for humans who want to look at
# the rendered pages before they ship.
#
# Everything runs inside a container built from site/Dockerfile, which
# pins the same Ruby and Gemfile as the site.yml workflow, so what you
# see locally is what GitHub Pages deploys. In particular the site is
# served under its baseurl prefix -- http://localhost:4000/stata-ssc2/,
# not http://localhost:4000/ -- because serving at the root would hide
# exactly the class of broken-asset-path bug this harness exists to
# catch.
#
# Commands:
#   serve   (default) live-reloading preview of site/ as it stands on
#           disk. Edits to .md/.html/.scss reload in the browser. Version
#           placeholders (@TOKEN@) are left unrendered -- use `build` for
#           a byte-faithful preview.
#   build   full CI replay: stages a copy of site/, runs the three
#           generator scripts against the copy, and builds it into
#           site/_site. The working tree is never modified.
#   test    `build`, then run the site checks in tests/test_site.py.
#   shell   interactive shell in the container.
#
# Usage: tools/serve_site.sh [serve|build|test|shell] [--port N] [--rebuild]

set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IMAGE="ssc2-site"
PORT=4000
REBUILD=0
COMMAND="serve"

while [ $# -gt 0 ]; do
  case "$1" in
    serve|build|test|shell) COMMAND="$1"; shift ;;
    --port) PORT="$2"; shift 2 ;;
    --rebuild) REBUILD=1; shift ;;
    -h|--help) sed -n '2,28p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done

# Either engine works; podman is preferred when both are present only if
# docker is not usable, to avoid surprising anyone with a working docker.
if docker info >/dev/null 2>&1; then
  ENGINE=docker
elif podman info >/dev/null 2>&1; then
  ENGINE=podman
else
  echo "neither docker nor podman is usable; one of them is required" >&2
  exit 1
fi

# The Gemfile is baked into the image, so rebuild whenever it changes.
if [ "$REBUILD" = 1 ] || ! "$ENGINE" image inspect "$IMAGE" >/dev/null 2>&1; then
  echo "==> building $IMAGE with $ENGINE"
  "$ENGINE" build -t "$IMAGE" "$REPO/site"
fi

# Read baseurl out of _config.yml rather than hardcoding it, so the URL
# printed below stays correct if the site ever moves.
BASEURL="$(sed -n 's/^baseurl:[ \t]*"\{0,1\}\([^"]*\)"\{0,1\}[ \t]*$/\1/p' "$REPO/site/_config.yml")"

# Staging area for `build`/`test`; gitignored.
STAGE="$REPO/site/.preview"

stage_and_generate() {
  echo "==> staging site/ into site/.preview/ (working tree untouched)"
  rm -rf "$STAGE"
  mkdir -p "$STAGE"
  tar -C "$REPO/site" \
      --exclude=./_site --exclude=./.preview --exclude=./vendor \
      --exclude=./.bundle --exclude=./.jekyll-cache --exclude=./__pycache__ \
      -cf - . | tar -C "$STAGE" -xf -

  # Same order as site.yml: render placeholders first, so that data
  # spliced in afterwards cannot trip the leftover-placeholder check.
  echo "==> rendering version placeholders"
  python3 "$REPO/tools/render_docs.py" "$STAGE/about.md" "$STAGE/index.html"
  echo "==> refreshing embedded snapshot data"
  python3 "$REPO/site/build_data.py" "$STAGE/index.html"
  echo "==> regenerating the Reference page"
  python3 "$REPO/site/build_reference.py" "$REPO/sthlp/ssc2.sthlp" "$STAGE/reference.md"
}

run_in_container() {
  # $1 = host directory to mount as the Jekyll source; rest = command.
  local source_dir="$1"; shift
  # -t only when there really is a terminal, so `build`/`test` still work
  # from a script or CI step.
  local tty=(); [ -t 0 ] && tty=(-it)
  # Ports are only published for the interactive commands; `build` binds
  # nothing, so it cannot collide with a preview already running.
  local ports=()
  case "$COMMAND" in
    serve|shell) ports=(-p "$PORT:4000" -p 35729:35729) ;;
  esac
  # Run as the invoking user so _site and .jekyll-cache come out owned by
  # them; a root-owned _site cannot even be moved out of the way later.
  # (podman remaps uids itself, so it only needs this under docker.)
  local as_user=()
  [ "$ENGINE" = docker ] && as_user=(--user "$(id -u):$(id -g)")
  "$ENGINE" run --rm "${tty[@]}" "${ports[@]}" "${as_user[@]}" \
    -v "$source_dir:/srv/site:z" \
    "$IMAGE" "$@"
}

case "$COMMAND" in
  serve)
    echo
    echo "==> serving at http://localhost:$PORT$BASEURL/"
    echo "    (the $BASEURL prefix is deliberate -- it matches GitHub Pages)"
    echo "    Ctrl-C to stop."
    echo
    run_in_container "$REPO/site" \
      bundle exec jekyll serve --host 0.0.0.0 --port 4000 \
        --livereload --force_polling
    ;;

  build)
    stage_and_generate
    echo "==> building into site/_site"
    rm -rf "$REPO/site/_site"
    run_in_container "$STAGE" \
      bundle exec jekyll build --destination /srv/site/_site
    rm -rf "$REPO/site/_site"
    mv "$STAGE/_site" "$REPO/site/_site"
    echo "==> built site/_site"
    ;;

  test)
    "${BASH_SOURCE[0]}" build --port "$PORT"
    echo "==> running site checks"
    ( cd "$REPO" && python3 -m unittest tests.test_site -v )
    ;;

  shell)
    run_in_container "$REPO/site" bash
    ;;
esac
