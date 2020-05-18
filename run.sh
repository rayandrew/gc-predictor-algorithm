#!/usr/bin/env bash
# set -euo pipefail

PYTHON="python"

export PYTHONPATH="`pwd`:$PYTHONPATH"

run_help() {
    echo "Available Commands: "
    echo "- help (this command)"
    echo "- train -c <config> -t type"
    echo "- train_all -c <config>"
    echo "- inference -c <config>"
    echo "- parse -c <config>"
}

run_train() {
    $PYTHON gcpredictor/train.py "$@"
}

run_train_all() {
    parallel=false; [ "$1" == "parallel" ] && parallel=true
    shift;

    echo "parallel = $parallel"

    $PYTHON gcpredictor/train.py "$@" -t ptt
    # $PYTHON gcpredictor/train.py "$@" -t trt

    # $PYTHON gcpredictor/train.py "$@" -t nmethod
    # $PYTHON gcpredictor/train.py "$@" -t srt
    # $PYTHON gcpredictor/train.py "$@" -t otyrt
    # $PYTHON gcpredictor/train.py "$@" -t references
    # $PYTHON gcpredictor/train.py "$@" -t prune

    # if [ "$parallel" = true ] ; then
    #     $PYTHON gcpredictor/train.py "$@" -t steal
    # fi
}

run_parse() {
    $PYTHON gcpredictor/parse.py "$@"
}

run_inference() {
    $PYTHON gcpredictor/inference.py "$@"
}


if [ -z $1 ]
then
    run_help
else
    command=$1
    shift;
    run_${command} "$@"
fi
