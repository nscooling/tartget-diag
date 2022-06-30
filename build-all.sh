#!/bin/bash

# The Build all script is intended for checking projects and solutions
# uploaded to a GIT repo for continuous integration checks.

# It looks for solutions to exercises in a "solutions" folder
# in a set of standard locations:

SOL_PATH=".. ../.. $HOME $HOME/course_material ."

# Solutions must be in folder names starting or ending with a digit and optional letter.
# If a solution folder contains a MakeLists.txt file a CMake build is run
# in the solution folder. If the solution contains an SConstruct file a
# scons build is run. Otherwise the build-one.sh command is run to
# build the solution.

set -o nounset 
set -o errexit

PROJ_DIR=$(dirname $(realpath "$0"))

SOL_DIR=
for dir in $SOL_PATH; do
  [[ -d $dir/solutions ]] && SOL_DIR="$dir/solutions" && break
done
[[ -z $SOL_DIR ]] && echo "Cannot find solutions folder in: $SOL_PATH" >&2 && exit 1

EX_DIR=$(ls $SOL_DIR | egrep '^[0-9]|[0-9][A-Z]?$') 
for ex in $EX_DIR; do
  if [[ -f $SOL_DIR/$ex/CMakeLists.txt ]]; then
    cd $SOL_DIR/$ex/
    cmake -S . -B build/
    cmake --build build/ --target clean    
    cmake --build build/
  elif [[ -f $SOL_DIR/$ex/SConscript ]]; then
    cd $SOL_DIR/$ex/
    scons -c
    scons
  else
    cd $PROJ_DIR
    $PROJ_DIR/build-one.sh $ex
  fi
done
