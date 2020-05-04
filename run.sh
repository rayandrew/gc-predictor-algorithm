#!/usr/bin/env bash
set -euo pipefail

run_help() {
    echo "Available Commands: "
    echo "- help (this command)"
    echo "- train -c <config> -t type"
    echo "- train_all -c <config>"
    echo "- inference -c <config>"
    echo "- parse -c <config>"
}

run_train() {
    python gcpredictor/train.py "$@"
}

run_train_all() {
    parallel=false; [ "$1" == "parallel" ] && parallel=true
    shift;

    python gcpredictor/train.py "$@" -t nmethod
    python gcpredictor/train.py "$@" -t srt
    python gcpredictor/train.py "$@" -t trt
    python gcpredictor/train.py "$@" -t otyrt
    python gcpredictor/train.py "$@" -t references
    python gcpredictor/train.py "$@" -t prune

    if [ "$parallel" = true ] ; then
        python gcpredictor/train.py "$@" -t steal
    fi
}

run_parse() {
    python gcpredictor/parse.py "$@"
}

run_inference() {
    python gcpredictor/inference.py "$@"
}


if [ -z $1 ]
then
    run_help
else
    command=$1
    shift;
    run_${command} "$@"
fi
