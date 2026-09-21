#!/usr/bin/env bash

# https://www.feralhosting.com/wiki/software/python

version=3.9.7
# Download
wget "https://www.python.org/ftp/python/$version/Python-$version.tgz"
tar -zxvf "Python-$version.tgz"
rm "Python-$version.tgz"
cd "Python-$version"
# Install
./configure --prefix=$HOME/python
make
make altinstall
cd ..
rm -r "Python-$version"
majMin="${version%.*}"
ln -s "$HOME/python/bin/python${majMin}" ~/python/bin/python
ln -s "$HOME/python/bin/pip${majMin}" ~/python/bin/pip
