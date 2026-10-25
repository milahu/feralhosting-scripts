#!/usr/bin/env bash

set -e
set -x # xtrace

env_name=gunicorn
workdir=$HOME/src/milahu/opensubtitles-scraper
git_remote=https://github.com/milahu/opensubtitles-scraper

new_subs_dir=$HOME/src/milahu/opensubtitles-scraper-new-subs
new_subs_remote=https://github.com/milahu/opensubtitles-scraper-new-subs

if ! [ -e $new_subs_dir ]; then
  echo fetching $new_subs_remote
  git clone $new_subs_remote $new_subs_dir
  pushd $new_subs_dir
  ./git-pull.sh
  ./mount-branches.sh
  popd
fi

export SUBTITLES_DATA_DIR=$HOME/.config/subtitles # default
export CAS=$HOME/cas # cas/btih/xxx/dir/file

if ! command -v micromamba; then
  echo installing micromamba
  # https://github.com/mamba-org/micromamba-releases
  bash <(curl -L https://micro.mamba.pm/install.sh)
fi

eval "$(micromamba shell hook --shell bash)"

# deactivate any previous conda env
micromamba deactivate

if ! [ -e ~/micromamba/envs/$env_name ]; then
  micromamba create --name $env_name
fi

micromamba activate $env_name

# default version is python 3.5 ...
python_version_minor=13 # python>=3.13
if ! python3 -c "import sys; sys.exit(int(sys.version_info < (3, $python_version_minor)))"; then
  echo updating python
  echo old python version: $(python3 --version)
  micromamba install --yes "python>=3.$python_version_minor"
  echo new python version: $(python3 --version)
else
  echo python is up-to-date at $(python3 --version)
fi

if ! command -v gunicorn; then
  echo installing gunicorn
  micromamba install --yes gunicorn
fi

if ! [ -e $workdir ]; then
  git clone $git_remote $workdir
fi

cd $workdir

if false; then
  echo updating the git repo
  git reset --hard HEAD~10
  git pull origin main
  # TODO does this always work?
fi

python_deps="guessit langcodes charset_normalizer stream_zip platformdirs"
c=""
for d in $python_deps; do c+=", $d"; done
c=${c:2} # remove first ", "
c="import $c"
if ! python3 -c "$c"; then
  echo installing python dependencies
  pip3 install $python_deps
fi

echo starting WSGI server at unix:"$PWD"/docs/wsgi/get-subs.sock
exec ./docs/wsgi/gunicorn.sh
