#!/bin/sh

# micromamba is a function defined in .bashrc
# so here we call the binary directly

exec ~/.local/bin/micromamba shell "$@"
