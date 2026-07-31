# Local Jekyll environment for the ssc2 site.
#
# Mirrors the site.yml workflow: same Ruby minor version, same Gemfile,
# same `jekyll build`. Serving locally through this image is therefore a
# faithful preview of what GitHub Pages deploys -- in particular the
# baseurl prefix, which is the difference between a styled site and a
# bare-HTML one.
#
# Used via tools/serve_site.sh; see that script for the entry points.

FROM ruby:3.3-slim

# jekyll's native extensions (ffi, sass-embedded) need a toolchain; the
# sass-embedded binary is fetched at install time, hence curl/ca-certs.
RUN apt-get update \
 && apt-get install --no-install-recommends -y \
      build-essential ca-certificates curl git \
 && rm -rf /var/lib/apt/lists/*

# Bundler is configured through the environment rather than through
# `bundle config --local`, which would write .bundle/config into the
# working directory -- and the working directory is a bind mount at run
# time, so the image's copy would be shadowed by the host's (and the
# host's points at a gitignored site/vendor/ tree that does not exist
# inside the container).
ENV BUNDLE_PATH=/usr/local/bundle \
    BUNDLE_APP_CONFIG=/usr/local/bundle \
    BUNDLE_SILENCE_ROOT_WARNING=1 \
    HOME=/tmp

# Install gems from a scratch directory, in their own layer, so that
# editing site content does not invalidate the (slow) bundle install and
# so that nothing is left behind under the eventual mount point.
WORKDIR /build
COPY Gemfile Gemfile.lock ./
RUN bundle install

# Gems and their bundler config must stay readable/writable when the
# container is run as an arbitrary host uid (see tools/serve_site.sh),
# which is how build output ends up owned by the invoking user.
RUN chmod -R a+rX /usr/local/bundle

WORKDIR /srv/site

# 4000 = jekyll serve, 35729 = livereload
EXPOSE 4000 35729

CMD ["bundle", "exec", "jekyll", "serve", \
     "--host", "0.0.0.0", "--port", "4000", "--livereload", "--force_polling"]
